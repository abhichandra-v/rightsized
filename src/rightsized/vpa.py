"""Stock VPA recommendations as a baseline for the head-to-head.

VPA runs in recommendation-only mode (updateMode: "Off"); we read status.recommendation
and apply its `target` exactly as VPA would, so the comparison is against stock VPA and not a
tuned version of it. Limits are scaled in proportion, matching VPA's default
controlledValues: RequestsAndLimits.
"""

from __future__ import annotations

from .config import Policy
from .models import Recommendation, Resources, Snapshot
from .recommend import score
from .units import parse_cpu, parse_memory


def targets_from_vpa_list(vpa_list: dict) -> dict[str, Resources]:
    """Map 'ns/workload/container' -> VPA target from `kubectl get vpa -A -o json`."""
    out: dict[str, Resources] = {}
    for vpa in vpa_list.get("items", []):
        ns = vpa["metadata"]["namespace"]
        workload = vpa["spec"]["targetRef"]["name"]
        recs = vpa.get("status", {}).get("recommendation", {}).get("containerRecommendations", [])
        for cr in recs:
            t = cr["target"]
            out[f"{ns}/{workload}/{cr['containerName']}"] = Resources(
                cpu=parse_cpu(t.get("cpu")), memory=parse_memory(t.get("memory"))
            )
    return out


def _scale(limit, old_req, new_req):
    if limit is None or not old_req:
        return limit
    return type(limit)(limit * new_req / old_req)


def recommendations(snapshot: Snapshot, vpa_list: dict, policy: Policy) -> list[Recommendation]:
    targets = targets_from_vpa_list(vpa_list)
    recs = []
    for ev in snapshot.containers:
        t = targets.get(ev.key)
        if t is None:
            continue
        lim = Resources(
            cpu=_scale(ev.limits.cpu, ev.requests.cpu, t.cpu),
            memory=_scale(ev.limits.memory, ev.requests.memory, t.memory),
        )
        # Scored for the report only; the VPA arm applies every target regardless of verdict.
        recs.append(score(Recommendation(evidence=ev, requests=t, limits=lim, source="vpa"), policy))
    return sorted(recs, key=lambda r: r.key)
