---
type: concept
project: agent-studio
status: active
updated: 2026-05-29
owners:
  - principal-software-engineer
  - backend-platform-engineer
  - scalability-reliability-engineer
  - inference-systems-engineer
confidence: high
source_notes:
  - [[../../raw/articles/2026-05-17-production-agent-system-design-canon]]
related:
  - [[three-tier-agent-memory]]
  - [[../ops/codex-obsidian-working-memory]]
  - [[../../00-system-design/HLD - Agent Studio]]
  - [[../../00-system-design/LLD - Agent Studio]]
---

# Production Agent System Design Canon

## Summary

Agent Studio should be designed as a durable AI product platform, not a pile of prompts or HTML pages. The foundation is Postgres + pgvector durability, explicit A2A-style agent contracts, realtime provider boundaries, OpenRouter/LiveKit/Kokoro live dialogue, retrieval-quality gates, layered guardrails, Obsidian-first planning memory, and observable long-running orchestration.

## Design Patterns To Apply

### Data-Intensive System Patterns

- Keep one source of truth for runs, events, checkpoints, feedback, sources, claims, artifacts, memories, and provenance.
- Treat event logs and checkpoints as complementary: events explain what happened; checkpoints let state machines resume.
- Make write paths idempotent so retries, worker restarts, and autonomous passes do not duplicate work.
- Design schema evolution and migrations before storing new artifact or agent-message shapes.
- Use derived read models and generated viewers only as projections from durable state.

### ML System Patterns

- Treat data quality, source quality, memory quality, and evaluation as part of the core product.
- Track precision, recall, false positives, false negatives, source coverage, freshness, and drift in retrieval and memory ledgers.
- Use feedback loops to improve routing, drafting, review, retrieval, and guardrails.
- Keep offline evaluation and live operator feedback connected through durable artifacts and labeled relevance fields.
- For any future RL, preference-tuned, or learned agent route, record the reward functions, reward weights, aggregation mode, normalization mode, loss normalizer, train/eval split seed, cache policy, and checkpoint-to-release provenance before promotion. This is a future training/evaluation governance rule only; it does not reopen the accepted OpenRouter/LiveKit/Kokoro live-voice proof or the current external-publication blocker.
- Cross-vault source `system_design_vault/01-sources/official-open/silent-failure-surface-inventory.md` plus `system_design_vault/01-sources/official-open/accelerate-trl-silent-failure-interactions.md` hardens that future-route rule: RL/GRPO routes must make rollout, reward, training, data, topology, precision, scheduler, device-placement, and batch-splitting contracts explicit before release.

### Inference Engineering Patterns

- Start each route with latency, cost, quality, modality, context-window, and reliability requirements.
- Separate realtime speech transport from expert reasoning. The current default route is OpenRouter `deepseek/deepseek-v4-flash` over LiveKit with Kokoro spoken output; native Gemma/HF audio work is historical experiment context, not the active proof blocker.
- Record provider readiness, fallback behavior, model provenance, provider smoke evidence, timeouts, and retries.
- Treat streaming, batching, caching, warm starts, and model routing as production design decisions.

### Agent Architecture Patterns

- Prefer explicit workflows and routing when tasks have known stages.
- Use specialist agents when separation improves expertise, review quality, or ownership.
- Give each specialist an A2A-style card with capabilities, allowed models, allowed tools, inputs, outputs, handoff rules, guardrails, and skill ids.
- Keep human feedback gates in the runtime state machine, not only in chat.
- Use critic, guardrails, source-ledger, and claim-verification agents as independent review paths.

### Scale And Operations Patterns

- Define SLOs for realtime turn latency, provider readiness, retrieval quality, worker heartbeat freshness, and artifact review time.
- Add backpressure and bounded worker cycles before always-on execution.
- Gracefully degrade only when quality impact is explicit and recorded.
- Keep traces, ledgers, runtime health checks, provider operations, and foundation audits visible to the operator.
- Centralize reusable evidence, memory, and artifact provenance so future runs can reuse high-quality context.

## Required Specialist Owners

- Principal Software Engineer: architecture coherence, tradeoffs, and implementation quality.
- Backend Platform Engineer: FastAPI, Postgres/pgvector, migrations, async APIs, and data consistency.
- Frontend Experience Engineer: conversational cockpit UI, browser voice controls, source/artifact views, feedback controls, and accessibility.
- Scalability/Reliability Engineer: SLOs, capacity, backpressure, always-on safety, and degradation policy.
- Inference Systems Engineer: OpenRouter/LiveKit/Kokoro realtime provider boundaries, legacy native-Gemma/HF context, rerankers, latency/cost budgets, fallback policy, and provider-backed smoke proof.
- Context Engineering Agent: context packets, memory policy, retrieval packs, compression, and freshness.
- Retrieval Intelligence Agent: hybrid retrieval, RRF, reranking, search optimization, graph traversal, and FP/FN reduction.
- Knowledge Graph Curator Agent: source, claim, artifact, entity, and memory graph coverage.

## Non-Negotiables

- No SQLite.
- No board workflow in the product or planning system.
- Obsidian is the planning and tracking source of truth.
- Generated HTML/JSON viewers are secondary projections, not durable authority.
- Provider-free realtime rehearsal is useful for UX testing but never satisfies provider-backed smoke readiness.
- Major content claims must map to source records or be marked unsupported.

## Implementation Hooks

- Code contracts: `src/all_about_llms/agents/roster.py`, `src/all_about_llms/agents/skills.py`, `src/all_about_llms/foundation_references.py`.
- Provider readiness: `src/all_about_llms/providers/readiness.py`.
- Runtime ledgers: model routing, provider ops, runtime health, retrieval quality, source ledger, feedback resolution, realtime dialogue, foundation audit.
- Obsidian memory: [[../ops/active-codex-context]], [[../product/agent-studio-memory-layer]], [[three-tier-agent-memory]].

## Review Rule

When an architecture choice changes, update this wiki note or the HLD/LLD before treating a generated viewer as current. If the code and Obsidian disagree, reconcile the Obsidian design first, then regenerate any output viewer.
