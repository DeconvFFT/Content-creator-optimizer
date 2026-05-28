---
type: implementation-matrix
updated: 2026-05-28
source: vault-audit-c74873d8 + synthesis-59e319d8 + codex-ci-vault-refresh
---

# Feature Implementation Status

Vault claim vs code evidence. Percentages are honest estimates, not marketing.

| Feature | Vault status | Code evidence | Est. % | Gap |
|---------|--------------|---------------|--------|-----|
| Obsidian planning & tracking | Done / active SoT | 113+ project vault files; 499 system-design files; Kanban + sprint synced | **95** | Keep vaults current after each slice |
| HLD/LLD & design canon | Draft HLD/LLD + production canon | [[../social_media_optimiser/00-system-design/HLD - Agent Studio]], [[../system_design_vault/04-agent-studio-implications/HLD - Agent Studio System Design]] | **85** | HLD frontmatter `updated: 2026-05-17` lags content |
| Backend orchestration & API | Long-running agents, A2A, workflows proven locally | 88 modules under `src/all_about_llms/`; `app.py` (~117 routes); `cli.py` | **88** | External publication proof remains unproven |
| Postgres + pgvector storage | No SQLite; durable state from v1 | `infra/postgres/001_foundation.sql`, `storage/postgres.py`, `docker-compose.yml` | **90** | Live Postgres is wired as a PR/main/manual merge gate; wait for PR check before merge |
| Retrieval & project memory | pgvector retrieval, reranking, ledgers done | `project_memory_retrieval.py`, `retrieval_quality.py`, `providers/rerank.py` | **75** | External vector/graph DBs design-only |
| Knowledge graph (Qdrant/Neo4j) | Canon-ready release gates in system-design vault | **No** `qdrant`/`neo4j` in `src/` | **25** | Postgres-first graph only; HLD rule: benchmark before adding |
| A2A-style collaboration | Scoped proven (local, public projection) | `a2a_projection.py`, `a2a_discovery.py`, `test_api_contracts.py` | **80** | Not full external A2A server |
| Frontend creator app | Creator studio with voice, sources, activity | 87 TS/TSX files in `frontend/next-app/`; build/lint/typecheck pass | **80** | External publication proof still blocked |
| Voice stack (local/rehearsal) | LiveKit dev, Kokoro, Rust edge evidenced | `voice_agent/`, `services/voice-edge/`, timing ledgers | **78** | Direct LiveKit-side Rust media bridge future work |
| **Provider-backed live voice** | **Accepted** | OpenRouter/LiveKit/Kokoro preflight, smoke, timing, and accepted proof record captured for run `190ae2f9-a74b-4a23-b39c-aaf2d636bd8e` | **90 infra / accepted proof** | Future work is concurrency/load hardening, not proof unblock |
| **External publication proof** | **Blocked** — objective incomplete | Publish-readiness + local fixture; failed record | **15 infra / 0 proof** | Manual-publication policy acknowledgement, durable destination, and rollback/postcondition artifacts |
| Provider-proof CLI & handoff | Extensive machinery done | `provider-proof-pr-handoff` now emits a no-secret manual PR body from completion and operator-input gates; UUID workspace artifacts remain ignored | **96** | Operator must run external publication capture chain |
| Agent skills (13 existing) | Done | `skills/agent-studio-local-bootstrap`, `skills/agent-studio-ship-gate`, `skills/agent-studio-provider-proof-capture`, `skills/agent-studio-ci-scaffold`, plus existing `agent-studio-*` skills | **95** | Keep skill docs current with proof/CI contract changes |
| Test coverage | Foundation + provider-proof + browser | Fresh focused checks: repo workflow CI `14 passed`, OpenRouter voice boundary browser `3 passed`, adjacent proof-surface browser `3 passed, 9 skipped`, foundation `23 passed`; stable Python CI script passed with `240 passed, 30 skipped`; branch-head remote CI was green for current pushed head at last live check | **Strong locally + remote green** | Keep coverage current with external publication proof work |
| CI/CD | Scaffolded and pushed on current branch | `.github/workflows/ci.yml` and `scripts/ci-python-stable-tests.sh` exist; Python sync uses `uv sync --locked`; CI installs Playwright Chromium; `tests/test_repo_workflow_ci.py` guards lockfile, PR proof-gate handoff, manual `provider-proof-pr-handoff` docs, and LiveKit SDK dev-extra use; `uv.lock` tracked; local command logs ignored | **88** | Branch-push product checks were green for `3dc61a30a67598e87e4a273cc695c241f8250eea`; `Live Postgres (PR/main/manual)` is skipped on branch push and must pass on PR before merge; REST PR lookup returned no open PR and connector PR creation still returns GitHub `403`; branch-protection/auto-merge still needs GitHub-side setup |
| Python lint (ruff) | Baseline verified locally and remotely | `[tool.ruff]` in `pyproject.toml`; fresh `uv run ruff check tests/test_repo_workflow_ci.py` returned `All checks passed!`; branch-head remote CI Ruff step was green at last live check | **85** | Keep as required CI gate |
| Production auth/security | Localhost-only acceptable | No auth, no CORS, secret-write routes | **15** | Required before any non-localhost deploy |
| Git / release discipline | Current fix branch pushed | `main` includes PR #16; `fix_20260528-live-postgres-gate` is pushed at `3dc61a30a67598e87e4a273cc695c241f8250eea`, branch-push product checks were green at last live check, and `provider-proof-pr-handoff` is available for manual PR creation | **62** | Manual PR/merge, PR live Postgres check, branch protection, auto-merge setup, and tagged release still pending because connector PR creation is permission-blocked |
| System-design ingestion | Nightly automation; ingestion lane clear | `system_design_vault/05-ingestion-runs/`; `urgent-blockers.json` status=clear | **70** | CS336 L17, Practical MLOps deepening |

## Overall objective

Substantially planned and implemented locally. **Not complete** until external publication has an accepted proof record, completion status is rechecked, and closure/release/CI follow-through is complete. Provider-backed live voice is already accepted for the OpenRouter + LiveKit + Kokoro route.

## Related notes

- [[../02-remaining-work/prioritized-backlog]]
- [[../04-cross-vault-links/vault-sync-notes]]
- [[../social_media_optimiser/01-work-tracking/Agent Studio Objective Completion Audit]]
