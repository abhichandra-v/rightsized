import json

from rightsized.config import Guardrails
from rightsized.verify import RunMetrics, node_change, render, verify


def run(p99, err=0.001, oom=0, thr=0.0):
    return RunMetrics(p99_ms=p99, p95_ms=p99 * 0.6, error_rate=err, oom_events=oom, max_throttle_ratio=thr)


def test_pass_within_noise():
    checks = verify([run(200), run(210), run(205)], [run(212), run(215), run(208)], Guardrails())
    assert all(c.passed for c in checks)
    assert "PASS" in render(checks)


def test_latency_regression_fails():
    checks = verify([run(200)] * 3, [run(260)] * 3, Guardrails())
    assert not checks[0].passed
    assert "roll back" in render(checks)


def test_any_oom_fails():
    checks = verify([run(200)], [run(200, oom=1)], Guardrails())
    assert not next(c for c in checks if "OOM" in c.name).passed


def check(checks, name):
    return next(c for c in checks if name in c.name)


def test_throttling_above_guardrail_fails_unless_baseline_was_already_there():
    assert not check(verify([run(200, thr=0.02)], [run(200, thr=0.2)], Guardrails()), "throttle").passed
    assert check(verify([run(200, thr=0.3)], [run(200, thr=0.3)], Guardrails()), "throttle").passed


def test_crash_loop_fails_even_with_clean_http():
    bad = run(200)
    bad.restarts, bad.unavailable = 9, ["boutique/adservice"]
    checks = verify([run(200)], [bad], Guardrails())
    assert not check(checks, "restarts").passed
    assert not check(checks, "not available").passed
    assert "boutique/adservice" in render(checks)


def test_reads_both_k6_summary_formats(tmp_path):
    handle = {"metrics": {"http_req_duration": {"values": {"p(99)": 250.0, "p(95)": 120.0}},
                          "http_req_failed": {"values": {"rate": 0.01}}}}
    export = {"metrics": {"http_req_duration": {"p(99)": 250.0, "p(95)": 120.0},
                          "http_req_failed": {"value": 0.01}}}
    cluster = tmp_path / "c.json"
    cluster.write_text(json.dumps({"oom_events": 1, "max_throttle_ratio": 0.05, "nodes": 3, "restarts": 2,
                                   "unavailable_deployments": ["ns/x"]}))
    for i, doc in enumerate((handle, export)):
        f = tmp_path / f"s{i}.json"
        f.write_text(json.dumps(doc))
        m = RunMetrics.from_files(f, cluster)
        assert (m.p99_ms, m.error_rate, m.oom_events, m.nodes, m.restarts, m.unavailable) == \
            (250.0, 0.01, 1, 3, 2, ["ns/x"])


def test_node_change_needs_every_run():
    a, b = run(200), run(200)
    assert node_change([a], [b]) is None
    a.nodes, b.nodes = 4, 3
    assert node_change([a], [b]) == (4, 3)


def test_failures_already_in_the_baseline_are_not_blamed_on_the_change():
    base, cand = run(200, oom=2), run(200, oom=2)
    base.restarts = cand.restarts = 2
    checks = verify([base], [cand], Guardrails())
    assert check(checks, "OOM").passed and check(checks, "restarts").passed
    cand.restarts = 3
    assert not check(verify([base], [cand], Guardrails()), "restarts").passed
