---
name: agent-studio-provider-proof-capture
description: "Operator workflow for capturing provider-backed proof without leaking secrets. Use when closing live voice, selected provider, web-search, reranker, or external publication blockers."
---

# Agent Studio Provider Proof Capture

## Workflow

1. Start with the no-secret plan for a durable run UUID:
   - `uv run all-about-llms-admin provider-proof-plan --run-id <run-id> --checked-at YYYY-MM-DD`
   - Or `PYTHONPATH=src python3 -m all_about_llms.cli provider-proof-plan ...`
2. Confirm credential presence only through readiness APIs/CLI snapshots. Never read, echo, or commit secret file contents.
3. Ensure local infrastructure is up when required:
   - Postgres: `docker compose up -d postgres`
   - LiveKit voice dev: `docker compose --profile voice up -d livekit`
   - Rust voice edge built when the plan requires it.
4. Record deterministic/local smoke first via provider-smoke ledger without live calls.
5. When credentials and infrastructure are ready, rerun with live execution:
   - `POST /api/runs/{run_id}/provider-smoke` with `execute_live_calls=true`, or
   - `uv run all-about-llms-admin build-provider-smoke-ledger --run-id <run-id> --live`
6. For voice proof, capture same-session evidence: selected realtime provider/OpenRouter response start or first text delta, Kokoro first-audio latency, end-to-end first-audio latency, captured microphone artifact hash/path when available, and barge-in/cancellation proof.
7. For publication proof, capture policy/disclosure evidence and external destination readiness without treating credential presence as publish proof.
8. Persist artifacts under the run timeline and update operator proof status docs; redact secrets from screenshots, logs, and reports.

## Quality Targets

- Every proof claim maps to a durable ledger event or artifact.
- Rehearsal sessions (`local_realtime_rehearsal`, deterministic fallbacks) are labeled non-provider-backed.
- Blocked/failed/unknown smoke statuses stay explicit.
- Publication readiness never conflates token presence with external publish completion.

## Outputs

- `provider_proof_plan`
- `provider_smoke_ledger`
- `voice_timing_evidence`
- `publication_boundary_report`
- `operator_capture_checklist`
