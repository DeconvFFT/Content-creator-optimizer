---
type: cross-vault-links
updated: 2026-05-24
---

# Vault Sync Notes

## Source of truth by topic

| Topic | Authoritative vault / artifact | Notes |
|-------|-------------------------------|-------|
| Sprint, Kanban, proof status | [[../social_media_optimiser/01-work-tracking/Current Sprint]] | Planning SoT; product code must not render Kanban |
| Kanban board state | [[../social_media_optimiser/01-work-tracking/Agent Studio Kanban]] | Updated 2026-05-21 |
| Objective completion audit | [[../social_media_optimiser/01-work-tracking/Agent Studio Objective Completion Audit]] | Does not mark objective complete |
| Architecture implications mirror | [[../system_design_vault/04-agent-studio-implications/agent-studio-objective-completion-audit]] | Synced with project audit on blockers |
| Codex compact handoff | [[../social_media_optimiser/wiki/ops/active-codex-context]] | Start here for project-memory-dependent work |
| HLD / LLD | [[../social_media_optimiser/00-system-design/HLD - Agent Studio]] | Frontmatter may lag sprint patches |
| Ingestion blockers (research lane) | [[../system_design_vault/05-ingestion-runs/urgent-blockers.json]] | `status: clear` — separate from product proof blockers |
| Ingestion status | [[../system_design_vault/05-ingestion-runs/status-summary]] | |
| **Agent session progress** | **This vault** (`agent_progress_vault/`) | Agent-owned; not planning SoT |
| Project MOC hub | [[../social_media_optimiser/Agent Studio MOC]] | |
| System-design MOC hub | [[../system_design_vault/MOC]] | |

## UUID proof workspace

Run ID: `190ae2f9-a74b-4a23-b39c-aaf2d636bd8e`

| Artifact | Path |
|----------|------|
| Current proof status | `../social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-proof-status.md` |
| Blocker matrix | `../social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-blocker-matrix.json` |
| Completion status | `../social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/completion-status.json` |
| Operator checklist | `../social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-unblocker-checklist.md` |
| Proof plan | `../social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/proof-plan.json` |

**Workspace state (2026-05-24):**

- `valid_workspace`; latest runtime-health ledger reports 10/10 checks ready locally
- Local LiveKit transport, Kokoro, Rust voice edge, context pruning evidenced
- OpenRouter text-turn live dialogue uses distinct **`openrouter-live-dialogue-reasoning`** readiness; it is not native Gemma audio proof
- Provider-backed live voice proof is accepted for this run using OpenRouter `deepseek/deepseek-v4-flash`, LiveKit, Kokoro, provider-smoke ledger `94857bb9-c5eb-4174-8bc5-6687bd8befbe`, and realtime timing ledger `7e932381-4bf4-4206-a490-58d6a4ca7880`
- Latest live provider smoke passes with ledger artifact `9b371737-1344-4cfa-be2e-fcfc9cc30700`, selected realtime session `89f7b584-6905-4e74-9210-08c28ba254e4`, first text delta `489.124 ms`, Kokoro first audio chunk `5668.734 ms`, and first-audio latency `6157.88 ms`
- Legacy/native **`gemma-audio-reasoning`** is optional/superseded for the current default path; accepted live proof capture/recheck must verify LiveKit transport, the LiveKit agent participant, backend event sink, OpenRouter `deepseek/deepseek-v4-flash` live-dialogue reasoning, Kokoro TTS, and Rust voice edge where applicable
- **Publication blocked** — LinkedIn credential, policy acknowledgement, durable destination, and rollback/postcondition artifacts
- External publication proof: `latest_record_failed` / `valid_failed_record`; live voice is `accepted_proof_record_available`
- Completion: `blocked_by_latest_failed_proof_record`

**Do not confuse with:** `RUN-2026-05-20-NEXT` — intentionally blocked (`run_id_not_product_uuid`); operators must use UUID bootstrap.

## HTML review surfaces

| Surface | Path |
|---------|------|
| Proof readiness | `../social_media_optimiser/01-work-tracking/agent-studio-proof-readiness.html` |
| A2A map | `../social_media_optimiser/00-system-design/agent-studio-a2a-map.html` |
| Legacy-named Gemma voice boundary | `../social_media_optimiser/02-research/gemma-voice-boundary-map.html` |
| Publication boundary | `../social_media_optimiser/03-review-packets/agent-studio-publication-boundary-map.html` |
| Feedback loop map | `../social_media_optimiser/03-review-packets/agent-studio-feedback-loop-map.html` |
| System-design source map | `../system_design_vault/output/viewers/system-design-source-map.html` |

## Known contradictions & stale docs

| Issue | Location | Problem | Resolution |
|-------|----------|---------|------------|
| **MOC "Next" vs Kanban "In Progress"** | [[../social_media_optimiser/Agent Studio MOC]] item 37 vs [[../social_media_optimiser/01-work-tracking/Agent Studio Kanban]] | MOC: configure credentials and execute smoke; Kanban: pick **non-credential** hardening slice | Trust Kanban for next code slice; MOC item 37 is credential-path guidance |
| **Stale `## Next` in Current Sprint** | [[../social_media_optimiser/01-work-tracking/Current Sprint#Next]] (~L699–704) | Lists old walkthrough blockers; buried under 600+ Done bullets; contradicts UUID workspace | Refresh `## Next` to match matrix + Kanban; do not treat as current gate |
| **HLD date lag** | HLD frontmatter `updated: 2026-05-17` | Content patched (A2A projection) via sprint; metadata stale | Bump frontmatter after doc sync |
| **Qdrant/Neo4j canon vs code** | System-design ingestion notes | `canon_ready` release gates documented; zero implementation in `src/` | Expected — Postgres-first until benchmarks justify |
| **Ingestion "clear" vs product "blocked"** | `urgent-blockers.json` vs proof matrix | Different lanes — not a true contradiction | Read both; ingestion lane ≠ product proof lane |

## Mirrors aligned

Project audit and system-design mirror agree on:

- Live voice accepted on the current OpenRouter/LiveKit/Kokoro path
- One remaining proof blocker: external publication
- UUID run `190ae2f9-a74b-4a23-b39c-aaf2d636bd8e`
- Failed external publication record pending operator inputs and accepted destination proof

## Agent progress vault role

This vault records **what Cursor agents did and found** in a session. After material slices:

1. Update planning vaults first ([[../social_media_optimiser/01-work-tracking/Current Sprint]], Kanban)
2. Optionally append session log here
3. Refresh [[../01-implementation-matrix/feature-implementation-status]] if code evidence changed

Do not duplicate Kanban/sprint content here — link instead.
