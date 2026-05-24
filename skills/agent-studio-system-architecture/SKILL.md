---
name: agent-studio-system-architecture
description: "Use production system-design patterns for Agent Studio architecture. Apply when designing service boundaries, data models, event logs, checkpoints, A2A contracts, Postgres/pgvector storage, reliability, schema evolution, or HLD/LLD changes."
---

# Agent Studio System Architecture

## Workflow

1. Start in Obsidian: read the MOC, HLD, LLD, Decision Log, Current Sprint, and active Codex context before changing architecture.
2. Identify the source of truth for each state type: run state, events, checkpoints, memories, sources, claims, artifacts, feedback, and generated views.
3. Separate command/write paths from query/read views so artifacts and viewers can be regenerated from durable state.
4. Design write paths for idempotency, replay, schema evolution, provenance, and fault recovery.
5. Keep Postgres + pgvector as the local-first durable store. Do not add SQLite or local JSON state substitutes.
6. Use A2A-style agent cards, typed task payloads, handoff rules, and guardrails for specialist boundaries.
7. Include failure modes, backpressure, SLO implications, provider readiness, and observability before calling a design production-ready.
8. Record durable decisions in Obsidian and expose implementation evidence through foundation audits or runtime ledgers.

## Quality Targets

- Reliability: every long-running run can pause, resume, replay recent events, and stop safely at human gates.
- Scalability: the design can add workers, provider routes, retrieval candidates, and artifacts without changing core contracts.
- Maintainability: HLD, LLD, agent cards, skill cards, and tests agree on the same architecture.
- Operability: runtime health, provider readiness, model routing, retrieval quality, and feedback blockers are inspectable.

## Outputs

- `architecture_decision`
- `service_contract`
- `data_flow_review`
- `failure_mode_review`
- `scalability_plan`
- `foundation_audit_evidence`
