---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "AI Engineering"
authors: "Chip Huyen"
chapter: "3"
chapter_title: "Evaluation Methodology"
source_path: "/Users/saumyamehta/DS interview prep/books/AI Engineering.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 3 - Evaluation Methodology

## Reading Status

Direct source reading pass completed for chapter 3 from the local user-provided PDF extraction span. This note is original synthesis only; it avoids raw text dumps, copied tables, copied figures, copied prompts, and long excerpts.

## Core Idea

Evaluation is the control system for AI engineering. Open-ended foundation-model behavior cannot be managed by demos, vibe checks, or broad public leaderboards alone. A serious evaluation system starts from expected failure modes, makes those failures visible, and combines exact tests, reference-based tests, judge-based tests, comparative signals, and human review where each is appropriate.

For Agent Studio, the chapter's most important message is that evaluation is not a detached report. It is part of the architecture: source selection, retrieval design, route registry, judge configuration, release gates, feedback loops, and monitoring all need eval records that are reproducible and interpretable.

## Why Foundation-Model Evaluation Is Hard

Foundation models are harder to evaluate than traditional task-specific models because their outputs are open-ended, their capabilities can exceed an evaluator's domain expertise, and many systems expose only black-box outputs rather than training data, architecture, or alignment details. Public benchmarks also saturate quickly, while application-specific behavior often depends on workflow context that public benchmarks do not cover.

Design implications:

- Do not treat public benchmark rank as proof that a model works for Agent Studio.
- Evaluate the full system path, not just the base model: prompt, retrieval, graph traversal, tools, memory, judge, guardrails, and UI feedback all change quality.
- Start eval design from failure inventory: hallucination, citation mismatch, wrong tool, wrong route, schema failure, style drift, unsafe action, stale source, and poor recovery.
- If a failure is invisible in traces, redesign the system to expose it before inventing another metric.

## Language Modeling Metrics

Cross entropy, perplexity, bits per character, and bits per byte measure how well a language model predicts sequences. They are useful for understanding training, compression-like fit, contamination suspicion, abnormal text detection, and rough model capability. They are not enough to judge a post-trained assistant's usefulness, because instruction tuning and preference tuning can improve task behavior while changing next-token prediction metrics.

Agent Studio implication: use language-modeling metrics only where they match the decision. They can support extraction-quality checks, anomaly detection, contamination suspicion, or model-adaptation diagnostics, but route promotion should rely on task-level evals.

## Exact Evaluation

Exact evaluation is preferable when the task has an unambiguous outcome. Functional correctness is the strongest version: generated code runs, SQL answers the query, a reservation is made, a workflow completes, or an optimization target improves. Similarity-based evaluation is weaker but useful when references exist.

Useful exact-eval types:

- Functional correctness: execute, verify, or simulate whether the intended operation succeeded.
- Exact match: useful for short factual answers, labels, IDs, and other constrained outputs.
- Lexical similarity: useful for overlap-sensitive text but brittle when many phrasings are valid.
- Semantic similarity: useful when meaning matters more than wording, but dependent on embedding quality.
- Embedding utility tests: evaluate embeddings by downstream retrieval, clustering, classification, or RAG performance rather than by vector aesthetics.

Agent Studio implication: every workflow should ask whether an exact test can be built before using a judge. Tool calls, schema output, retrieval citation validity, SQL generation, publish readiness, file creation, and route metadata can all have exact checks.

## AI As Judge

AI-as-judge is valuable because it can score open-ended outputs at scale without reference answers, but a judge is not an abstract metric. It is a system made of model, prompt, scoring scheme, sampling settings, input construction, and output parser. Changing any of those changes the metric.

Good judge use requires:

- a clearly named criterion;
- a task description;
- a rubric or scoring labels;
- examples when possible;
- judge model/version;
- judge prompt/version;
- sampling settings;
- calibration set;
- known biases;
- cost and latency budget;
- reproducibility and audit records.

Agent Studio implication: judge runs must be first-class datastore records. A score without judge provenance should not be allowed to promote or demote a production route.

## Judge Limitations

AI judges are inconsistent, criterion-dependent, cost-bearing, latency-bearing, and biased. Scores called the same thing across tools may mean different things if prompts and scales differ. Judges can favor their own model family, prefer first or longer answers, reward style over truth, or drift when model providers update behavior.

Risk controls:

- Pin judge model, prompt, parser, and sampling settings.
- Keep a stable calibration set with expected judgments and human-reviewed disagreements.
- Use classification labels where possible rather than vague continuous scores.
- Separate judge criteria instead of asking one score to mean quality, helpfulness, factuality, policy compliance, and style.
- Spot-check production outputs when full evaluation would add too much cost or latency.
- Use exact evaluation and human review to anchor judge reliability.

Agent Studio implication: the evaluation ledger should store judge drift events and distinguish changes in the product route from changes in the evaluator.

## Comparative Evaluation

Comparative evaluation ranks models or routes by asking which output is better. It is often easier than assigning absolute scores and is useful for model selection, preference data, and side-by-side product experiments. It does not prove a model is good enough, only that it tends to beat another candidate under the sampled prompts and evaluator population.

Design implications:

- Comparative eval should be paired with absolute thresholds for task readiness.
- Preference voting is appropriate only when users are qualified to judge the output.
- Some questions should be judged by correctness, not preference.
- Pairwise comparison records need prompt, model/route A, model/route B, evaluator, position order, winner/tie, and rationale if available.
- Ranking algorithms and sampling policies matter; comparing every model pair scales poorly.
- Product-integrated comparisons can give realistic signals but also introduce noisy clicks and incomplete reading.

Agent Studio implication: route comparison should be stored separately from release gates. A route can win a preference comparison and still fail grounding, cost, latency, or safety thresholds.

## Evaluation Datastore Requirements

Chapter 3 implies the following Agent Studio records:

- `eval_dataset`: task slice, source, rights/provenance, reference availability, expected failure mode, and owner.
- `eval_case`: input, context snapshot, expected exact checks, reference outputs, rubric, and tags.
- `eval_method`: exact check, reference similarity, judge, comparative match, human review, or hybrid.
- `judge_profile`: model, prompt, scoring schema, parser, sampling settings, calibration status, and known limitations.
- `eval_run`: route version, source snapshot, model/provider version, evaluator version, timestamp, cost, latency, and pass/fail summary.
- `eval_result`: criterion-specific scores, exact failures, judge explanations, confidence, and artifacts.
- `comparison_match`: side-by-side candidates, position order, evaluator identity/class, winner/tie, and ranking algorithm input.
- `calibration_record`: human-reviewed benchmark cases for judges and expected outputs for exact checks.
- `promotion_gate`: thresholds for factuality, citation validity, schema validity, latency, cost, safety, and user-impact slice.

## Failure Modes

- Evaluating only the base model while the product risk lives in retrieval, tools, memory, or orchestration.
- Treating a leaderboard as sufficient evidence for a specific workflow.
- Using AI-as-judge scores without storing judge model, prompt, rubric, and sampling settings.
- Comparing scores from two different judge prompts as if they were the same metric.
- Letting judge drift look like product improvement or regression.
- Optimizing for lexical overlap when functional correctness is what matters.
- Using preference voting for factual or expert questions that users cannot judge.
- Ranking models by pairwise wins without checking absolute readiness thresholds.
- Sampling too few hard cases and over-trusting easy prompts.
- Failing to include cost and latency of evaluation itself in production guardrail design.

## Agent Studio Design Implications

- Eval design should begin during route design, not after implementation.
- Each route-change proposal should name the eval cases that protect against the intended change's failure modes.
- The datastore should distinguish exact metrics, reference-based metrics, judge metrics, comparative metrics, and human-review metrics.
- Judge prompts should be versioned like production prompts.
- Evaluation dashboards should show criterion-level results, not just aggregate pass rates.
- Retrieval and citation evals should use exact checks where possible: cited source exists, cited source was retrieved, cited claim is supported, and unsupported claims are flagged.
- Agent workflows need functional checks for tool execution, schema validity, state transitions, rollback behavior, and human-approval gates.
- Comparative evals should be used for route selection, but production promotion still needs absolute gates for safety, grounding, latency, cost, and workflow completion.
- User feedback should be converted into eval cases only after classifying whether it is preference, correctness, policy, format, latency, or routing feedback.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
- [[../../../02-lectures/stanford/cs25-aligning-open-language-models]] - Stanford CS25, "Aligning Open Language Models" ([YouTube](https://www.youtube.com/watch?v=AdLgPmcrXwQ)).
