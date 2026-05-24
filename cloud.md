# Cloud And Repository Operations Handoff

This is the no-secret cloud setup checklist for Agent Studio in `DeconvFFT/Content-creator-optimizer`.

## Current Branch

- Branch: `feature/livekit-voice-proof-capture`
- Target: `main`
- PR body source: `provider-proof-pr-handoff`
- Token-aware helper: `provider-proof-pr-create`
- Local `gh` CLI is not installed in the current Codex environment.
- GitHub connector PR creation currently returns `403 Resource not accessible by integration`.
- Latest branch-head evidence must be regenerated before opening or updating a PR. Do not treat committed SHA or run IDs as current evidence; run `provider-proof-pr-handoff` with fresh `--ci-url` and `--head-sha` values from the latest branch-head CI. The current known blocker is still repository PR mutation: Auto PR can reach the no-secret handoff step but may emit `Auto PR skipped` when repository settings deny draft PR create/update, and local `provider-proof-pr-create` returns `manual_required` until `GITHUB_TOKEN` or `GH_TOKEN` is available.
- Fresh connector attempt after the latest green branch-head CI still returned `403 Resource not accessible by integration`; REST PR lookup returned no open feature-branch PR. Continue with manual PR creation or repository Actions/app permission changes.

## Required GitHub Settings

In repository settings, configure GitHub Actions workflow permissions:

- Select `Read and write permissions`.
- Enable `Allow GitHub Actions to create and approve pull requests`.
- Keep `.github/workflows/auto-pr.yml` limited to the built-in `GITHUB_TOKEN`; do not add custom repository secrets for PR creation.

Configure `main branch protection` or a ruleset:

- Require pull requests before merging.
- Require CODEOWNERS review from `.github/CODEOWNERS`.
- Require status checks to pass before merge.
- Require the branch to be up to date before merge if the repository policy needs it.
- Require conversation resolution if review comments are blocking.
- Enable auto-merge at the repository level after required checks and reviews are enforced.

The required status checks should cover:

- Branch policy / repo hygiene.
- Python backend checks, including `uv lock --check` and dependency sync from `uv.lock`.
- Next.js frontend build, lint, typecheck, and race tests.
- Rust service checks when `services/**` changes.

## Proof Gate Boundary

The current realtime path is:

- OpenRouter model: `deepseek/deepseek-v4-flash`
- Transport/runtime: `LiveKit`
- Voice: `Kokoro`

`provider-backed-live-voice-proof` is accepted for the current UUID run. Do not reopen it unless new evidence contradicts the accepted record.

`external-publication-proof` is still blocked on operator-owned LinkedIn/publication evidence:

- `LINKEDIN_ACCESS_TOKEN_FILE`
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
