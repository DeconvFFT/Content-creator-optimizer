---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Designing Machine Learning Systems"
author: "Chip Huyen"
chapter: "10"
chapter_title: "Infrastructure and Tooling for MLOps"
source_path: "/Users/saumyamehta/DS interview prep/books/Designing machine learning systems - an iterative process.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 10 - Infrastructure and Tooling for MLOps

## Reading Status

Direct source reading and official cross-check completed for chapter 10. This note is original synthesis only and does not include raw book text or long excerpts.

## Core Idea

Good infrastructure turns known best practices into repeatable defaults. The chapter frames ML infrastructure as layered support for storage/compute, development environments, resource management, workflow orchestration, model deployment, model stores, feature stores, and build-versus-buy decisions.

For Agent Studio, infrastructure must make the right AI-engineering behavior easy: source provenance, repeatable ingestion, traceable model routes, prompt/version control, reproducible evals, controlled rollouts, and debuggable production runs.

## Scale-Specific Infrastructure

Infrastructure needs depend on application count, specialization, scale, and risk. Most companies benefit from generalized infrastructure at reasonable scale rather than highly bespoke platform work.

Agent Studio implication:

- Start with generalized platform primitives that cover many agent workflows.
- Avoid overbuilding specialized infrastructure before workload shape is proven.
- Design escape hatches for specialized serving, retrieval, or compliance paths where product needs justify them.

## Infrastructure Layers

The chapter divides ML infrastructure into:

- storage and compute;
- resource management;
- ML platform;
- development environment.

Agent Studio mapping:

- storage/compute: source files, extracted text, chunks, embeddings, vector indexes, traces, eval artifacts, model outputs;
- resource management: ingestion jobs, eval jobs, embedding jobs, long-running agent workflows, serving queues;
- ML platform: model registry, prompt registry, feature/source store, eval store, trace store, deployment service;
- development environment: reproducible code, notebooks only where appropriate, CI/CD, containers, test fixtures.

## Storage And Compute

The chapter treats storage and compute as foundational but increasingly commoditized. Compute units are constrained by memory, I/O bandwidth, operation speed, utilization, and cost.

Agent Studio implication:

- Track workload resource needs explicitly: extraction, OCR, embedding, reranking, generation, eval judging, and video/lecture processing.
- Benchmark real workflows instead of trusting generic hardware or model benchmarks.
- Separate bursty development/eval jobs from steady production serving.
- Watch utilization and queueing, but optimize for engineering velocity until cost becomes a real constraint.

## Cloud, Data Centers, And Multicloud

Cloud is elastic and easy to start with, but long-term cost and lock-in can matter. Multicloud often arises from organizational history rather than deliberate design and adds orchestration complexity.

Agent Studio implication:

- Default to simple cloud/provider choices early.
- Keep artifacts portable where it is cheap: source manifests, extracted text metadata, eval datasets, prompt versions, trace schemas.
- Avoid coupling core intellectual assets to a single vendor-specific storage or workflow format.
- Do not pursue multicloud unless there is a clear compliance, availability, or cost reason.

## Development Environment

The chapter argues that development environment quality directly affects engineering productivity. Standardized environments reduce dependency drift and reproducibility failures.

Agent Studio implication:

- Use reproducible environments for ingestion and eval work.
- Keep dependency versions pinned for extraction, embedding, vector DB clients, and eval tooling.
- Treat notebooks as exploratory artifacts unless converted into tested pipelines.
- CI should run schema, extraction, retrieval, prompt, and eval smoke checks.

## Containers

Containers package dependencies and code so workloads can run consistently across machines. Multiple containers may be needed when pipeline stages have different compute or dependency requirements.

Agent Studio implication:

- Build separate runtime images for ingestion/extraction, embedding/indexing, eval, and serving if dependencies diverge.
- Use immutable images for production jobs and trace the image digest in run metadata.
- Do not let local developer environments become the only place ingestion can run.

## Resource Management

ML workflows are repetitive and dependency-heavy. Cron handles fixed schedules; schedulers manage DAG dependencies and retries; orchestrators provision lower-level resources.

Agent Studio implication:

- Model ingestion and eval workflows as DAGs with explicit dependencies.
- Include retries, idempotency, and artifact checks for each stage.
- Make failures resume from stable artifacts instead of restarting the whole corpus.
- Queue jobs by workload class: source extraction, embedding, index build, eval judging, batch synthesis, online serving.

## Workflow Tools

The chapter compares Airflow, Argo, Prefect, Kubeflow, and Metaflow through the lens of parameterization, dynamic workflows, containerized steps, local-to-cloud parity, and usability.

Agent Studio implication:

- Prefer workflow tooling that supports parameterized runs, dynamic source batches, per-step environments, and local-to-cloud parity.
- Avoid workflows that require every data/AI developer to own low-level Kubernetes details.
- Expose high-level run controls: source batch, corpus, extraction policy, embedding model, eval suite, and target environment.

## ML Platform

An ML platform provides shared tools across applications instead of separate bespoke systems per model. The chapter highlights deployment, model stores, and feature stores as core components.

Agent Studio platform equivalents:

- deployment service: model, prompt, agent, and workflow deployment;
- model store: model route registry plus prompt/tool/index versions;
- feature store: source/chunk/retrieval feature registry;
- monitoring store: traces, metrics, alerts, feedback, and eval history.

## Model Deployment

Deployment tooling should support both online and batch prediction, and it should make production testing patterns easier.

Agent Studio implication:

- Deployment service must support online agents and batch ingestion/eval pipelines.
- Rollouts should support shadow, canary, rollback, and environment separation.
- Promotion gates should be built into deployment, not handled manually in notes.

## Model Store

A useful model store tracks far more than a serialized model. The chapter lists artifacts such as model definition, parameters, featurization/prediction functions, dependencies, data, generation code, experiment artifacts, and tags.

Agent Studio implication:

- Create an `artifact_registry` concept for models, prompts, indexes, tools, corpora, evals, and workflows.
- Each registered artifact needs owner, task, version, dependency set, source data, generation code/config, evaluation metrics, tags, and deployment status.
- Debugging a production answer should identify the exact model route, prompt, retrieval index, corpus version, and tool policy used.

## Feature Store

Feature stores address feature management, feature computation, and feature consistency between training and inference.

Agent Studio implication:

- Treat source/chunk metadata and retrieval signals as features.
- Feature definitions should be shared between offline evals and online retrieval.
- Store source rights status, provenance, source type, extraction version, chunk policy, embedding model, chunk IDs, freshness, authority tier, and section/chapter metadata.
- Prevent train-serving skew equivalents between ingestion-time chunk construction and request-time retrieval filters.

## Build Versus Buy

Build-versus-buy decisions depend on company stage, competitive advantage, tool maturity, integration cost, security, and maintenance burden.

Agent Studio implication:

- Buy or use managed services for commoditized infrastructure when speed matters.
- Build thin, portable schemas for the system’s core value: source provenance, agent traces, eval cases, prompt/workflow versions, and artifact lineage.
- Avoid "integration hell" by keeping platform interfaces modular.
- Revisit build-versus-buy as usage, compliance, cost, and product differentiation change.

## Failure Modes

- Investing in platform infrastructure before the team understands workload shape.
- Letting notebooks become unversioned production pipelines.
- Storing model or agent artifacts without enough lineage to reproduce failures.
- Using separate online/offline feature logic and creating hidden skew.
- Choosing workflow tooling that blocks data scientists or hides operational failures.
- Treating cloud elasticity as infinite or cost-free.
- Building custom infrastructure in areas where mature managed tools are sufficient.
- Buying a point solution that captures core product data in a nonportable format.

## Agent Studio Design Decisions

- Define core registries: source registry, artifact registry, model-route registry, prompt registry, eval registry, trace store, and workflow run store.
- Use DAG orchestration for ingestion, embedding, eval, and batch synthesis.
- Keep environment/version metadata on every run.
- Standardize dev and production runtime paths enough to reproduce issues.
- Store source/chunk features once and reuse them across retrieval, eval, and monitoring.
- Keep build-versus-buy decisions modular so provider changes do not rewrite product architecture.

## Follow-Ups

- Draft Agent Studio platform schema map for registries and workflow runs.
- Connect this note with LLM Engineers Handbook chapter 11 and Inference Engineering chapter 7.
- Canon cross-check: [[01-sources/official-open/designing-machine-learning-systems-cross-check]]

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-state-space-transformer-tradeoffs]] - Stanford CS25, "On the Tradeoffs of State Space Models and Transformers" ([YouTube](https://www.youtube.com/watch?v=OyimE74UMF8)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
