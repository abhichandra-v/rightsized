"""rightsized CLI.

  collect  -> snapshot.json            (read-only: kubectl + Prometheus)
  analyze  -> evidence table + savings (offline, from a snapshot)
  pr       -> patched files + PR body  (optionally opens the PR with git + gh)
  capture  -> cluster.json for one load-test run
  verify   -> guardrail table; exit 1 means roll back
  compare  -> rightsized vs stock VPA on the same snapshot
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import replace
from pathlib import Path

from . import gitops, recommend, report, savings, verify, vpa
from .config import Config, load_config
from .models import Recommendation, Snapshot, Verdict


def _recs(args, cfg: Config, snap: Snapshot) -> list[Recommendation]:
    if getattr(args, "vpa", None):
        return vpa.recommendations(snap, json.loads(Path(args.vpa).read_text()), cfg.policy)
    return recommend.analyze(snap, cfg.policy)


def _split(recs: list[Recommendation], cfg: Config, source_is_vpa: bool):
    changed = [r for r in recs if r.changed]
    if source_is_vpa:  # stock VPA arm: apply everything it recommends
        return changed, []
    allowed = {Verdict(v) for v in cfg.policy.apply_verdicts}
    return [r for r in changed if r.verdict in allowed], [r for r in changed if r.verdict not in allowed]


def _load_snapshot(path: str, cfg: Config) -> Snapshot:
    snap = Snapshot.load(path)
    if snap.node_pool is None and cfg.node_pool is not None:
        snap = replace(snap, node_pool=cfg.node_pool)
    return snap


def cmd_collect(args, cfg: Config) -> int:
    from .collect import Prometheus, collect

    snap = collect(Prometheus(cfg.prometheus_url), cfg.namespaces, args.window or cfg.window,
                   args.cluster, cfg.node_pool)
    snap.save(args.out)
    print(f"wrote {args.out}: {len(snap.containers)} containers, window {snap.window}")
    return 0


def cmd_analyze(args, cfg: Config) -> int:
    snap = _load_snapshot(args.snapshot, cfg)
    recs = _recs(args, cfg, snap)
    applied, held = _split(recs, cfg, bool(args.vpa))
    print(report.evidence_table(recs))
    print()
    print(report.reasons_list(recs))
    s = savings.compute(snap, applied) if snap.node_pool else None
    if s:
        print("\n" + report.savings_section(s))
    if args.json:
        Path(args.json).write_text(json.dumps({
            "applied": [r.key for r in applied],
            "held": [r.key for r in held],
            "savings": s.as_dict() if s else None,
        }, indent=2) + "\n")
    return 0


def cmd_pr(args, cfg: Config) -> int:
    snap = _load_snapshot(args.snapshot, cfg)
    recs = _recs(args, cfg, snap)
    applied, held = _split(recs, cfg, bool(args.vpa))
    repo = Path(args.repo)
    files, missing = gitops.apply_to_repo(repo, applied, cfg)
    for key in missing:
        print(f"warning: no Git target configured for {key}; skipped", file=sys.stderr)
    s = savings.compute(snap, applied) if snap.node_pool else None
    body = report.pr_body(applied, held, s, args.snapshot, snap.window)
    Path(args.body_out).write_text(body)
    print(f"patched {len(files)} file(s); PR body in {args.body_out}")
    if args.open:
        title = args.title or f"rightsized: resize {len(applied)} container(s)"
        print(gitops.open_pr(repo, files, args.branch, title, body, args.base))
    return 0


def cmd_capture(args, cfg: Config) -> int:
    from .collect import Prometheus, node_count

    prom = Prometheus(cfg.prometheus_url)
    ns = "|".join(cfg.namespaces)
    d = args.duration
    out = {
        "oom_events": int(prom.scalar(
            f'sum(increase(container_oom_events_total{{namespace=~"{ns}"}}[{d}])) or vector(0)')),
        "max_throttle_ratio": prom.scalar(
            f'max(sum by (namespace, pod, container) (increase(container_cpu_cfs_throttled_periods_total'
            f'{{namespace=~"{ns}"}}[{d}])) / sum by (namespace, pod, container) '
            f'(increase(container_cpu_cfs_periods_total{{namespace=~"{ns}"}}[{d}])))'),
        "nodes": node_count(args.node_selector),
    }
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out))
    return 0


def _runs(specs: list[str]) -> list[verify.RunMetrics]:
    runs = []
    for spec in specs:
        k6, _, cluster = spec.partition(":")
        runs.append(verify.RunMetrics.from_files(Path(k6), Path(cluster) if cluster else None))
    return runs


def cmd_verify(args, cfg: Config) -> int:
    base, cand = _runs(args.baseline), _runs(args.candidate)
    checks = verify.verify(base, cand, cfg.guardrails)
    md = verify.render(checks)
    nodes = verify.node_change(base, cand)
    if nodes:
        before, after = nodes
        md += f"\nNodes (measured, median across runs): {before} → {after}"
        if cfg.node_pool:
            usd = (before - after) * cfg.node_pool.hourly_usd * savings.HOURS_PER_MONTH
            md += f" ≈ ${usd:,.2f}/mo at {cfg.node_pool.instance_type} pricing"
        md += "\n"
    print(md)
    if args.out:
        Path(args.out).write_text(md)
    return 0 if all(c.passed for c in checks) else 1


def cmd_compare(args, cfg: Config) -> int:
    snap = _load_snapshot(args.snapshot, cfg)
    ours, _ = _split(recommend.analyze(snap, cfg.policy), cfg, False)
    theirs, _ = _split(vpa.recommendations(snap, json.loads(Path(args.vpa).read_text()), cfg.policy), cfg, True)
    s_ours, s_vpa = savings.compute(snap, ours), savings.compute(snap, theirs)
    flagged = [r for r in theirs if r.verdict is not Verdict.SAFE]
    print("| Arm | Containers changed | CPU reclaimed | Mem reclaimed | Nodes (sim) | $/mo (sim) | "
          "Changes our scorer would hold |")
    print("|---|---|---|---|---|---|---|")
    for name, recs, s, held in (("rightsized", ours, s_ours, 0), ("stock VPA", theirs, s_vpa, len(flagged))):
        print(f"| {name} | {len(recs)} | {s.cpu_reclaimed:.2f} cores | {s.memory_reclaimed / 2**30:.2f} GiB | "
              f"{s.nodes_before} → {s.nodes_after} | ${s.node_monthly_usd:,.2f} | {held} |")
    if flagged:
        print("\nVPA changes the risk scorer would not auto-apply:")
        print(report.reasons_list(flagged))
    print("\nSimulated only. Regressions come from `rightsized verify` on each arm's load-test runs.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="rightsized", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-c", "--config", default=os.environ.get("RIGHTSIZED_CONFIG", "rightsized.yaml"))
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("collect", help="snapshot usage + spec from a live cluster")
    p.add_argument("--out", default="snapshot.json")
    p.add_argument("--cluster", default="kind-rightsized")
    p.add_argument("--window")
    p.set_defaults(fn=cmd_collect)

    p = sub.add_parser("analyze", help="recommendations, verdicts and savings from a snapshot")
    p.add_argument("snapshot")
    p.add_argument("--vpa", help="score stock VPA recommendations (kubectl get vpa -A -o json) instead")
    p.add_argument("--json", help="write machine-readable summary here")
    p.set_defaults(fn=cmd_analyze)

    p = sub.add_parser("pr", help="patch manifests/values and write (or open) a PR")
    p.add_argument("snapshot")
    p.add_argument("--repo", default=".")
    p.add_argument("--vpa", help="apply stock VPA targets instead (head-to-head arm)")
    p.add_argument("--body-out", default="pr-body.md")
    p.add_argument("--open", action="store_true", help="commit, push and run gh pr create")
    p.add_argument("--branch", default="rightsized/resize")
    p.add_argument("--base", default="main")
    p.add_argument("--title")
    p.set_defaults(fn=cmd_pr)

    p = sub.add_parser("capture", help="record OOMs, throttling and node count for one load-test run")
    p.add_argument("--duration", required=True, help="PromQL range covering the run, e.g. 30m")
    p.add_argument("--node-selector", default="")
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_capture)

    p = sub.add_parser("verify", help="compare baseline vs candidate runs against guardrails")
    p.add_argument("--baseline", nargs="+", required=True, metavar="K6.json[:cluster.json]")
    p.add_argument("--candidate", nargs="+", required=True, metavar="K6.json[:cluster.json]")
    p.add_argument("--out")
    p.set_defaults(fn=cmd_verify)

    p = sub.add_parser("compare", help="rightsized vs stock VPA on the same snapshot")
    p.add_argument("snapshot")
    p.add_argument("--vpa", required=True)
    p.set_defaults(fn=cmd_compare)

    args = ap.parse_args(argv)
    return args.fn(args, load_config(args.config))


if __name__ == "__main__":
    sys.exit(main())
