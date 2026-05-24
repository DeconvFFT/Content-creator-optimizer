---
type: official-source-cross-check
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-17
cross_checks:
  - source_title: "Building Machine Learning Powered Applications"
    chapters: "1-11"
sources:
  - https://developers.openai.com/api/docs/guides/evaluation-best-practices
  - https://developers.openai.com/api/docs/guides/agent-evals
  - https://developers.openai.com/api/docs/guides/trace-grading
  - https://developers.openai.com/api/docs/guides/agent-builder-safety
  - https://platform.claude.com/docs/en/test-and-evaluate/develop-tests
  - https://docs.cloud.google.com/architecture/deploy-operate-generative-ai-applications
  - https://docs.cloud.google.com/architecture/framework/perspectives/ai-ml/reliability
  - https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/design-principles.html
  - https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/generative-ai-lens.html
  - https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/genops03.html
  - https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-serverless/observability-and-monitoring.html
  - https://stanford-cs329s.github.io/index.html
  - https://stanford-cs329s.github.io/syllabus.html
  - https://docs.google.com/document/d/1C3dlLmFdYHJmACVkz99lSTUPF4XQbWb_Ah7mPE12Igo/edit
  - https://docs.google.com/document/d/1hNuW6bqWYZjlwpit_8W1cu7kllb-jTfy3Liof1GJWug/edit
  - https://docs.google.com/document/d/14uX2m9q7BUn_mgnM3h6if-s-r0MZrvDb-ZHNjgA1Uyo/edit
  - https://www.uber.com/ie/en/blog/michelangelo-machine-learning-platform/
  - https://docs.metaflow.org/introduction/what-is-metaflow
  - https://docs.metaflow.org/production/introduction
  - https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning
---

# Building ML Powered Applications - Official Cross-Check

## Scope

This note cross-checks the direct-read chapter notes for [[../../02-books/building-ml-powered-applications/chapters/1-from-product-goal-to-ml-framing]] through [[../../02-books/building-ml-powered-applications/chapters/11-monitor-and-update-models]] against current official/open engineering guidance.

It stores compact original synthesis only. It does not copy long source text.

## Cross-Check Result

Status: `canon_ready`.

The official sources strongly support the book's production themes: start from success criteria, prefer simple baselines before multi-agent complexity, evaluate continuously, version prompts/chains/data/assets, monitor application behavior and infrastructure, design for controlled autonomy, and keep traceability across model, prompt, retrieval, tool, and user-feedback paths.

Platform cross-check: [[production-ml-platform-cross-check]].

## Confirmation Matrix

| Book theme | Official-source confirmation | Agent Studio implication |
|---|---|---|
| Product metrics before model work | Anthropic eval guidance starts with specific, measurable, achievable, relevant success criteria across task fidelity, privacy, latency, price, and context use. OpenAI eval guidance likewise starts with an eval objective, dataset, metrics, comparison, and continuous evaluation. | Agent Studio capabilities need explicit success criteria before prompt/model/agent optimization. Do not mark an agent production-ready from subjective review alone. |
| Baselines before complexity | OpenAI eval guidance says multi-agent architecture should be driven by evals because starting there adds complexity and slows production. | Start with deterministic or single-agent baselines, then add specialist agents only when evals show a workflow-level need. |
| Trace-level debugging | OpenAI agent eval and trace-grading docs treat traces as the way to inspect model calls, tool calls, guardrails, handoffs, and workflow decisions. AWS serverless agent guidance also emphasizes trace-based monitoring for distributed agent workflows. | Store complete run traces and grade tool choice, handoff, retrieval, guardrail, and final output decisions separately. |
| Evaluation design | Anthropic recommends task-specific evals that mirror real-world distribution and edge cases, with automation when possible and scalable grading methods. OpenAI recommends continuous evaluation and growing eval sets from production and expert cases. | Keep eval datasets linked to source ledgers, user feedback, hard cases, and historical run logs. Use code graders where possible and rubric/model graders only after validation. |
| Prompt and chain versioning | Google Cloud GenAI deployment guidance says modifiable components such as prompt templates, chain definitions, external datasets, and adapters require strict versioning. AWS GenAI Lens highlights prompt/model/asset traceability. | Version prompts, graph definitions, retrieval corpora, embedding/reranker settings, model adapters, and agent cards together. |
| Deployment shape | Google Cloud distinguishes batch processes from online low-latency APIs and requires production-like integration tests, throughput checks, and load/performance validation. | Agent Studio should keep separate runtime classes for realtime studio turns, scheduled ingestion, batch source refresh, and offline evaluation. |
| Monitoring and continuous evaluation | Google Cloud recommends end-to-end logging, lineage across components, application-level monitoring first, drift/skew alerts, and continuous evaluation using production outputs and user feedback. | Monitor source freshness, retrieval quality, claim coverage, latency, cost, user feedback, and publish outcomes as one application-level health view before drilling into individual agents. |
| Reliability and graceful degradation | Google Cloud reliability guidance emphasizes scalable/HA infrastructure, modular architecture, well-defined APIs, graceful degradation, circuit breakers, fallbacks, SLOs, and golden signals. | Add circuit breakers and fallback routes for provider outages, retrieval misses, high latency, weak evidence, and stale memories. Define user-facing SLOs for realtime, background, and publish workflows. |
| Controlled autonomy and safety | AWS GenAI Lens calls for controlled autonomy, guardrails, boundaries, comprehensive observability, resource efficiency, distributed resilience, and centralized catalogs. OpenAI safety guidance recommends tool approvals, human approval nodes, guardrails for PII/jailbreaks, trace graders, and evals. | Autonomous agents need scoped tool permissions, approval gates, safety redaction, jailbreak checks, trace grading, and explicit failure conditions before acting. |
| Observability metrics | AWS prescriptive guidance lists agent behavior, tool selection, invalid tool calls, cost, latency, retrieval hit/miss and grounding relevance, hallucination/fallback rate, IAM/tool usage, token usage, and workflow retries/timeouts. | The cockpit should expose agent/tool behavior, retrieval health, grounding quality, fallback rate, token/cost trends, IAM/tool usage, and workflow health in one trace-correlated view. |
| User feedback loops | Google Cloud continuous evaluation uses direct user feedback and production outputs; AWS design principles include metrics across user feedback, model behavior, resource use, and security events. | Treat user ratings, overrides, accepted edits, rejected claims, and reviewer comments as first-class evaluation and retraining signals. |
| Product/system framing | Stanford CS329S starts from stakeholders and objectives, then teaches data management, feature engineering, model selection, deployment, monitoring, privacy, fairness, security, and business metrics as one iterative system. | Treat Agent Studio design as a product/system lifecycle, not a model or prompt optimization task. Every capability should name stakeholders, objectives, constraints, and update loops. |
| Production deployment modes | Stanford CS329S Lecture 8 distinguishes batch, online, hybrid, cloud, and edge deployment by latency, throughput, cost, freshness, privacy, and responsiveness tradeoffs. | Keep separate runtime lanes for realtime studio interaction, batch ingestion, scheduled refresh, offline eval, and precomputed retrieval/index jobs. |
| Silent failures and observability | Stanford CS329S Lecture 10 emphasizes that ML systems can fail silently and require monitoring of operational metrics, ML performance, prediction distributions, features, raw inputs, logs, dashboards, alerts, and observability metadata. | Instrument source-to-output traces so unsupported claims, retrieval misses, stale sources, provider fallbacks, and subgroup/topic quality drops are observable before users lose trust. |
| Production platform lifecycle | Uber Michelangelo, Metaflow, and Google Cloud MLOps converge on managed lifecycle infrastructure: data/features, training, evaluation, deployment, serving, monitoring, automation, metadata, and production orchestration. | Agent Studio should treat every content pipeline as a production lifecycle with durable metadata, parity checks, versioned artifacts, orchestration, monitoring, and rollback. |

## Agent Studio Design Decisions Strengthened

- Keep the local Postgres/pgvector store as the durable source of traces, source ledgers, artifact versions, user feedback, and evaluation records.
- Preserve separate execution classes for realtime dialogue, background ingestion, batch refresh, and offline evals.
- Make trace grading and source-ledger grading mandatory before enabling higher-autonomy profiles.
- Require versioned prompts, chain definitions, retrieval datasets, source manifests, and model/provider settings for reproducibility.
- Add SLOs and golden signals for the product, not only model metrics: latency, traffic, error rate, saturation, retrieval quality, fallback rate, cost, and user trust signals.
- Treat controlled autonomy as a product requirement: least-privilege tools, human approval, redaction, guardrails, and explicit blocked states.
- Add CS329S-style stakeholder/objective framing to ingestion and agent capability specs.
- Monitor Agent Studio as a living ML system whose data, business goals, and user behavior shift over time.
- Use production-platform patterns for workflow versioning, candidate comparison, automated triggers, metadata ledgers, and delayed feedback labels.

## Canon Status

The direct-read notes for Building ML Powered Applications chapters 1-11 are canon-ready for Agent Studio system-design decisions. Future platform sources may refine implementation details, but the core design lessons are sufficiently cross-checked.
