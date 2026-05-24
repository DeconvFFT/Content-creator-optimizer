---
type: raw-source
project: agent-studio
status: captured
updated: 2026-05-17
source_url: https://maxmitcham.substack.com/p/how-to-build-an-ai-agent-operating
source_title: How to Build an AI Agent Operating System That Compounds Over Time
author: Max Mitcham
accessed: 2026-05-17
copyright_note: Metadata and paraphrased observations only. Full article text is not stored.
derived_wiki:
  - [[wiki/concepts/three-tier-agent-memory]]
  - [[wiki/product/agent-studio-memory-layer]]
  - [[wiki/ops/codex-obsidian-working-memory]]
---

# Raw Source - AI Agent Operating System

## Source

- URL: https://maxmitcham.substack.com/p/how-to-build-an-ai-agent-operating
- Page title observed in Browser: `How to Build an AI Agent Operating System That Compounds Over Time`
- Accessed: 2026-05-17

## Paraphrased Observations

- The useful pattern is a layered agent memory system rather than one giant context window.
- Raw source material should stay separate from synthesized knowledge.
- A durable wiki layer lets agents reuse compressed project knowledge.
- Output artifacts should be generated from the memory system, not become the only source of truth.
- The operating system compounds when every cycle produces reusable memory, not only a one-off answer.
- Recurring maintenance should check stale pages, broken links, missing metadata, uncompiled raw sources, and index drift.
- Semantic search should index both raw and wiki collections, while exact keyword lookup remains important for IDs, named decisions, and explicit constraints.

## Design Implications For Agent Studio

- Obsidian should be treated as an agent memory operating system, not only a human notes folder.
- We should use three tiers: raw evidence, wiki synthesis, and generated outputs.
- Codex should read a small set of wiki pages before broad repo scans when the task depends on prior project context.
- Product agents should emit Obsidian review packets so human-readable memory grows after runs.
- JSON and HTML viewers should be generated from wiki state, not maintained manually.
- Scheduler/profile observability should report memory health and retrieval quality so always-on agents can identify weak memory before acting on it.

## Extraction Limits

This note intentionally does not store the full article text.

## Addendum - 2026-05-17 Browser Review

- Browser and web extraction confirmed publication date: 2026-04-10.
- The source frames the durable pattern as a three-layer memory architecture: raw source material, agent-compiled wiki knowledge, and generated outputs.
- The source also recommends recurring maintenance for memory quality: stale pages, broken links, uncompiled sources, missing metadata, and index drift.
- Applied project interpretation: Codex should read a compact Obsidian operating note before broad context loads, and each meaningful project slice should leave a small vault update that future agents can retrieve.
