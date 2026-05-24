---
type: official-source-cross-check
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-17
cross_checks:
  - source_title: "Inference Engineering"
    chapters: "0-7"
sources:
  - https://cs336.stanford.edu/
  - https://cs336.stanford.edu/spring2025/index.html
  - https://raw.githubusercontent.com/stanford-cs336/lectures/main/lecture_02.py
  - https://raw.githubusercontent.com/stanford-cs336/lectures/main/lecture_07.py
  - https://raw.githubusercontent.com/stanford-cs336/lectures/main/lecture_10.py
  - https://raw.githubusercontent.com/stanford-cs336/lectures/main/lecture_12.py
  - https://docs.vllm.ai/en/stable/
  - https://docs.vllm.ai/en/stable/serving/openai_compatible_server/
  - https://docs.vllm.ai/en/stable/features/multimodal_inputs/
  - https://docs.vllm.ai/en/stable/features/quantization/
  - https://docs.vllm.ai/en/stable/usage/metrics/
  - https://docs.nvidia.com/tensorrt-llm/
  - https://docs.nvidia.com/dynamo/getting-started/introduction
  - https://nvidia.github.io/TensorRT-LLM/key-features.html
  - https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/batcher.html
  - https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/model_analyzer/README.html
  - https://docs.ray.io/en/latest/serve/llm/index.html
  - https://docs.ray.io/en/latest/serve/llm/architecture/overview.html
  - https://docs.ray.io/en/latest/serve/llm/user-guides/observability.html
  - https://sgl-project-sglang-93.mintlify.app/concepts/radix-attention
  - https://kserve.github.io/archive/0.13/modelserving/v1beta1/rollout/canary/
---

# Inference Engineering - Official Cross-Check

## Scope

This note cross-checks the direct-read chapter notes for [[../../02-books/inference-engineering/chapters/0-inference]], [[../../02-books/inference-engineering/chapters/1-prerequisites]], [[../../02-books/inference-engineering/chapters/2-models]], [[../../02-books/inference-engineering/chapters/3-hardware]], [[../../02-books/inference-engineering/chapters/4-software]], [[../../02-books/inference-engineering/chapters/5-techniques]], [[../../02-books/inference-engineering/chapters/6-modalities]], and [[../../02-books/inference-engineering/chapters/7-production]].

It stores compact original synthesis only. It does not copy raw source text or long excerpts.

## Cross-Check Result

Status: `canon_ready`.

The official sources support the book's core argument: inference design starts with product constraints, then becomes a measured systems problem across model architecture, hardware topology, software stack, memory bandwidth, KV-cache pressure, batching, routing, parallelism, quantization, multimodal preprocessing, observability, and production rollout discipline. None of the checked sources contradict the existing chapter notes.

## Confirmation Matrix

| Book theme | Official-source confirmation | Agent Studio implication |
|---|---|---|
| Inference is a layered runtime, infrastructure, and tooling problem | NVIDIA Dynamo describes a distributed layer above engines with disaggregated serving, smart routing, KV-cache tiering, autoscaling, topology-aware scheduling, fault tolerance, observability, and modular adoption. | Agent Studio should keep runtime profile, infrastructure profile, capacity pool, and developer control surface as separate but linked records. |
| Inference is a product tradeoff, not a generic speed contest | CS336 frames inference around TTFT, per-token latency, throughput, repeated token volume, and deployment use cases. Ray Serve LLM and Triton docs also expose serving choices as workload-dependent configuration. | Each Agent Studio route needs an `inference_contract`: workload class, latency budget, cost budget, quality floor, concurrency shape, and compliance constraints. |
| Resource accounting matters before tuning | CS336 Lecture 2 teaches FLOPs, memory, arithmetic intensity, and roofline-style thinking; Lecture 10 applies that mindset to autoregressive inference. | Optimization reports should separate compute-bound, memory-bound, queue-bound, retrieval-bound, and client-bound bottlenecks instead of reporting only total latency. |
| Architecture determines serving behavior | CS336 2026 includes architecture, attention alternatives, MoE, GPU/TPU, kernels, parallelism, and inference lectures; TensorRT-LLM explicitly publishes support matrices for GPU/model/software combinations. | The model registry needs architecture family, tokenizer/template, modality, active/total parameter metadata, optimization compatibility, and runtime support evidence. |
| Hardware and topology matter | CS336 requires memory hierarchy and systems optimization background, and its 2026 schedule includes GPUs/TPUs, kernels, and parallelism; Dynamo exposes topology-aware gang scheduling and hardware/vendor support concerns. | Hardware records should include accelerator generation, precision support, VRAM, bandwidth, interconnect, instance profile, and placement constraints. |
| Software stack is part of the route | TensorRT-LLM documentation describes optimized engines, Python/C++ runtimes, release notes, support matrix, architecture docs, quantization APIs, plugins, and troubleshooting; vLLM exposes architecture, PagedAttention, prefix caching, metrics, profiling, plugins, and model-development docs. | Route releases should version engine, runtime, container, driver, compiler path, kernel/plugin choices, and model artifact format. |
| Prefill and decode are different workloads | CS336 Lecture 10 distinguishes prefill as parallelizable and generation as sequential and memory-bound. Ray Serve LLM explicitly supports prefill-decode disaggregation for advanced distributed serving. | Track `prefill_time`, `decode_time`, `TTFT`, `TPOT`, and token distributions separately. Do not tune long-context agents from short-chat benchmarks. |
| KV cache drives long-context serving | CS336 Lecture 10, vLLM, TensorRT-LLM, and SGLang all center KV-cache management, paging, prefix reuse, or radix-prefix sharing as first-class inference concerns. | Context engineering must be cache-aware: stable system/tool/source prefixes first, volatile user content later, with cache hit/miss and tenant scope in traces. |
| Continuous/dynamic batching is a throughput lever with latency cost | vLLM lists continuous batching as a core serving feature. Triton dynamic batching docs recommend measuring latency first, then trading delay or batch size for throughput while staying inside the budget. | Batch settings belong in the serving profile and should differ for realtime, interactive, ingestion, eval, and backfill workloads. |
| Quantization needs quality gates | CS336 and TensorRT-LLM cover low-precision formats and quantization features, while the book warns that speed gains can hide quality loss. | Quantized deployments need eval deltas, calibration provenance, precision settings, and rollback thresholds before replacing a baseline route. |
| Speculative decoding is route-specific | CS336 Lecture 10 covers speculative sampling as a way to exploit faster checking than generation. TensorRT-LLM lists speculative sampling as a supported feature. | Use speculation for low-batch interactive routes where decode smoothness matters; measure acceptance rate, latency, throughput, and quality before enabling it broadly. |
| Parallelism depends on interconnect and model shape | CS336 Lecture 7 explains the hardware hierarchy and communication costs. Ray Serve LLM supports tensor, pipeline, expert, data-parallel attention, and multi-node patterns. | Model deployment records need GPU count, interconnect assumptions, tensor/expert/pipeline strategy, and why replicas were not enough. |
| Multimodal serving is a first-class inference surface | vLLM current docs include multimodal input support for images and audio embeddings, stable media UUIDs for multimodal caching, multimodal model-development hooks, and vision-language/embedding examples. | Agent Studio should model VLM, embedding, ASR/TTS, image, and video routes as modality-specific pipelines with preprocessing, caching, and metric contracts. |
| Offline/batch inference is distinct from online serving | vLLM offline inference examples include batch-file format, embeddings, prefix caching, profiling, distributed, disaggregated prefill, and vision-language examples. | Keep ingestion, embedding backfills, eval sweeps, and source reprocessing on separate serving lanes from realtime/interactive agent turns. |
| Production serving needs observability | Ray Serve LLM exposes TTFT, TPOT, GPU cache utilization, batch size, throughput, and request metrics through metrics endpoints and dashboards. Triton Model Analyzer profiles configurations against QoS constraints. | Agent Studio traces should join application span data with engine metrics: TTFT, TPOT, queue depth, batch size, KV utilization, cache hit rate, GPU utilization, route, tenant, model, and cost. |
| Autoscaling and routing are serving architecture, not afterthoughts | Ray Serve LLM documents autoscaling coordination and custom routing; the book's queue/routing guidance is consistent with this. | Route by workload class, tenant priority, estimated token load, cache locality, adapter locality, region/compliance, and replica health. |
| Canary and rollback are normal inference deployment controls | KServe canary rollout docs support partial traffic routing, latest good revision tracking, and rollback. | Dedicated model changes need canary gates for latency, errors, quality, queue depth, cost, cache behavior, and user-impact slices before full promotion. |
| Evaluation remains part of inference decisions | CS336 Lecture 12 emphasizes that evaluation depends on the behavior being measured and requires clear rules of the game. | Model, precision, runtime, prompt-cache, and routing changes must run task-specific evals; public benchmarks are insufficient for Agent Studio production routes. |

## Agent Studio Design Decisions Strengthened

- Add `inference_contract`, `runtime_profile`, `hardware_profile`, `modality_contract`, and `serving_optimization_profile` to route/model deployment records.
- Split serving lanes for realtime voice, interactive studio turns, source ingestion, embedding/indexing, batch backfills, and offline evals.
- Store inference experiment artifacts with config, workload sample, quality delta, latency percentiles, throughput, cost, and rollback decision.
- Treat prompt/context ordering as both a correctness and performance concern because prefix reuse changes TTFT and cost.
- Make cache scope explicit: user, tenant, source set, model version, prompt template version, and retention policy.
- Prefer provider/shared APIs until measured volume, latency, compliance, model control, or cost justifies dedicated serving.
- Require canary deployment and engine observability before marking dedicated serving production-ready.
- Link serving telemetry to content quality outcomes so faster inference is not allowed to reduce groundedness, evidence quality, multimodal artifact quality, or user trust.

## Canon Status

Inference Engineering chapters 0-7 are canon-ready for Agent Studio system-design decisions. They should still be refined when deeper notes are created for remaining Stanford CS336/CS25 videos or newer runtime docs, but they are sufficiently cross-checked for architecture work now.
