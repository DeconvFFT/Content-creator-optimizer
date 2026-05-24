---
type: process-records-manifest-note
project: agent-studio-system-design
status: active
updated: 2026-05-18
manifest: source-records-process-audits.json
---

# Process Records Manifest

## Purpose

`source-records-process-audits.json` is the machine-readable manifest for operational records that govern the Agent Studio datastore itself: objective coverage, integrity checks, source-map path checks, raw-text safety, local-book coverage granularity, deferred local corpus handling, Stanford availability, video-source boundaries, public video ingestion status, URL coverage priority, the Obsidian ingestion operating model, the next ingestion queue, and the topic coverage matrix.

These records are not source notes and should not be treated as canon evidence about AI systems. They are control-plane evidence about what has been checked, what is blocked, and what future ingestion agents must preserve.

## Current Contents

The manifest currently tracks 15 active process/audit records:

- objective coverage audit;
- coverage integrity audit;
- source-map path integrity audit;
- wiki-link integrity audit;
- raw-text and excerpt safety audit;
- local-book coverage granularity;
- Stanford current availability checks;
- Stanford video-source coverage matrix;
- Stanford public video ingestion status;
- YouTube playlist worklist;
- official/open URL coverage priority;
- Obsidian ingestion operating model;
- next ingestion queue;
- Agent Studio topic coverage matrix;
- deferred local corpus queue.

## Agent Studio Implication

Agent Studio should keep source evidence and process evidence separate:

- source evidence supports architecture decisions;
- process evidence controls whether source evidence is eligible, current, safe, and correctly scoped;
- active process records should be visible to agents that plan ingestion, refresh sources, or decide whether a note can be treated as canon;
- process records must stay compact and must not store raw book text, transcripts, webpage copies, protected course material, or long excerpts.
