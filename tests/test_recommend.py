from conftest import DAY, MI, make_ev

from rightsized.config import Policy
from rightsized.models import Percentiles, Recommendation, Resources, Verdict
from rightsized.recommend import score, size

P = Policy()


def rec_for(ev):
    req, lim, notes = size(ev, P)
    return score(Recommendation(evidence=ev, requests=req, limits=lim, reasons=notes), P)


def test_cpu_from_p95_with_margin_memory_from_peak_with_wider_margin():
    req, _, _ = size(make_ev(requests=Resources(cpu=1.0, memory=400 * MI)), P)
    assert req.cpu == 0.23  # 0.2 * 1.15
    assert req.memory == 312 * MI  # 240Mi * 1.30 = 312Mi, already on an 8Mi step


def test_memory_ratchet_caps_cut_per_pr():
    req, _, notes = size(make_ev(), P)  # 1Gi request, ~312Mi needed
    assert req.memory == 512 * MI
    assert any("capped" in n for n in notes)


def test_small_changes_are_left_alone():
    ev = make_ev(requests=Resources(cpu=0.24, memory=320 * MI))
    req, _, _ = size(ev, P)
    assert (req.cpu, req.memory) == (0.24, 320 * MI)


def test_oom_raises_memory_above_the_limit_that_was_hit():
    ev = make_ev(requests=Resources(cpu=1.0, memory=192 * MI), limits=Resources(cpu=1.0, memory=192 * MI),
                 memory=Percentiles(150 * MI, 180 * MI, 186 * MI, 191 * MI), oom_events=2)
    r = rec_for(ev)
    assert r.requests.memory >= 240 * MI
    assert r.limits.memory >= r.requests.memory
    assert r.verdict is not Verdict.SAFE


def test_throttled_cpu_is_held_and_limit_raised():
    ev = make_ev(requests=Resources(cpu=0.5, memory=512 * MI), limits=Resources(cpu=0.5, memory=512 * MI),
                 throttle_ratio=0.12)
    req, lim, _ = size(ev, P)
    assert req.cpu == 0.5
    assert lim.cpu == 0.75


def test_well_evidenced_replicated_workload_is_safe():
    r = rec_for(make_ev())
    assert r.verdict is Verdict.SAFE
    assert r.confidence > 0.9


def test_too_little_data_is_hard_blocked():
    r = rec_for(make_ev(observed_seconds=6 * 3600))
    assert r.verdict is Verdict.DONT_TOUCH


def test_partial_week_costs_points():
    assert rec_for(make_ev(observed_seconds=3 * DAY)).risk_points > rec_for(make_ev()).risk_points


def test_blast_radius_pushes_to_review():
    r = rec_for(make_ev(replicas=1, has_pdb=False, criticality="critical"))
    assert r.verdict in (Verdict.REVIEW, Verdict.DONT_TOUCH)
    assert any("single replica" in x for x in r.reasons)


def test_severe_throttling_blocks_a_cpu_cut():
    ev = make_ev(throttle_ratio=0.4)
    r = Recommendation(evidence=ev, requests=Resources(cpu=0.3, memory=512 * MI), limits=Resources())
    assert score(r, P).verdict is Verdict.DONT_TOUCH


def test_cpu_noise_on_idle_containers_is_ignored():
    idle = make_ev(cpu=Percentiles(0.005, 0.01, 0.02, 0.06, mean=0.008, stddev=0.01))
    assert not any("variance" in x or "bursty CPU" in x for x in rec_for(idle).reasons)
