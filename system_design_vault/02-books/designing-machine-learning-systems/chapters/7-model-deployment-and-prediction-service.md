---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Designing Machine Learning Systems"
author: "Chip Huyen"
chapter: "7"
chapter_title: "Model Deployment and Prediction Service"
source_path: "/Users/saumyamehta/DS interview prep/books/Designing machine learning systems - an iterative process.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 7 - Model Deployment and Prediction Service

## Reading Status

Direct source reading and official cross-check completed for chapter 7. This note is original synthesis only and does not include raw book text or long excerpts.

## Core Idea

Deployment is not just exposing a prediction endpoint. The chapter treats deployment as the point where model logic enters a production environment with latency, uptime, scale, monitoring, team handoff, update, cost, and hardware constraints.

For Agent Studio, the equivalent is not "call an LLM." It is a production prediction and workflow service that must support many agent/model routes, multiple serving modes, traceability, fast updates, and workload-specific infrastructure.

## Production Is A Spectrum

The chapter emphasizes that production ranges from internal notebook outputs to services used by millions. Requirements depend on where the system sits on that spectrum.

Agent Studio implication:

- Classify every workflow by production tier: research, internal tooling, beta user-facing, production user-facing, and production automated action.
- Higher tiers require stronger availability, rollback, monitoring, audit, and access control.
- Do not use the same acceptance bar for exploratory notes ingestion and user-facing autonomous publishing.

## Deployment Myths

The chapter pushes against four common deployment assumptions:

- production systems often contain many models, not one or two;
- model performance degrades as production data changes;
- models should be updateable as often as the system safely allows;
- scale is relevant to many ML engineers, not only a few large companies.

Agent Studio implication:

- Plan for many model routes: retrieval, reranking, judging, writing, editing, tool planning, moderation, embedding, speech, and vision.
- Model and prompt refresh must be operationally cheap.
- The system needs model inventory, owner, environment, status, usage, quality metrics, and rollback target for every route.

## Batch Prediction And Online Prediction

Batch prediction generates outputs periodically or on a trigger, stores them, and retrieves them later. Online prediction generates outputs when the request arrives. Some online systems use only batch features; others combine batch and streaming features.

Agent Studio implication:

- Use batch mode for local book ingestion, embedding, offline evals, source inventories, playlist note preparation, and scheduled corpus refresh.
- Use online mode for interactive agent runs, chat, tool execution, and user-facing generation.
- Use hybrid mode where popular or stable artifacts can be precomputed but long-tail user requests are generated online.
- Do not make online generation do work that can be safely precomputed.

## Batch Versus Streaming Features

The chapter warns that separate batch and streaming pipelines are a common source of training-serving skew. If training and inference compute features differently, production bugs follow.

Agent Studio implication:

- Keep one feature definition for source metadata, chunking, embeddings, retrieval filters, and ranking features.
- If offline ingestion and online retrieval use different code paths, their outputs must be compared with fixtures.
- A source/chunk should carry enough metadata to support both offline evals and online retrieval without recomputation drift.

## Prediction Service Modes

Online prediction is required when requests are unpredictable, freshness matters, or delayed decisions cause harm. Batch prediction is useful when the request universe is known and immediate freshness is not required.

Agent Studio examples:

- batch: chapter summaries after approved extraction, embedding rebuilds, quality reports, playlist/source maps;
- online: user asks for a grounded answer, agent selects tools, editor asks for a rewrite, reviewer validates a claim;
- hybrid: precompute stable source cards and retrieval indexes, then assemble user-specific responses online.

## Model Compression

The chapter covers low-rank factorization, distillation, pruning, and quantization as ways to reduce model size or improve latency. Quantization is the most broadly applicable; distillation depends on teacher availability; pruning can change sparsity and behavior.

Agent Studio implication:

- Compression belongs in the model-route evaluation process.
- Smaller or quantized models can serve background tasks, local workflows, and high-volume low-risk calls.
- Measure task quality after compression, especially for citation, refusal, tool-use, and extraction fidelity.
- Do not promote a compressed route only because generic latency improves.

## Cloud And Edge

Cloud deployment is easy to start with but can be limited by cost, network latency, privacy, and internet availability. Edge deployment reduces network dependence and can help with privacy and cost, but requires adequate device compute, memory, and power.

Agent Studio implication:

- Cloud is the default for heavy models, shared evaluation, and collaborative production workflows.
- Local/edge routes are valuable for private source inspection, offline-first note reading, lightweight embeddings, and low-risk background processing.
- Route selection should account for data sensitivity, latency, cost, availability, and model capability.

## Compilation And Optimization

The chapter explains intermediate representations, lowering, local optimizations such as vectorization, parallelization, loop tiling, operator fusion, and global graph optimization. The broader point is that production speed depends on the full workload, not only an isolated model call.

Agent Studio implication:

- Benchmark end-to-end workflows, not only provider/model latency.
- Cross-framework movement, serialization, retrieval, prompt assembly, and post-processing can dominate latency.
- Serving optimization should include retrieval store, application service, model gateway, network, and client streaming behavior.

## Failure Modes

- Treating deployment as a final step instead of the start of production operation.
- Designing the platform for one model route when the product needs many.
- Using batch prediction for requests that need freshness.
- Forcing online prediction to recompute stable artifacts.
- Maintaining separate offline and online feature logic without parity tests.
- Ignoring network latency and cloud cost in serving design.
- Compressing/quantizing without task-specific regression tests.
- Benchmarking one optimized model or hardware target and assuming arbitrary Agent Studio workflows will behave similarly.

## Agent Studio Design Decisions

- Build around many model routes, not a single model endpoint.
- Add `production_tier` and `serving_mode` fields to each agent/workflow.
- Separate batch ingestion/eval queues from online interactive serving.
- Maintain shared feature definitions for chunks, metadata, embeddings, filters, and retrieval signals.
- Use hybrid precomputation for stable source artifacts and online generation for user-specific synthesis.
- Evaluate compression, edge/local serving, and engine changes with Agent Studio task suites before rollout.
- Track model route inventory and deployment lineage continuously.

## Follow-Ups

- Connect this note with Inference Engineering chapters 1, 5, and 7.
- Define Agent Studio `serving_mode`, `production_tier`, and model-route inventory schemas.
- Canon cross-check: [[01-sources/official-open/designing-machine-learning-systems-cross-check]]

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-state-space-transformer-tradeoffs]] - Stanford CS25, "On the Tradeoffs of State Space Models and Transformers" ([YouTube](https://www.youtube.com/watch?v=OyimE74UMF8)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
