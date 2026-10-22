| Guardrail | Baseline | Candidate | Limit | Run spread (base vs cand) | Result |
|---|---|---|---|---|---|
| p99 latency (ms) | 29.0 | 31.3 | ≤ 31.8 | 28–41 vs 21–46 | ✅ pass |
| error rate | 0.00% | 0.00% | ≤ 0.50% | 0.00%–0.00% vs 0.00%–0.00% | ✅ pass |
| OOM events during run | 0 | 0 | ≤ 0 |  | ✅ pass |
| container restarts during run | 0 | 0 | ≤ 0 |  | ✅ pass |
| deployments not available | 0 | 0 | ≤ 0 |  | ✅ pass |
| max container throttle ratio | 2.91% | 2.76% | ≤ 10.00% | 2.6%–4.3% vs 2.5%–4.1% | ✅ pass |

**Verdict: PASS: keep the change**

Nodes (median across runs; only meaningful with an autoscaler): 4 → 4 ≈ $0.00/mo at m6i.large pricing
