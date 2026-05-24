---
type: implementation-handoff
project: tcf-canada-training
status: active
updated: 2026-05-17
---

# Implementation Handoff

## Built

- Dedicated Obsidian vault: `tcf_canada_training/`.
- Three-layer memory structure: `raw/`, `wiki/`, `output/`.
- Official source ledger and raw source notes.
- HLD, LLD, current sprint, decision log, progress dashboard, curriculum, exam-target note, prompt bank, and templates.
- Local-first practice app:
  - `output/viewers/tcf-training-system.html`
  - `output/viewers/tcf-training-system.css`
  - `output/viewers/tcf-training-system.js`
  - `output/viewers/tcf-training-system.json`

## Verified

- JavaScript parse check: `node --check tcf_canada_training/output/viewers/tcf-training-system.js`
- JSON manifest check: `python3 -m json.tool tcf_canada_training/output/viewers/tcf-training-system.json`
- Desktop screenshot: `screenshots/tcf-training-dashboard.png`
- Mobile screenshot: `screenshots/tcf-training-mobile.png`
- Browser smoke: tab navigation, listening answer scoring, reading answer scoring, writing word-count display, mock save, and Vault Export generation.

## How To Use

1. Open `output/viewers/tcf-training-system.html`.
2. Set the baseline after Ev@lang plus a TCF-style diagnostic.
3. Practice through the daily tab and skill tabs.
4. Record mocks after timed full sections.
5. Use the Vault Export tab to create Markdown session notes for `raw/session-notes/`.

## Next Implementation Slice

- Add larger original drill banks.
- Add CSV import for manually scored official/supplementary practice.
- Add AI feedback only after official-source and privacy boundaries are explicit.
- Add optional backend vault-write endpoint if the learner wants app notes saved directly into Obsidian.
