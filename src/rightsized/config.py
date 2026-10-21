"""Policy and run configuration, loaded from rightsized.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ruamel.yaml import YAML

from .models import NodePool
from .units import parse_cpu, parse_memory


@dataclass
class Policy:
    # CPU is sized from a percentile; memory from the observed peak with a wider margin,
    # because the cost of being wrong is an OOMKill, not a slowdown.
    cpu_percentile: str = "p95"
    cpu_margin: float = 0.15
    memory_margin: float = 0.30
    cpu_floor: float = 0.010  # cores
    memory_floor: int = 32 * 2**20  # bytes
    cpu_step: float = 0.005
    memory_step: int = 8 * 2**20
    # Below this relative change we leave the container alone; churn has a cost too.
    min_change: float = 0.10
    # Memory comes down in steps of at most this fraction per PR (a ratchet); the next PR,
    # with fresh evidence, continues. CPU is not capped: undersized CPU throttles, it doesn't kill.
    max_memory_step_down: float = 0.50
    # Variance/burstiness on near-idle containers is noise, not risk.
    cpu_noise_floor: float = 0.05  # cores

    # Data confidence
    min_window_hours: float = 24.0
    full_window_days: float = 7.0  # a weekly peak needs at least one full week

    # Failure-signal thresholds
    throttle_warn: float = 0.05
    throttle_block: float = 0.25
    restart_warn: int = 3

    # Verdict cut-offs on accumulated risk points
    safe_max_points: int = 2
    review_max_points: int = 5

    # Which verdicts are written into the PR
    apply_verdicts: list[str] = field(default_factory=lambda: ["safe"])


@dataclass
class Target:
    """Where a container's resources live in Git."""

    workload: str  # namespace/name
    container: str
    file: str
    mode: str = "manifest"  # "manifest" | "helm"
    path: str = ""  # helm: dotted path to the resources block, e.g. frontend.resources


@dataclass
class Guardrails:
    p99_latency_increase_pct: float = 10.0
    error_rate_increase_pp: float = 0.5
    max_new_oom_events: int = 0
    max_new_restarts: int = 0  # liveness kills and crash loops, not just OOMs
    max_throttle_ratio: float = 0.10


@dataclass
class Config:
    prometheus_url: str = "http://localhost:9090"
    window: str = "7d"
    namespaces: list[str] = field(default_factory=lambda: ["default"])
    policy: Policy = field(default_factory=Policy)
    guardrails: Guardrails = field(default_factory=Guardrails)
    targets: list[Target] = field(default_factory=list)
    node_pool: NodePool | None = None

    def target_for(self, namespace: str, workload: str, container: str) -> Target | None:
        for t in self.targets:
            if t.workload == f"{namespace}/{workload}" and t.container == container:
                return t
        return None


def load_config(path: str | Path | None) -> Config:
    if path is None or not Path(path).exists():
        return Config()
    raw = YAML(typ="safe").load(Path(path).read_text()) or {}
    return Config(
        prometheus_url=raw.get("prometheus_url", Config.prometheus_url),
        window=raw.get("window", Config.window),
        namespaces=raw.get("namespaces", ["default"]),
        policy=Policy(**raw.get("policy", {})),
        guardrails=Guardrails(**raw.get("guardrails", {})),
        targets=[Target(**t) for t in raw.get("targets", [])],
        node_pool=_node_pool(raw.get("node_pool")),
    )


def _node_pool(raw: dict | None) -> NodePool | None:
    if not raw:
        return None
    return NodePool(
        instance_type=raw["instance_type"],
        cpu_allocatable=parse_cpu(raw["cpu_allocatable"]),
        memory_allocatable=parse_memory(raw["memory_allocatable"]),
        hourly_usd=float(raw["hourly_usd"]),
        min_nodes=int(raw.get("min_nodes", 0)),
        daemonset_cpu=parse_cpu(raw.get("daemonset_cpu", 0)),
        daemonset_memory=parse_memory(raw.get("daemonset_memory", 0)),
    )
