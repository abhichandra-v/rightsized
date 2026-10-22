## Rightsized: resource request changes

Evidence window: **92m**. Raw data: `results/snapshot.json`. This PR changes only `resources`; it does not touch the cluster directly.

### Savings

| | Value |
|---|---|
| Requests reclaimed (on paper) | 4.69 cores, 5.52 GiB (≈ $112.98/mo if every unit were billable) |
| Nodes after bin-packing (simulated) | 4 → 1, $210.24/mo |
| Nodes after autoscaler (measured) | _pending: `rightsized verify` reports node counts once the autoscaler has consolidated_ |

### Applied in this PR

| Workload / container | Verdict | CPU req | Mem req | CPU p50 / p95 / p99 / peak | Mem p99 / peak | Throttle | OOM | Restarts | Confidence |
|---|---|---|---|---|---|---|---|---|---|
| `adservice/server` ×1 | 🟢 safe | 1 → **23m** (-98%) | 256Mi → **105Mi** (-59%) | 6m / 22m / 26m / 27m | 91Mi / 96Mi | 0.1% | 0 | 0 | 0.65 |
| `cartservice/server` ×1 | 🟢 safe | 500m → **35m** (-93%) | 1Gi → **156Mi** (-85%) | 16m / 24m / 27m / 27m | 123Mi / 123Mi | 0.0% | 0 | 0 | 0.89 |
| `checkoutservice/server` ×1 | 🟡 review | 500m → **15m** (-97%) | 512Mi → **100Mi** (-80%) | 2m / 4m / 4m / 4m | 9Mi / 9Mi | 0.0% | 0 | 0 | 0.82 |
| `currencyservice/server` ×1 | 🟢 safe | 100m → **63m** (-37%) | 512Mi → **100Mi** (-80%) | 29m / 45m / 46m / 46m | 64Mi / 64Mi | 3.0% | 0 | 0 | 0.83 |
| `emailservice/server` ×1 | 🟢 safe | 250m → **15m** (-94%) | 512Mi → **100Mi** (-80%) | 2m / 3m / 3m / 3m | 43Mi / 43Mi | 0.0% | 0 | 0 | 0.98 |
| `frontend/server` ×2 | 🟢 safe | 500m → **63m** (-87%) | 512Mi → **100Mi** (-80%) | 29m / 53m / 56m / 59m | 14Mi / 15Mi | 0.0% | 0 | 0 | 0.79 |
| `paymentservice/server` ×1 | 🟡 review | 250m → **15m** (-94%) | 512Mi → **100Mi** (-80%) | 1m / 2m / 2m / 2m | 46Mi / 46Mi | 0.0% | 0 | 0 | 0.88 |
| `productcatalogservice/server` ×1 | 🟢 safe | 500m → **49m** (-90%) | 512Mi → **100Mi** (-80%) | 23m / 36m / 36m / 37m | 10Mi / 10Mi | 0.0% | 0 | 0 | 0.80 |
| `recommendationservice/server` ×1 | 🟢 safe | 500m → **35m** (-93%) | 1Gi → **100Mi** (-90%) | 14m / 22m / 23m / 23m | 42Mi / 42Mi | 0.0% | 0 | 0 | 0.84 |
| `redis-cart/redis` ×1 | 🟢 safe | 250m → **15m** (-94%) | 512Mi → **100Mi** (-80%) | 2m / 3m / 3m / 4m | 8Mi / 8Mi | 0.0% | 0 | 0 | 0.96 |
| `shippingservice/server` ×1 | 🟢 safe | 250m → **15m** (-94%) | 512Mi → **100Mi** (-80%) | 3m / 4m / 4m / 4m | 9Mi / 9Mi | 0.0% | 0 | 0 | 0.83 |

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
