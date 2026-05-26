---
type: decision-log
project: agent-studio
status: active
updated: 2026-05-17
---

# Decision Log

## 2026-05-17 - Obsidian Is The Planning Source Of Truth

Decision: use `social_media_optimiser/` as the system design, tracking, research, and review workspace.

Implication: major planning updates should be Obsidian-native notes first. Interactive HTML is allowed only as a companion render when it helps review complex flows.

Clarification: do not make HTML the center of project communication or tracking. The vault notes are the canonical working surface.

## 2026-05-17 - Retrieval Intelligence Is A First-Class Requirement

Decision: retrieval quality is part of the core harness, not a later optimization.

Implication: the system needs query rewriting, hybrid search, RRF, reranking, knowledge graph traversal, coverage checks, and explicit FP/FN reduction metrics.

Implementation status: Retrieval Intelligence Agent, Knowledge Graph Curator Agent, retrieval quality skill, retrieval tables, and the run-level retrieval quality ledger endpoint are now in the foundation.

Next implementation decision: retrieval quality must run inside the autonomous pass and be included in resume/context handoffs, not remain a manually triggered endpoint only.

Implementation update: retrieval quality now participates in autonomous pass gating, context packets, resume summaries, completion event payloads, and queryable Postgres retrieval/graph/evaluation rows.

## 2026-05-17 - Obsidian Review Notes Are Durable Artifacts

Decision: run review notes should be written as vault-native Obsidian notes and also recorded as artifacts/events.

Implication: the Interactive Note-Taking Agent should produce Markdown notes under `social_media_optimiser/03-review-packets/runs/` for durable review, while HTML notes remain optional companion views.

Implementation update: `POST /api/runs/{run_id}/obsidian-review-note` and the `generate_obsidian_review_note` A2A worker path now write vault-native notes and record `obsidian_note` artifacts plus `obsidian_review_note_generated` events.

## 2026-05-17 - Reranking Is A Provider Boundary

Decision: reranking should be provider-neutral instead of hardwired inside retrieval quality.

Implication: the retrieval workflow should call a `RerankerProvider` interface. The first provider is deterministic and local for repeatable tests; later providers can point at HF/cloud rerankers without changing orchestration contracts.

Implementation update: `RerankRequest`, `RerankCandidate`, `RerankResult`, and `RerankerProvider` now live in provider interfaces. `DeterministicRerankerProvider` is the default local provider, and retrieval-quality artifacts persist the reranker id and decision reason per candidate.

## 2026-05-17 - Product App Boundary Remains Clean

Decision: product app is a conversational studio, not a planning tracker.

Implication: Obsidian can track work and design. The app should focus on dialogue, drafts, sources, artifacts, feedback, voice settings, and run activity.

## 2026-05-17 - Accepted Retrieval Evidence Feeds Context First

Decision: once a retrieval quality ledger exists, accepted source-linked candidates should be the preferred evidence set for source ledgers, context packets, resume plans, and specialist writer revisions.

Implication: raw source order remains a fallback only when no accepted retrieval evidence exists. This reduces false positives by avoiding weak candidates and reduces false negatives by surfacing recall gaps and recommended follow-up queries before final drafting.

Implementation update: `retrieval_evidence.py` now parses the latest retrieval-quality ledger and promotes accepted source-linked candidates into source-ledger metadata, context packet source evidence, resume-plan summaries, and specialist writer artifact source dependencies.

## 2026-05-17 - Accepted Evidence Is A Claim Gate

Decision: accepted retrieval evidence must participate in claim and editorial gates, not only context selection.

Implication: when a retrieval-quality ledger contains accepted source-linked candidates, Claim Verification, Editor-in-Chief, and Publish Readiness should treat claims or artifacts with no accepted-evidence overlap as not publish-ready.

Implementation update: Claim Verification now records accepted-evidence claim counts and marks no-overlap claims unsupported. Editor-in-Chief review decisions record accepted retrieval source ids and block no-overlap claims. Publish Readiness now blocks no accepted retrieval evidence, claim no-overlap, and artifact no-overlap cases.

## 2026-05-17 - Claim Failures Need Writer-Facing Plans

Decision: claim gate failures should produce a durable rewrite/hold artifact, not only status flags and events.

Implication: writer agents need explicit held claim ids, rewrite actions, source alternatives, and accepted-evidence context before they create revised drafts.

Implementation update: Claim Verification now records `claim_revision_plan` artifacts for unsupported, needs-review, missing-source, or no-accepted-evidence claims. Writer artifacts include applicable claim revision context in content and provenance.

## 2026-05-17 - Claim Revision Plans Route Follow-Up Work

Decision: a claim revision plan should create targeted A2A follow-up tasks automatically.

Implication: Claim Verification now routes the plan to ELI5/Substack writers, Script Doctor, and Editor-in-Chief with idempotency signatures. Editor follow-up waits on newly created writer/script follow-ups when they are created in the same pass.

## 2026-05-17 - Claim Revision Needs A Closure Ledger

Decision: claim revision should have an explicit closure ledger rather than requiring humans or manager agents to infer state from scattered plan artifacts and A2A tasks.

Implication: Artifact Librarian and Product Manager handoffs should report whether held claims remain open, which follow-up tasks are pending/completed/blocked, and whether revised artifacts exist.

Implementation update: Artifact Librarian now records `claim_revision_ledger` artifacts. Publishing handoff and Product Manager sync pulse surface the latest closure status and block while claim revision follow-ups, revised artifacts, reverification, or editor review remain open.

## 2026-05-17 - Obsidian Is The Primary Planning Surface

Decision: HLD, LLD, sprint state, decisions, feedback, and review packets should live in Obsidian first.

Implication: HTML remains available only as a companion visualization when a specific architecture flow needs animation or visual inspection. It is not the canonical planning or tracking surface.

Implementation update: the vault now has a three-tier memory operating system: `raw/` for append-only captures, `wiki/` for synthesized durable knowledge, and `output/` for generated JSON, HTML, reports, and handoffs. Codex should use the wiki lookup path before broad context loading.

## 2026-05-17 - Memory Promotion Must Be Proposed Before Applied

Decision: run-derived memory should first become a proposed wiki-memory update, not an automatic rewrite of canonical wiki pages.

Implication: `POST /api/runs/{run_id}/obsidian-memory-promotion` and the `generate_obsidian_memory_promotion` A2A task create `obsidian_memory_promotion` artifacts under `wiki/run-memory-promotions/{run_id}/`. A human or later approved agent pass can apply stable lessons to wiki notes.

## 2026-05-17 - User Preferences And Project Decisions Are Typed Memories

Decision: durable user preferences and project decisions should be first-class memory records, not only generic notes.

Implication: `POST /api/runs/{run_id}/project-memory` and `record_project_memory` write `user_preference` or `project_decision` records to the Postgres + pgvector memory store with explicit scope, source run, confidence, tags, source artifacts, and target wiki notes.

## 2026-05-17 - Memory Health Gates Context Use

Decision: retrieved project memories should be checked before agents use them as current policy.

Implication: context packets now report `summary.memory_health` and create risks for stale, low-confidence, or conflicting project memories. Product Manager or Forward Deployed Engineer review should resolve conflicts before policy-sensitive autonomous work.

## 2026-05-17 - Autonomous Passes Export Memory Summaries As Output

Decision: autonomous passes may export selected memory summaries to Obsidian, but those summaries are output handoffs rather than canonical wiki updates.

Implication: `export_memory_summary_to_obsidian = true` on `POST /api/runs/{run_id}/autonomous-pass` writes `output/reports/autonomous-memory-summaries/{run_id}/memory-summary.md`, records an `obsidian_note` artifact, and emits `obsidian_memory_summary_exported`. Durable wiki policy still changes through reviewed wiki edits or explicit project-memory records.

## 2026-05-17 - Risky Project Memory Blocks Always-On Execution

Decision: always-on worker profiles must stop for human confirmation before execution when project-memory policy status is `needs_precision_review`, `needs_recall_repair`, `graph_only_review`, or `regressed`.

Implication: project-memory false positives and false negatives are treated as operational gates, not just observability metrics. The Agent Harness Engineer opens a structured `project_memory_policy_confirmation` feedback item for the Forward Deployed Engineer, moves the run to `waiting_for_human`, and records blocked heartbeat artifacts instead of running worker cycles or autonomous passes.

## 2026-05-17 - Production System Design Canon Is A Foundation Contract

Decision: Agent Studio architecture must follow [[../wiki/concepts/production-agent-system-design-canon]] rather than treating the project as a prompt collection or HTML planning exercise.

Implication: data durability, event logs, checkpoints, schema evolution, retrieval evaluation, ML feedback loops, inference latency/cost budgets, provider smoke evidence, SLOs, observability, and A2A specialist ownership are foundation requirements.

Implementation update: foundation references now include DDIA, Chip Huyen/O'Reilly ML systems, Baseten inference engineering, Anthropic effective agents, OpenAI agent guardrails, AWS ML Lens, Google Cloud AI/ML reliability, Uber Michelangelo, and Netflix/Metaflow. The roster now includes Backend Platform Engineer, Frontend Experience Engineer, Scalability/Reliability Engineer, and Inference Systems Engineer. Project skills now include system architecture, frontend engineering, and inference reliability.

## 2026-05-17 - Separate System Design Vault Uses Local Books As A Corpus

Decision: create `system_design_vault/` as a separate Obsidian workspace for deep system design source ingestion and architecture notes.

Implication: the existing `social_media_optimiser/` vault remains the active project planning/tracking memory. The new vault is for system design canon, source inventories, book scaffolds, and HLD/LLD learning. HTML/JSON viewers remain companion inspection outputs only.

Implementation update: the vault now includes official/open source notes, a local `/Users/saumyamehta/DS interview prep/books` corpus inventory, a PDF scaffold generator, and chapter-note scaffolds for five local user-provided books. The workflow creates compact original notes and design implications, not raw extracted book text.

## 2026-05-17 - Feynman Owns Background Ingestion Autonomously

Decision: the background agent `Feynman` owns the ingestion and source-note lane without main-thread polling.

Implication: the main implementation loop should focus on the product architecture and code. `Feynman` should interrupt only for concrete blockers such as missing file access, extraction failure, provenance ambiguity that changes whether a source can be used, or architecture conflicts that affect product design.

Implementation update: `Feynman` was given standing autonomy, the local books corpus remains in scope, and compact book synthesis now feeds the separate `system_design_vault` HLD/LLD and production Agent Studio canon.

## 2026-05-17 - Provider Smoke Is Durable And Live Calls Are Explicit

Decision: provider smoke belongs in a run-level ledger rather than only in static readiness notes.

Implication: every smoke attempt should record what was proven, what was skipped, what is blocked by configuration, source ids, realtime session ids, latency class, and smoke-proof status. External provider calls must stay opt-in so local runs can audit blockers without accidental network calls or provider spend.

Implementation update: `POST /api/runs/{run_id}/provider-smoke` records a `provider_smoke_ledger` artifact and `provider_smoke_ledger_built` event. The cockpit exposes Provider smoke separately from Provider ops and uses a Live smoke checkbox for `execute_live_calls=true`.

Implementation update: autonomous studio passes now build provider smoke by default before provider operations, and context packets include the latest provider-smoke ledger so always-on profiles inherit provider-readiness blockers/proof.

## 2026-05-17 - Voice Runtime Uses Gemma 4 E4B Plus Kokoro Over LiveKit

Decision: the production live voice path should be Gemma-first without OpenAI Realtime as the default. Use `google/gemma-4-E4B-it` for native audio understanding and reasoning, `hexgrad/Kokoro-82M` for TTS, and LiveKit as the public production transport framework. Pipecat is optional for internal pipeline composition.

Implication: raw browser PCM WebSockets are not an acceptable production voice transport. A raw WebSocket adapter may exist only for local development and must be marked non-production.

Architecture rule: use a Rust realtime edge for low-latency VAD, buffer control, concurrency control, and barge-in cancellation. Use the Python agent engine for async Gemma/Kokoro model calls, context pruning, and durable state updates.

Golden rules:

- prune raw audio after 3 turns and replace it with transcript plus compact summary;
- route production audio through LiveKit, not custom browser WebSockets;
- on barge-in, Rust must drop outbound audio, cancel Python/Gemma work, and clear Kokoro buffers immediately.

Research note: [[../02-research/Realtime Voice Architecture - Gemma Kokoro LiveKit Rust Python]]

## 2026-05-24 - OpenRouter LiveKit Kokoro Supersedes Gemma-First Default

Decision: the current production live-dialogue default is OpenRouter `deepseek/deepseek-v4-flash` text reasoning over LiveKit with Kokoro spoken output. Gemma/Gamma/Hugging Face/MLX setup is legacy or future native-audio work unless explicitly re-promoted in a new decision.

Implication: missing Gemma/Gamma/HF/MLX endpoints must not block the current realtime dialogue proof path. The provider-backed live voice proof is accepted for run `190ae2f9-a74b-4a23-b39c-aaf2d636bd8e`; the remaining completion blocker is external publication proof followed by closure review.

Architecture rule: keep LiveKit as the production transport and keep raw microphone PCM out of OpenRouter. Current OpenRouter proof uses bounded text-turn dialogue evidence plus Kokoro audio output evidence; native-audio experimentation must stay separately labeled.

Implementation update: the 2026-05-17 deeper research pass clarified that Gemma 4 E4B should be described as the native audio-understanding and reasoning leg with text output. Kokoro remains the TTS waveform leg. Live voice should avoid cold scale-to-zero endpoints; warm HF/Gemma and Kokoro capacity is required before provider-backed smoke can be considered interactive.

## 2026-05-17 - Retrieval Uses Multi-Stage Evidence Selection

Decision: retrieval should use candidate fanout, rank fusion, top-K reranking, evidence acceptance, contradiction/freshness checks, and FP/FN evaluation as one pipeline.

Implication: dense vector search, lexical search, web search, and graph traversal all produce candidates; none of them alone should decide final context. The source ledger and claim verifier should consume accepted evidence plus retrieval-quality warnings, not raw search results.

Implementation direction: Postgres + pgvector remains the canonical v1 store. Specialized indexes such as Qdrant, Elasticsearch, or Neo4j can be added behind provider interfaces only after benchmark evidence shows that the v1 hybrid stack is insufficient.

## 2026-05-18 - Spark Review Subagent After Implementation Slices

Decision: keep `Leibniz` open as the standing `gpt-5.3-codex-spark` review subagent for implementation quality checks.

Implication: after each meaningful implementation slice, the main thread sends `Leibniz` a concise read-only review request for correctness, code bloat, cleanliness, test coverage, and out-of-box usability, then fixes material findings before closeout.

## 2026-05-18 - Rust Voice Edge HTTP Sidecar Is Current But Stateless

Decision: the Rust voice edge now has an Axum/Tokio HTTP sidecar in addition to stdin and persistent JSONL.

Implication: the current Python LiveKit participant keeps using persistent JSONL for frame-by-frame VAD and barge-in calls, while HTTP gives a supervised typed service boundary for local serving and tests. This entry described the first sidecar cut; later entries supersede the VAD implementation details with real Silero ONNX inference and bounded recurrent stream state. The HTTP boundary remains request/response transport and is still not the direct LiveKit Rust media bridge.

Implementation update: Python now has `RustVoiceEdgeHttpClient`. Setting `RUST_VOICE_EDGE_HTTP_URL` opts the LiveKit participant into the HTTP sidecar; otherwise it keeps using persistent JSONL. Both paths share the same request builder and cancellation parser.

Review update: HTTP health is accepted only when the sidecar proves `service=voice-edge`, `transport=http`, `request_contract=voice_edge_request_v1`, and `state_model=stateless_request_response`. The HTTP+JSONL fallback wrapper preserves the primary VAD backend/model/fallback policy, and readiness distinguishes preflight-selected transport from the runtime wrapper transport.

## 2026-05-18 - Silero ONNX Is Linked Behind the Existing Rust VAD Contract

Decision: keep `deterministic_energy` as the default local backend, but make `silero_onnx` a real Rust inference path using the bundled `silero` crate model unless `vad_model_path` points to a custom ONNX file.

Implication: `vad_threshold` remains the deterministic RMS threshold, while `vad_probability_threshold` controls Silero speech probability. Failed Silero load/inference follows `allow_vad_fallback`: fallback to deterministic energy when allowed, conservative non-speech when disabled. Silero ONNX sessions are cached in a bounded process-wide pool keyed by model source and session id, so model bootstrap is not repeated per VAD request and concurrent sessions are not forced through a single global session.

## 2026-05-18 - Silero Recurrent Stream State Is Preserved Per Rust Session Slot

Decision: keep the HTTP and JSONL contracts request-scoped, but preserve bounded Silero `StreamState` entries inside the long-running Rust process.

Implication: each Silero session-pool slot now keeps an LRU-bounded stream-state cache keyed by stream id and sample rate. Realtime frames for the same session reuse recurrent Silero context across JSONL/HTTP requests, while `vad_stream_state_cache_size` caps retained streams per slot. The remaining production gap is not recurrent VAD continuity; it is benchmark/tuned concurrency plus the LiveKit-side Rust media bridge.
