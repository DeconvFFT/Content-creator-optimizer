---
type: book-chapter-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-17
source_title: "Designing Machine Learning Systems"
source_author: "Chip Huyen"
source_path: "/Users/saumyamehta/DS interview prep/books/Designing machine learning systems - an iterative process.pdf"
rights_status: user_provided_local
chapter: 6
chapter_title: "Model Development and Offline Evaluation"
source_lines: "6347-7964"
---

# Chapter 6 - Model Development And Offline Evaluation

## Reading Status

Direct source reading and official cross-check completed for chapter 6. This note is compact original synthesis for Agent Studio design use and does not include raw book text or long excerpts.

## Core Thesis

Model development is iterative engineering under constraints. Choosing a model is not only about headline accuracy; it depends on task fit, baselines, debuggability, reproducibility, scale, cost, latency, robustness, calibration, and slice performance. Offline evaluation is necessary but not sufficient for production trust.

For Agent Studio, this maps directly to choosing prompts, model providers, rerankers, judges, tools, graph policies, and agent routes. A better benchmark score does not justify a route if it is harder to debug, too slow, too expensive, poorly calibrated, or weak on critical slices.

## Model Selection Should Start Simple

The chapter argues for beginning with heuristics and simple models before complex systems. Simple baselines validate the problem framing, data, and pipeline. Complex models are justified only after simpler phases plateau or requirements demand them.

Agent Studio implications:

- Start each workflow with a deterministic or simple baseline: template, rules, static retrieval, keyword search, or single-pass prompt.
- Promote multi-agent planning only when it beats simpler routes on task quality, observability, latency, or maintainability.
- Keep baselines alive. They are needed for regression tests, fallback behavior, cost comparisons, and stakeholder explanation.

## Ensembles And Complexity

The chapter covers ensemble methods such as bagging, boosting, and stacking. Ensembles often improve performance, but they add training, serving, debugging, and latency complexity.

Agent Studio implications:

- Multi-agent systems are ensemble-like. Combining planner, retriever, writer, critic, and judge can improve quality while making attribution harder.
- Use ensemble routes for high-value or high-risk work, not every small task.
- Track which sub-agent or route changed the final artifact so failures can be debugged.
- Compare ensemble quality gains against extra cost, latency, and failure surface.

## Experiment Tracking And Versioning

The chapter treats experiment tracking and versioning as required for comparison and reproducibility. A useful run log includes code, data, hyperparameters, artifacts, metrics, samples, predictions, labels, system metrics, and environment details. Data versioning is harder than code versioning but equally important.

Agent Studio implications:

- Version prompts, models, source snapshots, extracted text, chunking, embeddings, vector indexes, rerankers, graph edges, tools, graders, and reviewer rubrics.
- Store run artifacts: retrieval candidates, selected context, generated output, citations, judge scores, trace IDs, user edits, and final decision.
- Compare candidate routes with the same source and eval snapshot unless the experiment is explicitly testing data changes.
- Treat source deletion, privacy updates, or user-data retention rules as constraints on reproducibility.

## Debugging ML Systems

The chapter emphasizes that ML failures can be silent, slow to validate, and cross-functional. Root causes may live in theory, implementation, hyperparameters, data, features, or infrastructure. Practical debugging starts simple, overfits a tiny batch, and controls randomness.

Agent Studio implications:

- Silent failures include fluent unsupported claims, missing citations, overconfident judges, bad tool calls, stale docs, and output that satisfies format while failing the user goal.
- Debug with tiny fixtures: one source, one query, one expected citation, one workflow trace.
- Add route-level determinism where possible: pinned prompts, model versions, seeds or temperature, source snapshots, and deterministic post-processing.
- Keep failure triage cross-functional: source ingestion, retrieval, generation, product UX, policy, and infrastructure can all cause the visible error.

## Distributed Training And Scale

The chapter explains why large-scale training needs out-of-core processing, checkpointing, data parallelism, model parallelism, pipeline parallelism, and careful treatment of stragglers, stale gradients, batch size, and resource imbalance.

Agent Studio implications:

- Even if Agent Studio does not train foundation models, the same systems thinking applies to indexing, embedding, eval, and batch synthesis.
- Large ingestion runs should checkpoint progress and be resumable by source, chapter, chunk, and note.
- Parallel processing must not break provenance ordering or duplicate detection.
- Batch size and concurrency should be tuned for throughput without starving interactive workflows.

## AutoML And Automated Search

The chapter distinguishes practical hyperparameter tuning from expensive architecture search and learned optimizers. The useful lesson is not that everything should be automated; it is that search spaces, evaluation sets, and validation discipline determine whether automation helps.

Agent Studio implications:

- Automate prompt, retrieval, reranking, and route parameter search only against validation sets, never the final test set.
- Search spaces need guardrails: allowed tools, max context, citation threshold, reranker count, model route, temperature, and escalation policy.
- Automated optimization should preserve interpretability. A slightly weaker route may be better if it is easier to explain and operate.

## Offline Evaluation

The chapter frames metrics as meaningless without baselines. Useful baselines include random, heuristic, zero-rule, human, and existing systems. Offline evaluation should test robustness, fairness, directional expectations, calibration, confidence, and slices, not just aggregate accuracy.

Agent Studio implications:

- Compare every agent route against a heuristic/source-first baseline and the current production route.
- Add perturbation tests for OCR noise, formatting changes, paraphrased user asks, source order changes, injected instructions, and missing metadata.
- Add invariance tests: irrelevant user/source attributes should not change answer quality, citation support, or moderation outcome.
- Add directional tests: stronger source evidence should increase confidence; missing citations should lower publish readiness; higher risk should increase review requirements.
- Track calibration for judges and confidence scores. If the system says high confidence, it should be right at a corresponding rate.
- Use confidence thresholds to decide whether to publish, ask for human review, request more sources, or abstain.

## Slice-Based Evaluation

The chapter argues that aggregate metrics can hide critical failures and even reverse conclusions. Slices must be chosen using domain knowledge, error analysis, and sometimes automated slice discovery.

Agent Studio implications:

- Required slices include source type, provider, topic, recency, rights status, workflow, audience, platform, model route, language, document length, retrieval depth, and risk tier.
- Track minority but high-impact slices such as long PDFs, lecture videos, conflicted sources, unsupported claims, tool-use tasks, and safety-sensitive topics.
- Eval data must contain enough correctly labeled examples per slice, or the slice metric is decorative.

## Failure Modes

- Chasing state of the art before validating a simple baseline.
- Promoting a multi-agent route without attribution and reproducibility.
- Logging final outputs but not the data, prompt, retrieval, and trace needed to reproduce them.
- Optimizing prompts or routes on the final test set.
- Reporting only aggregate metrics while critical slices fail.
- Treating confidence as a UI label instead of a calibrated operational decision.
- Assuming offline eval success guarantees production performance.

## Agent Studio Design Commitments

- Maintain simple baselines for each workflow.
- Version all data, prompts, tools, routes, eval sets, and artifacts.
- Store trace-level artifacts for every experiment and production run.
- Require perturbation, invariance, directional, calibration, confidence, and slice checks for promotion.
- Use offline eval as a gate to staged production testing, not as the final proof.

## Follow-Ups

- Define baseline routes for retrieval, chapter-note synthesis, claim checking, and content generation.
- Add an experiment schema that records source snapshot, route config, artifacts, metrics, and reviewer labels.
- Build slice requirements for Agent Studio eval suites.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
- [[../../../02-lectures/stanford/cs25-aligning-open-language-models]] - Stanford CS25, "Aligning Open Language Models" ([YouTube](https://www.youtube.com/watch?v=AdLgPmcrXwQ)).
