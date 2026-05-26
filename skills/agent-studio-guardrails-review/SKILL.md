---
name: agent-studio-guardrails-review
description: "Review multi-agent content and artifacts before approval. Use when checking unsupported claims, source coverage, safety, copyright risk, provenance, human feedback gates, model/tool boundaries, or whether an artifact is ready for user review."
---

# Agent Studio Guardrails Review

## Review Gates

1. Source gate: every important factual claim has a linked source or is marked unsupported.
2. Provenance gate: every artifact records prompt/input, model or tool, source dependencies, reviewer decisions, and revision history.
3. Boundary gate: OpenRouter DeepSeek V4 Flash handles current reasoning and critique; LiveKit handles realtime dialogue transport; Kokoro handles spoken output; imagegen handles raster assets; Gemma/Gamma/Hugging Face/MLX are legacy or non-default.
4. Feedback gate: unresolved user feedback blocks final approval.
5. Safety gate: remove or revise unsafe, misleading, overconfident, or copyright-risky content.
6. Architecture gate: record an `architecture_review` when durability, worker coverage, provider boundary, or feedback-gate risks need engineering triage.
7. Observability gate: record a `run_health_report` when agent tasks fail, provider fallback happens, tool/model policy denies execution, or feedback/guardrail blockers remain open.
8. Skill contract gate: build a `skill_usage_ledger` when manager review needs proof that processed A2A tasks used project skill cards and that skill card source paths still match actual `SKILL.md` files.
9. Model routing gate: build a `model_routing_ledger` when manager review needs proof that OpenRouter/LiveKit/Kokoro remain separate reasoning, transport, and spoken-output boundaries while web search and imagegen stay separate provider/tool boundaries.
10. Provider operations gate: build a `provider_operations_ledger` when manager review needs model/tool approvals, denials, OpenRouter usage, realtime sessions, provider fallbacks, and artifact model provenance in one place.
11. Runtime health gate: build a `runtime_health_ledger` when local Postgres, pgvector, Docker, LangGraph checkpointing, live runtime evidence, or no-SQLite boundaries need operator review.
12. Foundation audit gate: build a `foundation_audit` when manager review needs explicit pass/needs-attention/fail evidence against the non-negotiable architecture spec.
13. Feedback outcome gate: build or inspect a `feedback_resolution_ledger` before treating feedback as closed. Every feedback item must be classified as `accepted`, `revised`, `held`, or `rejected`; open, routed, pending, blocked, failed or canceled linked tasks must stay held until the specialist work is resolved or explicitly retried.

## Decisions

Return one of:

- `approved`
- `approved_with_notes`
- `needs_revision`
- `blocked`

## Required Report

- Decision
- Blocking issues
- Unsupported claims
- Source coverage gaps
- Boundary violations
- Architecture risks
- Required next agent or human action
- Skill usage/source contract status when worker skills or skill files affect the review
- Model routing status when OpenRouter, LiveKit, Kokoro, web search, imagegen, or explicitly selected legacy provider boundaries affect the run
- Run health risks and recommended operational action
- Provider operations summary when live providers or model/tool boundaries affected the run
- Runtime health status when local persistence or checkpoint readiness affects long-running work
- Foundation audit status when the review concerns architecture completeness or implementation readiness
- Feedback resolution outcome summary with accepted/revised/held/rejected counts, failed linked task ids, and the next human or agent action for held feedback
