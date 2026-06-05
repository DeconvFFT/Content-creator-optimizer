---
type: status-snapshot
updated: 2026-05-24
---

# Status Snapshot — Local Voice Stack

## Docker (verified 2026-05-23 16:53 CDT)

| Container | Status | Ports |
|-----------|--------|-------|
| `all-about-llms-postgres` | Up (healthy) | 5432 |
| `all-about-llms-livekit` | Up | 7880-7882 |

LiveKit logs also show a Cursor-started worker registered as the local voice agent. The FastAPI supervisor may still report `voice-agent-process.status=stopped` because the process was launched externally by Cursor, not by the app supervisor.

## Secrets / env

| File | Present |
|------|---------|
| `.secrets/openrouter_api_key` | yes (live dialogue reasoning) |
| `.secrets/livekit_api_key` | yes |
| `.secrets/livekit_api_secret` | yes |
| `.env` | OpenRouter + LiveKit configured; MLX/Gamma/Gemma multimodal default removed |

## Provider readiness (HTTP 200)

| Provider | Status | Blocker |
|----------|--------|---------|
| `openrouter-livekit` | ready | OpenRouter DeepSeek V4 Flash + LiveKit transport |
| LiveKit / Kokoro / voice checks | see `/api/voice-runtime-readiness` | `openrouter-live-dialogue-reasoning` covers the current text-turn dialogue path |

## Runtime preflight (verified outside sandbox 2026-05-23 16:53 CDT)

| Check | Status | Note |
|-------|--------|------|
| `livekit-transport` | ready | RoomService/ListRooms succeeded against `127.0.0.1:7880` |
| `livekit-agent-participant` | ready | Agent server startup preflight constructed the participant server |
| `voice-agent-backend-event-sink` | ready | FastAPI `/health` succeeded on `127.0.0.1:8000` |
| `openrouter-live-dialogue-reasoning` | ready | OpenRouter streaming returned a text delta |
| `kokoro-tts` | ready | Local Kokoro package importable |
| `rust-voice-edge` | ready | Persistent JSONL voice-edge preflight passed |
| `gemma-audio-reasoning` | blocked, not required for current path | Legacy native-Gemma check only; do not use it as the active blocker |

The earlier Cursor setup failure was `WritableIterable is closed` in a subagent transcript while it was still reading files. Treat that as Cursor orchestration/streaming failure, not a LiveKit/Docker failure.

## Codex continuation check (2026-05-23 CDT / 2026-05-24 UTC)

Codex verified Docker LiveKit/Postgres and FastAPI health without disturbing Cursor processes, then started the app-supervised OpenRouter/Kokoro voice-agent process (`pid=29685`) through the backend supervisor. `runtime-health-ledger.json` is now `ready` with 10/10 checks ready, and the refreshed `provider-smoke-ledger.live-openrouter.json` passes with ledger artifact `94857bb9-c5eb-4174-8bc5-6687bd8befbe`, selected realtime session `ebd43531-86e3-4af1-ade0-15ac8d7184bf`, OpenRouter first text delta `1111.171 ms`, Kokoro first audio chunk `4946.351 ms`, and first-audio latency `6057.54 ms`.

Superseded on 2026-05-24: this was the intermediate state before the accepted live-voice capture below. Superseded again on 2026-05-28: the current manual-publication proof path no longer requires a LinkedIn token file; publication remains blocked only on durable manual-publication policy, destination, and rollback/postcondition evidence.

## Proof workspace refresh (verified 2026-05-23 17:06 CDT)

| Artifact | Status | Note |
|----------|--------|------|
| `voice-runtime-readiness.preflight.json` | ready | OpenRouter live dialogue, LiveKit, Kokoro, Rust edge, and participant construction are ready |
| `provider-backed-live-voice-proof.preflight-validation.json` | valid | OpenRouter DeepSeek live dialogue, LiveKit, Kokoro, Rust edge, and participant checks validate for the current path |
| `current-blocker-matrix.json` | live voice accepted; publication still blocked | Live voice has no remaining operator-input blocker; external publication is now blocked by manual-publication evidence only |
| `external-publication-proof.preflight-validation.json` | invalid | Manual-publication policy/destination/rollback evidence remains missing |

Superseded on 2026-05-24: the live-voice accepted record now carries same-run OpenRouter DeepSeek dialogue evidence, LiveKit/session evidence, provider-smoke and timing ledgers, zero failed post-capture validation checks, and passed secret-redaction checks.

## Proof record refresh (verified 2026-05-23 CDT / superseded 2026-05-24 UTC)

The older `provider-backed-live-voice-proof.failed-record.json` referenced OpenRouter smoke ledger `94857bb9-c5eb-4174-8bc5-6687bd8befbe`, timing ledger `3244077a-e689-4d26-9a9e-ff8c1ddb74df`, and realtime session `ebd43531-86e3-4af1-ade0-15ac8d7184bf`. This failed-record state is superseded by the accepted live-voice proof below.

## Accepted live-voice proof (verified 2026-05-24 UTC)

Codex captured and recorded the accepted provider-backed live-voice proof for run `190ae2f9-a74b-4a23-b39c-aaf2d636bd8e`.

| Evidence | Current value |
|----------|---------------|
| Accepted proof | `provider-backed-live-voice-proof.accepted-record.json` |
| Realtime provider | `openrouter_livekit` |
| Provider smoke ledger | `94857bb9-c5eb-4174-8bc5-6687bd8befbe` |
| Timing ledger | `7e932381-4bf4-4206-a490-58d6a4ca7880` |
| Realtime session | `ebd43531-86e3-4af1-ade0-15ac8d7184bf` |
| LiveKit timing capture | `livekit-voice-timing-capture.json` |
| Post-capture validation | 7/7 checks passed, including first text/audio plus interruption evidence |
| Secret redaction | passed |

`completion-status.json` now lists `provider-backed-live-voice-proof` in `accepted_proofs`. The overall objective is not complete because `external-publication-proof` remains the latest failed proof.

## Remaining objective blocker (verified 2026-05-24 UTC)

External publication remains blocked by operator inputs and must not be faked or performed without action-time approval. As of the 2026-05-28 manual-publication path, the required inputs are a durable policy acknowledgement artifact id, a durable LinkedIn destination URL or platform id, and a durable rollback/postcondition artifact id; no LinkedIn token file is required for this path.

## Backend runtime caveat (verified 2026-05-23 CDT / 2026-05-24 UTC)

The pre-existing FastAPI process on `127.0.0.1:8000` is still listening, but `/health` timed out and the Next dev proxy reported repeated `ECONNRESET` responses from `/api/worker-scheduler-process`. A temporary isolated backend on `127.0.0.1:8001` returned `/health` successfully, so the current issue appears to be a stale or wedged existing process rather than a failing import/startup path. Do not restart the shared `:8000` process without operator approval because Cursor agents may still be attached to it.

## Test locally now

- LiveKit WebRTC transport (container **up**)
- OpenRouter live text-turn dialogue via Live Voice panel (**Send text turn**)
- Kokoro spoken replies over LiveKit
- Creator UI voice run creation + room join
- Cockpit at `/cockpit`

## No longer required for live dialogue

- MLX server on `:8080`
- MLX proxy on `:8090`
- `GEMMA4_MULTIMODAL_ENDPOINT_URL`

See [[openrouter-livekit-live-dialogue]] for the current runbook.

## Completion-status parser correction (verified 2026-05-24 UTC)

Codex found and fixed a status-only parser drift: a valid accepted `provider-backed-live-voice-proof` note could be marked invalid when ordinary Obsidian `##` sections followed the proof record. The parser now stops proof-record parsing at the next top-level Markdown section.

Fresh completion status for run `190ae2f9-a74b-4a23-b39c-aaf2d636bd8e` reports `provider-backed-live-voice-proof` accepted, no invalid accepted audit-note proofs, and `external-publication-proof` as the only latest failed proof. This does not change the remaining operator-owned LinkedIn publication blocker.

Verification passed: provider-proof CLI suite `201 passed, 30 skipped`; static proof/system-design browser render tests `6 passed`; stable Python CI slice `230 passed, 30 skipped`.
