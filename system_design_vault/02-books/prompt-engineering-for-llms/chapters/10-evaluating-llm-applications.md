---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Prompt Engineering for LLMs"
authors: "John Berryman; Albert Ziegler"
chapter: "10"
chapter_title: "Evaluating LLM Applications"
source_path: "/Users/saumyamehta/DS interview prep/books/Prompt Engineering for LLMs- The Art and Science of Building.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 10 - Evaluating LLM Applications

## Reading Status

Direct source reading pass completed for chapter 10 from the local user-provided PDF extraction span. This note is original synthesis only; it avoids raw text dumps, copied code listings, copied figures, copied tables, and long excerpts.

## Core Idea

Evaluation should be built before the application hardens. It guides prompt, model, architecture, and rollout decisions by turning subjective model behavior into comparable evidence. Evaluation can target the model, one prompt interaction, or the full application loop.

Agent Studio implication: the content studio must treat evals as production infrastructure. Every route change needs offline evidence, online monitoring hooks, and trace fields that make regressions diagnosable.

## What To Test

Model swaps are best tested against broad regression harnesses unless different models are used for different units. Prompt and parameter changes need unit-level tests on the affected interaction. Architecture changes need end-to-end tests that cover the full loop.

Agent Studio implication: store route-change type and required eval scope together. Prompt edits, retrieval changes, reranker changes, workflow topology changes, and model swaps should not share the same approval gate.

## Example Suites

A simple example suite contains a small diverse set of inputs, a script that renders prompts and completions, and a way to inspect diffs. It does not automatically prove correctness, but it creates disciplined qualitative review before statistical harnesses exist.

Agent Studio implication: every new content route should begin with a curated example suite covering typical, edge, adversarial, and brand-sensitive cases. Diffs should show rendered prompt, selected sources, output, extracted claims, and QA notes.

## Sample Sources

Examples can come from existing records, app usage, or synthetic generation. Existing records are valuable when they approximate the real problem. App usage is realistic but raises consent, privacy, stale-data, and label-quality issues. Synthetic examples scale but can be simplistic or biased toward the generating model.

Agent Studio implication: source eval datasets need provenance, consent class, freshness, generator model if synthetic, label origin, and intended route coverage. Synthetic evals should not be the only gate for switching away from the model that generated them.

## Output Tests

Gold-standard matching works for binary, classification, or simple structured outputs. Partial matching can focus on a critical aspect, such as using the right tool or producing parseable schema. Functional testing works when outputs can be executed, parsed, compiled, validated, or checked against external constraints.

Agent Studio implication: use functional tests wherever possible: citation URL resolves, claim is supported by retrieved source, JSON parses, platform limits pass, no banned policy class appears, generated code/build artifact renders, and final asset satisfies required dimensions.

## LLM Assessment

LLM-as-judge can evaluate natural-language outputs, but it should be framed as third-party assessment rather than self-grading. The chapter recommends SOMA-style assessments: specific questions, ordinal scales, and multiple aspects. Human agreement should ground model judges, and the judge output should be treated as relative quality evidence rather than absolute truth.

Agent Studio implication: evaluator prompts should be versioned and calibrated. Judge records should capture aspect definitions, scale anchors, model, temperature, rubric version, human calibration sample, and disagreement cases.

## Offline Evaluation Choices

Offline eval requires both an input source and an output test. The practical combinations are existing records plus gold/functional tests, app usage plus acceptance-derived labels, synthetic situations plus model/human assessment, and mixed suites for broader coverage.

Agent Studio implication: eval manifests should explicitly state what the suite can and cannot prove. A source-recall eval does not prove final script quality; a brand-voice eval does not prove factual grounding.

## Online Evaluation

Online evaluation tests changes with real users through A/B or related experiments. It is more valid but lower bandwidth, slower, and riskier than offline evaluation. The application must support multiple modes behind flags and have predefined success and guardrail metrics.

Agent Studio implication: route registry entries should be flaggable, staged, and reversible. Online rollout must track both user-facing quality and safety/operational guardrails.

## Metrics

The chapter groups online metrics into direct feedback, functional correctness, user acceptance, achieved impact, and incidental measurements. Direct feedback is high-quality but intrusive. Acceptance and impact often matter most. Incidental metrics such as latency, error rate, and conversation length help diagnose regressions even when they do not directly measure goodness.

Agent Studio implication: content metrics should include source recall, citation validity, factual correction rate, approval rate, revision count, publish acceptance, downstream engagement, latency, cost, policy intervention rate, and human override rate.

## Datastore Requirements

Agent Studio should store evaluation records:

- `eval_dataset`: source, consent class, route coverage, labels, synthetic-generation metadata, and freshness.
- `eval_case`: input artifact set, expected behavior, gold or rubric, and risk tags.
- `eval_run`: route version, model/provider versions, prompt hashes, outputs, scores, cost, latency, and trace pointer.
- `judge_rubric`: aspect list, ordinal anchors, evaluator prompt, model, calibration evidence, and known blind spots.
- `online_experiment`: variants, assignment unit, primary metric, guardrails, exposure, result, and rollout decision.

## Failure Modes

- Shipping prompt changes without a stable example suite.
- Treating LLM judge scores as absolute correctness.
- Using synthetic evals generated by the incumbent model as the only comparison gate.
- Measuring only final answer quality and missing latency/cost regressions.
- Asking broad judge questions instead of aspect-specific rubric questions.
- Running online tests without predefined guardrails and rollback triggers.

## Agent Studio Design Implications

- Eval artifacts should be linked to source snapshots and route versions.
- Offline eval should cover both unit tasks and end-to-end content loops.
- Online eval should be deliberate, flag-based, and guarded.
- Human calibration is required for high-stakes judge rubrics.
- Every route change proposal should include expected metric movement and residual risk.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-generalist-agents-open-ended-worlds]] - Stanford CS25, "Generalist Agents in Open-Ended Worlds" ([YouTube](https://www.youtube.com/watch?v=wwQ1LQA3RCU)).
- [[../../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Introduction to Transformers" ([YouTube](https://www.youtube.com/watch?v=XfpMkf4rD6E)).
