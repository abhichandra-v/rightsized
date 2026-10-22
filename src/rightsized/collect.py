"""Build a Snapshot from a live cluster: kubectl for spec, Prometheus for usage.

Only read access is needed. Nothing here mutates the cluster.
"""

from __future__ import annotations

import json
import subprocess
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from .models import ContainerEvidence, NodePool, Percentiles, Resources, Snapshot
from .units import parse_cpu, parse_memory

CRITICALITY_LABEL = "rightsized.io/criticality"


def pod_regex(kind: str, name: str) -> str:
    """Match every historic pod of a workload, not just the ones alive now."""
    if kind == "Deployment":
        return f"{name}-[a-z0-9]+-[a-z0-9]{{5}}"
    if kind == "StatefulSet":
        return f"{name}-[0-9]+"
    return f"{name}-[a-z0-9]{{5}}"  # DaemonSet and friends


def queries(ns: str, pod_re: str, container: str, window: str) -> dict[str, str]:
    sel = f'namespace="{ns}",pod=~"{pod_re}",container="{container}"'
    cpu_rate = f"sum by (pod) (rate(container_cpu_usage_seconds_total{{{sel}}}[5m]))"
    mem = f"max by (pod) (container_memory_working_set_bytes{{{sel}}})"
    q: dict[str, str] = {}
    # Per-pod series, then max across pods: sizing must cover the busiest replica.
    for name, phi in (("p50", 0.5), ("p95", 0.95), ("p99", 0.99)):
        q[f"cpu_{name}"] = f"max(quantile_over_time({phi}, ({cpu_rate})[{window}:1m]))"
        q[f"mem_{name}"] = f"max(quantile_over_time({phi}, ({mem})[{window}:1m]))"
    q["cpu_max"] = f"max(max_over_time(({cpu_rate})[{window}:1m]))"
    q["cpu_mean"] = f"max(avg_over_time(({cpu_rate})[{window}:1m]))"
    q["cpu_stddev"] = f"max(stddev_over_time(({cpu_rate})[{window}:1m]))"
    q["mem_max"] = f"max(max_over_time(({mem})[{window}:1m]))"
    q["mem_mean"] = f"max(avg_over_time(({mem})[{window}:1m]))"
    q["throttle_ratio"] = (
        f"sum(increase(container_cpu_cfs_throttled_periods_total{{{sel}}}[{window}]))"
        f" / sum(increase(container_cpu_cfs_periods_total{{{sel}}}[{window}]))"
    )
    q["oom_events"] = (
        f"sum(increase(container_oom_events_total{{{sel}}}[{window}]))"
        f" or sum(max_over_time(kube_pod_container_status_last_terminated_reason"
        f'{{namespace="{ns}",pod=~"{pod_re}",container="{container}",reason="OOMKilled"}}[{window}]))'
    )
    q["restarts"] = (
        f'sum(increase(kube_pod_container_status_restarts_total{{namespace="{ns}",pod=~"{pod_re}",'
        f'container="{container}"}}[{window}]))'
    )
    q["first_sample"] = f"min(min_over_time(timestamp({mem})[{window}:5m]))"
    return q


def top_by_container(prom: "Prometheus", query: str, n: int = 3) -> dict[str, float]:
    """The n largest per-container values of a `by (namespace, pod, container)` query."""
    out = {}
    for r in prom.vector(f"topk({n}, {query})"):
        m = r["metric"]
        v = float(r["value"][1])
        if v == v and v > 0:
            out[f"{m.get('namespace')}/{m.get('pod')}/{m.get('container')}"] = round(v, 4)
    return out


class Prometheus:
    def __init__(self, url: str):
        self.url = url.rstrip("/")

    def vector(self, query: str) -> list[dict]:
        qs = urllib.parse.urlencode({"query": query})
        with urllib.request.urlopen(f"{self.url}/api/v1/query?{qs}", timeout=60) as r:
            body = json.load(r)
        if body.get("status") != "success":
            raise RuntimeError(f"prometheus error for {query!r}: {body}")
        return body["data"]["result"]

    def scalar(self, query: str) -> float:
        result = self.vector(query)
        if not result:
            return 0.0
        v = float(result[0]["value"][1])
        return 0.0 if v != v else v  # NaN -> 0 (e.g. 0/0 throttle ratio)


def kubectl_json(*args: str) -> dict:
    out = subprocess.run(["kubectl", *args, "-o", "json"], check=True, capture_output=True, text=True)
    return json.loads(out.stdout)


def _pdb_covers(pdbs: list[dict], ns: str, labels: dict) -> bool:
    for pdb in pdbs:
        if pdb["metadata"]["namespace"] != ns:
            continue
        match = pdb["spec"].get("selector", {}).get("matchLabels", {})
        if match and all(labels.get(k) == v for k, v in match.items()):
            return True
    return False


def unmanaged_pods(managed_namespaces: list[str]) -> list[Resources]:
    """Requests of running pods outside the managed namespaces; they still take node space.

    DaemonSet pods are skipped: the node pool's daemonset_cpu/daemonset_memory covers them.
    """
    out = []
    for pod in kubectl_json("get", "pods", "-A", "--field-selector=status.phase=Running")["items"]:
        if pod["metadata"]["namespace"] in managed_namespaces:
            continue
        if any(o.get("kind") == "DaemonSet" for o in pod["metadata"].get("ownerReferences", [])):
            continue
        cpu = mem = 0
        for c in pod["spec"]["containers"]:
            req = c.get("resources", {}).get("requests", {})
            cpu += parse_cpu(req.get("cpu")) or 0
            mem += parse_memory(req.get("memory")) or 0
        out.append(Resources(cpu=cpu, memory=mem))
    return out


def collect(prom: Prometheus, namespaces: list[str], window: str, cluster: str,
            node_pool: NodePool | None = None) -> Snapshot:
    now = datetime.now(timezone.utc)
    containers: list[ContainerEvidence] = []
    for ns in namespaces:
        pdbs = kubectl_json("get", "pdb", "-n", ns)["items"]
        for kind in ("Deployment", "StatefulSet"):
            for obj in kubectl_json("get", kind.lower(), "-n", ns)["items"]:
                name = obj["metadata"]["name"]
                tmpl = obj["spec"]["template"]
                labels = tmpl["metadata"].get("labels", {})
                crit = obj["metadata"].get("labels", {}).get(CRITICALITY_LABEL, "normal")
                for c in tmpl["spec"]["containers"]:
                    res = c.get("resources", {})
                    r = {k: prom.scalar(v) for k, v in queries(ns, pod_regex(kind, name), c["name"], window).items()}
                    first = r["first_sample"]
                    containers.append(ContainerEvidence(
                        namespace=ns, workload=name, kind=kind, container=c["name"],
                        replicas=obj["spec"].get("replicas", 1),
                        requests=Resources(parse_cpu(res.get("requests", {}).get("cpu")),
                                           parse_memory(res.get("requests", {}).get("memory"))),
                        limits=Resources(parse_cpu(res.get("limits", {}).get("cpu")),
                                         parse_memory(res.get("limits", {}).get("memory"))),
                        cpu=Percentiles(r["cpu_p50"], r["cpu_p95"], r["cpu_p99"], r["cpu_max"],
                                        r["cpu_mean"], r["cpu_stddev"]),
                        memory=Percentiles(r["mem_p50"], r["mem_p95"], r["mem_p99"], r["mem_max"], r["mem_mean"]),
                        throttle_ratio=r["throttle_ratio"],
                        oom_events=int(round(r["oom_events"])),
                        restarts=int(round(r["restarts"])),
                        observed_seconds=max(0.0, now.timestamp() - first) if first else 0.0,
                        has_pdb=_pdb_covers(pdbs, ns, labels),
                        criticality=crit,
                    ))
    return Snapshot(cluster=cluster, collected_at=now.isoformat(timespec="seconds"),
                    window=window, containers=containers, node_pool=node_pool,
                    unmanaged_pods=unmanaged_pods(namespaces))


def unavailable_deployments(namespaces: list[str]) -> list[str]:
    """Deployments with fewer available replicas than desired, e.g. stuck in CrashLoopBackOff."""
    out = []
    for ns in namespaces:
        for d in kubectl_json("get", "deployments", "-n", ns)["items"]:
            want = d["spec"].get("replicas", 1)
            if d.get("status", {}).get("availableReplicas", 0) < want:
                out.append(f"{ns}/{d['metadata']['name']}")
    return out


def node_count(selector: str = "") -> int:
    args = ["get", "nodes"] + (["-l", selector] if selector else [])
    return len(kubectl_json(*args)["items"])
