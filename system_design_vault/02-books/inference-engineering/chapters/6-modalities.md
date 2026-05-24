---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Inference Engineering"
authors: "Philip Kiely"
chapter: "6"
chapter_title: "Modalities"
source_path: "/Users/saumyamehta/DS interview prep/books/Inference Engineering.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 6 - Modalities

## Reading Status

Direct source reading pass completed for chapter 6 from the local user-provided PDF extraction span. Promoted to `canon_ready` after official/open cross-check against Stanford CS336, NVIDIA Dynamo, TensorRT-LLM, vLLM multimodal/offline inference, and production serving/runtime docs. This note is original synthesis only; it avoids raw text dumps, copied modality tables, copied figures, and long excerpts.

## Core Idea

Modality changes inference. Text generation, vision-language reasoning, embeddings, ASR, TTS, speech-to-speech, image generation, and video generation have different latency metrics, bottlenecks, pipelines, quality tests, and serving architectures.

For Agent Studio, a route cannot be described only as "model call." It needs modality, input/output types, pipeline stages, metric family, runtime constraints, and quality gates. This is especially important for content-studio workflows where one user task may combine text, image, video, voice, retrieval, and embeddings.

## Modality Archetypes

The chapter reduces many modalities to two broad inference archetypes:

- autoregressive token generation, used by LLMs and many text/audio/multimodal models;
- iterative denoising, used by most image and video generation systems.

Even when modalities share transformer ancestry, their operational metrics differ. For speech synthesis, the first useful unit may be a byte, word, or sentence rather than a text token. For image generation, latency tracks denoising steps and component pipeline time. For video, the main constraint is compute across a full clip latent space.

Agent Studio implication: each route should declare its metric family. TTFT/TPOT is not enough for audio, embeddings, image, or video.

## Vision Language Models

VLMs combine an LLM with a vision encoder that turns images or video into visual tokens. The LLM often dominates parameter count, but the vision encoder and visual tokenization path are critical for runtime support and latency. High-resolution images and video clips increase input sequence length, which increases prefill work and KV-cache pressure.

Relevant optimization levers include KV-cache quantization, speculation during decode, prefix caching for repeated images or multi-turn conversations, tensor parallelism for larger models and contexts, disaggregated prefill for long visual inputs, and downsampling when the route can tolerate less detail.

Agent Studio implication:

- VLM routes need visual-token budgets and image/video preprocessing records;
- downsampling should be a route setting with quality evidence;
- repeated image/document/video contexts should be cacheable;
- video-understanding routes may need separate ASR or OCR preprocessing before the VLM call.

## Omni And Pipeline Models

Omni models blend multiple input and output types, but specialized models can still be faster and more accurate for narrow tasks. Production multimodal systems often use pipelines: OCR for images, PDF extractors for documents, ASR for video audio, embedding models for retrieval, and VLMs for visual reasoning.

Agent Studio implication: multimodal workflows should be represented as pipeline graphs with per-stage traces. A single "multimodal model" node hides too much when latency, accuracy, or cost fails.

## Embedding Models

Embedding models convert variable-length input into fixed-length vectors for search, RAG, memory, recommendations, and similarity. They have two distinct serving profiles:

- high-throughput backfills for indexing or refreshing corpora;
- low-latency lookups for online retrieval and recommendations.

BERT-style encoder models remain useful for small latency-sensitive tasks, while LLM-backbone embedding models often deliver stronger semantic quality. Dimensionality affects vector storage and retrieval cost more than model inference time. Vectors from different embedding models usually live in incompatible semantic spaces.

Agent Studio implication:

- separate online embedding lookup routes from offline embedding backfill routes;
- store embedding model id, vector dimension, normalization, truncation policy, and semantic-space version with every vector;
- never mix vector indexes from different embedding models without explicit migration;
- evaluate quantized embedding outputs with similarity and retrieval-quality checks.

## ASR Models

ASR maps audio to text. Whisper-style systems use an encoder-decoder architecture where the decoder is autoregressive and can use LLM-style optimizations. Real-time transcription is mostly an orchestration problem: stream audio, segment with voice activity detection, process chunks, and stream text back.

Long-file transcription is a different workload. It benefits from meaningful audio chunking, parallel chunk processing, timestamp stitching, hallucination detection, and repair by rerunning or rechunking suspect segments.

Diarization is adjacent but different. It is usually a classic ML pipeline with segmentation, embedding, and clustering stages, not the same model class as transcription.

Agent Studio implication:

- voice input routes should include VAD, chunking, ASR, optional diarization, and transcript repair as separate pipeline stages;
- real-time ASR should optimize round-trip chunk latency;
- long-file ASR should optimize real-time factor, throughput, and stitch quality;
- diarization needs its own quality and latency records.

## TTS And Speech-To-Speech

Modern open TTS models often use LLM-like backbones with audio tokens and a separate audio decoder that converts generated tokens into waveforms. TTS routes measure time to first byte, time to first meaningful phrase/sentence, token speed, and concurrent real-time streams. Once token generation is fast enough for realtime audio, extra speed matters mainly for concurrency and cost.

Cascading voice agents use ASR, LLM, and TTS as separate stages, often with VAD and retrieval/embedding support. Speech-to-speech models aim to combine audio input, reasoning, and audio output in one model; at the source's publication time, the chapter treated this as an emerging route that still needed modality-specific inference engineering.

Agent Studio implication:

- realtime voice routes should track ASR latency, LLM latency, TTS latency, first audio byte, first sentence, interruption handling, and stream stability separately;
- cascading and unified speech-to-speech routes should be comparable through end-to-end conversational latency and quality;
- TTS long-form generation should be chunked because quality can degrade on long inputs.

## Image Generation

Image generation differs from LLM serving in architecture, tooling, metrics, and quality evaluation. Most image systems are iterative denoising pipelines with text encoder, denoiser, VAE, and optional adapters or control components. They are usually compute-bound and expose direct speed-quality controls such as step count, guidance behavior, resolution, and few-step/distilled models.

High-performance image inference may use SGLang Diffusion, TensorRT, or carefully optimized PyTorch. Attention kernels, normalization fusion, GEMM kernels, quantization, and compile caching can matter. Human visual preference remains difficult to replace with automatic metrics.

Agent Studio implication:

- image routes should separate preview from final-render profiles;
- image-generation traces need prompt, negative prompt, seed, size/aspect, step count, guidance settings, component model ids, adapters, and postprocessing;
- automatic VLM scoring can help but should not be treated as full visual-quality truth;
- speed-quality tradeoffs should be route settings with review evidence.

## Video Generation

Video generation is the most demanding modality in the chapter. It is usually compute-bound, often runs across a full multi-GPU node, and may use batch size one because all GPUs collaborate on a single clip. Modern video models operate over a full video latent space rather than frame-by-frame, which improves coherence but makes attention extremely expensive.

Optimization focuses on attention kernels, caching across timesteps or transformer layers, selective quantization, and context parallelism. Quantizing video attention is risky because errors can accumulate through generation, so step/layer-specific precision policies need careful validation.

Agent Studio implication:

- video routes should be scarce batch jobs with explicit queueing, progress, cost estimates, and retry/resume behavior;
- video generation should not compete with realtime text/voice routes for capacity unless scheduling isolation is enforced;
- route records should store context-parallel plan, quantization policy, denoising steps, clip length, resolution, and quality-review status.

## Datastore Requirements

Multimodal route records should include:

- `modality_contract`: accepted input types, output types, metric family, realtime/batch mode, and user-visible artifacts.
- `pipeline_stage`: stage id, model id, modality, runtime, input/output schema, latency budget, and quality gate.
- `preprocessing_record`: image resizing/downsampling, OCR, PDF extraction, VAD, audio chunking, frame sampling, transcript stitching, and media normalization.
- `embedding_space`: model id, vector dimension, normalization, truncation, index version, corpus snapshot, and compatibility policy.
- `voice_trace`: VAD events, ASR chunks, transcript repair, LLM turn, TTS chunks, first audio byte, first sentence, interruption, and stream health.
- `image_trace`: seed, resolution, steps, guidance, adapters, ControlNet/refiner components, compile/runtime path, and review outcome.
- `video_trace`: clip duration, frame/sample policy, denoising steps, context-parallel plan, attention/cache policy, quantization policy, queue time, and progress state.

## Failure Modes

- Applying text-generation metrics to every modality.
- Sending long visual/video inputs without visual-token budgeting.
- Treating omni models as always better than specialized pipelines.
- Mixing embeddings from incompatible models or dimensions.
- Letting offline embedding backfills consume online retrieval capacity.
- Optimizing ASR for long-file throughput while hurting real-time chunk latency, or vice versa.
- Treating diarization as part of ASR instead of a separate pipeline.
- Measuring TTS token speed while ignoring first meaningful audio and stream stability.
- Treating image/video quality as fully automatable with generic model judges.
- Running video generation as if batch size and horizontal scaling work like text generation.

## Agent Studio Design Implications

- Add modality-specific route templates for text, embedding, VLM, ASR, TTS, image, and video.
- Represent multimodal work as pipeline graphs with per-stage traces.
- Split preview and final-generation routes for visual media.
- Keep online and offline embedding systems separate when volume justifies it.
- Add voice-specific end-to-end latency telemetry for realtime agents.
- Treat video generation as queued scarce capacity with explicit progress state and cost reporting.
- Store modality-specific eval and review requirements before promoting a route to canon.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-state-space-transformer-tradeoffs]] - Stanford CS25, "On the Tradeoffs of State Space Models and Transformers" ([YouTube](https://www.youtube.com/watch?v=OyimE74UMF8)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
