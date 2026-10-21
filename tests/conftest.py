from pathlib import Path

import pytest

from rightsized.models import ContainerEvidence, NodePool, Percentiles, Resources, Snapshot

MI = 2**20
DAY = 86400
ROOT = Path(__file__).resolve().parent.parent


def make_ev(**kw) -> ContainerEvidence:
    base = dict(
        namespace="shop", workload="web", kind="Deployment", container="app", replicas=3,
        requests=Resources(cpu=1.0, memory=1024 * MI), limits=Resources(cpu=2.0, memory=2048 * MI),
        cpu=Percentiles(p50=0.1, p95=0.2, p99=0.25, max=0.3, mean=0.12, stddev=0.03),
        memory=Percentiles(p50=200 * MI, p95=220 * MI, p99=230 * MI, max=240 * MI),
        throttle_ratio=0.0, oom_events=0, restarts=0, observed_seconds=8 * DAY,
        has_pdb=True, criticality="normal",
    )
    base.update(kw)
    return ContainerEvidence(**base)


@pytest.fixture
def pool() -> NodePool:
    return NodePool(instance_type="t", cpu_allocatable=2.0, memory_allocatable=8192 * MI, hourly_usd=0.1)


@pytest.fixture
def snapshot(pool) -> Snapshot:
    return Snapshot(cluster="test", collected_at="now", window="7d", containers=[make_ev()], node_pool=pool)
