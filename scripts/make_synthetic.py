"""Generate examples/synthetic-snapshot.json and synthetic-vpa.json.

SYNTHETIC DATA. These numbers are invented to exercise every code path (OOM, throttling,
short window, blast radius). They are not measurements and must never be quoted as results.
"""

import json
from pathlib import Path

MI = 2**20
DAY = 86400

# name, container, replicas, req(cpu, MiB), lim(cpu, MiB), cpu(p50,p95,p99,max,mean,sd),
# mem MiB(p50,p95,p99,max), throttle, oom, restarts, days observed, pdb, criticality
ROWS = [
    ("frontend", "server", 2, (0.5, 512), (1.0, 1024), (0.06, 0.14, 0.19, 0.31, 0.07, 0.03), (38, 44, 47, 52), 0.0, 0, 0, 7.5, True, "normal"),
    ("cartservice", "server", 1, (0.5, 1024), (1.0, 1024), (0.03, 0.08, 0.11, 0.18, 0.04, 0.02), (62, 70, 74, 81), 0.0, 0, 0, 7.5, False, "normal"),
    ("productcatalogservice", "server", 1, (0.5, 512), (1.0, 1024), (0.04, 0.09, 0.12, 0.16, 0.05, 0.02), (24, 27, 28, 30), 0.0, 0, 0, 7.5, False, "normal"),
    ("currencyservice", "server", 1, (0.1, 512), (0.1, 1024), (0.07, 0.10, 0.10, 0.10, 0.08, 0.02), (48, 55, 58, 63), 0.31, 0, 0, 7.5, False, "normal"),
    ("paymentservice", "server", 1, (0.25, 512), (0.5, 1024), (0.01, 0.02, 0.03, 0.05, 0.01, 0.01), (41, 45, 46, 49), 0.0, 0, 0, 7.5, False, "critical"),
    ("shippingservice", "server", 1, (0.25, 512), (0.5, 1024), (0.01, 0.02, 0.03, 0.04, 0.01, 0.005), (14, 16, 17, 18), 0.0, 0, 0, 7.5, False, "normal"),
    ("emailservice", "server", 1, (0.25, 512), (0.5, 1024), (0.01, 0.03, 0.04, 0.06, 0.015, 0.01), (52, 58, 60, 64), 0.0, 0, 0, 3.0, False, "normal"),
    ("checkoutservice", "server", 1, (0.5, 512), (1.0, 1024), (0.02, 0.05, 0.07, 0.09, 0.025, 0.01), (20, 23, 24, 26), 0.0, 0, 0, 7.5, True, "critical"),
    ("recommendationservice", "server", 1, (0.5, 1024), (1.0, 1024), (0.05, 0.12, 0.16, 0.22, 0.06, 0.03), (60, 66, 68, 72), 0.0, 0, 0, 7.5, False, "normal"),
    ("adservice", "server", 1, (1.0, 192), (1.0, 192), (0.04, 0.11, 0.18, 0.42, 0.05, 0.04), (150, 178, 186, 191), 0.0, 4, 4, 7.5, False, "normal"),
    ("redis-cart", "redis", 1, (0.25, 512), (0.5, 1024), (0.01, 0.02, 0.03, 0.12, 0.012, 0.012), (6, 9, 14, 21), 0.0, 0, 0, 7.5, False, "normal"),
]


def container(r):
    name, c, reps, req, lim, cpu, mem, thr, oom, rst, days, pdb, crit = r
    return {
        "namespace": "boutique", "workload": name, "kind": "Deployment", "container": c, "replicas": reps,
        "requests": {"cpu": req[0], "memory": req[1] * MI}, "limits": {"cpu": lim[0], "memory": lim[1] * MI},
        "cpu": dict(zip(("p50", "p95", "p99", "max", "mean", "stddev"), cpu)),
        "memory": {**dict(zip(("p50", "p95", "p99", "max"), (m * MI for m in mem))), "mean": mem[0] * MI, "stddev": 0.0},
        "throttle_ratio": thr, "oom_events": oom, "restarts": rst, "observed_seconds": days * DAY,
        "has_pdb": pdb, "criticality": crit,
    }


# Stock-VPA-style targets: VPA's recommender applies a 250Mi memory floor and sees
# throttled CPU as real usage, so it lowers currencyservice despite the throttling.
VPA = {
    "frontend": ("163m", "262144k"), "cartservice": ("93m", "262144k"),
    "productcatalogservice": ("109m", "262144k"), "currencyservice": ("93m", "262144k"),
    "paymentservice": ("25m", "262144k"), "shippingservice": ("25m", "262144k"),
    "emailservice": ("35m", "262144k"), "checkoutservice": ("63m", "262144k"),
    "recommendationservice": ("143m", "262144k"), "adservice": ("143m", "262144k"),
    "redis-cart": ("25m", "262144k"),
}

out = Path(__file__).resolve().parent.parent / "examples"
snap = {
    "cluster": "SYNTHETIC-fixture-not-a-measurement", "collected_at": "2026-01-01T00:00:00+00:00", "window": "7d",
    "containers": [container(r) for r in ROWS], "node_pool": None, "unmanaged_pods": [],
}
(out / "synthetic-snapshot.json").write_text(json.dumps(snap, indent=2) + "\n")
vpa = {"items": [{
    "metadata": {"name": n, "namespace": "boutique"},
    "spec": {"targetRef": {"kind": "Deployment", "name": n}},
    "status": {"recommendation": {"containerRecommendations": [
        {"containerName": "redis" if n == "redis-cart" else "server", "target": {"cpu": c, "memory": m}}]}},
} for n, (c, m) in VPA.items()]}
(out / "synthetic-vpa.json").write_text(json.dumps(vpa, indent=2) + "\n")
print("wrote synthetic fixtures to", out)
