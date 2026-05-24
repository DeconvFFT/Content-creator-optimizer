---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_class: official_doc_page
rights_status: official_public
stores_raw_source_text: false
sources:
  - https://kserve.github.io/website/
  - https://kserve.github.io/website/docs/model-serving/predictive-inference/frameworks/overview
  - https://kserve.github.io/website/docs/model-serving/generative-inference/overview
  - https://kserve.github.io/website/docs/model-serving/predictive-inference/rollout-strategies/canary
  - https://kserve.github.io/website/docs/model-serving/predictive-inference/autoscaling/kpa-autoscaler
  - https://kserve.github.io/website/docs/model-serving/predictive-inference/observability/prometheus-metrics
  - https://kserve.github.io/website/docs/model-serving/inferencegraph/overview
---

# KServe Model Serving Rollouts

## Direct-Read Scope

This note is compact original synthesis from current official KServe 0.17 documentation for the project overview, predictive runtimes, generative Hugging Face runtime, canary rollout strategy, Knative autoscaling, Prometheus metrics, and InferenceGraph. It replaces the older archived-only canary reference for current planning. It stores no raw source text or copied examples.

## System Design Takeaways

KServe's useful lesson for Agent Studio is that model serving is a Kubernetes-native release surface, not a plain endpoint URL. An `InferenceService` binds model/runtime identity, resource requests, networking, health, autoscaling, revision tracking, traffic management, observability, and protocol shape.

Agent Studio should mirror that shape for every production route:

- stable route identity;
- immutable candidate revision;
- currently served revision;
- previous known-good revision;
- traffic split;
- rollout mode;
- rollback target;
- health/eval/metric gates;
- protocol and runtime contract.

This applies to LLM routes, embedding/reranking routes, moderation routes, visual routes, and classic predictive models.

## Canary And Revision Controls

KServe canary rollout is explicitly revision based. A candidate `InferenceService` revision can receive a chosen percentage of traffic while the last fully rolled-out good revision keeps the remaining traffic. If the candidate becomes healthy and is promoted, it becomes the latest rolled-out revision. If rollback is needed, traffic can be pinned back to the previous healthy revision.

Agent Studio implications:

- store `latest_ready_revision`, `latest_rolled_out_revision`, and `previous_rolled_out_revision` separately;
- store `canaryTrafficPercent` or equivalent route weight as auditable release metadata;
- do not conflate "ready" with "promoted";
- block traffic to unhealthy candidate revisions;
- make rollback a pointer to a known-good revision, not a rebuild from memory;
- treat canary rollout as serverless-mode specific when using KServe's native rollout behavior.

For Agent Studio content routes, the same state machine should apply to prompt versions, retrieval indexes, reranker settings, model adapters, agent graphs, and media generation routes.

## Autoscaling And Cold Start

KServe's Knative Pod Autoscaler path scales by incoming load in serverless mode. It supports target concurrency, target QPS, GPU-backed services, hard container concurrency, scale-to-zero, and component-level scaling for transformer/predictor pieces.

The operational caveat is cold start: pod creation, image pull, and model download can dominate tail latency during scale-out or scale-from-zero. Agent Studio should separate:

- steady-state latency;
- cold-start latency;
- scale-up latency;
- model/image load time;
- queueing during hard concurrency limits;
- predictor versus transformer component saturation.

Autoscaling policy should match workload class. Realtime-adjacent routes need a warm floor. Batch ingestion and offline eval routes can tolerate queueing and scale-to-zero if user-visible status is clear.

## Observability And Metrics

KServe exposes Prometheus scraping through inference-service annotations, but the docs also warn that model servers do not export one unified metric set. Some runtimes expose step latency for preprocess, explain, predict, and postprocess; LLM runtimes may expose different metrics.

Agent Studio should therefore require a per-runtime metric contract:

- which port/path exposes metrics;
- which metrics exist for this runtime;
- which metrics are release-blocking;
- which metrics drive autoscaling;
- whether request/response logging is enabled and redacted;
- how traces link to route revision and source snapshot.

A route cannot be promoted just because Prometheus scraping is enabled. The metric names and eval gates need to match the runtime and product risk.

## Inference Graphs And Route Composition

KServe InferenceGraph supports sequence, switch, ensemble, and splitter nodes. The important Agent Studio pattern is explicit routing structure:

- sequence for preprocessing, retrieval, reranking, generation, and validation chains;
- switch for risk- or modality-dependent paths;
- ensemble for parallel judges or multi-model comparison;
- splitter for traffic experiments.

Graph edges must preserve response-passing semantics, conditions, and weights. Agent Studio should version these graph definitions as route artifacts and attach eval cases to each branch.

## Current-Source Cross-Check

Current KServe 0.17 canary docs still make canary rollout a serverless deployment-mode feature. They separate latest ready, latest rolled-out, previous rolled-out, and unhealthy candidate behavior, which supports Agent Studio's release-state separation and rollback target requirement.

Current KServe autoscaling docs still make KPA a Knative-mode path based on incoming load, target concurrency or QPS, GPU-backed services, hard concurrency, scale-to-zero, panic/stable windows, and cold-start/model-download cost. Agent Studio should treat autoscaling mode, warm floor, cold-start budget, and workload class as release evidence.

Current KServe observability and InferenceGraph docs still support runtime-specific metric contracts and explicit graph-route composition. Prometheus scraping alone is not enough; route release needs known metric names, branch semantics, graph weights, conditions, and eval coverage for each branch.

## Agent Studio Design Implications

- Replace archived KServe canary source references with current KServe 0.17 docs where possible.
- Route promotion should have an `InferenceService`-like release object even if the product does not use KServe directly.
- Canary percent, revision IDs, health status, eval gates, SLO gates, and rollback target should be written before any candidate receives real traffic.
- Keep ready, canary, promoted, rolled-back, and retired states distinct.
- Treat OpenAI-compatible generative endpoints as protocol contracts, not provider equivalence; rerank, embeddings, scoring, and chat may share an endpoint surface while having different eval gates.
- Store autoscaling mode and deployment mode because KServe canary rollout and Knative autoscaling assumptions are mode-specific.
- Keep graph route weights and canary traffic weights separate: one is product workflow logic, the other is release/traffic control.

## Datastore Objects Added

- `inference_service_record`
- `model_revision_record`
- `canary_rollout_record`
- `traffic_split_record`
- `rollout_health_gate`
- `rollout_promotion_event`
- `runtime_metric_contract`
- `inference_graph_record`
- `inference_graph_edge`
- `serving_rollout_release_gate`

## Canon Decision

This note is canon-ready for Agent Studio serving-release architecture. Model, embedding, reranking, moderation, vision, and agent-runtime routes should not receive production traffic until the serving rollout gate proves candidate and baseline revisions, deployment mode, canary split, latest ready and rolled-out revisions, previous known-good rollback target, health gates, runtime metric contract, autoscaling/cold-start evidence, graph-route branch evals where applicable, promotion event, and rollback condition.
