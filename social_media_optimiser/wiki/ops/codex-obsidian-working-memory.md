---
type: runbook
project: agent-studio
status: active
updated: 2026-05-17
owners:
  - interactive-note-taking-agent
  - forward-deployed-engineer
  - codex
source_notes:
  - [[../../raw/articles/2026-05-17-mitcham-ai-agent-operating-system]]
  - [[../../raw/articles/2026-05-17-ziwen-codex-knowledge-vault]]
  - [[../../SCHEMA]]
  - [[active-codex-context]]
  - [[autonomous-obsidian-ingestion-flow]]
---

# Codex Obsidian Working Memory

## Purpose

This note defines how Codex should use the vault during this project so it does not rely on long chat context for every decision.

## Current User Directive

The vault is the primary project memory and tracking surface. HTML and JSON viewers are useful only as generated inspection layers.

Codex should optimize for a small Obsidian preflight instead of consuming long conversation context. The compact starting note is [[active-codex-context]].

## Before Work

For any non-trivial Agent Studio task:

1. Read [[../../Agent Studio MOC]].
2. Read [[../../01-work-tracking/Current Sprint]].
3. Read [[active-codex-context]].
4. Read this note if the task affects memory, planning, tracking, or review.
5. Read the narrow wiki note for the relevant subsystem.
6. Search raw notes only if the wiki lacks source evidence.
7. For source-ingestion work, read [[autonomous-obsidian-ingestion-flow]] before writing durable notes.

## During Work

Use Obsidian as the working memory:

- Put new passive captures through `raw/inbox/` or a typed raw source folder before treating them as knowledge.
- Put new source references in `raw/`.
- Put durable design conclusions in `wiki/`.
- Put generated visualizations and exports in `output/`.
- Keep screenshots in `/screenshots` at the repo root.
- Keep code changes in product code, not in the vault.
- Track source lifecycle and index status when a source moves from capture to synthesis.

## Autonomous Ingestion Flow

For books, official docs, papers, articles, and YouTube lectures, use the pipeline in [[autonomous-obsidian-ingestion-flow]]:

1. Capture source metadata and rights strategy.
2. Check provenance and extraction quality.
3. Deep-read before synthesis.
4. Write compact original notes with Agent Studio implications.
5. Link notes to MOCs, related concepts, source ledgers, and project decisions.
6. Mark index status for retrieval and graph use.
7. Promote only stable, source-backed conclusions to `wiki/`.

Do not create placeholder or TOC-only notes. If extraction or access fails, mark the source blocked instead of filling the gap with a shallow note.

## After Work

Update, in this order:

1. Relevant wiki note.
2. [[../../01-work-tracking/Current Sprint]].
3. [[../../01-work-tracking/Decision Log]] if a decision changed.
4. [[../../03-review-packets/Feedback Inbox]] if user feedback was addressed.
5. [[../../log]] with one compact entry.

## Runtime Promotion Workflow

When a run produces useful durable lessons, use:

- API: `POST /api/runs/{run_id}/obsidian-memory-promotion`
- A2A task: `generate_obsidian_memory_promotion` for `interactive-note-taking-agent`

The workflow writes a proposed wiki-memory update under `wiki/run-memory-promotions/{run_id}/`.

Use the promotion note to decide what should be applied to canonical wiki notes. Do not automatically rewrite durable wiki knowledge from every run; only promote stable changes, repeated failures, user preferences, or policy updates.

## Autonomous Memory Summary Export

When an autonomous pass needs a compact Obsidian handoff, set `export_memory_summary_to_obsidian = true` on `POST /api/runs/{run_id}/autonomous-pass`.

The workflow writes `output/reports/autonomous-memory-summaries/{run_id}/memory-summary.md` and records an `obsidian_note` artifact with provenance `autonomous_memory_summary_export_v1`.

Use this note as a short run handoff for selected memories, memory health, risks, and recommended follow-up fetches. It is not a canonical wiki update.

For always-on autonomous profiles, persist the policy on the profile:

- `autonomous_export_memory_summary_to_obsidian`
- `autonomous_memory_summary_agent_id`
- `autonomous_memory_summary_limit`

The same profile can also persist research and retrieval gates through:

- `autonomous_auto_refresh_research_sources`
- `autonomous_block_on_research_freshness_blocked`
- `autonomous_block_on_retrieval_quality_blocked`

Heartbeat ledgers and scheduler events now include a compact `policy` or `profile_policies` summary. Use those fields to audit whether a profile merely had a policy configured or whether the autonomous pass actually exported memory, ran research refresh, or blocked on a gate.

Heartbeat ledgers and heartbeat/scheduler events also include compact `metrics` or `profile_metrics`:

- `retrieval_quality`: status, candidate counts, accepted evidence counts, precision risks, recall gaps, coverage gaps, graph node counts, recommended query counts, and whether a retrieval gate blocked the pass.
- `memory_health`: total/project memory counts, stale memory count, low-confidence memory count, conflict count, and context risk count.

Codex should use these metrics before assuming an always-on profile has enough trusted memory or evidence to continue autonomously.

## Typed Project Memory

Use `POST /api/runs/{run_id}/project-memory` or the `record_project_memory` A2A task when a lesson should be available to future agent context packets.

Use `user_preference` for durable user behavior or communication preferences.

Use `project_decision` for durable architecture, product, or process decisions.

Default to `scope = global` when the memory should apply across runs. Use `scope = run` only for temporary run-local facts.

## Project Memory Retrieval

Use `POST /api/runs/{run_id}/project-memory/retrieval` or the `retrieve_project_memory` A2A task when Codex or an agent needs a compact memory lookup before acting.

Use it for:

- Finding prior project decisions.
- Pulling related user preferences.
- Seeing which wiki notes and tags connect memories.
- Checking whether retrieved memories are direct semantic matches or graph neighbors.

The workflow uses pgvector when a `query_embedding` is supplied, then expands related memories through shared tags, target wiki notes, and source artifact ids. Treat graph-neighbor memories as useful context, not automatic policy, until reviewed.

Context packets and resume plans now include compact project-memory retrieval summaries by default. Codex should inspect `summary.project_memory_retrieval` or `context_summary.project_memory_retrieval` before reloading broad chat context. If the summary shows only graph neighbors and no seed matches, confirm the memory before applying it as current policy.

Recorded retrieval ledgers include `evaluation` metrics. Prefer labeled evaluations when `relevant_memory_ids`, `relevant_tags`, or `relevant_target_wiki_notes` are supplied. Heuristic evaluations are still useful for spotting drift, but they should not be treated as proof that recall is complete.

Use `trend = regressed` or nonzero `recall_gap_count` as a signal to inspect the prior ledger before depending on the retrieved memory set.

Worker context summaries now include `project_memory_policy`. Codex should treat `needs_precision_review`, `graph_only_review`, or `regressed` as signals to inspect the cited memories before relying on them. Always-on scheduler events expose the same risk classes as aggregate profile counts.

Always-on worker-profile heartbeats now open `project_memory_policy_confirmation` feedback gates before execution when policy status is `needs_precision_review`, `needs_recall_repair`, `graph_only_review`, or `regressed`. Codex should treat those gates as blockers until the Forward Deployed Engineer or user confirms which memories are valid for the current run.

## Memory Health In Context Packets

Context packets expose `summary.memory_health` and add risk items when retrieved project memories are stale, low-confidence, or conflicting.

Codex should treat those risks as blockers for policy-sensitive work:

- Refresh stale memories before using them as current direction.
- Confirm low-confidence memories before applying them.
- Resolve conflicting memories through Product Manager or Forward Deployed Engineer review.

## Token Discipline

Do not load the full vault by default.

Use this lookup order:

1. `wiki/ops/active-codex-context.md`.
2. `Agent Studio MOC.md`.
3. Current sprint.
4. Specific wiki page.
5. Decision log.
6. Raw source note.
7. Output viewer only for review.

If a task is purely local code and not affected by project memory, skip broad Obsidian reads.

For memory-related work, prefer the three-layer lookup:

1. Wiki synthesis for current operating rules.
2. Raw source notes only when source evidence or external inspiration matters.
3. Output viewers only to inspect generated design state.

## How Codex Should Refer To Memory

When reporting progress:

- Name the Obsidian note that changed.
- Avoid restating every detail from the note.
- Treat HTML viewers as secondary.
- Treat the vault as the project memory source of truth.

## Maintenance Checks

Codex should periodically check these vault risks when work touches memory or planning:

- Raw source exists but no wiki synthesis links to it.
- Inbox or raw capture exists without lifecycle status.
- Wiki note has no source note, owner, status, or confidence.
- Wiki note has no MOC backlink or related concept link.
- Source-derived note has no `index_status`.
- Output viewer exists without a paired JSON state file or source note list.
- Current sprint says an item is in progress but no code or note changed in the slice.
- User feedback is captured in chat but not represented under `raw/user-feedback/`, `03-review-packets/`, or a relevant wiki note.
