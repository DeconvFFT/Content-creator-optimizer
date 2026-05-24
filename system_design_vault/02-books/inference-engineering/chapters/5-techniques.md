---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Inference Engineering"
authors: "Philip Kiely"
chapter: "5"
chapter_title: "Techniques"
source_path: "/Users/saumyamehta/DS interview prep/books/Inference Engineering.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 5 - Techniques

## Reading Status

Direct source reading pass completed for chapter 5. Promoted to `canon_ready` after cross-check against Stanford CS336 and official serving/runtime docs. This note is original synthesis only and does not include raw book text or long excerpts.

## Core Idea

Inference acceleration is not one trick. Production performance comes from matching workload constraints to a balanced set of techniques: quantization, speculative decoding, KV/prefix caching, model parallelism, and prefill/decode disaggregation. These techniques can reinforce each other, but they can also conflict. Agent Studio should therefore treat serving optimization as measured experimentation, not static configuration.

The chapter's practical rule is that advanced optimizations need enough traffic to justify their operational cost. Some techniques require large fleets, repeated workloads, high request volume, or very large models. Applying them prematurely can increase cost and complexity without improving the product.

## Optimization As Experimentation

The chapter emphasizes patient experimentation because inference-engine settings and optimization techniques interact. Batch size, speculation, KV-cache size, quantization, routing, and disaggregation can move bottlenecks between compute, memory, queueing, and network transfer.

Agent Studio implication:

- Store optimization attempts as experiments with config, workload sample, latency percentiles, throughput, cost, quality deltas, and rollback decision.
- Do not treat "enabled" versus "disabled" as enough metadata. Capture precision, cache policy, routing policy, batch sizing, model-parallel plan, and prefill/decode split.

## Quantization

Quantization lowers numeric precision to improve TTFT, per-user token speed, throughput, memory pressure, and room for other optimizations. It helps prefill because lower precision can use faster compute paths, and helps decode because less memory must be read per value.

The risk is quality loss. Precision errors can compound across operations and tokens, especially in sensitive components.

Important distinctions:

- Floating-point formats preserve dynamic range better than integer formats and are safer for quality-sensitive production inference.
- FP8/MXFP8 are generally practical sweet spots for performance with low quality risk.
- FP4/NVFP4 are promising but require careful validation.
- Integer and highly compressed local formats can be excellent for edge/local demos, but are not automatically safe for production-quality serving.
- Weights and activations are less sensitive; KV cache is moderately sensitive; attention operations are highly sensitive.
- Early and late layers can be more sensitive than middle layers.

Agent Studio implication:

- Quantization should be an eval-gated deployment variant, not a silent provider detail.
- Store the model precision, quantized components, quantization tool, calibration data, and quality comparison against the original model.
- For sensitive agents, require product-specific evals in addition to perplexity and public benchmarks.
- Do not quantize attention-heavy paths aggressively without strong evidence.

## Measuring Quantization Impact

The chapter recommends checking quantized models against original precision using:

- Perplexity: quick signal for token-prediction drift.
- Public intelligence benchmarks: broader but less product-specific.
- Custom product evals: most important for real deployment decisions.

Agent Studio implication:

- A quantized model cannot replace a baseline model unless score movement is indistinguishable from normal eval noise or explicitly accepted by the product owner.
- Optimization dashboards should show quality delta beside latency/cost improvements.

## Speculative Decoding

Speculative decoding accelerates decode by generating draft tokens and having the target model validate them. It improves decode speed and per-user token rate, not time to first token.

Performance depends on:

- Draft token cost.
- Draft sequence length.
- Token acceptance rate.

Speculation works best at low batch sizes where spare compute exists. At higher batch sizes, verification can compete for compute and reduce throughput.

Agent Studio implication:

- Use speculation for interactive streaming agents when decode latency matters and batch sizes are low enough.
- Disable or tune speculation dynamically for high-throughput batch paths.
- Track acceptance rate, rejected-token depth, target model, draft/speculator type, temperature, workload class, and quality impact.

## Speculation Variants

- Draft-target speculation: easy to configure with a smaller related draft model, but adds memory, compute, KV cache, and orchestration overhead.
- Medusa: adds extra decoder heads to generate draft tokens, reducing the need for a separate draft model; historically important but less common in current production.
- EAGLE: purpose-built speculator using hidden states, often strong for general use when the team can train or attach the speculator and the engine supports it.
- N-gram speculation: no draft model; uses repeated sequences from context, strong for code completion/revision and other highly repetitive domains.
- Lookahead decoding: more general than n-gram speculation but uses extra compute to generate candidate sequences.

Agent Studio implication:

- Code agents should test n-gram speculation before general-purpose speculation because code often repeats prompt context.
- General chat agents should consider EAGLE-style support only after workload and engine support justify it.
- Speculation should be route-specific, not global across all agents.

## KV Cache And Prefix Caching

KV caching is required for practical autoregressive inference. Prefix caching extends KV reuse across requests when prompts share an identical prefix. This can sharply reduce TTFT and cost for:

- long system prompts;
- tool schemas;
- agent scaffolds;
- repeated codebase context;
- document QA;
- RAG prompts;
- multi-turn conversations.

Prefix caching only works until the first novel token. Context layout therefore affects performance: stable shared content should appear before request-specific content.

Agent Studio implication:

- Context Engineering should order prompts for cacheability: stable system instructions, tool schemas, and reusable context first; user-specific or volatile content later.
- Trace records should include cache hit/miss, cached token count, prefix length, cache scope, and latency savings.
- Cache-aware prompt templates are an inference feature, not only a prompt-engineering style preference.

## KV Cache Storage And Routing

KV cache is valuable but consumes scarce GPU memory. It can be stored in tiers:

- GPU VRAM: fastest, smallest.
- CPU RAM: slower, larger.
- Local SSD: much slower, larger.
- Networked SSD/global cache: broadest but slowest.

Routing should account for cache locality. A user with a long conversation or repeated codebase context should be routed to replicas likely to have the relevant KV blocks. Global cache can improve availability across replicas, but hot local cache is still faster.

Agent Studio implication:

- Add cache-aware routing for long-context chat, codebase QA, and multi-turn agents.
- Avoid routing purely by replica load when cache locality dominates latency/cost.
- Track cache eviction, hot keys, user/tenant scope, and cache storage tier.

## Long Context Handling

Long context becomes an inference problem when sequence length creates KV-cache and attention pressure. Long inputs should be part of benchmark suites because they often expose production bottlenecks.

The chapter highlights:

- FlashAttention to reduce attention memory traffic.
- PagedAttention to reduce KV fragmentation and duplication.
- Chunked prefill to avoid overwhelming the engine on long inputs.
- Parallelism when one GPU cannot hold weights plus KV cache.

Agent Studio implication:

- Long-context agents need separate benchmarks and SLOs.
- Retrieval should still be preferred over blindly stuffing context when latency, cost, or quality suffers.
- For book/codebase agents, measure performance at realistic context sizes, not only short prompts.

## Model Parallelism

Large models need multiple GPUs because weights plus KV cache often exceed one device. The chapter distinguishes:

- Tensor Parallelism: split tensors within layers; best default for low-latency inference inside a single node.
- Expert Parallelism: shard MoE experts; improves throughput and scales better across limited interconnects.
- Pipeline Parallelism: split model layers; generally poor for latency, mainly useful across nodes when required.
- Context/data-style parallelism: rare for LLM inference but important in some modalities such as video.

Agent Studio implication:

- Serving profiles should record model-parallel strategy, GPU count, interconnect assumptions, and expected latency/throughput tradeoff.
- Dense low-latency agents should prefer tensor parallelism when multi-GPU is necessary.
- MoE high-throughput deployments should evaluate expert parallelism.
- Avoid multi-node inference unless model size, sequence length, or throughput truly requires it.

## Disaggregation

Disaggregation separates prefill and decode onto different engines or hardware. It works because prefill is compute-bound and drives TTFT, while decode is memory-bound and drives token speed. Separation allows each side to be tuned independently.

Good candidates:

- very high volume, roughly hundreds of millions to billions of tokens per day depending on model size;
- large models, especially 100B+ parameter class;
- prefill-heavy traffic with long input sequences.

Poor candidates:

- low-volume agents;
- small models;
- short prompts;
- workloads dominated by prefix-cache hits;
- deployments where extra GPUs would be better used as replicas.

Agent Studio implication:

- Disaggregation should be reserved for mature, high-volume model lanes.
- Conditional disaggregation is preferable for mixed traffic because short or cache-hit requests can stay on decode workers.
- Track prefill queue size, prefill/decode engine ratio, KV transfer latency, queue thresholds, cache pressure, and runtime reconfiguration decisions.

## Failure Modes

- Quantization improves speed but silently reduces answer quality.
- Speculation improves per-user token speed but hurts throughput when batch sizes are too high.
- Cache keys ignore tenant/user/security scope and create leakage risk.
- Prompt templates put unique tokens early and destroy prefix-cache reuse.
- KV cache fills GPU memory and causes unexpected eviction/miss spikes.
- Long-context benchmarks are skipped, so production traffic hits OOM or tail-latency failures.
- Tensor parallelism is pushed across slow interconnects and becomes communication-bound.
- Multi-node inference is used where horizontal replica scaling would be cheaper and simpler.
- Disaggregation is deployed before traffic volume and workload shape justify the complexity.

## Agent Studio Design Decisions

- Add `serving_optimization_profile` to model deployments.
- Require eval baselines before quantization, speculation, or model replacement.
- Capture cacheability as part of prompt/context design.
- Use route-specific optimization: code agents, chat agents, retrieval agents, background ingestion, and eval runners should not share one tuning profile.
- Track latency and quality together in optimization reports.
- Separate long-context benchmarks from short-chat benchmarks.
- Keep disaggregation as a later-stage architecture option, not a default.

## Follow-Ups

- Define the Agent Studio serving profile schema.
- Add benchmark cases for long-context RAG, codebase QA, tool-heavy agents, and batch embedding.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-state-space-transformer-tradeoffs]] - Stanford CS25, "On the Tradeoffs of State Space Models and Transformers" ([YouTube](https://www.youtube.com/watch?v=OyimE74UMF8)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
