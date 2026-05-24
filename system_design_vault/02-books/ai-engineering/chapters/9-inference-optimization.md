---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "AI Engineering"
authors: "Chip Huyen"
chapter: "9"
chapter_title: "Inference Optimization"
source_path: "/Users/saumyamehta/DS interview prep/books/AI Engineering.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 9 - Inference Optimization

## Reading Status

Direct source reading pass completed for chapter 9 from the local user-provided PDF extraction span. This note is original synthesis only; it avoids raw text dumps, copied formulas, copied tables, copied figures, and long excerpts.

## Core Idea

Inference optimization is the discipline of making model serving fast enough, cheap enough, and reliable enough for product use. It operates at three layers: model, hardware, and service. Model-level techniques can reduce size or change architecture; hardware choices define available compute, memory, bandwidth, and power; service-level techniques allocate requests to resources under latency and cost constraints.

For Agent Studio, inference optimization is not a backend afterthought. It shapes which agents can run in realtime, which routes should be online versus batch, when to use prompt caching, when to self-host, when to use provider APIs, and how to measure route quality without hiding latency behind aggregate averages.

## Inference Service Vocabulary

An inference server hosts models and runs them on available hardware. An inference service wraps the server with request intake, routing, preprocessing, batching, caching, streaming, monitoring, and possibly postprocessing. Provider model APIs are inference services; self-hosted open models require Agent Studio to own more of this surface.

Agent Studio implication: each route should distinguish provider-managed serving from self-hosted serving. Provider routes still need latency, cost, streaming, cache, and failure telemetry. Self-hosted routes additionally need model placement, replica count, accelerator type, batching policy, cache policy, and autoscaling behavior.

## Bottlenecks

Optimization starts by identifying the bottleneck.

Compute-bound work is limited by arithmetic throughput. Prefill for transformer language models is usually compute-bound because input tokens can be processed in parallel.

Memory-bandwidth-bound work is limited by moving data fast enough. Autoregressive decoding is often bandwidth-bound because every output token requires repeatedly moving large model weights and cached states through accelerator memory.

Memory-capacity limits appear as out-of-memory failures, but many capacity problems turn into bandwidth problems once data is split or offloaded. The practical diagnostic is to measure where time is spent and whether the workload is saturating compute or memory bandwidth.

Agent Studio implication: capacity planning should track prefill and decode separately. Long prompts, large retrieved contexts, and many hidden agent steps pressure prefill and cache memory. Long outputs, tool-repair loops, and verbose drafts pressure decode and user-visible latency.

## Online, Batch, And Streaming

Online APIs optimize for latency. Batch APIs optimize for cost and throughput by accepting longer turnaround time. Streaming improves perceived responsiveness by returning tokens as they are generated, but it reduces the opportunity to score or guard the full response before the user sees it.

Agent Studio implication:

- interactive drafting, chat, voice, and agent steering need online routes;
- synthetic data generation, corpus reprocessing, eval sweeps, embedding refreshes, and offline audits should prefer batch routes;
- streaming routes need incremental safety strategy because final-response grading may arrive too late;
- non-user-visible planning and tool steps should be measured separately from time to first visible token.

## Performance Metrics

Total latency is too blunt for LLM systems. The chapter breaks latency into time to first token and time per output token. TTFT is driven largely by prefill. TPOT is driven largely by decode. For agentic routes, the first model token may be hidden from the user, so Agent Studio should also measure time to first published token.

Throughput measures total work completed, often output tokens per second or completed requests per minute. Goodput is more useful for production because it counts only requests that satisfy the latency SLO. Utilization metrics such as model FLOP utilization and model bandwidth utilization help diagnose efficiency, but they are not goals by themselves. Higher utilization is only useful if cost, latency, and reliability improve.

Agent Studio route telemetry should include:

- TTFT, TPOT, total latency, and time to first published token;
- p50, p90, p95, and p99 percentiles by route and workload slice;
- input tokens, output tokens, hidden tokens, retrieved context tokens, and tool-output tokens;
- request throughput, token throughput, and goodput under route SLOs;
- cache hit rate, batch size, queue time, model load time, and provider throttling;
- cost per request, cost per successful request, and cost per accepted artifact.

## Hardware And Accelerator Selection

Accelerators differ in compute throughput, memory size, memory bandwidth, precision support, interconnect, compiler/runtime support, power draw, and availability. GPU memory hierarchy matters because model weights, activations, and KV cache movement can dominate latency. For inference, memory bandwidth and cache management often matter as much as peak FLOP/s.

Agent Studio implication: model placement should be workload-aware. A code-editing route with long inputs and copied output has different needs from a short classification route, a realtime voice route, or a batch synthetic-data route. The serving profile should document accelerator type, precision, max batch, max context, cache strategy, expected concurrency, and cost envelope.

## Model-Level Optimization

Model compression reduces the serving footprint. Quantization is common because it reduces memory use and can improve throughput, especially for bandwidth-bound decode. Distillation trains a smaller model to approximate a larger one for a target behavior. Pruning can reduce parameters or sparsify weights, but practical speedups depend on hardware and runtime support.

Autoregressive decoding can be accelerated with techniques such as speculative decoding, inference with reference, and parallel decoding. Speculative decoding uses a faster draft model and verifies proposed tokens with the target model. Inference with reference reuses spans from the input when outputs overlap heavily with context, which is relevant to code editing, retrieval-based answers, and document-grounded workflows. Parallel decoding tries to produce multiple future tokens at once and then verify or reconcile them.

Attention optimization addresses KV cache size and attention computation. Long context and large batches can make the KV cache a major memory consumer. Techniques include attention redesign, multi-query or grouped-query attention, cross-layer sharing, KV cache compression or quantization, PagedAttention-style cache management, and specialized attention kernels such as FlashAttention.

Agent Studio implication: model-level optimizations should be treated as behavior-affecting unless proven otherwise. Quantization, distillation, pruning, altered attention, and custom kernels can change output quality, numerical behavior, or edge-case reliability. They require eval gates, not just latency benchmarks.

## Kernels And Compilers

Kernels are hardware-specific implementations of hot operations such as matrix multiplication and attention. Common optimization patterns include vectorization, parallelization, loop tiling, and operator fusion. Compilers lower model code into hardware-compatible execution plans and may replace generic operations with specialized kernels.

Agent Studio implication: the runtime record should identify inference framework, compiler path, kernel features, quantization mode, attention implementation, and hardware target. If a route moves from one serving stack to another, it should be evaluated like a model/provider change because optimized runtimes can produce different behavior or failure modes.

## Service-Level Optimization

Batching improves throughput by processing multiple requests together. Static batching waits for fixed-size batches, dynamic batching uses a size or time window, and continuous batching lets completed requests leave while new ones enter. Continuous batching is especially important for LLMs because output lengths vary widely.

Prefill/decode disaggregation assigns compute-bound and bandwidth-bound phases to different resources. Prompt caching reuses shared prompt prefixes or long context segments, reducing repeated prefill cost for system prompts, long documents, codebases, and multi-turn conversations.

Parallelism strategies include replica parallelism, tensor parallelism, pipeline parallelism, context parallelism, and sequence parallelism. Replica parallelism is simple and useful for latency/concurrency. Tensor parallelism helps serve large models and can reduce latency. Pipeline parallelism enables larger models but can add per-request latency and is more attractive for throughput-oriented workloads.

Agent Studio implication: the serving layer should make batching, cache, prefill/decode split, and parallelism explicit route settings. These choices affect TTFT, TPOT, cost, and capacity, so they belong in the route registry and capacity-estimation template.

## Datastore Requirements

Agent Studio should store inference decisions as first-class records:

- `serving_profile`: provider or self-hosted, model id, runtime, framework, accelerator, precision, context limit, max output, and streaming support.
- `optimization_config`: quantization, distillation source, speculative draft model, attention implementation, KV cache strategy, compiler, kernel flags, and prompt cache policy.
- `batching_policy`: static/dynamic/continuous mode, max batch size, max wait, queue limits, priority class, and overflow behavior.
- `parallelism_plan`: replica count, tensor parallel degree, pipeline stages, context/sequence split, placement constraints, and interconnect assumptions.
- `latency_slo`: route-level TTFT, TPOT, time-to-publish, total latency, p95/p99 limits, and goodput target.
- `capacity_run`: workload mix, input/output length distribution, concurrency, cache hit rate, throughput, goodput, cost, and bottleneck diagnosis.
- `optimization_eval`: before/after quality, safety, structured-output validity, grounding, latency, cost, and regression slices.
- `route_runtime_trace`: queue time, prefill time, decode time, tool time, hidden-token time, publish time, cache hits, batch id, and provider throttling.

## Failure Modes

- Reporting average latency while p95 or p99 latency is unusable.
- Optimizing throughput while goodput under the SLO gets worse.
- Treating TTFT and TPOT as one metric and misdiagnosing prefill versus decode bottlenecks.
- Streaming unsafe or low-quality content before guardrails can evaluate it.
- Using batch APIs for workflows that need interactive feedback.
- Ignoring hidden agent planning time and measuring only final visible generation.
- Assuming provider/model swaps preserve latency or cache behavior.
- Applying quantization or distillation without behavior regression tests.
- Filling long prompts with irrelevant retrieval and then blaming the model for high TTFT.
- Using batching settings that improve cost but make short requests wait behind long outputs.
- Choosing accelerators from peak FLOP/s while the workload is memory-bandwidth-bound.

## Agent Studio Design Implications

- Route promotion should require both quality evals and serving evals.
- Capacity estimates should be based on realistic input/output length distributions, not only model size.
- The cockpit should show latency decomposition: queue, prefill, decode, hidden agent work, tool time, and publish time.
- The route registry should separate online, batch, and realtime routes, with distinct SLOs.
- Prompt caching should be planned for stable system prompts, long source packs, codebase context, and repeated multi-turn work.
- Self-hosted inference should start with explicit workload assumptions and a fallback provider route.
- Model-level optimization should be gated by evals because faster serving is not useful if it changes groundedness, citation behavior, tool selection, or safety.
- Agent orchestration should have budgets for hidden tokens and hidden tool loops so the user-visible experience remains predictable.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-state-space-transformer-tradeoffs]] - Stanford CS25, "On the Tradeoffs of State Space Models and Transformers" ([YouTube](https://www.youtube.com/watch?v=OyimE74UMF8)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
