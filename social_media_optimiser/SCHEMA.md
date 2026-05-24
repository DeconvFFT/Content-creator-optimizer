---
type: memory-schema
project: agent-studio
status: active
updated: 2026-05-17
owners:
  - interactive-note-taking-agent
  - product-manager
  - agent-harness-engineer
---

# Obsidian Memory Schema

This vault is now the working memory system for Agent Studio. The project uses a three-tier memory architecture:

1. `raw/` captures source material and observations.
2. `wiki/` turns raw material into durable project knowledge.
3. `output/` contains generated deliverables, viewers, reports, and handoff artifacts.

HTML is a derived output. It is not the memory source of truth.

## Tier 1: Raw

Raw notes are append-only evidence packets.

Use raw notes for:

- Capture inbox entries that have not yet been synthesized.
- External articles, docs, papers, and reference pages.
- Book, PDF, lecture, and video source metadata.
- User feedback and design-review comments.
- Run exports, event summaries, screenshots metadata, and experiment observations.
- Source snippets that are legally safe to store.

Rules:

- Do not rewrite raw notes to fit a later conclusion.
- If a raw note needs correction, add an addendum with date and reason.
- Store source URL, access date, author, publication date when available, and extraction limits.
- Do not paste full copyrighted articles. Use metadata, short compliant excerpts, and paraphrased observations.
- Keep passive captures separate from durable conclusions. A raw note can be `captured` without being `synthesized`, `linked`, or `canon_ready`.

Recommended raw folders:

- `raw/inbox/`: low-friction capture queue before triage.
- `raw/articles/`: external articles and web references.
- `raw/videos/`: YouTube lecture or video metadata plus original transcript-derived notes.
- `raw/books/`: local book/PDF metadata and reading-status packets.
- `raw/user-feedback/`: direct user feedback and review notes.
- `raw/run-exports/`: run state, ledgers, screenshots metadata, and experiment observations.

## Tier 2: Wiki

Wiki notes are the durable knowledge layer.

Use wiki notes for:

- Architecture concepts.
- Product decisions.
- Agent responsibilities.
- Memory, retrieval, guardrail, orchestration, and provider policies.
- Runbooks for how agents and Codex should work.

Rules:

- Every wiki note should link to relevant raw sources or decision notes.
- Prefer concise, stable synthesis over transcript-style notes.
- Include status, owners, confidence, and review cadence in frontmatter.
- Update wiki pages when raw evidence changes the design.
- Do not promote a source into wiki canon until it has been materially read, source-linked, and reconciled with existing project rules.

## Tier 3: Output

Output notes and files are generated deliverables.

Use output for:

- Interactive HTML viewers.
- JSON system-state exports.
- Review packets.
- Reports, architecture snapshots, and implementation plans.
- Content drafts and publishable artifacts when mirrored into the vault.

Rules:

- Outputs must name the wiki notes and raw sources they derive from.
- Outputs can be regenerated.
- Outputs should not be treated as canonical if they conflict with wiki or raw notes.

## Codex Working Loop

Before implementation work:

1. Read [[Agent Studio MOC]].
2. Read [[01-work-tracking/Current Sprint]].
3. Read [[wiki/ops/active-codex-context]] when the task depends on project context.
4. Read the relevant narrow `wiki/` note.
5. Search raw notes only when the wiki is incomplete or source evidence is needed.
6. For ingestion work, follow [[wiki/ops/autonomous-obsidian-ingestion-flow]] before creating durable notes.
7. Update wiki or sprint notes before or alongside code changes.

After implementation work:

1. Append to [[log]].
2. Update the relevant wiki note.
3. Update [[01-work-tracking/Current Sprint]].
4. Create or refresh output artifacts only when they help review.

## Product Memory Contract

The product app stores durable machine state in Postgres + pgvector. Obsidian stores human-readable project memory and review packets.

The product memory system should mirror this same tiering:

- Raw: source records, user turns, feedback, events, run exports.
- Wiki: synthesized memories, stable decisions, user preferences, agent policies.
- Output: generated artifacts, content packages, HTML viewers, JSON handoffs.

## Agent Operating Rule

The vault is not an archive after the fact. It is the working memory layer for this project.

For future Codex turns:

- Start from [[wiki/ops/active-codex-context]] instead of replaying broad chat history.
- Promote stable project behavior into `wiki/`, not into generated viewers.
- Keep generated JSON/HTML viewers in `output/` and treat them as regenerable projections.
- Append raw source captures and user feedback under `raw/` before turning them into durable wiki policy.
- Use the smallest relevant vault read set that can answer the current implementation question.

## Ingestion Lifecycle Contract

Use these statuses consistently when a note or manifest tracks source ingestion:

- `captured`
- `provenance_checked`
- `extracted`
- `triaged`
- `deep_read_in_progress`
- `synthesized`
- `linked`
- `indexed`
- `canon_candidate`
- `canon_ready`
- `blocked_provenance`
- `blocked_extraction`
- `blocked_access`
- `blocked_conflict`

Every durable source-derived note should expose an `index_status` or equivalent ledger field so retrieval and graph agents can tell whether the note is searchable and linked.
