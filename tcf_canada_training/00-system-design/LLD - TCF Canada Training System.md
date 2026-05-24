---
type: lld
project: tcf-canada-training
status: active
updated: 2026-05-17
owners:
  - codex
source_notes:
  - [[../00-system-design/HLD - TCF Canada Training System]]
---

# LLD - TCF Canada Training System

## Files

- `output/viewers/tcf-training-system.html`: standalone app shell.
- `output/viewers/tcf-training-system.css`: responsive interface styling.
- `output/viewers/tcf-training-system.js`: practice data, UI rendering, timers, local state, scoring, and export logic.
- `output/viewers/tcf-training-system.json`: app-state manifest and content index for review.

## Browser State

The app uses `localStorage` under key `tcfCanadaTrainingState.v1`.

Stored state:

- learner profile and selected starting band.
- daily logs.
- listening and reading attempts.
- writing attempts with rubric scores and word counts.
- speaking attempts with rubric scores and notes.
- mock records.

Audio recordings are session-local object URLs when the browser supports `MediaRecorder`; the app stores the score and notes, not the raw audio blob.

## Score Interpretation

Production scores use a training proxy mapped to IRCC's published 20-point speaking/writing bands:

- 16-20: estimated NCLC 10+.
- 14-15: estimated NCLC 9.
- 12-13: estimated NCLC 8.
- 10-11: estimated NCLC 7.
- 7-9: estimated NCLC 6.
- 6: estimated NCLC 5.
- 4-5: estimated NCLC 4.

Listening and reading use raw accuracy readiness bands only. The app must not convert raw right answers into official FEI scores because FEI does not publish that private conversion.

## Practice Logic

Listening:

- Uses original French prompts and the browser speech synthesis API when available.
- Each item can be played once per active attempt.
- Transcript and rationale appear after the answer.

Reading:

- Uses short original passages with TCF-style multiple-choice questions.
- Stores trap type and remediation target.

Writing:

- Enforces Task 1, Task 2, and Task 3 word limits.
- Provides 0-4 rubric rows for task completion, cohesion, vocabulary, grammar, and argument/reformulation.

Speaking:

- Provides task-specific timers for 2:00, 5:30 with 2:00 prep, and 4:30.
- Supports recording in compatible browsers.
- Uses 0-4 rubric rows for interaction/task completion, discourse, vocabulary, grammar, and pronunciation/fluency/sociolinguistic fit.

Mock Tracker:

- Stores official-format mock results.
- Emits readiness text based on repeated stable performance rather than one peak score.

## Obsidian Loop

The app generates Markdown notes for:

- daily practice review.
- latest mock.
- latest writing attempt.
- latest speaking attempt.

These notes are intended to be saved under `raw/session-notes/` or used to update [[../01-work-tracking/Progress Dashboard]].
