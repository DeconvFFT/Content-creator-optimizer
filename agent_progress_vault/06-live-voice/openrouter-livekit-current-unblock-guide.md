---
type: current-unblock-guide
updated: 2026-05-24
active_realtime_path: OpenRouter LiveKit Kokoro
proof_run_id: 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e
---

# OpenRouter LiveKit Current Unblock Guide

This is the active live-dialogue and proof handoff path for Agent Studio.

## Current Live Dialogue Direction

- Reasoning: OpenRouter `deepseek/deepseek-v4-flash`
- Transport: LiveKit, local dev URL `ws://127.0.0.1:7880`
- Speech output: Kokoro
- Active setup fields: `OPENROUTER_API_KEY_FILE`, `OPENROUTER_LIVEKIT_URL`, `LIVEKIT_API_KEY_FILE`, and `LIVEKIT_API_SECRET_FILE`

## Current Proof State

- `provider-backed-live-voice-proof`: accepted for run `190ae2f9-a74b-4a23-b39c-aaf2d636bd8e`
- `external-publication-proof`: still blocked by LinkedIn token file, policy acknowledgement artifact, durable LinkedIn URL/platform id, and rollback or postcondition evidence
- Completion status: not complete until external publication proof validates, records, and passes closure review
- PR state: feature branch is pushed and CI is green, but PR creation may need the manual `provider-proof-pr-handoff` body until GitHub integration permissions are upgraded

## Do Next

1. Fill a local no-secret operator input file from `social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env`.
2. Keep secret values in files only; do not paste token values into notes, commits, PR bodies, or logs.
3. Run strict readiness:
   `uv run all-about-llms-admin provider-proof-operator-input-readiness --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e --input-path social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env --fail-on-blocked`
4. After readiness clears, regenerate credential snapshot, proof plan, current blocker matrix, current proof status, and operator checklist from the generated command chain.
5. Capture and validate the LinkedIn external publication proof only after explicit action-time approval.
6. Record the accepted external publication proof into the configured audit targets, then rerun completion status and closure review.

## Non-Default Legacy Boundary

Do not open new Hugging Face, Gamma, Gemma, or MLX setup tasks for the current realtime dialogue proof unless a later architecture decision explicitly reverses the OpenRouter default. The native-audio lane remains historical reference or optional non-default research only.

Use [[openrouter-livekit-live-dialogue]], [[local-livekit-setup]], [[operator-inputs-checklist]], and [[status-snapshot-2026-05-23]] for supporting context.
