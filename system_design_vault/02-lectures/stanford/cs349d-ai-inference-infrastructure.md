---
type: lecture-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
course: Stanford CS349D AI Inference Infrastructure
rights_status: official_or_open_public
provenance_status: official_stanford_course_page_direct_read_sparse_public_schedule_no_lecture_slides_or_video_claim
sources:
  - https://web.stanford.edu/class/cs349d/
---

# CS349D - AI Inference Infrastructure

## Scope

Direct-read synthesis from the official Stanford CS349D Spring 2026 public course page. The visible public page is sparse: it gives the course purpose, discussion-based lecture model, coursework structure, and mini serving-engine milestones, but it does not expose detailed lecture notes, slides, paper PDFs, recordings, or a populated schedule in the page text available in this pass. This note therefore treats CS349D as a high-value official source map and curriculum signal, not as full lecture-video or paper-ingestion coverage.

No raw page text, copied course material, or long excerpts are stored here.

Current-source check on 2026-05-18: the public page still identifies CS349D as Stanford Spring 2026 AI Inference Infrastructure, frames efficient LLM and agentic-AI inference as a production-scale systems challenge, says most lectures are in-class paper discussions, and exposes mini serving-engine milestones rather than detailed public lecture notes or recordings. The canon scope remains the public course framing and milestone ladder only.

## Production Inference Signal

CS349D is explicitly about infrastructure for efficient, cost-effective AI inference at production scale. The course framing matters for Agent Studio because it treats inference as a systems problem, not a model selection afterthought. The production serving route must make engineering choices about model parallelism, batching, memory layout, context reuse, prefill/decode split, speculative execution, and compatibility between features.

The mini serving-engine milestones are especially useful as an implementation ladder:

- parallelism first, so larger models and higher throughput have an explicit execution plan;
- continuous batching and PagedAttention next, so GPU utilization and KV memory behavior become measurable;
- context caching and chunked prefill next, so long-context and repeated-source workloads reduce redundant work;
- advanced serving features later, such as speculative decoding, hierarchical caching, and prefill/decode disaggregation.

For Agent Studio, this ladder should become the promotion path for self-hosted or dedicated model serving. A route should not jump to advanced serving complexity until baseline parallelism, batching, memory, and cache behavior are measured.

## Agent Studio Implications

### Serving Features Are Compatibility Surfaces

The course milestone wording says later features build on earlier features and must remain compatible. That is a useful production rule: batching, KV management, prefix caching, chunked prefill, speculative decoding, tensor parallelism, and disaggregation are not independent toggles. Each optimization changes scheduler behavior, memory pressure, latency distribution, failure modes, and sometimes output equivalence.

Agent Studio should store a compatibility matrix before promoting an inference route.

Required route evidence:

- workload class: realtime-adjacent chat, source-backed drafting, batch eval, ingestion, media, or long-context review;
- parallelism configuration and model-shard assumptions;
- batching policy and fairness caveats;
- KV/cache policy and eviction behavior;
- prefill/decode phase metrics;
- feature compatibility test results;
- quality regressions from speculation, quantization, cache reuse, or changed tokenizer/runtime config.

### Mini-Engine Thinking Belongs In Capacity Planning

Even if Agent Studio uses managed providers, the mini-engine structure is a strong mental model for capacity planning. Provider endpoints still have implicit batching, memory, prefill, decode, and cache behavior. Where the provider does not expose internals, the route should at least record black-box measurements that approximate the same surfaces: time to first token, inter-token latency, queue delay, long-context penalty, repeated-context speedup, and cost per output.

### Source-Heavy Routes Need Context-Caching Discipline

Agent Studio will repeatedly send stable source packs: local book syntheses, official doc notes, route policies, eval rubrics, and artifact histories. Context caching and chunked prefill are therefore not just infra optimizations; they are product features for source-grounded workflows. Cache boundaries must include source snapshot, route version, model/tokenizer, tenant/project scope, and rights/sensitivity scope.

### Advanced Features Need Release Gates

Speculative decoding, hierarchical context caching, and prefill/decode disaggregation are valuable only with workload-specific evidence. They need separate gates because they can improve throughput while worsening tail latency, fairness, debuggability, or route reproducibility.

Agent Studio should require:

- baseline versus optimized route comparison;
- p50/p95/p99 latency and throughput by workload slice;
- first-token and per-token latency split;
- memory pressure and cache-hit evidence;
- output-quality and citation-grounding regression checks;
- rollback trigger and fallback engine.

## Datastore Additions

- `serving_feature_compatibility_matrix`: route/runtime feature set, compatibility status, test fixtures, incompatible combinations, and release decision.
- `mini_serving_engine_milestone`: milestone record for parallelism, batching, attention/KV memory, context caching, chunked prefill, speculation, hierarchical caching, and disaggregation.
- `inference_phase_metric`: validation, queue, prefill, decode, streaming, cache-transfer, and end-to-end timing by workload slice.
- `context_cache_boundary`: cache key scope for source snapshot, route version, model/tokenizer, tenant/project, rights status, and sensitivity label.
- `serving_optimization_gate`: baseline route, candidate optimization, workload slice, performance deltas, quality deltas, memory deltas, compatibility result, rollback condition, and decision.
- `serving_feature_stack_release_gate`: promotion gate for a serving stack that combines parallelism, continuous batching, PagedAttention/KV policy, context caching, chunked prefill, speculation, hierarchical caching, or prefill/decode disaggregation.

## Serving Feature Stack Release Gate

`serving_feature_stack_release_gate` is the promotion gate for self-hosted, dedicated, or provider-backed serving lanes when Agent Studio adopts inference-engine features beyond a plain managed call. It turns CS349D's milestone ladder into release evidence.

Required evidence:

- `gate_id`, `route_id`, `candidate_release_id`, `serving_workload_profile_ref`, `runtime_engine_ref`, `endpoint_contract_ref`, `baseline_runtime_ref`, and `fallback_runtime_ref`;
- `mini_serving_engine_milestone_refs`, `serving_feature_compatibility_matrix_ref`, `parallelism_profile_ref`, `batching_policy_ref`, `attention_or_kv_policy_ref`, `context_cache_boundary_refs`, `chunked_prefill_policy_ref`, `speculation_policy_ref`, `hierarchical_cache_policy_ref`, and `prefill_decode_topology_ref`;
- `inference_phase_metric_refs` for queue, validation, prefill, decode, streaming, cache transfer, first-token, per-token, and end-to-end timings;
- `workload_benchmark_refs`, `p50_p95_p99_latency_refs`, `throughput_refs`, `memory_pressure_refs`, `cache_hit_refs`, `cost_delta_refs`, and `saturation_signal_refs`;
- `quality_regression_refs`, `citation_grounding_refs`, `tokenizer_runtime_config_refs`, `source_snapshot_cache_scope_refs`, `tenant_rights_scope_refs`, `fairness_or_starvation_refs`, `observability_refs`, `rollback_trigger_refs`, `decision`, and `reviewed_at`.

Do not promote a serving feature stack when:

- a later feature is enabled before earlier parallelism, batching, memory, and cache behavior are measured;
- context cache keys omit source snapshot, route version, model/tokenizer, tenant/project, rights, or sensitivity scope;
- speculation, quantization, cache reuse, or runtime changes improve throughput but fail quality, citation, or reproducibility checks;
- prefill/decode separation lacks phase metrics, queue policy, cache-transfer evidence, and fallback topology;
- workload classes with different latency behavior share one unbounded serving lane;
- provider black-box endpoints are treated as feature-compatible without p50/p95/p99, first-token, per-token, long-context, and repeated-context measurements.

## Cross-Checks

- Reinforces [[../../01-sources/official-open/vllm-runtime-serving]] for PagedAttention, prefix caching, speculative decoding, disaggregated prefill, and runtime metrics.
- Reinforces [[../../01-sources/official-open/huggingface-tgi-continuous-batching]] for continuous batching, token/batch limits, scheduler behavior, KV cache evidence, and phase metrics.
- Reinforces [[../../01-sources/official-open/nvidia-dynamo-disaggregated-inference]] for prefill/decode disaggregation, KV-aware routing, and LLM-specific autoscaling.
- Reinforces [[../../01-sources/official-open/ray-serve-llm-production-serving]] for deployment-level serving, autoscaling, and endpoint contracts above the inference engine.
- Reinforces [[../../02-lectures/stanford/cs25-production-inference]] and [[../../01-sources/official-open/baseten-inference-engineering]] on treating inference as a layered runtime/infrastructure/tooling design problem.

## Coverage Caveat

This is not a full CS349D lecture series note. It should be upgraded only if Stanford publishes detailed public lecture materials, readings, student notes, recordings, or project artifacts that can be read directly without login or rights ambiguity.
