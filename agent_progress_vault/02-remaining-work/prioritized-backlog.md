---
type: backlog
updated: 2026-05-28
sources:
  - synthesis-59e319d8
  - vault-audit-c74873d8
  - codex-live-voice-proof-accepted
---

# Prioritized Backlog

Synced from final synthesis Phase 0–3 plan + vault audit top 5.

## Phase 0 — Objective blockers (operator, Effort L)

Requires operator-owned durable publication evidence and action-time approval. **Cannot be closed by agents alone.**

| # | Item | Commands / refs |
|---|------|-----------------|
| 1 | Capture accepted live voice proof | **Done 2026-05-24** — `provider-backed-live-voice-proof.accepted-record.json` is recorded for OpenRouter `deepseek/deepseek-v4-flash` + LiveKit + Kokoro with timing ledger `7e932381-4bf4-4206-a490-58d6a4ca7880` |
| 2 | Configure publication inputs | Manual-publication policy acknowledgement artifact, durable destination URL/platform id, and rollback/postcondition artifact; no LinkedIn token file is required for the current path |
| 3 | Run post-unblock external publication proof capture | UUID `190ae2f9-a74b-4a23-b39c-aaf2d636bd8e`; use external-publication `proof_capture_commands_after_unblock` from matrix only after explicit action-time approval |
| 4 | Record accepted external publication proof | `validate-provider-proof-record` -> `record-provider-proof-record` for `external-publication-proof` |
| 5 | Closure review | `provider-proof-closure-review-template`; update blocker state when `all_required_proofs_accepted: true` |

```bash
uv run all-about-llms-admin provider-proof-completion-status \
  --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e
```

## Phase 1 — Ship blockers (engineering, Effort M–L)

No user secrets required for items 1–5; item 6 requires Phase 0 proofs.

| # | Item | Effort | Status |
|---|------|--------|--------|
| 1 | Install Playwright browsers | **S** | Branch-head remote CI passed the Python backend Playwright install step at last live check |
| 2 | CI pipeline | **M** | **Remote branch-push product checks green on `fix_20260528-live-postgres-gate` at latest live check** — last live check passed branch policy, frontend, Python backend, and both Rust services. `Live Postgres (PR/main/manual)` is configured for PR/main/manual and must pass on the PR before approval or merge. PR creation/open PR remains blocked or absent: Auto PR failed with GitHub `403`, GitHub connector returned `403`, local `gh` is unavailable, REST PR lookup returned no open PR, and branch-protection/auto-merge setup still needs GitHub-side configuration. Use `provider-proof-pr-handoff` to generate the no-secret manual PR body until connector permissions are upgraded; token-backed `provider-proof-pr-create` updates an existing open branch PR before creating a new draft. `cloud.md` captures the no-secret GitHub Actions permission, branch-protection, required-check, and auto-merge checklist |
| 3 | Four ship skills | **M** | **Done** — local-bootstrap, ship-gate, provider-proof-capture, and ci-scaffold skills exist under `skills/agent-studio-*` |
| 4 | Ruff baseline | **S** | **Done locally** — `[tool.ruff]` exists in `pyproject.toml`; fresh `uv run ruff check src/ tests/` returned `All checks passed!` |
| 5 | Initial git commit / branch push | **S** | **Done** — `main` is seeded and current branch `fix_20260528-live-postgres-gate` is pushed; PR/merge/release tag remain pending |
| 6 | Production auth + disable secret-write in prod | **L** | **Backend guard done 2026-05-24** — non-local mutating API requests require a configured `ADMIN_API_TOKEN` bearer token, missing token fails closed, and local secret/config write endpoints still reject production after auth. Broader identity/RBAC remains out of scope for this slice |
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
| 5 | Keep sprint `## Next` fresh | [[../social_media_optimiser/01-work-tracking/Current Sprint#Next]] now points at publication proof, closure review, branch-protection/auto-merge, and demo feedback; refresh again after any proof-state change |
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

1. **External publication proof** — LinkedIn credential + channel policy; durable destination and rollback/postcondition evidence
2. **Execute external-publication UUID proof capture chain** — run `190ae2f9-a74b-4a23-b39c-aaf2d636bd8e` post-unblock commands after explicit approval
3. **Closure review** — only after both required proofs are accepted and completion status reports `all_required_proofs_accepted: true`
4. **Non-credential product hardening** — Kanban next bounded slice
5. **Finish branch integration** — manual PR with `provider-proof-pr-handoff` or upgraded GitHub integration permission, branch-protection/auto-merge proof, merge/release decision

## Do not

- Mark objective complete without accepted proof records
- Reopen Gamma/Gemma/Hugging Face as the active realtime default unless the user explicitly reactivates legacy native-audio research
- Implement Qdrant/Neo4j without benchmark justification
