# Cloud And Repository Operations Handoff

This is the no-secret cloud setup checklist for Agent Studio in `DeconvFFT/Content-creator-optimizer`.

## Current Branch

- Branch: `fix_20260528-live-postgres-gate`
- Target: `main`
- PR body source: `provider-proof-pr-handoff`
- Token-aware helper: `provider-proof-pr-create`
- Local `gh` CLI is not installed in the current Codex environment.
- GitHub connector PR creation currently returns `403 Resource not accessible by integration`.
- Latest branch-head evidence must be regenerated before opening or updating a PR. Do not treat committed SHA or run IDs as current evidence; run `provider-proof-pr-handoff` with fresh `--ci-url` and `--head-sha` values from the latest branch-head CI. The current known blocker is still repository PR mutation: Auto PR can reach the no-secret handoff step but should now emit `Auto PR failed` and fail the Auto PR job when repository settings deny draft PR create/update, and local `provider-proof-pr-create` returns `manual_required` until `GITHUB_TOKEN` or `GH_TOKEN` is available.
- Fresh connector attempt after the latest green branch-head CI still returned `403 Resource not accessible by integration`; REST PR lookup returned no open PR for the current branch. Continue with manual PR creation or repository Actions/app permission changes.
- Fresh continuation check on 2026-05-24 after the proof-handoff refresh and before the Auto PR fail-fast fix: remote branch head `08ac1e7d09c784357d5ffcb9adc52a863d27c738` had green CI at `https://github.com/DeconvFFT/Content-creator-optimizer/actions/runs/26384108251`; Auto PR run `26384108228` completed successfully but no pull request exists for `DeconvFFT:feature/livekit-voice-proof-capture`; and `provider-proof-pr-create` still returned `manual_required` / `github_token_unavailable` in this environment. Remote `main` is `f45c0a3f3659301c944e3bed0c58197efeab0719`. Regenerate exact SHA/CI evidence after any follow-up commit.
- Fresh continuation check on 2026-05-25 after pushing the Auto PR fail-fast fix: local branch head is `c995e386e7bde9a2580ea22c99d3903b3dbcf8c0`, and GitHub runs for that commit had started, but current Codex network polling could not reach GitHub to verify final CI or Auto PR conclusions. Regenerate exact SHA/CI evidence before opening or updating a PR.
- Fresh local state after the vault/handoff sync: the branch has one local commit waiting to push, but HTTPS to GitHub currently fails before the remote handshake. Fresh proof checks still show accepted OpenRouter/LiveKit/Kokoro live voice and external publication blocked on the three operator-owned manual-publication evidence inputs.
- Fresh local proof/view check on 2026-05-26: existing static proof/readiness browser tests and repo workflow guards passed locally with `47 passed` after rerunning Playwright outside the sandbox. `provider-proof-completion-status` still reports `accepted_proofs=["provider-backed-live-voice-proof"]`, `status=blocked_by_latest_failed_proof_record`, and latest failed proof `external-publication-proof`; strict operator readiness exits `2` on the same three publication inputs below.
- Fresh pushed-branch check on 2026-05-26: branch head `94f9e9f974150d61ba9a6766265135295bfac621` is pushed to origin. CI run `26433827993` completed `success`; Auto PR run `26433827994` completed `failure` and no open PR exists for the feature branch. `provider-proof-pr-create` with the current CI URL and head SHA returned `manual_required` / `github_token_unavailable`, so the current PR path is the compare URL or a token-backed helper retry.
- Fresh connector PR attempt on 2026-05-26: GitHub connector draft PR creation for the pushed green branch returned `403 Resource not accessible by integration`. Keep using the compare URL/manual PR path or retry `provider-proof-pr-create` only after `GITHUB_TOKEN`/`GH_TOKEN` or repository integration permissions are available.
- Fresh current branch check on 2026-05-28: `fix_20260528-live-postgres-gate` head `3dc61a30a67598e87e4a273cc695c241f8250eea` is pushed. CI run `26577750258` completed green for branch-push product checks (`Branch name policy`, `Python backend`, `Next.js frontend`, both Rust service jobs); `Live Postgres (PR/main/manual)` was skipped on the branch push and is now configured to run on pull requests before merge. Auto PR run `26577750829` failed at draft PR mutation with GitHub `403`, REST PR lookup returned no open PR, `provider-proof-pr-create` returned `manual_required` / `github_token_unavailable`, and connector PR creation returned `403 Resource not accessible by integration`. Current manual PR path: `https://github.com/DeconvFFT/Content-creator-optimizer/compare/main...fix_20260528-live-postgres-gate?expand=1`.

## Required GitHub Settings

In repository settings, configure GitHub Actions workflow permissions:

- Select `Read and write permissions`.
- Enable `Allow GitHub Actions to create and approve pull requests`.
- Keep `.github/workflows/auto-pr.yml` limited to the built-in `GITHUB_TOKEN`; do not add custom repository secrets for PR creation.
- Keep the Node 24-native action pins in both CI workflows: `actions/checkout@v6`, `actions/setup-python@v6`, `actions/setup-node@v6`, `actions/github-script@v8`, and `astral-sh/setup-uv@v8.1.0`.
- Keep `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` in both CI workflows as a compatibility guard before GitHub's June 2026 default switch.

Configure `main branch protection` or a ruleset:

- Require pull requests before merging.
- Require CODEOWNERS review from `.github/CODEOWNERS`.
- Require status checks to pass before merge.
- Require the branch to be up to date before merge if the repository policy needs it.
- Require conversation resolution if review comments are blocking.
- Enable auto-merge at the repository level after required checks and reviews are enforced.

The required status checks should cover:

- `Branch name policy`.
- `Python backend`, including `uv lock --check` and dependency sync from `uv.lock`.
- `Next.js frontend` build, lint, typecheck, and race tests.
- `Rust service (services/retrieval-ranker)`.
- `Rust service (services/voice-edge)`.
- `Live Postgres (PR/main/manual)`.

Do not make `Auto PR / Draft PR after green branch CI` a required merge check. That job is PR automation only; it may fail when repository settings deny draft PR mutation even when product CI is green.

## Proof Gate Boundary

The current realtime path is:

- OpenRouter model: `deepseek/deepseek-v4-flash`
- Transport/runtime: `LiveKit`
- Voice: `Kokoro`

`provider-backed-live-voice-proof` is accepted for the current UUID run. Do not reopen it unless new evidence contradicts the accepted record.

`external-publication-proof` is still blocked on operator-owned manual publication evidence:

- `LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID`
- `PUBLICATION_DURABLE_PLATFORM_ID_OR_URL`
- `PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID`

These values belong in ignored local operator input files and external durable records. Keep no secret values in commits, PR bodies, Actions logs, or vault notes.

## Merge Rules

- Merge only after CI is green on the latest branch head.
- Merge only after proof gate status is stated in the PR.
- If publication remains blocked, the PR must say that clearly and list the missing operator input names, not values.
- Do not commit provider proof output, local credential files, screenshots, PDFs, media, private audio, local databases, or command logs.
- Dependency lock changes use `uv.lock`; do not add local command-log artifacts.
