---
type: runbook
project: agent-studio
status: active
updated: 2026-05-17
owners:
  - interactive-note-taking-agent
  - source-ledger-agent
  - knowledge-graph-curator-agent
  - feynman
  - codex
confidence: high
source_notes:
  - [[../../raw/articles/2026-05-17-ziwen-codex-knowledge-vault]]
  - [[codex-obsidian-working-memory]]
  - [[../../SCHEMA]]
---

# Autonomous Obsidian Ingestion Flow

## Purpose

This runbook turns the vault from a passive archive into a living project-memory system for Codex and Agent Studio. The goal is not to accumulate notes. The goal is to make captured sources usable for future agents without pretending unread or unprocessed material is canon.

## Operating Model

Use this pipeline for books, PDFs, official docs, papers, YouTube lectures, articles, screenshots, and user feedback:

1. Capture into an inbox or raw source note with source URL/path, author, date, access method, rights strategy, and extraction limits.
2. Run the provenance gate before synthesis. Use official/open sources, user-provided local files, or explicit user-owned material. Exclude shadow-library indicators.
3. Extract only the working text needed for reading. Temporary extraction files can live outside the vault; do not store raw book text or long copyrighted excerpts in Obsidian.
4. Triage the source by relevance, domain, extraction quality, and priority for Agent Studio.
5. Read materially before writing synthesis. Do not create TOC-only notes or placeholder chapter notes.
6. Write compact original source, chapter, or video notes with attribution, key ideas, design implications, and open questions.
7. Link each durable note to the relevant MOC, source ledger, concept notes, and project decisions.
8. Mark index status so retrieval and graph systems know whether a note is searchable, linked, stale, or blocked.
9. Promote only stable, source-backed conclusions into `wiki/`. Keep raw captures append-only and outputs regenerable.
10. Audit for orphan captures, unsupported claims, duplicate sources, missing backlinks, stale docs, and weak provenance.

## Lifecycle States

Use these states for ingestion notes and manifests:

- `captured`: source is known but not yet trusted or processed.
- `provenance_checked`: source is legal/local/official enough for notes.
- `extracted`: text, transcript, or page content is readable enough for study.
- `triaged`: relevance and priority are assigned.
- `deep_read_in_progress`: source is being materially read.
- `synthesized`: original notes exist and avoid raw-text dumping.
- `linked`: notes connect to MOCs, related concepts, and source ledgers.
- `indexed`: semantic or graph retrieval can use the note.
- `canon_candidate`: conclusion is stable enough to consider for wiki promotion.
- `canon_ready`: conclusion has source support and is reflected in the durable wiki layer.
- `blocked_provenance`, `blocked_extraction`, `blocked_access`, `blocked_conflict`: work cannot proceed without a decision or access fix.

## Minimum Source Note Fields

Every source note should include:

- `source_url` or absolute local `source_path`
- `source_type`
- `author` or organization when known
- `published` or file metadata date when known
- `captured`
- `retrieval_method`
- `rights_strategy`
- `extraction_status`
- `ingestion_status`
- `index_status`
- `confidence`

## Daily Loop

The daily loop is for processing new captures, not for inventing summaries from unread material.

1. Inspect new files in `raw/inbox/`, `raw/articles/`, `raw/videos/`, `raw/books/`, and user feedback.
2. Deduplicate against existing raw and wiki notes.
3. Apply provenance and extraction gates.
4. Deep-read the highest-priority item that can be processed legally.
5. Produce or update the durable source note and link it to the right MOC.
6. Update status ledgers and index status.
7. If a source changes operating rules, update `wiki/ops/` and the active context note.

## Weekly Loop

The weekly loop looks for structural changes rather than more volume:

- Which source-backed patterns are recurring across books, docs, papers, and runs?
- Which folders or MOCs no longer match how the project thinks?
- Which operating rules in [[codex-obsidian-working-memory]] are stale?
- Which claims appear important but unsupported?
- Which notes are isolated from the graph and should be linked or archived?

Only update master operating instructions when the change is source-backed and useful for future work.

## Accuracy Gates

- Agents should cite a specific note or source before making policy-sensitive technical decisions.
- If a current task contradicts older source-backed notes, stop for a tie-breaker unless the newer source clearly supersedes the old one.
- Before code or architecture work that depends on memory, write a short plan grounded in the active context and relevant wiki note.
- Do not treat graph-neighbor memories, generated viewers, or unprocessed inbox notes as policy.

## Agent Studio Product Implications

- Product memory needs first-class source lifecycle state, not just stored text.
- The retrieval layer should expose whether evidence is raw, synthesized, linked, indexed, or canon-ready.
- The agent harness should support passive capture, plan-first checkpoints, source-citation gates, contradiction detection, and weekly memory refactoring.
- YouTube and lecture ingestion should store URLs, transcript-derived original notes, timestamps when useful, and source-aware implications. Do not download videos.
