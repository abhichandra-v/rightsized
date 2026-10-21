# Cloud run: measured nodes and real dollars

kind proves the loop works. Only an autoscaling cluster on a real bill proves the money.
This runbook brings up a small EKS + Karpenter cluster, runs the same pipeline, records node
counts and billing, and **tears everything down**.

## Before you start

- Budget: write down a hard ceiling. Create an AWS Budget alert on it before running anything.
- Tag everything with `project=rightsized-run-<date>` and **activate it as a cost-allocation tag**
  in the Billing console. Tags only show up in Cost Explorer for usage after activation, with up to 24h lag.
- Record the instance price you use in `rightsized.yaml` (`node_pool.hourly_usd`) from the
  current AWS price list on the day of the run, with the date in the comment.

## 1. Cluster

Create with `eksctl` (Karpenter enabled, a small managed node group for system pods only).
Then add a Karpenter `NodePool` restricted to a single on-demand instance type, so node
count × price is unambiguous:

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: boutique
spec:
  template:
    metadata:
      labels: { rightsized.io/pool: boutique }
    spec:
      requirements:
        - { key: node.kubernetes.io/instance-type, operator: In, values: [m6i.large] }
        - { key: karpenter.sh/capacity-type, operator: In, values: [on-demand] }
      nodeClassRef: { group: karpenter.k8s.aws, kind: EC2NodeClass, name: default }
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 2m
```

Use `nodeSelector: rightsized.io/pool: boutique` on the Boutique workloads (add it as a
kustomize patch) so system pods don't distort the count.

## 2. Run

Same targets as kind, with real-time policy (delete the compressed `policy` block, or keep
it and say so in the write-up):

```bash
make monitoring vpa boutique forward
make observe collect analyze
make baseline candidate verify
make vpa-arm compare
```

Export `NODE_SELECTOR=rightsized.io/pool=boutique` so each run's `capture` counts only
Boutique nodes. Wait for Karpenter consolidation
(watch `kubectl get nodeclaims`) before each candidate run, so the node count reflects the new requests.

## 3. Evidence to keep

- `results/` (snapshots, k6 summaries, cluster captures, verify tables, PR bodies)
- `kubectl get nodeclaims -o wide` before and after each arm
- Cost Explorer export filtered by the project tag, grouped by usage type, daily:
  `aws ce get-cost-and-usage --time-period Start=...,End=... --granularity DAILY --metrics UnblendedCost --filter '{"Tags":{"Key":"project","Values":["rightsized-run-..."]}}' --group-by Type=DIMENSION,Key=USAGE_TYPE`

Note that the run's total bill is **not** the savings. Savings = node-hours removed ×
price, extrapolated to a month. The bill is there to show the price you used was real.

## 4. Teardown (same day)

```bash
kubectl delete nodepool boutique   # let Karpenter drain its nodes first
eksctl delete cluster --name <name> --wait
```

Then check for leftovers that keep billing: EBS volumes (Prometheus PVC), load balancers,
NAT gateways, Elastic IPs, CloudWatch log groups. Re-check Cost Explorer the next day.
