---
type: moc
project: agent-progress
status: active
updated: 2026-05-24
boundary: agent-owned-progress-tracking
---

# Agent Progress Vault MOC

**This vault is agent-owned progress tracking.** It records Cursor/Codex session outcomes, implementation evidence, and cross-vault sync notes. It does **not** replace planning source-of-truth vaults.

## Planning vaults (SoT)

- [[../social_media_optimiser/Agent Studio MOC|Social Media Optimiser]] — sprint, Kanban, proof status, HLD/LLD, operator handoffs
- [[../system_design_vault/MOC|System Design Vault]] — research memory, ingestion runs, architecture implications

## This vault

Current live voice default: OpenRouter `deepseek/deepseek-v4-flash` + LiveKit + Kokoro. The MLX/E4B/Gemma/HF notes below are historical or optional native-audio background unless a future note explicitly reactivates them.

| Section | Note |
|---------|------|
| [[00-session-log/2026-05-23-ship-readiness-audit]] | 2026-05-23 ship-readiness session log |
| [[01-implementation-matrix/feature-implementation-status]] | Vault claim vs code evidence matrix |
| [[02-remaining-work/prioritized-backlog]] | Phased backlog (Phase 0–3) |
| [[03-agent-activity/background-agents-registry]] | Cursor session agents + monitoring deliverables |
| [[04-cross-vault-links/vault-sync-notes]] | SoT authority, contradictions, proof workspace links |
| [[05-quality/errors-and-failures]] | Runtime/setup interruptions and failure evidence |
| [[06-live-voice/local-livekit-setup]] | Local LiveKit + start commands |
| [[06-live-voice/openrouter-livekit-live-dialogue]] | OpenRouter + LiveKit live-dialogue runbook |
| [[06-live-voice/openrouter-livekit-current-unblock-guide]] | Current OpenRouter/LiveKit/Kokoro proof and external publication unblock guide |
| [[06-live-voice/status-snapshot-2026-05-23]] | Current local voice stack status |
| [[06-live-voice/local-e4b-setup-runbook]] | Superseded local E4B MLX + proxy runbook for native-audio experiments |
| [[06-live-voice/local-e4b-inference-options]] | Superseded MLX/vLLM/SGLang comparison for native-Gemma experiments |
| [[06-live-voice/operator-inputs-checklist]] | Historical credential checklist; current OpenRouter/LiveKit live-voice inputs are configured |

## Current gate (2026-05-24)

Objective **not complete**. Proof run UUID: `190ae2f9-a74b-4a23-b39c-aaf2d636bd8e`.

- Platform ~75–90% implemented locally by area
- Provider-backed live voice proof is **accepted** on the current OpenRouter `deepseek/deepseek-v4-flash` + LiveKit + Kokoro path
- External publication proof remains blocked on LinkedIn token file, policy acknowledgement artifact, durable destination URL/platform id, and rollback/postcondition evidence
- Production verdict: **NO-GO** until external publication proof and closure review pass; local demo: **CONDITIONAL GO** (7/10)

See [[../social_media_optimiser/01-work-tracking/Agent Studio Objective Completion Audit]] and [[01-implementation-matrix/feature-implementation-status]].

## Monitoring tools (repo, not vault)

- Canvas: `~/.cursor/projects/Users-saumyamehta-Gen-AI-all-about-llms/canvases/agent-status-board.canvas.tsx`
- Watch script: `../scripts/watch-agent-transcripts.sh`
- Docs: `../scripts/AGENT-MONITORING.md`
