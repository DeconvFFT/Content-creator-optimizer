# Agent Operating Contract

This repo is the product/code workspace for Agent Studio. The Obsidian vaults are planning and memory artifacts, not product UI. Keep the app boundary clear.

## Branch And PR Flow

- Use branch prefixes that describe the work: `feature/` for new features, `fix_` plus a timestamp or UUID for bug fixes, and `tests/` for test-only changes.
- Prefer small PR-style commits with focused verification notes.
- Do not merge or claim completion until CI is green and the proof gates below are checked.
- `.github/workflows/auto-pr.yml` should create or update a draft PR after matching branch CI passes on `feature/**` or `fix_*` pushes, using only the workflow `GITHUB_TOKEN`, a temporary no-secret PR input file, and the committed no-secret operator input example as the key-list reference. If repository Actions settings deny PR creation, it should fail the Auto PR job with `Auto PR failed` so the missing repository permission is not reported as a green PR-creation gate.
- If workflow PR creation or integration PR creation is blocked, try the no-secret `provider-proof-pr-create` helper with `GITHUB_TOKEN` or `GH_TOKEN`; if no token is available, leave the branch pushed and record the exact blocker in the vault handoff.

## Files That May Be Versioned

- Code, tests, `.github/workflows/ci.yml`, `.github/workflows/auto-pr.yml`, `uv.lock`, lightweight Markdown coordination files, `AGENTS.md`, `agents.md`, `CLOUD.md`, and `cloud.md`.
- `uv.lock` is the committed Python dependency lockfile; include it when Python dependencies change.
- Local command-log artifacts are transient output and must not be tracked.

## Files That Must Stay Out

- Do not commit secrets, `.env` values, secret files, provider tokens, raw private provider responses, private audio, screenshots, PDFs, generated media, generated proof workspaces, local caches, or large artifacts.
- Use secret file references such as `.secrets/...` only in local operator inputs; never print or commit secret contents.

## Current Realtime Stack

- The active realtime dialogue path is OpenRouter `deepseek/deepseek-v4-flash` + LiveKit + Kokoro.
- Do not use Hugging Face, Gemma4, Gamma4, or MLX as active realtime defaults for the current live dialogue proof path.
- Do not restart Cursor, backend, LiveKit, Docker, or shared local processes unless the operator explicitly approves it.

## Vault Coordination

- Check `agent_progress_vault` for Cursor/background-agent status before touching runtime-sensitive work.
- Keep durable implementation memory in `social_media_optimiser` and architecture implications in `system_design_vault`.
- Preserve source attribution between vaults and avoid duplicate long-form notes.

## Proof Gates

- `provider-backed-live-voice-proof` is the OpenRouter/LiveKit/Kokoro proof gate. Its current accepted state must not be reopened without new evidence.
- `external-publication-proof` is the remaining publication gate. It must not be faked with local substitutes.
- The current external publication proof requires these operator-owned inputs:
  - `LINKEDIN_ACCESS_TOKEN_FILE`
  - `LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID`
  - `PUBLICATION_DURABLE_PLATFORM_ID_OR_URL`
  - `PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID`
- Publication artifact inputs must be durable external evidence references, not generic bare local labels.
- After operator inputs are supplied, refresh readiness, credential snapshot, proof plan, blocker matrix, current status, unblocker checklist, completion status, closure review, and blocker-state update in that order.

## Verification Baseline

- Run the narrow test for your change first.
- Before pushing, run relevant Python, frontend, Rust, or browser-render checks for the touched surface.
- For proof-gate changes, include a fresh no-secret `provider-proof-completion-status` or operator-readiness command result in the vault handoff.
