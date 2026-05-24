---
type: backlog
updated: 2026-05-23
sources:
  - synthesis-59e319d8
  - vault-audit-c74873d8
---

# Prioritized Backlog

Synced from final synthesis Phase 0–3 plan + vault audit top 5.

## Phase 0 — Objective blockers (operator, Effort L)

Requires user secrets and operator action. **Cannot be closed by agents alone.**

| # | Item | Commands / refs |
|---|------|-----------------|
| 1 | Capture accepted live voice proof | OpenRouter `deepseek/deepseek-v4-flash`, LiveKit, and Kokoro inputs are configured for the current path per [[../social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-blocker-matrix.json\|current-blocker-matrix.json]]; remaining work is same-run runtime/timing/participant proof capture and accepted record validation |
| 2 | Configure publication inputs | LinkedIn token file, policy acknowledgement, durable destination, rollback/postcondition artifacts |
| 3 | Run post-unblock proof capture | UUID `190ae2f9-a74b-4a23-b39c-aaf2d636bd8e`; `proof_capture_commands_after_unblock` from matrix |
| 4 | Record accepted proof records | `validate-provider-proof-record` → `record-provider-proof-record` for both proofs |
| 5 | Closure review | `provider-proof-closure-review-template`; update blocker state when `all_required_proofs_accepted: true` |

```bash
uv run all-about-llms-admin provider-proof-completion-status \
  --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e
```

## Phase 1 — Ship blockers (engineering, Effort M–L)

No user secrets required for items 1–5; item 6 requires Phase 0 proofs.

| # | Item | Effort | Status |
|---|------|--------|--------|
| 1 | Install Playwright browsers | **S** | Pending — `uv run playwright install` |
| 2 | CI pipeline | **M** | **Pending** — c75e2d04 stalled; create `.github/workflows/ci.yml` |
| 3 | Four ship skills | **M** | **Pending** — local-bootstrap, ship-gate, provider-proof-capture, ci-scaffold |
| 4 | Ruff baseline | **S** | **Pending** — add to `pyproject.toml`, run on `src/` |
| 5 | Initial git commit | **S** | Pending user approval |
| 6 | Production auth + disable secret-write in prod | **L** | Not started |
| 7 | Closure review (after proofs) | **M** | Blocked on Phase 0 |

**CI scaffold spec** (from c75e2d04 handoff):

- Trigger: push/PR to `main`
- Service: `postgres:16` with pgvector
- Steps: `uv sync`, `playwright install --with-deps`, `pytest`, frontend `npm ci/build/lint/typecheck`
- Optional separate job: `LIVE_POSTGRES=1` pytest

## Phase 2 — Platform depth (Effort M)

| # | Item | Notes |
|---|------|-------|
| 1 | CORS allowlist | `http://127.0.0.1:3000` only |
| 2 | Rate limiting | slowapi on LLM/expensive routes |
| 3 | Live Postgres in CI | `LIVE_POSTGRES=1 uv run pytest tests/test_live_postgres.py` |
| 4 | Non-credential product hardening | Per [[../social_media_optimiser/01-work-tracking/Agent Studio Kanban]] — next bounded slice (browser single-flight, source-refresh boundaries) |
| 5 | Refresh stale sprint `## Next` | [[../social_media_optimiser/01-work-tracking/Current Sprint#Next]] contradicts UUID workspace state |
| 6 | Direct LiveKit Rust media bridge | Sprint backlog item |
| 7 | Repo cleanup | `.tmp_paper_work/`, `cs336_*_tmp/`, `tcf_canada_training/` |

## Phase 3 — Ingestion & research (parallel, Effort S–M)

| # | Item | Source |
|---|------|--------|
| 1 | Practical MLOps deepening | [[../system_design_vault/05-ingestion-runs/status-summary]] |
| 2 | Stanford CS336 Lecture 17 when public | [[../system_design_vault/05-ingestion-runs/next-ingestion-queue]] |
| 3 | Keep vault-sync heartbeat | [[../social_media_optimiser/wiki/ops/active-codex-context]] |
| 4 | Qdrant/Neo4j evaluation | Only after Postgres pgvector benchmarks (HLD rule) |

## Top 5 (vault perspective)

1. **Provider-backed live voice proof** — same-run OpenRouter DeepSeek + LiveKit + Kokoro dialogue, participant evidence, smoke, runtime health, and complete timing ledgers
2. **External publication proof** — LinkedIn credential + channel policy; durable destination evidence
3. **Execute UUID proof capture chain** — run `190ae2f9-a74b-4a23-b39c-aaf2d636bd8e` post-unblock commands
4. **Non-credential product hardening** — Kanban next bounded slice
5. **Complete c75e2d04 deliverables** — CI, skills, ruff, Playwright install (still on disk as gaps)

## Do not

- Mark objective complete without accepted proof records
- Reopen local LiveKit/Kokoro as substitute for Gemma audio proof
- Implement Qdrant/Neo4j without benchmark justification
