| Guardrail | Baseline | Candidate | Limit | Run spread (base vs cand) | Result |
|---|---|---|---|---|---|
| p99 latency (ms) | 32.9 | 36.3 | ≤ 36.2 | 32–48 vs 35–37 | ❌ FAIL |
| error rate | 0.00% | 0.00% | ≤ 0.50% | 0.00%–0.00% vs 0.00%–0.00% | ✅ pass |
| OOM events during run | 0 | 0 | ≤ 0 |  | ✅ pass |
| container restarts during run | 0 | 0 | ≤ 0 |  | ✅ pass |
| deployments not available | 0 | 0 | ≤ 0 |  | ✅ pass |
| max container throttle ratio | 3.65% | 3.79% | ≤ 10.00% | 3.4%–5.6% vs 3.4%–3.8% | ✅ pass |

**Verdict: FAIL: roll back**

Nodes (median across runs; only meaningful with an autoscaler): 4 → 4 ≈ $0.00/mo at m6i.large pricing
