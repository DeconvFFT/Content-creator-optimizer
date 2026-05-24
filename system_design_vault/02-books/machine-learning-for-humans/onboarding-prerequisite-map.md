---
type: local-book-support-note
project: agent-studio-system-design
status: support_ready
updated: 2026-05-19
source_id: local_books.machine_learning_generic
rights_status: user_provided_local
provenance_status: user_confirmed_official_clean
stores_raw_source_text: false
stores_long_excerpts: false
source_scope:
  - "/Users/saumyamehta/DS interview prep/books/machine_learning.pdf"
  - "direct-read local slices: introduction, supervised learning, regression/classification, overfitting, cross-validation, non-parametric learner overview"
related:
  - "[[../islp/statistical-learning-validation]]"
  - "[[../aima/agent-planning-foundations]]"
  - "[[../designing-machine-learning-systems/chapters/6-model-development-and-offline-evaluation]]"
  - "[[../ai-engineering/chapters/3-evaluation-methodology]]"
  - "[[../../03-patterns/evaluation/eval-design-canon]]"
  - "[[../../05-ingestion-runs/deferred-local-corpus-queue]]"
---

# Agent Studio Onboarding Prerequisite Map

## Purpose

This is a support note for onboarding agents and human reviewers who need the prerequisite vocabulary behind the deeper Agent Studio canon. It uses the deferred local `Machine Learning for Humans` PDF only for compact concept grounding, then routes architecture decisions back to canon-ready notes. It is not a replacement for ISLP, AIMA, Designing Machine Learning Systems, AI Engineering, or the release-gate notes.

## Boundary

Use this note when a downstream agent needs to explain or disambiguate basic ML terms before applying a route gate. Do not use it as standalone architecture evidence for production decisions.

## Concept Map

| Concept | Working meaning for Agent Studio | Route implication |
|---|---|---|
| AI | A broad family of systems that perceive, decide, plan, act, or support decision-making. | Do not call every model call an agent. A route needs environment, action, observation, and authority contracts before it becomes agentic. |
| Machine learning | A system learns patterns from observed examples rather than only following handwritten rules. | Treat data lineage, objective, training/eval split, and deployment context as part of the product design, not model trivia. |
| Supervised learning | Training from examples with known labels or targets. | Source-labeled evals, reviewer labels, preference pairs, and classification thresholds need label policy and reviewer provenance. |
| Regression | Predicting a continuous value. | Use for scores, cost estimates, latency estimates, rank scores, and confidence-like quantities only when calibration and error bounds are visible. |
| Classification | Assigning a discrete label or class. | Moderation, routing, source eligibility, no-answer decisions, and publish/block gates need threshold and false-positive/false-negative policy. |
| Feature | Input signal used by a model or decision rule. | Agent Studio should version extraction, normalization, metadata, embedding, and source features so ingest/query parity can be reviewed. |
| Target label | The value the model is trained or evaluated to predict. | Label wording, label source, ambiguity, and reviewer disagreement must be stored before labels drive tuning or gates. |
| Loss/cost function | A numerical penalty for being wrong. | A route optimizes what it measures; score functions must include source support, safety, latency, cost, and human-review burden where relevant. |
| Gradient descent | Iterative parameter improvement by following a loss signal. | Training and tuning runs need objective, dataset, hyperparameters, run lineage, stop criteria, and rollback records. |
| Overfitting | A model or route fits the examples too specifically and fails on new cases. | Prompt, retriever, reranker, judge, or route improvements must be checked on held-out and failure-slice cases before promotion. |
| Regularization | A constraint or penalty that discourages overly complex explanations. | Route design should prefer simpler interventions before finetuning, multi-agent loops, or high-budget reasoning. |
| Hyperparameter | A setting chosen outside direct parameter learning. | Top-k, thresholds, cache TTLs, sample counts, temperature, reranker cutoffs, and retry budgets are release metadata. |
| Cross-validation | Repeated held-out validation across data slices. | Agent Studio should preserve selection versus assessment splits and avoid reusing the same examples to tune and approve a route. |
| False positive | The system says yes when the correct answer is no. | Publishing, moderation, source eligibility, and security gates need an explicit cost for wrongly allowing or wrongly blocking. |
| False negative | The system says no when the correct answer is yes. | Safety, support escalation, retrieval recall, and source omission can have asymmetric risk; thresholds must reflect that. |
| Non-parametric learner | A flexible model whose behavior is shaped strongly by stored examples. | Memory, nearest-neighbor retrieval, example banks, and vector stores need snapshot, distance, filtering, and stale-example controls. |
| Distance metric | The definition of "near" or "similar." | Embedding retrieval quality depends on metric choice, vector representation, metadata filters, and reranker policy. |
| Decision tree | A sequence of splits that routes examples by feature tests. | Agent route policy should be inspectable: branch rules, fallback states, and stop conditions should not be hidden in prose. |
| Ensemble | Multiple models or rules combined for a decision. | Multi-judge, multi-agent, or model-panel routes need aggregation policy, disagreement handling, cost budget, and escalation rules. |

## How To Use This In Agent Studio

- Use this map to translate beginner questions into the correct canon surface: eval, retrieval, serving, agent, security, or governance.
- If a route change changes a threshold, feature, label, hyperparameter, or distance metric, treat it as a release-controlled behavior change.
- If a metric improves on examples that shaped the change, require a held-out assessment or failure-slice replay before promotion.
- If a classifier gates publishing, tool authority, source acceptance, or privacy-sensitive behavior, document false-positive and false-negative costs explicitly.
- If a retrieval route depends on "similarity," route reviewers need the embedding model, distance operator, filter path, rerank policy, and recall evidence.

## Escalation To Canon Notes

| If the question is about... | Use this canon surface |
|---|---|
| Held-out evaluation, cross-validation, and model selection | [[../islp/statistical-learning-validation]] |
| Agent environments, perception, actions, rationality, and planning | [[../aima/agent-planning-foundations]] |
| ML system deployment, monitoring, and production feedback | [[../designing-machine-learning-systems/chapters/6-model-development-and-offline-evaluation]] and [[../../03-patterns/system-design/production-agent-studio-canon]] |
| AI application eval methodology | [[../ai-engineering/chapters/3-evaluation-methodology]] and [[../../03-patterns/evaluation/eval-design-canon]] |
| Retrieval similarity, nearest neighbors, and reranking | [[../../03-patterns/retrieval/reranking-search-kg-patterns]] |
| Route changes controlled by thresholds or experiments | [[../../04-agent-studio-implications/Route Change Proposal Template]] |

## Agent Studio Design Implications

- Add a lightweight onboarding lane to retrieval so new agents can resolve basic terms before entering dense release-gate notes.
- Keep glossary support separate from architecture canon; glossary notes explain terms, canon notes decide production behavior.
- Surface asymmetric error costs in route cards whenever a binary classifier, threshold, or approval gate changes user-visible behavior.
- Treat similarity as a product contract, not a vague embedding property.
- Use simpler baselines and held-out examples before escalating to finetuning, multi-agent panels, or high-budget reasoning.

## Safe Notes Strategy

This note is original synthesis from a small local support slice plus existing canon links. It stores no raw source text, copied tables, exercises, figures, or long excerpts. The source remains deferred for architecture canon; only this onboarding prerequisite map is promoted to `support_ready`.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
- [[../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
