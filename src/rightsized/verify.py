"""Closed-loop verification: compare baseline and candidate load-test runs against SLO guardrails.

Each side should be several runs of the same k6 script; we compare medians and print the
spread, so a reader can see whether a delta is bigger than run-to-run noise.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from pathlib import Path

from .config import Guardrails


@dataclass
class RunMetrics:
    p99_ms: float
    p95_ms: float
    error_rate: float  # 0..1
    oom_events: int = 0
    max_throttle_ratio: float = 0.0
    nodes: int | None = None

    @classmethod
    def from_files(cls, k6_summary: Path, cluster: Path | None = None) -> "RunMetrics":
        m = json.loads(Path(k6_summary).read_text())["metrics"]
        dur = m["http_req_duration"]
        dur = dur.get("values", dur)  # handleSummary() nests under "values"; --summary-export does not
        failed = m["http_req_failed"]
        failed = failed.get("values", failed)
        rate = failed.get("rate", failed.get("value", 0.0))
        c = json.loads(Path(cluster).read_text()) if cluster else {}
        return cls(
            p99_ms=dur["p(99)"],
            p95_ms=dur["p(95)"],
            error_rate=rate,
            oom_events=int(c.get("oom_events", 0)),
            max_throttle_ratio=float(c.get("max_throttle_ratio", 0.0)),
            nodes=c.get("nodes"),
        )


@dataclass
class Check:
    name: str
    baseline: float
    candidate: float
    limit: float
    spread: str
    passed: bool


def _median(runs: list[RunMetrics], attr: str) -> float:
    return statistics.median(getattr(r, attr) for r in runs)


def _spread(runs: list[RunMetrics], attr: str, fmt: str) -> str:
    vals = [getattr(r, attr) for r in runs]
    return f"{format(min(vals), fmt)}–{format(max(vals), fmt)}" if len(vals) > 1 else "n=1"


def verify(baseline: list[RunMetrics], candidate: list[RunMetrics], g: Guardrails) -> list[Check]:
    if not baseline or not candidate:
        raise ValueError("need at least one baseline and one candidate run")
    b_p99, c_p99 = _median(baseline, "p99_ms"), _median(candidate, "p99_ms")
    b_err, c_err = _median(baseline, "error_rate"), _median(candidate, "error_rate")
    c_oom = max(r.oom_events for r in candidate)
    b_thr, c_thr = _median(baseline, "max_throttle_ratio"), _median(candidate, "max_throttle_ratio")

    p99_limit = b_p99 * (1 + g.p99_latency_increase_pct / 100)
    err_limit = b_err + g.error_rate_increase_pp / 100
    thr_limit = max(g.max_throttle_ratio, b_thr)
    return [
        Check("p99 latency (ms)", b_p99, c_p99, p99_limit,
              f"{_spread(baseline, 'p99_ms', '.0f')} vs {_spread(candidate, 'p99_ms', '.0f')}", c_p99 <= p99_limit),
        Check("error rate", b_err, c_err, err_limit,
              f"{_spread(baseline, 'error_rate', '.2%')} vs {_spread(candidate, 'error_rate', '.2%')}",
              c_err <= err_limit),
        Check("OOM events during run", max(r.oom_events for r in baseline), c_oom, g.max_new_oom_events,
              "", c_oom <= g.max_new_oom_events),
        Check("max container throttle ratio", b_thr, c_thr, thr_limit,
              f"{_spread(baseline, 'max_throttle_ratio', '.1%')} vs {_spread(candidate, 'max_throttle_ratio', '.1%')}",
              c_thr <= thr_limit),
    ]


def node_change(baseline: list[RunMetrics], candidate: list[RunMetrics]) -> tuple[int, int] | None:
    """Median node count per side, if every run recorded one. Meaningful only with an autoscaler."""
    if any(r.nodes is None for r in baseline + candidate):
        return None
    return int(statistics.median(r.nodes for r in baseline)), int(statistics.median(r.nodes for r in candidate))


def render(checks: list[Check]) -> str:
    def fmt(name: str, v: float) -> str:
        if "rate" in name or "ratio" in name:
            return f"{v:.2%}"
        return f"{v:.0f}" if "OOM" in name else f"{v:.1f}"

    rows = ["| Guardrail | Baseline | Candidate | Limit | Run spread (base vs cand) | Result |",
            "|---|---|---|---|---|---|"]
    for c in checks:
        rows.append(f"| {c.name} | {fmt(c.name, c.baseline)} | {fmt(c.name, c.candidate)} | "
                    f"≤ {fmt(c.name, c.limit)} | {c.spread} | {'✅ pass' if c.passed else '❌ FAIL'} |")
    verdict = "PASS: keep the change" if all(c.passed for c in checks) else "FAIL: roll back"
    return "\n".join(rows) + f"\n\n**Verdict: {verdict}**\n"
