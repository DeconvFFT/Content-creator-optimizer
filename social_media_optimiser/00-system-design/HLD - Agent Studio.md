---
type: hld
project: agent-studio
status: draft
updated: 2026-05-17
owners:
  - principal-software-engineer
  - product-manager
  - interactive-note-taking-agent
---

# HLD - Agent Studio

## Purpose

Build a local-first, long-running, realtime multi-agent content studio that can interact naturally by voice or text, research current sources, create source-backed social posts, reels, and Substack articles, and improve through human feedback loops.

## System Boundary

The product app includes:

- Voice/text conversation.
- Draft previews.
- Source ledger.
- Memory policy status.
- Artifact browser.
- Feedback controls.
- Voice settings.
- Run activity.
- Bounded A2A worker continuation from the creator surface.

The first product-app implementation is the Next.js app under `frontend/next-app`. It is the creator-facing workflow, with voice-provider settings, dialogue history, run activity, automatic specialist continuation after submitted turns, manual Run agents control, source-backed draft review, platform packaging, media planning, publish-readiness checks, and feedback controls. `/cockpit` remains an operator/debug surface and the Obsidian/HTML planning viewers remain planning surfaces.

The product app does not include:

- Planning workspace.
- Work tracker.
- Obsidian design notes.

The planning system lives here in the Obsidian vault.

## High-Level Components

### Production Design Canon

The architecture follows [[../wiki/concepts/production-agent-system-design-canon]] as the durable design standard. This adds explicit production-system gates from data-intensive systems, ML system design, inference engineering, agent architecture, and reliability guidance:

- durable source-of-truth data with event logs, checkpoints, schema evolution, idempotency, and replay;
- retrieval and memory evaluation with precision, recall, false positives, false negatives, coverage, and freshness;
- provider/model routes with latency, cost, streaming, caching, batching, fallback, and smoke-test evidence;
- explicit A2A specialist ownership and human feedback gates;
- observable, scalable, loosely coupled, reliability-first runtime behavior.

### Realtime Dialogue Layer

Owns natural interaction: speech-to-speech, turn-taking, interruption, spoken replies, and text fallback.

Current production direction: OpenRouter (`deepseek/deepseek-v4-flash`) for live dialogue reasoning, LiveKit for transport, and Kokoro for spoken output.

- Dialogue reasoning: OpenRouter chat completions with `deepseek/deepseek-v4-flash`; raw microphone PCM is not sent to OpenRouter.
- TTS layer: `hexgrad/Kokoro-82M`.
- Transport: LiveKit public media transport first; Pipecat is optional for internal pipeline processors.
- Rust realtime edge: Axum/Tokio control, Silero VAD through ONNX, bounded audio buffers, and barge-in cancellation.
- Python agent engine: asyncio state, OpenRouter reasoning calls, Kokoro streaming, context pruning, and durable turn/event recording.

Important boundary: the current OpenRouter route is text-turn live dialogue over LiveKit with Kokoro speech output, not native audio-to-audio reasoning. Earlier Gemma/HF audio-understanding work is historical/native-audio background and is not the active realtime default.

Production rule: raw browser PCM WebSockets are not the production voice transport. Raw WebSockets may exist only as an explicitly marked local dev adapter.

See [[../02-research/Realtime Voice Architecture - Gemma Kokoro LiveKit Rust Python]].

Provider readiness now exposes a smoke walkthrough for the selected realtime provider. A live smoke run must record a realtime session, selected transport framework, routed turn, spoken response plan, context-pruning policy, barge-in policy, and realtime dialogue ledger before voice readiness is considered proven.

The cockpit also supports a provider-free realtime rehearsal mode. Rehearsal sessions let the browser voice controls, routing path, spoken response plan, and realtime dialogue ledger be tested before credentials exist, but they are explicitly marked `dry_run` and never satisfy provider-backed smoke readiness.

Runtime health now treats the local Rust voice edge as an operator-visible readiness surface. The ledger should run the persistent `voice-edge --jsonl` benchmark when the binary exists and record latency plus false-positive / missed-speech / missed-cancellation counts. This proves only the local edge contract; end-to-end voice readiness is tracked separately by the LiveKit room timing ledger with OpenRouter dialogue reasoning and Kokoro output in the loop.

The first LiveKit room timing ledger is now implemented as durable evidence. Voice-agent events from the LiveKit data channel are persisted through FastAPI, sanitized before storage, and assembled into `realtime_voice_timing_ledger` artifacts. Readiness requires a correlated chain for one session/turn/response: LiveKit readiness, speech start, user-turn commit, OpenRouter/Kokoro turn start, first text/audio output, and barge-in cancellation plus turn-cancelled proof.

Vault memory rule: `social_media_optimiser/` and `system_design_vault/` must stay in sync. A background vault-sync subagent runs every 5 minutes and should reconcile architecture decisions, implementation evidence, research notes, and work-tracking updates between the two vaults without blocking product implementation. The same planning boundary now includes the Leibniz review-watch escalation loop in `03-review-packets/agent-studio-feedback-loop-map.html`: standing reviewer `019e3899-5ab3-7171-9d3c-32e7c57bbde7` stays quiet when there are no Critical/Important findings, and material findings surface with severity, files, and next action.

### Orchestration Layer

Owns durable state machines, A2A-style handoffs, worker profiles, checkpoints, resume plans, event streams, and human feedback gates. This follows LangGraph-style durable orchestration.

The A2A compatibility surface is discoverable but scoped. The well-known Agent Card at `/.well-known/agent-card.json`, the `/api/a2a` interface root, and the interactive A2A map all advertise the same public task-inspection policy: use `projection=public` for external-safe reads, apply `agent-message-public-projection-v1`, and support that projection on `getTask`, `listRunMessages`, and `agentInbox` while keeping mutation routes private. This keeps local AgentMessage execution truthful without leaking provider payloads through public discovery.

### Expert Agent Layer

OpenRouter is the active default for live dialogue reasoning and specialist reasoning unless a later decision explicitly changes provider policy. Gemma 4/Hugging Face cloud endpoints are legacy or future native-audio experiment context, not current implementation defaults and not current live voice blockers. Gemma does not own WebRTC/media transport, and Kokoro owns speech waveform synthesis.

The readiness gate treats OpenRouter `deepseek/deepseek-v4-flash`, LiveKit, Kokoro, the backend event sink, and Rust voice edge as the active live-dialogue proof path. A future native Gemma audio proof must be labeled separately and must not block the OpenRouter route.

The engineering specialist layer now includes explicit Backend Platform Engineer, Frontend Experience Engineer, Scalability/Reliability Engineer, and Inference Systems Engineer roles so system design, implementation, UI, scale, and provider operations are separately owned.

### Retrieval Intelligence Layer

Owns query rewriting, hybrid search, rank fusion, reranking, graph traversal, knowledge graph construction, coverage checks, and false-positive/false-negative reduction.

See [[02-research/Retrieval Intelligence and Knowledge Graph Research]].

Current implementation surface:

- Retrieval Intelligence Agent is now an explicit roster agent.
- Knowledge Graph Curator Agent is now an explicit roster agent.
- `POST /api/runs/{run_id}/retrieval-quality-ledger` creates a durable retrieval quality artifact.
- Retrieval quality status can be `ready`, `needs_rerank`, `needs_more_recall`, or `blocked`.
- Local reranking has two provider paths: the deterministic Python fallback and the optional Rust retrieval-ranker subprocess selected with `RERANKER_PROVIDER=rust`.

Research direction: retrieval must remain multi-stage: query rewriting, dense plus lexical plus web plus graph candidate fanout, rank fusion, top-K reranking, evidence acceptance, contradiction/freshness checks, and FP/FN evaluation before content synthesis. Postgres + pgvector remains the canonical v1 store; Qdrant, Elasticsearch, Neo4j, or other specialized indexes can be added behind provider interfaces only after benchmark evidence justifies them.

### Durable Knowledge Layer

Postgres + pgvector stores runs, events, checkpoints, feedback, source ledgers, artifacts, memories, semantic retrieval data, and provenance. No SQLite fallback.

### Obsidian Memory Operating System

The Obsidian vault is the human-readable project memory layer. It follows [[../SCHEMA|SCHEMA]]:

- `raw/` stores append-only source captures, feedback, and run observations.
- `wiki/` stores durable synthesized project knowledge.
- `output/` stores generated JSON, HTML, review packets, reports, and handoff artifacts.
- Typed `user_preference` and `project_decision` memories are stored in Postgres + pgvector through `POST /api/runs/{run_id}/project-memory`.
- Context packets surface memory health so stale, low-confidence, or conflicting project memories do not silently steer agents.
- Autonomous passes can export selected memory summaries as Obsidian output handoffs without rewriting canonical wiki notes.

See [[../wiki/product/agent-studio-memory-layer]] and [[../wiki/ops/codex-obsidian-working-memory]].

### Artifact and Review Layer

Generated content is not final until major claims map to source records or are marked unsupported, reviewer decisions are recorded, and feedback gates are resolved.

## Core Flow

1. User speaks or types a request.
2. Realtime Conversation Host captures the turn.
3. Intent Router classifies create, revise, research, route, or clarify.
4. Retrieval Intelligence Layer gathers and ranks evidence.
5. Retrieval quality ledger records candidate ranking, accepted evidence, graph coverage, precision risks, recall gaps, and recommended follow-up queries.
6. Accepted retrieval evidence becomes the preferred evidence packet for source ledger, context packets, resume plans, and specialist writer revisions.
7. Source Ledger and Claim Verification agents validate claims.
8. Claim revision plans create targeted writer/editor follow-up tasks when accepted evidence does not support a claim.
9. Artifact Librarian records the claim revision closure ledger and blocks publishing handoff while the loop remains open.
10. Guardrails and review agents gate publishing.
11. User feedback becomes structured feedback routed to the right agent.
12. Always-on worker profiles stop for human confirmation when project-memory policy status shows precision risk, recall gap, graph-only context, or regression.
13. The Next.js product app exposes the creator flow: text/voice input, bounded A2A continuation, draft review, copy/export/revise, source/claim evidence, platform package generation, media planning, publish-readiness checks, feedback resolution, and run restore.
14. The product cockpit exposes run timeline, source ledger, accepted-evidence drilldowns, project-memory recording, provider-free demo run loading, feedback gates, context packets, and memory policy so the operator can see why the system is ready or blocked.
15. A provider-free demo run can seed official-documentation sources, supported claims, draft artifacts, retrieval quality, source ledger, a feedback gate, and project memory so the cockpit is functional before external provider keys exist.
16. Provider-free realtime rehearsal can exercise voice dialogue UX and durable routing before provider secrets are configured, while the walkthrough ledger still requires a non-rehearsal session from the selected realtime provider for provider-backed smoke.
17. The cockpit walkthrough ledger packages runtime health, provider readiness, provider-free demo proof, source coverage, realtime smoke state, provider observability, and feedback-loop state into one run-level proof packet.
18. Obsidian review notes, memory-promotion proposals, and autonomous memory summaries keep reusable project knowledge out of chat context.
19. Checkpoints, event logs, retrieval ledgers, claim revision ledgers, walkthrough ledgers, and context packets make the run resumable.

## Open Design Questions

- Should Retrieval Intelligence and Knowledge Graph Curation become two explicit new agent cards, or one combined agent?
- Resolved: they are two explicit agent cards so retrieval ranking and graph coverage can evolve independently.
- Which reranker should be the default local/cloud option for v1?
- Resolved for local v1: deterministic Python remains the default fallback; Rust retrieval-ranker is an opt-in low-latency local provider behind `RERANKER_PROVIDER=rust`.
- Should the knowledge graph live in Postgres tables first, or should we introduce a graph database only if traversal needs exceed Postgres?
- Resolved for run handoffs: autonomous passes write compact memory summaries to `output/reports/autonomous-memory-summaries/{run_id}/memory-summary.md` when requested.
- Resolved for risky always-on memory use: worker-profile heartbeats open structured feedback gates before execution when project-memory policy status is `needs_precision_review`, `needs_recall_repair`, `graph_only_review`, or `regressed`.

## Planning Interface Rule

Obsidian notes are the source of truth for HLD, LLD, decisions, sprint state, research, feedback, and review packets. HTML is not the planning source; it is only a companion visualization when a specific flow needs animation or visual inspection.

When implementation direction changes, update the relevant Obsidian notes before or alongside code. The working contract is vault-first communication, not HTML-first planning.

Generated inspection artifacts:

- `output/viewers/agent-studio-system-design.json`
- `output/viewers/agent-studio-system-design-viewer.html`

These artifacts must be regenerated from Obsidian state when the architecture changes.
