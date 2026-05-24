---
type: ingestion-operating-model
project: agent-studio-system-design
status: process_note
updated: 2026-05-18
source_status: public_third_party_workflow_article_plus_official_obsidian_help
sources:
  - https://x.com/ziwenxu_/status/2053241837453029439?s=12
  - https://help.obsidian.md/links
related:
  - "[[2026-05-17-ingestion-plan]]"
  - "[[status-summary]]"
  - "[[deep-reading-coverage-ledger]]"
  - "[[../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# Obsidian Ingestion Operating Model

## Scope

This note captures workflow adjustments after reading the public X article on an automated Codex/Obsidian knowledge vault and cross-checking the note-linking mechanics against official Obsidian help. The article is used as process inspiration only, not as Agent Studio source canon. This note stores compact original synthesis and no long article excerpts.

## What Changes

Agent Studio's vault workflow should be explicit about the transition from capture to trusted knowledge:

1. `capture`: incoming links, videos, PDFs, docs, and user pointers are recorded with provenance and rights status.
2. `triage`: sources are classified by legal status, relevance, extraction feasibility, and priority.
3. `direct_read`: notes are created only after materially reading the source or watching the official video.
4. `cross_check`: architecture-relevant claims are checked against official docs, books, lectures, papers, or production guidance.
5. `canon`: only cross-checked synthesis can support product decisions.

This keeps passive ingestion useful without letting bookmarks, transcripts, or scraped snippets become unchecked authority.

## Folder Logic

The current vault already mostly matches the useful operating pattern:

| Function | Current vault location | Rule |
|---|---|---|
| Master map | `MOC.md`, `README.md`, status files | Keep updated whenever the map changes. |
| Capture and triage | `01-sources/`, `05-ingestion-runs/` manifests | Store source identity, not raw source text. |
| Durable notes | `02-books/`, `02-lectures/`, `01-sources/official-open/` | Use direct-reading synthesis with source attribution. |
| Original implications | `03-patterns/`, `04-agent-studio-implications/` | Separate source understanding from product decisions. |
| Project-facing architecture | `04-agent-studio-implications/` | Only cite canon-ready or explicitly marked lower-confidence notes. |

No separate raw `inbox/` folder is needed inside this vault yet. If one is added later, it should contain only manifests, links, and processing queues, not copied article bodies, video transcripts, or book text.

## Link And Graph Rules

Official Obsidian mechanics reinforce that the vault should be a graph of understood notes, not a folder dump. Links, backlinks, and graph views are useful only when the edge means something.

- Use wikilink syntax inside the actual explanatory sentence when one note materially depends on another note.
- Use display aliases only to keep prose readable; do not hide a vague or unrelated target behind a friendly label.
- Use heading links when the dependency is a specific section of a long canon note.
- Let backlinks expose source-to-pattern and pattern-to-architecture dependencies; do not create backlinks solely to inflate graph density.
- Avoid deliberate ghost notes in this vault except for explicit backlog or open-question records. Missing links should usually be treated as hygiene failures.
- After adding or renaming notes, rerun wiki-link validation before treating the map as navigable.

This changes the ingestion flow in one concrete way: every new source note should add at least one meaningful link to an existing MOC, pattern, architecture implication, or process ledger, and every new architecture note should link back to the source notes that justify it.

## Freshness And Audit Rules

- Every architecture-changing note must link back to specific source notes or manifest records.
- If a claim is not in the vault, the agent should label it as an assumption or open question.
- Daily ingestion should update queues, blockers, and source status, not silently promote material to canon.
- Weekly ingestion should review whether the folder map, MOC, source ledgers, and datastore schema still match the real workflow.
- When the vault structure changes, update `MOC.md`, `status-summary.md`, and any affected source manifests in the same pass.
- Do not use automated capture, captions, transcripts, comments, or metadata as a substitute for direct reading or official full-video watching.
- Treat link integrity as a release check for the note graph. A note can be correct in isolation and still be operationally weak if it is not connected to the source, pattern, or architecture layer that will use it.

## Agent Studio Design Implications

The product datastore should model the same lifecycle:

- `source_record` for identity, provenance, rights, and status;
- `ingestion_run` for capture/extraction/audit events;
- `note_artifact` for compact human-readable synthesis;
- `coverage_status` for inventory, direct-read, cross-check, and canon state;
- `decision_reference` for architecture decisions that depend on specific source notes;
- `audit_record` for daily or weekly queue reviews.

The important product lesson is not passive scraping by itself. The useful system is a governed memory loop: low-friction capture, strict provenance, explicit promotion gates, source-cited decisions, and regular map maintenance.

## Guardrails

- Do not bookmark, like, repost, reply, or otherwise interact with social content as part of ingestion unless the user explicitly asks and confirms the public action.
- Do not ingest private bookmarks or account data without an explicit user request for that source and destination.
- Do not store raw X article text, raw YouTube transcripts, or raw book extracts in the vault.
- Do not mark a source `canon_ready` because it was captured; canon requires direct reading and cross-checking.
