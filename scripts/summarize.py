"""Rebuild the results summary from raw run files. No number in the write-up is typed by hand.

    python scripts/summarize.py results-published/<run>/ > results-published/<run>/SUMMARY.md

Reads the snapshot, the VPA objects, and every k6 summary + cluster capture; recomputes
recommendations, savings and guardrail checks with the same code the pipeline used.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from rightsized import recommend, report, savings, verify, vpa
from rightsized.config import load_config
from rightsized.models import Snapshot, Verdict


def runs(d: Path) -> list[verify.RunMetrics]:
    out = []
    for k6 in sorted(d.glob("run*.json")):
        if k6.name.endswith(".cluster.json"):
            continue
        cluster = k6.with_name(k6.stem + ".cluster.json")
        out.append(verify.RunMetrics.from_files(k6, cluster if cluster.exists() else None))
    return out


def main(root: Path) -> None:
    cfg = load_config(root / "rightsized.demo.yaml")
    snap = Snapshot.load(root / "snapshot.json")
    if snap.node_pool is None:
        snap.node_pool = cfg.node_pool
    ours = recommend.analyze(snap, cfg.policy)
    applied = [r for r in ours if r.changed and r.verdict.value in cfg.policy.apply_verdicts]
    vpa_list = json.loads((root / "vpa.json").read_text())
    theirs = [r for r in vpa.recommendations(snap, vpa_list, cfg.policy) if r.changed]

    print(f"# Results: {snap.cluster}, collected {snap.collected_at}\n")
    env = root / "environment.txt"
    if env.exists():
        print("```\n" + env.read_text().strip() + "\n```\n")

    counts = Counter(r.verdict for r in ours)
    print("## Verdicts\n")
    print(" · ".join(f"{report.ICON[v]}: {counts.get(v, 0)}" for v in Verdict), "\n")
    print(report.evidence_table(ours), "\n")
    print(report.reasons_list(ours), "\n")

    base = runs(root / "baseline")
    arms = {"rightsized": (applied, root / "candidate"), "stock VPA": (theirs, root / "vpa")}
    print("## Savings and SLOs, per arm\n")
    print("| Arm | Containers changed | CPU reclaimed | Mem reclaimed | Nodes (bin-packed sim) | $/mo (sim) "
          "| p99 ms (median) | Errors | New restarts | Unavailable | Guardrails |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    details = []
    for name, (recs, d) in arms.items():
        s = savings.compute(snap, recs)
        cand = runs(d) if d.exists() else []
        if base and cand:
            checks = verify.verify(base, cand, cfg.guardrails)
            ok = "✅ pass" if all(c.passed for c in checks) else "❌ " + ", ".join(c.name for c in checks if not c.passed)
            p99 = next(c for c in checks if "p99" in c.name)
            err = next(c for c in checks if "error" in c.name)
            rst = next(c for c in checks if "restarts" in c.name)
            una = next(c for c in checks if "available" in c.name)
            slo = (f"{p99.baseline:.1f} → {p99.candidate:.1f} | {err.baseline:.2%} → {err.candidate:.2%} | "
                   f"{rst.candidate - rst.baseline:+.0f} | {una.spread or 'none'} | {ok}")
            details.append((name, verify.render(checks)))
        else:
            slo = "– | – | – | – | not run"
        print(f"| {name} | {len(recs)} | {s.cpu_reclaimed:.2f} cores | {s.memory_reclaimed / 2**30:.2f} GiB | "
              f"{s.nodes_before} → {s.nodes_after} | ${s.node_monthly_usd:,.2f} | {slo} |")
    print()
    print(f"Paper value of rightsized's reclaimed requests: "
          f"${savings.compute(snap, applied).paper_monthly_usd:,.2f}/mo at {snap.node_pool.instance_type} pricing. "
          "Node and dollar figures are bin-packing simulations: kind has a fixed node count and no autoscaler.\n")
    for name, md in details:
        print(f"### Guardrails: {name}\n\n{md}")
    for name, d in (("baseline", root / "baseline"), ("rightsized", root / "candidate"), ("stock VPA", root / "vpa")):
        tops = [json.loads(f.read_text()) for f in sorted(d.glob("run*.cluster.json"))] if d.exists() else []
        if any("top_throttled" in t for t in tops):
            print(f"### Attribution: {name}\n")
            for i, t in enumerate(tops, 1):
                print(f"- run {i}: throttled {t.get('top_throttled') or '-'}; restarts {t.get('top_restarts') or '-'}")
            print()

    flagged = [r for r in theirs if r.verdict is not Verdict.SAFE]
    if flagged:
        print("## VPA changes rightsized's scorer would have held back\n")
        print(report.reasons_list(flagged), "\n")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
