---
type: lecture-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
course: "Stanford CS329S Machine Learning Systems Design"
source_status: official_public
sources:
  - https://stanford-cs329s.github.io/index.html
  - https://stanford-cs329s.github.io/syllabus.html
  - https://docs.google.com/document/d/1C3dlLmFdYHJmACVkz99lSTUPF4XQbWb_Ah7mPE12Igo/edit
  - https://docs.google.com/document/d/1hNuW6bqWYZjlwpit_8W1cu7kllb-jTfy3Liof1GJWug/edit
  - https://docs.google.com/document/d/14uX2m9q7BUn_mgnM3h6if-s-r0MZrvDb-ZHNjgA1Uyo/edit
retrieval_method: "official course site plus public Google Docs lecture-note links"
rights_strategy: "links-and-original-synthesis-only"
---

# Stanford CS329S - ML Systems Design

## Source Reading Scope

Official sources read:

- Course overview and syllabus.
- Lecture 1: Machine Learning Systems in Production.
- Lecture 8: Model Deployment.
- Lecture 10: Data Distribution Shifts and Monitoring.

Current-source check on May 18, 2026 verified the official CS329S course overview, syllabus, and public Google Docs links for Lecture 1, Lecture 8, and Lecture 10. This note stores compact original synthesis only. It does not store full lecture notes, transcript dumps, copied slide text, or long excerpts.

## Material Takeaways

CS329S frames ML systems design as the process of choosing software architecture, infrastructure, algorithms, data, and interfaces to satisfy concrete requirements. The course starts from stakeholders and objectives because different objectives create different system choices. This directly confirms the Building ML Powered Applications position that model work should start from product goals, constraints, and metrics.

Lecture 1 makes the production distinction explicit: the ML algorithm is only one part of a deployed system. A production ML system includes user/developer interfaces, data stack, hardware, deployment path, monitoring, and update mechanics. It also defines durable requirements around reliability, scalability, maintainability, and adaptability. The key warning is that ML systems fail silently, because the software call can succeed while the prediction is wrong.

The lecture's "when to use ML" filter is practical: ML fits problems with learnable complex patterns, available or collectible data, predictive structure, similar future data, scale, and tolerance for errors. It warns against ML when the task is unethical, simpler solutions work, or the solution is not cost-effective. This reinforces a baseline-first Agent Studio design rule.

Lecture 8 separates deployment modes by product requirement. Batch prediction favors throughput and precomputation; online prediction favors responsiveness and low latency; hybrid systems are normal. It also warns that separate training/batch and inference/streaming paths create bugs when feature logic diverges. Deployment constraints should influence model and data design before launch.

Lecture 10 treats monitoring as a permanent part of the ML lifecycle. Deployed models degrade because feedback loops, training-serving skew, edge cases, distribution shifts, software failures, and business changes all affect production behavior. Good monitoring tracks operational metrics and ML-specific performance, but observability needs logs, dashboards, alerts, trace IDs, metadata, and sliceable runtime outputs so failures can be debugged without shipping new instrumentation.

## Agent Studio Design Implications

- Keep product goal, stakeholder, metric, risk, and deployment mode in every source-backed capability spec.
- Preserve deterministic and simpler baselines before adding RAG, multi-agent routing, or large-model expert steps.
- Treat Agent Studio as a system made of interfaces, data stores, model/provider paths, orchestration, monitoring, and update loops, not as a model wrapper.
- Separate runtime classes explicitly: realtime online interaction, batch ingestion, scheduled refresh, offline evaluation, and precomputed retrieval/index jobs.
- Avoid train/serve and ingest/query skew by versioning extraction, chunking, metadata, embedding, ranking, and prompt logic together.
- Monitor for silent failures: unsupported claims, stale sources, retrieval misses, hallucination, user override spikes, latency regressions, cost spikes, provider fallback spikes, and subgroup/topic-specific quality drops.
- Use trace IDs and structured metadata so every generated artifact can be traced through source records, retrieval candidates, prompts, tool calls, model/provider calls, guardrails, and feedback.
- Make dashboards useful to non-engineering reviewers by surfacing product/business metrics next to system and model metrics.

## Production ML Systems Release Gate

Agent Studio should require a `production_ml_system_release_gate` before an ML/LLM-backed capability, source-ingestion route, retrieval index, or agent workflow becomes production-facing. The gate should include:

- product objective, stakeholders, user-visible success metric, business metric, and known harm/risk class;
- baseline decision: deterministic, manual, rules, retrieval-only, prompt-only, or existing route, with evidence for why ML/agent complexity is needed;
- deployment mode: online, realtime, batch, scheduled, hybrid, edge/local, or managed-provider path with latency, cost, privacy, and freshness rationale;
- training-serving or ingest-query parity plan for feature logic, extraction, chunking, metadata, embeddings, prompts, and ranking policy;
- operational monitors for availability, latency, error rates, queue depth, provider fallback, cost, and data freshness;
- ML/product monitors for unsupported claims, stale sources, retrieval misses, hallucination, reviewer override rate, user correction rate, slice quality, and distribution shift;
- trace and metadata contract linking artifacts back to source records, retrieval candidates, prompts, tools, model calls, guardrails, reviewers, and feedback;
- alert policy, owner, dashboard, review cadence, mitigation playbook, fallback path, and rollback target.

This gate captures the CS329S lesson that a correct API call is not the same as a working ML system. Agent Studio should prove the full production loop: objective, baseline, deployment, parity, monitoring, debugging, update, and rollback.

## Failure Modes To Guard Against

- Treating "the model responded" as proof that the system worked.
- Choosing online, batch, cloud, or edge deployment as a default instead of deriving it from latency, cost, privacy, and freshness needs.
- Maintaining separate ingestion and serving transformations without versioned parity checks.
- Monitoring too many low-level feature signals and creating alert fatigue while missing user-visible quality loss.
- Waiting for ground-truth labels that arrive too late to catch production failures.

## Cross-Links

- [[../../01-sources/official-open/building-ml-powered-applications-cross-check]]
- [[../../02-books/building-ml-powered-applications/chapters/1-from-product-goal-to-ml-framing]]
- [[../../02-books/building-ml-powered-applications/chapters/9-choose-your-deployment-option]]
- [[../../02-books/building-ml-powered-applications/chapters/10-build-safeguards-for-models]]
- [[../../02-books/building-ml-powered-applications/chapters/11-monitor-and-update-models]]

## Related Official Video Sources

The CS329S public notes and slides are the source truth used here. The current vault evidence does not contain public full-lecture video URLs for the covered lectures, so no CS329S video note is promoted.

| Video source | URL | Relevant topics | Status |
|---|---|---|---|
| CS329S lecture recordings | Official course page notes enrolled/SCPD recording boundary in the video coverage matrix | ML systems lifecycle, deployment, monitoring, update loops | recording boundary tracked; no public full-watch source ingested |
