---
type: lld
project: agent-studio
status: draft
updated: 2026-05-19
owners:
  - principal-software-engineer
  - agent-harness-engineer
  - context-engineering-agent
---

# LLD - Agent Studio

## Runtime Modules

### FastAPI App

Files:

- `src/all_about_llms/app.py`
- `src/all_about_llms/main.py`

Responsibilities:

- API routes.
- SSE event streaming.
- Product app and cockpit artifact serving.
- Provider readiness reports.
- Conversation, feedback, artifact, source, and run endpoints.
- Cockpit surfaces for source ledger, accepted-evidence drilldowns, project-memory recording, provider-free demo run loading, run timeline, feedback gates, context packets, worker profiles, and project-memory policy.

### Next.js Product App

Files:

- `frontend/next-app/app/page.tsx`
- `frontend/next-app/components/`
- `frontend/next-app/lib/api/`
- `frontend/next-app/next.config.mjs`

Responsibilities:

- Creator-facing text/voice content-generation workflow.
- Local browser dictation capture before routing transcript turns.
- Live voice runtime preparation for OpenRouter `deepseek/deepseek-v4-flash` + LiveKit + Kokoro sessions.
- The production voice transport is LiveKit; raw browser PCM WebSockets are not the production path. Pipecat can be added later for internal pipeline composition.
- Voice-session provider selection for OpenRouter live dialogue, legacy/native-audio alternatives, and local transcript rehearsal.
- Prompt starters, target-format controls, run restore through local storage and `?runId=`.
- Conversation history from durable `ConversationTurn` records.
- Agent/event activity from context-packet `agent_messages` and `recent_events`.
- Source-backed draft review with copy/export/revise controls.
- Production controls that call `POST /api/runs/{run_id}/distribution-package`, `POST /api/runs/{run_id}/media-production`, and `POST /api/runs/{run_id}/publish-readiness`.
- Draft filtering for social packages and media planning artifacts.
- Feedback resolution and source/claim evidence inspection.
- Responsive layout for desktop, tablet, and mobile.
- Same-origin `/api/*` proxy to FastAPI for local development.

Non-responsibilities:

- It is not the cockpit.
- It is not the planning workspace.
- It does not own durable orchestration or provider calls directly.
- It does not implement production audio transport itself. It should join a LiveKit session once the backend/runtime issues a room token.

### Durable Storage

Files:

- `infra/postgres/001_foundation.sql`
- `src/all_about_llms/storage/postgres.py`

Responsibilities:

- Runs.
- Events.
- Checkpoints.
- A2A messages.
- Conversation turns.
- Sources and claims.
- Artifacts and provenance.
- Feedback items.
- Agent memories with pgvector.

Constraint: no SQLite fallback.

### Rust Retrieval Ranker

Files:

- `services/retrieval-ranker/src/`
- `services/retrieval-ranker/tests/`
- `src/all_about_llms/providers/rerank.py`

Responsibilities:

- Deterministic hybrid reranking from vector, lexical, graph, authority, and freshness signals.
- Bounded graph traversal for local knowledge/source neighborhoods.
- Stdin/stdout JSON and persistent JSONL contracts for Python integration.
- Opt-in backend provider selected with `RERANKER_PROVIDER=rust`.

Non-responsibilities:

- It does not query Postgres or pgvector.
- It does not call model/search providers.
- It does not replace the Python deterministic fallback.

### Realtime Voice Runtime

Planned files:

- `services/voice-edge/` for the Rust realtime edge.
- `src/all_about_llms/voice_agent/` for the Python OpenRouter/Kokoro LiveKit agent engine; older Gemma/Kokoro classes are legacy names until code is renamed.
- `frontend/next-app/components/voice/RealtimeVoicePanel.tsx` for the creator-facing runtime controls.
- `frontend/next-app/app/page.tsx` and `frontend/next-app/lib/api/client.ts` for text/dictation turn routing plus bounded `/api/a2a/workers/run-cycle` continuation from the product surface.
- `src/all_about_llms/providers/realtime.py` for provider/session descriptors.

Responsibilities:

- LiveKit transport is the production media layer.
- Rust edge owns high-frequency audio control: Axum/Tokio session control, Silero VAD via ONNX, bounded audio buffers, backpressure, and interruption detection.
- Python agent engine owns model state: conversation buffer, OpenRouter live-dialogue reasoning calls, Kokoro-82M TTS streaming, context pruning, and durable turn/event writes.
- FastAPI remains the durable orchestration/control API; it does not become the media server.
- OpenRouter returns text for live dialogue reasoning; Kokoro is responsible for waveform synthesis. The current route is a text-turn spoken-output cascade over LiveKit, and raw microphone PCM is not sent to OpenRouter. Gemma 4 native-audio work is a superseded default path and only remains as legacy/future-native-audio background.

Hard rules:

- Prune raw audio context after 3 turns and replace it with transcript plus compact turn summary.
- Bound every turn and keep raw audio local unless a future native-audio proof path is explicitly selected.
- On barge-in, drop outbound audio immediately, cancel the active OpenRouter/Kokoro turn, clear Kokoro output buffers, and record interruption events.
- Do not use raw browser WebSockets as the production audio transport.

Primary stack:

- OpenRouter `deepseek/deepseek-v4-flash` for active live dialogue reasoning.
- `hexgrad/Kokoro-82M` for TTS.
- LiveKit for media transport, with Pipecat optional for internal pipeline processors.
- `silero-vad-rust`/ONNX Runtime for Rust-side VAD.

Immediate implementation contracts:

- `frontend/next-app` joins LiveKit only from an ephemeral backend transport grant.
- Local runs without `livekit-client` must show a blocked SDK state instead of treating browser dictation as production voice.
- The Python voice agent must prune raw audio after 3 turns and emit context-pruning events.
- The Rust edge must expose cancellation acknowledgements so `record_realtime_session_control` can eventually verify that OpenRouter/Kokoro work actually stopped, not only that an interrupt event was recorded.

Current frontend state:

- `frontend/next-app/lib/voice/livekitRuntime.ts` creates a LiveKit `Room`, joins using the backend transport token, enables the local microphone, attaches remote audio tracks, and clears local audio elements on interruption/disconnect.
- `RealtimeVoicePanel.tsx` now shows room/participant/token-presence state, reports blocked joins when OpenRouter, LiveKit, or Kokoro configuration is incomplete, displays all `GET /api/voice-runtime-readiness` checks for LiveKit, OpenRouter live-dialogue reasoning, Kokoro, Rust voice-edge, backend event sink, and context pruning, and calls the backend interrupt contract while also clearing local audio playback.
- The readiness UI renders each check's first evidence line, missing environment variables, and first next action. This is deliberate product behavior: a blocked voice-to-voice session must tell the creator/operator whether the missing piece is OpenRouter live-dialogue reasoning, LiveKit transport, the backend participant/process, Kokoro, Rust edge preflight, or the event sink.
- The voice panel now has a launch checklist derived from `frontend/next-app/lib/voice/setup.ts`. It identifies the first blocking prerequisite across content run, LiveKit transport, runtime readiness, Gemma/Kokoro agent process, joined room, and participant presence. `Check setup` refreshes process status, runtime preflight, and participant proof together, while `Resolve next` maps the blocker to the concrete action: start LiveKit, run preflight, start the agent, join the room, start rehearsal, or probe participant presence.
- Voice setup checks and resolver attempts are durable product evidence, not only local UI messages. `POST /api/runs/{run_id}/voice-setup-proof` writes a `voice_setup_proof` artifact and `voice_setup_proof_recorded` event with action, status, provider, transport framework, runtime/process statuses, primary blocker, checklist steps, and creator-panel provenance.
- The product artifact surface separates creator content from operational evidence. The default board shows generated content artifacts first, while a `Proofs` filter exposes ledgers and proof artifacts. Only content artifacts can be selected for revision; operational artifacts stay browseable, copyable, and exportable without entering the draft-edit workflow.
- The product artifact surface renders `voice_setup_proof` as an operational proof card, not raw JSON or draft content. The card exposes the setup status, action, provider, transport framework, primary blocker, runtime readiness, LiveKit process, OpenRouter/Kokoro process, and captured checklist-step count so the creator can understand setup failure without reading the artifact payload.
- The product voice panel controls local LiveKit transport separately from the OpenRouter/Kokoro participant. `LocalLiveKitDevServerSupervisor` can start native `livekit-server --dev` or supervised foreground `docker compose --profile voice up livekit`, FastAPI exposes `/api/local-livekit-process`, and the UI surfaces status/start/stop/mode controls under `Local LiveKit transport`. Detached `docker compose --profile voice up -d livekit` remains a manual/operator route outside the product supervisor.
- The primary provider-backed `Join voice room` flow treats the local OpenRouter/Kokoro LiveKit participant as part of voice-to-voice startup. After runtime preflight, the panel starts the supervised `all-about-llms-admin run-voice-agent` process when it is stopped, blocks if that start fails, and only skips local startup when process supervision is disabled for an externally managed participant.
- The primary provider-backed `Join voice room` flow now tries supervised local LiveKit transport startup before runtime preflight when local transport supervision is enabled and stopped/exited/failed. This keeps LiveKit transport setup as a product-visible prerequisite rather than a hidden terminal-only step.
- Local LiveKit proof can now start with either native `livekit-server --dev` or `docker compose --profile voice up -d livekit`. The current local-development URL is `OPENROUTER_LIVEKIT_URL=ws://127.0.0.1:7880`; provider-backed readiness also requires OpenRouter key-file routing and Kokoro availability. Runtime preflight additionally calls LiveKit `RoomService/ListRooms`, converting `ws` to the matching HTTP Twirp endpoint and using a short-lived room-list token, so wrong URL/key/secret combinations block before browser join.
- LiveKit connectivity preflight timeout is an explicit bounded setting (`LIVEKIT_CONNECTIVITY_PREFLIGHT_TIMEOUT_SECONDS`, finite, > 0, <= 30). Preflight accepts root URLs and path-prefix proxy URLs, records the probed path prefix in metadata, and rejects query/fragment URLs before network calls because they are not stable RoomService endpoint configuration.
- Captured LiveKit user audio turns are persisted as bounded local PCM artifacts under `ARTIFACTS_ROOT/voice-audio` when `VOICE_AGENT_PERSIST_AUDIO_ARTIFACTS=true`. The turn keeps an `artifact://...` audio ref plus relative path, byte count, and SHA-256 metadata for audit/replay; durable events and materialized conversation turns do not carry raw PCM. The current OpenRouter route does not send raw PCM to OpenRouter; persisted audio remains local proof/timing evidence unless a future native-audio provider route is explicitly selected. `VOICE_AGENT_AUDIO_ARTIFACT_RETENTION_DAYS` and `VOICE_AGENT_AUDIO_ARTIFACT_CLEANUP_INTERVAL_SECONDS` define opportunistic local cleanup for long-running sessions; expired `.pcm` cleanup is destructive by design, so retention must be raised for evidence-preservation runs.
- `RealtimeVoicePanel.tsx` also exposes transcript rehearsal as a local, non-production proof path. Selecting `Transcript rehearsal` creates a dry-run `local_realtime_rehearsal` session, labels the panel `NOT PRODUCTION AUDIO`, routes a typed transcript through the realtime turn endpoint, refreshes the run, and continues specialist agents from the returned realtime follow-up. This proves realtime routing and A2A handoff contracts without claiming LiveKit media, OpenRouter provider-backed dialogue, or Kokoro speech output.
- `GET /api/voice-runtime-readiness?preflight_edge=true` is the product-facing runtime proof endpoint. It keeps secrets out of the response and can run full runtime readiness with the selected Rust edge preflight before the user joins the LiveKit room.
- The voice panel also owns a compact product proof surface: dry voice-only provider smoke by default, explicit live-smoke opt-in with confirmation before external calls, and realtime voice timing ledger generation. The current smoke path must prove the OpenRouter + LiveKit + Kokoro route, not a legacy Gemma/HF endpoint.
- Live provider smoke should prefer real same-session interaction evidence over synthetic probes. For the current OpenRouter route, captured audio artifacts prove LiveKit/session timing and local edge behavior but are not sent to OpenRouter as raw PCM. Synthetic silence remains only a fallback for non-accepted endpoint smoke that is not claiming active-room proof.
- Provider smoke must share the same Kokoro readiness boundary as the runtime: hosted `KOKORO_TTS_ENDPOINT_URL` is valid, but a local Kokoro package is also valid for first-audio smoke. The ledger records `kokoro_provider`, `kokoro_transport`, endpoint presence, and local-package availability so local open-weight TTS proof is not falsely blocked on a hosted endpoint.
- `KokoroRuntimeRoute` is the shared local/open TTS routing contract. Readiness, provider-smoke blocked details, and live provider-smoke proof must all derive hosted endpoint, local package, or missing-state evidence from this route object so setup guidance stays consistent across product UI and durable ledgers.
- Route promotion is shape-validated before evidence is shown. A non-empty `KOKORO_TTS_ENDPOINT_URL` is not enough for hosted TTS readiness; it must be an `http(s)` URL with a host. Malformed hosted config is recorded as `kokoro_endpoint_error` and either blocks TTS or falls back to local Kokoro with explicit evidence.
- Runtime builders must fail fast from the same route object. If `KokoroRuntimeRoute.ready` is false, LiveKit and provider-smoke streamer construction raises a configuration error before any first-token or first-audio measurement starts.
- Provider-backed voice proof has two levels. Endpoint smoke can measure provider/Kokoro behavior without a room, but session-bound live smoke must reuse the active LiveKit realtime session and require a fresh agent-ready event for that same session before measuring OpenRouter reasoning latency or Kokoro first audio.
- Session-bound proof must bind the runtime turn, not only the ledger label. The provider-smoke `RealtimeVoiceTurnInput` carries the active session id, LiveKit room, and creator participant identity whenever session-bound presence is required.
- Session-bound proof also binds the audio fixture. Once LiveKit participant presence is required, the smoke step must use a persisted user `voice-audio` artifact from that same realtime session; synthetic probe audio remains valid only for endpoint smoke that is not claiming active-room proof.
- Same-session audio matching prefers explicit `realtime_session_id` metadata, but may use the artifact path as compatibility evidence for older records when the path contains the requested session id. Missing or mismatched session evidence still blocks active-room smoke.
- The product live-smoke control must not depend on stale room-join proof. Before requesting session-bound provider smoke, the creator app sends a fresh LiveKit `voice_agent_presence_probe`, polls the durable presence endpoint with that probe id for a bounded window, updates the visible participant proof, and then lets the backend smoke ledger pass or block from authoritative run state.
- Presence/event UI writes are run-and-session owned. Stop, run replacement, or session replacement must invalidate in-flight smoke/timing requests, cancel bounded presence waits, and prevent stale LiveKit data-channel events from repainting the active product view.
- Provider-smoke status values are a contract, not arbitrary labels. `ProviderSmokeStepStatus` and `ProviderSmokeRunStatus` constrain backend ledger statuses while preserving string JSON output for the Next app. Unknown frontend statuses are treated as unproven, but the backend should reject them before persistence.
- The creator app must expose that proof without requiring raw JSON inspection. `RealtimeVoicePanel.tsx` renders hosted-vs-local Kokoro transport, OpenRouter reasoning latency, Kokoro first-audio latency, end-to-end first-audio latency, and captured-audio/session proof from the OpenRouter/Kokoro streaming smoke step. The captured-audio proof shows artifact path, byte size, short SHA-256, and source turn id when a persisted microphone artifact was used, a synthetic-fallback label only when a completed smoke used probe audio, and explicit blocked/failed/pending labels when no valid smoke proof exists.
- The creator app must also expose realtime timing proof without requiring raw JSON inspection. `RealtimeVoicePanel.tsx` renders `realtime_voice_timing_ledger` stages as measured/missing LiveKit, OpenRouter, Kokoro, and barge-in proof rows and shows latest-turn latency segments such as speech-to-commit, agent-to-OpenRouter, OpenRouter-to-first-audio, and barge-in-to-stopped when those durable events exist.
- `src/all_about_llms/voice_agent/livekit_app.py` is the runnable Python LiveKit participant scaffold. It subscribes to room audio, uses the persistent Rust `voice-edge --jsonl` bridge for VAD endpointing and barge-in acknowledgements, commits bounded user turns, calls the OpenRouter/Kokoro engine, and forwards durable-safe voice events.
- `src/all_about_llms/voice_agent/benchmark.py` provides the current local proof harness for the Rust edge. Runtime health should record this benchmark as operator evidence, including latency and FP/FN-style quality counts.
- The backend now has the first LiveKit room timing ledger. The next backend voice slice is accepted proof-record capture/recheck for the configured OpenRouter/LiveKit/Kokoro route, plus benchmarked Silero concurrency tuning and moving Python from the JSONL/HTTP bridge to the LiveKit-side Rust media bridge.

Required live-voice UI state machine:

- Disconnected.
- Connecting.
- Connected.
- Listening.
- Thinking.
- Speaking.
- Interrupting.
- Reconnecting.
- Ended.
- Failed.

Implementation note: the creator app now derives this state machine in `frontend/next-app/lib/voice/liveStage.ts`. LiveKit runtime events own connected/reconnecting/ended/failed projection, while `agent.voice.event` data-channel events own listening/thinking/speaking/interrupting projection from durable Gemma/Kokoro event names.
Runtime callbacks must be ownership-guarded before they update the visual projection: stale LiveKit runtime events from stopped/replaced sessions are discarded, and reconnecting is preserved through transient connection-state disconnects until the final disconnected event arrives.

Required live-voice UI signals:

- LiveKit room connected.
- Microphone permission/publishing status.
- Agent participant joined.
- Gemma processing state.
- Kokoro speaking/buffer state.
- Context policy: recent raw audio window plus pruned summary.
- Server-side cancellation acknowledgement for Gemma cancellation, Kokoro buffer clearing, and LiveKit audio stop.
- Clear fallback label when the session is transcript-only rehearsal rather than provider-backed realtime voice.

Implementation note: `RealtimeVoicePanel.tsx` renders these as a compact `voice-stage-strip` with room connection, microphone publishing, agent participant proof, and context-window/prune policy. Transcript rehearsal keeps the explicit non-provider-backed label.
Microphone publishing is a user-controlled LiveKit runtime state. The product app exposes Mute/Unmute only after a provider-backed room is ready, calls `livekitRuntime.setMicrophonePublishing()`, and keeps the action disabled for transcript rehearsal because rehearsal has no media track. Mic-control completions are guarded by run id, realtime session id, and a local operation sequence before updating the state strip, so Stop or run replacement invalidates late mic completions. The runtime also reports local audio track published, unpublished, muted, and unmuted signals through a dedicated mic-state callback so the strip can follow transport state without duplicating success log entries.
Live captions are part of the runtime UX, not a separate transcript app. `GemmaKokoroLiveKitAgentEngine` emits safe `text_delta` values on `assistant_text_delta`; `livekit_app.py` includes committed user transcripts when available; and `frontend/next-app/lib/voice/liveTranscript.ts` projects active You/Agent caption cards in `RealtimeVoicePanel.tsx` from the current run/session's data-channel events. Caption updates must correlate by turn id and response id inside the session so old response completions or deltas cannot repaint a newer turn after barge-in or rapid follow-up speech.
Cancellation acknowledgement is projected by `frontend/next-app/lib/voice/cancellation.ts`: frontend interrupt control is only a request until Rust edge or Gemma/Kokoro data-channel events confirm the stop contract.
Manual product interrupt must use the same realtime channel as automatic barge-in. `RealtimeVoicePanel` clears browser playback immediately, asks `livekitRuntime.interruptAgent()` to publish `voice_interrupt` on `agent.voice.control`, and then records the durable `realtime_session_control_recorded` event with the LiveKit control id or error. `livekit_app.py` validates run/session targeting before canceling the active engine response, emits `voice_manual_interrupt_received` when cancellation was attempted, and emits `voice_interrupt_no_active_response` when there was no active output to stop. The UI treats agent acknowledgement as an intermediate state; only `gemma_kokoro_voice_turn_cancelled` is final stop proof.
Control-channel trust boundary: readiness probes and manual interrupts are ignored unless the LiveKit data message is on topic `agent.voice.control`, carries explicit matching `run_id` and `realtime_session_id`, and comes from the creator participant identity stored on `LiveKitVoiceAgentSessionState`. Missing ids, wrong topics, wrong senders, and wrong sessions must produce no ready or cancellation events.
Session stop is also a cancellation path, not just a browser disconnect. `RealtimeVoicePanel` must send the same LiveKit agent control before disconnecting, then record durable `stop_output` with `cancel_gemma`, `clear_kokoro_buffers`, and `stop_livekit_audio`, with `create_followup_task=false` because a plain session stop should not create a content handoff. This prevents a hidden Gemma/Kokoro generation from continuing after the creator leaves the room.
Stop is asynchronous and must be run/session owned. Late stop-output control, disconnect, session-end, or refresh completions can only clear product state if the original run/session and stop sequence still own the panel; otherwise they must leave a newer voice session intact.
Connected-session liveness: after the initial room join probe, the product app must continue checking Gemma/Kokoro participant presence while the provider-backed LiveKit room is open. The monitor should refresh durable presence on an interval, send a bounded `voice_agent_presence_probe` only when proof is missing/stale/old, update the visible presence strip, and use the same run/session ownership guard as other voice async paths.
Cancellation failure projection is monotonic around acknowledgements: a late frontend control failure cannot downgrade a Rust or engine acknowledgement, and Stop clears stale cancellation state from the active view.

Current Python agent-engine state:

- `src/all_about_llms/voice_agent/models.py` defines the internal runtime contracts for voice turns, conversation history, assistant audio chunks, events, config, and results.
- `src/all_about_llms/voice_agent/context.py` implements deterministic raw-audio context pruning. It keeps the recent raw-audio window and replaces older audio references with transcript plus compact summary before Gemma receives context.
- `src/all_about_llms/voice_agent/engine.py` implements `GemmaKokoroLiveKitAgentEngine`. It streams Gemma text deltas, flushes sentence/length-bounded fragments to Kokoro, publishes assistant PCM chunks through a LiveKit publisher protocol, emits durable-safe events, and cancels active responses by clearing Kokoro and stopping LiveKit audio.
- `HuggingFaceGemmaAudioReasoner` now attempts SSE/OpenAI-compatible token streaming when `GEMMA4_REALTIME_STREAM_GEMMA=true`, `HF_TOKEN`, and a Gemma endpoint URL are configured. This is the low-latency path that lets Kokoro begin speech before a full Gemma response is complete.
- `src/all_about_llms/voice_agent/livekit_app.py` is the runnable LiveKit participant scaffold. It uses the LiveKit Agents server entrypoint, joins rooms with audio-only subscription, handles transcript/data turns, reads raw audio frames through `rtc.AudioStream`, and forwards bounded turns into the engine.
- `src/all_about_llms/voice_agent/adapters.py` contains the concrete adapter layer for Hugging Face Gemma audio reasoning, hosted or local Kokoro TTS, LiveKit audio-track publishing, and LiveKit data-channel events.
- `src/all_about_llms/voice_agent/edge.py` contains Python adapters for the Rust voice-edge contract. The debug adapter can call one request per subprocess; `PersistentRustVoiceEdgeClient` keeps `voice-edge --jsonl` open for frame-by-frame realtime use, converts PCM16 frames into typed Rust JSON requests, parses VAD speech-start and cancellation events, and returns cancellation acknowledgements to the LiveKit participant.
- `RustVoiceEdgeHttpClient` is the opt-in supervised sidecar adapter. When `RUST_VOICE_EDGE_HTTP_URL` is set, `_build_voice_edge_client` selects HTTP first, posts the same tagged contract to `POST /v1/voice-edge`, and the LiveKit session runs a startup `GET /healthz` preflight before readiness. If the local binary is executable, it wraps HTTP with `FallbackVoiceEdgeClient` so JSONL keeps VAD/barge-in behavior available during startup or request outages. JSONL mode also preflights before readiness by starting the persistent process and sending a harmless cancellation contract.
- `src/all_about_llms/voice_agent/benchmark.py` contains local synthetic benchmark/proof logic for the persistent edge bridge: silence false-positive checks, speech-start detection checks, barge-in cancellation checks, latency summary, and FP/FN-style counters.
- `VoiceTurnCaptureBuffer` in `livekit_app.py` uses Rust VAD events to hold a small pre-roll, open a user turn on `voice_user_speech_started`, and commit after the configured silence frame count.
- `livekit_app.py` now emits `voice_user_turn_committed` before scheduling the Gemma/Kokoro turn, which gives the timing ledger a real end-of-turn marker.
- `frontend/next-app/lib/voice/livekitRuntime.ts` listens to LiveKit `RoomEvent.DataReceived` on topic `agent.voice.event`, normalizes both nested and top-level event envelopes, and the Next voice panel persists those events through `recordRealtimeVoiceEvent`.
- `frontend/next-app/app/page.tsx` and `components/voice/RealtimeVoicePanel.tsx` use active-run refs and run-version tokens for every run-coupled async write. In-flight compose, worker continuation, feedback, production actions, Autopilot controls, and LiveKit voice startup must discard late results after New/run replacement; stale Gemma/Kokoro LiveKit sessions are ended before the UI stores them.
- `frontend/next-app/lib/state/runOwnership.ts` is the shared product-app contract for run-version ownership and run-scoped busy cleanup. `npm run test:race` exercises the stale-run policy, including a deferred old-run async completion that lands after a newer run has taken ownership; Python regression invokes this command so the policy is checked with the backend suite.
- `frontend/next-app/lib/state/autopilotEvidence.ts` is the product-app contract for always-on profile evidence. The Activity panel uses it to bind heartbeat proof to the active/latest autonomous profile by `profile_id`, prefers durable `worker_profile_heartbeat_ledger` artifacts, falls back only to matching heartbeat events, and refuses cross-profile proof borrowing.
- Active autonomous profiles expose a creator-app `Heartbeat` action through `frontend/next-app/lib/api/client.ts::heartbeatWorkerProfile`. The page treats it as run-owned async work, calls `POST /api/worker-profiles/{profile_id}/heartbeat`, then refreshes the run context so the Activity panel can show the new durable heartbeat ledger proof.
- The product `Heartbeat` action must validate current run ownership, active autonomous profile ownership, and duplicate in-flight state before calling the endpoint. Duplicate clicks remain visible as `Running autopilot heartbeat` plus an already-running error rather than an unhandled promise rejection.
- Active autonomous profiles also expose a run-scoped `Run due` scheduler wake through `frontend/next-app/lib/api/client.ts::runWorkerScheduler`. The backend scheduler accepts optional `run_id` and `execution_mode` so the product app does not run unrelated due profiles or non-Autopilot worker profiles, and the Activity panel renders scheduler proof only from `worker_scheduler_pass_completed` events whose `profile_ids` include the active/latest Autopilot profile. If no Autopilot profile exists, heartbeat evidence is hidden even if older heartbeat artifacts exist in the run context. Scheduler in-flight state is tracked per run id so a stale run cannot indefinitely block a newer run's scheduler action.
- Live Postgres proof hardened this path: optional scheduler filters are explicitly typed in SQL, the context packet reads the latest event tail for product Activity, and the side-rail layout keeps Autopilot status/proof readable while controls wrap. Restored run `bcb1fd1a-419a-479b-8588-6e4b42723340` showed scheduler proof for one due Autopilot profile, one heartbeat, and 29 processed tasks before Stop reset the controls to a stopped profile with only Start enabled.
- `POST /api/realtime-sessions/{realtime_session_id}/voice-events` records sanitized voice-agent timing events; `POST /api/runs/{run_id}/realtime-voice-timing-ledger` and `all-about-llms-admin build-realtime-voice-timing-ledger` build the durable timing artifact.
- `src/all_about_llms/orchestration/realtime_voice_timing.py` refuses to assemble readiness from unrelated global first events. It correlates readiness by session plus turn/response identifiers and treats mismatched barge-in acknowledgement/cancellation response ids as missing evidence.
- `all-about-llms-admin run-voice-agent` starts the LiveKit participant process after the optional `voice` dependencies are installed.
- The current participant is not production-complete: the Rust edge bridge is persistent JSONL or request/response HTTP rather than the direct LiveKit media bridge, and a real LiveKit/HF/Kokoro smoke has not run in this workspace. Provider smoke now has the live Gemma/Kokoro TTFT and first-audio measurement step ready for configured credentials.
- The next Rust voice slice must benchmark/tune Silero session pools and stream-state caches under concurrent sessions, then move the JSONL/HTTP bridge into the intended LiveKit-side Rust media service.

Current Rust voice-edge state:

- `services/voice-edge` is a Rust contract-core crate for the low-latency edge.
- `src/contracts.rs` defines JSON-friendly request/response types for audio frames, VAD events, state snapshots, and cancellation acknowledgements.
- `src/vad.rs` implements deterministic energy-gate VAD for local tests and real `silero_onnx` inference through the Rust `silero` crate. `VoiceEdgeConfig` carries `vad_backend`, `target_vad_model`, optional `vad_model_path`, `vad_probability_threshold`, `vad_session_pool_size`, `vad_stream_state_cache_size`, and `allow_vad_fallback`; Silero sessions and recurrent stream states are bounded and reused across JSONL/HTTP requests while the Rust process is alive.
- `src/service.rs` detects user speech starts, bounded inbound-buffer trimming, barge-in while the assistant is speaking, and cancellation acknowledgement actions.
- The cancellation acknowledgement contract already maps to the required side effects: drop outbound audio, cancel Gemma, clear Kokoro buffers, and stop LiveKit audio.
- This crate currently exposes a stdin/stdout JSON CLI, a persistent `--jsonl` mode, and a stateless Axum/Tokio HTTP sidecar mode.
- Python now calls JSONL from `PersistentRustVoiceEdgeClient` when the compiled binary exists at `RUST_VOICE_EDGE_BINARY_PATH`, so the LiveKit participant can use VAD-driven turn commits and honor barge-in cancellation acknowledgements while avoiding per-frame process startup.
- The HTTP sidecar exposes `GET /healthz`, `POST /v1/voice-edge`, `POST /v1/voice-edge/analyze`, and `POST /v1/voice-edge/cancel` using the same typed contract. It is ready for supervised local serving and contract tests; Python can opt in with `RUST_VOICE_EDGE_HTTP_URL`. It is not yet the LiveKit-side Rust media bridge.
- The Python edge client bounds recent frame-window keys and reuses the HTTP async client for opt-in sidecar mode, so long-running sessions do not accumulate unbounded `(session_id, response_id)` windows or reconnect per frame.
- Python treats the JSONL binary as available only when the configured path exists as an executable file, preventing non-executable placeholders from being selected as a fallback.
- The focused test suite includes a real sidecar smoke that launches the compiled HTTP binary, checks `/healthz`, and sends typed analyze, typed cancel, generic analyze, and generic client cancellation requests when loopback binding is available.

Benchmark gates:

- speech-start to interrupt control under the configured latency target;
- speech-end to first text delta;
- first text delta to first Kokoro audio chunk;
- first audio chunk to LiveKit playback;
- false interruption and missed interruption rates;
- bounded queue/memory growth in a 30-minute soak.

Local benchmark entrypoint:

- `all-about-llms-admin benchmark-voice-edge`
- Equivalent direct module command: `PYTHONPATH=src python3 -m all_about_llms.cli benchmark-voice-edge`
- Current scope: local synthetic Rust-edge proof only. It does not replace OpenRouter/LiveKit/Kokoro provider proof.

LiveKit timing ledger entrypoint:

- `all-about-llms-admin build-realtime-voice-timing-ledger --run-id <run-id>`
- Required event chain: current events may still use legacy `gemma_kokoro_*` names until code is renamed, but the proof they represent is the OpenRouter/Kokoro turn over LiveKit: agent ready, speech started, turn committed, provider turn started, reasoning started, assistant text delta, assistant audio chunk published, voice-edge cancellation acknowledged, and turn cancelled.
- Current scope: durable timing proof from persisted LiveKit/OpenRouter/Kokoro events. A real provider-backed room still needs accepted OpenRouter/LiveKit/Kokoro proof-record capture/recheck.

### Obsidian Memory OS

Files:

- `social_media_optimiser/SCHEMA.md`
- `social_media_optimiser/log.md`
- `social_media_optimiser/raw/`
- `social_media_optimiser/wiki/`
- `social_media_optimiser/output/`
- `social_media_optimiser/templates/`

The vault-sync subagent now runs every 5 minutes to keep this planning vault and `system_design_vault/` aligned. The main implementation thread should update the most relevant source notes; the sync subagent owns cross-vault propagation and conflict surfacing.

Responsibilities:

- Keep raw source captures append-only.
- Keep durable synthesized design in wiki notes.
- Keep generated JSON, HTML, reports, and review packets in output.
- Give Codex and product agents a compact lookup path before loading broad context.

Implemented artifacts:

- `wiki/concepts/production-agent-system-design-canon.md`
- `wiki/concepts/three-tier-agent-memory.md`
- `wiki/product/agent-studio-memory-layer.md`
- `wiki/ops/codex-obsidian-working-memory.md`
- `wiki/ops/active-codex-context.md`
- `output/viewers/agent-studio-memory-os.json`
- `output/viewers/agent-studio-memory-os-viewer.html`
- `output/viewers/agent-studio-system-design.json`
- `output/viewers/agent-studio-system-design-viewer.html`

Implemented runtime workflow:

- `src/all_about_llms/orchestration/obsidian_memory.py`
- `src/all_about_llms/orchestration/project_memory.py`
- `src/all_about_llms/orchestration/project_memory_retrieval.py`
- `src/all_about_llms/orchestration/cockpit_walkthrough.py`
- `POST /api/demo/cockpit-run`
- `POST /api/runs/{run_id}/cockpit-walkthrough-ledger`
- `all-about-llms-admin build-cockpit-walkthrough-ledger --run-id <run-id>`
- `POST /api/runs/{run_id}/obsidian-memory-promotion`
- `POST /api/runs/{run_id}/project-memory`
- `POST /api/runs/{run_id}/project-memory/retrieval`
- `POST /api/runs/{run_id}/autonomous-pass` with `export_memory_summary_to_obsidian = true`
- Interactive Note-Taking Agent task `generate_obsidian_memory_promotion`
- Context Engineering/Product Manager/Interactive Note-Taking task `record_project_memory`
- Context Engineering/Knowledge Graph Curator/Product Manager task `retrieve_project_memory`
- Durable artifact type `obsidian_memory_promotion`
- Durable artifact type `project_memory_retrieval_ledger`
- Output notes under `wiki/run-memory-promotions/{run_id}/`
- Context packets include `summary.memory_health` and `stale_project_memories`, `low_confidence_project_memories`, or `conflicting_project_memories` risks when retrieved memory needs review.
- Autonomous memory summaries write `obsidian_note` artifacts under `output/reports/autonomous-memory-summaries/{run_id}/` with provenance `autonomous_memory_summary_export_v1`.
- Project memory retrieval ledgers use pgvector when embeddings are supplied, keyword scoring otherwise, and graph expansion through shared tags, wiki notes, and source artifacts.
- Context packets and resume plans now include compact project-memory retrieval digests without recording extra artifacts, so agents can inspect seed matches, graph-neighbor memories, and memory graph counts before continuing.
- Project memory retrieval ledgers include `evaluation` metrics for labeled or heuristic precision, recall, F1, false-positive ids, false-negative ids, repeated-query counts, and trend deltas against prior ledgers with the same query/agent.
- Worker task context summaries include `project_memory_policy`, and Gemma worker prompts include the policy status/instructions before the model is called.
- Worker-profile heartbeat metrics and scheduler events aggregate project-memory retrieval precision risks, recall gaps, regressed profiles, and no-seed profiles.
- Worker-profile heartbeats now open `project_memory_policy_confirmation` feedback gates and skip execution when policy status is `needs_precision_review`, `needs_recall_repair`, `graph_only_review`, or `regressed`.
- The cockpit Memory Policy panel can send labeled relevance fields to project-memory retrieval so operators can evaluate precision/recall against known-good memory ids, tags, or wiki notes.
- The cockpit Record Project Memory panel can persist user-confirmed `project_decision` and `user_preference` memories with global/run scope, confidence, tags, target wiki notes, source artifact ids, and cockpit provenance through `POST /api/runs/{run_id}/project-memory`.
- The cockpit `Load demo run` action calls `POST /api/demo/cockpit-run` to create a provider-free run with source records, supported claims, post/reel/Substack artifacts, retrieval quality, source ledger, feedback gate, and a `project_decision` memory.
- The cockpit walkthrough ledger records a durable `cockpit_walkthrough_ledger` artifact that packages runtime health, provider readiness, provider-free demo proof, source-ledger coverage, realtime smoke state, provider observability, and feedback-loop state.

### Orchestration

Files:

- `src/all_about_llms/orchestration/content_workflow.py`
- `src/all_about_llms/orchestration/agent_worker.py`
- `src/all_about_llms/orchestration/autonomous_pass.py`
- `src/all_about_llms/orchestration/run_resume.py`
- `src/all_about_llms/orchestration/context_engineering.py`

Responsibilities:

- Content generation workflow.
- A2A task execution.
- Autonomous studio passes.
- Checkpointed resume plans.
- Always-on worker profiles with persisted autonomous pass policy controls.

Worker profile autonomous controls:

- `autonomous_auto_refresh_research_sources`
- `autonomous_block_on_research_freshness_blocked`
- `autonomous_block_on_retrieval_quality_blocked`
- `autonomous_export_memory_summary_to_obsidian`
- `autonomous_memory_summary_agent_id`
- `autonomous_memory_summary_limit`

These fields are persisted in Postgres and routed into `AutonomousStudioPassRequest` when a profile heartbeat runs in `autonomous_pass` mode.

Worker profile observability:

- `worker_profile_heartbeat_ledger` artifacts include a `policy` section with configured memory context, autonomous refresh/block/export controls, and observed outcomes.
- `worker_profile_heartbeat_ledger` artifacts include a `metrics` section with retrieval-quality status/candidate/coverage counts and context memory-health counts.
- `worker_profile_heartbeat` and `worker_profile_heartbeat_blocked` events include the same compact policy and metrics summaries.
- `worker_scheduler_pass_completed` events aggregate `profile_policies`, `profile_metrics`, retrieval-quality blocker/gap counts, memory stale/low-confidence/conflict profile counts, memory-summary export counts, and research-refresh cycle counts across due profiles.
- `worker_profile_heartbeat_blocked` events include `skipped_reason = project_memory_policy_confirmation_required` when a risky project-memory policy gate stopped execution before any worker cycle or autonomous pass.
- The product cockpit renders project-memory policy from explicit retrieval calls, context packets, resume plans, and heartbeat ledgers.
- The creator Activity rail shows `Background runner` status and Start/Stop controls for the local `run-worker-scheduler --watch` process. Internal API, handler, and worker-profile names may still use scheduler/autopilot terminology, but creator-visible labels must use `Always-on studio`, `Specialist pulse`, and `Background runner` language.
- Context packets.
- Feedback gates.

### Provider Boundary

Files:

- `src/all_about_llms/providers/interfaces.py`
- `src/all_about_llms/providers/factory.py`
- `src/all_about_llms/providers/rerank.py`
- `src/all_about_llms/providers/realtime.py`
- `src/all_about_llms/providers/huggingface.py`
- `src/all_about_llms/providers/search.py`
- `src/all_about_llms/providers/imagegen_boundary.py`

Responsibilities:

- Gemma 4/HF expert calls.
- Gemma 4 E4B + Kokoro realtime voice session descriptors.
- Realtime voice metadata for transport framework, context pruning, Rust VAD/barge-in policy, and Python agent-engine responsibilities.
- Optional proprietary realtime/TTS adapters stay non-default and opt-in.
- Realtime audio session creation.
- Web search providers.
- Provider-neutral reranking over fused candidate evidence.
- Image generation boundary.
- Provider readiness and fallbacks.
- `GET /api/provider-readiness` now returns provider documentation links, missing/configured env names, `provider_backed_smoke_ready`, `demo_walkthrough`, and `smoke_test_plan`.
- The cockpit Provider Readiness panel renders smoke steps with status, cockpit action, API path, expected evidence, missing env, and next actions.
- Provider-backed smoke readiness requires OpenRouter live dialogue, the selected realtime provider, the selected web-search provider, and the deterministic reranker to be ready. Postgres + pgvector remains a local runtime prerequisite for durable proof.
- The realtime session endpoint supports `dry_run = true` to create a `local_realtime_rehearsal` session. This lets the browser voice controls, turn routing, spoken response plan, and realtime dialogue ledger run without provider credentials.
- Rehearsal sessions are marked `dry_run` and `not_provider_backed`; the cockpit walkthrough ledger reports their count but still requires a non-rehearsal session from the selected realtime provider before realtime provider smoke is ready.
- The cockpit walkthrough ledger is the run-level proof packet for DB-backed walkthrough QA. It stays blocked until live provider and realtime evidence exist, even when the provider-free demo proof is ready.

### Production Design Contracts

Files:

- `src/all_about_llms/foundation_references.py`
- `src/all_about_llms/agents/roster.py`
- `src/all_about_llms/agents/skills.py`
- `skills/agent-studio-system-architecture/SKILL.md`
- `skills/agent-studio-frontend-engineering/SKILL.md`
- `skills/agent-studio-inference-reliability/SKILL.md`

Responsibilities:

- Map DDIA, ML-system design, inference engineering, effective-agent, guardrail, reliability, Uber Michelangelo, Netflix/Metaflow, Google, OpenAI, Anthropic, AWS, pgvector, LangGraph, and provider references into explicit architecture decisions.
- Keep Backend Platform, Frontend Experience, Scalability/Reliability, and Inference Systems ownership visible as A2A agent cards.
- Keep system architecture, frontend engineering, and inference reliability as project-owned skill cards with source files and runtime skill metadata.
- Make foundation audit counts reflect 38 agents, 9 skills, and 18 reference records.

### Retrieval Intelligence

Current files:

- `src/all_about_llms/orchestration/retrieval_quality.py`
- `src/all_about_llms/orchestration/retrieval_evidence.py`
- `infra/postgres/001_foundation.sql`

Planned files:

- `src/all_about_llms/orchestration/retrieval_intelligence.py`
- `src/all_about_llms/orchestration/knowledge_graph.py`
- `src/all_about_llms/orchestration/retrieval_evaluation.py`

Responsibilities:

- Query rewriting.
- Hybrid sparse/dense/web candidate generation.
- Reciprocal Rank Fusion.
- Reranking.
- Entity and claim graph creation.
- Coverage and FP/FN audits.
- Evidence packets for source-backed drafting.

Implemented endpoint:

- `POST /api/runs/{run_id}/retrieval-quality-ledger`

Implemented artifact:

- `retrieval_quality_ledger`

Implemented harness integration:

- Autonomous pass builds the retrieval quality ledger after research freshness/source refresh.
- Retrieval quality can block downstream creative/review gates only when status is `blocked`.
- Context packets include latest retrieval-quality summary, accepted candidate counts, precision risks, recall gaps, and graph coverage gaps.
- Resume plans surface retrieval-quality status and recommended source repair actions.
- Postgres stores candidate rows, rerank decisions, graph coverage nodes, graph edges where available, and evaluation snapshots in addition to the artifact JSON.

Implemented accepted-evidence slice:

- Extract accepted candidate evidence from the latest `retrieval_quality_ledger` artifact.
- Annotate source-ledger source entries with retrieval rank, rerank score, reranker, and acceptance status.
- Prefer accepted evidence order in context packets and resume summaries once a retrieval ledger exists.
- Restrict specialist writer revisions to accepted retrieval source dependencies when available.
- Fall back to raw source order only when no retrieval-quality ledger has accepted source-linked evidence.

Implemented claim-evidence slice:

- Claim Verification should mark a claim supported only when its source dependencies include accepted retrieval evidence once a retrieval-quality ledger has accepted source-linked candidates.
- Editor-in-Chief should block artifacts whose claims or source dependencies do not overlap accepted retrieval evidence.
- Publish Readiness should independently block artifacts or claims that bypass accepted retrieval evidence, even if earlier review workers have not run yet.
- The cockpit source-ledger panel renders accepted evidence sources, rejected/unaccepted sources, artifact claim coverage, claim-source verdicts, quality/freshness status, and accepted-source overlap from the existing `SourceLedgerSnapshotResult` contract.

Implemented rewrite/hold slice:

- Claim Verification should create a durable `claim_revision_plan` artifact when claims are unsupported, need review, lack sources, or lack accepted retrieval evidence.
- The plan should identify held claim ids, rewrite actions, accepted source alternatives, and writer-facing instructions.
- Writer artifacts should include the latest relevant claim revision context so ELI5/Substack workers know what to rewrite or avoid.
- Claim Verification should materialize idempotent A2A follow-up tasks for ELI5/Substack writers, Script Doctor, and Editor-in-Chief from each claim revision plan.

Implemented closure-ledger slice:

- Artifact Librarian builds a `claim_revision_ledger` snapshot from the latest claim revision plan, follow-up A2A task statuses, revised artifacts, editor review state, and current held-claim support.
- Publishing handoff includes the latest claim revision ledger summary and blocks handoff status while claim revision work is still open.
- Product Manager sync pulse surfaces the latest claim revision ledger and records a blocker when the held-claim loop is still open.
- Always-on autonomous profile heartbeats are covered by regression tests: after claim-revision writer, script, and editor follow-ups complete, the same autonomous pass records a refreshed ledger showing no pending follow-ups and a `needs_claim_reverification` next action when held claims still need verification.

### Obsidian Review Notes

Implemented files:

- `src/all_about_llms/orchestration/obsidian_notes.py`

Responsibilities:

- Write vault-native Markdown review notes under `social_media_optimiser/03-review-packets/runs/`.
- Summarize run status, latest retrieval quality, source evidence, artifacts, feedback, pending A2A work, and recommended next actions.
- Record the note as a durable artifact so the product run, event stream, and Obsidian vault stay linked.
- Keep HTML as a companion visualization only, not the canonical review record.

## Data Contracts To Add

### RetrievalCandidate

Fields:

- `candidate_id`
- `source`
- `retriever`
- `query`
- `title`
- `url`
- `snippet`
- `rank`
- `score`
- `metadata`

### RerankDecision

Fields:

- `candidate_id`
- `reranker`
- `rank_before`
- `rank_after`
- `relevance_score`
- `reason`

### KnowledgeGraphNode

Fields:

- `node_id`
- `node_type`
- `label`
- `source_ids`
- `claim_ids`
- `metadata`

### KnowledgeGraphEdge

Fields:

- `edge_id`
- `from_node_id`
- `to_node_id`
- `relationship`
- `confidence`
- `source_ids`

### RetrievalEvaluation

Fields:

- `run_id`
- `precision_proxy`
- `recall_proxy`
- `coverage_score`
- `false_positive_risks`
- `false_negative_risks`
- `recommended_queries`

## Implementation Order

1. Done: add agent cards for Retrieval Intelligence Agent and Knowledge Graph Curator Agent.
2. Done: add retrieval quality contracts and ledger endpoint.
3. Done: add Postgres tables for retrieval candidates, rerank decisions, graph nodes, graph edges, and retrieval evaluations.
4. Done: add retrieval quality to autonomous pass, context packets, resume plans, and Postgres evidence persistence.
5. Done: add Obsidian review note output for run/retrieval evaluations.
6. Done: add provider-neutral reranker interface.
7. Done: add accepted-evidence integration so source ledger, context packets, resume plans, and writer artifacts use the retrieval-quality decision set.
8. Done: make Claim Verification, Editor-in-Chief, and Publish Readiness consume accepted evidence directly before final drafting and publication.
9. Done: create rewrite/hold artifacts for unsupported or unaccepted claims so writers get explicit revision instructions rather than only gate failures.
10. Done: route claim revision plans into targeted A2A follow-up tasks so writers and editors automatically close the loop.
11. Done: add and verify a claim revision closure ledger that summarizes follow-up status and remaining held claims, including the always-on autonomous profile path.

## Mixed-Mode Live Dialogue Contract

- The product live voice session supports both microphone audio and typed text as first-class inputs to the same Gemma/Kokoro LiveKit participant.
- Browser text turns publish reliable LiveKit data on `agent.voice.control` with `type=transcript_turn`, UUID `turn_id`, run id, realtime session id, room name, transcript, voice, and expected agent identity.
- The Python LiveKit participant accepts data-channel turns only when topic, run id, realtime session id, and creator participant identity match the current session.
- Empty or non-string direct `transcript_turn` payloads emit `voice_text_turn_rejected` and do not enter Gemma/Kokoro.
- Typed turns emit `voice_user_turn_committed` with `input_modality=text` and `windowing=livekit_data_transcript`; microphone turns emit `input_modality=voice`.
- Durable materialization uses `input_modality` so typed live turns appear as text conversation turns while assistant completions still flow through `assistant_response_completed`, realtime follow-up tasks, and Kokoro speech output.
- The product UI enables the typed live-turn form only when the provider-backed LiveKit room is connected and fresh `gemma_kokoro_voice_agent_ready` presence exists. If the agent is thinking or speaking, typed input first publishes the same interrupt contract used by barge-in.

## Product Source Ledger Visibility

- Source-backed drafts must expose source provenance in the product app, not only in backend artifacts.
- The Source panel shows claim support counts for supported, needs-review, and unsupported claims before listing sources.
- Each source row shows whether it is a live web-search result, search seed, provider reference, or generic source record.
- Live search metadata includes freshness, rank, query, published timestamp when available, retrieved timestamp, and recorded snippet.
- Search seeds must be visibly labeled as needing provider-backed web research before publish so seed fallbacks cannot masquerade as real evidence.
- Search seeds must also be actionable in the product app. The Source panel shows live-source and search-seed counts and exposes `Run web research` only when a search seed exists.
- The source-refresh action creates a targeted A2A `research_topic` message for `web-research-agent` when there is no runnable web-research task, then runs a bounded worker cycle for Web Research Agent and Claim Verification Agent with Gemma disabled.
- The action passes visible deduped seed queries as capped `search_queries`; Web Research Agent must execute each admitted query, record per-result `search_query` metadata, and report skipped query count when the cap is reached instead of searching only the first display topic or fanning out without bound.
- Once source repair moves claims away from weak/search-seed sources, historical seed records remain in the ledger for provenance but should not keep the refresh affordance visible as unresolved work.
- Runnable web-research tasks are intentionally narrow: task type `research_topic` plus status `accepted`, `claimed`, or `in_progress`. Unrelated task types, failed, blocked, canceled, completed, or human-waiting tasks must not suppress a fresh source-refresh enqueue.
- If provider-backed search is missing and Gemma fallback is disabled, the Web Research Agent records `web_search_provider_blocked`, appends `web_research_blocked`, and still builds a research freshness ledger. The product UI must show that blocked reason beside the source ledger instead of implying the seed was refreshed.
- Successful web research must surface accepted-source count in the Source panel from durable task/event proof, so users can distinguish `Research refreshed` from `Research blocked` without inspecting raw JSON.
- Successful web research also owns the next A2A handoff. When source repair changes claim dependencies, Web Research Agent creates an idempotent `verify_source_refresh_claims` task for Claim Verification Agent unless a runnable claim-verification task already exists.
- The creator-facing source-refresh action should allow that claim-verification follow-up to execute in the same bounded refresh cycle when Web Research Agent creates it, making the UI evidence closer to the actual source and claim state.
- The claim-verification follow-up depends on the web-research task and carries repaired claim ids, replacement source ids, freshness ledger id, and source-repair metadata so Claim Verification can re-evaluate after source replacement.
- Malformed source URLs render as non-link titles so evidence inspection never creates unsafe or broken anchors.
- Claim rows remain attached to each source with support status icons and text so users can inspect which claims depend on which evidence.
- Accepted retrieval evidence is a first-class source drilldown. The Source panel consumes context `source_evidence` and shows accepted/not-accepted context status, retrieval rank, rerank score, reranker, quality/freshness, coverage topics, rerank reason, and precision/recall risks per source.
- The accepted-evidence summary separates source count from source quality: live source count, unresolved search seeds, accepted context evidence, precision risks, recall risks, coverage topics, and quality issues are all distinct product signals.

## Product Draft Evidence Visibility

- Draft review cards must show evidence and guardrail state directly beside the draft, not only in the source ledger rail.
- Each draft card shows source count, supported claim count, needs-review claim count, unsupported claim count, latest reviewer decision, revision count, and deduplicated linked-claim count.
- A draft with no sources or unsupported claims is blocked; a draft with needs-review claims is review-needed; a fully source-backed draft is supported.
- Draft claim linkage prefers explicit artifact `claim_ids` from content/provenance; source-overlap is only a legacy fallback.
- Linked claims are deduplicated across source ids so a claim that cites multiple draft sources is not double-counted.
- This is product UI for creator review and revision routing; it is not a planning cockpit surface.

## Product Artifact Content/Proof Boundary

- The product artifact board defaults to content artifacts because the creator's primary job is drafting, revising, and publishing content.
- Operational proof artifacts remain inspectable through `Proofs` and `All`, but they are copy/export evidence, not draft-edit targets.
- Content artifacts are `post`, `reel_script`, `substack_article`, `social_package`, `image`, `audio`, and `video`.
- Non-content artifacts such as setup proofs, ledgers, scheduler proof, and source proof must not render revision checkboxes, Revise buttons, linked-claim revision pills, or count as selected drafts.
- Page-level production calls for revision, media plan, distribution package, and publish readiness consume the content-filtered selected artifact list, not raw UI selection state.
- Regression coverage locks both the component behavior and the page-level selected-artifact contract; `Leibniz` review found no blockers.

## Product Voice Provider Release Gate

- The actual creator voice panel consumes `/api/provider-readiness`; planning/cockpit surfaces are not the authority for provider readiness.
- The release gate is scoped to the selected route: OpenRouter live-dialogue reasoning, selected OpenRouter/Kokoro realtime provider, selected web-search provider, selected reranker, runtime preflight, current voice-agent participant presence, and latest provider-smoke proof.
- Missing environment variables must be reported only for the selected release-gate providers. Unused OpenAI, Cartesia, ElevenLabs, Hugging Face/Gemma, Gamma, MLX, or other inactive providers must not pollute the OpenRouter/Kokoro readiness path.
- Rehearsal mode and non-live provider smoke are useful product proofs, but they cannot mark the route provider-backed ready.
- Current-session readiness also requires an active provider-backed LiveKit session; participant proof and provider smoke must match that session id before the gate can be ready.
- Ready state requires live provider smoke with `provider_backed` proof and a passing OpenRouter/Kokoro streaming step, so the UI does not confuse local transcript rehearsal with real voice-to-voice production readiness.

## Local Secret Boundary

- Local provider credentials should be read from ignored files when possible.
- `HF_TOKEN_FILE` points at a token file such as `.secrets/hf_token`; `Settings` promotes the file content into the effective `hf_token` only at runtime.
- `TAVILY_API_KEY_FILE` points at a token file such as `.secrets/tavily_api_key`; `Settings` promotes the file content into the effective `tavily_api_key` only at runtime.
- Direct secret env values are stripped; blank direct values do not suppress file fallback, and missing or empty files keep readiness blocked without failing process startup.
- Readiness reports may say `HF_TOKEN` is configured because that is the effective credential boundary, but the token value must never appear in events, screenshots, docs, or tracked files.
- Provider readiness exposes only file status metadata for selected secret-file routes: file env name, status, configured boolean, optional path, and non-secret detail.
- The product release gate renders those diagnostics so a creator can fix local secret files without inspecting backend logs or exposing token values.
- `.env` can hold non-secret routing defaults and file paths, while endpoint URLs and provider keys remain explicit blockers until configured.

## Hugging Face Gemma Routing - Legacy/Non-Default

This section is retained for specialist expert agents and future native-audio experiments. It is not the active realtime dialogue direction and must not block OpenRouter + LiveKit + Kokoro proof capture.

- Text/chat expert-agent calls prefer dedicated Gemma endpoint URLs when present.
- If no dedicated text endpoint is configured and `HF_INFERENCE_ROUTER_ENABLED=true`, the Gemma expert provider uses the Hugging Face router chat-completions endpoint with the requested Gemma model id.
- The router URL must be a valid `http(s)` URL with a host. Malformed values are treated as missing configuration instead of provider-backed readiness.
- The router route is only promoted for text/chat expert synthesis and smoke tests. Native realtime voice remains a separate route because it needs audio attachment handling, streaming deltas, Kokoro first-audio proof, and session-bound LiveKit evidence.
- Voice code disables default router fallback when no dedicated audio endpoint exists, so missing Gemma audio endpoint config remains visible if and only if a native Gemma audio route is explicitly selected. It must not block the active OpenRouter route.
