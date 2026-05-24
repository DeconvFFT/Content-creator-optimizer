---
type: lecture-note
project: agent-studio-system-design
status: canon_ready
source_title: "Stanford CS336 Language Modeling from Scratch"
source_status: official_public
updated: 2026-05-18
sources:
  - https://cs336.stanford.edu/spring2025/index.html
  - https://www.youtube.com/playlist?list=PLoROMvodv4rOY23Y0BoGoBGgQ1zmU_MT_
  - https://raw.githubusercontent.com/stanford-cs336/spring2025-lectures/main/lecture_02.py
  - https://raw.githubusercontent.com/stanford-cs336/lectures/main/lecture_07.py
  - https://raw.githubusercontent.com/stanford-cs336/spring2025-lectures/main/lecture_10.py
  - https://raw.githubusercontent.com/stanford-cs336/spring2025-lectures/main/lecture_12.py
---

# CS336 - Systems, Inference, And Evaluation

## Reading Status

Canon-ready direct read of the official CS336 Spring 2025 course page, official Stanford Online playlist pointer, and official lecture source files for resource accounting, parallelism, inference, and evaluation. Current-source check on May 18, 2026 confirmed that the archived Stanford course page links the relevant public course materials for Lecture 2 resource accounting, Lecture 7 parallelism, Lecture 10 inference, and Lecture 12 evaluation. This note is original synthesis only and does not include raw lecture text, copied source-code blocks, video transcripts, or long excerpts.

## Why This Matters

CS336 is valuable for Agent Studio because it explains the systems substrate under language-model products: tensor resource accounting, GPU memory hierarchy, parallelism, inference bottlenecks, KV-cache behavior, batching, benchmark validity, and the distinction between evaluating a model and evaluating a full agentic system.

The course also has the right posture for the vault: implementation-heavy, systems-aware, and skeptical of abstract benchmark scores without knowing the rules of the evaluation.

## Lecture 2 - Resource Accounting

The core lesson is to count resources before optimizing. Memory and FLOPs are not vague implementation details; they determine which workloads fit, which operations are bottlenecked, and which tradeoffs are available.

Agent Studio implications:

- Every model route should record compute class, memory footprint, expected sequence lengths, batch size assumptions, and cost envelope.
- For ingestion and evaluation jobs, estimate corpus size, token volume, embedding calls, reranker calls, and model calls before launching a large run.
- Keep lightweight "napkin math" in design notes: expected tokens, files, chunks, model calls, wall-clock time, and cost.
- Treat mixed precision, checkpointing, batching, and data loading as production design choices, not after-the-fact tuning.

Failure modes:

- Starting a large ingestion or eval run without a token/cost/runtime estimate.
- Comparing models without normalizing for hardware, precision, context length, and batching assumptions.
- Treating GPU memory failure as an operational surprise instead of a predictable sizing error.

## Lecture 7 - Parallelism

The parallelism lecture's durable idea is that compute is far from data. Scaling is mostly about orchestrating computation while minimizing data transfer across a hierarchy: local cache, HBM, NVLink/NVSwitch, InfiniBand/RDMA, and slower network paths.

Agent Studio implications:

- Prefer horizontal replicas for simple throughput needs before distributed model serving.
- Only use tensor, pipeline, expert, or sequence parallelism when model size, throughput, or latency demands justify communication overhead.
- Record the interconnect assumption for any dedicated serving plan; a multi-GPU design that needs NVLink is not portable to weakly connected nodes.
- For MoE or multi-agent routing, watch all-to-all and cross-service communication costs. Routing intelligence can become a latency tax.

Failure modes:

- Designing a serving plan that assumes fast interconnect without proving the deployment has it.
- Scaling a multi-stage agent pipeline by duplicating the whole chain instead of scaling the bottleneck stage.
- Moving data between services or regions when colocating the work would be cheaper and more reliable.

## Lecture 10 - Inference

The inference lecture connects product metrics to hardware realities. Inference appears in chat, code completion, batch processing, evaluation, test-time reasoning, and reinforcement learning sampling. The important metrics differ by workload: TTFT for first response, per-token latency for interactive smoothness, and throughput for batch jobs.

The central systems point is that autoregressive generation is sequential and memory-limited. Prefill can use parallelism; decode repeatedly reads model weights and KV cache. KV cache therefore becomes a production resource, not an implementation footnote.

Agent Studio implications:

- Split `prefill_time`, `decode_time`, `TTFT`, `TPOT`, total latency, queue time, retrieval time, and tool time in traces.
- Treat context layout as an inference feature: stable system instructions, tool schemas, and reusable source context should be placed for prefix reuse when the provider/runtime supports it.
- Use separate benchmarks for short chat, long-context research, tool-heavy agents, codebase QA, source ingestion, and offline evals.
- Apply speculative decoding, quantization, pruning/distillation, continuous batching, and PagedAttention-style KV management as measured deployment variants, not as global defaults.
- For Agent Studio's source-grounded workflows, control token growth in internal traces; agentic loops can create unbounded inference spend.

Failure modes:

- Optimizing model-only latency while the real bottleneck is retrieval, tools, queueing, orchestration, or client streaming.
- Measuring throughput on batch workloads and assuming interactive users will see low latency.
- Ignoring KV-cache pressure for long source contexts and multi-turn workflows.
- Enabling lossy optimizations without product evals and groundedness checks.

## Lecture 12 - Evaluation

The evaluation lecture is directly relevant to Agent Studio because it rejects the idea of one universal score. Evaluation depends on the question being asked: purchase decision, raw capability, safety/benefit tradeoff, or developer feedback. It also distinguishes models, methods, and systems.

For Agent Studio, this means an eval suite must state the rules of the game:

- Inputs: use cases, tail cases, multi-turn context, source coverage, and adversarial or low-quality source conditions.
- Calls: model-only, RAG, tool-use, agent workflow, human-in-the-loop, or full production system.
- Outputs: exact answers, generated artifacts, citations, tool decisions, state transitions, or reviewer outcomes.
- Interpretation: cost, latency, safety, hallucination risk, asymmetric errors, train-test contamination, and deployment threshold.

Agent Studio implications:

- Keep separate evals for model route quality, retrieval recall, citation precision, tool-call correctness, workflow completion, safety, and user/reviewer acceptance.
- Do not evaluate an agentic system as though it were only a base model. Tool use, memory, retrieval, retries, and scaffolding are part of the system being judged.
- Inspect individual failures, not just aggregate scores. Bad source provenance, weak retrieval, wrong tool choice, and unsafe autonomy need different fixes.
- Include realistic "asking" prompts where users do not know the answer, not only quiz-style prompts with known facts.

Failure modes:

- Treating leaderboard scores as production readiness.
- Mixing model comparisons and workflow comparisons without saying which is being measured.
- Ignoring cost and latency when choosing a higher-scoring model.
- Using stale or contaminated benchmark data to justify architecture decisions.

## Agent Studio Design Decisions

- Add a standard resource-estimate block to every major ingestion, evaluation, and serving design.
- Make `inference_contract` and `evaluation_contract` sibling concepts in agent cards.
- Maintain workload classes: realtime voice, interactive studio, long-context research, batch ingestion, offline eval, source refresh, and background synthesis.
- Extend trace schema with inference systems fields: prefill/decode split, TTFT, TPOT, token counts, KV/cache hit metadata when available, batch size, queue time, and route/provider.
- Extend eval schema with evaluation target: model, method, retrieval stack, tool policy, agent workflow, or full product system.
- Treat Stanford CS336 as the canonical lecture backbone for resource accounting, inference bottlenecks, and evaluation validity.

## Systems Evaluation Release Gate

Agent Studio should require a `systems_evaluation_release_gate` before promoting a model route, inference runtime, retrieval/agent workflow, or large ingestion/eval run. The gate should include:

- resource estimate: corpus size, tokens, chunks, expected model calls, embedding/reranker calls, GPU/CPU memory, wall-clock time, and cost envelope;
- workload class: realtime, interactive, long-context research, tool-heavy agent, batch ingestion, offline eval, source refresh, or background synthesis;
- inference contract: latency budget, cost budget, input/output length distribution, streaming policy, concurrency, queue policy, and data boundary;
- phase metrics: prefill, decode, queue, retrieval, reranking, tool, cold-start, end-to-end latency, token counts, batch size, and KV/cache behavior where available;
- parallelism and placement assumptions: horizontal replicas, tensor/pipeline/expert/sequence parallelism, interconnect requirement, colocated services, and communication bottlenecks;
- evaluation contract: target being evaluated, allowed tools/memory/retrieval, source snapshots, success criteria, failure slices, contamination checks, cost/latency thresholds, and reviewer policy;
- failure inspection: individual failed traces grouped by source provenance, retrieval, citation, tool choice, safety, latency, and workflow recovery cause;
- fallback and rollback target for runtime, route, source index, prompt, eval set, or serving-profile changes.

## Related Official Video Sources

The CS336 Spring 2025 archive and Stanford Online playlist are public navigation sources for this topic. This note uses the official course page and source files for direct-read synthesis; it does not claim full video watching, transcript ingestion, comments, captions, or timestamp-level coverage.

| Video source | URL | Relevant topics | Status |
|---|---|---|---|
| Stanford CS336 Language Modeling from Scratch public playlist | https://www.youtube.com/playlist?list=PLoROMvodv4rOY23Y0BoGoBGgQ1zmU_MT_ | resource accounting, parallelism, inference systems, evaluation | playlist candidate; individual videos not watched in full |

This gate prevents a common systems mistake: using a model benchmark to approve a product workflow. Agent Studio routes need evidence for the full system under the workload that will actually run.

## Follow-Ups

- Create separate notes for CS336 data and alignment lectures after direct reading.
- Cross-check LLM Engineers Handbook chapters 7, 8, 9, and 11 against this lecture note and official runtime/eval docs.
- Add concrete Agent Studio schemas for `resource_estimate`, `inference_contract`, and `evaluation_contract`.
