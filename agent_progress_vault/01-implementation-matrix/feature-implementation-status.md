---
type: implementation-matrix
updated: 2026-05-23
source: vault-audit-c74873d8 + synthesis-59e319d8
---

# Feature Implementation Status

Vault claim vs code evidence. Percentages are honest estimates, not marketing.

| Feature | Vault status | Code evidence | Est. % | Gap |
|---------|--------------|---------------|--------|-----|
| Obsidian planning & tracking | Done / active SoT | 113+ project vault files; 499 system-design files; Kanban + sprint synced | **95** | Keep vaults current after each slice |
| HLD/LLD & design canon | Draft HLD/LLD + production canon | [[../social_media_optimiser/00-system-design/HLD - Agent Studio]], [[../system_design_vault/04-agent-studio-implications/HLD - Agent Studio System Design]] | **85** | HLD frontmatter `updated: 2026-05-17` lags content |
| Backend orchestration & API | Long-running agents, A2A, workflows proven locally | 88 modules under `src/all_about_llms/`; `app.py` (~117 routes); `cli.py` | **88** | External publication proof remains unproven |
| Postgres + pgvector storage | No SQLite; durable state from v1 | `infra/postgres/001_foundation.sql`, `storage/postgres.py`, `docker-compose.yml` | **90** | Live Postgres CI job not wired |
| Retrieval & project memory | pgvector retrieval, reranking, ledgers done | `project_memory_retrieval.py`, `retrieval_quality.py`, `providers/rerank.py` | **75** | External vector/graph DBs design-only |
| Knowledge graph (Qdrant/Neo4j) | Canon-ready release gates in system-design vault | **No** `qdrant`/`neo4j` in `src/` | **25** | Postgres-first graph only; HLD rule: benchmark before adding |
| A2A-style collaboration | Scoped proven (local, public projection) | `a2a_projection.py`, `a2a_discovery.py`, `test_api_contracts.py` | **80** | Not full external A2A server |
| Frontend creator app | Creator studio with voice, sources, activity | 87 TS/TSX files in `frontend/next-app/`; build/lint/typecheck pass | **80** | External publication proof still blocked |
| Voice stack (local/rehearsal) | LiveKit dev, Kokoro, Rust edge evidenced | `voice_agent/`, `services/voice-edge/`, timing ledgers | **78** | Direct LiveKit-side Rust media bridge future work |
| **Provider-backed live voice** | **Accepted** | OpenRouter/LiveKit/Kokoro preflight, smoke, timing, and accepted proof record captured for run `190ae2f9-a74b-4a23-b39c-aaf2d636bd8e` | **90 infra / accepted proof** | Future work is concurrency/load hardening, not proof unblock |
| **External publication proof** | **Blocked** — objective incomplete | Publish-readiness + local fixture; failed record | **15 infra / 0 proof** | LinkedIn creds + policy/destination artifacts |
| Provider-proof CLI & handoff | Extensive machinery done | `test_provider_proof_plan_cli.py` (223 pass); UUID workspace artifacts | **95** | Operator must run capture chain |
| Agent skills (8 existing) | Done | `skills/agent-studio-*/SKILL.md` | **90** | 4 recommended ship skills **not yet created** (c75e2d04 stalled) |
| Test coverage | Foundation + provider-proof + browser | 31 test modules; 808 collected; 766 pass without Playwright browsers | **Strong locally** | 32 browser tests need `playwright install`; no CI |
| CI/CD | Scaffolded on feature branch | `.github/workflows/ci.yml` and `scripts/ci-python-stable-tests.sh` exist; Python sync uses `uv sync --locked`; `tests/test_repo_workflow_ci.py` guards lockfile use; `uv.lock` tracked; local command logs ignored | **65** | Needs PR/remote branch protection and CI run confirmation |
| Python lint (ruff) | Scaffolded | `[tool.ruff]` in `pyproject.toml`; local ruff checks pass on touched proof/CI files | **60** | Needs full-repo ruff CI confirmation |
| Production auth/security | Localhost-only acceptable | No auth, no CORS, secret-write routes | **15** | Required before any non-localhost deploy |
| Git / release discipline | Not started | Zero commits on `main` | **0** | Initial commit + tagged releases pending |
| System-design ingestion | Nightly automation; ingestion lane clear | `system_design_vault/05-ingestion-runs/`; `urgent-blockers.json` status=clear | **70** | CS336 L17, Practical MLOps deepening |

## Overall objective

Substantially planned and implemented locally. **Not complete** until external publication has an accepted proof record, completion status is rechecked, and closure/release/CI follow-through is complete. Provider-backed live voice is already accepted for the OpenRouter + LiveKit + Kokoro route.

## Related notes

- [[../02-remaining-work/prioritized-backlog]]
- [[../04-cross-vault-links/vault-sync-notes]]
- [[../social_media_optimiser/01-work-tracking/Agent Studio Objective Completion Audit]]
