import pytest
from conftest import MI, make_ev

from rightsized.models import NodePool, Recommendation, Resources, Snapshot
from rightsized.savings import HOURS_PER_MONTH, binpack, compute


def test_binpack_counts_nodes_with_daemonset_overhead():
    pool = NodePool("t", cpu_allocatable=2.0, memory_allocatable=8192 * MI, hourly_usd=0.1, daemonset_cpu=0.5)
    pods = [Resources(cpu=0.5, memory=100 * MI) for _ in range(6)]  # 1.5 cores usable per node
    assert binpack(pods, pool) == 2


def test_binpack_respects_min_nodes_and_rejects_oversized_pods(pool):
    pool.min_nodes = 3
    assert binpack([Resources(cpu=0.1, memory=MI)], pool) == 3
    with pytest.raises(ValueError):
        binpack([Resources(cpu=4.0, memory=MI)], pool)


def test_reclaimed_requests_do_not_equal_removed_nodes(pool):
    # 3 replicas x 1 core on 2-core nodes = 2 nodes. Cutting to 0.8 cores reclaims 0.6 cores on
    # paper, but only two 0.8-core pods fit per node, so it still takes 2 nodes: zero dollars.
    ev = make_ev(requests=Resources(cpu=1.0, memory=MI), replicas=3)
    snap = Snapshot("t", "now", "7d", [ev], node_pool=pool)
    rec = Recommendation(evidence=ev, requests=Resources(cpu=0.8, memory=MI), limits=Resources())
    s = compute(snap, [rec])
    assert s.cpu_reclaimed == pytest.approx(0.6)
    assert s.paper_monthly_usd > 0
    assert (s.nodes_before, s.nodes_after) == (2, 2)
    assert s.node_monthly_usd == 0


def test_node_dollars_and_measured_override(pool):
    ev = make_ev(requests=Resources(cpu=1.0, memory=MI), replicas=4)
    snap = Snapshot("t", "now", "7d", [ev], node_pool=pool)
    rec = Recommendation(evidence=ev, requests=Resources(cpu=0.25, memory=MI), limits=Resources())
    s = compute(snap, [rec])
    assert (s.nodes_before, s.nodes_after) == (2, 1)
    assert s.node_monthly_usd == round(0.1 * HOURS_PER_MONTH, 2)
    assert s.measured_monthly_usd is None
    s.measured_nodes_before, s.measured_nodes_after = 3, 2
    assert s.measured_monthly_usd == round(0.1 * HOURS_PER_MONTH, 2)


def test_containers_of_one_pod_are_packed_together(pool):
    a = make_ev(container="a", requests=Resources(cpu=1.2, memory=MI), replicas=1)
    b = make_ev(container="b", requests=Resources(cpu=0.7, memory=MI), replicas=1)
    snap = Snapshot("t", "now", "7d", [a, b], node_pool=pool)
    assert compute(snap, []).nodes_before == 1  # one 1.9-core pod, not two pods
