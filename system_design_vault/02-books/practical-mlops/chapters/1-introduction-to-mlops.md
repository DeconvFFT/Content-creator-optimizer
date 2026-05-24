---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Practical MLOps"
authors: "Noah Gift; Alfredo Deza"
chapter: "1"
chapter_title: "Introduction to MLOps"
source_path: "/Users/saumyamehta/DS interview prep/books/Practical MLOps_ Operationalizing Machine Learning Models.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# Practical MLOps - Chapter 1: Introduction to MLOps

## Source Reading Scope

Direct-read extraction span: `/tmp/practical_mlops_text.txt` lines 630-1352.

This note is original synthesis only. It does not preserve raw source text.

## Core Takeaways

MLOps is the application of DevOps automation and feedback loops to systems where data and models are first-class production assets. The chapter emphasizes that production ML work is not only modeling; it includes software engineering, data engineering, platform operations, monitoring, business alignment, and iteration.

The hierarchy is important: DevOps foundations come first, then data automation, then platform automation, then mature MLOps. Teams that skip the lower layers usually compensate with manual work and fragile heroics.

CI/CD is framed as shared infrastructure, not one person's responsibility. A production ML team should treat build, lint, test, packaging, deployment, and monitoring as collective operating discipline.

MLOps adds extra failure surfaces to ordinary software operations: model retraining, data drift, model packaging, audit trails, and production feedback. The point is not just to deploy once, but to make model and data updates routine, observable, and reversible.

The chapter's "rule of 25%" is a useful planning heuristic: software engineering, data engineering, modeling, and the business problem all deserve serious attention. Over-optimizing one quadrant while ignoring the others creates brittle systems.

## Agent Studio Design Implications

- Build Agent Studio around production loops, not demos: source intake, extraction, retrieval, generation, review, deployment, monitoring, and feedback.
- Require CI checks for ingestion logic, prompt bundles, tool schemas, evaluator code, and retrieval/index configuration.
- Treat data-store operations as production operations: versioned manifests, provenance records, extraction logs, and rollback points.
- Make business/user value part of evaluation; do not let model or retrieval metrics become the only success definition.
- Use the hierarchy as an adoption roadmap: first reliable repo/test/deploy mechanics, then automated source/index pipelines, then platform automation, then continuous agent improvement.

## Failure Modes To Guard Against

- Treating agent work as research notebooks with no deployment discipline.
- Building model/prompt logic before source and data automation are reliable.
- Depending on manual review as the only quality gate.
- Measuring only accuracy-like metrics while ignoring cost, latency, uptime, user value, and maintenance effort.
- Assuming MLOps is a job title instead of a team behavior.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-state-space-transformer-tradeoffs]] - Stanford CS25, "On the Tradeoffs of State Space Models and Transformers" ([YouTube](https://www.youtube.com/watch?v=OyimE74UMF8)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
