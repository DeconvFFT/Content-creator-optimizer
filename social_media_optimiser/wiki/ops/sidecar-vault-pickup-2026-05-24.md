---
type: sidecar-pickup
project: agent-studio
status: active
updated: 2026-05-24
scope: social-media-optimiser-and-system-design-vault
source_policy: source-attributed-synthesis
---

# Sidecar Vault Pickup - 2026-05-24

## Why This Note Exists

This is a compact handoff for future LLM workers that need project context without replaying both Obsidian vaults. It does not replace the MOC, HLD, LLD, Kanban, proof packets, or generated viewers. It records what this sidecar pass understood from `social_media_optimiser/` and `system_design_vault/` and points to the narrow source notes to reopen.

Primary companion artifact: `../../system_design_vault/07-agent-studio-knowledge-graph/Agent Studio Sidecar Pickup 2026-05-24.md`

Diagram companion: `../../system_design_vault/07-agent-studio-knowledge-graph/Agent Studio Sidecar Pickup 2026-05-24.excalidraw.md`

## Project In One Screen

Agent Studio is a local-first realtime multi-agent content studio. The creator-facing product is the Next.js app with voice/text input, drafts, source/claim evidence, artifact review, feedback, production packaging, and run activity. FastAPI is the durable control plane. Postgres + pgvector is the product state plane. The two vaults are planning, design, tracking, and memory surfaces, not product UI.

Current realtime direction: OpenRouter `deepseek/deepseek-v4-flash` for live dialogue reasoning, LiveKit for room/media/data-channel transport, Kokoro for spoken output, and Rust voice-edge for VAD/barge-in/cancellation proof. Gemma, Gamma, Hugging Face, MLX, and `GEMMA4_MULTIMODAL_ENDPOINT_URL` are legacy or non-default lanes unless a future route note explicitly promotes them.

## What Is Done

- Obsidian-first planning system exists in this vault: MOC, HLD, LLD, roster, sprint, decision log, feedback inbox, proof-readiness surfaces, raw/wiki/output memory conventions, and generated companion HTML/JSON.
- Product surface exists as a creator studio rather than a project tracker: Next.js product app, voice panel, source/draft/artifact/activity views, feedback controls, production package/media/publish-readiness actions, and run restore.
- Backend control plane exists: FastAPI routes, durable Postgres + pgvector records, event streams, context packets, A2A-style worker cycles, source/claim/artifact/feedback/memory records, proof-workspace commands, and generated viewers.
- Retrieval and claim gates are first-class: retrieval-quality ledgers, source ledgers, accepted evidence, claim verification, reranking boundary, feedback/revision loops, and publish-readiness gates.
- Provider-backed live voice is accepted for the current OpenRouter + LiveKit + Kokoro direction. The UUID proof workspace shows configured OpenRouter/LiveKit file/URL inputs, valid preflight validation, live OpenRouter/Kokoro smoke, 8/8 realtime timing stages, and accepted proof-record validation for run `190ae2f9-a74b-4a23-b39c-aaf2d636bd8e`.
- Secret-safe proof packet infrastructure exists: current blocker matrix, current proof status, operator checklist, proof-plan packets, workspace validation, record templates, validator, completion-status checker, closure-review path, and no-state-change guardrails.
- CI/PR mechanics exist outside the vaults: PR-first branch workflow, branch-name CI check, backend stable Python slice, frontend build/lint/typecheck/race tests, Rust service checks, and optional live Postgres job.

## What Remains

- Accepted external publication proof is still blocked. Remaining inputs are policy/account acknowledgement, durable external destination URL or platform id, and rollback/postcondition evidence.
- Completion status remains `blocked_by_latest_failed_proof_record` because `external-publication-proof` is still the latest failed required proof. Closure review and blocker-state update are downstream and must not run as completion claims until the external publication proof is accepted too.
- Retrieval Intelligence and Knowledge Graph Curation are partially implemented and still need broader curation/eval, graph coverage checks, and Obsidian review output for retrieval-quality decisions.
- The Rust voice path still needs benchmarked concurrent-session tuning and eventual LiveKit-side Rust media bridge work; the current JSONL/HTTP bridge is useful but not the final media service.
- Repository settings still need out-of-repo enforcement for branch protection, required checks, required review, and auto-merge rules.

## Proof Gate Rules

- Do not claim the objective complete from credentials, preflight, local rehearsal, provider smoke alone, generated viewers, or static proof packets.
- Accepted live voice proof already exists for run `190ae2f9-a74b-4a23-b39c-aaf2d636bd8e`; do not reopen it unless newer evidence supersedes the accepted record.
- Accepted external publication proof requires a real external platform destination, policy acknowledgement, credential/path proof, rollback or postcondition evidence, validation, and no-secret checks.
- `provider-proof-completion-status` is status-only. Even when it reports accepted proofs, closure review is a separate reviewer step before blocker-state update.
- No proof command or note may print token values, API keys, raw provider responses, private audio, or secret file contents.

## CI And PR Workflow Pickup

Source-truth workflow files are outside this vault and were read-only during this sidecar pass:

- `docs/repo-workflow.md`
- `.github/pull_request_template.md`
- `.github/workflows/ci.yml`

Current workflow shape:

- Use short-lived branches: `feature/<short-name>` or `fix_<timestamp-or-uuid>`.
- Keep parallel agents in disjoint worktrees/file scopes when possible.
- Local pre-PR checks: `uv run ruff check src/ tests/`, `bash scripts/ci-python-stable-tests.sh`, frontend build/lint/typecheck/test:race, and Rust format/test when touching Rust services.
- CI jobs: branch name policy, Python backend, Next.js frontend, Rust services, and optional/manual or main-only live Postgres.
- Python CI dependency sync uses `uv sync --locked`, guarded by `tests/test_repo_workflow_ci.py`, so the workflow installs from committed `uv.lock`; local command logs remain ignored.
- The PR checklist requires verification commands, no secrets/artifacts, and green CI plus review before auto-merge.

## Source Attribution

| Source | Vault or area | Used for |
|---|---|---|
| `Agent Studio MOC.md` | `social_media_optimiser` | Planning source of truth, non-negotiables, current focus, proof packet refs |
| `wiki/ops/active-codex-context.md` | `social_media_optimiser` | Current OpenRouter/LiveKit/Kokoro route, proof status, operator inputs |
| `01-work-tracking/Current Sprint.md` | `social_media_optimiser` | Latest implementation and validation evidence |
| `01-work-tracking/Agent Studio Objective Completion Audit.md` | `social_media_optimiser` | Done/left split, objective status, blocked proof records |
| `00-system-design/HLD - Agent Studio.md` | `social_media_optimiser` | Product boundary and high-level architecture |
| `00-system-design/LLD - Agent Studio.md` | `social_media_optimiser` | Runtime modules, voice contracts, timing evidence requirements |
| `01-work-tracking/Decision Log.md` | `social_media_optimiser` | Durable design decisions and superseded voice assumptions |
| `MOC.md` | `system_design_vault` | Cross-vault source map and system-design focus |
| `07-agent-studio-knowledge-graph/Agent Studio Project Knowledge Graph.md` | `system_design_vault` | Existing compact KG and proof-gate summary |
| `04-agent-studio-implications/HLD - Agent Studio System Design.md` | `system_design_vault` | Production-system architecture and release gates |
| `04-agent-studio-implications/LLD - Agent Studio System Design.md` | `system_design_vault` | Runtime contracts and realtime voice timing gate |
| `04-agent-studio-implications/agent-studio-objective-completion-audit.md` | `system_design_vault` | System-design mirror of implementation reality |
| `05-ingestion-runs/status-summary.md` | `system_design_vault` | Source-ingestion scope, source hygiene, active blockers |

## Future Worker Read Order

1. Read this note.
2. Read `system_design_vault/07-agent-studio-knowledge-graph/Agent Studio Sidecar Pickup 2026-05-24.md`.
3. For proof work, read `output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-proof-status.md` and `completion-status.json`, then focus on external publication unless the accepted live-voice record has been superseded.
4. For architecture work, read the system-design HLD/LLD and then only the relevant source-pattern note.
5. For product work, preserve the boundary: Obsidian trackers and planning boards stay out of the creator app.
