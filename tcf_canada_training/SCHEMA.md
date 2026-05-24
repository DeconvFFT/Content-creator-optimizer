---
type: memory-schema
project: tcf-canada-training
status: active
updated: 2026-05-17
owners:
  - codex
  - learner
---

# TCF Canada Training Memory Schema

This vault is the working memory system for the personalized TCF Canada training project.

The vault uses three layers:

1. `raw/` captures evidence, user feedback, session notes, and source checks.
2. `wiki/` turns raw material into stable exam, curriculum, scoring, and operating knowledge.
3. `output/` contains generated deliverables such as the practice app, JSON state, reports, and handoffs.

HTML is a derived output. Obsidian notes are the source of truth for decisions, progress, and future implementation context.

## Raw Layer

Use `raw/` for:

- Source checks from FEI, IRCC, RFI, TV5MONDE, and the supplied deep-research PDF.
- Original user feedback and project directives.
- Session observations, rough error logs, and copied app exports.

Rules:

- Preserve what was observed at the time.
- Add dated addenda instead of silently rewriting old evidence.
- Keep official-source links and access dates.
- Avoid storing copyrighted practice passages in full unless they are original project-authored content.

## Wiki Layer

Use `wiki/` for:

- Exam targets and constraints.
- Curriculum design.
- Rubrics and score interpretation policy.
- Codex operating context.
- Memory rules and project decisions.

Rules:

- Link wiki conclusions back to raw source notes or official ledgers.
- Mark estimates clearly when official scoring is not public.
- Update the relevant wiki note before or alongside implementation changes.

## Output Layer

Use `output/` for:

- The interactive practice app.
- JSON practice-system state.
- Reports and implementation handoffs.
- Generated progress exports.

Rules:

- Outputs can be regenerated.
- If output conflicts with wiki notes, the wiki wins.
- Any app-generated score must be labeled as training readiness, not an official FEI score.

## Working Loop

Before major work:

1. Read [[TCF Canada Training MOC]].
2. Read [[01-work-tracking/Current Sprint]].
3. Read [[wiki/ops/active-codex-context]].
4. Read the narrow wiki note affected by the task.

After major work:

1. Update the relevant wiki note.
2. Update [[01-work-tracking/Current Sprint]].
3. Add a compact entry to [[log]].
4. Refresh output artifacts only when they help the learner practice or review progress.
