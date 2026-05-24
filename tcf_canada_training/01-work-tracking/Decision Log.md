---
type: decision-log
project: tcf-canada-training
status: active
updated: 2026-05-17
---

# Decision Log

## 2026-05-17 - Create Dedicated Vault

Decision: Use `tcf_canada_training/` as a separate Obsidian vault inside the current repo workspace.

Reason: The user asked for a separate vault for this project and the current workspace permits writing under `/Users/saumyamehta/Gen AI/all-about-llms`.

## 2026-05-17 - Official-First Format Policy

Decision: FEI and IRCC pages are the source of truth for exam format, timing, score-band interpretation, category threshold, retake delay, and validity.

Reason: The supplied PDF is useful planning input, but exam and immigration details can change and must be checked against official sources.

## 2026-05-17 - Estimated Readiness, Not Official Score Prediction

Decision: The app will show raw comprehension accuracy and readiness bands for listening/reading instead of converting raw scores into official TCF scaled scores.

Reason: FEI's QCM scoring uses difficulty-weighted psychometric conversion and does not disclose the raw-to-scaled conversion.

## 2026-05-17 - Static Local App First

Decision: Build v1 as a standalone local HTML/CSS/JS practice app.

Reason: The learner can practice immediately without API keys, Postgres, or model-provider configuration. A backend can be added later if automated file writes, AI feedback, or multi-device sync becomes necessary.
