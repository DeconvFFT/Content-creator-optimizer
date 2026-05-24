# All About LLMs Agent Studio

Local-first foundation for a realtime, source-backed, multi-agent content studio.

## Current Capabilities

- FastAPI backend with A2A-style agent cards, a public A2A discovery card at `/.well-known/agent-card.json`, and durable message routes.
- Creator-facing Next.js app under `frontend/next-app`, with text/voice input, prompt starters, browser speech capture, voice-provider settings, session restore, run refresh, dialogue history, run activity, source-backed draft review, automatic bounded A2A worker continuation after submitted turns, a manual Run agents control, production controls for platform packaging/media planning/publish readiness, copy/export/revise actions, feedback resolution, responsive layouts, and a same-origin `/api` proxy to the FastAPI backend for local UI testing.
- Project-owned skill cards at `/api/skills`, `/.well-known/agent-skills.json`, and `/api/a2a/agents/{agent_id}/skills`, mapped onto every specialist agent. The public A2A discovery card advertises the studio as an HTTP+JSON compatibility interface, while `/.well-known/agent-cards.json` keeps the full internal specialist roster visible.
- Durable A2A task lifecycle: accepted, atomically claimed, in progress, waiting for human, completed, failed, blocked, or canceled, with explicit upstream task dependencies, durable handoff traces, stale claimed/in-progress tasks recoverable back to accepted work, and retry-exhausted tasks blocked for human review.
- Human-authorized retry at `POST /api/a2a/messages/{message_id}/retry`, so blocked/failed/canceled A2A tasks can be deliberately reset or given a higher retry cap after review.
- Local agent worker loop through `POST /api/a2a/workers/{agent_id}/run` or `all-about-llms-admin run-agent-worker`, including bounded stale-task recovery, atomic attempt counting, and retry-exhaustion blocking before polling accepted work.
- Multi-agent worker cycles through `POST /api/a2a/workers/run-cycle` or `all-about-llms-admin run-agent-cycle --watch`, with configurable stale A2A task recovery for crash-safe always-on operation.
- Bounded autonomous studio passes at `POST /api/runs/{run_id}/autonomous-pass` or `all-about-llms-admin run-autonomous-pass`, chaining checkpoint, runtime health preflight, A2A collaboration graph preflight, open-feedback preflight, worker cycle, multimodal follow-up continuation, research freshness ledger, bounded provider-backed source refresh for blocked evidence, retrieval quality ledger, media planning, distribution packaging, source ledger, guardrail audit, publish readiness, post-quality-gate artifact indexing with the latest publishing handoff, next-pass work planning, manager sync pulse, skill usage ledger, model routing ledger, provider smoke ledger, provider operations ledger, realtime dialogue ledger, feedback resolution ledger, an evidence-aware autonomous context packet artifact before audit evidence, a post-audit work-plan refresh that routes same-pass foundation remediation, a post-audit manager sync pulse, a post-audit refreshed context packet carrying foundation remediation and retrieval-quality state, foundation self-audit with remediation counts, checkpoint-anchored replay ledger, and optional HTML notes. The completion event also exposes retrieval quality status/counts, provider smoke status/counts, the work-plan/sync/context refresh reasons, artifact-index publishing handoff status, latest retrieval-quality summary, and latest foundation-audit remediation summary for replay/debug tooling.
- Agent-card tool/model policy checks around worker execution, emitting `agent_tool_use_approved`, `agent_tool_use_denied`, `agent_model_use_approved`, and `agent_model_use_denied` timeline events before external tool or selected model use.
- Saved worker profiles with start, stop, and heartbeat controls through `/api/runs/{run_id}/worker-profiles` and `all-about-llms-admin run-worker-profile --watch`; profiles can run either raw worker cycles or guarded autonomous studio passes, and active heartbeats acquire a durable lease and run a resume-plan gate before producing durable next-pass work plans. Worker-cycle heartbeats now refresh realtime dialogue and feedback resolution ledgers before writing post-cycle context packets, then record a compact `worker_profile_heartbeat_ledger`; blocked heartbeats record the same loop ledgers, a post-ledger context packet, and a blocked heartbeat ledger so always-on runs and pauses both leave replayable evidence.
- Active profile discovery through `POST /api/worker-profiles/scheduler/run` or `all-about-llms-admin run-worker-scheduler --watch`, carrying each heartbeat's execution mode, autonomous-pass event ids, work-plan artifact ids, heartbeat ledger artifact ids, and heartbeat context packet ids into scheduler events. The CLI scheduler can be scoped with `--run-id` and `--execution-mode autonomous_pass`, and capped with `--max-iterations` for local smoke runs.
- Specialist worker executors for Realtime Conversation Host session/control briefs with deterministic downstream A2A handoff task creation, A2A protocol contract audits, Intent Router route plans, web research with source-grounding repair, source ledger snapshots, durable context packet artifacts, Agent Harness checkpointed resume-plan artifacts, Forward Deployed Engineer feedback-requirements capture, Principal Software Engineer architecture reviews, durable claim verification status updates with accepted retrieval-evidence gates, writer-facing claim revision plans, and idempotent claim-revision follow-up A2A tasks, data brief generation, content strategy task fan-out, targeted feedback-aware ELI5/Substack artifact writing, Script Doctor hook/pacing revisions, Lead UI/UX Designer surface reviews, Interactive Systems Designer planning-surface reviews, Visual Director briefs, Image Generation Agent prompt packs, Audio Producer realtime/TTS briefs, Video/Reel Producer storyboards, editorial/critic review decisions, artifact index/provenance and publishing handoff snapshots, Obsidian review notes, optional interactive HTML run notes, growth/distribution packaging, Product Manager sync pulses, Sprint/Progress work plans, observability health reports, guardrail audits, and media planning.
- Postgres + pgvector durable state for runs, events, agent messages, conversation turns, sources, claims, artifacts, guardrail audits, feedback, and agent memories.
- LangGraph Postgres checkpoint setup via admin CLI.
- Provider adapters for OpenRouter DeepSeek V4 Flash, the default LiveKit/OpenRouter/Kokoro voice runtime, optional proprietary realtime adapters, Tavily, SerpAPI, provider-neutral reranking with a deterministic local default, an optional Rust retrieval-ranker subprocess provider, and the Codex `imagegen` boundary.
- Non-secret provider readiness report at `GET /api/provider-readiness`, surfaced in the cockpit for OpenRouter, LiveKit, Kokoro, web search, and imagegen boundary checks.
- Durable provider smoke ledger at `POST /api/runs/{run_id}/provider-smoke`, surfaced in the cockpit with an explicit live-call toggle. By default it records local/deterministic proof, blocked configuration, source ids, realtime session ids, smoke-proof status, and provider readiness without calling external providers. Passing `execute_live_calls=true` runs configured OpenRouter/LiveKit/Kokoro, selected web-search, and local reranker smoke steps.
- Autonomous passes build the provider smoke ledger before provider operations by default, so always-on profiles and context packets carry provider smoke blockers/proof into the next durable handoff.
- Model routing ledger at `POST /api/runs/{run_id}/model-routing-ledger`, proving per run that OpenRouter DeepSeek V4 Flash is the selected dialogue reasoning layer while realtime transport, speech output, web search, and imagegen remain separate provider/tool boundaries; deterministic fallback writing is flagged as non-publishable routing evidence.
- Provider operations ledger at `POST /api/runs/{run_id}/provider-ops-ledger`, summarizing model/tool policy decisions, OpenRouter usage, realtime sessions, provider fallbacks, artifact model provenance, latency classes, provider/end-to-end latency, fallback reasons, and provider-backed versus rehearsal/local-demo smoke status as a durable observability artifact.
- Realtime dialogue ledger at `POST /api/runs/{run_id}/realtime-dialogue-ledger`, auditing voice/text sessions, turns, assistant acknowledgements, provider-neutral spoken response plans, durable interrupt/resume/stop-output control events, pending Realtime Conversation Host follow-ups, and open feedback gates.
- Worker-cycle proof now covers the live voice-to-content continuation path: a finalized voice transcript can be summarized by Realtime Conversation Host, handed to Intent Router, routed to content/research/media specialists, and expanded by Content Strategist into writer, reel, audio, distribution, influencer, editor, and artifact tasks. For voice/conversation-originated requests that did not enter through the original content workflow, Content Strategist now creates deterministic seed post/reel/Substack drafts scoped to the content-strategy handoff, reloads seeds after insert conflicts before fanout, marks them non-publishable with `needs_web_research_before_publish` or explicit-source-only `source_context_available_needs_review`, and pins downstream child tasks to those seed artifact ids so writers and media producers do not pick up stale run-level content. Direct existing-content strategy tasks now pass explicit existing artifact ids instead of relying on run-wide fallback selection, and ambiguous same-format existing drafts fail fast until explicit targets are supplied. Intent Router route-plan artifacts and downstream child tasks use deterministic insert-if-absent writes, and Content Strategist uses deterministic insert-if-absent child task ids for fanout, so replayed worker steps do not duplicate plans or downstream pipelines.
- Feedback resolution ledger at `POST /api/runs/{run_id}/feedback-resolution-ledger`, turning open/routed/resolved feedback, linked A2A tasks, targeted artifact/source/claim context, remaining blockers, and resume actions into durable loop-closing evidence.
- A2A collaboration graph at `POST /api/runs/{run_id}/a2a-collaboration-graph`, materializing agent nodes, task nodes, dependency edges, dependency-cycle detection, handoff-trace edges, ready tasks, blocked tasks, retry-exhausted tasks, trace gaps, and recommended coordination actions.
- Skill usage ledger at `POST /api/runs/{run_id}/skill-usage-ledger`, proving processed A2A tasks carried project skill-card evidence from `agent_skill_invocation_recorded` events into task result provenance and validating that skill cards still match their `SKILL.md` source files.
- Runtime health ledger at `POST /api/runs/{run_id}/runtime-health-ledger` or `all-about-llms-admin build-runtime-health-ledger`, separating static Postgres/pgvector/Docker/LangGraph/no-SQLite readiness from live runtime evidence without running Docker commands from the API path; when backed by `PostgresStore`, it records a `runtime_health_live_postgres_connected` event as durable proof of the current store path.
- Research freshness ledger at `POST /api/runs/{run_id}/research-freshness-ledger`, recording search queries, accepted sources, placeholder seeds, freshness risk, and whether source-backed content needs another research pass; provider-backed content and Web Research Agent worker searches now emit `web_research_completed` with result counts and persist snippets, search rank, retrieval time, and published dates into source/provenance evidence.
- Retrieval quality ledger at `POST /api/runs/{run_id}/retrieval-quality-ledger`, owned by the Retrieval Intelligence Agent and Knowledge Graph Curator Agent, recording provider-neutral reranker decisions, accepted context evidence, precision risks, recall gaps, graph coverage gaps, and recommended follow-up queries for FP/FN reduction.
- Foundation audit at `POST /api/runs/{run_id}/foundation-audit`, comparing the foundation spec against agent cards, skills, model routing, provider contracts, references, Postgres/pgvector schema, UI boundaries, durable run evidence, worker-profile heartbeat ledgers/context packets, post-audit work-plan/sync/context refresh evidence, and the generated-artifact provenance contract, then emitting owner-routed remediation items for any missing evidence.
- Foundation reference ledger at `GET /api/foundation/references`, mapping official OpenRouter, LiveKit, LangGraph/LangChain, pgvector, OpenAI, ElevenLabs, Cartesia, and Anthropic/Claude guidance to architecture decisions and agent implications.
- Realtime session creation at `POST /api/runs/{run_id}/realtime-session`, sanitized session ledger listing at `GET /api/runs/{run_id}/realtime-sessions`, durable controls at `POST /api/realtime-sessions/{realtime_session_id}/control`, routed voice turns at `POST /api/realtime-sessions/{realtime_session_id}/turns`, and LiveKit voice-agent event persistence at `POST /api/realtime-sessions/{realtime_session_id}/voice-events`; `voice_user_turn_committed` and `assistant_response_completed` events now materialize durable voice conversation turns so the creator-facing dialogue history updates from real LiveKit agent events. Newly materialized assistant voice completions also enqueue a Realtime Conversation Host `summarize_realtime_turn_context` task with source/response turn ids and a routing policy that does not treat raw audio as verified text. Routed user realtime turns return a `spoken_response` plan with provider, voice, output channel, interrupt state, and provider payload, and controls enqueue Realtime Conversation Host follow-up tasks so the next worker cycle can build a voice/session/interruption brief. Passing `dry_run=true` creates a `local_realtime_rehearsal` session for provider-free browser voice UX testing; rehearsal sessions are marked `not_provider_backed` and do not satisfy provider-backed smoke.
- Internal cockpit voice rehearsal with final speech auto-routing, spoken assistant replies from the durable `spoken_response` plan, and persisted interruption metadata on routed voice turns. The actual creator-facing product voice path is the Next.js LiveKit client plus the OpenRouter/Kokoro voice-agent runtime.
- Multimodal intake ledger at `POST /api/runs/{run_id}/multimodal-intake`, also attachable to natural `/api/conversation/turns` and routed realtime turns, recording user-provided image, screenshot, audio, voice, video, reel, document, or text references as durable specialist work with OpenRouter/LiveKit realtime, imagegen, web-search, and legacy/non-default model boundaries explicit.
- Specialist `review_multimodal_intake` workers now turn those routed asset tasks into durable `multimodal_review` artifacts with per-agent focus, provider boundaries, next actions, and `multimodal_intake_review_recorded` events. The current default keeps Gemma/Hugging Face disabled for this flow unless a request explicitly reactivates a legacy/native-audio experiment; completed reviews still materialize idempotent follow-up A2A tasks such as context packets, manager coordination, voice-context routing, planning notes, or imagegen prompt-pack preparation unless a human feedback gate is open.
- Run timeline reads and streaming at `GET /api/runs/{run_id}/events` and `GET /api/runs/{run_id}/events/stream`, with cursor-based replay for long-running sessions.
- Product cockpit UI at `/cockpit` for run control, voice session creation, timeline, agent tasks, worker-profile heartbeat ledgers, artifacts, latest publishing handoff state, source ledger, and feedback, including post-audit work-plan/sync/context refresh chips and highlighted foundation-remediation A2A tasks. The Worker Profile panel reloads saved profiles and has a one-click Launch autopilot action that creates or reuses an autonomous profile, starts it, and runs the first heartbeat.
- Natural dialogue routing at `POST /api/conversation/turns` for one-turn create, revise, route, or record actions, with durable assistant reply turns linked back to the user turn, explicit or inferred revision target artifacts for conversational follow-ups like "make the reel hook sharper," and `conversation_handoff` artifacts for background Intent Router work.
- Standalone feedback routing at `POST /api/feedback`, converting user notes into a routed `FeedbackItem`, artifact/source/claim target context when content artifacts are implicated, a specialist A2A task, note-taking and sprint/progress support tasks, and note/progress memories; content-strategy worker fan-out now preserves that target context so writer and script-doctor workers revise only the implicated draft lineage.
- Planning feedback intake at `POST /api/planning/feedback`, so suggestions captured in the separate planning HTML can become routed `FeedbackItem` records, specialist A2A tasks, support task ids, memory notes, and `planning_feedback_ingested` timeline events.
- Durable feedback gate listing and approval through `GET /api/runs/{run_id}/feedback` and `POST /api/feedback/{feedback_id}/resolve`.
- First runnable content workflow at `POST /api/orchestrations/content-studio`, generating source-backed social posts, ELI5 reel scripts, and Substack drafts by default, with each draft carrying source citations, claim traces, source evidence snippets, prompt input, model/provider provenance, and an initial guardrail review state.
- Feedback-driven revision loop at `POST /api/runs/{run_id}/revision-loop`.
- Claim verification can now emit durable `claim_revision_plan` artifacts that identify held claims, rewrite actions, accepted source alternatives, and writer instructions; it materializes idempotent targeted follow-up tasks for ELI5/Substack writers, Script Doctor, and Editor-in-Chief, writer workers carry that context into revised artifacts, and Artifact Librarian records a `claim_revision_ledger` so open rewrite loops are visible before publishing.
- Media production planning at `POST /api/runs/{run_id}/media-production`, creating source-linked imagegen prompt, audio brief, and reel storyboard artifacts.
- Distribution packaging at `POST /api/runs/{run_id}/distribution-package` or `all-about-llms-admin build-distribution-package`, creating source-linked platform hooks, captions, hashtags, keywords, CTAs, and outreach angles as a guardrail-auditable `social_package` artifact.
- Guardrail audit loop at `POST /api/runs/{run_id}/guardrail-audit`, now checking source coverage, claim status, revision history, reviewer decisions, generation provenance, and prompt/input context.
- Publishing-readiness gate at `POST /api/runs/{run_id}/publish-readiness`, combining artifacts, provenance completeness, OpenRouter/model provenance, source quality/freshness, accepted retrieval evidence, claim status, audits, and open feedback into a ready/needs-review/blocked decision.
- Source ledger snapshots at `POST /api/runs/{run_id}/source-ledger`, mapping source quality, freshness, accepted retrieval evidence, claims, artifact coverage, and a per-artifact claim-to-source matrix into a durable `source_ledger` artifact.
- Artifact Librarian index tasks now include a `publishing_handoff` snapshot that packages publishable drafts, distribution and media artifacts, source ledger state, claim support, claim revision closure state, guardrail audit coverage, open feedback gates, latest publish-readiness evidence, and recommended next actions for the next long-running handoff.
- Application-level run checkpoints at `POST /api/runs/{run_id}/checkpoints`, resume plans at `POST /api/runs/{run_id}/resume-plan`, and gated resume execution at `POST /api/runs/{run_id}/resume` for restart-safe, human-gated long-running work, including explicit retry-exhausted and dependency-cycle task gates plus latest source-evidence, web-research, retrieval quality, realtime dialogue, feedback resolution, publishing handoff, and foundation-audit remediation summaries.
- Run replay ledgers at `POST /api/runs/{run_id}/replay-ledger`, comparing checkpoint cursors to later events and current state deltas for time-travel debugging.
- Dependency repair at `POST /api/a2a/messages/{message_id}/dependencies/repair`, allowing authorized sender, recipient, manager, harness, forward-deployed, or A2A protocol agents to remove circular or stale `depends_on_message_ids` with `dependencies_repaired` trace evidence and an `agent_message_dependencies_repaired` event.
- Sprint/Progress Agent work plans at `POST /api/runs/{run_id}/work-plan`, turning routed feedback, pending A2A tasks, retry-exhausted A2A blockers, dependency-cycle tasks, dependency-waiting tasks, latest foundation-audit remediation, worker profile state, and quality gates into a durable `system_plan` artifact, with optional idempotent follow-up A2A task creation.
- Product Manager sync pulses at `POST /api/runs/{run_id}/sync-pulse`, recording agent focus, retry authorization needs, dependency cycles, upstream dependency waits, claim revision closure blockers, handoffs, work-plan context, and recommended next actions as a durable `system_plan` artifact.
- Context packets at `POST /api/runs/{run_id}/context-packet`, backed by pgvector memory search at `POST /api/memories/search`, now including relevant foundation-reference guide items, retry-exhausted task context, dependency-waiting task context, first-class retrieval quality, realtime dialogue, and feedback resolution ledger items, unresolved realtime control-event counts, source-evidence snippets/dates/quality/linkage for resumed content agents, latest publishing handoff state, latest foundation-audit remediation, latest post-audit work-plan and manager-sync coordination digests, project-memory freshness/conflict checks, a budgeted `context_manifest`, `context_risks`, recent event tail, and recommended fetches for long-running agents.
- Obsidian review notes at `POST /api/runs/{run_id}/obsidian-review-note`, generated by the Interactive Note-Taking Agent under `social_media_optimiser/03-review-packets/runs/`, turning durable run state, retrieval quality, source evidence, feedback, pending A2A work, and event tails into vault-native Markdown artifacts.
- Obsidian memory promotion at `POST /api/runs/{run_id}/obsidian-memory-promotion`, generating proposed wiki-memory updates under `social_media_optimiser/wiki/run-memory-promotions/` from review notes, retrieval ledgers, claim revision ledgers, publishing handoffs, feedback, guardrails, and pending A2A state.
- Typed project memory at `POST /api/runs/{run_id}/project-memory`, recording first-class global or run-scoped `user_preference` and `project_decision` memories on the Postgres + pgvector memory store, with source run metadata, wiki targets, confidence, tags, and run timeline events.
- Optional interactive HTML run notes at `POST /api/runs/{run_id}/interactive-note`, generated by the Interactive Note-Taking Agent with a content-readiness packet covering source dependencies, claim traceability, unsupported claims, feedback gates, reviewer decisions, and guardrail evidence.
- Separate interactive planning artifact at `planning/foundation-system-design.html`, including structured local suggestion capture, optional durable feedback routing, a drag/drop progress tracker for implementation slices, and exportable packets for the next design iteration.
- Obsidian vault planning workspace under `social_media_optimiser/`, with native HLD/LLD notes, decision log, sprint state, review packets, and retrieval-quality research. This vault is the communication and planning source of truth; companion HTML exists only when a specific design needs a visual review surface, and it is not part of the product app.

## Local Setup

```bash
docker compose up -d postgres
uv run all-about-llms-admin setup-durable-storage
uv run all-about-llms
```

The API starts at `http://127.0.0.1:8000`.

Run the product app separately:

```bash
cd frontend/next-app
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
```

The app starts at `http://127.0.0.1:3000` and proxies same-origin `/api/*` requests to FastAPI. Set `NEXT_API_PROXY_TARGET` if the backend is not on `http://127.0.0.1:8000`; set `NEXT_PUBLIC_API_BASE_URL` only when the browser should call a public API origin directly.

For local browser validation against a backend on another port, prefer the proxy route so client fetches stay same-origin and do not need FastAPI CORS:

```bash
NEXT_API_PROXY_TARGET=http://127.0.0.1:8001 npm run build
NEXT_API_PROXY_TARGET=http://127.0.0.1:8001 npm run start -- -H 127.0.0.1 -p 3003
```

Build the Rust retrieval ranker when using the low-latency local reranking path:

```bash
cd services/retrieval-ranker
cargo build
```

Build and test the Rust voice-edge contract core:

```bash
cd services/voice-edge
cargo build --offline
cargo test --offline
```

This crate now verifies VAD/buffer/barge-in/cancellation acknowledgement contracts with both a deterministic energy gate and a real Silero ONNX path through the Rust `silero` crate. The Rust request config has an explicit VAD backend contract: `deterministic_energy` is the default, and `silero_onnx` runs the bundled Silero model unless `RUST_VOICE_EDGE_VAD_MODEL_PATH` points at a custom ONNX file. Loaded Silero sessions are cached in a bounded process-wide pool keyed by model source and session id, and each slot preserves bounded recurrent `StreamState` entries across requests, so the model is not bootstrapped on every VAD request and realtime frames reuse the correct Silero context. If Silero load/inference fails, the edge uses deterministic fallback only when `RUST_VOICE_EDGE_ALLOW_VAD_FALLBACK=true`; otherwise it fails conservatively by treating the frame as non-speech. The Python LiveKit participant calls the compiled `voice-edge --jsonl` process through `RUST_VOICE_EDGE_BINARY_PATH` to start turns from VAD speech-start events, commit turns after `RUST_VOICE_EDGE_MIN_SILENCE_FRAMES`, and honor barge-in cancellation acknowledgements.

The Rust sidecar also has an Axum/Tokio HTTP surface for supervised local runs and contract tests:

```bash
cd services/voice-edge
cargo run -- --http 127.0.0.1:7071
```

It exposes `GET /healthz`, `POST /v1/voice-edge`, `POST /v1/voice-edge/analyze`, and `POST /v1/voice-edge/cancel`. The HTTP sidecar still uses request/response transport, but the long-running Rust process preserves bounded per-stream Silero recurrent state while it is alive. Python uses persistent JSONL by default for frame-by-frame LiveKit calls, or the supervised HTTP sidecar when `RUST_VOICE_EDGE_HTTP_URL` is configured. HTTP mode runs a startup `/healthz` preflight before voice-agent readiness; if HTTP is unhealthy and the local `voice-edge` binary is executable, Python falls back to JSONL so transient sidecar failures do not remove VAD/barge-in behavior. JSONL mode also preflights before readiness by starting the persistent process and sending a harmless cancellation contract. The next Rust runtime upgrades are benchmarked pool sizing for concurrent users and the direct LiveKit-side Rust media bridge.

Run the local synthetic voice-edge benchmark:

```bash
PYTHONPATH=src python3 -m all_about_llms.cli benchmark-voice-edge --runs-per-scenario 5
```

The benchmark exercises the persistent Rust JSONL bridge for silence false positives, speech-start detection, barge-in cancellation, and concurrent stream probes. It reports latency, false-positive / missed-detection counts, VAD backend/pool configuration, and whether the concurrency probe was serialized by the client. To measure the supervised Rust HTTP sidecar instead of the JSONL subprocess, start `voice-edge --http 127.0.0.1:7071` and run:

```bash
PYTHONPATH=src python3 -m all_about_llms.cli benchmark-voice-edge --http-url http://127.0.0.1:7071 --vad-backend silero_onnx --vad-probability-threshold 0.01 --speech-amplitude 12000
```

For Silero tuning, prefer a real local speech fixture over the synthetic tone:

```bash
PYTHONPATH=src python3 -m all_about_llms.cli benchmark-voice-edge --vad-backend silero_onnx --speech-wav path/to/mono-16khz-16bit-speech.wav
```

Use multiple `--speech-wav` flags or `--speech-wav-dir path/to/fixtures` to run a corpus. Directory loading is recursive and matches `.wav` case-insensitively, then fails fast if the directory is missing or empty. Add `--vad-probability-threshold-sweep 0.01,0.1,0.5` to compare Silero thresholds over the same real fixture corpus; sweeps intentionally reject synthetic-only runs. Set `RUST_VOICE_EDGE_BENCHMARK_SPEECH_WAV_PATH` to use a single WAV fixture in runtime-health ledgers, and `RUST_VOICE_EDGE_BENCHMARK_MAX_SPEECH_FRAMES=64` to cap fixture length.

The CLI `--http-url` benchmark targets HTTP directly. Runtime health uses HTTP with JSONL fallback when both `RUST_VOICE_EDGE_HTTP_URL` and an executable `RUST_VOICE_EDGE_BINARY_PATH` are configured.

This is local edge proof only; real provider-backed voice readiness still requires LiveKit + OpenRouter DeepSeek V4 Flash + Kokoro smoke with user audio and generated assistant speech.

Runtime health includes this local benchmark by default when building a run ledger. Use `--skip-voice-edge-benchmark` only when you need a schema/store-only health packet:

```bash
uv run all-about-llms-admin build-runtime-health-ledger --run-id <run-id>
```

Run the open realtime voice participant after LiveKit and model credentials are configured:

```bash
docker compose --profile voice up -d livekit
export OPENROUTER_LIVEKIT_URL=ws://127.0.0.1:7880
export OPENROUTER_API_KEY=...
export LIVEKIT_API_KEY=<local-livekit-api-key>
export LIVEKIT_API_SECRET=<local-livekit-api-secret>
uv sync --extra voice
uv run all-about-llms-admin run-voice-agent --dev
```

The Compose `voice` profile starts local LiveKit dev mode. Native `livekit-server --dev` is also valid. Keep the LiveKit API key/secret in local environment variables or ignored `.secrets/` files, never in committed docs or source. The default voice path is LiveKit transport + OpenRouter `deepseek/deepseek-v4-flash` dialogue reasoning + `hexgrad/Kokoro-82M` TTS. This requires `OPENROUTER_API_KEY`, `OPENROUTER_LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, and either local Kokoro dependencies or a configured Kokoro endpoint. Gemma/Hugging Face/MLX setup is legacy/native-audio background and is not required for the current LiveKit proof path. The current Python participant is the baseline media/model bridge; when the Rust voice-edge binary is present, it keeps a preflighted persistent JSONL edge process open for VAD-driven turn commits and barge-in cancellation. Captured LiveKit user turns are written as bounded local PCM artifacts under `ARTIFACTS_ROOT/voice-audio/...` when `VOICE_AGENT_PERSIST_AUDIO_ARTIFACTS=true`; durable events and materialized conversation turns store artifact URI/path/hash/byte metadata. `VOICE_AGENT_AUDIO_ARTIFACT_RETENTION_DAYS` and `VOICE_AGENT_AUDIO_ARTIFACT_CLEANUP_INTERVAL_SECONDS` provide opportunistic local cleanup for long-running sessions; this cleanup is intentionally destructive for expired `.pcm` files, so raise retention for evidence-preservation runs. Local Rust binary paths are resolved relative to the project root when configured as relative paths. Set `RUST_VOICE_EDGE_HTTP_URL=http://127.0.0.1:7071` to use the supervised Rust HTTP sidecar first, with startup health preflight and JSONL fallback when the binary is available. The LiveKit/Silero streaming bridge remains a follow-on slice.
The product voice panel can supervise the local LiveKit dev server separately from the OpenRouter/Kokoro agent process. `GET /api/local-livekit-process`, `POST /api/local-livekit-process/start`, and `POST /api/local-livekit-process/stop` expose native `livekit-server --dev` or supervised foreground Compose mode (`docker compose --profile voice up livekit`), and the `Join voice room` flow attempts local transport startup before LiveKit preflight when supervision is enabled. Detached Compose (`docker compose --profile voice up -d livekit`) remains the manual/operator route outside the product supervisor.
Build `services/voice-edge` first if you want the participant to call the Rust VAD/barge-in contract during local LiveKit runs.

Check the non-secret voice runtime state from the API or the Next voice panel:

```bash
curl "http://127.0.0.1:8000/api/voice-runtime-readiness?preflight_edge=true"
```

This reports LiveKit, OpenRouter, Kokoro, Rust voice-edge, and context-pruning readiness. With `preflight_edge=true`, the backend proves the selected Rust edge transport before reporting readiness.
Add `preflight_livekit=true` to verify the configured LiveKit RoomService API with a short-lived server token before claiming the transport is reachable:

```bash
curl "http://127.0.0.1:8000/api/voice-runtime-readiness?preflight_livekit=true&preflight_edge=true&preflight_agent=true"
```

After a run has persisted LiveKit agent events, build the voice timing ledger:

```bash
uv run all-about-llms-admin build-realtime-voice-timing-ledger --run-id <run-id>
```

This records a `realtime_voice_timing_ledger` artifact for the correlated LiveKit/OpenRouter/Kokoro chain: agent ready, user speech start, user-turn commit, OpenRouter turn start, OpenRouter generation start, first text/audio output, and barge-in cancellation plus turn-cancelled proof. The ledger refuses to mark readiness from unrelated turns or mismatched response ids.

The Next.js product voice panel renders this ledger as stage-level proof rows plus latest-turn latency segments, so creators/operators can see which part of the LiveKit -> OpenRouter -> Kokoro -> barge-in chain is measured or still missing without reading raw JSON.

After creating or loading a durable run, build the run-level cockpit proof packet:

```bash
uv run all-about-llms-admin build-cockpit-walkthrough-ledger --run-id <run-id>
```

This records runtime health, provider readiness, provider-free demo proof, source coverage, realtime smoke state, provider observability, and feedback-loop state in one `cockpit_walkthrough_ledger` artifact.

Provider smoke can be recorded without external calls:

```bash
uv run all-about-llms-admin build-provider-smoke-ledger --run-id <run-id>
```

Set `--live` only after provider credentials are configured and you want real network smoke evidence. The same smoke path is available through `POST /api/runs/{run_id}/provider-smoke` with `execute_live_calls=true`.

When `openrouter_livekit` is the selected realtime provider, provider smoke adds the OpenRouter/LiveKit/Kokoro realtime step. With `--live`, it records the selected LiveKit transport, the OpenRouter DeepSeek V4 Flash dialogue path, Kokoro first-audio latency, and end-to-end first-audio latency. If the run already has a materialized voice turn backed by a local `voice-audio` artifact, live smoke uses that captured PCM as the input fixture and records the artifact URI/path/hash/bytes in the smoke details; otherwise it falls back to a synthetic silence probe. Kokoro smoke can use either a hosted `KOKORO_TTS_ENDPOINT_URL` or the local Kokoro package when installed. Legacy Gemma/Hugging Face audio paths are not part of the current provider-backed proof gate.

The Next.js product voice panel renders that same proof in the runtime smoke card: Kokoro transport (`hosted endpoint` or `local package`), OpenRouter TTFT, Kokoro first-audio latency, end-to-end first-audio latency, captured microphone artifact path, byte size, short SHA-256, and source turn id when available. It shows synthetic fallback only after a completed smoke actually used probe audio; blocked, failed, or unknown smoke statuses stay explicit instead of being treated as evidence.

Before attempting the remaining live voice or external publication blockers, print the no-secret operator plan:

```bash
PYTHONPATH=src python3 -m all_about_llms.cli provider-proof-plan --run-id <run-id> --checked-at YYYY-MM-DD
```

Installed environments can use `all-about-llms-admin provider-proof-plan`. The command makes no live calls, reads no secret file contents, and combines the current credential snapshot with the exact runtime proof commands and capture requirements, including publication policy/disclosure capture. Use a durable product run UUID for `--run-id`; shell-safe labels such as `RUN-ID` remain blocked before executable API/CLI proof commands, and command fields render `<run-id>` until a product UUID is supplied. A `ready_for_runtime_attempt` status still means only `runtime_configuration_present_unverified`; same-session provider smoke, voice timing, or external destination proof is still required.

## Verification

```bash
bash scripts/ci-python-stable-tests.sh
LIVE_POSTGRES=1 uv run pytest tests/test_live_postgres.py -q
```

The CI Python slice covers the active OpenRouter/LiveKit proof path, LiveKit timing capture command, supervisor redaction, and browser-rendered proof surfaces. The full `uv run pytest -q` suite remains the broader local migration-audit check and is expected to pass in the current workspace. Local provider-proof output fixture tests are opt-in with `RUN_PROVIDER_PROOF_ARTIFACT_FIXTURE_TESTS=1` because their inputs live under ignored output directories.

The default suite intentionally skips live Postgres tests unless `LIVE_POSTGRES=1` is set and can skip the real Rust voice-edge HTTP sidecar smoke when loopback binding is unavailable in the current sandbox. To prove the Python backend suite with those infrastructure gates enabled from a host context that can reach local Postgres and bind `127.0.0.1`, run:

```bash
LIVE_POSTGRES=1 uv run pytest -q -rs
```

In the current local workspace, with `services/voice-edge/target/debug/voice-edge` built and local Postgres reachable, this full host-context command is expected to run without skips. If it skips `test_real_rust_voice_edge_http_sidecar_health_and_cancel_smoke`, build `services/voice-edge` and rerun from a context that permits loopback binding.

Default tests do not call live model/search/audio providers. Provider-backed behavior is covered with fake providers; real provider calls require keys in `.env`.

## Provider Configuration

Copy `.env.example` to `.env`, then configure the providers you want. For local secrets, prefer ignored secret files such as `OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key`, `LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret`, and `TAVILY_API_KEY_FILE=.secrets/tavily_api_key`; direct environment values also work for local runs but must never be committed.

- `REALTIME_DEFAULT_PROVIDER=openrouter_livekit`, `OPENROUTER_API_KEY`, `OPENROUTER_LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, and either hosted `KOKORO_TTS_ENDPOINT_URL` or local Kokoro dependencies for the current default realtime voice stack.
- `OPENROUTER_CHAT_COMPLETIONS_URL` only when using a non-default OpenRouter-compatible endpoint.
- Compatibility environment names that still start with `GEMMA4_REALTIME_` map to the OpenRouter/LiveKit/Kokoro runtime in the current code path; do not configure Hugging Face/Gemma endpoints for the default product proof.
- `RUST_VOICE_EDGE_BINARY_PATH` after building `services/voice-edge` so the LiveKit participant can use VAD-driven turn endpointing, detect barge-in, and cancel active OpenRouter/Kokoro work.
- `RUST_VOICE_EDGE_HTTP_URL` only when the Rust voice-edge sidecar is already running and you want Python to call HTTP instead of the persistent JSONL subprocess.
- `RUST_VOICE_EDGE_VAD_BACKEND=deterministic_energy` for the default local path, or `silero_onnx` to run real Rust Silero ONNX VAD. Leave `RUST_VOICE_EDGE_VAD_MODEL_PATH` empty for the bundled model, set it for a custom ONNX file, tune `RUST_VOICE_EDGE_VAD_PROBABILITY_THRESHOLD=0.5` separately from the deterministic energy threshold, use `RUST_VOICE_EDGE_VAD_SESSION_POOL_SIZE=4` for the bounded Silero session pool, and use `RUST_VOICE_EDGE_VAD_STREAM_STATE_CACHE_SIZE=512` for recurrent per-stream VAD state retained per pool slot.
- `RUST_VOICE_EDGE_BENCHMARK_SPEECH_WAV_PATH` for an optional local 16-bit PCM WAV speech fixture used by runtime-health voice-edge benchmarks, plus `RUST_VOICE_EDGE_BENCHMARK_MAX_SPEECH_FRAMES=64` to cap how many frames are used. The cap must be between 1 and 4096 frames.
- `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`, or `CARTESIA_API_KEY` only for optional proprietary realtime adapters.
- `TAVILY_API_KEY`/`TAVILY_API_KEY_FILE` or `SERPAPI_API_KEY` for source-backed web search.
- `INSTAGRAM_ACCESS_TOKEN`, `LINKEDIN_ACCESS_TOKEN`, `X_ACCESS_TOKEN` or `X_API_KEY`, and `SUBSTACK_API_TOKEN` for non-live publish-channel readiness checks. These checks only verify local credential presence and platform-policy acknowledgement; they do not publish externally.
- `RERANKER_PROVIDER=deterministic` for the local baseline reranker.
- `RERANKER_PROVIDER=rust` plus `RUST_RERANKER_BINARY_PATH` for the Rust retrieval-ranker subprocess path.

If keys are absent, the content, revision, and multimodal review workers record provider fallback events and produce deterministic artifacts so the durable loop remains testable.

Provider-backed smoke is considered real only when the selected realtime provider, selected web-search provider, and reranker all pass in the durable provider-smoke ledger. For the current realtime stack, that means OpenRouter DeepSeek V4 Flash over LiveKit plus Kokoro TTS, not Gamma/Gemma/Hugging Face. Provider-free realtime rehearsal and seeded demo artifacts are useful for UI testing, but they do not count as provider-backed proof.
