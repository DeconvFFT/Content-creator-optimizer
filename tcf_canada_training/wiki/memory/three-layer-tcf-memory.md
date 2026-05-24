---
type: wiki-note
project: tcf-canada-training
status: active
updated: 2026-05-17
confidence: high
source_notes:
  - [[../../SCHEMA]]
  - [[../../raw/user-feedback/2026-05-17-initial-build-request]]
---

# Three-Layer TCF Memory

The training system uses Obsidian as a memory operating layer, not only as a notes folder.

## Layer 1 - Raw

Raw memory stores evidence and observations:

- official-source checks.
- supplied PDF research.
- user directives.
- daily practice exports.
- rough error logs.

This layer should preserve what happened.

## Layer 2 - Wiki

Wiki memory stores durable interpretation:

- exam constraints.
- curriculum decisions.
- scoring policy.
- active Codex context.
- remediation rules.

This layer should be compact and stable enough for a future Codex turn to resume without rereading the full chat.

## Layer 3 - Output

Output memory stores generated artifacts:

- practice app.
- JSON app state.
- handoff reports.
- exported practice summaries.

This layer is useful for action, but it is not the canonical source if it conflicts with wiki notes.
