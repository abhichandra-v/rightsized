"""Turn evidence into new requests/limits, then score how much to trust the change."""

from __future__ import annotations

from .config import Policy
from .models import ContainerEvidence, Recommendation, Resources, Snapshot, Verdict
from .units import round_up


def _rel_change(old: float | None, new: float) -> float:
    if not old:
        return float("inf")
    return (new - old) / old


def size(ev: ContainerEvidence, p: Policy) -> tuple[Resources, Resources, list[str]]:
    """Compute new requests and limits for one container. Returns (requests, limits, notes)."""
    notes: list[str] = []
    cur_req, cur_lim = ev.requests, ev.limits

    cpu_basis = getattr(ev.cpu, p.cpu_percentile)
    cpu = max(p.cpu_floor, round_up(cpu_basis * (1 + p.cpu_margin), p.cpu_step))

    # Memory is sized from the observed peak, not a percentile, with a wider margin:
    # undersized memory kills the pod, undersized CPU only slows it down.
    mem = max(p.memory_floor, int(round_up(ev.memory.max * (1 + p.memory_margin), p.memory_step)))

    if ev.oom_events > 0:
        # The observed peak is capped by the limit that killed it, so true demand is unknown.
        ceiling = cur_lim.memory or cur_req.memory or ev.memory.max
        floor = int(round_up(ceiling * 1.25, p.memory_step))
        if mem < floor:
            mem = floor
        notes.append(f"{ev.oom_events} OOM event(s): memory raised 25% above the limit that was hit")

    if ev.throttle_ratio >= p.throttle_warn and cur_req.cpu and cpu < cur_req.cpu:
        # Usage is capped by the CPU limit while throttled, so percentiles understate demand.
        cpu = cur_req.cpu
        notes.append(f"throttled {ev.throttle_ratio:.0%}: CPU request held, not lowered")

    if cur_req.memory and mem < cur_req.memory * (1 - p.max_memory_step_down):
        mem = int(round_up(cur_req.memory * (1 - p.max_memory_step_down), p.memory_step))
        notes.append(f"memory step capped at -{p.max_memory_step_down:.0%} for this PR")

    if cur_req.cpu and abs(_rel_change(cur_req.cpu, cpu)) < p.min_change:
        cpu = cur_req.cpu
    if cur_req.memory and abs(_rel_change(cur_req.memory, mem)) < p.min_change:
        mem = cur_req.memory

    lim_cpu = cur_lim.cpu
    if lim_cpu is not None:
        if ev.throttle_ratio >= p.throttle_warn:
            lim_cpu = max(lim_cpu * 1.5, cpu)
            notes.append("CPU limit raised 50% to relieve throttling")
        lim_cpu = max(lim_cpu, cpu)
    lim_mem = cur_lim.memory
    if lim_mem is not None:
        lim_mem = max(lim_mem, mem)

    return Resources(cpu=cpu, memory=mem), Resources(cpu=lim_cpu, memory=lim_mem), notes


def score(rec: Recommendation, p: Policy) -> Recommendation:
    """Attach verdict, confidence and human-readable reasons to a recommendation."""
    ev = rec.evidence
    reasons = list(rec.reasons)
    points = 0
    hard_block = False

    hours = ev.observed_seconds / 3600
    coverage = min(1.0, hours / (p.full_window_days * 24))
    stability = 1 / (1 + max(0.0, ev.cpu.cv - 0.25))
    confidence = round(coverage * stability, 2)

    cpu_delta = _rel_change(ev.requests.cpu, rec.requests.cpu or 0)
    mem_delta = _rel_change(ev.requests.memory, rec.requests.memory or 0)
    cpu_down = cpu_delta < 0
    mem_down = mem_delta < 0

    # Data confidence
    if hours < p.min_window_hours:
        hard_block = True
        reasons.append(f"only {hours:.1f}h of data (< {p.min_window_hours:.0f}h minimum)")
    elif hours < p.full_window_days * 24:
        points += 2
        reasons.append(f"{hours / 24:.1f}d observed: weekly peak not yet seen")
    if ev.cpu.cv > 0.5 and ev.cpu.mean >= p.cpu_noise_floor:
        points += 1
        reasons.append(f"high CPU variance (CV {ev.cpu.cv:.2f})")
    if cpu_down and ev.cpu.max >= 2 * p.cpu_noise_floor and ev.cpu.max / ev.cpu.p95 > 3:
        points += 1
        reasons.append(f"bursty CPU: peak is {ev.cpu.max / ev.cpu.p95:.1f}x p95")
    if mem_down and ev.memory.p50 > 0 and ev.memory.max / ev.memory.p50 > 2:
        points += 1
        reasons.append(f"bursty memory: peak is {ev.memory.max / ev.memory.p50:.1f}x p50")

    # Failure signals
    if ev.oom_events > 0:
        points += 3
        reasons.append("OOMKilled during window: memory must not go down; needs a human")
        if mem_down:
            hard_block = True
    if ev.throttle_ratio >= p.throttle_block and cpu_down:
        hard_block = True
        reasons.append(f"severe throttling ({ev.throttle_ratio:.0%}) and CPU would drop")
    elif ev.throttle_ratio >= p.throttle_warn:
        points += 2
        reasons.append(f"CPU throttled {ev.throttle_ratio:.0%} of periods")
    if ev.restarts >= p.restart_warn:
        points += 1
        reasons.append(f"{ev.restarts} restarts in window")

    # Blast radius
    if ev.replicas <= 1:
        points += 1
        reasons.append("single replica: a bad change is an outage")
    if not ev.has_pdb:
        points += 1
        reasons.append("no PodDisruptionBudget")
    if ev.criticality == "critical":
        points += 2
        reasons.append("labelled critical")

    if hard_block:
        verdict = Verdict.DONT_TOUCH
    elif points <= p.safe_max_points:
        verdict = Verdict.SAFE
    elif points <= p.review_max_points:
        verdict = Verdict.REVIEW
    else:
        verdict = Verdict.DONT_TOUCH

    rec.verdict, rec.confidence, rec.risk_points, rec.reasons = verdict, confidence, points, reasons
    return rec


def analyze(snapshot: Snapshot, policy: Policy) -> list[Recommendation]:
    recs = []
    for ev in snapshot.containers:
        req, lim, notes = size(ev, policy)
        recs.append(score(Recommendation(evidence=ev, requests=req, limits=lim, reasons=notes), policy))
    return sorted(recs, key=lambda r: (r.verdict.rank, r.key))
