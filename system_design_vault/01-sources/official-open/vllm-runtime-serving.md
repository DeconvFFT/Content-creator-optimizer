---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_class: official_doc_page
rights_status: official_public
stores_raw_source_text: false
sources:
  - https://docs.vllm.ai/en/stable/
  - https://docs.vllm.ai/en/stable/serving/openai_compatible_server/
  - https://docs.vllm.ai/en/stable/usage/metrics/
  - https://docs.vllm.ai/en/stable/features/automatic_prefix_caching/
  - https://docs.vllm.ai/en/stable/features/quantization/
  - https://docs.vllm.ai/en/stable/features/speculative_decoding/
  - https://docs.vllm.ai/en/stable/features/disagg_prefill/
  - https://docs.vllm.ai/en/stable/design/paged_attention/
---

# vLLM Runtime Serving

## Direct-Read Scope

This note is compact original synthesis from current official vLLM stable documentation for serving, metrics, prefix caching, quantization, speculative decoding, disaggregated prefill, and PagedAttention design. It stores no raw source text, copied tables, copied examples, or copied diagrams.

## System Design Takeaways

vLLM should be treated as a serving runtime contract, not just a model loader. Its product-visible behavior is shaped by API compatibility, scheduler behavior, KV memory pressure, prefix/cache policy, parallelism, quantization, speculation, multimodal support, and metrics availability.

Current-doc check on 2026-05-18 confirms that this remains a route-release boundary: the OpenAI-compatible server now explicitly covers Completions, Chat Completions, Responses, embeddings, audio transcription/translation, Realtime, tokenizer, pooling, classification, score/generative-scoring, and rerank APIs with runtime-specific caveats; model repository generation configs can override sampling defaults unless disabled; production metrics expose request success, queue/waiting reasons, TTFT, prefill/decode/request latency, KV usage, prefix-cache hits/queries, cached prompt tokens, speculative decoding acceptance, NIXL KV transfer, and optional MFU counters; and disaggregated prefilling remains experimental, useful for TTFT/ITL control, and not a throughput improvement.

Agent Studio route records should preserve the difference between:

- the public endpoint shape exposed to callers;
- the engine/runtime and its pinned version;
- the model artifact and tokenizer/chat template;
- batching and cache policy;
- precision, quantization, and hardware assumptions;
- measured prefill, decode, queue, and streaming behavior.

The same model can satisfy different tasks only after route-specific proof. A source-ingestion route, realtime-adjacent chat route, eval-judge route, and long-context synthesis route should not inherit one vLLM profile silently.

## OpenAI-Compatible Endpoint Surface

vLLM's OpenAI-compatible server is a pragmatic integration layer: it can expose chat/completions, responses, embeddings, audio transcription/translation, realtime, tokenizer, pooling, classification, scoring, and reranking-like custom APIs depending on model type. Compatibility does not mean semantic identity with OpenAI-hosted models.

Agent Studio should record:

- supported endpoint family and unsupported parameters;
- model aliases and tokenizer/chat-template assumptions;
- generation-config policy, because model repository defaults can change sampling behavior;
- extra vLLM-only request parameters;
- streaming and tool-call behavior;
- error semantics and smoke-test results.

This belongs in route-release evidence because callers may assume OpenAI API shape while the runtime still has different defaults, supported modalities, and request parameters.

## KV Cache And Prefix Policy

Automatic prefix caching reuses KV cache for shared prompt prefixes. For Agent Studio, this is most useful when repeated work shares stable source packs, system prompts, policy blocks, schema instructions, or eval rubrics.

The route must still prove safe cache boundaries:

- cache keys should include tenant, source snapshot, route version, model/tokenizer, and rights boundary when relevant;
- stable prefixes should be ordered before volatile user content when that does not harm quality;
- hit, miss, eviction, and cache-pressure metrics should be traceable without storing prompt/cache contents;
- cache reuse should have a fallback to normal prefill when the reuse signal is stale or unsafe.

PagedAttention and related KV management make long-context serving feasible, but they also make memory a release-gating resource. A route should track KV usage, preemptions, queue pressure, prompt tokens cached, and prefill/decode timing instead of treating latency as a single number.

## Quantization And Optimization Gates

vLLM supports many quantization formats and hardware combinations, including weight, activation, FP8, INT4/INT8, GGUF/GPTQ/AWQ-style paths, online quantization, and quantized KV cache options. The important design point is not that quantization exists; it is that each format has hardware support, model support, kernel support, memory effects, and quality risk.

Agent Studio should treat quantization, KV-cache dtype, CUDA graphs, speculative decoding, disaggregated prefill, LoRA/multimodal features, and custom kernels as optimization flags with measured deltas:

- memory saved;
- TTFT and inter-token latency;
- throughput and queue behavior;
- quality and source-grounding regressions;
- supported hardware and model families;
- rollback trigger.

Speculative decoding is especially workload-sensitive. vLLM frames it as a latency tool for medium-to-low-QPS memory-bound workloads, with model-based methods offering stronger latency reductions and lighter methods offering simpler peak-traffic behavior. It should be gated by output-equivalence or quality checks and by metrics for accepted/draft tokens.

## Disaggregated Prefill

Disaggregated prefill separates prefill and decode into different vLLM instances so TTFT and inter-token latency can be tuned independently. The stable docs mark this feature as experimental and explicitly frame it as a latency-control technique, not a throughput improvement.

Agent Studio implication: use disaggregated prefill only for routes with measured long-prompt pressure or tail inter-token latency. Store the topology as a first-class route object with prefill lane, decode lane, KV transfer connector, fallback mode, and feature-compatibility caveats.

For book ingestion and source-backed drafting, a prefill-heavy lane may be valuable. For realtime voice, prefill-heavy work should stay outside the audio-critical path unless the route proves it can preserve interruption and first-audio budgets.

## Metrics And Release Gates

vLLM exposes metrics through the OpenAI-compatible server metrics endpoint. Useful Agent Studio gates include:

- request success and corrupted request counts;
- running and waiting request counts, including waiting reason;
- queue, prefill, decode, inference, inter-token, time-to-first-token, and end-to-end latency;
- prompt, generation, and cached-token distributions;
- KV cache usage and block reuse/eviction samples;
- prefix cache hits and queries;
- speculative-decoding drafts and accepted tokens;
- optional MFU-style performance counters when enabled.

These metrics should drive autoscaling, admission control, and rollout promotion. GPU utilization alone is insufficient because LLM serving bottlenecks can be queue, prefill, decode, cache, connector transfer, or token-distribution shape.

## Agent Studio Design Implications

- Add a `vllm_runtime_profile` record under serving evidence for self-hosted vLLM routes.
- Keep OpenAI-compatible endpoint evidence separate from runtime engine evidence.
- Version engine args, server args, model/tokenizer/chat template, generation-config policy, quantization, KV cache dtype, prefix caching, speculation, and disaggregated prefill settings.
- Track TTFT, inter-token latency, queue time, prefill time, decode time, cached-token rate, KV pressure, request success, and waiting reasons per workload class.
- Promote vLLM route changes through the same canary/rollback discipline as KServe/Ray Serve route changes.
- Compare vLLM, TGI, Ray Serve, Dynamo, TensorRT-LLM, SGLang, and managed APIs by workload slice, not by headline feature list.

## Datastore Objects Added

- `vllm_runtime_profile`
- `openai_compatible_endpoint_contract`
- `paged_attention_memory_record`
- `prefix_cache_policy_record`
- `speculative_decoding_profile`
- `disaggregated_prefill_topology`
- `kv_metric_sample`
- `serving_engine_argument_snapshot`
- `vllm_serving_release_gate`

## Release Gate

Promote vLLM-backed routes only after a `vllm_serving_release_gate` proves endpoint contract, model/tokenizer/chat-template snapshot, generation-config policy, engine and server argument snapshots, batching/KV/PagedAttention behavior, prefix-cache boundary, quantization/KV dtype, speculative decoding profile where enabled, disaggregated-prefill topology where enabled, compatibility matrix, workload benchmarks, metric snapshots, quality/source-grounding deltas, capacity/admission policy, fallback mode, and rollback target.
