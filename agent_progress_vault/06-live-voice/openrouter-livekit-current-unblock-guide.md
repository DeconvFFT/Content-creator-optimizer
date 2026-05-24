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
- External publication validation now rejects local/draft/bare-placeholder policy acknowledgement and rollback/postcondition artifact references in both accepted proof records and compact audit notes; use durable non-local artifact IDs only.
- Completion status: not complete until external publication proof validates, records, and passes closure review
- PR state: feature branch is pushed and CI is green, but PR creation may need either the token-aware `provider-proof-pr-create` helper or the manual `provider-proof-pr-handoff` body until GitHub integration permissions are upgraded

## Current Manual PR Handoff

- Latest live check: the pushed feature branch had green GitHub Actions CI for the branch head at check time.
- Regenerate exact PR evidence at manual PR creation time; do not treat this vault note as the source of truth for branch head or CI run because follow-up documentation commits can make pinned values stale.
- Token-aware PR attempt:
  `uv run all-about-llms-admin provider-proof-pr-create --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e --operator-input-path social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env --ci-url <latest-branch-head-ci-url> --head-sha <current-branch-head-sha>`
- Manual PR body command:
  `uv run all-about-llms-admin provider-proof-pr-handoff --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e --operator-input-path social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env --ci-url <latest-branch-head-ci-url> --head-sha <current-branch-head-sha>`
- Manual PR handoff output includes `operator_input_example: docs/external-publication-operator-inputs.example.env`; use that committed no-secret file as the key list before filling the ignored UUID operator input file locally.
- PR handoff output now redacts operator-input and provider-proof output paths outside the checkout to portable placeholders such as `<filled-ignored-operator-input-file>` and `<provider-proof-output-dir>`, so CI runner temp paths and local absolute paths do not enter PR descriptions.
- Manual PR compare: <https://github.com/DeconvFFT/Content-creator-optimizer/compare/main...feature/livekit-voice-proof-capture?expand=1>
- Automated PR creation through the GitHub connector remains blocked by integration permission `403 Resource not accessible by integration`; `provider-proof-pr-create` can create the PR only when a local `GITHUB_TOKEN` or `GH_TOKEN` is available, otherwise use the generated `provider-proof-pr-handoff` body in a manual PR until repository app permissions are upgraded.
- Auto-merge cannot be enabled by this session until a PR exists and repository settings permit the integration to mutate it.

## Do Next

1. Fill a local no-secret operator input file from `social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env`, using `docs/external-publication-operator-inputs.example.env` as the committed placeholder-only key list.
2. Keep secret values in files only; do not paste token values into notes, commits, PR bodies, or logs.
3. Run strict readiness:
   `uv run all-about-llms-admin provider-proof-operator-input-readiness --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e --input-path social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env --fail-on-blocked`
4. After readiness clears, regenerate credential snapshot, proof plan, current blocker matrix, current proof status, and operator checklist from the generated command chain.
5. Capture and validate the LinkedIn external publication proof only after explicit action-time approval.
6. Record the accepted external publication proof into the configured audit targets, then rerun completion status and closure review.

## Non-Default Legacy Boundary

Do not open new Hugging Face, Gamma, Gemma, or MLX setup tasks for the current realtime dialogue proof unless a later architecture decision explicitly reverses the OpenRouter default. The native-audio lane remains historical reference or optional non-default research only.

Use [[openrouter-livekit-live-dialogue]], [[local-livekit-setup]], [[operator-inputs-checklist]], and [[status-snapshot-2026-05-23]] for supporting context.
