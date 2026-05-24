---
type: operator-checklist
updated: 2026-05-23
proof_run_id: 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e
---

# Live Voice Operator Inputs Checklist

## Done

- [x] **OpenRouter key** → `.secrets/openrouter_api_key`
- [x] **LiveKit local dev key** → `.secrets/livekit_api_key` (`devkey`)
- [x] **LiveKit local dev secret** → `.secrets/livekit_api_secret` (`secret`)
- [x] **LiveKit URL** → `OPENROUTER_LIVEKIT_URL=ws://127.0.0.1:7880`

## Done in current local stack

- [x] **Docker running** — Postgres healthy and LiveKit up on `7880-7882` (verified 2026-05-23 16:53 CDT)
- [x] **Voice dependencies installed** — LiveKit agents and Kokoro import in runtime preflight
- [x] **Rust voice-edge built** — `services/voice-edge/target/debug/voice-edge`
- [x] **OpenRouter live dialogue route** → `deepseek/deepseek-v4-flash` via `.secrets/openrouter_api_key`

## Still required for accepted live-voice proof

- [ ] Accepted proof-record capture/recheck for run `190ae2f9-a74b-4a23-b39c-aaf2d636bd8e`
- [ ] Same-run timing evidence for the remaining live voice stages: audio-track bridge, speech start, end-of-turn/agent-turn correlation, and barge-in stop
- [ ] Accepted proof record with provider-smoke ledger `94857bb9-c5eb-4174-8bc5-6687bd8befbe`, timing ledger `3244077a-e689-4d26-9a9e-ff8c1ddb74df`, realtime session `ebd43531-86e3-4af1-ade0-15ac8d7184bf`, and secret-redaction pass

## Optional (later / cloud)

- [ ] Cloud LiveKit project URL + production keys
- [ ] `KOKORO_TTS_ENDPOINT_URL` if not using local Kokoro package

## Proof vs local demo

| Goal | Needs |
|------|-------|
| OpenRouter back-and-forth demo in browser | LiveKit + voice agent + **Send text turn** composer |
| Accepted `provider-backed-live-voice-proof` | OpenRouter DeepSeek + LiveKit + Kokoro proof capture chain for run `190ae2f9-...` |

See [[local-livekit-setup]] for start commands.
