## Rightsized: resource request changes

Evidence window: **92m**. Raw data: `results/snapshot.json`. This PR changes only `resources`; it does not touch the cluster directly.

### Savings

| | Value |
|---|---|
| Requests reclaimed (on paper) | 4.62 cores, 5.57 GiB (≈ $111.95/mo if every unit were billable) |
| Nodes after bin-packing (simulated) | 4 → 1, $210.24/mo |
| Nodes after autoscaler (measured) | _pending: `rightsized verify` reports node counts once the autoscaler has consolidated_ |

### Applied in this PR

| Workload / container | Verdict | CPU req | Mem req | CPU p50 / p95 / p99 / peak | Mem p99 / peak | Throttle | OOM | Restarts | Confidence |
|---|---|---|---|---|---|---|---|---|---|
| `adservice/server` ×1 | 🟢 safe | 1 → **23m** (-98%) | 256Mi → **105Mi** (-59%) | 7m / 24m / 32m / 32m | 88Mi / 88Mi | 0.0% | 0 | 0 | 0.67 |
| `cartservice/server` ×1 | 🟢 safe | 500m → **63m** (-87%) | 1Gi → **100Mi** (-90%) | 24m / 43m / 50m / 51m | 60Mi / 60Mi | 0.0% | 0 | 0 | 0.84 |
| `checkoutservice/server` ×1 | 🟡 review | 500m → **15m** (-97%) | 512Mi → **100Mi** (-80%) | 2m / 4m / 4m / 4m | 10Mi / 10Mi | 0.0% | 0 | 0 | 0.82 |
| `currencyservice/server` ×1 | 🟢 safe | 100m → **63m** (-37%) | 512Mi → **100Mi** (-80%) | 31m / 52m / 54m / 57m | 64Mi / 64Mi | 4.9% | 0 | 0 | 0.82 |
| `emailservice/server` ×1 | 🟢 safe | 250m → **15m** (-94%) | 512Mi → **100Mi** (-80%) | 2m / 3m / 4m / 4m | 42Mi / 43Mi | 0.2% | 0 | 0 | 0.92 |
| `frontend/server` ×2 | 🟢 safe | 500m → **78m** (-84%) | 512Mi → **100Mi** (-80%) | 34m / 59m / 62m / 66m | 14Mi / 14Mi | 0.0% | 0 | 0 | 0.79 |
| `paymentservice/server` ×1 | 🟡 review | 250m → **15m** (-94%) | 512Mi → **100Mi** (-80%) | 1m / 2m / 2m / 2m | 45Mi / 46Mi | 0.1% | 0 | 0 | 0.88 |
| `productcatalogservice/server` ×1 | 🟢 safe | 500m → **63m** (-87%) | 512Mi → **100Mi** (-80%) | 26m / 42m / 44m / 45m | 10Mi / 10Mi | 0.0% | 0 | 0 | 0.80 |
| `recommendationservice/server` ×1 | 🟢 safe | 500m → **35m** (-93%) | 1Gi → **100Mi** (-90%) | 16m / 27m / 28m / 29m | 42Mi / 42Mi | 0.0% | 0 | 0 | 0.83 |
| `redis-cart/redis` ×1 | 🟢 safe | 250m → **15m** (-94%) | 512Mi → **100Mi** (-80%) | 3m / 4m / 5m / 5m | 8Mi / 8Mi | 0.0% | 0 | 0 | 0.97 |
| `shippingservice/server` ×1 | 🟢 safe | 250m → **15m** (-94%) | 512Mi → **100Mi** (-80%) | 3m / 5m / 5m / 5m | 9Mi / 9Mi | 0.0% | 0 | 0 | 0.82 |

### Why each verdict

- `boutique/adservice/server`: 🟢 safe (2 pts): single replica: a bad change is an outage; no PodDisruptionBudget
- `boutique/cartservice/server`: 🟢 safe (2 pts): single replica: a bad change is an outage; no PodDisruptionBudget
- `boutique/checkoutservice/server`: 🟡 review (3 pts): single replica: a bad change is an outage; labelled critical
- `boutique/currencyservice/server`: 🟢 safe (2 pts): single replica: a bad change is an outage; no PodDisruptionBudget
- `boutique/emailservice/server`: 🟢 safe (2 pts): single replica: a bad change is an outage; no PodDisruptionBudget
- `boutique/frontend/server`: 🟢 safe (0 pts): no risk signals
- `boutique/paymentservice/server`: 🟡 review (4 pts): single replica: a bad change is an outage; no PodDisruptionBudget; labelled critical
- `boutique/productcatalogservice/server`: 🟢 safe (2 pts): single replica: a bad change is an outage; no PodDisruptionBudget
- `boutique/recommendationservice/server`: 🟢 safe (2 pts): single replica: a bad change is an outage; no PodDisruptionBudget
- `boutique/redis-cart/redis`: 🟢 safe (2 pts): single replica: a bad change is an outage; no PodDisruptionBudget
- `boutique/shippingservice/server`: 🟢 safe (2 pts): single replica: a bad change is an outage; no PodDisruptionBudget

### Merge checklist

- [ ] `rightsized verify` passed on the baseline vs candidate load test (p99, errors, OOM, throttling)
- [ ] Rollback plan: revert this PR; the previous values are in the diff
