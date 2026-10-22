# Results: kind-rightsized, collected 2026-10-22T02:56:58+00:00

```
runner: 4 vCPU, 15 GiB
Linux runnervmxehtw 7.0.0-1017-azure #17~24.04.1-Ubuntu SMP PREEMPT Thu Sep 24 18:46:57 UTC 2026 x86_64 x86_64 x86_64 GNU/Linux
kind v0.24.0 go1.22.6 linux/amd64
v3.16.2+g13654a5
k6 v0.54.0 (commit/baba871c8a, go1.23.1, linux/amd64)
inputs: day=10m observe=7 runs=3 peak_rps=25
2a8cc4fe0e8a82b751b557021dcf2087451573f7
```

## Verdicts

🟢 safe: 9 · 🟡 review: 2 · 🔴 don't touch: 0 

| Workload / container | Verdict | CPU req | Mem req | CPU p50 / p95 / p99 / peak | Mem p99 / peak | Throttle | OOM | Restarts | Confidence |
|---|---|---|---|---|---|---|---|---|---|
| `adservice/server` ×1 | 🟢 safe | 1 → **30m** (-97%) | 256Mi → **128Mi** (-50%) | 6m / 22m / 26m / 27m | 91Mi / 96Mi | 0.1% | 0 | 0 | 0.65 |
| `cartservice/server` ×1 | 🟢 safe | 500m → **30m** (-94%) | 1Gi → **512Mi** (-50%) | 16m / 24m / 27m / 27m | 123Mi / 123Mi | 0.0% | 0 | 0 | 0.89 |
| `currencyservice/server` ×1 | 🟢 safe | 100m → **55m** (-45%) | 512Mi → **256Mi** (-50%) | 29m / 45m / 46m / 46m | 64Mi / 64Mi | 3.0% | 0 | 0 | 0.83 |
| `emailservice/server` ×1 | 🟢 safe | 250m → **10m** (-96%) | 512Mi → **256Mi** (-50%) | 2m / 3m / 3m / 3m | 43Mi / 43Mi | 0.0% | 0 | 0 | 0.98 |
| `frontend/server` ×2 | 🟢 safe | 500m → **65m** (-87%) | 512Mi → **256Mi** (-50%) | 29m / 53m / 56m / 59m | 14Mi / 15Mi | 0.0% | 0 | 0 | 0.79 |
| `productcatalogservice/server` ×1 | 🟢 safe | 500m → **45m** (-91%) | 512Mi → **256Mi** (-50%) | 23m / 36m / 36m / 37m | 10Mi / 10Mi | 0.0% | 0 | 0 | 0.80 |
| `recommendationservice/server` ×1 | 🟢 safe | 500m → **25m** (-95%) | 1Gi → **512Mi** (-50%) | 14m / 22m / 23m / 23m | 42Mi / 42Mi | 0.0% | 0 | 0 | 0.84 |
| `redis-cart/redis` ×1 | 🟢 safe | 250m → **10m** (-96%) | 512Mi → **256Mi** (-50%) | 2m / 3m / 3m / 4m | 8Mi / 8Mi | 0.0% | 0 | 0 | 0.96 |
| `shippingservice/server` ×1 | 🟢 safe | 250m → **10m** (-96%) | 512Mi → **256Mi** (-50%) | 3m / 4m / 4m / 4m | 9Mi / 9Mi | 0.0% | 0 | 0 | 0.83 |
| `checkoutservice/server` ×1 | 🟡 review | 500m → **10m** (-98%) | 512Mi → **256Mi** (-50%) | 2m / 4m / 4m / 4m | 9Mi / 9Mi | 0.0% | 0 | 0 | 0.82 |
| `paymentservice/server` ×1 | 🟡 review | 250m → **10m** (-96%) | 512Mi → **256Mi** (-50%) | 1m / 2m / 2m / 2m | 46Mi / 46Mi | 0.0% | 0 | 0 | 0.88 | 

- `boutique/adservice/server`: 🟢 safe (2 pts): single replica: a bad change is an outage; no PodDisruptionBudget
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
| rightsized | 9 | 4.00 cores | 2.88 GiB | 4 → 2 | $140.16 | 29.0 → 31.3 | 0.00% → 0.00% | +0 | none | ✅ pass |
| stock VPA | 11 | 4.69 cores | 5.52 GiB | 4 → 1 | $210.24 | 29.0 → 188.0 | 0.00% → 0.00% | +8 | boutique/emailservice | ❌ p99 latency (ms), container restarts during run, deployments not available, max container throttle ratio |

Paper value of rightsized's reclaimed requests: $87.17/mo at m6i.large pricing. Node and dollar figures are bin-packing simulations: kind has a fixed node count and no autoscaler.

### Guardrails: rightsized

| Guardrail | Baseline | Candidate | Limit | Run spread (base vs cand) | Result |
|---|---|---|---|---|---|
| p99 latency (ms) | 29.0 | 31.3 | ≤ 31.8 | 28–41 vs 21–46 | ✅ pass |
| error rate | 0.00% | 0.00% | ≤ 0.50% | 0.00%–0.00% vs 0.00%–0.00% | ✅ pass |
| OOM events during run | 0 | 0 | ≤ 0 |  | ✅ pass |
| container restarts during run | 0 | 0 | ≤ 0 |  | ✅ pass |
| deployments not available | 0 | 0 | ≤ 0 |  | ✅ pass |
| max container throttle ratio | 2.91% | 2.76% | ≤ 10.00% | 2.6%–4.3% vs 2.5%–4.1% | ✅ pass |

**Verdict: PASS: keep the change**

### Guardrails: stock VPA

| Guardrail | Baseline | Candidate | Limit | Run spread (base vs cand) | Result |
|---|---|---|---|---|---|
| p99 latency (ms) | 29.0 | 188.0 | ≤ 31.8 | 28–41 vs 163–188 | ❌ FAIL |
| error rate | 0.00% | 0.00% | ≤ 0.50% | 0.00%–0.00% vs 0.00%–0.00% | ✅ pass |
| OOM events during run | 0 | 0 | ≤ 0 |  | ✅ pass |
| container restarts during run | 0 | 8 | ≤ 0 |  | ❌ FAIL |
| deployments not available | 0 | 1 | ≤ 0 | boutique/emailservice | ❌ FAIL |
| max container throttle ratio | 2.91% | 100.00% | ≤ 10.00% | 2.6%–4.3% vs 100.0%–100.0% | ❌ FAIL |

**Verdict: FAIL: roll back**

### Attribution: baseline

- run 1: throttled {'boutique/currencyservice-b47dcb68f-24kjn/server': 0.0291}; restarts -
- run 2: throttled {'boutique/currencyservice-b47dcb68f-24kjn/server': 0.0433}; restarts -
- run 3: throttled {'boutique/currencyservice-b47dcb68f-24kjn/server': 0.0264}; restarts -

### Attribution: rightsized

- run 1: throttled {'boutique/currencyservice-b47dcb68f-24kjn/server': 0.0227}; restarts -
- run 2: throttled {'boutique/currencyservice-b47dcb68f-24kjn/server': 0.0245}; restarts -
- run 3: throttled {'boutique/currencyservice-b47dcb68f-24kjn/server': 0.0405}; restarts -

### Attribution: stock VPA

- run 1: throttled {'boutique/adservice-866dd467d-8mpnh/server': 1.0, 'boutique/currencyservice-6d5c9659c6-x66mb/server': 0.2795, 'boutique/checkoutservice-6dbf74774-khxns/server': 0.1567}; restarts {'boutique/emailservice-74db7fbbdb-cjp9m/server': 4.093, 'boutique/adservice-866dd467d-8mpnh/server': 3.0698}
- run 2: throttled {'boutique/adservice-866dd467d-8mpnh/server': 1.0, 'boutique/emailservice-74db7fbbdb-cjp9m/server': 0.7627, 'boutique/currencyservice-6d5c9659c6-x66mb/server': 0.2162}; restarts {'boutique/emailservice-74db7fbbdb-cjp9m/server': 4.093, 'boutique/adservice-866dd467d-8mpnh/server': 4.093}
- run 3: throttled {'boutique/adservice-866dd467d-8mpnh/server': 1.0, 'boutique/emailservice-74db7fbbdb-cjp9m/server': 0.9721, 'boutique/currencyservice-6d5c9659c6-x66mb/server': 0.2005}; restarts {'boutique/emailservice-74db7fbbdb-cjp9m/server': 4.093, 'boutique/adservice-866dd467d-8mpnh/server': 2.0465}

## VPA changes rightsized's scorer would have held back

- `boutique/checkoutservice/server`: 🟡 review (3 pts): single replica: a bad change is an outage; labelled critical
- `boutique/paymentservice/server`: 🟡 review (4 pts): single replica: a bad change is an outage; no PodDisruptionBudget; labelled critical 

