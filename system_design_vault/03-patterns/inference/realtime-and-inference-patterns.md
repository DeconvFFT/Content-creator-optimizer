---
type: pattern-note
project: agent-studio-system-design
status: active
updated: 2026-05-23
sources:
  - "[[../../02-lectures/stanford/cs224g-building-scaling-llm-apps]]"
  - "[[../../02-lectures/stanford/cs349d-ai-inference-infrastructure]]"
  - "[[../../02-lectures/stanford/cs25-production-inference]]"
  - "[[../../02-books/applied-ml-ai-engineers/applied-ml-engineering-patterns]]"
  - "[[../../02-books/hands-on-generative-ai/generative-media-pipelines]]"
  - "[[../../02-books/speech-language-processing/rag-dialogue-speech-ie]]"
  - "[[../../02-books/speech-language-processing/chapters/16-asr-and-tts]]"
  - "[[../../01-sources/official-open/gemma4-and-realtime-sources]]"
  - "[[../../01-sources/official-open/speech-dialogue-ie-runtime-governance]]"
  - "[[../../01-sources/official-open/baseten-inference-engineering]]"
  - "[[../../01-sources/official-open/nvidia-dynamo-disaggregated-inference]]"
  - "[[../../01-sources/official-open/vllm-runtime-serving]]"
  - "[[../../01-sources/official-open/ray-serve-llm-production-serving]]"
  - "[[../../01-sources/official-open/huggingface-tgi-continuous-batching]]"
  - "[[../../01-sources/official-open/opentelemetry-genai-observability]]"
  - "[[../../01-sources/official-open/aws-builders-library-resilience]]"
---

# Realtime And Inference Patterns

## Pattern Summary

Realtime voice and expert reasoning are different layers.

Realtime providers own:

- streaming microphone capture,
- turn-taking,
- interruptions,
- spoken output,
- transcript deltas,
- audio deltas and playback state,
- latency-sensitive session control.

Speech/runtime governance adds that every voice route must also preserve audio input conditions, turn-detection mode, transcript confidence, TTS voice/SSML support, provider/version, and privacy boundary before transcript text can drive memory, graph writes, publishing, or external tools.

Speech and Language Processing Chapter 16 adds a lower-level production rule: every voice route needs a declared speech workload slice, audio frontend contract, ASR decoding/finalization policy, CTC/RNN-T or attention model boundary, LM rescoring policy where used, WER plus task-specific error analysis, TTS text-normalization policy, vocoder/voice contract, and listener-quality evidence. Wake words, diarization, speaker identity, and language identification are separate governed tasks, not generic ASR metadata.

The current Agent Studio live-dialogue route is OpenRouter `deepseek/deepseek-v4-flash` for text-turn reasoning over LiveKit transport, with Kokoro providing spoken output. Missing Hugging Face, Gamma, Gemma, or MLX configuration must not block this route.

OpenRouter/LiveKit/Kokoro agents own:

- low-latency text-turn dialogue reasoning,
- LiveKit room/session transport and participant evidence,
- backend event-sink linkage,
- Kokoro spoken replies,
- runtime preflight and same-session proof capture.

## Provider Boundary

The product should expose provider-neutral interfaces:

- `RealtimeSessionProvider`
- `RealtimeAudioProvider`
- `ExpertModelProvider`
- `SpeechToTextProvider`
- `TextToSpeechProvider`
- `RerankerProvider`
- `SearchProvider`
- `ImageGenerationProvider`

Each provider call must record:

- provider id,
- model id,
- dependency timeout/retry/backoff/jitter/idempotency policy,
- latency,
- token/audio duration metrics where available,
- fallback reason,
- cost estimate if configured,
- output hash or artifact id,
- source dependencies.

Realtime and voice calls additionally record session type, connection type, turn policy, safety/user identifier hash where applicable, transcript delta lineage, audio delta lineage, endpointing and interruption events, first transcript/audio timings, cancellation proof, and playback state.

CS224G's realtime voice workshop adds a concrete security and control boundary: browser clients should receive short-lived session credentials, not master API keys, and realtime media lanes should be separated from control/event lanes. Backend sideband control is required when the product must inspect events, enforce privileged state, or run tools outside the client trust boundary.

Local and media-generation calls also need runtime shape: model parameter count, precision, device map or offload policy, image/audio resolution, sequence or audio duration, sampling rate where applicable, and memory ceiling. A route that works with `float16` on one GPU is not proven for CPU, browser, MPS, or batch serving.

Managed AI service calls need a different but equally explicit contract: provider endpoint, API version, model/version policy, network dependency, data boundary, latency profile, metering mode, confidence semantics, fallback path, and drift-review cadence. Containers can reduce latency and behavioral drift by pinning versions closer to the data boundary, but they still need licensing and metering constraints recorded.

## OpenRouter LiveKit Routing

Use OpenRouter as the default managed reasoning boundary for live dialogue, not Hugging Face, Gamma, Gemma, or MLX.

- `deepseek/deepseek-v4-flash`: default live-dialogue reasoning model through OpenRouter.
- LiveKit: realtime room/session transport, participant presence, and data-channel evidence.
- Kokoro: local spoken-output route, waveform generation, and TTS readiness.
- Rust voice edge and backend event sink: local voice pipeline health and durable event linkage.

Gemma/Hugging Face/Gamma/MLX routes may remain as historical source-background or explicit non-default experiments, but they are not the current live-dialogue path.

Native Gemma audio support, if reintroduced later, is an input-understanding capability. It should not be treated as proof that the current OpenRouter/LiveKit/Kokoro route can satisfy low-latency speech output, interruption, playback, or accepted proof-record requirements.

## Realtime Session Types

Separate session families before comparing providers:

- Voice-agent sessions: conversational state, speech-to-speech responses, tool calls, and route events.
- Transcription sessions: streaming transcript deltas without model-generated speech.
- Translation sessions: continuous speech translation that does not use the ordinary assistant turn lifecycle.
- TTS-only streams: text chunks to audio chunks, alignment/timestamps, flush/done, and cancel behavior.

Browser/mobile capture should prefer WebRTC when possible. Server media pipelines can use WebSockets. Telephony requires a separate SIP/phone contract and model-support check.

## Turn Policy

Turn-taking is its own route contract:

- VAD-only: language-flexible and responsive but semantically shallow.
- STT endpointing: uses speech provider phrase boundaries, often with VAD for interruption responsiveness.
- Realtime-provider turn detection: lets the realtime model own server-side VAD/semantic turn detection and interruption signaling.
- Manual turn control: push-to-talk or explicit start/end/cancel/commit operations.

Each policy must record endpointing delays, interruption behavior, noise cancellation, provider-specific settings, and known failure modes. A latency number without turn policy is not comparable.

## Latency Budget

Define budgets per task:

- Voice turn first response: sub-second to low-single-digit seconds depending on provider path.
- Search/retrieval planning: seconds, with streamed timeline.
- Deep research/content synthesis: minutes, resumable.
- Human feedback gates: indefinite wait, resumable from checkpoint.

## Production Inference Workload Classes

CS25 production-inference coverage, Modal's serving guidance, and Baseten's inference-engineering source map sharpen this split: throughput, low latency, and bursty workflows are different serving problems. They also sit at different layers of the stack: runtime, infrastructure, and tooling.

- Throughput routes handle ingestion, eval scoring, backfills, batch critique, and source refresh. They can queue and batch aggressively.
- Low-latency routes handle chat, realtime-adjacent reasoning, and human review. They need TTFT, TPOT, streaming, region, and decode bottlenecks measured directly.
- Bursty workflow routes handle occasional deep synthesis, media generation, or revision bursts. They need cold-start, snapshot, prewarm, and fallback policy.

Do not promote one serving route as "production-ready" for all three classes.

## Inference Contract

Before a route is optimized or moved to dedicated serving, it needs an explicit inference contract:

- use case and workload class;
- latency budget, cost budget, and quality floor;
- modality and preprocessing/output contract;
- model architecture and context/cache assumptions;
- runtime engine and container/provider choice;
- hardware/capacity pool and fallback pool;
- observability and rollback gates.

Optimization techniques such as quantization, speculative decoding, KV reuse, model parallelism, and disaggregation are candidate changes, not defaults. Each one needs workload-specific measurement and quality regression checks before it can replace a baseline route.

Natural Language Processing with Transformers Chapter 8 adds the small/medium transformer deployment version of the same rule. Distillation, dynamic quantization, ONNX/ORT export, and pruning are not interchangeable "make it faster" switches. The route should record teacher/student lineage for distillation, precision and layer scope for quantization, opset/execution-provider/equivalence checks for runtime export, sparse-kernel support for pruning, and benchmark deltas for quality, latency, size, memory, cost, and failure slices.

Promote a served model route only after an `inference_workload_release_gate` proves workload class, input/output length distributions, concurrency, streaming and queueing assumptions, SLO, phase measurements, runtime/provider, GPU or accelerator choice, precision/quantization, cold-start posture, endpoint contract, representative benchmark, quality/grounding/safety regression checks, background-starvation behavior, fallback, and rollback.

CS349D adds a serving-engine compatibility ladder: parallelism, continuous batching/PagedAttention, context caching/chunked prefill, and advanced features such as speculation or prefill-decode disaggregation must remain compatible. Agent Studio should treat each serving feature as a release surface with fixture tests, phase metrics, and rollback gates.

Promote serving feature stacks only after a `serving_feature_stack_release_gate` proves workload profile, runtime and endpoint contracts, milestone order, feature compatibility matrix, parallelism, batching, KV/cache, chunked-prefill, speculation, hierarchical-cache, and disaggregation policies, phase metrics, p50/p95/p99 latency, throughput, memory pressure, cache hit rate, cost delta, quality/citation regressions, tenant/rights cache boundaries, fairness/starvation review, fallback runtime, and rollback trigger.

## Disaggregated And KV-Aware Serving

NVIDIA Dynamo sharpens the serving contract for long-context, source-heavy, and agentic workloads. Prefill and decode can be separate serving lanes with different bottlenecks, replica counts, parallelism assumptions, and scale policies. KV cache is also a routable resource: a route can reduce redundant prefill by sending repeated or overlapping context to workers that already hold useful cache state.

Agent Studio should use these techniques only when the route has measured evidence:

- prefill, decode, queue, cache-transfer, cold-start, and end-to-end timings;
- input/output length distributions, not only max context;
- KV hit, miss, eviction, and reuse-boundary signals;
- cache-aware routing fairness across urgent and cache-friendly work;
- TTFT and TPOT targets for the specific workload class;
- scale-down and in-flight request behavior;
- fallback from KV-aware routing to simpler routing when cache events are stale or unavailable.

For book ingestion, eval replay, artifact review, and source-backed drafting, KV reuse can be valuable because many tasks share stable source packs. For realtime voice, a long source prefill should not block decode or audio responsiveness; deep synthesis should remain outside the realtime critical path unless the route proves it can satisfy the latency budget.

## vLLM Runtime Serving

vLLM makes the runtime contract concrete: an OpenAI-compatible endpoint can still have runtime-specific sampling defaults, request parameters, tokenizer/chat-template assumptions, KV cache behavior, prefix caching, quantization support, speculative decoding knobs, disaggregated prefill topology, and metrics. Agent Studio should therefore store a `vllm_runtime_profile` beside the general serving profile, not collapse vLLM into a generic provider string.

For source-heavy workloads, prefix caching and PagedAttention make repeated stable context cheaper only when route boundaries are safe. Cache keys need tenant, source snapshot, route version, model/tokenizer, and rights scope; traces need hit/miss, eviction, KV pressure, waiting reason, queue, prefill, decode, TTFT, and inter-token evidence without storing prompt or cache contents.

Quantization, speculative decoding, KV-cache dtype, CUDA graphs, and disaggregated prefill are optimization candidates. Each requires workload-specific latency, memory, throughput, and quality-regression gates before promotion.

vLLM-backed route promotion needs a dedicated serving release gate. The gate should prove endpoint contract, model/tokenizer/chat-template snapshot, generation-config policy, engine/server argument snapshots, batching and KV/PagedAttention behavior, prefix-cache boundary, quantization/KV dtype, speculative decoding profile where enabled, disaggregated-prefill topology where enabled, compatibility matrix, workload benchmarks, metric snapshots, quality and source-grounding deltas, capacity/admission policy, fallback mode, and rollback target.

## Ray Serve Production Serving

Ray Serve LLM adds a deployment layer between product routes and low-level inference engines. It is useful when Agent Studio needs OpenAI-compatible endpoint shape, application-level autoscaling, multi-node serving, custom routing, KubeRay RayService lifecycle, model/adaptor multiplexing, and explicit deployment status in one serving substrate.

Use it as a route substrate only when the route has:

- an endpoint contract separate from the serving deployment and inference engine;
- Serve deployment/resource/autoscaling config recorded as release metadata;
- KubeRay RayService health, status, upgrade, and rollback evidence if deployed on Kubernetes;
- adapter/model multiplexing policy with load, eviction, fairness, and per-adapter eval evidence;
- separate Serve-level autoscaling and cluster/node autoscaling telemetry;
- OpenAI-compatible smoke tests that prove this endpoint behaves correctly for streaming, errors, tokenizer/context behavior, tool expectations, and route-specific regression slices.

This is especially relevant for batch critique, source ingestion, eval workers, and specialist LoRA/adaptor routes. It should not be put on the realtime audio critical path unless first-audio/turn-taking SLOs are proven under traffic and cold/warm states.

Ray Serve-backed route promotion needs a serving-platform release gate. The gate should prove Serve application identity, deployment graph/config version, endpoint contract, RayService or VM deployment status, Serve and cluster autoscaling policies, resource/placement assumptions, model/adaptor multiplexing policy, adapter provenance and eval slices, serving-engine contract, OpenAI-compatible smoke tests, health/status evidence, load-test slices, metrics/observability wiring, upgrade strategy, fallback route, and rollback target.

## TGI And Continuous Batching

Hugging Face TGI and Transformers continuous batching make the runtime-level serving contract explicit. A route is not just "served by Hugging Face"; it has token limits, batch-token limits, scheduler policy, queue pressure, prefill/decode split, KV cache behavior, prefix-cache eligibility, dtype/quantization, speculation, endpoint compatibility, Prometheus metrics, and OpenTelemetry tracing.

Because Hugging Face now marks TGI as maintenance mode and recommends vLLM or SGLang for Inference Endpoints, Agent Studio should treat new TGI adoption as an exception or legacy route, not the default open-model serving choice. Promotion requires:

- token and batch limit metadata for max input, generated, total, batch-prefill, and batch-total tokens;
- phase metrics for validation, queue, prefill, decode, inference, streaming, and end-to-end latency;
- input/output token distributions for the actual workload slice;
- KV cache admission, prefix-cache hit/miss, offload, and soft-reset evidence;
- scheduler selection rationale for long-prompt, short-chat, eval, and ingestion workloads;
- optimization experiments for quantization, KV dtype, speculation, CUDA graphs, async batching, CPU offload, and custom kernels.

Continuous batching is high-leverage for throughput routes, but it can also hide tail latency and fairness problems. Source ingestion, eval replay, source-backed drafting, and realtime-adjacent chat should have separate queue and scheduling policies.

TGI-backed route promotion needs a serving release gate. The gate should prove runtime adoption or migration justification, model/container revision, endpoint compatibility, token and batch limits, scheduler/continuous-batching policy, KV/cache admission behavior, prefix-cache boundary, quantization/KV dtype/speculation settings, launcher argument snapshot, phase-level metrics, workload benchmark, quality/source-grounding deltas, autoscaling/admission policy, observability wiring, fallback to vLLM/SGLang/managed endpoint where appropriate, and rollback target.

## Media Runtime Contracts

Generated media and audio routes have workload-specific constraints:

- diffusion image generation is controlled by scheduler, inference steps, guidance, seed, dimensions, VAE/latent representation, and adapter/control modules;
- audio routes depend on sampling rate, channel count, duration, representation type, decoder or vocoder, and whether the route must be realtime;
- local inference capacity depends on parameter count, precision, activation/context memory, media resolution, batch size, and offload strategy;
- browser/local routes need a separate `local_runtime_profile`, because privacy and latency benefits can disappear if memory pressure forces slow offload.

## Agent Studio Implications

- Provider-free rehearsal is useful for UI and event contracts but cannot count as real provider smoke.
- Provider-backed smoke must produce non-rehearsal realtime sessions, transcript turns, provider readiness, and event evidence.
- Provider-backed smoke must prove first transcript delta, first audio delta, endpointing, interruption/cancellation, and fallback behavior for the chosen session type.
- Realtime route release should also prove ephemeral-token issuance, media/control-channel separation, reconnect behavior, and sideband server-control behavior when privileged tools or state are involved.
- Deep synthesis should run outside the realtime audio critical path when possible.
- Inference routes must declare workload class and measure prefill, decode, queue, cold-start, retrieval, rerank, tool, and end-to-end latency separately.
- Cost, cache, quota, and degradation policy should be promoted through [[cost-latency-budget-control]] before serving traffic scales; latency wins that depend on unbounded budget, shared cache leakage, or silent provider fallback are not production wins.
- Disaggregated serving routes must also declare prefill/decode lanes, KV-cache policy, cache-transfer telemetry, router fallback, and scale-down behavior.
- Ray Serve routes must also declare Serve application/deployment identity, RayService rollout status when on Kubernetes, application autoscaling policy, cluster placement assumptions, model/adaptor multiplexing policy, endpoint smoke evidence, and engine contract.
- TGI routes must also declare runtime profile, maintenance/migration posture, token/batch limits, scheduler policy, KV/cache admission policy, prefix-cache boundary, phase-level metrics, optimization flags, and fallback target.
- GenAI observability should record operation name, provider, requested model, response model, streaming flag, first-chunk latency, finish reason, token usage, cache usage, and reasoning-token usage where available, while keeping prompt/output bodies behind explicit content-capture policy.
- Interactive, batch, media, MCP/browser-tool, and eval workloads need separate concurrency pools and retry budgets. A slow image route, source-refresh job, or external tool must not starve realtime voice or artifact review.
- Runtime engine, GPU type, precision, batching policy, region, snapshot/prewarm policy, and endpoint contract are route metadata, not deployment afterthoughts.
- Inference source provenance should stay linked to route decisions: Baseten official source map, local chapter notes, CS336/CS25 serving notes, and runtime provider docs answer different parts of the same release question.
- Provider readiness should separate real provider smoke from dry UI rehearsal: credentials/config, quota/capacity assumptions, endpoint health, first-token or first-audio proof, quality gate, fallback path, and last verification time.
- Voice and audio generation routes must store sampling-rate and representation contracts before they are used for realtime or video workflows.
- Speech routes must store ASR and TTS as separate evidence surfaces: transcript confidence, WER/CER slice, endpointing/barge-in events, text-normalization policy, MOS or pairwise TTS preference evidence, and retention/redaction policy. Streaming partial transcripts should not overwrite final transcript evidence.
- Promote realtime speech, dialogue-state, or extraction-backed graph routes only after a speech/dialogue/IE release gate proves provider/API version, credential boundary, audio configuration, turn and interruption policy, transcript-finalization policy, ASR/TTS eval slices, first-transcript/first-audio timings, realtime tool/MCP exposure, dialogue-state policy, extraction pipeline version, offset encoding, entity/coreference candidate policy, graph-write review policy, privacy/retention posture, bias slice checks, fallback mode, and rollback target.
- Media generation should be benchmarked by route class: text-to-image, image edit, audio ASR, TTS, text-to-audio, and video/media postprocessing have different latency and memory profiles.
- Managed OCR, moderation, vision, speech, and language APIs are provider routes, not utility calls; each needs version, drift, latency, data-boundary, and fallback evidence before promotion.
- The current live-dialogue voice stack is a provider-backed half-cascade: OpenRouter `deepseek/deepseek-v4-flash` for dialogue reasoning, LiveKit for WebRTC/data-channel transport, Kokoro-82M for speech waveform output, Python for orchestration, and Rust for VAD/buffer/barge-in edge behavior. `OPENROUTER_LIVEKIT_URL=ws://127.0.0.1:7880` is the local dev transport URL.
- Open/local TTS routes such as Kokoro need the same provider evidence as managed TTS: voice/model rights, G2P/text normalization, sample rate, alignment limits, first-audio latency, and quality evals.
- Rust voice edge now has an Axum/Tokio HTTP sidecar as well as persistent JSONL. Python selects HTTP when `RUST_VOICE_EDGE_HTTP_URL` is configured, checks `/healthz` before voice-agent readiness, wraps it with JSONL fallback when the binary is executable, and otherwise uses JSONL as the current frame-loop bridge. JSONL also preflights before readiness by starting the persistent process and sending a harmless cancellation contract. `silero_onnx` now runs real Rust Silero ONNX inference through the bundled `silero` crate model or a configured ONNX file; `deterministic_energy` remains the default and fallback path. Silero ONNX sessions are cached in a bounded process-wide pool keyed by normalized model source and session id, with LRU-style custom-model eviction, pool-size-aware keys, and bounded recurrent `StreamState` caches keyed by stream id and sample rate. The voice-edge benchmark now records concurrent stream probes, can target HTTP via `--http-url`, can use local 16-bit PCM WAV corpora via repeated `--speech-wav` or recursive case-insensitive `--speech-wav-dir`, fails fast on bad corpus/threshold inputs and synthetic-only sweeps, and can run Silero probability threshold sweeps over the same fixtures. Treat HTTP as the supervised request/response sidecar contract until benchmarked concurrency tuning and the direct LiveKit media bridge land.
- Voice readiness should be product-visible, not only operator-visible. `GET /api/voice-runtime-readiness` exposes non-secret readiness for LiveKit transport, LiveKit agent participant, backend event sink, OpenRouter live-dialogue reasoning, Kokoro TTS, Rust edge, and context pruning; the Next product app renders all checks, runs a full Runtime preflight with Rust edge proof before LiveKit join, and must not disable the current OpenRouter/LiveKit/Kokoro path because Gemma/HF/Gamma/MLX is missing.
- Runtime construction is not participant presence. Product UX should require a durable same-session agent-ready observation for the run/session before claiming that the OpenRouter/Kokoro LiveKit agent is actually present. The current contract is `GET /api/runs/{run_id}/voice-agent-presence`, backed by persisted LiveKit data-channel events, with explicit `ready`, `stale`, and `missing` states plus room, expected agent identity, actual LiveKit sender identity, optional `probe_id` challenge-response binding, and a freshness window. The browser sends a presence probe after LiveKit room join; the Python agent replies over `agent.voice.event`; the frontend persists the event before the panel reports participant proof.
- Local process supervision is a developer/operator convenience, not voice proof. The product can expose Start/Stop/status for the local `all-about-llms-admin run-voice-agent` process so a local-first user is not forced into hidden terminal orchestration, but that status only proves a process attempt. The release gate remains readiness plus durable LiveKit participant presence plus provider smoke/timing proof. Process log tails must be bounded and secret-redacted before they are shown in the product UI, and stop/exit races should return stable status envelopes with typed control errors rather than surfacing transport exceptions to the creator.
- Provider-backed voice proof should be product-visible too. The creator app now exposes dry voice-only provider smoke and realtime voice timing ledgers in the same voice surface. Live provider smoke stays opt-in so configured credentials are not called accidentally; dry smoke records blockers for OpenRouter, LiveKit, Kokoro, Rust edge, backend event sink, and missing correlated timing evidence.
- Live voice media events should feed the durable conversation state and the A2A work queue, not only timing ledgers. The current bridge materializes `voice_user_turn_committed` into a user voice turn with pending transcript status when needed, materializes `assistant_response_completed` into an assistant voice turn with OpenRouter/Kokoro text, enqueues a Realtime Conversation Host follow-up task for newly materialized assistant completions, and refreshes the Next dialogue view from the materialized turn id returned by the event API.
- Realtime Conversation Host briefs should not be terminal artifacts. The host now materializes recommended handoffs as deterministic insert-if-absent A2A child tasks, so a live voice exchange can activate intent routing, audio/realtime review, product control resolution, or user-feedback translation while retaining retry idempotence.
- The voice-to-content route must be tested as a chain, not isolated handlers. Current regression proof exercises Realtime Conversation Host -> Intent Router -> Content Strategist -> downstream workers, showing that a finalized voice transcript about a source-backed post/reel/Substack can produce seed drafts plus writer, data, audio, video, distribution, influencer, editorial, and artifact work. Content Strategist creates deterministic seed post/reel/Substack artifacts scoped to the content-strategy handoff, reloads message-scoped seeds after insert-if-absent conflicts before child fanout, marks them non-publishable with `needs_web_research_before_publish` unless explicit source/claim lineage exists, then pins downstream child tasks to those seed ids; this gives writer/media workers durable turn-specific inputs while source research and verification remain required before publishing. Direct existing-content strategy tasks pass explicit artifact ids rather than relying on run-wide writer fallback selection, and ambiguous same-format existing drafts are rejected until explicit target ids are supplied. Intent Router route-plan artifacts and child tasks use deterministic insert-if-absent writes, while Content Strategist child fanout uses deterministic insert-if-absent task ids so worker replays do not fork duplicate content pipelines.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.

- [[../../02-lectures/stanford/cs25-state-space-transformer-tradeoffs]] - Stanford CS25, "On the Tradeoffs of State Space Models and Transformers" ([YouTube](https://www.youtube.com/watch?v=OyimE74UMF8)).
- [[../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
