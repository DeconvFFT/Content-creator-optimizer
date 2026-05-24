---
type: sprint
project: tcf-canada-training
status: active
updated: 2026-05-17
---

# Current Sprint

## Sprint Goal

Create a dedicated Obsidian vault and first usable TCF Canada practice system from the supplied deep-research plan.

## Done

- Created a separate vault at `tcf_canada_training/`.
- Created three-layer memory folders: `raw/`, `wiki/`, and `output/`.
- Added project MOC, schema, log, HLD, LLD, source ledger, active context, exam target note, curriculum note, prompt bank, and practice templates.
- Verified core official-source anchors from FEI and IRCC as of 2026-05-17.
- Built the first local practice app under `output/viewers/`.
- Verified the app with static JS/JSON checks, desktop screenshot, mobile screenshot, and a Playwright smoke test covering tabs, listening/reading scoring, writing word count, mock save, and Vault Export.

## In Progress

- Add more drill-bank volume after the first app pass proves the workflow.

## Next

1. Use the first diagnostic/baseline session to set the learner's starting band.
2. Expand the listening and reading banks from original practice content.
3. Add a second-rater workflow for speaking feedback if a coach or language partner becomes available.
4. Add optional backend vault-write support if browser local storage and Markdown export are not enough.
