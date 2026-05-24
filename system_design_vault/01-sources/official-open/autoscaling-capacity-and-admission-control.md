---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/
  - https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/
  - https://kubernetes.io/docs/concepts/policy/resource-quotas/
  - https://kubernetes.io/docs/concepts/policy/limit-range/
  - https://kubernetes.io/docs/concepts/cluster-administration/flow-control/
  - https://docs.ray.io/en/latest/serve/autoscaling-guide.html
  - https://keda.sh/docs/2.17/concepts/scaling-deployments/
  - https://keda.sh/docs/latest/concepts/scaling-deployments/
source_status: official_public
verification_notes:
  - Kubernetes current docs opened directly on 2026-05-18; docs version selector showed v1.36.
  - Ray Serve autoscaling docs opened directly on 2026-05-18; page showed Ray 2.55.1.
  - KEDA scaling deployments docs opened directly on 2026-05-18; the latest URL redirected to v2.19, while the older v2.17 page remains version-pinned historical evidence.
  - This note stores original synthesis only and does not copy source text or examples.
---

# Autoscaling Capacity And Admission Control

## Direct-Read Scope

Direct-read pass over official Kubernetes Horizontal Pod Autoscaling, pod resource management, ResourceQuota, LimitRange, and API Priority and Fairness docs, plus official Ray Serve autoscaling and KEDA event-driven scaling docs.

This note fills the control-plane gap between Agent Studio's queue contracts and serving profiles. Queues decide what work waits; autoscaling and admission controls decide whether work can start, how many workers can exist, what each worker is allowed to consume, and which traffic is protected during overload.

## Canon Cross-Check

Promoted to `canon_ready` after cross-check against [[google-sre-reliability-practices]], [[netflix-load-spike-prioritized-shedding]], [[aws-builders-library-resilience]], [[async-workflow-and-queue-reliability]], [[kserve-model-serving-rollouts]], [[ray-serve-llm-production-serving]], [[../../03-patterns/system-design/production-agent-studio-canon]], [[../../04-agent-studio-implications/HLD - Agent Studio System Design]], and [[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]].

The cross-check sets this boundary:

- SRE defines user-visible reliability targets and budget-driven release control.
- Netflix defines what survives once a spike or overload is already happening.
- Builders Library defines timeout, retry, idempotency, and isolation behavior for dependencies under pressure.
- Workflow/queue notes define whether scaled workers can safely replay, retry, redrive, and preserve ordering.
- Serving-runtime notes define runtime-specific scaling surfaces such as request pressure, per-replica concurrency, canary rollout, model serving metrics, and cold-start evidence.

Autoscaling and admission control are therefore canon for Agent Studio's capacity contract. A route is not production-ready until it declares scaling target, resource envelope, quota boundary, admission class, capacity signal, scale-decision telemetry, and overload interaction with queue/workflow/idempotency contracts.

## Core Read

Kubernetes HPA is a feedback controller. It periodically compares observed metrics against targets and adjusts desired replica count. The core formula is proportional: current replicas multiplied by current metric over desired metric, with tolerance and stabilization behavior to prevent excessive oscillation. This is useful but limited: it reacts after metrics exist, it needs valid resource requests for utilization-based scaling, and it can lag behind sudden demand.

Kubernetes resource requests and limits separate scheduling from enforcement. Requests tell the scheduler how much capacity to reserve. Limits tell the runtime/kernel how much a container can consume. CPU overuse is throttled; memory overuse can become an OOM kill. For Agent Studio, that means "the worker scaled" is not enough evidence. The worker needs right-sized requests, realistic limits, and OOM/throttle telemetry.

ResourceQuota and LimitRange make capacity a namespace or tenant policy. Quotas cap aggregate object or resource consumption. LimitRanges constrain per-object requests, limits, ratios, and defaults at admission time. These are not only platform concerns; they are product controls for multi-route Agent Studio workloads so backfills, media generation, or eval sweeps cannot consume all shared capacity.

Kubernetes API Priority and Fairness adds overload isolation for the control plane. It classifies requests into flows and priority levels, applies concurrency limits, and uses fair queuing so one noisy client/controller does not starve leader election, controllers, or other flows. The product-level analogy is direct: Agent Studio needs admission classes for realtime review, foreground conversation, source ingestion, eval backfill, media generation, and maintenance.

Ray Serve autoscaling is closer to model-serving behavior. It scales deployments based on incoming traffic and queue/ongoing request pressure. Its knobs are product-facing: min replicas for cold-start tolerance, max replicas for cost/capacity ceiling, target ongoing requests for latency/throughput, and max ongoing requests for per-replica admission. This maps cleanly to LLM routes where concurrency, queue time, first-token latency, and memory pressure are more useful than CPU alone.

KEDA connects event sources to Kubernetes scaling. It can activate workloads from zero and feed event-source metrics into HPA while workers pull from queues/topics. This is useful for ingestion, embedding refresh, eval judging, publishing, and cleanup lanes. The key boundary is that event-driven scale does not replace handler correctness: ordering, retries, dead letters, checkpointing, and idempotency still belong to the queue/workflow contract.

## Agent Studio Design Implications

- Use autoscaling only after defining workload class, metric source, target, min replicas, max replicas, stabilization/cooldown behavior, and cost ceiling.
- Keep separate scaling policies for realtime voice, interactive studio chat, source extraction, embedding/indexing, eval judging, media generation, publishing, and maintenance.
- For model-serving routes, scale on request pressure, queue time, TTFT/TPOT, GPU/KV-cache pressure, and error rate; CPU alone is usually too indirect.
- Record resource requests and limits for every worker class. A worker without requests cannot support reliable utilization-based scaling or scheduling guarantees.
- Treat OOM kills, CPU throttling, pod evictions, queue wait, scale-up latency, and cold starts as release evidence, not incidental logs.
- Use quotas and limit ranges to prevent one route, tenant, corpus, or backfill from exhausting shared compute, memory, storage, or object count.
- Add admission classes before production: critical user-visible work, normal foreground work, background freshness work, best-effort research/backfill, and maintenance.
- Admission control should reject, defer, or degrade work before the system collapses. A visible "deferred due to capacity" state is better than hidden timeout cascades.
- Event-driven scale-to-zero is suitable for low-priority or bursty background lanes, but not for latency-sensitive realtime routes unless cold-start cost is acceptable.
- Scaling signals must link back to queue contracts and workflow records: scaling out workers should not violate per-key ordering, provider quotas, side-effect idempotency, or source rights gates.
- Add a `capacity_release_gate` before promoting any serving or worker lane. The gate should prove autoscaling policy, resource requests/limits, quota boundary, admission class, saturation signal, scale-decision telemetry, and queue/workflow compatibility.
- Version-pin autoscaler behavior. Kubernetes, Ray Serve, and KEDA defaults can change across releases, so route evidence should record the platform/runtime version that produced each capacity decision.

## Datastore Objects To Add

| Object | Purpose |
|---|---|
| `autoscaling_policy_record` | Workload scaling policy with metric source, target, min/max replicas, stabilization/cooldown behavior, scale-to-zero allowance, and owner. |
| `resource_request_limit_profile` | CPU, memory, GPU, storage, and ephemeral-resource requests/limits for one worker or serving class. |
| `admission_class_record` | Priority class for work admission: user-visible critical, foreground, background, best-effort, maintenance, or blocked. |
| `capacity_quota_record` | Route, tenant, namespace, corpus, or workload quota for compute, memory, storage, object count, provider calls, or queue depth. |
| `scale_decision_record` | Observed metric, desired replicas, current replicas, decision, stabilization reason, and linked workload state. |
| `capacity_saturation_signal` | OOM kills, throttling, evictions, queue age, cold starts, rejected work, or over-quota attempts by surface. |
| `admission_decision_record` | Accept/defer/reject/degrade decision with class, capacity signal, user impact, retry-after, and audit trace. |
| `capacity_release_gate` | Promotion gate proving autoscaling, resource envelope, quotas, admission classes, saturation signals, scale-decision telemetry, and queue/workflow compatibility. |

## Canon Decision

Agent Studio should treat capacity as a first-class product contract. A route is not production-ready merely because it has a queue and a worker. It needs workload-specific scaling targets, resource requests/limits, quota boundaries, admission classes, overload behavior, scale-decision telemetry, and a capacity release gate tied back to queue/workflow safety. For LLM and media routes, application-level pressure metrics should lead; CPU and memory are supporting signals, not the whole control loop.
