---
name: agent-studio-ci-scaffold
description: "Maintain and extend Agent Studio CI. Use when adding GitHub Actions jobs, wiring Postgres/pgvector services, Playwright browser setup, frontend checks, or opt-in LIVE_POSTGRES gates."
---

# Agent Studio CI Scaffold

## Workflow

1. Treat `.github/workflows/ci.yml` as the source of truth for automated ship gates.
2. Keep job commands aligned with README verification and local bootstrap commands.
3. Backend job minimum:
   - `uv sync --extra dev`
   - `uv run playwright install --with-deps chromium`
   - `uv run pytest -q`
4. Frontend job minimum:
   - `npm ci` in `frontend/next-app`
   - `npm run build`, `npm run lint`, `npm run typecheck`
5. Live Postgres job is opt-in and infrastructure-heavy:
   - Use `pgvector/pgvector:pg16` service
   - Set `DATABASE_URL` and `LIVE_POSTGRES=1`
   - Run `uv run pytest tests/test_live_postgres.py -q -rs`
   - Do not fold live Postgres into the default PR gate until flake rate and runtime are acceptable.
6. When adding Python lint, prefer `ruff check src/` with the repo `[tool.ruff]` config before expanding rule sets.
7. Document any new skip gates, secret requirements, or host-only tests in README Verification.

## Quality Targets

- CI reproduces the default local no-secret regression path.
- Browser tests install Chromium explicitly; avoid relying on preinstalled GitHub runner browsers.
- Live infrastructure tests remain clearly separated from default PR signal.
- Workflow changes stay small, readable, and cache-friendly (`setup-uv`, npm cache).

## Outputs

- `ci_workflow_update`
- `job_command_matrix`
- `infrastructure_gate_notes`
- `follow_up_ci_tasks`
