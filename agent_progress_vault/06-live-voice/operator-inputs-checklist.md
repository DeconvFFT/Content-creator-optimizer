---
type: operator-checklist
updated: 2026-05-24
proof_run_id: 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e
---

# Live Voice And Publication Operator Inputs Checklist

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

## Accepted live-voice proof

- [x] Accepted proof-record capture/recheck for run `190ae2f9-a74b-4a23-b39c-aaf2d636bd8e`
- [x] Same-run timing evidence for LiveKit ready, speech, user-turn commit, OpenRouter generation, text/audio output, and barge-in/cancellation proof
- [x] Accepted proof record with provider-smoke ledger `94857bb9-c5eb-4174-8bc5-6687bd8befbe`, timing ledger `7e932381-4bf4-4206-a490-58d6a4ca7880`, realtime session `ebd43531-86e3-4af1-ade0-15ac8d7184bf`, and secret-redaction pass

## Still required for objective completion

- [ ] `LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID` is a durable non-local policy acknowledgement artifact id
- [ ] `PUBLICATION_DURABLE_PLATFORM_ID_OR_URL` is a durable LinkedIn URL or platform id
- [ ] `PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID` is a durable rollback or postcondition artifact id
- [ ] External publication proof is validated and recorded after explicit action-time approval

## Optional (later / cloud)

- [ ] Cloud LiveKit project URL + production keys
- [ ] `KOKORO_TTS_ENDPOINT_URL` if not using local Kokoro package

## Proof vs local demo

| Goal | Needs |
|------|-------|
| OpenRouter back-and-forth demo in browser | LiveKit + voice agent + **Send text turn** composer |
| Accepted `provider-backed-live-voice-proof` | Done for run `190ae2f9-...` |
| Accepted `external-publication-proof` | Manual publication policy acknowledgement, durable destination, rollback/postcondition evidence, and explicit operator approval |

See [[local-livekit-setup]] for start commands.
