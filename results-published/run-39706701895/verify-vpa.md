| Guardrail | Baseline | Candidate | Limit | Run spread (base vs cand) | Result |
|---|---|---|---|---|---|
| p99 latency (ms) | 29.0 | 188.0 | ≤ 31.8 | 28–41 vs 163–188 | ❌ FAIL |
| error rate | 0.00% | 0.00% | ≤ 0.50% | 0.00%–0.00% vs 0.00%–0.00% | ✅ pass |
| OOM events during run | 0 | 0 | ≤ 0 |  | ✅ pass |
| container restarts during run | 0 | 8 | ≤ 0 |  | ❌ FAIL |
| deployments not available | 0 | 1 | ≤ 0 | boutique/emailservice | ❌ FAIL |
| max container throttle ratio | 2.91% | 100.00% | ≤ 10.00% | 2.6%–4.3% vs 100.0%–100.0% | ❌ FAIL |

**Verdict: FAIL: roll back**

Nodes (median across runs; only meaningful with an autoscaler): 4 → 4 ≈ $0.00/mo at m6i.large pricing
