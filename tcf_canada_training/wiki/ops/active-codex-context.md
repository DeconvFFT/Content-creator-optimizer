---
type: active-context
project: tcf-canada-training
status: active
updated: 2026-05-17
owners:
  - codex
source_notes:
  - [[../../raw/user-feedback/2026-05-17-initial-build-request]]
  - [[../../raw/source-notes/2026-05-17-chatgpt-deep-research-plan]]
  - [[../../raw/source-notes/2026-05-17-official-tcf-canada-source-check]]
---

# Active Codex Context

## Current User Goal

Build a personalized TCF Canada training system that uses a dedicated Obsidian vault as project memory and gives the learner a practical way to train for a high score.

## Current System State

- Vault exists at `tcf_canada_training/`.
- The vault uses raw/wiki/output memory layers.
- The first practice app lives at `output/viewers/tcf-training-system.html`.
- The app is local-first and does not require provider keys.
- Official-source-sensitive details were checked on 2026-05-17 and captured in [[../../02-research/Official Source Ledger]].

## Implementation Rules

- Keep official facts sourced to FEI or IRCC.
- Do not invent an official raw-score conversion for listening or reading.
- Prefer original practice content unless the learner provides licensed material.
- Keep future project decisions in Obsidian notes.
- Update [[../../01-work-tracking/Current Sprint]] and [[../../log]] after meaningful changes.

## Next Useful Work

1. Run the first diagnostic and set the starting track.
2. Expand the original prompt bank.
3. Add AI-assisted feedback only after the local-first practice loop is reliable.
