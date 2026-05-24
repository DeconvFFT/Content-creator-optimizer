# Repository Workflow

This repo uses a PR-first workflow. Keep `main` as the protected integration branch and do all implementation work on short-lived branches.

## Branches

- Features: `feature/<short-name>`
- Bug fixes: `fix_<timestamp-or-uuid>`
- Keep branch names specific, for example `feature/livekit-voice-proof-capture` or `fix_20260523_voice-ledger-cli`.
- Do not work directly on `main` after the baseline commit exists.

## Parallel Agent Worktrees

Use worktrees for parallel Codex/Cursor agents once the baseline commit exists:

```bash
git switch main
git pull --ff-only
git worktree add .worktrees/<task-name> -b feature/<task-name>
git worktree add .worktrees/fix_<timestamp-or-uuid> -b fix_<timestamp-or-uuid>
```

Each agent owns one worktree and one branch. Give every agent a disjoint file ownership scope when possible. Agents must not revert or overwrite work from other agents; they should report changed files and verification commands before integration.

## Tests

Put new Python tests under `tests/`. Frontend tests live under `frontend/next-app/tests/` and are run through the Next app scripts.

Expected local checks before opening a PR:

```bash
uv lock --check
uv run ruff check src/ tests/
bash scripts/ci-python-stable-tests.sh
cd frontend/next-app && npm run build
cd frontend/next-app && npm run lint
cd frontend/next-app && npm run typecheck
cd frontend/next-app && npm run test:race
```

`scripts/ci-python-stable-tests.sh` is the required Python CI slice for the current OpenRouter/LiveKit proof branch. It includes the repo workflow guard that checks GitHub Actions Python dependency sync uses `uv sync --locked`, and CI now runs `uv lock --check` before Python dependency sync, so `pyproject.toml` and the committed `uv.lock` cannot drift silently. The full `uv run pytest -q` suite is still useful as a broader migration audit and is expected to pass locally in the current workspace. Local provider-proof output fixture tests are opt-in with `RUN_PROVIDER_PROOF_ARTIFACT_FIXTURE_TESTS=1`; they read ignored files under `social_media_optimiser/output/provider-proof/` and must not become required CI checks.

When touching Rust services, also run:

```bash
cd services/retrieval-ranker && cargo fmt --all -- --check && cargo test --locked
cd services/voice-edge && cargo fmt --all -- --check && cargo test --locked
```

## Secret And Artifact Policy

Do not commit:

- `.env`, `.env.*`, `.secrets/`, credentials, tokens, private keys, certificates, or local secret snapshots
- local databases, provider proof output, voice audio captures, browser traces, screenshots, images, PDFs, generated media, or bulky scratch artifacts
- virtualenvs, caches, local worktrees, build output, coverage output, or temporary research/course folders

Commit:

- source code, tests, lightweight Markdown/docs, CI config, `.env.example`, `uv.lock`, package lockfiles, Cargo lockfiles, `AGENTS.md`/`agents.md`, and `CLOUD.md`/`cloud.md` when present

Track `uv.lock` when Python dependencies change. Do not commit local command logs.

Secrets belong in local environment variables or ignored files under `.secrets/`. Documentation may name required environment variables but must never contain real values.

## PR And Auto-Merge

Open PRs into `main`. The PR checklist should show the local verification commands that were run, plus the current provider proof gate state. For the current Agent Studio branch, the PR must explicitly state the `provider-backed-live-voice-proof` status, the `external-publication-proof` status, and whether any operator-owned LinkedIn inputs remain blocked. Enable auto-merge only after required CI checks and review pass.

If GitHub integration permissions prevent creating the PR automatically, generate a no-secret manual PR body from the current proof gates:

```bash
uv run all-about-llms-admin provider-proof-pr-handoff \
  --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e \
  --operator-input-path social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env \
  --ci-url <latest-branch-head-ci-url> \
  --head-sha <current-branch-head-sha>
```

Fill the CI URL and head SHA placeholders from the current branch head before pasting the generated PR body. The generated handoff must keep `provider-backed-live-voice-proof`, `external-publication-proof`, `LINKEDIN_ACCESS_TOKEN_FILE`, the OpenRouter/LiveKit/Kokoro route, CI evidence, and the no secret values boundary visible in the manual PR description.

For the remaining publication gate, use `docs/external-publication-proof-runbook.md` as the committed no-secret operator handoff. The generated `operator-unblocker-checklist.md` under `social_media_optimiser/output/provider-proof/` remains the detailed ignored proof packet and must not be committed.

Repository settings still need to enforce:

- `main` branch protection or a GitHub ruleset
- required status checks: branch policy, Python backend, Next.js frontend, and Rust service jobs
- required review through `.github/CODEOWNERS`
- auto-merge enabled in repository settings
- conversation resolution and up-to-date branch requirements if desired

GitHub settings cannot be fully represented in repo files, so keep this document and the actual repository ruleset in sync.
