---
type: product-architecture
project: agent-studio
status: active
updated: 2026-05-17
owners:
  - principal-software-engineer
  - context-engineering-agent
  - artifact-librarian
  - observability-agent
source_notes:
  - [[../../raw/articles/2026-05-17-mitcham-ai-agent-operating-system]]
  - [[../concepts/three-tier-agent-memory]]
---

# Agent Studio Memory Layer

## Goal

Agent Studio needs memory that compounds across long-running work without turning every run into a giant prompt. The memory layer should support source-backed content generation, voice dialogue, feedback loops, retrieval, guardrails, and resumable multi-agent work.

The same operating principle applies to Codex while building the system: use [[../ops/active-codex-context]] and subsystem wiki notes as compact project memory before loading broad chat history or generated viewers.

## Product Memory Tiers

### Tier 1: Raw Product Memory

Stored primarily in Postgres, with selected human-readable mirrors in Obsidian.

Includes:

- Conversation turns.
- Realtime session events.
- Source records.
- Web search results.
- Retrieval candidates.
- Rerank decisions.
- User feedback.
- Run events.
- Checkpoints.
- Provider operations events.
- Screenshot or media metadata.

Purpose:

- Preserve evidence and event history.
- Support auditability and replay.
- Avoid losing source provenance.

### Tier 2: Synthesized Product Memory

Stored in Postgres + pgvector and mirrored to Obsidian when useful for human review.

Includes:

- Stable user preferences.
- Project decisions.
- Agent policy memories.
- Retrieval quality summaries.
- Claim revision lessons.
- Guardrail failure patterns.
- Platform-specific content strategy lessons.
- Knowledge graph nodes and edges.

Purpose:

- Give agents a compact, high-signal context layer.
- Reduce repeated reasoning.
- Improve precision, recall, and coverage over time.

### Tier 3: Output Product Memory

Stored as artifacts and optionally exported to Obsidian.

Includes:

- Posts.
- Reel scripts.
- Substack drafts.
- Source ledgers.
- Publishing handoffs.
- Claim revision ledgers.
- HTML viewers.
- JSON handoffs.
- Obsidian review packets.

Purpose:

- Deliver work to the user.
- Make state inspectable.
- Provide reusable review context without becoming canonical source evidence.

## Retrieval Path

For project-internal decisions:

1. Search wiki memory.
2. Read decision log.
3. Read raw notes if evidence is needed.
4. Regenerate output if stale.

For content generation:

1. Search external web and source records.
2. Build retrieval quality ledger.
3. Rerank and accept evidence.
4. Store source ledger and claim links.
5. Use synthesized run memory only after source-backed evidence is assembled.

## Memory Promotion Rules

Raw becomes wiki when:

- It affects architecture.
- It captures user preference.
- It changes agent behavior.
- It resolves an open design question.

Wiki becomes output when:

- The user needs a visual or artifact.
- A run needs a handoff.
- The product app needs JSON state.
- A design review needs a generated viewer.

Output feeds raw only when:

- User comments on it.
- A reviewer finds an issue.
- A test or run event records behavior.

## Codex Working-Memory Mapping

For implementation work, the vault maps to Codex behavior like this:

- Raw: source article captures, user feedback, browser observations, run exports, and test observations.
- Wiki: current architecture, active constraints, subsystem policies, retrieval strategy, guardrail policy, and Codex runbooks.
- Output: interactive viewers, JSON design snapshots, review packets, and generated handoff reports.

Codex should update wiki notes for durable design changes and only refresh viewers when the user needs visual inspection or the system design changed materially.

## Open Implementation Items

- Done: add a memory-promotion workflow that converts run review packets and durable run state into proposed wiki-memory updates.
- Done: add explicit memory records for user preferences and project decisions in Postgres.
- Done: add memory freshness and conflict checks to context packets.
- Done: add autonomous-pass export for selected memory summaries into Obsidian output notes.
- Done: add heartbeat/scheduler metrics for retrieval quality and memory health.
- Done: add pgvector-backed synthesized-memory retrieval and graph traversal across project memories.
- Done: wire project-memory retrieval summaries into context packets and resume plans.
- Done: add project-memory retrieval evaluation metrics for labeled and heuristic precision/recall plus repeated-query trend deltas.
- Done: expose project-memory retrieval policy in agent context summaries and always-on scheduler/profile metrics.
- Done: block always-on worker-profile heartbeats behind human feedback gates when project-memory policy status is risky.
- Done: add a provider-free cockpit demo run that records a project decision through the same project-memory workflow used for user-confirmed decisions.

## Implemented Promotion Workflow

Endpoint:

- `POST /api/runs/{run_id}/obsidian-memory-promotion`

Worker task:

- `interactive-note-taking-agent` handles `generate_obsidian_memory_promotion`.

Output:

- Proposed wiki-memory notes under `wiki/run-memory-promotions/{run_id}/`.
- Durable `obsidian_memory_promotion` artifacts with source artifact ids, target wiki notes, promoted item count, and promotion provenance.
- `obsidian_memory_promotion_generated` events for run timelines.

Policy:

- Promotion notes propose wiki updates; they do not silently rewrite canonical wiki pages.
- Stable lessons can be applied to wiki notes after review.
- One-off observations stay in raw notes or run review packets.

## Implemented Typed Project Memory

Endpoint:

- `POST /api/runs/{run_id}/project-memory`

Worker task:

- `record_project_memory` for `context-engineering-agent`, `product-manager`, or `interactive-note-taking-agent`.

Memory kinds:

- `user_preference`
- `project_decision`

Scopes:

- `global`: stored with `run_id = null`, retrieved by run context when global memories are included.
- `run`: stored directly against the run.

Metadata:

- `source_run_id`
- `project_memory_kind`
- `memory_scope`
- `confidence`
- `tags`
- `source_artifact_ids`
- `target_wiki_notes`
- `workflow = project_memory_record_v1`

## Implemented Memory Health Checks

Context packets now include `summary.memory_health`.

Checks:

- Stale project memories: expired memories or memories older than their review window.
- Low-confidence project memories: confidence is `low`, `unknown`, or `tentative`.
- Conflicting project memories: same memory kind with shared tags, shared wiki targets, or shared key terms but opposite negation.

Risk types:

- `stale_project_memories`
- `low_confidence_project_memories`
- `conflicting_project_memories`

Policy:

- Stale memory should be refreshed or reconfirmed before use as current policy.
- Low-confidence memory should be reviewed before it changes agent behavior.
- Conflicting memory should be resolved by Product Manager or Forward Deployed Engineer review.

## Implemented Autonomous Memory Summary Export

Autonomous passes can now export a compact selected-memory summary into Obsidian when requested.

Trigger:

- `POST /api/runs/{run_id}/autonomous-pass`
- Request field: `export_memory_summary_to_obsidian = true`
- Optional request fields: `memory_summary_agent_id`, `memory_summary_limit`
- Always-on worker profiles can persist the same policy through `autonomous_export_memory_summary_to_obsidian`, `autonomous_memory_summary_agent_id`, and `autonomous_memory_summary_limit`.

Output:

- Note path: `output/reports/autonomous-memory-summaries/{run_id}/memory-summary.md`
- Durable artifact type: `obsidian_note`
- Provenance workflow: `autonomous_memory_summary_export_v1`
- Event: `obsidian_memory_summary_exported`

Policy:

- The exported note is an output handoff, not a canonical wiki rewrite.
- It summarizes selected project memories, memory health, memory risks, and recommended follow-up fetches.
- Stable policy changes should still be promoted through reviewed wiki updates or explicit `project_memory` records.

## Implemented Always-On Memory Observability

Worker profile heartbeat ledgers now include `content.metrics`.

Retrieval quality metrics:

- `status`
- `candidate_count`
- `accepted_candidate_count`
- `accepted_candidate_ratio`
- `precision_risk_count`
- `recall_gap_count`
- `coverage_gap_count`
- `graph_node_count`
- `recommended_query_count`
- `gate_blocked_pass`

Memory health metrics:

- `memory_count`
- `project_memory_count`
- `stale_memory_count`
- `low_confidence_memory_count`
- `conflict_count`
- `context_risk_count`

Events:

- `worker_profile_heartbeat` and `worker_profile_heartbeat_blocked` include the same compact `metrics` payload as the heartbeat ledger.
- `worker_scheduler_pass_completed` includes `profile_metrics` plus aggregate retrieval and memory-health counts across due profiles.

Policy:

- Always-on profiles should not continue blindly when accepted evidence is weak or memory health shows stale, low-confidence, or conflicting memories.
- Scheduler metrics are the compact operations surface for deciding which profile needs source refresh, memory review, or human feedback.

## Implemented Project Memory Retrieval

Endpoint:

- `POST /api/runs/{run_id}/project-memory/retrieval`

Worker task:

- `retrieve_project_memory` for Context Engineering Agent, Knowledge Graph Curator Agent, and Product Manager.

Artifact:

- `project_memory_retrieval_ledger`

Retrieval behavior:

- Uses pgvector ordering when `query_embedding` is provided.
- Adds keyword scoring over memory content, kind, tags, wiki targets, source artifacts, and source run metadata.
- Seeds graph traversal from the highest-scoring project memories.
- Expands to related memories only through higher-precision connectors: shared `tags`, `target_wiki_notes`, and `source_artifact_ids`.
- Avoids broad graph connectors such as same agent, same memory kind, or same source run because those create false-positive neighbors.

Returned observability:

- Seed and related memory counts.
- Keyword, semantic, graph, and combined scores per memory.
- Shared graph connectors that caused each related memory to enter the result.
- Bipartite graph nodes and edges connecting memories to tags, wiki notes, and source artifacts.
- Recommended actions when embeddings are missing, memory is empty, or graph metadata is too weak.

Context integration:

- `POST /api/runs/{run_id}/context-packet` can include `summary.project_memory_retrieval`.
- Context manifests include a `project_memory_retrieval` item when retrieved memory exists.
- Autonomous pass context packets and worker-profile heartbeat context packets include the same compact retrieval digest.
- `RunResumePlan.context_summary` includes `project_memory_retrieval`, `project_memory_retrieval_memory_count`, and `project_memory_retrieval_graph_edge_count`.
- Internal context/resume calls use `record_artifact = false` so routine handoffs do not create extra retrieval-ledger artifacts unless explicitly requested.

Evaluation behavior:

- `ProjectMemoryRetrievalRequest` can supply labeled relevance through `relevant_memory_ids`, `relevant_tags`, and `relevant_target_wiki_notes`.
- When labels are supplied, the ledger computes precision, recall, F1, false-positive memory ids, false-negative memory ids, precision-risk count, and recall-gap count.
- When labels are not supplied, the ledger uses a heuristic expected set from direct semantic or keyword matches so graph-neighbor drift is still visible.
- Recorded ledgers compare against previous ledgers with the same query and target agent, exposing `previous_precision`, `previous_recall`, `precision_delta`, `recall_delta`, `repeated_query_count`, and `trend`.
- Trend values are `no_prior`, `improved`, `stable`, or `regressed`.

Policy:

- Treat labeled precision/recall as stronger evidence than heuristic precision/recall.
- Treat graph neighbors outside the expected set as precision risks until reviewed.
- Treat false-negative memories as recall gaps that need better embeddings, tags, wiki targets, or source-artifact links.

Agent and scheduler integration:

- Worker context summaries include `project_memory_policy` derived from the retrieval digest.
- Gemma worker prompts include the project-memory policy status and instructions before the task is executed.
- Policy statuses include `ready`, `no_memory`, `graph_only_review`, `needs_precision_review`, `needs_recall_repair`, `regressed`, and `not_available`.
- Heartbeat ledgers include `metrics.project_memory_retrieval` with memory counts, seed counts, graph-edge counts, precision, recall, risk counts, repeated-query count, trend, and policy status.
- Scheduler events aggregate project-memory precision-risk profile counts, recall-gap profile counts, regressed-profile counts, and no-seed profile counts.

## Implemented Project Memory Policy Confirmation Gates

Always-on worker-profile heartbeats now run a memory-policy preflight before any worker cycle or autonomous pass executes.

Gate-triggering policy statuses:

- `needs_precision_review`
- `needs_recall_repair`
- `graph_only_review`
- `regressed`

Gate behavior:

- Create a structured `FeedbackItem` with `gate = project_memory_policy_confirmation`.
- Route the feedback to the Forward Deployed Engineer.
- Move the run to `waiting_for_human`.
- Rebuild the resume plan so the heartbeat response shows `waiting_for_human` and `open_human_feedback`.
- Record blocked context packets and heartbeat ledgers instead of running specialist agents.
- Avoid duplicate project-memory policy gates for the same profile, query, and policy status while an open or routed feedback item already exists.

Policy:

- `ready`, `no_memory`, and `not_available` do not block always-on execution by themselves.
- Precision risks and recall gaps are treated as human-confirmation points before memory can steer autonomous work.
- Graph-neighbor memory can inform review, but it cannot silently become current policy for always-on agents.

## Implemented Cockpit Memory Policy Surface

The product cockpit now exposes project-memory policy as a live operator surface, separate from Obsidian planning.

Inputs:

- Explicit `POST /api/runs/{run_id}/project-memory/retrieval` calls from the Memory Policy panel.
- `summary.project_memory_retrieval` from context packets.
- `context_summary.project_memory_retrieval` from resume plans.
- `metrics.project_memory_retrieval` from worker-profile heartbeat ledgers.
- `project_memory_policy_confirmation` feedback metadata.

Operator view:

- Current policy status.
- Memory count, seed count, related count, precision risks, recall gaps, precision, recall, and trend.
- Labeled relevance inputs for expected memory ids, expected tags, and expected wiki notes.
- Top retrieved memories and recommended actions.
- Feedback gate cards for project-memory confirmation gates.
- Timeline chips when memory-policy gates or blocked heartbeats occur.
- Source-ledger drilldowns that show accepted retrieval evidence, unaccepted sources, artifact claim coverage, claim-source verdicts, and accepted-source overlap.
- Project-memory recording controls for user-confirmed `project_decision` and `user_preference` memories with scope, confidence, tags, wiki targets, source artifact ids, and cockpit provenance.

Evaluation behavior:

- If labeled relevance fields are empty, the cockpit surfaces heuristic precision/recall from the retrieval workflow.
- If labeled relevance fields are supplied, the cockpit sends `relevant_memory_ids`, `relevant_tags`, and `relevant_target_wiki_notes` with the retrieval request.
- Labeled runs expose expected/retrieved/relevant counts, F1, false-positive ids, false-negative ids, repeated-query count, and the labels used for evaluation.

Recording behavior:

- The operator records only confirmed decisions or preferences.
- The cockpit sends metadata `source = cockpit_user_confirmed_memory` and `recorded_from = project_memory_controls`.
- Recorded memories immediately appear in the run timeline through `project_memory_recorded` events and become available to future project-memory retrieval calls.
