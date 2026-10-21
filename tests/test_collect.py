from rightsized import collect


def test_pod_regex_matches_historic_pods_only_of_that_workload():
    import re
    rx = re.compile(collect.pod_regex("Deployment", "cartservice") + "$")
    assert rx.match("cartservice-7d4f9c8b6d-x2k9p")
    assert not rx.match("cartservice-db-0")


def test_unmanaged_pods_skips_managed_namespaces_and_daemonsets(monkeypatch):
    pods = {"items": [
        {"metadata": {"namespace": "boutique"}, "spec": {"containers": [{"resources": {"requests": {"cpu": "1"}}}]}},
        {"metadata": {"namespace": "kube-system", "ownerReferences": [{"kind": "DaemonSet"}]},
         "spec": {"containers": [{"resources": {"requests": {"cpu": "100m"}}}]}},
        {"metadata": {"namespace": "monitoring", "ownerReferences": [{"kind": "StatefulSet"}]},
         "spec": {"containers": [{"resources": {"requests": {"cpu": "200m", "memory": "1Gi"}}}, {}]}},
    ]}
    monkeypatch.setattr(collect, "kubectl_json", lambda *a: pods)
    out = collect.unmanaged_pods(["boutique"])
    assert [(r.cpu, r.memory) for r in out] == [(0.2, 2**30)]


def test_queries_cover_every_signal():
    q = collect.queries("boutique", "x-.*", "server", "7d")
    assert {"cpu_p95", "mem_max", "throttle_ratio", "oom_events", "restarts", "first_sample"} <= q.keys()
    assert all('container="server"' in v for v in q.values())
