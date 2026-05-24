---
name: agent-studio-conversation-harness
description: "Operate the realtime voice/text conversation layer for the multi-agent content studio. Use when routing user dialogue, handling interruptions, recording conversation turns, opening human feedback gates, or converting natural dialogue into structured agent messages."
---

# Agent Studio Conversation Harness

## Workflow

1. Preserve natural dialogue first: accept voice or text, keep the user's wording, and do not force project-management UI concepts into the app.
2. Record each meaningful user/assistant turn as a durable conversation turn with modality, transcript, optional audio URI, and metadata.
3. Prefer `POST /api/conversation/turns` for natural dialogue turns so one request can start content generation, route feedback into revision, create an Intent Router A2A task, or record-only.
4. Use `POST /api/feedback` for standalone user notes that need to become a routed `FeedbackItem`, specialist A2A task, and note/progress memories without forcing a full revision loop.
5. Use `POST /api/planning/feedback` when suggestions captured in the separate planning HTML should become routed `FeedbackItem` records, specialist A2A tasks, memory notes, and a `planning_feedback_ingested` event.
6. Route semantic work through the Intent Router as an A2A-style message. Use specialist agents for research, content, media, review, or feedback.
7. Persist a `conversation_handoff` artifact for routed live turns so the Intent Router sees the user turn, assistant reply, recent turns, run state, pending tasks, open feedback, and recommended next steps.
8. Use `POST /api/runs/{run_id}/multimodal-intake` when voice dialogue includes image, screenshot, audio, video, reel, document, or text asset references that should become durable specialist work.
9. Let Realtime Conversation Host worker tasks persist a `realtime_conversation_brief` artifact with session inventory, interruption state, voice feedback, and handoff recommendations.
10. Let Intent Router worker tasks persist an `intent_route_plan` artifact, select specialists, and create idempotent downstream `AgentMessage` handoffs from the live turn.
11. Open a human feedback gate whenever the next step depends on user preference, approval, or correction.
12. Resolve approval gates through durable feedback status updates instead of only changing run status.
13. Let Forward Deployed Engineer worker tasks convert user feedback into `feedback_requirements` artifacts with acceptance criteria and specialist handoff tasks.
14. Let Principal Software Engineer worker tasks record `architecture_review` artifacts across durability, worker coverage, provider boundaries, feedback gates, and engineering next actions.
15. Use `POST /api/runs/{run_id}/resume` after restart or pause recovery only after the resume plan proves no human gate, failed run, canceled run, completed run, or blocked task prevents autonomous work.
16. Use `POST /api/runs/{run_id}/distribution-package` after source-backed drafts exist and the user needs platform-ready hooks, captions, hashtags, keywords, CTAs, or outreach angles.
17. Use `POST /api/runs/{run_id}/sync-pulse` when the Product Manager, Sprint/Progress Agent, or Agent Harness Engineer needs a shared view of current agent focus, blockers, handoffs, and next actions.
18. Use `POST /api/runs/{run_id}/work-plan` when the Sprint/Progress Agent needs to convert pending feedback, A2A tasks, worker profile state, and quality gates into a concrete next-pass plan; use follow-up task creation only when the next worker pass should pick up missing quality-gate work.
19. Use `POST /api/runs/{run_id}/context-packet` before long-running synthesis or resumed specialist work so agents receive a budgeted context manifest, risk flags, recent event tail, and recommended fetches.
20. Let the A2A Protocol Agent worker audit agent cards, skill coverage, model/tool boundaries, and current AgentMessage handoffs into an `a2a_contract_audit` artifact when protocol work arrives.
21. Let Context Engineering worker tasks persist a `context_packet` artifact when a resumed or long-running agent needs reusable context.
22. Let the Agent Harness Engineer worker create a checkpointed `run_resume_plan` artifact when a durable run needs pause/restart context for a target specialist or the whole run.
23. Use `POST /api/runs/{run_id}/replay-ledger` after a checkpoint when a resumed agent needs to inspect event and state deltas before continuing.
24. Let Product Manager and Sprint/Progress Agent worker tasks invoke sync-pulse and work-plan generation when routed feedback or coordination tasks arrive in their inboxes.
25. Use `execution_mode=autonomous_pass` worker profiles for always-on studio runs that should heartbeat through the full checkpointed, runtime-checked, research-gated autonomous pass instead of only a raw worker cycle. Every active heartbeat must claim a durable heartbeat lease, build a resume-plan gate, and stop on human feedback, blocked tasks, failed runs, or canceled runs.
26. Let autonomous studio passes create a checkpoint, run runtime health and research freshness preflights, launch one bounded provider-backed Web Research Agent source-refresh task when source evidence is blocked, and continue pending `multimodal_review_followup_v1` tasks in a second bounded worker cycle so asset-aware handoffs do not stall after the first review pass. Keep `block_on_runtime_health_blocked` and `block_on_research_freshness_blocked` enabled for autonomous publishing work.
27. Use `POST /api/runs/{run_id}/runtime-health-ledger`, `all-about-llms-admin build-runtime-health-ledger`, or an Observability Agent `build_runtime_health_ledger` task when local runtime readiness needs a durable Postgres/pgvector/Docker/LangGraph/no-SQLite preflight record. Keep `record_live_store_evidence` enabled when backed by PostgresStore so the run timeline captures `runtime_health_live_postgres_connected`.
28. Emit timeline events for state changes. Do not create a board-based workflow unless the user explicitly reverses the current no-board decision.

## Required Outputs

- `ConversationTurn` for each durable voice/text turn.
- `realtime_conversation_brief_created` event and `realtime_conversation_brief` artifact when the Realtime Conversation Host summarizes session and turn-taking state.
- `AgentMessage` for each routed specialist task.
- `conversation_handoff_recorded` event and `conversation_handoff` artifact when a live turn is routed to the Intent Router.
- `intent_route_plan_created` event and `intent_route_plan` artifact when the Intent Router converts live dialogue into specialist handoffs.
- `FeedbackItem` with routed status when standalone feedback has already been assigned to a specialist.
- `AgentMemory` notes for the specialist, Interactive Note-Taking Agent, and Sprint/Progress Agent after standalone feedback routing.
- `RunEvent` for accepted messages, feedback gates, provider state, and failures.
- `conversation_turn_routed` event for the selected durable dialogue action.
- `feedback_routed` event when standalone feedback becomes specialist work.
- `planning_feedback_ingested` event when the separate planning surface routes saved suggestions into the durable agent loop.
- `multimodal_intake_recorded` event and `multimodal_intake_ledger` artifact when user-provided media or document references are routed to specialists.
- `multimodal_intake_review_recorded` event and `multimodal_review` artifact when a specialist processes an attached asset task; Gemma-backed reviews also emit model policy approval plus `gemma_worker_completed` and `gemma_multimodal_review_completed` events.
- `multimodal_review_followups_materialized` event and follow-up `AgentMessage` records when a completed multimodal review can safely hand work to context, manager, planning-note, voice, or media specialists.
- `feedback_requirements_recorded` event and `feedback_requirements` artifact when the Forward Deployed Engineer turns feedback into acceptance criteria and specialist handoffs.
- `architecture_review_recorded` event and `architecture_review` artifact when the Principal Software Engineer records engineering risks and next actions.
- `feedback_resolved` event when an approval or correction gate is closed.
- `run_work_plan_built` event and `system_plan` artifact when the Sprint/Progress Agent creates the next-pass work plan.
- `multi_agent_sync_pulse_recorded` event and `system_plan` artifact when manager/scrum/harness agents need a shared coordination snapshot.
- `worker_profile_heartbeat` event with execution mode, resume-plan context, autonomous-pass event id, processed task count, and work-plan artifact ids when an always-on profile heartbeats.
- `worker_profile_heartbeat_blocked` event when an active profile pauses because the resume-plan gate found open human feedback, blocked tasks, failed runs, or canceled runs.
- `skipped_reason=heartbeat_already_running` when a manual heartbeat or scheduler pass finds an active unexpired profile heartbeat lease.
- `autonomous_multimodal_followups_continued` event when an autonomous studio pass consumes pending multimodal follow-up tasks after the primary worker cycle.
- `autonomous_research_sources_refreshed` event when an autonomous studio pass repairs a blocked source-evidence gate through a configured web search provider.
- `a2a_protocol_audit_recorded` event and `a2a_contract_audit` artifact when A2A cards, skills, and handoffs are audited.
- `distribution_package_built` or `distribution_package_reused` event and `social_package` artifact when growth/platform/outreach agents package current drafts for channel-specific use.
- `agent_tool_use_approved` / `agent_tool_use_denied` and `agent_model_use_approved` / `agent_model_use_denied` events before a worker uses external tools or Gemma models.
- `run_resume_started`, `run_resume_blocked`, or `run_resume_completed` when long-running work is restarted or gated.
- `context_packet_built` with manifest, risk, and recommended-fetch counts when a context packet is prepared for an agent.
- `context_packet_artifact_created` and `context_packet` artifact when a reusable packet is persisted for a specialist.
- `resume_plan_built`, `run_checkpoint_recorded`, `agent_harness_resume_plan_recorded`, and `run_resume_plan` artifact when the harness worker prepares long-running recovery context.
- `run_replay_ledger_built` event and `run_replay_ledger` artifact when checkpoint-to-event replay context is generated.
- `runtime_health_ledger_built` event and `runtime_health_ledger` artifact when the Observability Agent records static runtime checks and live-evidence gaps, including autonomous pass preflight when enabled.
- `research_freshness_ledger_built` event and `research_freshness_ledger` artifact during autonomous passes when source freshness preflight is enabled.
- `runtime_health_live_postgres_connected` event when the current runtime-health request proves read/write access through the Postgres-backed store.
- `AgentMessage` follow-ups from the Sprint/Progress Agent when a work-plan item has no live task and can be safely materialized.
- A concise spoken/text status summary for the user when background work starts, pauses, resumes, or finishes.

## Boundaries

- Realtime audio providers own speech transport, turn-taking, interruption, and spoken output.
- Gemma 4 experts own reasoning, synthesis, critique, writing, and multimodal review when the agent card permits Gemma and the HF provider is configured.
- The animated planning HTML is separate from the product app.
- Postgres is required for durable runs; do not introduce SQLite or local JSON substitutes.
