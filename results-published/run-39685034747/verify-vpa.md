| Guardrail | Baseline | Candidate | Limit | Run spread (base vs cand) | Result |
|---|---|---|---|---|---|
| p99 latency (ms) | 32.9 | 208.6 | ≤ 36.2 | 32–48 vs 132–293 | ❌ FAIL |
| error rate | 0.00% | 0.00% | ≤ 0.50% | 0.00%–0.00% vs 0.00%–0.00% | ✅ pass |
| OOM events during run | 0 | 0 | ≤ 0 |  | ✅ pass |
| container restarts during run | 0 | 8 | ≤ 0 |  | ❌ FAIL |
| deployments not available | 0 | 0 | ≤ 0 |  | ✅ pass |
| max container throttle ratio | 3.65% | 99.89% | ≤ 10.00% | 3.4%–5.6% vs 99.9%–100.0% | ❌ FAIL |

**Verdict: FAIL: roll back**

Nodes (median across runs; only meaningful with an autoscaler): 4 → 4 ≈ $0.00/mo at m6i.large pricing
