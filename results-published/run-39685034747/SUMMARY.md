# Results: kind-rightsized, collected 2026-10-21T23:34:10+00:00

```
runner: 4 vCPU, 15 GiB
Linux runnervmxehtw 7.0.0-1017-azure #17~24.04.1-Ubuntu SMP PREEMPT Thu Sep 24 18:46:57 UTC 2026 x86_64 x86_64 x86_64 GNU/Linux
kind v0.24.0 go1.22.6 linux/amd64
v3.16.2+g13654a5
k6 v0.54.0 (commit/baba871c8a, go1.23.1, linux/amd64)
inputs: day=10m observe=7 runs=3 peak_rps=25
a2e7356c4f09a3823e0b05b52d8590707ec9c806
```

## Verdicts

🟢 safe: 9 · 🟡 review: 2 · 🔴 don't touch: 0 

| Workload / container | Verdict | CPU req | Mem req | CPU p50 / p95 / p99 / peak | Mem p99 / peak | Throttle | OOM | Restarts | Confidence |
|---|---|---|---|---|---|---|---|---|---|
| `adservice/server` ×1 | 🟢 safe | 1 → **30m** (-97%) | 256Mi → **128Mi** (-50%) | 7m / 24m / 32m / 32m | 88Mi / 88Mi | 0.0% | 0 | 0 | 0.67 |
| `cartservice/server` ×1 | 🟢 safe | 500m → **50m** (-90%) | 1Gi → **512Mi** (-50%) | 24m / 43m / 50m / 51m | 60Mi / 60Mi | 0.0% | 0 | 0 | 0.84 |
| `currencyservice/server` ×1 | 🟢 safe | 100m → **60m** (-40%) | 512Mi → **256Mi** (-50%) | 31m / 52m / 54m / 57m | 64Mi / 64Mi | 4.9% | 0 | 0 | 0.82 |
| `emailservice/server` ×1 | 🟢 safe | 250m → **10m** (-96%) | 512Mi → **256Mi** (-50%) | 2m / 3m / 4m / 4m | 42Mi / 43Mi | 0.2% | 0 | 0 | 0.92 |
| `frontend/server` ×2 | 🟢 safe | 500m → **70m** (-86%) | 512Mi → **256Mi** (-50%) | 34m / 59m / 62m / 66m | 14Mi / 14Mi | 0.0% | 0 | 0 | 0.79 |
| `productcatalogservice/server` ×1 | 🟢 safe | 500m → **50m** (-90%) | 512Mi → **256Mi** (-50%) | 26m / 42m / 44m / 45m | 10Mi / 10Mi | 0.0% | 0 | 0 | 0.80 |
| `recommendationservice/server` ×1 | 🟢 safe | 500m → **35m** (-93%) | 1Gi → **512Mi** (-50%) | 16m / 27m / 28m / 29m | 42Mi / 42Mi | 0.0% | 0 | 0 | 0.83 |
| `redis-cart/redis` ×1 | 🟢 safe | 250m → **10m** (-96%) | 512Mi → **256Mi** (-50%) | 3m / 4m / 5m / 5m | 8Mi / 8Mi | 0.0% | 0 | 0 | 0.97 |
| `shippingservice/server` ×1 | 🟢 safe | 250m → **10m** (-96%) | 512Mi → **256Mi** (-50%) | 3m / 5m / 5m / 5m | 9Mi / 9Mi | 0.0% | 0 | 0 | 0.82 |
| `checkoutservice/server` ×1 | 🟡 review | 500m → **10m** (-98%) | 512Mi → **256Mi** (-50%) | 2m / 4m / 4m / 4m | 10Mi / 10Mi | 0.0% | 0 | 0 | 0.82 |
| `paymentservice/server` ×1 | 🟡 review | 250m → **10m** (-96%) | 512Mi → **256Mi** (-50%) | 1m / 2m / 2m / 2m | 45Mi / 46Mi | 0.1% | 0 | 0 | 0.88 | 

- `boutique/adservice/server`: 🟢 safe (2 pts): memory step capped at -50% for this PR; single replica: a bad change is an outage; no PodDisruptionBudget
- `boutique/cartservice/server`: 🟢 safe (2 pts): memory step capped at -50% for this PR; single replica: a bad change is an outage; no PodDisruptionBudget
- `boutique/currencyservice/server`: 🟢 safe (2 pts): memory step capped at -50% for this PR; single replica: a bad change is an outage; no PodDisruptionBudget
- `boutique/emailservice/server`: 🟢 safe (2 pts): memory step capped at -50% for this PR; single replica: a bad change is an outage; no PodDisruptionBudget
- `boutique/frontend/server`: 🟢 safe (0 pts): memory step capped at -50% for this PR
- `boutique/productcatalogservice/server`: 🟢 safe (2 pts): memory step capped at -50% for this PR; single replica: a bad change is an outage; no PodDisruptionBudget
- `boutique/recommendationservice/server`: 🟢 safe (2 pts): memory step capped at -50% for this PR; single replica: a bad change is an outage; no PodDisruptionBudget
- `boutique/redis-cart/redis`: 🟢 safe (2 pts): memory step capped at -50% for this PR; single replica: a bad change is an outage; no PodDisruptionBudget
- `boutique/shippingservice/server`: 🟢 safe (2 pts): memory step capped at -50% for this PR; single replica: a bad change is an outage; no PodDisruptionBudget
- `boutique/checkoutservice/server`: 🟡 review (3 pts): memory step capped at -50% for this PR; single replica: a bad change is an outage; labelled critical
- `boutique/paymentservice/server`: 🟡 review (4 pts): memory step capped at -50% for this PR; single replica: a bad change is an outage; no PodDisruptionBudget; labelled critical 

## Savings and SLOs, per arm

| Arm | Containers changed | CPU reclaimed | Mem reclaimed | Nodes (bin-packed sim) | $/mo (sim) | p99 ms (median) | Errors | New restarts | Unavailable | Guardrails |
|---|---|---|---|---|---|---|---|---|---|---|
| rightsized | 9 | 3.96 cores | 2.88 GiB | 4 → 2 | $140.16 | 32.9 → 36.3 | 0.00% → 0.00% | +0 | none | ❌ p99 latency (ms) |
| stock VPA | 11 | 4.62 cores | 5.57 GiB | 4 → 1 | $210.24 | 32.9 → 208.6 | 0.00% → 0.00% | +8 | none | ❌ p99 latency (ms), container restarts during run, max container throttle ratio |

Paper value of rightsized's reclaimed requests: $86.26/mo at m6i.large pricing. Node and dollar figures are bin-packing simulations: kind has a fixed node count and no autoscaler.

### Guardrails: rightsized

| Guardrail | Baseline | Candidate | Limit | Run spread (base vs cand) | Result |
|---|---|---|---|---|---|
| p99 latency (ms) | 32.9 | 36.3 | ≤ 36.2 | 32–48 vs 35–37 | ❌ FAIL |
| error rate | 0.00% | 0.00% | ≤ 0.50% | 0.00%–0.00% vs 0.00%–0.00% | ✅ pass |
| OOM events during run | 0 | 0 | ≤ 0 |  | ✅ pass |
| container restarts during run | 0 | 0 | ≤ 0 |  | ✅ pass |
| deployments not available | 0 | 0 | ≤ 0 |  | ✅ pass |
| max container throttle ratio | 3.65% | 3.79% | ≤ 10.00% | 3.4%–5.6% vs 3.4%–3.8% | ✅ pass |

**Verdict: FAIL: roll back**

### Guardrails: stock VPA

| Guardrail | Baseline | Candidate | Limit | Run spread (base vs cand) | Result |
|---|---|---|---|---|---|
| p99 latency (ms) | 32.9 | 208.6 | ≤ 36.2 | 32–48 vs 132–293 | ❌ FAIL |
| error rate | 0.00% | 0.00% | ≤ 0.50% | 0.00%–0.00% vs 0.00%–0.00% | ✅ pass |
| OOM events during run | 0 | 0 | ≤ 0 |  | ✅ pass |
| container restarts during run | 0 | 8 | ≤ 0 |  | ❌ FAIL |
| deployments not available | 0 | 0 | ≤ 0 |  | ✅ pass |
| max container throttle ratio | 3.65% | 99.89% | ≤ 10.00% | 3.4%–5.6% vs 99.9%–100.0% | ❌ FAIL |

**Verdict: FAIL: roll back**

## VPA changes rightsized's scorer would have held back

- `boutique/checkoutservice/server`: 🟡 review (3 pts): single replica: a bad change is an outage; labelled critical
- `boutique/paymentservice/server`: 🟡 review (4 pts): single replica: a bad change is an outage; no PodDisruptionBudget; labelled critical 

