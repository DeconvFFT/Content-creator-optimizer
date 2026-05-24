---
type: lecture-note
project: agent-studio-system-design
status: canon_ready
source_title: "Stanford CS25 Transformers United V6"
lecture_title: "Serving Transformers: Lessons from the Trenches of Production Inference"
speaker: "Charles Frye, Modal"
source_status: official_public_listing_plus_modal_docs
updated: 2026-05-18
sources:
  - https://web.stanford.edu/class/cs25/
  - https://web.stanford.edu/class/cs25/recordings/
  - https://modal.com/docs/guide/high-performance-llm-inference
  - https://modal.com/docs/guide/gpu
  - https://modal.com/docs/examples/trtllm_throughput
related:
  - "[[cs25-ultra-scale-training]]"
  - "[[../../03-patterns/inference/realtime-and-inference-patterns]]"
  - "[[../../03-patterns/transformer-systems/cs25-transformer-systems-canon]]"
  - "[[../../04-agent-studio-implications/Capacity Estimation - Adaptation and Serving Decisions]]"
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# CS25 - Production Inference

## Reading Status

Direct read of the official Stanford CS25 V6 listing for the May 28 production-inference talk, the CS25 recordings page, and current Modal documentation for high-performance LLM inference, GPU selection, and a TensorRT-LLM serving example. Current-source check on 2026-05-18 confirmed the CS25 listing, recordings-page visibility boundary, and Modal docs. The public recordings page does not currently expose this lecture as a selected public recording in the visible page text, so this note does not claim video-level coverage and stores no transcript, slide text, copied code, or long excerpts.

## Why This Matters

Training creates a model; inference creates the product. Agent Studio is a long-running multi-agent content system, so inference design has to distinguish interactive human latency, background ingestion throughput, bursty workflow steps, media generation, realtime voice, and eval/backfill jobs. These are not one serving problem.

The main design lesson: serving profiles should be workload-specific. A route optimized for batch throughput can be wrong for voice. A route optimized for low latency can waste money for backfills. A route optimized for bursty serverless traffic can behave differently from always-warm production serving.

## Three Inference Workload Classes

Modal's current inference guidance usefully separates high-throughput, low-latency, and bursty workloads.

Agent Studio should model the same split:

| Workload | Product examples | Dominant concern | Route implication |
|---|---|---|---|
| High throughput | source backfills, embedding refresh, offline eval scoring, batch critique | tokens or tasks per second | maximize batching, accept queueing, optimize prefill-heavy work |
| Low latency | chat, critique, realtime voice-adjacent reasoning, human-in-the-loop review | TTFT, TPOT, perceived latency | stream, reduce decode bottlenecks, avoid cold paths |
| Bursty workflow | occasional deep synthesis, review workflows, user-triggered media generation | cold start and peak-to-average ratio | autoscale, snapshot, prewarm, and choose when to keep replicas warm |

This split should be visible in `serving_profile`, `route_registry_entry`, and eval gates.

## Prefill, Decode, And Bottleneck Diagnosis

Transformer inference has at least two distinct phases:

- prefill/prompt processing over the input context;
- decode/token generation over the output sequence.

Long-context batch jobs can be prefill-heavy and compute-bound when batching is high enough. Interactive chat can be decode-heavy and memory-bandwidth-bound because tokens are generated serially. These phases require different optimizations and hardware choices.

Agent Studio implication: store prefill time, decode time, retrieval time, rerank time, tool time, and end-to-end latency separately. A single "latency" field hides the bottleneck.

## Throughput Routes

For offline or async work, the system can batch aggressively. This is appropriate for:

- ingestion transforms;
- source classification;
- OCR post-processing;
- offline eval scoring;
- candidate critique at scale;
- recurring quality audits.

Throughput routes should prioritize GPU utilization and queue health over immediate response. The datastore should store batch size, queue wait, input length distribution, output length distribution, tokens/sec, tasks/sec, GPU utilization, and failure/retry behavior.

## Low-Latency Routes

For interactive work, perceived latency matters. Streaming can make a long generation tolerable by reducing time to first useful output, but it does not remove the serial decode cost. Smaller models, quantization, speculative decoding, tensor parallelism, regional deployment, and low-overhead servers can all help, but they change quality, cost, and operational complexity.

Agent Studio implication: low-latency route changes must be evaluated on the actual interaction surface. A voice-adjacent route needs first-response and interruption behavior; a review route needs time-to-useful-critique; a chat route needs TTFT and TPOT. Do not reuse a batch-serving benchmark as proof of interactive readiness.

## Bursty Workflow Routes

Agent Studio has many bursty workloads: a user starts a deep research job, launches a media pipeline, or requests a batch of revisions after minutes of inactivity. Keeping maximum capacity warm is wasteful; starting from zero can be too slow.

Cold-start strategy should be explicit:

- model size and load path;
- image/container startup;
- dependency and compilation cost;
- model storage path;
- memory or GPU snapshot policy;
- prewarm or minimum replica policy;
- fallback route when cold-start exceeds budget.

Snapshotting and serverless autoscaling can help, but they are not free. They add operational assumptions and should be recorded in the route's serving profile.

## Hardware And Runtime Selection

Modal's GPU guidance reinforces a practical point: the most expensive accelerator is not always the best choice. Small-batch language-model inference can be memory-bound rather than arithmetic-bound, and software support can matter as much as peak hardware specs. New hardware may have higher raw capability but less mature kernels.

Agent Studio should record:

- GPU type and memory;
- precision/quantization;
- runtime engine such as vLLM, SGLang, TensorRT-LLM, hosted API, or managed provider;
- batching/concurrency policy;
- context and output length assumptions;
- cold-start and warm-path measurements;
- region/network path for interactive routes.

## API Surface And Deployment Evidence

The Modal TensorRT-LLM example shows the production path from core inference function to web/API endpoint. The lesson for Agent Studio is not the copied code; it is the deployment evidence. A production route should have a callable endpoint or provider route, request/response schema, auth boundary, observability, and smoke-test trace.

For external or public-facing routes, add:

- input schema;
- output schema;
- auth and approval requirements;
- rate limits;
- error and retry policy;
- structured logs with redaction;
- endpoint health evidence;
- rollback route.

## Failure Modes

- A route uses the same model/server for batch ingestion and interactive chat, making both worse.
- A benchmark reports tokens/sec while the product problem is TTFT or cold start.
- A route optimizes decode speed but retrieval/reranking/tool calls dominate end-to-end latency.
- A serverless route cold-starts too slowly for a human workflow.
- A larger GPU is chosen even though the bottleneck is memory bandwidth, host overhead, queueing, or network path.
- Quantization improves latency but silently harms grounding, style, or safety on the route's eval slice.
- Production smoke tests hit a toy prompt instead of representative context and output lengths.
- API routes expose inference without schema, auth, redaction, or rollback evidence.

## Agent Studio Design Implications

1. Create serving profiles by workload class: realtime, interactive, batch, background, media, and bursty workflow.
2. Measure TTFT, TPOT, TTLT, prefill, decode, retrieval, rerank, tool, queue, cold-start, and end-to-end latency separately.
3. Treat runtime engine, GPU type, precision, batching, region, and snapshot/prewarm policy as versioned route metadata.
4. Require route-specific quality evals after quantization, speculative decoding, runtime migration, or hardware migration.
5. Use queue-based async inference for ingestion/eval/backfill work instead of forcing it through interactive routes.
6. Keep endpoint schema, auth, observability, redaction, rate limits, and rollback attached to each served route.
7. Use representative workload slices before promoting a route: real context lengths, output lengths, source retrieval, tool calls, and media constraints.

## Datastore Implications

Add or strengthen these records:

- `serving_workload_profile`: workload class, interaction mode, concurrency, input/output length distribution, streaming support, and SLOs.
- `inference_phase_measurement`: prefill, decode, retrieval, rerank, tool, queue, cold-start, and end-to-end latency by route and workload slice.
- `runtime_engine_record`: engine/provider, version, precision, quantization, batching policy, cache behavior, supported modalities, and caveats.
- `gpu_capacity_record`: GPU type, memory, bandwidth class, region, fallback list, cost rate, and compatibility assumptions.
- `cold_start_record`: image startup, model load, compilation, snapshot/prewarm policy, warm-path/cold-path measurements, and fallback route.
- `endpoint_contract_record`: endpoint URL or provider route, input/output schema, auth boundary, rate limits, redaction policy, health check, and rollback route.
- `serving_regression_eval`: quality, grounding, safety, latency, cost, and failure slices after runtime, quantization, batching, or hardware changes.
- `inference_workload_release_gate`: route promotion gate proving workload class, SLO, phase metrics, runtime/hardware choice, cold-start posture, endpoint contract, representative benchmark, quality regression, fallback, and rollback.

## Release Gate Contract

`inference_workload_release_gate` is required before a model route can become a foreground, background, batch, media, or realtime-adjacent serving path.

The gate should reject promotion unless:

- the workload class is declared as interactive, realtime-adjacent, batch, background, media, or bursty workflow;
- input length, output length, concurrency, streaming, queueing, and SLO assumptions match the product surface;
- phase measurements separate prefill, decode, retrieval, rerank, tool, queue, cold-start, and end-to-end latency;
- runtime engine, provider endpoint, GPU/accelerator class, region, precision, quantization, batching, and cache behavior are versioned;
- cold-start evidence names image startup, model load, compilation, snapshot/prewarm policy, warm-path and cold-path measurements, and fallback route;
- endpoint contract covers request/response schema, auth boundary, rate limits, redaction, observability, health check, and rollback;
- representative benchmarks use route-specific context lengths, output lengths, retrieval/tool steps, and media constraints rather than toy prompts;
- runtime, quantization, batching, hardware, or region changes include quality, grounding, safety, latency, cost, and failure-slice regression results;
- background and batch routes cannot starve interactive or realtime-adjacent routes under load;
- fallback and rollback targets are named before the route can affect production artifacts, user-visible chat, publishing, or source-ingestion jobs.
