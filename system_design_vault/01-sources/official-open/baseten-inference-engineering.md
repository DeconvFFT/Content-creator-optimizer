---
type: source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_url: https://www.baseten.co/inference-engineering/
source_status: official_public
cross_checks:
  - ../../02-books/inference-engineering/chapters/0-inference
  - ../../02-books/inference-engineering/chapters/1-prerequisites
  - ../../02-books/inference-engineering/chapters/2-models
  - ../../02-books/inference-engineering/chapters/3-hardware
  - ../../02-books/inference-engineering/chapters/4-software
  - ../../02-books/inference-engineering/chapters/5-techniques
  - ../../02-books/inference-engineering/chapters/6-modalities
  - ../../02-books/inference-engineering/chapters/7-production
  - ../../01-sources/official-open/inference-engineering-cross-check
  - ../../03-patterns/inference/realtime-and-inference-patterns
---

# Baseten Inference Engineering

## Direct-Read Scope

Read directly from Baseten's official Inference Engineering book page on 2026-05-18. The page is an official source map and availability/provenance source for the book, not a substitute for the local direct-read chapter notes already in the vault. This note stores original synthesis only and no raw book text.

## Source Map Read

Baseten frames inference engineering as a production discipline across three layers:

- runtime: model architecture, execution engine, kernels, attention, quantization, KV cache, modality-specific preprocessing;
- infrastructure: GPUs/accelerators, memory, interconnects, model placement, capacity, autoscaling, queues, regions;
- tooling: deployment, model management, observability, evaluation, rollback, and developer control surfaces.

The official table of contents maps cleanly to the local chapter notes:

| Book section | Baseten source-map signal | Vault implication |
|---|---|---|
| Chapter 0 Inference | Inference is a cross-layer map, not a single API call. | Keep route, runtime, infrastructure, and tooling records separate but joined by release IDs. |
| Chapter 1 Prerequisites | Product use case, latency budget, cost budget, model choice, and evaluation come before optimization. | Require an `inference_contract` before serving experiments or provider migration. |
| Chapter 2 Architecture | Model families and bottlenecks determine optimization surface, with attention called out as central. | Store architecture class, context limit, active parameters, modality, tokenizer/template, and attention/cache behavior. |
| Chapter 3 Hardware | GPU spec sheets, memory, architecture, and SKUs matter. | Keep accelerator records with memory, bandwidth class, precision support, interconnect, region, and fallback pool. |
| Chapter 4 Software | CUDA, PyTorch, Transformers, Diffusers, vLLM, SGLang, TensorRT-LLM, and Dynamo are serving-stack decisions. | Version runtime engine, container, driver, compiler path, model artifact format, and engine caveats per route. |
| Chapter 5 Techniques | Quantization, speculative decoding, KV reuse, model parallelism, and disaggregation are production techniques. | Treat each optimization as a measured experiment with quality, latency, throughput, cost, and rollback gates. |
| Chapter 6 Modalities | Voice, visuals, embeddings, ASR, TTS, image, and video routes share some serving tools but differ in bottlenecks. | Do not benchmark all provider paths with one LLM chat workload. Each modality needs preprocessing, metric, rights, and latency contracts. |
| Chapter 7 Production | Operating optimized inference services is a production-systems problem. | Promote provider routes only with readiness smoke, observability, fallback, canary, and incident/rollback evidence. |

## Canon Decision

Inference must be represented as a first-class Agent Studio subsystem. A model call is not a complete design unit; it sits inside a route with product SLOs, workload class, model architecture, runtime engine, hardware/capacity plan, modality contract, serving lane, telemetry, and rollback path.

This source also confirms a rights/provenance point: the book is available as a free PDF from Baseten's official site. The local PDF can be treated as user-provided official-source material unless future metadata contradicts that provenance.

## Agent Studio Design Implications

- Add or strengthen `inference_contract`: use case, workload class, latency budget, cost budget, quality floor, compliance/data-boundary constraints, and target modality.
- Add `inference_source_map`: official source page, local file, chapter coverage, provenance status, and cross-check notes.
- Add `serving_lane`: realtime, interactive, batch ingestion, eval sweep, media generation, embedding/indexing, and backfill lanes should not share production-readiness claims.
- Add `optimization_experiment`: optimization technique, baseline route, candidate route, workload sample, quality delta, latency/throughput/cost delta, and rollback trigger.
- Add `modality_serving_contract`: modality, preprocessing, output artifact type, metric set, rights/consent surface, latency class, and storage/redaction policy.
- Add `provider_readiness_record`: provider, endpoint, credentials/config state, smoke result, quota/capacity assumption, fallback path, and last verified time.
- Keep realtime voice transport and waveform generation separate from deep expert reasoning. Gemma-style expert routes can help with reasoning, but the realtime stack must prove turn-taking, transcript deltas, audio chunks, endpointing, interruption, cancellation, and playback.

## Failure Modes

- Optimizing before the product latency/cost/quality contract exists.
- Treating one model benchmark as proof for realtime, batch, retrieval, media, and eval workloads.
- Collapsing runtime, infrastructure, and tooling into one opaque provider setting.
- Shipping quantization, speculative decoding, cache reuse, or disaggregation without a quality gate.
- Marking a provider route ready from a dry rehearsal that did not call the real provider.
- Forgetting that multimodal routes need modality-specific preprocessing, metrics, and rights handling.
