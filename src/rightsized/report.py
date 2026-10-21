"""Markdown rendering: the PR description and the evidence table."""

from __future__ import annotations

from .models import Recommendation, Verdict
from .savings import SavingsReport
from .units import format_cpu, format_memory

ICON = {Verdict.SAFE: "🟢 safe", Verdict.REVIEW: "🟡 review", Verdict.DONT_TOUCH: "🔴 don't touch"}


def _cpu(v: float | None) -> str:
    return "-" if v is None else format_cpu(v)


def _mem(v: int | float | None) -> str:
    return "-" if v is None else format_memory(int(v))


def _delta(old, new) -> str:
    if not old or new is None:
        return ""
    pct = (new - old) / old * 100
    return f" ({pct:+.0f}%)" if abs(pct) >= 0.5 else ""


def evidence_table(recs: list[Recommendation]) -> str:
    rows = [
        "| Workload / container | Verdict | CPU req | Mem req | CPU p50 / p95 / p99 / peak | "
        "Mem p99 / peak | Throttle | OOM | Restarts | Confidence |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in recs:
        ev = r.evidence
        rows.append(
            f"| `{ev.workload}/{ev.container}` ×{ev.replicas} | {ICON[r.verdict]} "
            f"| {_cpu(ev.requests.cpu)} → **{_cpu(r.requests.cpu)}**{_delta(ev.requests.cpu, r.requests.cpu)} "
            f"| {_mem(ev.requests.memory)} → **{_mem(r.requests.memory)}**"
            f"{_delta(ev.requests.memory, r.requests.memory)} "
            f"| {_cpu(ev.cpu.p50)} / {_cpu(ev.cpu.p95)} / {_cpu(ev.cpu.p99)} / {_cpu(ev.cpu.max)} "
            f"| {_mem(ev.memory.p99)} / {_mem(ev.memory.max)} "
            f"| {ev.throttle_ratio:.1%} | {ev.oom_events} | {ev.restarts} | {r.confidence:.2f} |"
        )
    return "\n".join(rows)


def reasons_list(recs: list[Recommendation]) -> str:
    lines = []
    for r in recs:
        why = "; ".join(r.reasons) if r.reasons else "no risk signals"
        lines.append(f"- `{r.key}`: {ICON[r.verdict]} ({r.risk_points} pts): {why}")
    return "\n".join(lines)


def savings_section(s: SavingsReport) -> str:
    measured = (
        f"{s.measured_nodes_before} → {s.measured_nodes_after} nodes, ${s.measured_monthly_usd:,.2f}/mo"
        if s.measured_monthly_usd is not None
        else "_pending: `rightsized verify` reports node counts once the autoscaler has consolidated_"
    )
    return "\n".join([
        "| | Value |",
        "|---|---|",
        f"| Requests reclaimed (on paper) | {s.cpu_reclaimed:.2f} cores, {s.memory_reclaimed / 2**30:.2f} GiB "
        f"(≈ ${s.paper_monthly_usd:,.2f}/mo if every unit were billable) |",
        f"| Nodes after bin-packing (simulated) | {s.nodes_before} → {s.nodes_after}, "
        f"${s.node_monthly_usd:,.2f}/mo |",
        f"| Nodes after autoscaler (measured) | {measured} |",
    ])


def pr_body(applied: list[Recommendation], held: list[Recommendation], savings: SavingsReport | None,
            snapshot_ref: str, window: str) -> str:
    parts = [
        "## Rightsized: resource request changes",
        "",
        f"Evidence window: **{window}**. Raw data: `{snapshot_ref}`. "
        "This PR changes only `resources`; it does not touch the cluster directly.",
        "",
    ]
    if savings:
        parts += ["### Savings", "", savings_section(savings), ""]
    parts += ["### Applied in this PR", "", evidence_table(applied) if applied else "_none_", ""]
    if held:
        parts += ["### Not applied (needs a human)", "", evidence_table(held), ""]
    parts += [
        "### Why each verdict",
        "",
        reasons_list(applied + held),
        "",
        "### Merge checklist",
        "",
        "- [ ] `rightsized verify` passed on the baseline vs candidate load test (p99, errors, OOM, throttling)",
        "- [ ] Rollback plan: revert this PR; the previous values are in the diff",
        "",
    ]
    return "\n".join(parts)
