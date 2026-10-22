## Rightsized: resource request changes

Evidence window: **92m**. Raw data: `results/snapshot.json`. This PR changes only `resources`; it does not touch the cluster directly.

### Savings

| | Value |
|---|---|
| Requests reclaimed (on paper) | 4.00 cores, 2.88 GiB (≈ $87.17/mo if every unit were billable) |
| Nodes after bin-packing (simulated) | 4 → 2, $140.16/mo |
| Nodes after autoscaler (measured) | _pending: `rightsized verify` reports node counts once the autoscaler has consolidated_ |

### Applied in this PR

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

### Not applied (needs a human)

| Workload / container | Verdict | CPU req | Mem req | CPU p50 / p95 / p99 / peak | Mem p99 / peak | Throttle | OOM | Restarts | Confidence |
|---|---|---|---|---|---|---|---|---|---|
| `checkoutservice/server` ×1 | 🟡 review | 500m → **10m** (-98%) | 512Mi → **256Mi** (-50%) | 2m / 4m / 4m / 4m | 9Mi / 9Mi | 0.0% | 0 | 0 | 0.82 |
| `paymentservice/server` ×1 | 🟡 review | 250m → **10m** (-96%) | 512Mi → **256Mi** (-50%) | 1m / 2m / 2m / 2m | 46Mi / 46Mi | 0.0% | 0 | 0 | 0.88 |

### Why each verdict

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

### Merge checklist

- [ ] `rightsized verify` passed on the baseline vs candidate load test (p99, errors, OOM, throttling)
- [ ] Rollback plan: revert this PR; the previous values are in the diff
