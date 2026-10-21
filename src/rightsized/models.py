"""Data model. A Snapshot is the raw evidence; everything downstream is derived from it.

Snapshots are plain JSON so they can be committed next to results and re-analyzed
by anyone without cluster access.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path


@dataclass
class Percentiles:
    p50: float
    p95: float
    p99: float
    max: float
    mean: float = 0.0
    stddev: float = 0.0

    @property
    def cv(self) -> float:
        """Coefficient of variation; 0 when mean is 0."""
        return self.stddev / self.mean if self.mean > 0 else 0.0


@dataclass
class Resources:
    cpu: float | None = None  # cores
    memory: int | None = None  # bytes


@dataclass
class ContainerEvidence:
    namespace: str
    workload: str
    kind: str
    container: str
    replicas: int
    requests: Resources
    limits: Resources
    cpu: Percentiles  # cores
    memory: Percentiles  # bytes
    throttle_ratio: float  # throttled periods / total periods, 0..1
    oom_events: int
    restarts: int
    observed_seconds: float  # span between first and last sample in the window
    has_pdb: bool = False
    criticality: str = "normal"  # value of the rightsized.io/criticality label

    @property
    def key(self) -> str:
        return f"{self.namespace}/{self.workload}/{self.container}"


@dataclass
class NodePool:
    instance_type: str
    cpu_allocatable: float
    memory_allocatable: int
    hourly_usd: float
    min_nodes: int = 0
    # Requests consumed on every node by DaemonSets (CNI, kube-proxy, node-exporter...).
    daemonset_cpu: float = 0.0
    daemonset_memory: int = 0


@dataclass
class Snapshot:
    cluster: str
    collected_at: str
    window: str
    containers: list[ContainerEvidence]
    node_pool: NodePool | None = None
    # Requests from pods the tool does not manage (system pods, etc.); they still take node space.
    unmanaged_pods: list[Resources] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json() + "\n")

    @classmethod
    def load(cls, path: str | Path) -> "Snapshot":
        return cls.from_dict(json.loads(Path(path).read_text()))

    @classmethod
    def from_dict(cls, d: dict) -> "Snapshot":
        containers = [
            ContainerEvidence(
                **{
                    **c,
                    "requests": Resources(**c["requests"]),
                    "limits": Resources(**c["limits"]),
                    "cpu": Percentiles(**c["cpu"]),
                    "memory": Percentiles(**c["memory"]),
                }
            )
            for c in d["containers"]
        ]
        pool = NodePool(**d["node_pool"]) if d.get("node_pool") else None
        unmanaged = [Resources(**r) for r in d.get("unmanaged_pods", [])]
        return cls(
            cluster=d["cluster"],
            collected_at=d["collected_at"],
            window=d["window"],
            containers=containers,
            node_pool=pool,
            unmanaged_pods=unmanaged,
        )


class Verdict(str, Enum):
    SAFE = "safe"
    REVIEW = "review"
    DONT_TOUCH = "dont_touch"

    @property
    def rank(self) -> int:
        return {"safe": 0, "review": 1, "dont_touch": 2}[self.value]


@dataclass
class Recommendation:
    evidence: ContainerEvidence
    requests: Resources
    limits: Resources
    verdict: Verdict = Verdict.REVIEW
    confidence: float = 0.0  # 0..1
    risk_points: int = 0
    reasons: list[str] = field(default_factory=list)
    source: str = "rightsized"

    @property
    def key(self) -> str:
        return self.evidence.key

    @property
    def changed(self) -> bool:
        cur = self.evidence.requests
        return (cur.cpu, cur.memory) != (self.requests.cpu, self.requests.memory)
