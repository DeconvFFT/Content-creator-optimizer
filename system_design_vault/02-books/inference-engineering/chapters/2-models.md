---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Inference Engineering"
authors: "Philip Kiely"
chapter: "2"
chapter_title: "Models"
source_path: "/Users/saumyamehta/DS interview prep/books/Inference Engineering.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 2 - Models

## Reading Status

Direct source reading pass completed for chapter 2 from the local user-provided PDF extraction span. Promoted to `canon_ready` after official/open cross-check against Stanford CS336, NVIDIA Dynamo, TensorRT-LLM, vLLM, and production serving/runtime docs. This note is original synthesis only; it avoids raw text dumps, copied formulas, copied tables, copied figures, and long excerpts.

## Core Idea

Inference engineering depends on model architecture. The same product route can have completely different bottlenecks depending on whether it uses a decoder-only LLM, an embedding model, an encoder-decoder speech model, an MoE model, a diffusion image model, or a video generation model.

For Agent Studio, model records cannot stop at provider and model name. They need architecture, modality, tokenizer/template, context behavior, attention/KV-cache behavior, active-parameter behavior, and known serving bottlenecks.

## Model Architecture As A Serving Contract

The chapter treats architecture as the set of training-time design decisions that determine inference behavior. A model family can have many sizes, variants, and fine-tunes while sharing the same architecture. That matters because runtime support, kernels, cache behavior, and optimization maturity usually follow architecture families.

Agent Studio implication: model registry entries should separate:

- model family and architecture;
- parameter count and active parameter count;
- base, instruct, reasoning, tool-use, or fine-tuned variant;
- tokenizer and chat template;
- modality and output type;
- serving runtime compatibility;
- supported optimization modes.

Fine-tunes and adapters may change behavior without changing architecture. Route compatibility should therefore track both architecture compatibility and behavior/eval compatibility.

## Neural Network Intuition

The chapter gives the minimum architecture intuition needed for inference work: layers transform internal representations, linear layers dominate weight count, activation functions make deep networks useful, and encoders/decoders create or consume representations. LLMs are often decoder-only, while speech, image, and multimodal systems commonly compose encoders, decoders, and other components.

Agent Studio implication: a route graph should be allowed to represent model pipelines, not only single model calls. Image, speech, and multimodal routes often include multiple model stages, each with its own latency, memory, quality, and failure profile.

## LLM Inference Mechanics

LLMs use autoregressive token generation. Input text is tokenized with a model-specific tokenizer and rendered through a model-specific chat template. The model then runs two phases:

- prefill processes the input sequence and builds the KV cache;
- decode generates output tokens one step at a time.

Reasoning models can add hidden intermediate sequences. Tool-using agents can add hidden calls, function schemas, tool outputs, and repair loops. These tokens still consume context and serving budget even if users never see them.

Agent Studio implication: route traces should count input tokens, hidden reasoning tokens, tool-schema tokens, retrieved-context tokens, tool-output tokens, and visible output tokens separately. User-visible latency is not enough to diagnose model-serving cost.

## Sampling And Structured Output

After each decode step, the model produces logits over its vocabulary. Sampling controls such as temperature, top-k, and top-p influence which token is selected. Structured output and tool use may add constraints such as logit biasing, schema decoding, or grammar-guided generation.

Agent Studio implication: sampling and structured-output settings are route artifacts. They should be versioned with prompt/template changes because they alter reliability, determinism, tool-call validity, and latency.

## Attention And KV Cache

Attention relates the current token to prior tokens. In naive form, attention becomes expensive as sequence length grows. In production LLM inference, the KV cache avoids recomputing key/value vectors for prior tokens and makes decode practical, but the cache itself becomes a major GPU-memory and routing concern.

Attention is also quality-sensitive. Small errors in attention can compound across tokens, so attention optimizations need quality checks, not just throughput tests.

Agent Studio implication:

- long-context routes need explicit KV-cache budget and cache-eviction behavior;
- cache-aware routing matters for long conversations, codebase work, and document-grounded agents;
- attention implementation should be stored in the serving profile;
- long-context evals should be separate from short-chat evals.

## Mixture Of Experts

MoE models use many expert subnetworks but activate only a subset per token. This can make single-request inference efficient because fewer parameters are active. In production batching, many different requests may activate different experts, so the system may still need most parameters available across the fleet. Large MoE models introduce expert routing and expert-parallel serving concerns.

Agent Studio implication: MoE model records should store total parameters and active parameters separately. Capacity estimates should not assume active-parameter count alone determines fleet memory or throughput. For high-throughput MoE routes, the serving profile should record expert-parallel strategy and router behavior where available.

## Image Generation Mechanics

Image generation is a pipeline, not one monolithic decoder-only model. A typical text-to-image system includes a text encoder, denoising model, and VAE, plus optional LoRAs, ControlNets, refiners, or other steering components. Diffusion models operate in latent space and usually refine the whole latent representation over many steps.

Agent Studio implication: visual routes need pipeline-level traces. Each component should have model id, adapter id, precision, step count, guidance settings, image size, seed, and postprocessing metadata. A route change may modify one component without changing the whole pipeline.

## Few-Step And Distilled Image Models

Few-step image models trade quality for speed by reducing denoising steps. They can fit realtime or preview use cases where lower quality is acceptable, while higher-step pipelines remain better for final assets.

Agent Studio implication: the studio should distinguish preview routes from final-render routes. Preview routes can use cheaper/faster models or fewer steps; final routes should use quality-oriented settings and stronger review gates.

## Video Generation Mechanics

Video models extend image generation with a time dimension. Modern approaches operate over the whole clip in latent space rather than frame-by-frame to avoid accumulated errors. This makes them extremely compute-heavy; attention across frames and time limits output length and often drives batch size toward one.

Agent Studio implication: video generation should be modeled as a scarce batch workload with explicit queueing, progress state, cost estimates, and retry policy. It should not share realtime text-agent capacity unless the scheduler enforces strict isolation.

## Bottleneck Mapping

The chapter's most useful design pattern is mapping model architecture to expected bottlenecks:

- LLM prefill is usually compute-bound and shapes time to first token.
- LLM decode is usually memory-bandwidth-bound and shapes token speed.
- Image and video generation are usually compute-bound.
- Attention and KV cache dominate long-context behavior.
- Batch size can move bottlenecks by increasing compute per memory movement.

Agent Studio implication: capacity estimates should start with workload shape, not model name alone. The same model can behave differently for short chat, long document QA, code editing, agent planning, and batch synthesis.

## Attention Optimization Families

The chapter separates attention optimizations into implementation improvements and algorithmic changes.

Implementation improvements, such as optimized attention kernels and paged KV-cache management, aim to be lossless and make existing models practical on current hardware. Algorithmic changes, such as sliding-window, compressed, latent, gated, linear, or hybrid attention/state-space approaches, change the model architecture or trained behavior and may trade quality for efficiency.

Agent Studio implication: implementation-level attention changes should still be recorded, but architecture-level attention changes should be evaluated like model changes. Hybrid and non-transformer models need separate long-context, retrieval, and tool-use evals because their failure patterns may differ from standard transformer LLMs.

## Datastore Requirements

Model records should include:

- `architecture_family`: e.g., dense decoder-only, MoE decoder-only, encoder-decoder, diffusion transformer, hybrid state-space/transformer.
- `modality`: text, embedding, image, video, audio, multimodal, or tool-call.
- `tokenizer_template`: tokenizer id, vocabulary family, chat template, stop tokens, tool-call template, structured-output mode.
- `sequence_budget`: max context, max output, hidden-token policy, and modality-specific input size limits.
- `bottleneck_profile`: expected prefill/decode/media bottlenecks, memory bandwidth pressure, KV-cache pressure, and compute pressure.
- `component_pipeline`: encoder, decoder, denoiser, VAE, adapter, ControlNet, refiner, or other stage records.
- `optimization_compatibility`: quantization support, attention kernel support, paged KV support, speculation support, parallelism support, and engine compatibility.
- `quality_eval_contract`: task slices needed before changing architecture, runtime, attention algorithm, precision, or pipeline component.

## Failure Modes

- Treating all generative models like decoder-only LLMs.
- Ignoring tokenizer and chat-template mismatch during model/provider swaps.
- Counting only visible output tokens while hidden reasoning and tool tokens dominate cost.
- Selecting an MoE model from active-parameter count and underestimating production memory/capacity.
- Using short-chat benchmarks to approve long-context routes.
- Applying attention optimizations without checking grounding, recall, and structured-output validity.
- Treating image/video pipelines as single model calls and losing component-level provenance.
- Running video generation like an interactive text route and overwhelming realtime capacity.

## Agent Studio Design Implications

- Extend the model registry with architecture-aware and modality-aware fields.
- Store pipeline components for visual, audio, and multimodal routes.
- Make chat template, tokenizer, and structured-output settings part of route versioning.
- Record hidden-token and KV-cache usage in traces.
- Create separate benchmarks for short chat, long-context retrieval, code editing, image preview, final image render, and video generation.
- Treat architecture-level optimization as a route change requiring eval evidence.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-state-space-transformer-tradeoffs]] - Stanford CS25, "On the Tradeoffs of State Space Models and Transformers" ([YouTube](https://www.youtube.com/watch?v=OyimE74UMF8)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
