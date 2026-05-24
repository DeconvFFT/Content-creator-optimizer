---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Building Machine Learning Powered Applications"
authors: "Emmanuel Ameisen"
chapter: "7"
chapter_title: "Using Classifiers for Writing Recommendations"
source_path: "/Users/saumyamehta/DS interview prep/books/building-machine-learning-powered-applications-going-from-idea-to-product.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# Building ML Powered Applications - Chapter 7: Using Classifiers for Writing Recommendations

## Source Reading Scope

Direct-read extraction span: `/tmp/building_ml_powered_applications_text.txt` lines 5464-6097.

This note is original synthesis only. It does not preserve raw source text.

## Core Takeaways

The chapter shows how to turn model behavior into user-facing recommendations. Classification is not the product; the product is actionable guidance that helps the user improve an input or decision.

Recommendations can come from feature statistics, global feature importance, model scores, and local feature importance. The right method depends on whether the advice must be global, personalized, interpretable, calibrated, fast, or robust.

The ML Editor example chooses a model that is not purely best by aggregate performance. It prefers a model whose features are understandable enough to produce useful recommendations. Product utility beats leaderboard-style scoring.

The chapter is especially relevant for Agent Studio because agent output should often be advisory and editable, not final. The system should expose why a draft, source, claim, or route is recommended and how the user can improve it.

## Agent Studio Design Implications

- Turn evaluator and verifier outputs into actionable feedback, not just pass/fail verdicts.
- Prefer explainable signals for user-facing critique: missing source, weak evidence, stale source, unsupported claim, off-brand tone, or risky latency path.
- Calibrate scores before exposing them as confidence or readiness indicators.
- Use local explanations for specific draft issues and global explanations for project-wide coaching.
- Let users override recommendations and use those overrides as labeled feedback.

## Failure Modes To Guard Against

- Optimizing for internal metrics while producing vague or unactionable advice.
- Showing model confidence without calibration or explanation.
- Choosing a stronger opaque model when the product needs interpretable recommendations.
- Hiding feedback loops that could improve future recommendations.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
- [[../../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
