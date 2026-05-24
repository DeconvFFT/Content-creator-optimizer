---
type: official-source-cross-check
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-17
cross_checks:
  - source_title: "Building Machine Learning Powered Applications"
    chapters: "8-11 deployment, safeguards, monitoring"
sources:
  - https://www.uber.com/ie/en/blog/michelangelo-machine-learning-platform/
  - [[uber-ml-platform-agentic-governance]]
  - https://docs.metaflow.org/introduction/what-is-metaflow
  - https://docs.metaflow.org/production/introduction
  - https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning
---

# Production ML Platform Cross-Check

## Scope

This note cross-checks the deployment, safeguards, lifecycle, and monitoring lessons from Building ML Powered Applications against official production-platform sources:

- Uber Michelangelo engineering blog.
- Metaflow official docs.
- Google Cloud MLOps continuous delivery and automation guidance.

It stores compact original synthesis only. It does not copy raw source text or long excerpts.

## Cross-Check Result

Status: `canon_ready` for the Building ML Powered Applications deployment and monitoring direction when combined with the direct-read chapter notes, official eval/observability/safety docs, and Stanford CS329S note.

The sources converge on the same architecture: production ML is a managed lifecycle of data, training, evaluation, deployment, serving, monitoring, feedback, metadata, and retraining. A model artifact alone is not a production system.

## Confirmation Matrix

| Platform theme | Source confirmation | Agent Studio implication |
|---|---|---|
| End-to-end lifecycle | Uber Michelangelo standardizes data management, model training, evaluation, deployment, prediction, and prediction monitoring as a single platform workflow. Google Cloud MLOps describes the same path from business use case and success criteria through extraction, analysis, preparation, training, evaluation, validation, serving, and monitoring. | Agent Studio should model every content run as a lifecycle: source intake, preparation, retrieval, generation, evaluation, publish readiness, feedback, monitoring, and memory update. |
| Feature/data parity | Michelangelo emphasizes data pipelines that support online and offline use while reducing duplicate feature work and training-serving skew. Google Cloud MLOps calls out training-serving skew as a risk in manual handoff deployments. | Version extraction, chunking, embeddings, metadata, graph transforms, reranking, and prompt inputs together so ingestion/query behavior does not diverge. |
| Production deployment modes | Michelangelo supports offline/batch deployment, online prediction services, and library-style deployment. Metaflow treats production as automated, reliable workflows that may write to warehouses, populate caches, trigger larger systems, or hand models to hosting platforms. | Maintain separate Agent Studio runtime modes: realtime dialogue, batch ingestion, scheduled brief generation, offline evaluation, cached retrieval/index updates, and publish workflows. |
| Automation maturity | Google Cloud MLOps separates manual level 0, pipeline automation level 1, and CI/CD pipeline automation level 2. Level 1 adds automated retraining, validation, triggers, and metadata; level 2 adds source control, build/test, deployment, registry, feature store, metadata store, and orchestrator. | Treat manual Obsidian work as learning input, but product ingestion needs automated pipelines, validation gates, metadata ledgers, and reproducible deployment paths. |
| Metadata and rollback | Google Cloud MLOps requires metadata for pipeline/component versions, timing, executor, parameters, artifact pointers, validation anomalies, model pointers, rollback, and evaluation metrics. | Run ledgers should store source IDs, extraction version, prompt/model/provider versions, artifact IDs, eval scores, feedback, and rollback pointers. |
| Safe model replacement | Michelangelo supports model UUIDs/tags, side-by-side deployment, gradual traffic switching, and A/B testing. Metaflow supports running newer production versions alongside existing deployments and comparing results. | Use tags/aliases for agent, prompt, retrieval, and provider versions; compare candidate workflows against current production behavior before promotion. |
| Monitoring predictions | Michelangelo logs or holds back predictions, later joins them to observed outcomes, and publishes live accuracy metrics for alerts. Google Cloud MLOps treats monitoring as the trigger for retraining or new experiments. | Capture accepted/rejected claims, user edits, ratings, publishing outcomes, and delayed performance signals so Agent Studio can detect quality drift and retrain or revise workflows. |
| Reliable orchestration | Metaflow defines production as automated, highly available, predictable execution without manual laptop runs. It emphasizes production-grade orchestrators, event triggers, local resume/debugging, and inspection of production run state. | Background ingestion and autonomous profiles should run from durable orchestration with retry, resume, event triggers, run-state inspection, and local debugging paths. |

## Agent Studio Design Decisions Strengthened

- Promote source and artifact metadata to a first-class schema, not a loose note convention.
- Keep source ingestion, retrieval, generation, verification, and publishing as separately observable pipeline components.
- Require parity checks between ingestion-time processing and serving-time retrieval.
- Support candidate workflow versions running beside production workflow versions for comparison.
- Store enough metadata to replay, resume, audit, and roll back every autonomous run.
- Treat user feedback and observed outcomes as delayed labels, not only comments.
- Use production orchestration for background ingestion instead of depending on interactive/manual execution.

## Canonical Implication For Building ML Powered Applications

The Building ML Powered Applications chapter notes are now supported by:

- Direct local book reading for all 11 chapters.
- Official eval, trace, safety, deployment, observability, and reliability docs.
- Stanford CS329S official course and lecture notes.
- Production platform sources from Uber Michelangelo, Metaflow, and Google Cloud MLOps.
- The dedicated Uber platform/governance note, which adds current agentic MCP design-spec automation and responsible-AI governance evidence.

This is enough to use the book's lessons as canon for Agent Studio system-design decisions, while still allowing future notes to refine details from newer platform sources.
