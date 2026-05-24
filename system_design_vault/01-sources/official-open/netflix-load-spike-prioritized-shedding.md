---
type: source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - https://sites.google.com/netflix.com/javaplatformnetflix/qconsf25
  - https://reinvent.awsevents.com/content/dam/reinvent/2024/slides/nfx/NFX301_How-Netflix-handles-sudden-load-spikes-in-the-cloud.pdf
related:
  - "[[aws-builders-library-resilience]]"
  - "[[autoscaling-capacity-and-admission-control]]"
  - "[[../../03-patterns/system-design/production-agent-studio-canon]]"
  - "[[../../04-agent-studio-implications/HLD - Agent Studio System Design]]"
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
source_status: official_or_open_public
verification_notes:
  - Netflix Java Platform reference page and AWS re:Invent slide deck were opened directly on 2026-05-18.
  - The Netflix TechBlog articles are referenced by the official pages/slides but were not used as direct-read evidence in this pass.
  - This note stores original synthesis only and does not copy slide text, diagrams, or long excerpts.
---

# Netflix Load Spike And Prioritized Shedding

## Direct-Read Scope

Direct-read pass over the official Netflix Java Platform reference page for the QCon SF 2025 service-level prioritized load-shedding talk and the AWS re:Invent 2024 `NFX301` slide deck, "How Netflix handles sudden load spikes in the cloud." This note covers load spikes, autoscaling limits, priority tagging, success/failure buffers, CPU and IO load signals, fallback/shift behavior, retries, and resilience testing.

## Canon Cross-Check

Promoted to `canon_ready` after cross-check against [[google-sre-reliability-practices]], [[aws-builders-library-resilience]], [[autoscaling-capacity-and-admission-control]], [[async-workflow-and-queue-reliability]], [[../../03-patterns/system-design/production-agent-studio-canon]], [[../../04-agent-studio-implications/HLD - Agent Studio System Design]], and [[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]].

The cross-check sets this boundary:

- SRE defines the user-visible reliability targets and when budget burn should freeze release.
- Autoscaling/capacity controls define worker scale, quota, admission classes, and resource envelopes.
- AWS Builders Library defines retry, timeout, idempotency, and dependency isolation mechanics.
- Async workflow and queue contracts define replay, redrive, leases, duplicate handling, and quarantine.
- Netflix load-shedding guidance defines overload-time prioritization: what to defer, shed, degrade, or protect when capacity is already constrained.

Netflix is therefore canon for Agent Studio's overload survival plane. A route is not spike-ready until it has criticality tags, lane-local saturation signals, success/failure buffers, shed/defer/degrade behavior, retry-after and jitter policy, protected critical surfaces, and load-spike drill evidence.

## Core Read

Netflix's load-spike materials sharpen a point that the AWS Builders Library note only implied: autoscaling is not fast enough or expressive enough to be the only overload control. CPU target tracking can indicate saturation, but once a service is fully saturated it cannot distinguish a small overload from a massive spike. Agent Studio therefore needs both proactive capacity posture and reactive admission/shedding controls.

The slides separate detection, startup time, and runtime availability. Faster metrics and faster startup reduce time to recovery, but overload still requires deciding which work is least important. For Agent Studio, that means the system should pre-classify work by product criticality instead of inventing priority during an incident. Realtime interruption, active user conversation, artifact save, source-rights decisions, and publish gates are not the same priority as embedding backfills, lecture scans, eval sweeps, or cache warming.

Prioritized load shedding requires shared criticality nomenclature. Netflix's source material uses tags such as tier, business domain, and lifecycle stage. Agent Studio should use route-level and work-item-level tags: user-visible critical, foreground, background, maintenance, best-effort, deprecated, private-source-sensitive, and publish-impacting. A scheduler cannot protect what the data model does not name.

Service-level shedding matters because not all overload enters through one gateway. Agent Studio has the same issue: browser/computer-use tools, model providers, vector search, ingestion workers, local file extraction, realtime audio, and eval runners can overload independently. The cockpit gateway can reject some requests, but each worker lane also needs local admission and shedding behavior.

CPU is not sufficient for IO-bound or provider-bound routes. A route can spend most of its time waiting on storage, vector search, provider APIs, network calls, or browser actions while CPU remains low. Agent Studio should support latency-target or queue-age signals as utilization proxies for those lanes, not only CPU, RAM, or process count.

Retries are part of shedding design, not a separate afterthought. If the system sheds load and every client immediately retries, the overload can return. Retries should be sparse, jittered, bounded, and attached to the priority class and user-facing surface. Background work can defer; interactive routes may need a short retry budget; side-effecting routes need idempotency or reviewer-mediated resume.

The testing lesson is direct: load-shedding policy is not real until it has been tested under synthetic load, production-like load, and regional/failover-style scenarios. Agent Studio can start smaller, but it still needs squeeze tests: force queue pressure, provider throttling, vector search latency, model cold starts, browser-tool stalls, and ingestion spikes, then prove critical routes survive.

## Agent Studio Design Implications

- Add priority tags before adding workers. Every route and queue item should declare criticality, lifecycle stage, user-visible surface, tenant/source sensitivity, and allowed degradation behavior.
- Separate autoscaling from shedding. Autoscaling asks for more capacity; shedding protects the current capacity while more capacity may or may not arrive.
- Use lane-local admission control: realtime voice, foreground conversation, retrieval/reranking, model inference, media generation, browser/computer-use, source ingestion, and evals each need their own shed/defer policy.
- Keep success and failure buffers explicit. Do not run foreground routes at the same saturation target as background work.
- Use latency/queue-age utilization for IO-bound lanes: vector search, provider APIs, browser tools, and storage writes can be overloaded while CPU looks normal.
- Prefer dropping or deferring low-priority work before degrading critical user-visible work.
- Treat writes, approvals, source-rights decisions, publishing, and cost/budget records as higher criticality than easily retryable reads or cache warmups.
- Couple retry policy to shedding policy: shed/defer decisions need retry-after hints, jitter, and max-attempt rules.
- Validate overload behavior with synthetic and production-like drills before treating a route as resilient.
- Add an `overload_release_gate` for user-visible and mutation-capable lanes so route promotion proves critical work survives source-ingestion spikes, eval sweeps, media jobs, provider throttling, and tool stalls.
- Keep overload decisions route-local as well as gateway-level. Browser/computer-use, vector search, provider inference, media generation, and extraction workers must be able to defer or reject work without waiting for a single front-door limiter.

## Datastore Objects To Strengthen

| Object | Strengthened requirement |
|---|---|
| `admission_class_record` | Include criticality tier, lifecycle stage, product surface, source sensitivity, and allowed degradation mode. |
| `capacity_saturation_signal` | Support CPU, queue age, request rate, provider latency, vector-search latency, browser-tool wait, cold-start, and first-token delay. |
| `admission_decision_record` | Record accept, defer, shed, degrade, retry-after, priority bucket, and user-visible status. |
| `load_shedding_decision` | Link overload signal, priority class, shed/defer choice, retry policy, success/failure buffer, and observed user impact. |
| `dependency_isolation_pool` | Track protected surfaces and queue/concurrency limits per worker lane or dependency. |
| `retry_budget_policy` | Bind retry count, jitter, backoff, and retry-after behavior to priority class and shed reason. |
| `fault_injection_result` | Add squeeze-test and load-spike drill evidence for the specific route/lane, not only generic dependency failure. |
| `degradation_policy` | Distinguish no-op, stale-source, background deferral, text-only, smaller model, human handoff, and safe refusal modes. |
| `overload_release_gate` | Promotion gate requiring criticality tags, saturation signals, success/failure buffers, shed/defer/degrade rules, retry-after policy, and load-spike drill evidence. |

## Canon Decision

Agent Studio should not rely on autoscaling alone for reliability. Every production route needs priority-aware admission and load-shedding policy before launch. The minimum contract is: criticality tags, lane-local saturation signals, success/failure buffers, defer/drop/degrade behavior, retry-after and jitter policy, protected critical surfaces, and a load-spike drill that proves low-priority work is shed before critical user work fails.
