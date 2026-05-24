---
name: agent-studio-local-bootstrap
description: "First-time local setup for Agent Studio. Use when onboarding a developer machine, restoring a fresh clone, starting Postgres/pgvector, syncing Python/Node deps, installing Playwright, or verifying the default no-secret regression path."
---

# Agent Studio Local Bootstrap

## Workflow

1. Confirm prerequisites: Python 3.12+, `uv`, Node 20+, and Docker Desktop if live Postgres or LiveKit voice dev is needed.
2. Copy `.env.example` to `.env`. Do not commit secrets. Prefer ignored secret files (`HF_TOKEN_FILE`, `TAVILY_API_KEY_FILE`, etc.) over inline env values.
3. Start durable storage when needed: `docker compose up -d postgres`. Wait for `pg_isready` before running the app or live Postgres tests.
4. Sync backend deps: `uv sync --extra dev`.
5. Install browser test deps: `uv run playwright install --with-deps chromium`.
6. Sync frontend deps: `cd frontend/next-app && npm ci`.
7. Run the default no-secret verification path:
   - `uv run pytest -q`
   - `cd frontend/next-app && npm run build && npm run lint && npm run typecheck`
8. Optional live Postgres proof (host context with Docker Postgres reachable): `LIVE_POSTGRES=1 uv run pytest tests/test_live_postgres.py -q -rs`.
9. Optional voice stack: `docker compose --profile voice up -d livekit`, build `services/voice-edge`, configure Gemma/Kokoro/LiveKit env vars, then run provider-proof planning without live calls first.

## Quality Targets

- Default regression passes without provider credentials or live network calls.
- Playwright browser tests run after browser install; missing browsers should not be mistaken for product failures.
- Postgres/pgvector is the only durable store path; do not add SQLite or local JSON substitutes.
- Frontend and backend both build cleanly before attempting provider-backed smoke.

## Outputs

- `local_bootstrap_checklist`
- `verification_command_log`
- `infrastructure_gap_report`
- `next_operator_action`
