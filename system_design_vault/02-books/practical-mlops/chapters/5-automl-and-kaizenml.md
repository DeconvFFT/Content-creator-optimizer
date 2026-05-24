---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Practical MLOps"
authors: "Noah Gift; Alfredo Deza"
chapter: "5"
chapter_title: "AutoML and KaizenML"
source_path: "/Users/saumyamehta/DS interview prep/books/Practical MLOps_ Operationalizing Machine Learning Models.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# Practical MLOps - Chapter 5: AutoML and KaizenML

## Source Reading Scope

Direct-read extraction span: `/tmp/practical_mlops_text.txt` lines 4855-6135.

This note is original synthesis only. It does not preserve raw source text.

## Core Takeaways

AutoML is useful but narrow. It automates model selection and training tasks on prepared data; it does not solve data quality, feature reuse, deployment, monitoring, governance, or product alignment.

KaizenML is the broader principle: continuously improve the whole ML system. The chapter treats model quality, software quality, data quality, feature quality, deployment quality, and customer feedback as one improvement loop.

Feature stores are presented as a concrete automation pattern. They reduce repeated feature work, support reuse across training and prediction, and create a shared registry of high-quality model inputs.

Explainability is part of production operations. SHAP, ELI5, and provider-native explainability tools are analogous to dashboards: they help the team inspect why the model behaves the way it does and catch mismatches between learned behavior and stakeholder expectations.

The chapter favors pragmatic automation over craft identity. Teams should use AutoML, pretrained models, provider APIs, open-source tooling, and managed platforms when they improve speed and quality.

## Agent Studio Design Implications

- Do not frame Agent Studio optimization as "better prompts only." Improve the whole loop: source quality, extraction quality, chunking, embeddings, retrieval, reranking, generation, evaluation, review, and feedback.
- Build reusable feature-like assets for agents: source metadata, provenance labels, entity graphs, chunk quality scores, citation confidence, user feedback signals, and task outcome labels.
- Treat evaluation explainability as an operational dashboard: why did the agent retrieve this, choose this tool, cite this source, or fail this task?
- Use managed or automated tools where they reduce undifferentiated work, but keep provenance, export, and replay paths.
- Make continuous improvement explicit: every failed extraction, weak answer, bad citation, and user correction should map to an actionable improvement category.

## Failure Modes To Guard Against

- Over-crediting AutoML-like automation while leaving ingestion and governance manual.
- Rebuilding the same source features, metadata, or evaluation signals in isolated workflows.
- Optimizing model or prompt choice without improving data and feedback loops.
- Shipping opaque agent behavior without explanation surfaces for retrieval, tool calls, and final answers.
- Rejecting provider or open-source automation because it feels less technically impressive than custom work.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-state-space-transformer-tradeoffs]] - Stanford CS25, "On the Tradeoffs of State Space Models and Transformers" ([YouTube](https://www.youtube.com/watch?v=OyimE74UMF8)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
