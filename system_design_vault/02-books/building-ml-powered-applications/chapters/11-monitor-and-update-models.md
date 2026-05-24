---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Building Machine Learning Powered Applications"
authors: "Emmanuel Ameisen"
chapter: "11"
chapter_title: "Monitor and Update Models"
source_path: "/Users/saumyamehta/DS interview prep/books/building-machine-learning-powered-applications-going-from-idea-to-product.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# Building ML Powered Applications - Chapter 11: Monitor and Update Models

## Source Reading Scope

Direct-read extraction span: `/tmp/building_ml_powered_applications_text.txt` lines 7553-8796.

This note is original synthesis only. It does not preserve raw source text.

## Core Takeaways

Monitoring is how production ML systems notice drift, abuse, quality loss, and refresh needs. A model should be monitored like software, but with extra attention to prediction quality, input distribution, delayed labels, and business impact.

The chapter separates performance metrics from business metrics. Performance metrics track model quality, but ground truth may be delayed, biased, or unavailable. Business metrics capture the product outcome but can be influenced by many non-model factors. Good monitoring needs both.

CI/CD for ML requires more than a software test suite. Teams need safe deployment patterns such as shadow mode, canaries, A/B tests, and experiment platforms. New models should be compared against current behavior before they are fully exposed.

A/B testing is powerful but easy to misuse. Group assignment, sample size, duration, statistical significance, independent groups, and infrastructure all matter. Bandits and contextual bandits add adaptive allocation but increase complexity.

## Agent Studio Design Implications

- Monitor model/retrieval quality, source freshness, latency, cost, user overrides, publish outcomes, and business/content metrics together.
- Use shadow evaluation for new prompts, rerankers, extraction methods, and provider routes before promoting them.
- Gate memory or prompt updates with canary-style exposure and rollback.
- Track delayed feedback separately from immediate signals so the system does not overreact to noisy short-term metrics.
- Build experiment infrastructure before allowing autonomous agents to optimize production behavior.

## Failure Modes To Guard Against

- Treating green tests as proof that production model behavior is healthy.
- Retraining or changing prompts without comparison against current behavior.
- Running experiments without enough sample size, clean assignment, or a clear success metric.
- Optimizing short-term engagement while damaging long-term user trust or output quality.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
- [[../../../02-lectures/stanford/cs25-aligning-open-language-models]] - Stanford CS25, "Aligning Open Language Models" ([YouTube](https://www.youtube.com/watch?v=AdLgPmcrXwQ)).
