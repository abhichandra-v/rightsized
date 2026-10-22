| Arm | Containers changed | CPU reclaimed | Mem reclaimed | Nodes (sim) | $/mo (sim) | Changes our scorer would hold |
|---|---|---|---|---|---|---|
| rightsized | 9 | 3.96 cores | 2.88 GiB | 4 → 2 | $140.16 | 0 |
| stock VPA | 11 | 4.62 cores | 5.57 GiB | 4 → 1 | $210.24 | 2 |

VPA changes the risk scorer would not auto-apply:
- `boutique/checkoutservice/server`: 🟡 review (3 pts): single replica: a bad change is an outage; labelled critical
- `boutique/paymentservice/server`: 🟡 review (4 pts): single replica: a bad change is an outage; no PodDisruptionBudget; labelled critical

Simulated only. Regressions come from `rightsized verify` on each arm's load-test runs.
