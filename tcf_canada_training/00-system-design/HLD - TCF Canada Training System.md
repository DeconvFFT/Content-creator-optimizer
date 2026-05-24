---
type: hld
project: tcf-canada-training
status: active
updated: 2026-05-17
owners:
  - codex
  - learner
source_notes:
  - [[../raw/source-notes/2026-05-17-chatgpt-deep-research-plan]]
  - [[../raw/source-notes/2026-05-17-official-tcf-canada-source-check]]
---

# HLD - TCF Canada Training System

## Goal

Build a practical system that helps the learner train for TCF Canada across all four mandatory abilities: listening, reading, writing, and speaking.

The system targets two layers:

- Immigration floor: NCLC 7 in all four abilities for the Express Entry French-language proficiency category.
- Operational buffer: NCLC 9-style consistency where possible, because borderline test-day variance is risky.

## Product Shape

The first implementation is a local-first training cockpit inside this vault:

- Dashboard for track selection, current week, target band, and readiness signals.
- Daily training plan based on the 12 to 24 week curriculum.
- Listening drills with one-pass playback behavior.
- Reading drills with answer keys, trap tags, and remediation prompts.
- Writing task surface with word limits, timer, rubric, and saved attempts.
- Speaking task simulator with official-style timing, recording support, rubric, and feedback notes.
- Mock tracker that stores estimated readiness trends without claiming official FEI score conversion.
- Obsidian export panel for daily notes and practice summaries.

## Memory Architecture

The vault is the human-readable memory layer:

- Raw: source checks, supplied plan, user directives, and session notes.
- Wiki: stable exam/curriculum/scoring knowledge.
- Output: generated app, JSON state, reports, and handoffs.

The app stores practice history in browser local storage. Obsidian remains the durable project planning and review system.

## Scope Boundary

In scope for v1:

- Official-format-aware practice.
- Original seed drills and prompt banks.
- Rubric-based production scoring.
- Progress logging and app state export/import.
- Vault-native templates for recurring review.

Out of scope for v1:

- Claiming official score prediction for listening/reading.
- Reusing copyrighted official practice items in full.
- Automatic French speech scoring that pretends to replace a human rater.
- Immigration advice beyond linking to official sources and training targets.

## Readiness Policy

The system should recommend booking only when the learner has repeated evidence across full mocks:

- Listening and reading raw readiness is stable above the NCLC 7 training threshold.
- Writing and speaking rubric scores are at least 10/20, preferably 14/20+ for buffer.
- No skill is consistently weaker than the rest.
- Error logs show the same failure modes are shrinking over time.
