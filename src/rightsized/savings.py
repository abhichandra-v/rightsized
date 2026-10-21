"""Three savings numbers, kept apart on purpose.

1. Requests reclaimed: what a recommender's dashboard shows. On paper only.
2. Nodes removed: requests only turn into money when the autoscaler can drain a node.
   We simulate first-fit-decreasing bin-packing here; the verify step records the
   node count the real autoscaler (Cluster Autoscaler / Karpenter) settled on.
3. Dollars per month at the node pool's instance price.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .models import NodePool, Recommendation, Resources, Snapshot

HOURS_PER_MONTH = 730


@dataclass
class SavingsReport:
    cpu_reclaimed: float  # cores, summed over replicas
    memory_reclaimed: int  # bytes, summed over replicas
    paper_monthly_usd: float  # requests reclaimed x per-unit price; what dashboards claim
    nodes_before: int
    nodes_after: int
    node_monthly_usd: float  # simulated nodes removed x instance price
    hourly_usd: float
    # Filled in from the cluster after the autoscaler has consolidated (verify step).
    measured_nodes_before: int | None = None
    measured_nodes_after: int | None = None

    @property
    def measured_monthly_usd(self) -> float | None:
        if self.measured_nodes_before is None or self.measured_nodes_after is None:
            return None
        removed = self.measured_nodes_before - self.measured_nodes_after
        return round(removed * self.hourly_usd * HOURS_PER_MONTH, 2)

    def as_dict(self) -> dict:
        d = {k: getattr(self, k) for k in self.__dataclass_fields__}
        d["measured_monthly_usd"] = self.measured_monthly_usd
        return d


def _pods(snapshot: Snapshot, overrides: dict[str, Resources]) -> list[Resources]:
    """One Resources entry per pod replica, summing the containers of each workload."""
    by_workload: dict[tuple[str, str], list] = defaultdict(lambda: [0.0, 0, 0])
    for ev in snapshot.containers:
        req = overrides.get(ev.key, ev.requests)
        acc = by_workload[(ev.namespace, ev.workload)]
        acc[0] += req.cpu or 0.0
        acc[1] += req.memory or 0
        acc[2] = max(acc[2], ev.replicas)
    pods = []
    for cpu, mem, replicas in by_workload.values():
        pods.extend(Resources(cpu=cpu, memory=mem) for _ in range(replicas))
    pods.extend(snapshot.unmanaged_pods)
    return pods


def binpack(pods: list[Resources], pool: NodePool) -> int:
    """First-fit-decreasing node count. A lower bound on what a real scheduler achieves."""
    cap_cpu = pool.cpu_allocatable - pool.daemonset_cpu
    cap_mem = pool.memory_allocatable - pool.daemonset_memory

    def weight(p: Resources) -> float:
        return max((p.cpu or 0) / cap_cpu, (p.memory or 0) / cap_mem)

    nodes: list[list[float]] = []  # [free_cpu, free_mem]
    for pod in sorted(pods, key=weight, reverse=True):
        cpu, mem = pod.cpu or 0.0, pod.memory or 0
        if cpu > cap_cpu or mem > cap_mem:
            raise ValueError(f"pod requesting {cpu} cores / {mem} B does not fit on {pool.instance_type}")
        for node in nodes:
            if node[0] >= cpu - 1e-9 and node[1] >= mem:
                node[0] -= cpu
                node[1] -= mem
                break
        else:
            nodes.append([cap_cpu - cpu, cap_mem - mem])
    return max(pool.min_nodes, len(nodes))


def compute(snapshot: Snapshot, applied: list[Recommendation]) -> SavingsReport:
    pool = snapshot.node_pool
    if pool is None:
        raise ValueError("snapshot has no node_pool; savings need instance shape and price")

    overrides = {r.key: r.requests for r in applied}
    cpu_rec = sum(((r.evidence.requests.cpu or 0) - (r.requests.cpu or 0)) * r.evidence.replicas for r in applied)
    mem_rec = sum(((r.evidence.requests.memory or 0) - (r.requests.memory or 0)) * r.evidence.replicas for r in applied)

    # Per-unit prices: split the node price evenly between its CPU and memory.
    per_core_hr = pool.hourly_usd * 0.5 / pool.cpu_allocatable
    per_byte_hr = pool.hourly_usd * 0.5 / pool.memory_allocatable
    paper = (cpu_rec * per_core_hr + mem_rec * per_byte_hr) * HOURS_PER_MONTH

    before = binpack(_pods(snapshot, {}), pool)
    after = binpack(_pods(snapshot, overrides), pool)
    return SavingsReport(
        cpu_reclaimed=round(cpu_rec, 3),
        memory_reclaimed=int(mem_rec),
        paper_monthly_usd=round(paper, 2),
        nodes_before=before,
        nodes_after=after,
        node_monthly_usd=round((before - after) * pool.hourly_usd * HOURS_PER_MONTH, 2),
        hourly_usd=pool.hourly_usd,
    )
