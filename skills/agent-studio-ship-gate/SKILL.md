---
name: agent-studio-ship-gate
description: "Pre-ship GO/NO-GO checklist for Agent Studio. Use before claiming production readiness, opening a release PR, or closing a ship-readiness sprint."
---

# Agent Studio Ship Gate

## Workflow

1. Run automated gates locally or in CI:
   - `uv run pytest -q`
   - `cd frontend/next-app && npm run build && npm run lint && npm run typecheck`
   - Optional host-context durable proof: `LIVE_POSTGRES=1 uv run pytest -q -rs`
2. Confirm CI scaffold exists and matches local commands (`.github/workflows/ci.yml`).
3. Review provider readiness at `GET /api/provider-readiness` without assuming live proof.
4. Build or inspect ledgers for the target run: runtime health, provider smoke, model routing, provider operations, feedback resolution, foundation audit, publish readiness.
5. Classify blockers:
   - **Automated**: failing tests, lint/type errors, missing migrations, broken build.
   - **Credential**: missing HF/LiveKit/search/publish tokens.
   - **Operator proof**: live voice timing, external publication capture, same-session smoke evidence.
   - **Architecture**: SQLite fallback, missing durable events, boundary violations.
6. Return a single ship decision with explicit evidence links and owner-routed next actions.

## GO Criteria

- Default pytest and frontend checks pass.
- No unresolved high-severity security findings without documented acceptance.
- Durable store path is Postgres/pgvector when persistence is required.
- Provider boundaries remain separated: realtime audio, Gemma/HF expert layer, web search, imagegen.
- Known proof gaps are documented as operator tasks, not hidden skips.

## NO-GO Criteria

- Any default regression failure.
- Claiming provider-backed or publish-ready status from rehearsal-only evidence.
- Open foundation-audit or guardrail blockers without remediation owners.
- Missing CI for the commands used to justify readiness.

## Outputs

- `ship_decision` (`go`, `go_with_operator_proof_pending`, `no_go`)
- `blocking_issues`
- `automated_gate_results`
- `operator_proof_gaps`
- `recommended_next_actions`
