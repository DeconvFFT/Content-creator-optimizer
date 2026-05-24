---
type: source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/machine-learning-lens.html
  - https://docs.cloud.google.com/architecture/framework/perspectives/ai-ml/reliability
  - https://www.uber.com/ie/en/blog/michelangelo-machine-learning-platform/
  - https://docs.metaflow.org/introduction/what-is-metaflow
  - https://sre.google/books/
  - [[google-sre-reliability-practices]]
  - [[aws-builders-library-resilience]]
  - [[netflix-load-spike-prioritized-shedding]]
source_status: official_public
verification_notes:
  - AWS ML Lens opened directly; publication date shown as 2025-11-19.
  - Google Cloud AI/ML reliability page opened directly.
  - Metaflow docs opened directly.
  - Google SRE books page opened directly.
  - Uber Michelangelo official blog was verified through search-result snippet after direct page fetch did not return content in this tool.
---

# Scale And Reliability Sources

## Direct-Read Scope

Read directly or source-verified from official/open AWS, Google Cloud, Google SRE, Metaflow, and Uber engineering sources on 2026-05-18. This note stores original synthesis only. It does not copy source text or long excerpts.

## Core Reliability Read

AWS ML Lens frames ML as a production lifecycle with continuous monitoring because data and model behavior change after launch. Google Cloud's AI/ML reliability guidance makes graceful degradation, fault isolation, redundancy, proactive monitoring, model/data drift, SLOs, and error-budget burn part of AI/ML architecture. Google SRE provides the broader reliability discipline: product quality is governed by user-visible SLIs/SLOs, error budgets, burn-rate alerting, incident learning, postmortems, toil control, and systematic operational practice.

AWS Builders Library resilience guidance adds the distributed-systems mechanics under those controls: timeouts must bound resource consumption, retries need budgets and idempotency, backoff needs jitter, existing safe work should survive control-plane impairment, and slow dependencies need isolated concurrency pools.

Netflix load-spike material adds the overload-control layer: autoscaling can arrive too late or lose signal under extreme spikes, so route surfaces need criticality tags, service-level shedding, success/failure buffers, latency-based IO limiters, retry-after behavior, and load-spike drills.

Metaflow contributes the workflow reliability layer: flows, experiments, artifacts, environment dependencies, local testing, and production orchestration must remain traceable. Uber Michelangelo contributes the platform-shape lesson: scalable ML work needs a unified lifecycle for data, training, evaluation, deployment, prediction, and monitoring rather than one-off notebooks or disconnected services.

For Agent Studio, reliability is not only uptime. It includes source freshness, retrieval quality, route quality, tool safety, inference latency, voice interruption behavior, artifact lineage, evaluator stability, and graceful fallback when a provider or source route fails.

## Reliability Control Matrix

| Control | Source signal | Agent Studio implication |
|---|---|---|
| User-visible SLOs | Google Cloud reliability and Google SRE emphasize reliability targets tied to user experience. | Define SLOs for route success, grounded answer quality, TTFT/TPOT, voice turn latency, artifact save durability, retrieval coverage, and ingestion freshness. |
| Error budgets and burn alerts | Google Cloud points to SRE-style SLOs and error-budget burn as reliability indicators. | Store `error_budget_record` and trigger route freezes or rollback reviews when quality, latency, or freshness burns too fast. |
| Graceful degradation | Google Cloud recommends fallback paths, circuit breakers, redundancy, and cached/simpler alternatives. | Every provider route needs fallback mode: cached answer, smaller model, text-only, no-voice mode, retrieval-only answer, human handoff, or delayed background job. |
| Continuous monitoring | AWS and Google both emphasize monitoring data/model behavior and system health. | Monitor model outputs, retrieval drift, source freshness, data drift, provider latency, GPU/queue pressure, and guardrail outcomes as separate signals. |
| Incident learning | Google reliability guidance includes postmortem practice. | Convert incidents into eval cases, route-change proposals, blocked-release checks, and source-ledger updates. |
| Workflow reproducibility | Metaflow tracks flows, experiments, and artifacts while supporting local test and production orchestration. | Ingestion and agent runs need flow/run versions, parameters, dependency snapshots, artifacts, and replay/compare pointers. |
| Unified platform lifecycle | Uber Michelangelo source signal covers data management, training, evaluation, deployment, prediction, and monitoring. | Agent Studio should manage source ingestion, evals, route releases, serving, feedback, and monitoring as one lifecycle. |
| Prioritized overload control | Netflix load-spike materials separate autoscaling, priority tagging, success/failure buffers, CPU and latency-based shedding, and resilience testing. | Critical user-visible routes need priority-aware admission and lane-local shedding before background jobs, evals, ingestion, or cache work can consume shared capacity. |
| Toil reduction | Google SRE treats recurring manual operational work as design debt. | Repeated reviewer fixes, source cleanup, routing mistakes, and alert interrupts should create engineering backlog, not permanent manual process. |

## Agent Studio Design Implications

- Add `slo_record`: surface, target, measurement window, user impact, owner, and release-blocking behavior.
- Add `sli_record`: user-visible behavior, collection point, aggregation/window, distribution buckets, and proxy caveat.
- Add `error_budget_record`: SLO, consumed budget, burn rate, triggering events, freeze/rollback policy, and reviewer.
- Add SLO burn alert policy with page/ticket/log classification and actionability tests.
- Add `degradation_policy`: failure class, circuit breaker threshold, fallback route, user-visible mode, and recovery condition.
- Add `backpressure_event`: queue depth, concurrency, provider throttle, dropped/deferred work, and user-visible impact.
- Add timeout/retry/backoff/jitter/idempotency policies per dependency and route surface.
- Add dependency-isolation pools and load-shedding decisions so one slow provider or tool cannot starve unrelated work.
- Add route/work criticality tags and success/failure buffers so overload drops or defers low-priority work before critical user actions fail.
- Add static-stability reviews for route releases: what keeps working when session creation, provider discovery, source refresh, or worker launch is impaired?
- Add `reliability_signal`: latency, error rate, drift, freshness, eval regression, voice timing, retrieval coverage, and guardrail signal with route scope.
- Add `postmortem_record`: incident, timeline, contributing factors, corrective actions, linked eval cases, and route/source changes.
- Add `toil_record` and `reliability_release_gate` so repeated manual operations and exhausted error budgets block risky route changes.
- Add `workflow_reproducibility_record`: flow version, dependency snapshot, parameters, artifact refs, local/prod environment, and replay eligibility.
- Add `platform_lifecycle_record`: source/data, training/adaptation, evaluation, deployment, serving, prediction, feedback, and monitoring stage state.
- Treat source ledgers, artifacts, traces, and eval cases as reliability controls, not documentation extras.
- Background ingestion should run through scheduled or event-triggered durable workflows with retry, resume, comparison, and stale-source alarms.

## Canon Decision

Agent Studio should promote a route only when reliability evidence exists for both product behavior and operational behavior. The minimum release bundle is: SLIs, SLOs, error-budget policy, burn-alert policy, degradation policy, observability signals, reproducible workflow metadata, rollback path, incident feedback loop, toil-reduction path, and lifecycle state. A route that is accurate in a notebook but lacks these controls is not production-ready.
