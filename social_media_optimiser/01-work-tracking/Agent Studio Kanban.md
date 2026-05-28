---
type: kanban
project: agent-studio
status: active
updated: 2026-05-24
boundary: planning-vault-only
sources:
  - [[Current Sprint]]
  - [[../Agent Studio MOC]]
  - [[../wiki/ops/active-codex-context]]
---

# Agent Studio Kanban

Product app must not render this board. This is an Obsidian planning note for Codex/operator coordination, review watch, blockers, and next implementation slices. Creator-facing UI remains the live conversational studio, not a project-management surface.

## Backlog

- [ ] External publication proof capture for LinkedIn.
  Source: [[Current Sprint]] and current UUID proof workspace.
  Exit: accepted `external-publication-proof` record passes after policy acknowledgement, durable destination, rollback/postcondition evidence, validation, and recording.

## Ready

No review-watch alignment item is waiting. The standing reviewer status is tracked in Review Watch, and the next ready review action is the next material code slice review after implementation changes.

## In Progress

- [ ] Select the next bounded non-publication implementation slice.
  Source: active Codex goal and [[../wiki/ops/active-codex-context]].
  Exit: next slice has a failing-first test, implementation target, validation plan, and `Leibniz` review packet. Current likely non-credential slice is a small product/proof hardening patch; credential-gated publication proof remains blocked.

## Blocked

- [ ] External publication proof remains blocked on real destination credentials.
  Source: [[Current Sprint]] and `social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-proof-status.md`.
  Blocker: manual-publication policy review remains missing, and accepted proof still requires durable external destination evidence plus rollback or postcondition evidence. Use the matrix `Report-only operator-input retry chain` for normal inspection after operator inputs change, and the `Guarded operator-input retry chain` only when a non-zero blocked exit is wanted. The UUID proof workspace already has approved local fixture artifact, source, claim, guardrail audit, and source ledger evidence.

## Done

- [x] Provider-backed live voice proof accepted for the current OpenRouter/LiveKit/Kokoro path.
  Source: [[Current Sprint]] and `social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-proof-status.md`.
  Exit: accepted record references OpenRouter `deepseek/deepseek-v4-flash`, LiveKit, Kokoro, provider-smoke ledger `94857bb9-c5eb-4174-8bc5-6687bd8befbe`, timing ledger `7e932381-4bf4-4206-a490-58d6a4ca7880`, realtime session `ebd43531-86e3-4af1-ade0-15ac8d7184bf`, 7/7 post-capture checks, and passed secret redaction. Do not reopen Hugging Face/Gamma/Gemma/MLX as the active realtime path unless a later decision explicitly supersedes OpenRouter; those paths are legacy/native-audio background only.
- [x] OpenRouter text-turn live-dialogue readiness contract added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `agent_progress_vault/06-live-voice/openrouter-livekit-live-dialogue.md`, `src/all_about_llms/voice_agent/adapters.py`, `src/all_about_llms/voice_agent/readiness.py`, and `tests/test_api_contracts.py`.
  Exit: `/api/voice-runtime-readiness` now has hermetic coverage proving OpenRouter chat-completions routing can satisfy the live-dialogue reasoning check without a Gemma multimodal endpoint, while HF router/text-primary endpoints remain insufficient for native Gemma audio proof. The runtime emits both OpenRouter and native Gemma checks when both configs are present, provider-proof validation rejects OpenRouter-only readiness as native audio proof, and the Gemma/OpenRouter streaming preflight now constructs auth headers with the keyword-only helper and reaches the streamed HTTP path.
- [x] Project-memory and publish-readiness durable event redaction added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `src/all_about_llms/orchestration/project_memory.py`, `src/all_about_llms/orchestration/publish_readiness.py`, `src/all_about_llms/realtime_safety.py`, and `tests/test_api_contracts.py`.
  Exit: `ProjectMemoryWorkflow` and `PublishReadinessWorkflow` now sanitize `project_memory_recorded`, publish-readiness `feedback_recorded`, `human_feedback_gate_opened`, and `publish_readiness_checked` durable event payloads through `safe_realtime_metadata`. Private `AgentMemory`, `FeedbackItem`, and publish-readiness response payloads still preserve the trusted local content, while durable event payloads redact Bearer/HF/Tavily-shaped strings, including lower-case bearer variants from normalized publish-channel names, and drop sensitive metadata keys before persistence.
- [x] Feedback and memory durable event redaction added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `src/all_about_llms/orchestration/feedback_routing.py`, `src/all_about_llms/orchestration/revision_workflow.py`, `src/all_about_llms/app.py`, and `tests/test_api_contracts.py`.
  Exit: `feedback_recorded`, `feedback_routed`, and `memory_recorded` durable events now sanitize payloads through `safe_realtime_metadata` across `FeedbackRoutingWorkflow`, `RevisionWorkflow`, and direct memory recording. Stored `FeedbackItem` records, routed A2A messages, and private `AgentMemory` records keep original user feedback or memory text, while durable event payloads redact Bearer/HF/Tavily-shaped strings and drop sensitive metadata keys before persistence.
- [x] Conversation-turn durable event redaction added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `src/all_about_llms/app.py`, `src/all_about_llms/orchestration/content_workflow.py`, `src/all_about_llms/orchestration/conversation_router.py`, and `tests/test_api_contracts.py`.
  Exit: direct run turn recording, content workflow turn capture, and conversation router user/assistant turn events now sanitize `conversation_turn_recorded` durable event payloads through `_safe_realtime_metadata` or `safe_realtime_metadata`. Private stored turns and API responses keep the original transcript, while event payloads redact Bearer/HF/Tavily-shaped strings and drop sensitive metadata keys before persistence.
- [x] A2A skill-invocation event redaction added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `src/all_about_llms/orchestration/a2a_projection.py`, and `tests/test_api_contracts.py`.
  Exit: `agent_skill_invocation_recorded` now uses `public_a2a_skill_invocation_event_payload`, preserving workflow/status/notes, message id, agent id, skill ids, skill source paths, outputs, guardrails, and context summary counts while redacting token-shaped task type strings in durable skill-use event payloads.
- [x] A2A context-packet event redaction added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `src/all_about_llms/orchestration/a2a_projection.py`, and `tests/test_api_contracts.py`.
  Exit: worker and `/api/runs/{run_id}/context-packet` `context_packet_built` events now use `public_a2a_context_packet_event_payload`, preserving worker context counts, skill ids, project-memory policy, and retrieval summary shape while redacting token-shaped task type and memory-query strings in durable event payloads.
- [x] A2A stale-recovery event redaction added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `src/all_about_llms/orchestration/a2a_projection.py`, and `tests/test_api_contracts.py`.
  Exit: `agent_message_recovered` now uses `public_a2a_recovered_event_payload`, preserving message id, transition status, previous timestamp, worker id, and stale threshold while redacting token-shaped task type and previous claimant strings with `redact_realtime_string`.
- [x] A2A retry/dependency event redaction added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `src/all_about_llms/orchestration/a2a_projection.py`, and `tests/test_api_contracts.py`.
  Exit: `agent_message_retry_authorized`, `agent_message_dependencies_repaired`, `agent_message_dependency_waiting`, and `agent_message_retry_exhausted` now use `public_a2a_retry_event_payload`, `public_a2a_dependency_repair_event_payload`, `public_a2a_dependency_waiting_event_payload`, and `public_a2a_retry_exhausted_event_payload`, preserving retry counters and dependency ids while redacting token-shaped task type, sender/recipient/worker, notes, and reason strings with `redact_realtime_string`.
- [x] A2A status-event redaction added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `src/all_about_llms/orchestration/a2a_projection.py`, and `tests/test_api_contracts.py`.
  Exit: `agent_message_status_updated` events now use the shared A2A status-event projection backed by `redact_realtime_string`, so status transition payloads preserve message id/status/skill metadata including worker `skill_ids` while redacting token-shaped task type, sender/recipient, and notes strings.
- [x] A2A accepted-message event redaction added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `src/all_about_llms/orchestration/a2a_projection.py`, and `tests/test_api_contracts.py`.
  Exit: `agent_message_accepted` events now use the shared public A2A projection before persistence, so top-level `task_type` / `claimed_by_agent_id` plus message payload/result/handoff/error values drop sensitive keys and redact Bearer/HF/Tavily-shaped strings across API, provider-smoke, revision, feedback, content, multimodal, work-plan, autonomous-pass, and worker paths.
- [x] A2A collaboration graph trace-note redaction added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `src/all_about_llms/orchestration/a2a_graph.py`, and `tests/test_api_contracts.py`.
  Exit: graph trace edge metadata now reuses the shared realtime redaction boundary, and the A2A graph trace identity fix-back covers trace actor/action/status plus task-node `latest_handoff_action`, so Bearer/HF/Tavily-shaped strings render as `Bearer [redacted]`, `hf_[redacted]`, and `tvly-[redacted]` in both the API response and recorded graph artifact.
- [x] Project vault home routes to system-design source-map viewer.
  Source: [[Current Sprint]], [[../Agent Studio MOC]], `agent-studio-vault-home.html`, `system_design_vault/output/viewers/system-design-source-map.html`, and `tests/test_vault_home_browser.py`.
  Exit: the project vault home and MOC now expose the generated system-design source-map viewer, and Chromium navigation proves the route reaches `Agent Studio Source Map` with 175 source records and 126 design implications while staying outside product UI.
- [x] System-design source-map viewer browser proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `system_design_vault/output/viewers/system-design-source-map.html`, and `tests/test_system_design_source_map_viewer_browser.py`.
  Exit: Chromium opens the system-design source-map viewer and proves it renders source records, source groups, policy lists, first-slice items, search, kind filter, and coverage-granularity filter, plus design implications, implication search, visible record counts, no-match states, and clickable source-note paths while staying a planning-memory surface.
- [x] System-design vault entry links to review and generated viewer added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `system_design_vault/agent-studio-system-design-home.html`, and `tests/test_system_design_vault_home_browser.py`.
  Exit: the system-design vault browser index now routes reviewers to `Project HLD/LLD Review Surface` and `Project System Design Viewer`, preserving comment export and generated-viewer source-truth boundaries without putting planning surfaces into product UI.
- [x] Feedback loop map review-watch escalation added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `social_media_optimiser/03-review-packets/agent-studio-feedback-loop-map.html`, and `tests/test_feedback_loop_map_browser.py`.
  Exit: the feedback-loop map now filters and exports `leibniz-review-watch-escalation`, including standing reviewer `019e3899-5ab3-7171-9d3c-32e7c57bbde7`, latest no-Critical/Important status, and the severity/files/next-action escalation contract while keeping no-finding heartbeats quiet.
- [x] Active context A2A discovery paragraph is current.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `tests/test_foundation.py`.
  Exit: current-state handoff names `projection=public`, `agent-message-public-projection-v1`, `getTask`, `listRunMessages`, and `agentInbox` in the main A2A discovery paragraph.
- [x] HLDs record public A2A projection discovery.
  Source: [[Current Sprint]], [[../00-system-design/HLD - Agent Studio]], `system_design_vault/04-agent-studio-implications/HLD - Agent Studio System Design.md`, and `tests/test_foundation.py`.
  Exit: both HLDs name the well-known Agent Card, `/api/a2a`, `projection=public`, `agent-message-public-projection-v1`, and supported read endpoints so design docs match runtime discovery.
- [x] Well-known Agent Card advertises public projection.
  Source: [[Current Sprint]], `/.well-known/agent-card.json`, and `tests/test_api_contracts.py`.
  Exit: public Agent Card clients can discover the same `projection=public` task-inspection policy as `/api/a2a`.
- [x] A2A map renders public projection contract.
  Source: [[Current Sprint]], `social_media_optimiser/00-system-design/agent-studio-a2a-map.html`, and `tests/test_a2a_map_browser.py`.
  Exit: the Public boundary filter visibly exports `projection=public`, `agent-message-public-projection-v1`, and supported projection endpoints for browser-first reviewers.
- [x] A2A discovery advertises public projection.
  Source: [[Current Sprint]], `/api/a2a`, and `tests/test_api_contracts.py`.
  Exit: A2A clients can discover that `getTask`, `listRunMessages`, and `agentInbox` accept `projection=public` under `agent-message-public-projection-v1`, while mutation routes stay private.
- [x] A2A agent inbox supports public projection.
  Source: [[Current Sprint]], `/api/a2a/agents/{agent_id}/inbox`, and `tests/test_api_contracts.py`.
  Exit: A2A clients can poll a recipient inbox with `projection=public` and receive the same redacted public payload shape as single-message detail.
- [x] Run-level A2A message list supports public projection.
  Source: [[Current Sprint]], `/api/runs/{run_id}/agent-messages`, `/api/a2a`, and `tests/test_api_contracts.py`.
  Exit: A2A clients can list run messages with `projection=public` and receive the same redacted public payload shape as single-message detail, while `/api/a2a` advertises the list route.
- [x] System-design viewer renders route-level required evidence.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], generated system-design viewer, UUID `current-blocker-matrix.json`, and `tests/test_system_design_viewer_browser.py`.
  Exit: each Objective Completion Audit per-proof route now includes `required_evidence_after_unblock`, so route-first reviewers see the live voice and publication evidence gates without returning to the top-level blocker map.
- [x] System-design viewer renders operator-input readiness status.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], generated system-design viewer, UUID `current-blocker-matrix.json`, and `tests/test_system_design_viewer_browser.py`.
  Exit: Objective Completion Audit diagnostics now include matrix-owned `status=blocked_by_operator_inputs` beside the aggregate operator-input contract.
- [x] System-design viewer renders aggregate operator-input diagnostics.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], generated system-design viewer, UUID `current-blocker-matrix.json`, and `tests/test_system_design_viewer_browser.py`.
  Exit: Objective Completion Audit diagnostics now include `required_fields`, `field_contracts`, and `field_statuses` from the matrix-owned aggregate operator-input readiness payload.
- [x] System-design Current proof gate renders completion recovery.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], generated system-design viewer, UUID `current-blocker-matrix.json`, and `tests/test_system_design_viewer_browser.py`.
  Exit: Objective Completion Audit detail now shows `completion_next_action` plus `completion_next_action_commands` in the top-level Current proof gate, matching the matrix-owned recovery route.
- [x] System-design viewer renders proof-plan sequence and closeout commands.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], generated system-design viewer, UUID `proof-plan.json`, and `tests/test_system_design_viewer_browser.py`.
  Exit: Objective Completion Audit detail now shows the proof-plan operator sequence and per-proof closeout commands, including completion-status recheck and blocker-state update only after approved closure review.
- [x] System-design viewer renders proof-plan recovery authority.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], generated system-design viewer, and `tests/test_system_design_viewer_browser.py`.
  Exit: Objective Completion Audit detail now shows `Proof-plan current gate recovery authority`, routing browser-first architecture reviewers from the compact proof-plan packet to the current matrix packet for current gate and recovery commands.
- [x] HTML proof-plan packet panels render recovery authority.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], proof-readiness HTML, OpenRouter LiveKit voice boundary, publication boundary, and `tests/test_blocker_proof_packets_browser.py`.
  Exit: visible proof-plan operator packet sections now show `current_gate_recovery_authority`, pointing browser-first reviewers to the current matrix packet for current gate and recovery commands.
- [x] README/proof-plan packets name current-gate recovery authority.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], generated proof workspace READMEs, proof-plan packets, proof-readiness/boundary exports, and `tests/test_provider_proof_plan_cli.py`.
  Exit: compact proof-plan and README packet sections now tell operators to open `current_matrix_packet_ref` at `current_matrix_operator_packet_ref` for current gate, completion next action, and recovery commands, avoiding stale duplication of matrix-owned state.
- [x] HTML proof surfaces render packet completion recovery.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], proof-readiness HTML, OpenRouter LiveKit voice boundary, publication boundary, system-design viewer, and browser/static tests.
  Exit: browser-first A2A/review agents see `completion_next_action` and completion recovery commands inside packet current gates across the central proof-readiness, specialized boundary, and generated system-design surfaces.
- [x] Operator proof packet current gates render completion recovery commands.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], UUID `current-blocker-matrix.json`, `current-proof-status.md`, `operator-unblocker-checklist.md`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: each packet-local `current_gate` now includes `completion_next_action` plus nested recovery commands ending with one completion-status recheck, so packet-first A2A/review agents do not need a separate top-level lookup.
- [x] Current-state handoffs render completion recovery commands.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], UUID `current-blocker-matrix.json`, `current-proof-status.md`, `operator-unblocker-checklist.md`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: current-state matrix/status/checklist surfaces now expose `completion.next_action` plus top-level completion recovery commands, ending with one completion-status recheck, while provider-backed live voice is accepted and external publication proof remains blocked.
- [x] Completion-status top-level recovery commands are populated.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], UUID `completion-status.json`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: `provider-proof-completion-status` now exposes top-level `next_action_commands` for unresolved proof records, ending with one completion-status recheck, while accepted proofs are not reopened.
- [x] Browser proof-plan panels render compact field ownership.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], proof-readiness HTML, OpenRouter LiveKit voice boundary, publication boundary, system-design viewer, and browser tests.
  Exit: visible `Proof-plan operator packet` sections now show `Proof-plan field ownership` with `proof_id` and `proof_input_role`, matching compact packet JSON without requiring export inspection.
- [x] Browser proof surfaces render field ownership.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], proof-readiness HTML, OpenRouter LiveKit voice boundary, publication boundary, system-design viewer, and browser tests.
  Exit: visible detail panes now show `Field ownership` and proof-input roles for provider and publication fields, matching the JSON handoff without requiring export inspection.
- [x] Workspace README summaries render field ownership.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], generated proof workspace READMEs, and `tests/test_provider_proof_plan_cli.py`.
  Exit: README aggregate and per-proof operator-input route sections now expose `field_ownership` with `proof_id` and `proof_input_role`, matching status/checklist summary handoffs.
- [x] Status/checklist readiness sections render field ownership.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `current-proof-status.md`, `operator-unblocker-checklist.md`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: aggregate and per-proof Operator Input Readiness sections now expose `field_ownership` with `proof_id` and `proof_input_role`, so text-first agents can route fields without opening packet blocks.
- [x] Markdown operator proof packets render field ownership as nested lines.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], generated proof workspace READMEs, `current-proof-status.md`, `operator-unblocker-checklist.md`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: packet-local `operator_input_readiness.field_ownership` now expands each required field into readable `proof_id` and `proof_input_role` lines instead of inline dictionary text.
- [x] Compact proof-plan operator packets carry direct field ownership.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `proof-plan.json`, proof-readiness/OpenRouter LiveKit voice/publication static exports, system-design viewer, and `tests/test_provider_proof_plan_cli.py`.
  Exit: `proof_plan.operator_proof_packet.operator_input_readiness.field_ownership` now carries direct no-secret proof/role ownership for each remaining operator input, matching the richer readiness/matrix handoffs without requiring agents to traverse `field_statuses`.
- [x] Operator-input readiness owns aggregate field contracts and statuses.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `operator-input-readiness.json`, `current-blocker-matrix.json`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: top-level `required_fields`, `field_contracts`, and `field_statuses` now let broad automation inspect all operator-input contracts and states without proof-by-proof traversal.
- [x] Operator-input readiness owns aggregate blocked fields.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `operator-input-readiness.json`, `current-blocker-matrix.json`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: top-level `operator-input-readiness.json.blocked_fields` now lists every currently blocked operator input in required field order, and the current matrix preserves that source list for broad automation.
- [x] Markdown operator proof packets render retry command arrays as nested lists.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], generated proof workspace READMEs, `current-proof-status.md`, `operator-unblocker-checklist.md`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: `operator_input_readiness.next_action_commands` and `guarded_next_action_commands` now render as copyable command bullets inside each `operator_proof_packet`, instead of one long inline list.
- [x] Operator-input readiness owns per-proof blocked field lists.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `operator-input-readiness.json`, `current-blocker-matrix.json`, `proof-plan.json`, static proof surfaces, system-design viewer, and `tests/test_provider_proof_plan_cli.py`.
  Exit: per-proof `blocked_fields` now comes directly from readiness in required operator-input order and is preserved by the current matrix plus compact proof-plan handoffs, so agents do not infer field order from grouped diagnostics.
- [x] Compact proof-plan operator packets carry operator-input field statuses.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `proof-plan.json`, proof-readiness/OpenRouter LiveKit voice/publication static exports, system-design viewer, and `tests/test_provider_proof_plan_cli.py`.
  Exit: `proof_plan.operator_proof_packet.operator_input_readiness` now carries compact no-secret field groups, field contracts, field statuses, retry commands, blocked fields, and required post-unblock evidence, matching the current-matrix readiness handoff without including secret values.
- [x] Markdown operator proof packets render field statuses as nested lines.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `current-proof-status.md`, `operator-unblocker-checklist.md`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: packet-local `operator_input_readiness.field_statuses` now expands each required field into readable state, issue-code, value-source, next-action, and contract lines instead of a single inline dictionary.
- [x] Operator-input readiness JSON carries per-field status maps.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `operator-input-readiness.json`, `current-blocker-matrix.json`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: each required operator input now has a no-secret `field_statuses` entry with state, issue code, value source, next action, and contract, so automation does not have to infer unblock steps from grouped field lists.
- [x] Operator-input readiness JSON carries field-level contracts.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `operator-input-readiness.json`, `current-blocker-matrix.json`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: per-proof readiness rows now include `field_contracts`, so automation can inspect the no-secret validation contract from JSON without opening Markdown packets.
- [x] Operator proof packets render field-level input validation contracts.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], generated proof workspace READMEs, `current-blocker-matrix.json`, `current-proof-status.md`, `operator-unblocker-checklist.md`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: each live-voice and publication `operator_proof_packet` now names the expected validation contract for its remaining operator-input fields, including readable OpenRouter/LiveKit secret-file paths, OpenRouter LiveKit URL, durable LinkedIn destination, and durable policy/rollback artifacts.
- [x] Markdown status/checklist operator packets render operator-input readiness.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `current-proof-status.md`, `operator-unblocker-checklist.md`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: matrix-derived Markdown `operator_proof_packet` sections include `operator_input_readiness`, so text-first A2A/review agents can see blocked fields, issue codes, next actions, and retry commands from inside the packet block.
- [x] Markdown operator proof packets render packet-local proof-record schema.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], generated proof workspace READMEs, `current-proof-status.md`, `operator-unblocker-checklist.md`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: each Markdown `operator_proof_packet` section includes `proof_record_schema` and `proof_record_required_fields`, so packet-first A2A/review agents can validate record shape without leaving the packet block.
- [x] Markdown status/checklist operator packets render current-state packet refs.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `current-proof-status.md`, `operator-unblocker-checklist.md`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: matrix-derived Markdown `operator_proof_packet` sections include `current_state_packets` plus `current_state_packet_commands`, so text-first A2A/review agents can refresh the matrix/status/checklist triad from inside the packet block.
- [x] Markdown status/checklist operator packets render current gate state.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `current-proof-status.md`, `operator-unblocker-checklist.md`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: matrix-derived Markdown `operator_proof_packet` sections include `current_gate` completion, closure, state-change, and goal-completion flags while proof-plan README packets avoid a non-authoritative empty gate.
- [x] Markdown operator proof packets render closeout evidence refs.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], generated proof workspace `README.md`, `current-proof-status.md`, `operator-unblocker-checklist.md`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: each Markdown `operator_proof_packet` section now includes `completion_evidence_ref` and `closure_evidence_refs`, so text-first A2A/review agents can follow the matrix-owned closeout evidence path without leaving the packet block.
- [x] Markdown operator proof packets render packet-owned capture commands.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], generated proof workspace `README.md`, `current-proof-status.md`, `operator-unblocker-checklist.md`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: each Markdown `operator_proof_packet` section now includes `proof_capture_commands_after_unblock`, so text-first A2A/review agents can follow the matrix-owned post-unblock capture chain without leaving the packet block.
- [x] Markdown operator proof packets render proof IDs and matrix parity refs.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], generated proof workspace `README.md`, `current-proof-status.md`, `operator-unblocker-checklist.md`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: each Markdown `operator_proof_packet` section includes `proof_id`, `matrix_parity_ref`, and `proof_capture_matrix_ref` for both remaining proofs, matching current-matrix packet identity and capture-chain routing while only external publication remains an active proof blocker.
- [x] Generated proof workspace READMEs render current-matrix packet navigation.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], generated proof workspace `README.md`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: README `operator_proof_packet` sections include `current_matrix_packet`, `current_matrix_packet_ref`, `current_matrix_packet_command`, and `current_matrix_operator_packet_ref` for both remaining proofs.
- [x] Generated proof workspace READMEs render proof-plan packet navigation.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], generated proof workspace `README.md`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: README `operator_proof_packet` sections include `proof_plan_packet`, `proof_plan_packet_ref`, `proof_plan_packet_command`, and `proof_plan_operator_packet_ref` for both remaining proofs.
- [x] Markdown operator proof packets render source artifacts.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `current-proof-status.md`, `operator-unblocker-checklist.md`, generated proof workspace `README.md`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: Markdown packet sections list `operator-input-readiness.json`, `current-blocker-matrix.json`, `operator-inputs.template.env`, and `proof-plan.json` under `source_artifacts`.
- [x] Proof-readiness and boundary pages render compact proof-plan packet details.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `agent-studio-proof-readiness.html`, `openrouter-livekit-voice-boundary-map.html`, `agent-studio-publication-boundary-map.html`, and `tests/test_blocker_proof_packets_browser.py`.
  Exit: the proof-plan panels visibly render the compact `Proof-plan operator packet`, `current_matrix_packet_ref`, matrix refresh command, and proof-plan source artifacts.
- [x] System-design viewer renders compact proof-plan provenance in route details.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `output/viewers/agent-studio-system-design-viewer.html`, and `tests/test_system_design_viewer_browser.py`.
  Exit: the Objective Completion Audit detail renders `current_matrix_packet_ref` and proof-plan source artifacts inside each visible `proof_plan_operator_packet` block.
- [x] Compact proof-plan operator packet source artifacts name proof-plan and matrix provenance.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/proof-plan.json`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: `proof_plan.operator_proof_packet.source_artifacts` now lists `proof_plan: proof-plan.json` and `current_blocker_matrix: current-blocker-matrix.json` wherever the compact packet links to the matrix.
- [x] Current-matrix operator packet source artifacts include proof-plan provenance.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-blocker-matrix.json`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: `operator_proof_packets.source_artifacts` now includes `proof_plan: proof-plan.json` wherever the packet links to and can refresh the proof-plan artifact.
- [x] Compact proof-plan operator packets expose the current-matrix refresh command.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/proof-plan.json`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: `proof_plan.operator_proof_packet` now exposes `current_matrix_packet_command` beside matrix refs so plan-first agents can refresh `current-blocker-matrix.json` directly.
- [x] Current-matrix operator packets expose the proof-plan refresh command.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-blocker-matrix.json`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: `operator_proof_packets` now expose `proof_plan_packet_command` beside `proof_plan_packet_ref`, and generated status/checklist/static/viewer packets mirror it where applicable so packet-first agents can refresh `proof-plan.json` directly.
- [x] Current-matrix operator packets reciprocate to proof-plan packets.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-blocker-matrix.json`, `social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/proof-plan.json`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: `operator_proof_packets` now expose `proof_plan_packet`, `proof_plan_packet_ref`, and `proof_plan_operator_packet_ref`; the status packet, checklist, static proof exports, and system-design viewer mirror the reciprocal refs where applicable while provider-backed live voice is accepted and external publication proof remains blocked.
- [x] Kanban names the operator-input retry-chain split.
  Source: `social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-blocker-matrix.json` and [[../wiki/ops/active-codex-context]].
  Exit: board-level blocker tracking distinguishes the report-only operator-input retry chain from the guarded chain, so future continuation turns do not use a failing readiness command when they only need to refresh `operator-input-readiness.json`, `credential-snapshot.json`, `proof-plan.json`, `current-blocker-matrix.json`, `current-proof-status.md`, and `operator-unblocker-checklist.md`.
- [x] Kanban links the current proof status packet.
  Source: `social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-proof-status.md`, `social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-blocker-matrix.json`, and `social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-unblocker-checklist.md`.
  Exit: board-level blocker tracking now points to the generated status, matrix, and operator checklist packets so continuation turns can inspect the live proof blockers without scraping the sprint log.
- [x] UUID provider proof downstream handoff regenerated from refreshed failed-proof state.
  Source: [[Current Sprint]], `social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/`, `src/all_about_llms/cli.py`, and `tests/test_provider_proof_plan_cli.py`.
  Exit corrected 2026-05-24: workspace validation is `valid_workspace`; provider-backed live voice is accepted for OpenRouter `deepseek/deepseek-v4-flash` + LiveKit + Kokoro, while publication remains invalid/blocked for its precise external LinkedIn inputs; downstream completion, closure, blocker-state update, current blocker matrix, and operator checklist remain blocked/no-write with `goal_completion_claimed=false` until external publication proof is accepted.
- [x] Accepted live voice records require required runtime-check/preflight linkage.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, `01-work-tracking/agent-studio-proof-readiness.html`, `02-research/openrouter-livekit-voice-boundary-map.html`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI proof verifies accepted `provider-backed-live-voice-proof` records and hand-edited audit notes fail when `validated_runtime_checks` omits a required runtime check or includes non-generated runtime-check names; record validation now carries the canonical required-check sequence from preflight reports, compact audit notes preserve that list, and proof-plan/static voice surfaces require the same linkage.
- [x] Accepted external publication records require destination/preflight channel linkage.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI proof verifies an accepted `external-publication-proof` record fails with `destination_channel_missing_from_preflight` when `destination_channel` is absent from the linked preflight-validation report's `validated_publish_channels`; compact audit notes now preserve `preflight_validation_report_validated_publish_channels`, and completion-status audit-note parsing requires the same channel linkage before treating a publication note as accepted.
- [x] Publication preflight rejects duplicate, alias-duplicate, blank, or unsupported channel checks.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI proof verifies a ready `publish-readiness.preflight.json` with duplicate `linkedin` channel checks, alias-equivalent `x`/`twitter` checks, or unsupported `mastodon` checks returns `invalid_preflight_artifacts`, emits `publish_channel_duplicate_platform` or `publish_channel_platform_unsupported`, withholds preflight artifact IDs, rejects blank platforms with `publish_channel_platform_missing`, and proof-plan surfaces require one normalized, non-empty supported `publish_channel_checks` entry per channel.
- [x] Live voice preflight rejects duplicate required runtime check IDs.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI proof verifies a duplicate ready `livekit-transport` check cannot mask an earlier blocked check with the same ID; validation emits `voice_runtime_duplicate_check_id`, returns no artifact IDs, redacts token-shaped duplicate IDs from issue paths, and proof-plan surfaces require each required runtime check to be present once and ready.
- [x] Publication proof preflight rejects contradictory channel policy and blocker state.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI proof verifies `validate-provider-proof-preflight-artifacts` keeps policy-review-only `needs_review` publication handoff valid only with the exact single top-level policy-review blocker, empty or policy-review-only channel blockers, at least one channel policy remaining `needs_review`, and no policy-review blocker on acknowledged channels; ready publication evidence now requires every channel `policy_status` to be `acknowledged` and every channel `blocking_issues` list to be empty.
- [x] Provider proof closure-review recording keeps proof-read and review-write targets separate.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, `tests/test_provider_proof_plan_cli.py`, and `Leibniz`.
  Exit: CLI proof verifies `record-provider-proof-closure-review` uses only `--proof-audit-target` or default proof audit targets for completion-status rechecks, while review `--audit-target` paths only select closure-review write destinations.
- [x] Provider proof closure review has a no-secret audit bridge.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI proof verifies `record-provider-proof-closure-review` validates filled review records, appends compact redacted audit notes, refuses invalid reviews without writing, preserves separate proof-audit targets for completion-status rechecks, and keeps `state_change_allowed=false`.
- [x] Provider proof closure review supports rejected reviewer decisions.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, `tests/test_provider_proof_plan_cli.py`, and `Leibniz`.
  Exit: CLI proof verifies rejected closure-review records can be valid when at least one expected review requirement is rejected, while blocker-state updates remain disallowed.
- [x] Provider proof closure review has a no-secret validator.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI proof verifies `validate-provider-proof-closure-review` rechecks accepted completion status, validates reviewer decision, timestamp, accepted proof/source linkage, review requirements, redaction proof, and token-shaped values without changing blocker state; the template exposes the validation command with active audit-target overrides.
- [x] Provider proof closure-review command preserves audit-target overrides.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, `tests/test_provider_proof_plan_cli.py`, and `Leibniz`.
  Exit: CLI proof verifies accepted completion status generated from `--audit-target` overrides emits a reproducible `provider-proof-closure-review-template` command with the same targets, including paths containing spaces.
- [x] Provider proof closure review has a no-secret template command.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI proof verifies `provider-proof-closure-review-template` emits a reviewer-fillable record only after `provider-proof-completion-status` is `required_proofs_accepted`, blocks when accepted proof is missing, keeps `state_change_allowed=false`, and is linked from accepted completion status as the next no-secret review command.
- [x] Provider proof completion status exposes closure-review packet.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI proof verifies `required_proofs_accepted` status includes top-level `next_action=prepare_blocker_closure_review`, no state-changing commands, and a no-secret `closure_review_packet` with accepted record sources, review requirements, and candidate blocker states after reviewer approval while keeping `blocker_state_change_allowed_by_this_command=false`.
- [x] Provider proof completion status exposes next action commands.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI proof verifies blocked completion status includes per-proof `next_action`, `next_action_commands`, and `record_proof_in` so operators can go from missing/invalid proof status to template generation, validation, audit recording, and recheck without reopening separate proof-plan surfaces; placeholder, unsafe, and secret-shaped run ids expose the same payload shape with safe `<run-id>` command substitution, and workspace initialization also sanitizes token-shaped run ids before output.
- [x] Provider proof completion status rejects accepted audit notes with invalid proof fields.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI proof verifies hand-edited accepted audit notes cannot bypass accepted-record validators; invalid live voice or publication fields block as `blocked_by_invalid_accepted_audit_note`, duplicate accepted-note fields are treated as invalid evidence, duplicate secret-shaped values are still caught by the secret scan, missing schema-required audit fields block accepted status, accepted notes must preserve zero-failed validation-summary and redaction-check audit lines, JSON records and audit notes require parseable validation timestamps, unorderable invalid/secret accepted notes cannot be masked by older accepted notes, and proof-level output reports `latest_record_has_invalid_fields` plus `invalid_source_targets`.
- [x] External publication proof rejects cross-channel destination evidence.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI proof verifies accepted `external-publication-proof` records fail validation with `destination_channel_mismatch` when a known platform URL/URN contradicts `destination_channel`, while preserving matching platform URLs, repo-canonical channel aliases, and opaque unknown external evidence.
- [x] External publication proof rejects local/draft destination substitutes.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI proof verifies accepted `external-publication-proof` records fail validation when `durable_platform_id_or_url` is `file://`, localhost, private/link-local/unspecified IPs, filesystem paths, dotless/internal/reserved DNS names, non-proof URL schemes, opaque draft/preview/local/internal marker evidence, or explicit external `/draft` and `/preview` paths, while preserving normal external slugs and opaque platform IDs.
- [x] Provider proof plans require runtime-health voice-edge benchmark evidence.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, proof readiness, OpenRouter LiveKit voice boundary map, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI/browser proof verifies live voice proof plans require `build-runtime-health-ledger --run-id <run-id>`, a same-run `runtime_health_ledger` with `voice-edge-local-benchmark` ready status, proof-record schema fields for `runtime_health_ledger_artifact_id` plus `voice_edge_benchmark_status`, and accepted-record validation rejects contradictory benchmark/live-call/provider fields.
- [x] Provider proof completion status blocks secret-shaped audit notes.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI proof verifies `provider-proof-completion-status` blocks as `blocked_by_secret_shaped_audit_note` when a latest otherwise valid audit note contains token-shaped text, emits `audit_note_secret_shape_detected`, keeps that status ahead of failed/missing proof states, and does not echo the matched value.
- [x] Provider proof completion status requires matching artifact types.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI proof verifies `provider-proof-completion-status` ignores accepted/failed audit notes whose `proof_artifact_type` does not match the selected proof schema.
- [x] Provider proof completion status is self-auditing and status-only.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI proof verifies `provider-proof-completion-status` includes `required_proofs`, `completion_requirements`, `state_change_boundary`, and `blocker_state_change_allowed_by_this_command=false` so accepted-proof status remains separate from blocker-state mutation.
- [x] Provider proof completion status uses validation timestamps for latest-record selection.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI proof verifies `provider-proof-completion-status` prefers parseable `validation_timestamp` values over audit-note file order when choosing the latest accepted/failed proof note, while retaining file order as a tie/fallback.
- [x] Provider proof completion status follows latest valid record.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI proof verifies `provider-proof-completion-status` uses the latest valid accepted/failed audit note per proof/run/readable target, blocks as `blocked_by_latest_failed_proof_record` when a later failed note supersedes an older accepted note, and reports `failed_source_targets`.
- [x] Provider proof completion status requires full target coverage.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI proof verifies `provider-proof-completion-status` blocks as `blocked_by_incomplete_audit_target_coverage` when accepted live voice/publication proof notes are present in one configured readable audit target but missing from another, and reports per-proof `missing_source_targets`.
- [x] Provider proof plans expose completion-status commands.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, proof-readiness/boundary-map exports, and `tests/test_blocker_snapshot_consistency.py`.
  Exit: CLI/browser parity proof verifies `provider-proof-plan`, proof readiness, and the OpenRouter LiveKit voice/publication boundary maps carry `completion_status_commands` that point to `provider-proof-completion-status --run-id <run-id>` after template and record commands.
- [x] Provider proof has a no-secret completion-status checker.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI proof verifies `provider-proof-completion-status` scans configured audit targets for exact valid accepted live voice and publication proof-record notes for a concrete run id, reports missing accepted proof records plus missing/invalid audit targets without changing blocker state, rejects accepted-like malformed markers, and the proof workspace README links the check after record commands.
- [x] Provider proof has a no-secret workspace initializer.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI proof verifies `init-provider-proof-workspace` writes voice/publication proof-record template JSON plus README capture instructions for a concrete run id, writes nothing for placeholder/unsafe run ids, and refuses to overwrite existing target files.
- [x] Provider proof records have no-secret templates.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, `tests/test_provider_proof_plan_cli.py`, and proof-readiness/boundary-map exports.
  Exit: CLI proof verifies `provider-proof-record-template` emits concrete-run-id-only draft records with required fields and post-capture validation keys, placeholder/unsafe run ids return no record, partially filled template placeholders still fail validation, and proof-plan packets expose `template_commands`.
- [x] Provider proof records have a no-secret audit bridge.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, `tests/test_provider_proof_plan_cli.py`, and proof-readiness/boundary-map exports.
  Exit: CLI proof verifies valid accepted/failed proof records can be validated and appended as compact redacted Markdown audit notes to configured vault targets, invalid records and placeholder/unsafe run ids write nothing, and proof-plan packets expose `record_commands` for live voice and publication proof handoff.
- [x] Provider proof records have a no-secret validator.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI helper proof verifies captured live voice or publication proof JSON is validated against the selected proof schema, command run id, outcome, post-capture validation results, and token-shaped value scan without changing blocker state or echoing secrets.
- [x] Provider proof plans carry proof-artifact schemas.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, proof-readiness and boundary-map exports, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI/browser parity proof verifies each remaining blocker proof plan defines the accepted/failed proof record artifact type, allowed outcomes, state field, and required no-secret fields for future live voice or publication proof records.
- [x] Provider proof plans carry success-recording requirements.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, proof-readiness and boundary-map exports, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI/browser parity proof verifies passing live voice or publication proof must record run/check/validation time, artifact ids, passed validation checks, blocker-state update timing, and follow-up closure/linkage before it can clear blocker state.
- [x] Provider proof plans carry failure-recording requirements.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, proof-readiness and boundary-map exports, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI/browser parity proof verifies failed live voice or publication attempts must record run/check time, failed step, redacted provider/platform context, blocked-state preservation, and follow-up task creation instead of clearing blockers.
- [x] Provider proof plans carry post-capture validation checks.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, proof-readiness and boundary-map exports, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI/browser parity proof verifies each remaining blocker proof plan states the validation checks operators must run after capture, including live-call/provider flags, run/session linkage, required timing/evidence, destination ID/URL linkage, and no-secret artifacts.
- [x] Provider proof plans carry proof-linkage requirements.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, proof-readiness and boundary-map exports, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI/browser parity proof verifies live voice proof must link provider-smoke and voice-timing ledgers to the same run/session, and publication proof must link publish-readiness, artifact approval, destination proof, and rollback/postcondition evidence to the same platform ID or URL.
- [x] Provider proof plans name rejected substitutes.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, proof-readiness and boundary-map exports, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI/browser parity proof verifies each proof plan carries `rejected_substitutes` so blocked routes cannot be cleared by credentials, rehearsal, HF text routing, non-live smoke, generic policy acknowledgement, or local draft evidence.
- [x] Provider proof plans expose safe command run ids.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, proof-readiness and boundary-map exports, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI/browser parity proof verifies each proof plan carries `command_run_id` as the accepted concrete run id or substituted `<run-id>`.
- [x] Provider proof plans reject unsafe run ids.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI proof verifies a run id containing shell-control syntax becomes `unsafe_run_id`, remains blocked, and is not emitted into command or preflight text.
- [x] Proof-plan renderers preserve literal placeholders.
  Source: [[Current Sprint]], proof-readiness and boundary-map browser tests, and `Leibniz` review.
  Exit: browser proof verifies visible proof-plan details keep literal `<run-id>` in commands and preflight checks while command/path lists are escaped before HTML insertion.
- [x] Provider proof plans carry preflight checks.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, proof-readiness and boundary-map exports, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI and browser parity proof verify each remaining blocker proof plan includes readiness/policy preflight checks before live voice calls or external destination proof.
- [x] Provider proof plans fail closed on placeholder run ids.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, proof-readiness and boundary-map exports, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI proof verifies configured credential names plus `<run-id>` return `blocked_by_run_id`, and browser parity proof verifies static proof-plan exports carry the same run-id guard fields.
- [x] Provider proof plans carry evidence record targets.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, `agent-studio-proof-readiness.html`, OpenRouter LiveKit voice/publication boundary maps, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI and browser parity proof verify each remaining blocker proof plan includes `record_proof_in` targets for the project audit, active context, and system-design audit mirror, without reading or printing secret values.
- [x] Wiki index exposes proof-plan packet handoff.
  Source: [[Current Sprint]], `wiki/_index.md`, and `tests/test_foundation.py`.
  Exit: foundation proof verifies the wiki index states that proof readiness plus OpenRouter LiveKit voice/publication boundary maps carry proof_plan proof-plan packets matching `provider-proof-plan`.
- [x] MOCs expose proof-plan packet handoff.
  Source: [[Current Sprint]], `Agent Studio MOC.md`, `system_design_vault/MOC.md`, and `tests/test_foundation.py`.
  Exit: foundation proof verifies both MOCs state that proof readiness plus the OpenRouter LiveKit voice/publication boundary maps carry proof_plan proof-plan packets matching `provider-proof-plan`.
- [x] Project vault home exposes proof-plan packet coverage.
  Source: [[Current Sprint]], `agent-studio-vault-home.html`, `tests/test_vault_home_browser.py`, and `tests/test_foundation.py`.
  Exit: browser and foundation proof verify the primary project-vault entry point tells reviewers that proof readiness plus the OpenRouter LiveKit voice/publication boundary maps carry `proof_plan` proof-plan packets.
- [x] Generated system-design viewer carries proof-plan packet state.
  Source: [[Current Sprint]], `output/viewers/agent-studio-system-design.json`, `output/viewers/agent-studio-system-design-viewer.html`, `tests/test_system_design_viewer_browser.py`, and `tests/test_foundation.py`.
  Exit: browser and foundation proof verify the generated Objective Completion Audit detail includes `proof_plan` / `provider-proof-plan` wording, and the embedded viewer projection matches the standalone JSON.
- [x] Proof-plan operator packet handoff added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/proof-plan.json`, `output/viewers/agent-studio-system-design-viewer.html`, `tests/test_blocker_snapshot_consistency.py`, `tests/test_system_design_viewer_browser.py`, and `tests/test_foundation.py`.
  Exit: board-level handoff names the compact `proof_plan.operator_proof_packet` projection and the system-design viewer `proof_plan_operator_packet` route field, preserving the compact provider-proof-plan packet beside the richer current-matrix `operator_proof_packet`.
- [x] Proof-plan operator packet links back to current matrix.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `src/all_about_llms/cli.py`, `social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/proof-plan.json`, `tests/test_provider_proof_plan_cli.py`, `tests/test_blocker_snapshot_consistency.py`, and `tests/test_system_design_viewer_browser.py`.
  Exit: compact proof-plan operator packets carry `current_matrix_packet`, `current_matrix_packet_ref`, and `current_matrix_operator_packet_ref`, so plan-first agents can jump back to the authoritative current-matrix packet without guessing paths.
- [x] System-design home exposes proof-plan packet coverage.
  Source: [[Current Sprint]], `system_design_vault/agent-studio-system-design-home.html`, `tests/test_system_design_vault_home_browser.py`, and `tests/test_foundation.py`.
  Exit: browser and foundation proof verify the system-design-vault home tells reviewers that proof readiness plus the voice/publication boundary maps preserve both credential snapshot exports and `proof_plan` proof-plan packets.
- [x] Proof-plan packets propagate to boundary maps.
  Source: [[Current Sprint]], `02-research/openrouter-livekit-voice-boundary-map.html`, `03-review-packets/agent-studio-publication-boundary-map.html`, `01-work-tracking/agent-studio-proof-readiness.html`, and `tests/test_blocker_snapshot_consistency.py`.
  Exit: browser proof verifies the OpenRouter LiveKit voice and publication boundary exports carry `proof_plan` packets matching proof readiness, so voice/publication boundary reviewers see the same commands, capture requirements, manual publication steps, and unblocking conditions as the CLI-backed proof-readiness view.
- [x] Proof-readiness proof plan matches CLI output.
  Source: [[Current Sprint]], `01-work-tracking/agent-studio-proof-readiness.html`, `src/all_about_llms/cli.py`, and `tests/test_blocker_snapshot_consistency.py`.
  Exit: browser proof verifies each proof-readiness blocker export carries `proof_plan` fields matching `_provider_proof_plan_payload`, including live voice commands, publication manual capture steps, capture requirements, and unblocking conditions.
- [x] Provider proof plan CLI added.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, and `tests/test_provider_proof_plan_cli.py`.
  Exit: CLI helper proof verifies `provider-proof-plan` emits no-secret JSON that combines the current blocker credential snapshot with live voice and external publication proof commands, policy/disclosure capture requirements, and blocked/ready-for-runtime-attempt status without making live calls or reading secret file contents.
- [x] Secret-file presence recognized in blocker snapshots.
  Source: [[Current Sprint]], `src/all_about_llms/orchestration/blocker_credentials.py`, `src/all_about_llms/cli.py`, `tests/test_blocker_credential_classifier.py`, and `tests/test_blocker_credential_snapshot_cli.py`.
  Exit: tests verify `OPENROUTER_API_KEY_FILE`, `LIVEKIT_API_KEY_FILE`, and `LIVEKIT_API_SECRET_FILE` can satisfy credential presence by non-empty file existence without reading or printing file contents, while configured state remains unverified until runtime proof.
- [x] Proof-readiness snapshots match CLI classifier output.
  Source: [[Current Sprint]], `tests/test_blocker_snapshot_consistency.py`, `01-work-tracking/agent-studio-proof-readiness.html`, `02-research/openrouter-livekit-voice-boundary-map.html`, `03-review-packets/agent-studio-publication-boundary-map.html`, and `src/all_about_llms/cli.py`.
  Exit: browser proof verifies proof-readiness `credential_snapshot` records match `_blocker_credential_snapshot_payload` for current `.env.example` placeholder state, including `configured_inputs`, and boundary-map snapshots still propagate the same fields from proof readiness.
- [x] CLI blocker credential snapshot refresh added.
  Source: [[Current Sprint]], `src/all_about_llms/cli.py`, and `tests/test_blocker_credential_snapshot_cli.py`.
  Exit: CLI helper proof verifies `blocker-credential-snapshot` emits JSON snapshots from `.env.example` placeholder names plus process env-name presence without printing values, and reports configured inputs as unverified rather than complete.
- [x] No-secret blocker credential classifier added.
  Source: [[Current Sprint]], `src/all_about_llms/orchestration/blocker_credentials.py`, and `tests/test_blocker_credential_classifier.py`.
  Exit: unit proof verifies the classifier can rebuild live voice and publication blocker snapshots from env-name presence without echoing values, preserves placeholder-only and missing-configuration states, supports `X_ACCESS_TOKEN`/`X_API_KEY` group semantics, and reports runtime configuration as unverified rather than complete.
- [x] Operator proof packets exported for remaining blockers.
  Source: [[Current Sprint]], `tests/test_blocker_proof_packets_browser.py`, `01-work-tracking/agent-studio-proof-readiness.html`, `02-research/openrouter-livekit-voice-boundary-map.html`, and `03-review-packets/agent-studio-publication-boundary-map.html`.
  Exit: browser proof verifies proof readiness and both boundary maps render/export `operator_proof_packet`, require concrete runtime captures, preserve the no-secret-printing rule, and point captured proof back into the project audit, active context, and system-design mirror.
- [x] Blocker acceptance gates exported across proof surfaces.
  Source: [[Current Sprint]], `tests/test_blocker_acceptance_gates_browser.py`, `01-work-tracking/agent-studio-proof-readiness.html`, `02-research/openrouter-livekit-voice-boundary-map.html`, and `03-review-packets/agent-studio-publication-boundary-map.html`.
  Exit: browser proof verifies Live voice and Publication details expose `Acceptance gate`, exported JSON carries `proof_acceptance_gate`, credentials are explicitly not proof, live voice requires same-session runtime evidence, publication requires exact destination evidence, and boundary-map gates match proof readiness.
- [x] Blocker credential snapshot attribution guarded across exports.
  Source: [[Current Sprint]], `tests/test_blocker_snapshot_consistency.py`, `01-work-tracking/agent-studio-proof-readiness.html`, `02-research/openrouter-livekit-voice-boundary-map.html`, and `03-review-packets/agent-studio-publication-boundary-map.html`.
  Exit: browser proof compares proof-readiness credential snapshots with the propagated OpenRouter LiveKit voice and publication boundary exports, requiring shared blocker fields to match and requiring each boundary export to preserve `source_snapshot: "non-secret local classifier"` while citing `agent-studio-proof-readiness`.
- [x] System-design home links blocker boundary maps.
  Source: [[Current Sprint]], `system_design_vault/agent-studio-system-design-home.html`, `tests/test_system_design_vault_home_browser.py`, and `tests/test_foundation.py`.
  Exit: browser proof verifies the system-design-vault home links to the project proof-readiness surface, OpenRouter LiveKit voice boundary map, and publication boundary map, and preserves credential snapshot export copy with `secret_values_printed=false`.
- [x] Voice/publication boundary maps carry credential snapshot evidence.
  Source: [[Current Sprint]], `02-research/openrouter-livekit-voice-boundary-map.html`, `03-review-packets/agent-studio-publication-boundary-map.html`, `tests/test_openrouter_livekit_voice_boundary_browser.py`, and `tests/test_publication_boundary_browser.py`.
  Exit: browser proof filters Proof gate and External proof, verifies each detail pane shows non-secret credential snapshot state, and verifies exported JSON carries `credential_snapshot` with current OpenRouter/LiveKit live-voice input names, publication placeholder input names, canonical LiveKit naming, and `secret_values_printed=false`.
- [x] Proof-readiness credential snapshot export added.
  Source: [[Current Sprint]], `01-work-tracking/agent-studio-proof-readiness.html`, and `tests/test_proof_readiness_browser.py`.
  Exit: browser proof filters the Live voice and Publication blockers, verifies the detail pane shows non-secret credential snapshot state, and verifies the exported JSON carries `credential_snapshot` with placeholder-only input names, generic `LIVEKIT_URL` absence for voice, and `secret_values_printed=false`.
- [x] Provider/publication credential blocker snapshot recorded.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and [[Agent Studio Objective Completion Audit]].
  Exit: non-secret local scan classified required live voice and publication credential names without printing values; the current live-voice path uses `OPENROUTER_API_KEY_FILE`, `OPENROUTER_LIVEKIT_URL`, `LIVEKIT_API_KEY_FILE`, and `LIVEKIT_API_SECRET_FILE`, with generic `LIVEKIT_URL` still treated as non-required legacy absence.
- [x] Topbar Refresh/New source-refresh exclusion proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction starts `Run web research`, waits until source-refresh worker-cycle work has started but not completed, attempts topbar `Refresh` and `New`, proves no manual context-packet refresh starts, and proves the active run remains selected while source refresh is in flight.
- [x] Continue specialists source-refresh boundary proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction rapid-clicks `Continue specialists`, waits until the manual specialist worker cycle has started but not completed, clicks `Run web research`, and proves neither the source-refresh A2A message nor source-refresh worker cycle starts while manual A2A continuation is in flight.
- [x] Feedback Resolve source-refresh boundary proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction rapid-clicks `Resolve` for an open feedback gate, waits until feedback resolution has started but not completed, clicks `Run web research`, and proves neither the source-refresh A2A message nor source-refresh worker cycle starts while feedback resolution is in flight.
- [x] Check setup readiness stale-ownership guards added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `frontend/next-app/tests/voiceProviderReadiness.test.ts`, and `frontend/next-app/components/voice/RealtimeVoicePanel.tsx`.
  Exit: source contract proves setup-check runtime preflight readiness and provider-readiness fanout calls use `shouldApply: isCurrentSetupCheck`, so stale run/check completions cannot repaint readiness.
- [x] Resolver/provider readiness stale-ownership guards added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `frontend/next-app/tests/voiceProviderReadiness.test.ts`, and `frontend/next-app/components/voice/RealtimeVoicePanel.tsx`.
  Exit: source contract proves resolver provider readiness refresh uses `shouldApply: isCurrentSetupAction`, and live proof path runtime preflight uses `shouldApply: isCurrentProofAction`, so stale run/session/action completions cannot repaint readiness.
- [x] Resolve next Run preflight source-refresh boundary added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `frontend/next-app/tests/browser_single_flight.py`, `frontend/next-app/tests/voiceProviderReadiness.test.ts`, and `frontend/next-app/components/voice/RealtimeVoicePanel.tsx`.
  Exit: Chromium-driven real UI interaction clicks resolver `Run preflight`, waits until the full runtime preflight request has started but not completed, clicks `Run web research`, and proves neither the source-refresh A2A message nor source-refresh worker cycle starts while resolver preflight plus setup-proof recording is in flight.
- [x] Voice session Stop source-refresh boundary added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `frontend/next-app/tests/browser_single_flight.py`, `frontend/next-app/tests/voiceCancellation.test.ts`, and `frontend/next-app/components/voice/RealtimeVoicePanel.tsx`.
  Exit: Chromium-driven real UI interaction starts transcript rehearsal, routes a rehearsal turn, starts action-row `Stop`, waits until the session status update has started but not completed, clicks `Run web research`, and proves neither the source-refresh A2A message nor source-refresh worker cycle starts while Stop is in flight.
- [x] Secret-file save source-refresh boundary added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `frontend/next-app/tests/browser_single_flight.py`, `frontend/next-app/tests/voiceProviderReadiness.test.ts`, and `frontend/next-app/components/voice/RealtimeVoicePanel.tsx`.
  Exit: Chromium-driven real UI interaction fills selected-provider `LIVEKIT_API_KEY`, starts `Save locally`, waits until `/api/local-secret-files` has started but not completed, clicks `Run web research`, and proves neither the source-refresh A2A message nor the source-refresh worker cycle starts while the save plus provider-readiness refresh is in flight; refresh failure cannot be mislabeled as a failed secret write.
- [x] Provider endpoint save source-refresh boundary added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `frontend/next-app/tests/browser_single_flight.py`, `frontend/next-app/tests/voiceProviderReadiness.test.ts`, and `frontend/next-app/components/voice/RealtimeVoicePanel.tsx`.
  Exit: Chromium-driven real UI interaction fills a provider endpoint row, starts `Save endpoint`, waits until `/api/local-provider-config` has started but not completed, clicks `Run web research`, and proves neither the source-refresh A2A message nor the source-refresh worker cycle starts while the save plus readiness refresh is in flight.
- [x] Local LiveKit dev setup source-refresh boundary added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `frontend/next-app/tests/browser_single_flight.py`, `frontend/next-app/tests/voiceProviderReadiness.test.ts`, and `frontend/next-app/components/voice/RealtimeVoicePanel.tsx`.
  Exit: Chromium-driven real UI interaction starts `Use local LiveKit dev defaults`, waits until the local config request has started but not completed, clicks `Run web research`, and proves neither the source-refresh A2A message nor the source-refresh worker cycle starts while config plus readiness refresh is in flight; resolver `Configure LiveKit dev` proof recording is skipped when the parent gate denies or the attempt is stale.
- [x] Route rehearsal turn source-refresh boundary added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `frontend/next-app/tests/browser_single_flight.py`, `frontend/next-app/tests/voiceProviderReadiness.test.ts`, and `frontend/next-app/components/voice/RealtimeVoicePanel.tsx`.
  Exit: Chromium-driven real UI interaction starts `Route rehearsal turn`, waits until the transcript rehearsal realtime-turn request has started but not completed, clicks `Run web research`, and proves neither the source-refresh A2A message nor the source-refresh worker cycle starts while the rehearsal turn is in flight.
- [x] Voice follow-up continuation source-refresh boundary added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `frontend/next-app/tests/browser_single_flight.py`, `frontend/next-app/tests/sourceRefreshInteractionContract.test.ts`, `frontend/next-app/tests/runMutationGate.test.ts`, `frontend/next-app/lib/state/runMutationGate.ts`, and `frontend/next-app/app/page.tsx`.
  Exit: Chromium-driven real UI interaction routes a transcript rehearsal turn that creates a voice follow-up worker cycle, then proves `Run web research` cannot create a source-refresh A2A message or source-refresh worker cycle while that follow-up continuation is in flight.
- [x] Runtime preflight single-flight and source-refresh boundary added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `frontend/next-app/tests/browser_single_flight.py`, `frontend/next-app/tests/voiceProviderReadiness.test.ts`, `frontend/next-app/lib/voice/runtimeReadiness.ts`, and `frontend/next-app/components/voice/RealtimeVoicePanel.tsx`.
  Exit: Chromium-driven real UI interaction rapidly clicks `Runtime preflight` and proves one full provider preflight request, then clicks `Run web research` while preflight is in flight and proves neither the source-refresh A2A message nor the source-refresh worker cycle starts; stale direct-preflight success/failure event emission is ownership-guarded.
- [x] Local LiveKit and Gemma/Kokoro process controls single-flight and source-refresh boundary added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `frontend/next-app/tests/browser_single_flight.py`, `frontend/next-app/tests/voiceProviderReadiness.test.ts`, and `frontend/next-app/components/voice/RealtimeVoicePanel.tsx`.
  Exit: Chromium-driven real UI interaction rapidly clicks direct `Stop LiveKit` / `Stop agent` and resolver `Start LiveKit` / `Start agent`, proving one process request per path and proving neither the source-refresh A2A message nor the source-refresh worker cycle starts while local process mutation and resolver proof writing are in flight.
- [x] Provider panel Provider readiness single-flight and source-refresh boundary added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `frontend/next-app/tests/browser_single_flight.py`, `frontend/next-app/tests/voiceProviderReadiness.test.ts`, and `frontend/next-app/components/voice/RealtimeVoicePanel.tsx`.
  Exit: Chromium-driven real UI interaction rapidly clicks the exact provider panel `Provider readiness` control and proves one provider-readiness request, then clicks `Run web research` while provider refresh is in flight and proves neither the source-refresh A2A message nor the source-refresh worker cycle starts; no-run and run-bound stale provider-readiness completions are ownership-guarded.
- [x] Live voice proof path Refresh provider readiness single-flight and source-refresh boundary added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `frontend/next-app/tests/browser_single_flight.py`, `frontend/next-app/tests/voiceProviderReadiness.test.ts`, and `frontend/next-app/components/voice/RealtimeVoicePanel.tsx`.
  Exit: Chromium-driven real UI interaction rapidly clicks the live proof path `Refresh provider readiness` control and proves one provider-readiness request, then clicks `Run web research` while provider refresh is in flight and proves neither the source-refresh A2A message nor the source-refresh worker cycle starts; stale provider-readiness completions are ownership-guarded.
- [x] Resolve next Refresh providers single-flight and source-refresh boundary added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `frontend/next-app/tests/browser_single_flight.py`, `frontend/next-app/tests/voiceProviderReadiness.test.ts`, and `frontend/next-app/components/voice/RealtimeVoicePanel.tsx`.
  Exit: Chromium-driven real UI interaction rapidly clicks `Refresh providers` and proves one provider-readiness refresh plus one durable `refresh_provider_readiness` setup proof, then clicks `Run web research` while provider refresh is in flight and proves neither the source-refresh A2A message nor the source-refresh worker cycle starts.
- [x] Check setup blocks source-refresh browser proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction starts `Check setup`, waits until the runtime-preflight branch has started but not completed, clicks `Run web research`, and proves neither the source-refresh A2A message nor the source-refresh worker cycle starts while voice setup fanout is in flight.
- [x] Timing ledger blocks source-refresh browser proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction starts `Timing ledger`, waits until the realtime voice timing-ledger request has started but not completed, clicks `Run web research`, and proves neither the source-refresh A2A message nor the source-refresh worker cycle starts while timing proof writing is in flight.
- [x] Runtime smoke blocks source-refresh browser proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction starts `Runtime smoke`, waits until the provider-smoke request has started but not completed, clicks `Run web research`, and proves neither the source-refresh A2A message nor the source-refresh worker cycle starts while voice proof writing is in flight.
- [x] Join voice room blocks source-refresh browser proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction starts `Join voice room`, waits until the provider-backed realtime-session request has started but not completed, clicks `Run web research`, and proves neither the source-refresh A2A message nor the source-refresh worker cycle starts while the LiveKit session grant is in flight.
- [x] Always-on Stop blocks source-refresh browser proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction starts the always-on rail `Stop`, waits until the worker-profile stop request has started but not completed, clicks `Run web research`, and proves neither the source-refresh A2A message nor the source-refresh worker cycle starts while always-on stop is in flight.
- [x] Stop runner blocks source-refresh browser proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction starts `Stop runner`, waits until the background runner stop request has started but not completed, clicks `Run web research`, and proves neither the source-refresh A2A message nor the source-refresh worker cycle starts while runner stop is in flight.
- [x] Start runner blocks source-refresh browser proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction starts `Start runner`, waits until the background runner start request has started but not completed, clicks `Run web research`, and proves neither the source-refresh A2A message nor the source-refresh worker cycle starts while runner start is in flight.
- [x] Media plan blocks source-refresh browser proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction starts `Media plan`, waits until the media-plan request has started but not completed, clicks `Run web research`, and proves neither the source-refresh A2A message nor the source-refresh worker cycle starts while media planning is in flight.
- [x] Growth package blocks source-refresh browser proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction starts `Growth package`, waits until the growth-package request has started but not completed, clicks `Run web research`, and proves neither the source-refresh A2A message nor the source-refresh worker cycle starts while packaging is in flight.
- [x] Generate blocks source-refresh browser proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction starts `Generate`, waits until the conversation-turn request has started but not completed, clicks `Run web research`, and proves neither the source-refresh A2A message nor the source-refresh worker cycle starts while generation is in flight.
- [x] Publish check blocks source-refresh browser proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction starts `Publish check`, waits until the publish-readiness request has started but not completed, clicks `Run web research`, and proves neither the source-refresh A2A message nor the source-refresh worker cycle starts while publish readiness is in flight.
- [x] Send revision blocks source-refresh browser proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction starts `Send revision`, waits until the revision-loop request has started but not completed, clicks `Run web research`, and proves neither the source-refresh A2A message nor the source-refresh worker cycle starts while revision is in flight.
- [x] Start always-on blocks source-refresh browser proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction starts `Start always-on`, waits until the always-on launch request has started but not completed, clicks `Run web research`, and proves neither the source-refresh A2A message nor the source-refresh worker cycle starts while launch is in flight.
- [x] Run pulse blocks source-refresh browser proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction starts `Run pulse`, waits until the worker-profile heartbeat request has started but not completed, clicks `Run web research`, and proves neither the source-refresh A2A message nor the source-refresh worker cycle starts while the heartbeat is in flight.
- [x] Check due work blocks source-refresh browser proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction starts `Check due work`, waits until the run-scoped scheduler request has started but not completed, clicks `Run web research`, and proves neither the source-refresh A2A message nor the source-refresh worker cycle starts while the scheduler pass is in flight.
- [x] Always-on pulse and scheduler browser proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction rapidly double-clicks `Run pulse` and proves exactly one worker-profile heartbeat request plus creator-facing completion copy, then rapidly double-clicks `Check due work` and proves exactly one run-scoped scheduler request with `run_id`, `execution_mode=autonomous_pass`, and `max_profiles=10`.
- [x] Long-running stop controls browser proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction rapidly double-clicks `Stop runner` after the background runner starts and proves exactly one stop request plus creator-facing stopped copy, then rapidly double-clicks the always-on rail `Stop` control and proves exactly one worker-profile stop request plus creator-facing stopped copy.
- [x] Activity retry blocks source-refresh browser proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction starts `Queue and run`, waits until the targeted retry worker cycle has started but not completed, clicks `Run web research`, and proves neither the source-refresh A2A message nor the source-refresh worker cycle starts during or shortly after the targeted retry cycle.
- [x] Planned-agent execution blocks source-refresh browser proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction starts `Run next steps`, waits until the planned worker cycle has started but not completed, clicks `Run web research`, and proves neither the source-refresh A2A message nor source-refresh worker cycle starts while planned agents are running.
- [x] Work-plan planning blocks source-refresh browser proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction starts `Suggest next step`, waits until work-plan planning has started but not completed, clicks `Run web research`, and proves neither the source-refresh A2A message nor source-refresh worker cycle starts while planning is in flight.
- [x] Source-refresh blocks production browser proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction reruns `Run web research`, waits until the source-refresh worker cycle has started but not completed, clicks `Growth package`, and proves no growth-package request is sent while source quality work is in flight.
- [x] Production packaging browser single-flight and cross-action proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction rapidly double-clicks `Growth package` and `Media plan`, proving exactly one growth-package request and one media-production request with the expected creator packaging payloads; the same browser smoke also proves `Growth package` blocks `Media plan`, and `Media plan` blocks `Publish check`, while delayed requests are still in flight.
- [x] Provider-backed Join voice room browser proof and cleanup hardening added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], `frontend/next-app/tests/browser_single_flight.py`, and `frontend/next-app/tests/voiceProviderReadiness.test.ts`.
  Exit: Chromium-driven real UI interaction rapidly double-clicks `Join voice room` after mocked full provider readiness and proves exactly one provider-backed LiveKit realtime-session request plus one cleanup status update after blocked join; stale starts and stale post-join completions end their durable sessions, and cleanup failures retain local session state so another Join cannot hide an active backend session.
- [x] Live voice Interrupt/Stop single-flight controls hardened.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/voiceCancellation.test.ts`.
  Exit: rapid duplicate `Interrupt` and `Stop` actions are blocked before async LiveKit/backend realtime-control calls; Interrupt requires ready active-session ownership before publishing controls; Stop invalidates pending interrupt ownership; Start/run-change/unmount clear both control guards; final `Leibniz` review found no material issues.
- [x] Cockpit walkthrough realtime provider-turn ownership hardened.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `tests/test_api_contracts.py`.
  Exit: selected-provider realtime proof requires a routed/recorded turn event whose `realtime_session_id` matches an active, unexpired selected provider-backed session; rehearsal, ended-session, and expired-session turns remain generic realtime evidence but cannot clear `provider_backed_realtime_turn:<provider>`.
- [x] Cockpit walkthrough feedback-loop gate hardened.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `tests/test_api_contracts.py`.
  Exit: routed demo feedback gates are required walkthrough `needs_review` evidence, not optional noise; the ledger and endpoint response expose open/routed/unresolved counts, `unresolved_feedback_items`, and `feedback_routed` linkage.
- [x] Live text-turn duplicate-submit and pre-send ownership hardened.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/voiceLiveTextTurn.test.ts`.
  Exit: source-contract regression proves the live text-turn form has a synchronous submit gate before LiveKit send, run/session/token ownership, invalidation on run change/Start/Stop/unmount, and a current-owner recheck after optional interrupt before publishing `sendTranscriptTurn`.
- [x] Transcript rehearsal turn browser single-flight proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction rapidly double-clicks `Route rehearsal turn` after a dry-run rehearsal session exists and proves exactly one non-production realtime-turn request with rehearsal-only metadata; the product voice panel uses a synchronous rehearsal-turn gate, active-session route gate, and run/session/token completion ownership before routing.
- [x] Transcript rehearsal start browser single-flight proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction switches Runtime to `Transcript rehearsal`, rapidly double-clicks `Start transcript rehearsal`, and proves exactly one dry-run realtime-session request with `transport_framework=local_rehearsal` and `dry_run=true`; the product voice panel uses a synchronous start-action gate before realtime-session API work.
- [x] Voice proof-action browser single-flight proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction rapidly double-clicks `Runtime smoke` and proves exactly one non-live provider-smoke request with `execute_live_calls=false`, rapidly double-clicks `Timing ledger` and proves exactly one realtime timing-ledger request with `event_limit=500`, then cross-clicks both proof buttons in both orders to prove the shared proof-action gate blocks overlap.
- [x] Voice setup check browser single-flight proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction rapidly double-clicks `Check setup` after a voice-first run exists and proves the browser records exactly one durable voice setup proof after one LiveKit process refresh, one voice-agent process refresh, one provider-readiness refresh, one runtime preflight, and one voice-agent presence check.
- [x] Runtime preflight browser single-flight proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction rapidly double-clicks `Runtime preflight` after a voice-first run exists and proves the browser sends exactly one readiness request carrying LiveKit, OpenRouter dialogue, Kokoro TTS, Rust edge, and agent preflight flags.
- [x] Voice-run create browser single-flight proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction rapidly double-clicks `Create voice run` on the no-run Live Voice panel and proves the browser creates exactly one voice-mode `POST /api/runs` payload with OpenRouter DeepSeek/LiveKit/Kokoro provenance, refreshes the same run context, hides the no-run starter, and binds the next Generate turn to that run.
- [x] Activity retry browser single-flight proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction renders a failed specialist task in `Needs attention`, rapidly double-clicks `Queue and run`, and proves the browser creates exactly one retry authorization plus one targeted retry worker cycle for the retried message id.
- [x] Publication boundary browser proof added.
  Source: [[Current Sprint]], [[../03-review-packets/Feedback Inbox]], [[Agent Studio Objective Completion Audit]], and `tests/test_publication_boundary_browser.py`.
  Exit: Chromium opens `03-review-packets/agent-studio-publication-boundary-map.html`, filters to `External proof`, `Non-live smoke`, `Policy review`, and `Rollback`, and proves the exported boundary packet preserves `external-publication-proof`, `non-live-channel-smoke`, `publish_channel_checks`, `missing_publish_channel_credentials`, `publish_channel_policy_review_required`, `durable platform ID or URL`, destination credential names, exact destination policy review, and rollback/correction evidence without treating non-live smoke as real API publish proof.
- [x] OpenRouter LiveKit voice boundary browser proof added.
  Source: [[Current Sprint]], [[../02-research/Realtime Voice Architecture - Gemma Kokoro LiveKit Rust Python]], and `tests/test_openrouter_livekit_voice_boundary_browser.py`.
  Exit: Chromium opens `02-research/openrouter-livekit-voice-boundary-map.html`, filters to `Current`, `OpenRouter`, `LiveKit`, `Kokoro TTS`, `Rust edge`, `Proof gate`, and `Legacy`, and proves the exported boundary packet preserves the current OpenRouter `deepseek/deepseek-v4-flash` + LiveKit + Kokoro path, required OpenRouter/LiveKit input names, and accepted-proof-record evidence while marking Gemma/HF/Gamma/MLX as legacy/non-default.
- [x] Feedback loop map browser proof added.
  Source: [[Current Sprint]], [[../03-review-packets/Feedback Inbox]], and `tests/test_feedback_loop_map_browser.py`.
  Exit: Chromium opens `03-review-packets/agent-studio-feedback-loop-map.html`, filters to `Guardrails` and `Publish gate`, and proves the exported feedback-loop packet preserves `feedback_resolution_ledger`, accepted/revised/held/rejected outcomes, failed linked task ids, held-until-review policy, `publish_readiness_checked`, unsupported claims, and external-publication blocker copy.
- [x] A2A map browser proof added.
  Source: [[Current Sprint]], [[../00-system-design/HLD - Agent Studio]], and `tests/test_a2a_map_browser.py`.
  Exit: Chromium opens `00-system-design/agent-studio-a2a-map.html`, filters to `Public boundary` and `Repair`, and proves the exported A2A packet preserves `/.well-known/agent-card.json`, `/api/a2a`, `fullA2AProtocolServer=false`, JSON/text HTTP+JSON scope, retry/dependency-repair routes, and `a2a_graph_blocked` evidence.
- [x] Proof readiness browser proof added.
  Source: [[Current Sprint]], [[Agent Studio Objective Completion Audit]], and `tests/test_proof_readiness_browser.py`.
  Exit: Chromium opens `01-work-tracking/agent-studio-proof-readiness.html`, filters to `Live voice` and `Publication`, and proves the exported blocker packet preserves `provider-backed-live-voice-proof`, `external-publication-proof`, required OpenRouter/LiveKit and publication input names, timing/publication evidence, and blocked status.
- [x] Skill matrix browser proof added.
  Source: [[Current Sprint]], [[../00-system-design/Agent Roster and Responsibilities]], and `tests/test_skill_matrix_browser.py`.
  Exit: Chromium opens `00-system-design/agent-studio-skill-matrix.html`, filters to `Guardrails`, and proves the exported packet preserves `agent-studio-guardrails-review`, `feedback_resolution_ledger`, guardrail/reviewer agents, and the source `SKILL.md` path.
- [x] System-design-vault browser index proof added.
  Source: [[Current Sprint]] and `tests/test_system_design_vault_home_browser.py`.
  Exit: Chromium opens `system_design_vault/agent-studio-system-design-home.html` and verifies links to the objective-audit mirror, Gemma/realtime sources, production canon, and source map while preserving blocker copy.
- [x] Vault home generated-viewer navigation proof added.
  Source: [[Current Sprint]] and `tests/test_vault_home_browser.py`.
  Exit: Chromium opens the vault home, follows the generated Memory OS and System Design Viewer links, and verifies the destination headings/content.
- [x] Retrieval research browser filter proof added.
  Source: [[Current Sprint]] and `tests/test_retrieval_research_browser.py`.
  Exit: Chromium opens the Retrieval Quality Research artifact, filters to `Graph`, hides retrieval/reranking/evaluation cards, and preserves the count plus summary copy for the visible graph research cards.
- [x] HLD/LLD design-review browser interaction proof added.
  Source: [[Current Sprint]] and `tests/test_hld_lld_viewer_browser.py`.
  Exit: Chromium opens the static HLD/LLD viewer, saves a high-priority Retrieval comment from `Codex Browser Proof`, verifies the rendered comment references the Retrieval Intelligence Agent, and proves the exported comment packet preserves `agent-studio-hld-lld`, source, target, priority, author, and routing action.
- [x] Work tracker browser interaction proof added.
  Source: [[Current Sprint]] and `tests/test_work_tracker_browser.py`.
  Exit: Chromium opens the static work tracker, advances `Functional Content Studio Cockpit` from `in_progress` to `blocked`, and proves the exported tracker packet preserves `agent-studio-work-tracker`, the updated item status, and the requested planning action.
- [x] Generated Memory OS viewer browser interaction proof added.
  Source: [[Current Sprint]] and `tests/test_memory_os_viewer_browser.py`.
  Exit: Chromium opens the static Memory OS viewer, filters to the `Output Memory` tier, promotes that visible tier into the selected detail pane, preserves the generated-output authority question, and the HTML-embedded Memory OS JSON matches the standalone projection.
- [x] Work-plan execution browser single-flight proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction rapidly double-clicks `Run next steps` after `Suggest next step` and proves the browser creates exactly one work-plan materialization, one bounded planned worker cycle, and one post-run next-action refresh.
- [x] Generated system-design viewer browser interaction proof added.
  Source: [[Current Sprint]] and `tests/test_system_design_viewer_browser.py`.
  Exit: Chromium opens the static system-design viewer, filters for `external publication proof`, shows only the `Objective Completion Audit` runtime component, promotes that visible node into the selected detail pane, and preserves the `Do not call the goal complete` blocker copy.
- [x] Source-refresh browser single-flight proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction keeps an unresolved search-seed claim visible, rapidly double-clicks `Run web research`, and proves the browser creates exactly one A2A source-refresh message plus one bounded Web Research / Claim Verification worker cycle.
- [x] Always-on/background-runner browser status proof added.
  Source: [[Current Sprint]], [[../wiki/ops/active-codex-context]], and `frontend/next-app/tests/browser_single_flight.py`.
  Exit: Chromium-driven real UI interaction clicks `Start always-on` and `Start runner` against stale backend summary fixtures, then proves the status strip shows `Always-on studio`, `Creator always-on studio`, and `Background runner` copy while hiding raw `Autopilot` / `local scheduler` wording.
- [x] Objective completion audit projected into generated system-design viewer.
  Source: [[Current Sprint]], [[Agent Studio Objective Completion Audit]], and `output/viewers/agent-studio-system-design-viewer.html`.
  Exit: generated system-design JSON and HTML projection include the `Objective Completion Audit` component, list `01-work-tracking/Agent Studio Objective Completion Audit.md` in `canonical_sources`, and preserve the live voice / external publication proof blockers as viewer-visible current focus.
- [x] Objective completion audit added.
  Source: [[Current Sprint]], [[Agent Studio Objective Completion Audit]], and `system_design_vault/04-agent-studio-implications/agent-studio-objective-completion-audit.md`.
  Exit: active objective is mapped requirement-by-requirement to current proof, caveats, blockers, and next executable slices; system-design-vault mirror preserves source attribution back to the project vault; foundation checks prevent the audit links from drifting.
- [x] Generated system-design viewer projection refreshed.
  Source: [[Current Sprint]] and `output/viewers/agent-studio-system-design-viewer.html`.
  Exit: generated JSON and embedded HTML viewer data are dated `2026-05-19`, include the `Always-On Activity Rail` component, expose `Always-on studio`, `Specialist pulse`, and `Background runner` language, have exact standalone/embedded projection equality coverage, and the active context no longer carries stale creator-facing `Local scheduler` proof wording.
- [x] LLD background-runner product-language contract synchronized.
  Source: [[Current Sprint]], [[../00-system-design/LLD - Agent Studio]], and `system_design_vault/04-agent-studio-implications/LLD - Agent Studio System Design.md`.
  Exit: both LLDs say the creator Activity rail shows `Background runner` status while internal scheduler/autopilot terms remain implementation details, and the foundation regression prevents the stale `Local scheduler` status contract from returning.
- [x] Creator-visible always-on/background-runner copy tightened.
  Source: [[Current Sprint]] and [[../wiki/ops/active-codex-context]].
  Exit: page-level busy labels, action summaries, fallback errors, raw backend result summaries, and the default profile name use `Always-on studio`, `Specialist pulse`, and `Background runner` language instead of visible `Autopilot` / `local scheduler` copy, and the frontend source/AppShell contracts prevent those stale creator-surface strings from returning.
- [x] Source-refresh same-run mutation gate hardened.
  Source: [[Current Sprint]] and [[../wiki/ops/active-codex-context]].
  Exit: `Run web research` owns a synchronous source-refresh action gate, `runMutationGate` treats source refresh as an in-flight same-run mutation, overlapping same-run mutation handlers reject before mutating APIs, rapid browser double-click proof creates one backend action, and `Leibniz` found no actionable findings.
- [x] Non-live publish-channel credential and policy smoke added.
  Source: [[Current Sprint]].
  Exit: publish-readiness proof distinguishes missing credentials from policy-review acknowledgement, normalizes known platform aliases, blocks unsupported channels, covers direct selected post/reel platform metadata, exposes non-secret channel checks for every requested platform, prevents credential-value echoes in readiness/event surfaces, and passed `Leibniz` review with no actionable findings.
- [x] Browser-level single-flight interaction coverage added.
  Source: [[Current Sprint]] and [[../wiki/ops/active-codex-context]].
  Exit: Chromium-driven real UI interaction rapidly double-clicks Generate, Suggest next step, Publish check, and Send revision while mocked API calls are delayed, proving only one backend action is created for each guarded path.
- [x] Compact Kanban handoff added to active Codex context.
  Source: [[../wiki/ops/active-codex-context]].
  Exit: future turns can locate the next board item, blockers, and review trigger from the compact context without scanning the full sprint log.
- [x] Guardrails skill aligned with feedback outcome ledger semantics.
  Source: [[../wiki/ops/active-codex-context]].
  Exit: skill contract requires `feedback_resolution_ledger`, accepted/revised/held/rejected outcomes, held status for failed or canceled linked tasks, and `Leibniz` reported no actionable findings.
- [x] Feedback outcome analytics added to the resolution ledger.
  Source: [[../03-review-packets/Feedback Inbox]].
  Exit: ledger reports accepted, revised, held, and rejected buckets; entries carry per-feedback outcomes; pending, blocked, failed, or canceled linked work remains held; artifact/event payloads preserve the same summary.
- [x] Vault-only Kanban tracking artifact added.
  Source: current implementation slice.
  Exit: foundation regression proves the note exists, is linked from the MOC and wiki index, and stays outside product/planning HTML.
- [x] Always-on launch/stop single-flight ownership hardened.
  Source: [[Current Sprint]].
- [x] Standalone interactive HTML run-note secret hardening completed.
  Source: [[Current Sprint]].
- [x] Feedback-loop action single-flight ownership hardened.
  Source: [[Current Sprint]].
- [x] Production action single-flight ownership hardened.
  Source: [[Current Sprint]].
- [x] Stale busy-state cleanup and compose submit gate hardened.
  Source: [[Current Sprint]].
- [x] Hosted Kokoro and Gemma voice runtime preflights added.
  Source: [[Current Sprint]].
- [x] Provider proof publication summary canonicality hardened.
  Source: [[Current Sprint]].
  Exit: accepted external publication JSON records and compact audit notes reject unsupported, duplicate, alias-form, and blank-padded `validated_publish_channels` summaries before destination linkage can count.
- [x] Static operator-input field-status parity added.
  Source: [[Current Sprint]] and `tests/test_blocker_snapshot_consistency.py`.
  Exit: proof-readiness, OpenRouter LiveKit voice boundary, and publication boundary static packets export/render current-matrix field contracts and per-field statuses; escalated browser/static/foundation verification passed with `253 passed`.
- [x] System-design viewer field-status parity added.
  Source: [[Current Sprint]], `output/viewers/agent-studio-system-design.json`, `output/viewers/agent-studio-system-design-viewer.html`, and `tests/test_system_design_viewer_browser.py`.
  Exit: Objective Completion Audit routes now export/render field contracts and per-field statuses; viewer checks passed with `2 passed`, combined viewer/static/foundation checks passed with `32 passed`, and provider-proof CLI passed with `223 passed`.
- [x] Workspace README field-status parity added.
  Source: [[Current Sprint]], generated provider proof workspace READMEs, and `tests/test_provider_proof_plan_cli.py`.
  Exit: README `operator_proof_packet` blocks now include per-field operator-input readiness statuses; focused README checks passed with `2 passed`, provider-proof CLI passed with `223 passed`, and combined viewer/static/foundation checks passed with `32 passed`.
- [x] Aggregate operator-input field groups added.
  Source: [[Current Sprint]], generated provider proof readiness/matrix packets, and `tests/test_provider_proof_plan_cli.py`.
  Exit: readiness and matrix packets expose aggregate configured, missing, placeholder, invalid, and unavailable secret-file field groups; focused checks passed with `3 passed`, provider-proof CLI passed with `223 passed`, and static/viewer parity passed with `9 passed`.
- [x] Markdown aggregate operator-input groups added.
  Source: [[Current Sprint]], generated current status/checklist packets, and `tests/test_provider_proof_plan_cli.py`.
  Exit: current proof status and operator unblocker checklist render top-level configured fields plus aggregate missing/placeholder/invalid/unavailable groups; focused Markdown checks passed with `2 passed`, and provider-proof CLI passed with `223 passed`.
- [x] System-design viewer aggregate readiness diagnostics added.
  Source: [[Current Sprint]], `output/viewers/agent-studio-system-design.json`, `output/viewers/agent-studio-system-design-viewer.html`, and `tests/test_system_design_viewer_browser.py`.
  Exit: Objective Completion Audit diagnostics expose aggregate blocked/configured fields and grouped readiness in the interactive viewer; focused viewer checks passed with `2 passed`, static/viewer parity passed with `9 passed`, and provider-proof CLI passed with `223 passed`.
- [x] Workspace README aggregate readiness added.
  Source: [[Current Sprint]], generated provider proof workspace READMEs, and `tests/test_provider_proof_plan_cli.py`.
  Exit: proof workspace READMEs render aggregate configured fields plus grouped missing/placeholder/invalid/unavailable inputs before per-proof routes; focused README/workspace validation passed with `3 passed`, and provider-proof CLI passed with `223 passed`.
- [x] Per-proof configured-field parity added.
  Source: [[Current Sprint]], generated matrix/proof-plan/status/checklist/README/static/viewer packets, and `tests/test_provider_proof_plan_cli.py`.
  Exit: readiness proof rows, operator proof packets, static proof pages, and system-design viewer routes preserve per-proof `configured_fields`; focused packet/viewer checks passed with `4 passed`, static/viewer suites passed with `11 passed`, and provider-proof CLI passed with `223 passed`.
- [x] Per-proof required-field parity added.
  Source: [[Current Sprint]], generated matrix/proof-plan/status/checklist/README/static/viewer packets, and `tests/test_provider_proof_plan_cli.py`.
  Exit: readiness proof rows, operator proof packets, static proof pages, and system-design viewer routes preserve per-proof `required_fields`; focused checks passed with `5 passed`, provider-proof CLI passed with `223 passed`, and static/viewer suites passed with `11 passed`.
- [x] Compact Markdown required/configured field parity added.
  Source: [[Current Sprint]], generated current status/checklist packets, and `tests/test_provider_proof_plan_cli.py`.
  Exit: compact per-proof readiness sections in `current-proof-status.md` and `operator-unblocker-checklist.md` list `required_fields` and `configured_fields` alongside blocked fields and retry commands; focused Markdown checks passed with `2 passed`, and provider-proof CLI passed with `223 passed`.
- [x] Aggregate Markdown required-field parity added.
  Source: [[Current Sprint]], generated current status/checklist packets, and `tests/test_provider_proof_plan_cli.py`.
  Exit: aggregate operator-input readiness in `current-proof-status.md` and `operator-unblocker-checklist.md` now lists required fields before configured fields; focused Markdown checks passed with `2 passed`, and provider-proof CLI passed with `223 passed`.
- [x] Aggregate Markdown field contract/status parity added.
  Source: [[Current Sprint]], generated current status/checklist packets, and `tests/test_provider_proof_plan_cli.py`.
  Exit: aggregate operator-input readiness in `current-proof-status.md` and `operator-unblocker-checklist.md` now renders field contracts and field statuses before per-proof routes; focused Markdown checks passed with `2 passed`, and provider-proof CLI passed with `223 passed`.
- [x] Per-proof Markdown field contract/status parity added.
  Source: [[Current Sprint]], generated current status/checklist packets, and `tests/test_provider_proof_plan_cli.py`.
  Exit: compact per-proof readiness routes in `current-proof-status.md` and `operator-unblocker-checklist.md` now render field contracts and field statuses; focused Markdown checks passed with `2 passed`, and provider-proof CLI passed with `223 passed`.
- [x] Workspace README aggregate field parity added.
  Source: [[Current Sprint]], generated provider proof workspace READMEs, and `tests/test_provider_proof_plan_cli.py`.
  Exit: proof workspace READMEs now render aggregate required fields, field contracts, and field statuses alongside configured fields and grouped diagnostics; focused README checks passed with `2 passed`, and provider-proof CLI passed with `223 passed`.
- [x] Workspace README per-proof route field parity added.
  Source: [[Current Sprint]], generated provider proof workspace READMEs, and `tests/test_provider_proof_plan_cli.py`.
  Exit: README per-proof route-command blocks now render required/configured fields plus field contracts/statuses before retry commands; focused README checks passed with `2 passed`, and provider-proof CLI passed with `223 passed`.
- [x] Workspace README per-proof route state parity added.
  Source: [[Current Sprint]], generated provider proof workspace READMEs, and `tests/test_provider_proof_plan_cli.py`.
  Exit: README per-proof route-command blocks now render status, checked_at, evidence ref, next action, and effective blocked exit code before fields and retry commands; focused README checks passed with `2 passed`, and provider-proof CLI passed with `223 passed`.
- [x] Operator input template contract handoff added.
  Source: [[Current Sprint]], generated `operator-inputs.template.env` files, and `tests/test_provider_proof_plan_cli.py`.
  Exit: operator input templates now include no-secret contract and value-source comments for every remaining input field; focused template checks passed with `2 passed`, and provider-proof CLI passed with `223 passed`.
- [x] Workspace README blocked-field parity added.
  Source: [[Current Sprint]], generated provider proof workspace READMEs, and `tests/test_provider_proof_plan_cli.py`.
  Exit: README aggregate readiness and per-proof route-command blocks now render blocked fields before retry commands; focused README checks passed with `2 passed`, and provider-proof CLI passed with `223 passed`.
- [x] Operator input template status handoff added.
  Source: [[Current Sprint]], generated `operator-inputs.template.env` files, and `tests/test_provider_proof_plan_cli.py`.
  Exit: operator input templates now include no-secret template state, issue code, and next-action comments for every remaining input field; focused template checks passed with `2 passed`, and provider-proof CLI passed with `223 passed`.
- [x] Operator input template proof ownership handoff added.
  Source: [[Current Sprint]], generated `operator-inputs.template.env` files, and `tests/test_provider_proof_plan_cli.py`.
  Exit: operator input templates now include no-secret proof id and proof-input role comments for every remaining input field; focused template checks passed with `2 passed`, and provider-proof CLI passed with `223 passed`.
- [x] Operator input readiness proof ownership handoff added.
  Source: [[Current Sprint]], `operator-input-readiness.json`, generated proof/static/viewer packets, `tests/test_provider_proof_plan_cli.py`, `tests/test_blocker_snapshot_consistency.py`, `tests/test_blocker_proof_packets_browser.py`, and `tests/test_system_design_viewer_browser.py`.
  Exit: field-status JSON now carries proof id and proof-input role through the blocker matrix, proof-readiness HTML, voice/publication boundary maps, and system-design viewer; focused checks passed with `2 passed`, provider-proof CLI passed with `223 passed`, and escalated static/viewer parity passed with `11 passed`.
- [x] Operator input direct field ownership map added.
  Source: [[Current Sprint]], `operator-input-readiness.json`, generated proof/static/viewer packets, `tests/test_provider_proof_plan_cli.py`, `tests/test_blocker_snapshot_consistency.py`, `tests/test_blocker_proof_packets_browser.py`, and `tests/test_system_design_viewer_browser.py`.
  Exit: aggregate and per-proof `field_ownership` maps now propagate through the blocker matrix, proof-readiness HTML, voice/publication boundary maps, and system-design viewer; provider-proof CLI passed with `223 passed`, and escalated static/viewer parity passed with `11 passed`.

## Review Watch

- [x] Review-watch heartbeat alignment current.
  Source: `vault-sync-subagent` heartbeat automation and standing reviewer `019e3899-5ab3-7171-9d3c-32e7c57bbde7`.
  Scope: latest check of the A2A skill-invocation durable event redaction for `agent_skill_invocation_recorded`.
  Exit: review request was sent to Leibniz; no Critical/Important finding or blocker was returned, and no material finding needs surfacing.
- [x] Leibniz latest status: no Critical/Important findings.
  Source: standing reviewer `019e3899-5ab3-7171-9d3c-32e7c57bbde7`.
  Scope: A2A skill-invocation durable event redaction for `agent_skill_invocation_recorded`.
  Exit: `public_a2a_skill_invocation_event_payload` preserves skill-use observability while redacting token-shaped task strings; private worker result payloads and provider prompts remain full-fidelity.
- [ ] Next material code slice review.
  Source: standing reviewer `019e3899-5ab3-7171-9d3c-32e7c57bbde7`.
  Trigger: after the next implementation pass changes backend, frontend, or project skill contracts.
