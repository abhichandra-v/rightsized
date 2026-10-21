# Methodology

Every number Rightsized prints can be recomputed from `snapshot.json` plus the code in
`src/rightsized/`. This page documents the rules; the code is authoritative.

## 1. Evidence (`collect.py`)

Per container, over the window (default 7d), across **all historic pods** of the workload
(matched by pod-name regex, not just pods alive now), taking the **busiest replica**:

| Signal | Source |
|---|---|
| CPU p50/p95/p99/max/mean/stddev | `rate(container_cpu_usage_seconds_total[5m])` subqueried at 1m |
| Memory p50/p95/p99/max | `container_memory_working_set_bytes` |
| Throttle ratio | `increase(cfs_throttled_periods) / increase(cfs_periods)` |
| OOM events | `container_oom_events_total`, falling back to KSM `last_terminated_reason="OOMKilled"` |
| Restarts | `kube_pod_container_status_restarts_total` |
| Observed span | Earliest working-set sample in the window |
| Replicas, PDB, criticality | kubectl: `spec.replicas`, PDB selector match, `rightsized.io/criticality` label |

## 2. Sizing (`recommend.size`)

| | CPU | Memory |
|---|---|---|
| Basis | p95 | observed **peak** |
| Margin | +15% | +30% |
| Floor / step | 10m / 5m | 32Mi / 8Mi |
| Max cut per PR | none | 50% (a ratchet: the next PR continues with fresh evidence) |
| On failure signal | throttled ≥ 5%: request held, limit +50% | OOMKilled: request ≥ 125% of the limit that was hit |

The asymmetry is deliberate. Under-sized CPU means throttling, which slows the pod and
is caught by the verify step. Under-sized memory means an OOMKill, which takes the pod down.

Changes under 10% are dropped: churn isn't free.
Limits are only changed where they exist, and never set below the new request. Adding
limits is a policy decision, not a sizing one.

## 3. Risk score (`recommend.score`)

Points accumulate. **0–2 → safe, 3–5 → review, ≥6 → don't touch.** Some conditions block outright.

| Category | Condition | Points |
|---|---|---|
| Data | observed < 24h | **block** |
| Data | observed < 7d (weekly peak unseen) | +2 |
| Data | CPU CV > 0.5 (ignored below 50m mean) | +1 |
| Data | CPU peak > 3× p95 and CPU going down (ignored below 100m peak) | +1 |
| Data | memory peak > 2× p50 and memory going down | +1 |
| Failure | any OOM event | +3 (**block** if memory would drop) |
| Failure | throttle ≥ 25% and CPU would drop | **block** |
| Failure | throttle ≥ 5% | +2 |
| Failure | ≥ 3 restarts | +1 |
| Blast radius | single replica | +1 |
| Blast radius | no PDB | +1 |
| Blast radius | `criticality: critical` | +2 |

**Confidence** (shown, not used for the verdict) = window coverage × stability, where
coverage = observed / 7d (capped at 1) and stability = 1 / (1 + max(0, CV − 0.25)).

By default only `safe` goes into the PR. `review` and `don't touch` are listed in the PR body with reasons.

## 4. Savings (`savings.py`)

Three numbers, never merged into one:

1. **Requests reclaimed:** Σ (old − new) × replicas. The paper $ figure prices each core
   and GiB at half the node's hourly price divided by its allocatable. That is what most
   dashboards show.
2. **Nodes after bin-packing (simulated):** first-fit-decreasing over all pod replicas
   (containers of one pod packed together), against allocatable minus DaemonSet overhead.
3. **Nodes after the autoscaler (measured):** node count recorded by `capture` during the
   baseline and candidate runs on a real autoscaling cluster. Only this number is quoted
   as savings.

The gap between 1 and 3 is a finding in itself: a cut that frees 0.6 cores but leaves every
node with a pod on it saves $0.

## 5. Verification (`verify.py`)

Baseline and candidate each get N ≥ 3 runs of the same deterministic k6 script. Rightsized
compares **medians** and prints the min–max spread so a reader can judge noise.

| Guardrail | Default |
|---|---|
| p99 latency | ≤ baseline + 10% |
| Error rate | ≤ baseline + 0.5 pp |
| OOM events during candidate runs | ≤ baseline (no new OOMs) |
| Container restarts during candidate runs | ≤ baseline (catches liveness kills and crash loops) |
| Deployments not fully available | 0 |
| Max container throttle ratio | ≤ max(10%, baseline) |

Any failure → exit 1 → `make verify` restores the previous values and re-applies.

## 6. Head-to-head with stock VPA (`vpa.py`)

The VPA recommender runs in `updateMode: "Off"` during the same observation window. Its
`target` values are applied as-is, with limits scaled proportionally
(VPA's default `RequestsAndLimits`), and go through the same baseline/candidate/verify
loop. The VPA arm is also scored by Rightsized's risk model, so the comparison shows which
VPA changes the scorer would have held back.

## Known simplifications

- Pod-name regex matching can over-match workloads whose names prefix one another (`api` vs `api-gateway`).
- Pods outside the managed namespaces are counted at their current requests (DaemonSets excluded; they are the node pool's `daemonset_*` overhead).
- The p99 guardrail compares medians of p99s, not a pooled p99; with 3 runs the test has low power for small regressions.
