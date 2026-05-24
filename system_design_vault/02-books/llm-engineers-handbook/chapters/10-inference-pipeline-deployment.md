---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "LLM Engineer's Handbook"
authors: "Paul Iusztin; Maxime Labonne"
chapter: "10"
chapter_title: "Inference Pipeline Deployment"
source_path: "/Users/saumyamehta/DS interview prep/books/LLM Engineers Handbook.pdf"
rights_status: user_provided_local
source_lines: "13004-14573"
updated: 2026-05-17
cross_check_note_path: "system_design_vault/01-sources/official-open/llm-engineers-handbook-cross-check.md"
---

# 10 - Inference Pipeline Deployment

## Reading Status

Direct source reading and official/open cross-check completed for chapter 10. This note is original synthesis only and does not include raw book text, commands, or long excerpts.

## Core Idea

Inference deployment is where model capability turns into product value. A strong model has little business value if users cannot reach it reliably, cheaply, and within acceptable latency. The chapter frames deployment decisions around four coupled requirements: throughput, latency, data, and infrastructure.

For Agent Studio, inference design must be decided per workflow route. A real-time voice assistant, a background research agent, a batch corpus-ingestion job, and an offline evaluation sweep should not share one deployment pattern.

## Deployment Choice Criteria

The chapter starts with requirements:

- Throughput: requests or items processed per unit time.
- Latency: time from request to usable result.
- Data: input/output size, type, format, and complexity.
- Infrastructure: hardware, software, network, scaling model, and cost profile.

These variables pull against each other. Batching can increase throughput while increasing per-request latency. GPU instances can reduce model time but increase idle cost. Large context windows improve reasoning only if the service can afford their token and memory cost.

Agent Studio implication: each route needs an explicit serving profile: target latency, max latency, throughput, concurrency, context size, model class, retrieval dependency, streaming requirement, and cost ceiling.

## Three Inference Deployment Types

The chapter distinguishes three serving patterns.

Online real-time inference is synchronous request-response serving through REST, gRPC, or similar protocols. It is appropriate for chat, live recommendations, embeddings, reranking, and user-facing agent turns where immediate output matters. Streaming can improve perceived responsiveness for LLM interactions.

Asynchronous inference accepts work, queues it, and returns results later through polling, push, object storage, or a result queue. It is useful for long-running tasks, traffic spikes, cost control, and workflows where delayed completion is acceptable.

Offline batch transform processes large datasets on a schedule or manual trigger, then writes results to storage. It is the cheapest and simplest pattern when freshness requirements are loose and throughput matters more than latency.

Agent Studio implication:

- Use real-time serving for interactive planning, voice, chat, retrieval, reranking, and fast agent handoffs.
- Use async serving for long research, video analysis, batch content generation, heavy critique loops, and queueable tool work.
- Use batch transform for corpus ingestion, embedding refreshes, offline evals, source scans, and periodic index rebuilds.

## Monolith Versus Microservices

The chapter compares bundling business logic and model inference in one service versus separating them. A monolith is simpler to build and operate early, but it makes independent scaling hard. The LLM path is GPU-heavy; retrieval, prompt assembly, authorization, logging, and source-ledger logic are mostly CPU and I/O-bound.

Microservices add network latency and operational complexity, but they allow independent scaling, separate technology stacks, and lower GPU waste. The book's deployment design separates a business/RAG service from an LLM microservice.

Agent Studio implication: start with modular boundaries even if deployment begins as one process. The LLM runtime, retrieval/reranking layer, source-ledger service, orchestration engine, and product API should be separable when traffic or cost demands it.

## LLM Twin Deployment Pattern

The chapter's reference architecture uses:

- a business microservice for RAG retrieval, prompt construction, and product logic;
- an LLM microservice optimized for generation;
- an online vector store for retrieval features;
- a model registry for the fine-tuned model;
- prompt monitoring for request, context, answer, and intermediate traces.

The core flow is user query, retrieve context, assemble prompt, call LLM service, log monitoring payload, return answer.

Agent Studio implication: this maps closely to a production multi-agent studio. The orchestrator should not hide route internals. Each agent run should capture query, retrieval candidates, chosen context, prompt version, model endpoint, inference parameters, generated answer, evaluator output, and final user/editor decision.

## Model Serving Infrastructure

The chapter uses AWS SageMaker with Hugging Face Deep Learning Containers and Text Generation Inference. The general lessons are portable:

- use model registries to version deployable models;
- use specialized inference runtimes for LLM serving;
- configure GPU count, memory, token limits, batching, quantization, and generation parameters explicitly;
- separate deploy-time configuration from application logic;
- give deployed resources least-privilege access through roles;
- monitor endpoint logs, errors, CPU, memory, disk, and GPU utilization.

Agent Studio implication: deployment configuration is part of the system design, not an ops afterthought. The vault should capture serving constraints for each candidate runtime: vLLM, TGI, managed APIs, SageMaker, Vertex AI, Bedrock, and local runtimes.

## Training-Serving Skew

The chapter calls out a critical split between training and inference pipelines. Training reads batch data from offline stores and optimizes lineage and throughput. Inference reads live features from online stores and optimizes latency and availability. Shared preprocessing and postprocessing must remain consistent, or the model behaves differently in production than it did during evaluation.

Agent Studio implication: use versioned shared components for prompt formatting, retrieval preprocessing, citation formatting, safety filters, and response schemas. Any divergence between eval and serving should be visible in the run trace.

## Business API Layer

The chapter uses a FastAPI service to expose the RAG workflow while delegating generation to the LLM endpoint. The important architectural move is dependency inversion: the business service talks to an inference interface, so the backing model strategy can change without rewriting the product logic.

Agent Studio implication:

- Define provider-neutral inference interfaces.
- Keep route orchestration separate from model-specific SDK calls.
- Make retrieval and generation swappable for tests.
- Preserve prompt templates and parameters at the call boundary.

## Autoscaling

Static GPU replicas waste money during idle periods and fail during spikes. The chapter describes autoscaling through scalable targets and policies, including minimum and maximum capacity, target-tracking metrics, and cooldown periods.

Autoscaling needs careful tuning. Over-scaling burns cost; under-scaling harms user experience. Target metrics can include requests per replica, queue depth, GPU utilization, latency, or combinations of operational signals.

Agent Studio implication:

- Real-time routes need load testing before production.
- Async routes should scale on queue depth and age.
- Reranking, embedding, and generation may need separate scaling policies.
- Cost controls must include maximum replicas, idle timeout, and deletion/cleanup routines for test deployments.

## Agent Studio Design Commitments

- Maintain route-level serving profiles for latency, throughput, cost, context length, and freshness.
- Use different deployment modes for interactive, async, and batch work.
- Design the monolith with hard software boundaries so later service extraction is cheap.
- Keep GPU work isolated from CPU/I/O-heavy business logic when scale or cost justifies it.
- Store prompt version, retriever version, model endpoint, runtime, inference parameters, and trace IDs for every served answer.
- Use model registries and deployment manifests for any self-hosted model.
- Apply least-privilege credentials to cloud deployment roles.
- Use streaming where perceived latency matters.
- Build autoscaling around measured product traffic and stress tests, not guesswork.
- Delete or scale down expensive test endpoints by default.

## Failure Modes

- One deployment pattern is forced onto all workflows.
- GPU services run idle because business logic is bundled into the same replicas.
- Batch jobs are incorrectly exposed as real-time features.
- Online inference depends on slow offline stores.
- Eval and serving use different preprocessing, prompt templates, or inference parameters.
- Autoscaling policies are too sensitive and create runaway cost.
- Scaling is too conservative and user-facing latency collapses during spikes.
- Endpoint logs and prompt traces are missing, making failures hard to debug.
- Cloud roles are overprivileged.
- Test endpoints remain running after experiments.

## Follow-Ups

- Cross-check against AWS SageMaker autoscaling docs, Hugging Face TGI docs, vLLM production serving guidance, Ray Serve/KServe patterns, OpenTelemetry GenAI conventions, and Stanford CS336 inference material.
- Add route-level serving profiles to the Agent Studio HLD and LLD.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-state-space-transformer-tradeoffs]] - Stanford CS25, "On the Tradeoffs of State Space Models and Transformers" ([YouTube](https://www.youtube.com/watch?v=OyimE74UMF8)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Introduction to Transformers" ([YouTube](https://www.youtube.com/watch?v=XfpMkf4rD6E)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "How I Learned to Stop Worrying and Love the Transformer" ([YouTube](https://www.youtube.com/watch?v=1GbDTTK3aR4)).
