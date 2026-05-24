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
- PR/CI handoff: feature branch remote CI was green for the current pushed head at last live check. The Auto PR workflow also reached its create/update step after generating the no-secret provider proof PR body, but GitHub denied draft PR create/update with repository-settings `403`, so it emitted `Auto PR skipped` and no PR was created. GitHub connector PR creation still returns `403 Resource not accessible by integration`, REST lookup shows no open PR, and public branch metadata reports `main` is currently unprotected. CI now runs `uv lock --check` before Python dependency sync and installs from committed `uv.lock`; keep local command logs untracked. Use `uv run all-about-llms-admin provider-proof-pr-handoff --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e --operator-input-path social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env --ci-url <latest-branch-head-ci-url> --head-sha <current-branch-head-sha>` for a no-secret manual PR body generated with fresh branch evidence. The filled CI URL must be a same-repo GitHub Actions run URL, and the filled SHA must be a 40-character hex commit id.
- Fresh PR integration check `2026-05-24`: branch-head CI completed green, Auto PR completed after the no-secret handoff path but no PR was created, GitHub connector PR creation still returned `403 Resource not accessible by integration`, and local `provider-proof-pr-create` still returns `manual_required` without `GITHUB_TOKEN` or `GH_TOKEN`. Manual PR compare remains <https://github.com/DeconvFFT/Content-creator-optimizer/compare/main...feature/livekit-voice-proof-capture?expand=1>. Regenerate `provider-proof-pr-handoff` with fresh `--ci-url` and `--head-sha` at PR creation time.
- Fresh continuation check `2026-05-24` before this documentation refresh: observed branch head was `755d4ff09b5c6bd01ccd454b4942419e698521dc`; GitHub Actions CI run `26376107041` was completed/success; REST PR lookup still returned no open PR; `provider-proof-pr-create` with that CI URL and SHA returned `manual_required` / `github_token_unavailable`; public branch metadata reported `main.protected=false`, while the protection endpoint itself requires authenticated repo-admin access. Keep using manual PR creation or repository Actions/app permission changes, and regenerate exact SHA/CI evidence after any follow-up commit.
- Manual PR body update: generated `provider-proof-pr-handoff` now embeds the repository settings checklist for Actions read/write permission, PR-creation permission, `main` branch protection/ruleset, required checks, CODEOWNERS review, and auto-merge setup.
- CI/CD runtime hardening: GitHub Actions annotations on Auto PR run `26375041710` warned that Node 20 JavaScript actions will be forced to Node 24 in June 2026. The CI and Auto PR workflows now set `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true`, and Auto PR's temporary publication placeholders match the committed no-secret example shape with `-or-url` suffixes.
- Fresh local render follow-up `2026-05-24T22:25Z`: `127.0.0.1:3001` is occupied by a Next dev process in `frontend/next-app`, but local HTTP and in-app Browser navigation did not complete. Starting another dev server on `3002` was refused by Next because the existing dev server lock points at PID `60273`. Do not kill or restart the shared dev process without operator approval. `npm run build` in `frontend/next-app` completed successfully and prerendered `/`, so the code path builds; the current unresolved issue is the stale/unresponsive local dev server, not a committed UI compile failure.

**Do not confuse with:** `RUN-2026-05-20-NEXT` — intentionally blocked (`run_id_not_product_uuid`); operators must use UUID bootstrap.

## HTML review surfaces

| Surface | Path |
|---------|------|
| Proof readiness | `../social_media_optimiser/01-work-tracking/agent-studio-proof-readiness.html` |
| A2A map | `../social_media_optimiser/00-system-design/agent-studio-a2a-map.html` |
| OpenRouter LiveKit voice boundary | `../social_media_optimiser/02-research/openrouter-livekit-voice-boundary-map.html` |
| Publication boundary | `../social_media_optimiser/03-review-packets/agent-studio-publication-boundary-map.html` |
| Feedback loop map | `../social_media_optimiser/03-review-packets/agent-studio-feedback-loop-map.html` |
| System-design source map | `../system_design_vault/output/viewers/system-design-source-map.html` |

Current rename sync: the live voice boundary review surface now uses
`../social_media_optimiser/02-research/openrouter-livekit-voice-boundary-map.html`,
and the current unblock guide is
`../agent_progress_vault/06-live-voice/openrouter-livekit-current-unblock-guide.md`.
Do not reintroduce Gemma/Gamma/Hugging Face/MLX as active-current filenames or
task names for the accepted OpenRouter/LiveKit/Kokoro proof path.

## Known contradictions & stale docs

| Issue | Location | Problem | Resolution |
|-------|----------|---------|------------|
| **MOC "Next" vs Kanban "In Progress"** | [[../social_media_optimiser/Agent Studio MOC]] item 37 vs [[../social_media_optimiser/01-work-tracking/Agent Studio Kanban]] | MOC: configure credentials and execute smoke; Kanban: pick **non-credential** hardening slice | Trust Kanban for next code slice; MOC item 37 is credential-path guidance |
| **Resolved 2026-05-24: `## Next` in Current Sprint** | [[../social_media_optimiser/01-work-tracking/Current Sprint#Next]] | Now lists the current external publication proof, closure review, blocker-state update, branch-protection/auto-merge, and demo feedback gates. Remote CI and Playwright install were green at last live check; connector PR creation is blocked by GitHub `403` and REST lookup currently shows no open PR. | Keep it fresh after any proof-state change |
| **HLD date lag** | HLD frontmatter `updated: 2026-05-17` | Content patched (A2A projection) via sprint; metadata stale | Bump frontmatter after doc sync |
| **Qdrant/Neo4j canon vs code** | System-design ingestion notes | `canon_ready` release gates documented; zero implementation in `src/` | Expected — Postgres-first until benchmarks justify |
| **Ingestion "clear" vs product "blocked"** | `urgent-blockers.json` vs proof matrix | Different lanes — not a true contradiction | Read both; ingestion lane ≠ product proof lane |

## Mirrors aligned

Project audit and system-design mirror agree on:

- Live voice accepted on the current OpenRouter/LiveKit/Kokoro path
- One remaining proof blocker: external publication
- UUID run `190ae2f9-a74b-4a23-b39c-aaf2d636bd8e`
- Failed external publication record pending operator inputs and accepted destination proof
- External publication artifact inputs must now avoid generic bare values such as `policy-artifact-1` / `rollback-artifact-1`; use an external non-local URL, LinkedIn URN with an ID suffix, whitelisted namespaced durable artifact id, or UUID-bearing artifact id.
- Reserved documentation domains such as `docs.example.com`, `example.com`, `example.org`, and `example.net` are now treated as placeholder evidence and must not clear policy acknowledgement or rollback/postcondition readiness.
- Accepted proof packet rendering now suppresses proof-specific retry/capture/credential-snapshot details for `provider-backed-live-voice-proof`; future agents should treat only `external-publication-proof` as actionable unless completion status changes.
- CI/CD mirrors now include the Node 24-native action pin follow-up: `actions/checkout@v6`, `actions/setup-python@v6`, `actions/setup-node@v6`, `actions/github-script@v8`, and `astral-sh/setup-uv@v8.1.0`, plus the existing `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` guard and `uv.lock` dependency-lock boundary.
- Current realtime env docs now use `OPENROUTER_REALTIME_*` and generic `REALTIME_*` names for the accepted OpenRouter/LiveKit/Kokoro path. `GEMMA4_REALTIME_*` settings remain compatibility aliases only and should not appear as active-current setup tasks.

## Agent progress vault role

This vault records **what Cursor agents did and found** in a session. After material slices:

1. Update planning vaults first ([[../social_media_optimiser/01-work-tracking/Current Sprint]], Kanban)
2. Optionally append session log here
3. Refresh [[../01-implementation-matrix/feature-implementation-status]] if code evidence changed

Do not duplicate Kanban/sprint content here — link instead.
