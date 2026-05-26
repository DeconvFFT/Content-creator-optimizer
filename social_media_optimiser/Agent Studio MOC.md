---
type: moc
project: agent-studio
status: active
updated: 2026-05-21
---

# Agent Studio MOC

This Obsidian vault is the planning and tracking source of truth for the Agent Studio. Product code stays outside the vault. Interactive HTML can exist as a companion view, but core design, decisions, research, and tracking should be readable and linkable inside Obsidian.

## Start Here

- [[00-system-design/HLD - Agent Studio]]
- [[00-system-design/LLD - Agent Studio]]
- [[00-system-design/Agent Roster and Responsibilities]]
- HTML: `00-system-design/agent-studio-a2a-map.html`
- HTML: `00-system-design/agent-studio-skill-matrix.html`
- [[SCHEMA]]
- [[wiki/_index]]
- [[wiki/concepts/three-tier-agent-memory]]
- [[wiki/concepts/production-agent-system-design-canon]]
- [[wiki/product/agent-studio-memory-layer]]
- [[wiki/ops/codex-obsidian-working-memory]]
- [[wiki/ops/autonomous-obsidian-ingestion-flow]]
- [[wiki/ops/active-codex-context]]
- [[02-research/Retrieval Intelligence and Knowledge Graph Research]]
- HTML: `02-research/openrouter-livekit-voice-boundary-map.html`
- [[01-work-tracking/Current Sprint]]
- [[01-work-tracking/Agent Studio Kanban]]
- [[01-work-tracking/Agent Studio Objective Completion Audit]]
- HTML: `01-work-tracking/agent-studio-proof-readiness.html`
- [[01-work-tracking/Decision Log]]
- [[03-review-packets/Feedback Inbox]]
- HTML: `03-review-packets/agent-studio-publication-boundary-map.html`
- HTML: `03-review-packets/agent-studio-feedback-loop-map.html`

## Companion Outputs

- JSON: `output/viewers/agent-studio-memory-os.json`
- HTML: `output/viewers/agent-studio-memory-os-viewer.html`
- System JSON: `output/viewers/agent-studio-system-design.json`
- System HTML: `output/viewers/agent-studio-system-design-viewer.html`
- System Design Source Map Viewer: `../system_design_vault/output/viewers/system-design-source-map.html`
- A2A Map HTML: `00-system-design/agent-studio-a2a-map.html`
- Skill Matrix HTML: `00-system-design/agent-studio-skill-matrix.html`
- Proof Readiness HTML: `01-work-tracking/agent-studio-proof-readiness.html`
- Publication Boundary HTML: `03-review-packets/agent-studio-publication-boundary-map.html`
- Feedback Loop Map HTML: `03-review-packets/agent-studio-feedback-loop-map.html`
- OpenRouter LiveKit Voice Boundary HTML: `02-research/openrouter-livekit-voice-boundary-map.html` (visible content and exports describe the current OpenRouter + LiveKit + Kokoro route)
- Proof-plan handoff: proof readiness plus the OpenRouter LiveKit voice and publication boundary maps carry proof_plan proof-plan packets matching `provider-proof-plan`, including `proof_plan.operator_proof_packet` as the compact provider-proof-plan packet with `current_matrix_packet_command`; the current-matrix `operator_proof_packet` reciprocates with `proof_plan_packet`, `proof_plan_packet_ref`, `proof_plan_packet_command`, and `proof_plan_operator_packet_ref`.
- Current proof packets: `output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-proof-status.md`, `output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-blocker-matrix.json`, and `output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-unblocker-checklist.md`; current-matrix operator packets list `proof_plan` in `source_artifacts`.

## Non-Negotiables

- No SQLite.
- Durable store is Postgres + pgvector from v1.
- OpenRouter `deepseek/deepseek-v4-flash` is the current live-dialogue reasoning default; Gemma/Gamma/Hugging Face/MLX are legacy or future native-audio lanes unless deliberately re-promoted.
- Realtime audio providers own natural speech-to-speech dialogue, interruption, turn-taking, and spoken output.
- Product app is a live conversational studio, not a planning or project-management dashboard.
- Planning, design, tracking, and review happen in this Obsidian vault.
- The Kanban board is vault-only planning state and must not become product UI.
- Obsidian memory uses three tiers: `raw/`, `wiki/`, and `output/`.
- Codex should start from the compact [[wiki/ops/active-codex-context]] note for project-memory-dependent work.

## Current Focus

1. Make the Obsidian vault the working planning system.
2. Keep HLD and LLD clear enough for review.
3. Add retrieval intelligence and knowledge graph design as first-class system requirements.
4. Done: wire retrieval quality into autonomous passes, context packets, resume plans, and Postgres evidence tables.
5. Done: create Obsidian-native run review notes from durable run state so agent reviews land in the vault.
6. Done: add provider-neutral reranker interface with deterministic local default and future HF/cloud reranker slot.
7. Done: promote accepted retrieval evidence into source-ledger, context, resume, and writer flows.
8. Current communication rule: update Obsidian notes first; use HTML only as a companion visualization when specifically useful.
9. Done: make Claim Verification, Editor-in-Chief, and Publish Readiness consume accepted retrieval evidence directly so unsupported or unaccepted claims are held.
10. Done: add deterministic claim rewrite/hold artifacts so writer agents get explicit revision instructions before new draft versions are generated.
11. Done: route claim revision plans into autonomous follow-up tasks for targeted writer/editor cycles.
12. Done: add a run-level claim revision closure ledger so the manager and publish-readiness handoff can see whether rewrite tasks closed the loop.
13. Done: create an Obsidian three-tier memory layer for project memory and Codex working memory.
14. Done: implement memory-promotion proposals from run review packets and durable run state into `wiki/run-memory-promotions/`.
15. Done: add explicit `user_preference` and `project_decision` memory records in Postgres + pgvector.
16. Done: add memory freshness and conflict checks to context packets.
17. Done: export selected memory summaries to Obsidian after autonomous passes when explicitly requested.
18. Done: verify always-on autonomous passes refresh claim revision closure state after writer/editor follow-ups.
19. Done: persist always-on autonomous profile controls for memory-summary export, research refresh policy, and retrieval block policy.
20. Done: surface always-on policy decisions in heartbeat ledgers and scheduler events.
21. Done: surface retrieval-quality and memory-health metrics in heartbeat ledgers, heartbeat events, blocked-heartbeat events, and scheduler events.
22. Done: add pgvector-backed project-memory retrieval with keyword scoring, graph-neighbor expansion, ledger artifacts, and worker support.
23. Done: wire project-memory retrieval summaries into context packets, autonomous context artifacts, worker-profile heartbeat context artifacts, and resume plans.
24. Done: add synthesized-memory retrieval evaluation metrics for labeled/heuristic precision, recall, false positives, false negatives, and repeated-query trend deltas.
25. Done: use project-memory retrieval metrics in worker context policy, Gemma prompt instructions, heartbeat metrics, and scheduler profile aggregates.
26. Done: use project-memory policy status to open human-confirmation gates for risky always-on actions before worker-profile execution.
27. Done: surface memory policy in the product cockpit from retrieval, context, resume, heartbeat, feedback, and timeline signals.
28. Done: add explicit labeled-relevance UI for project-memory retrieval evaluation.
29. Done: add compact active Codex context so future turns can use Obsidian as working memory before broad context loads.
30. Done: add generated JSON/HTML system-design viewer derived from HLD, LLD, and memory notes.
31. Done: add richer source-ledger drilldowns for accepted retrieval evidence and claim coverage.
32. Done: add cockpit controls for recording project memories directly from user-confirmed decisions.
33. Done: create an end-to-end cockpit demo run with seeded source, claim, artifact, retrieval ledger, source ledger, feedback gate, and project memory data.
34. Done: add provider-readiness smoke walkthroughs for Gemma/HF, selected realtime audio, selected web search, local reranking, imagegen boundary, and provider-free cockpit demo proof.
35. Done: add a durable cockpit walkthrough ledger that packages runtime, provider, source, realtime, observability, and feedback proof for a run.
36. Done: execute the cockpit walkthrough ledger against live Docker Postgres + pgvector for run `f34c732f-1168-4582-86f7-8bd6efcd0b02`; `4/6` required steps are ready.
37. Next: configure provider credentials/endpoints and execute realtime/provider-backed smoke.
38. Done: add production agent system design canon, expand foundation references to 18 records, and add Backend Platform, Frontend Experience, Scalability/Reliability, and Inference Systems specialists with project skills.
39. Done: add compact proof-plan operator-packet source-artifact provenance for `proof-plan.json` and `current-blocker-matrix.json`.
40. Done: render compact proof-plan packet details in proof-readiness, OpenRouter LiveKit voice boundary, publication boundary, and system-design viewer inspection surfaces.
41. Done: render operator packet `source_artifacts` in Markdown status, checklist, and proof workspace README packets.
42. Done: render proof-plan packet refs and refresh commands in generated proof workspace README packets.
43. Done: render current-matrix packet refs and refresh commands in generated proof workspace README packets.
