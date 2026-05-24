---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Prompt Engineering for LLMs"
authors: "John Berryman; Albert Ziegler"
chapter: "7"
chapter_title: "Taming the Model"
source_path: "/Users/saumyamehta/DS interview prep/books/Prompt Engineering for LLMs- The Art and Science of Building.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 7 - Taming The Model

## Reading Status

Direct source reading pass completed for chapter 7 from the local user-provided PDF extraction span. This note is original synthesis only; it avoids raw text dumps, copied formulas, copied code listings, copied figures, copied tables, and long excerpts.

## Core Idea

The chapter shifts from prompt input to model output. A useful completion has controlled preamble, recognizable start and end, minimal irrelevant postscript, parseable format, bounded generation, quality signals, and an appropriate model choice.

Agent Studio implication: route quality depends on output control as much as prompt quality. The datastore needs completion-boundary, parser, confidence, model-selection, and fallback records.

## Completion Preamble

Preambles can be structural boilerplate, useful reasoning, or unwanted fluff. Structural boilerplate is often better placed in the prompt. Reasoning preambles can improve difficult answers but may need to be hidden or separated. Fluff should be banished behind the answer or eliminated when programmatic parsing matters.

Agent Studio implication: output schemas should separate reasoning/scratchpad, answer, explanation, citations, and metadata. Do not let the parser guess from prose when a known section boundary can be enforced.

## Recognizable Boundaries

The chapter emphasizes recognizable starts and ends for extraction and cost control. Stop sequences and streaming cancellation can prevent paying for useless postscript tokens. Some structures have simple substring stops; others require indentation, bracket, or parser-aware end detection.

Agent Studio implication: each route should store start detector, end detector, stop sequences, streaming cancellation policy, and parser behavior.

## Logprobs As Signals

Logprobs expose how probable the model considered generated or prompt tokens. They can support completion-quality heuristics, candidate ranking, classification confidence, calibration, and detection of surprising prompt regions. They are model/provider dependent and not perfectly deterministic.

Agent Studio implication: logprobs are telemetry, not truth. Store provider support, availability, aggregation method, thresholds, and calibration dataset before using them for gating.

## Classification With LLMs

The chapter shows that LLMs can classify when prompted to choose among fixed labels, but label tokenization can distort probabilities if labels share prefixes. Calibration may require shifting token/logit probabilities or using logit bias. Classification thresholds should be tuned against ground truth.

Agent Studio implication: LLM classifiers need label-token design, calibration, threshold policy, and confusion-matrix evals. Do not treat the model's chosen label as a calibrated probability.

## Critical Prompt Points

Logprobs on echoed prompt text can identify surprising or information-dense locations. This can catch typos, unusual phrasing, or places where the model is likely to be uncertain.

Agent Studio implication: prompt linting can use model signals, but tests must tolerate numerical variation and should not rely on exact logprob equality.

## Model Choice

The chapter recommends choosing by intelligence, speed, cost, ease of use, functionality, and special requirements such as data residency, licensing, open weights, or provider constraints. The best model is route-specific, and the choice should remain revisable.

Agent Studio implication: provider/model selection belongs in the route registry with benchmark evidence, cost/latency profile, capability flags, and rollback options.

## Fine-Tuning Decision

Fine-tuning can internalize format, style, prior distributions, and task behavior, but it requires examples and can reduce generic capability. The chapter distinguishes full fine-tuning, LoRA-style parameter-efficient tuning, and soft prompting. It also notes loss masking as a way to train only on the answer portion.

Agent Studio implication: fine-tuning is a continuation of prompt engineering by other means. It should be proposed only after prompt/RAG/tool routes have a measured gap and enough high-quality training examples exist.

## Datastore Requirements

Agent Studio should store output-control records:

- `completion_contract`: answer section, reasoning section, metadata section, start/end detectors, stop sequences, and parser version.
- `generation_observation`: raw completion, extracted answer, finish reason, token count, latency, cost, logprobs summary, and parser errors.
- `classification_policy`: labels, label tokens, calibration constants, threshold, confusion matrix, and fallback for low confidence.
- `model_selection_record`: model/provider, capability flags, cost, latency, data boundary, logprob support, tool support, and eval result.
- `adaptation_option`: prompt/RAG/tool change, full fine-tune, LoRA/adapter, soft prompt, data requirement, risk, and rollback plan.

## Failure Modes

- Paying for long preambles or postscripts that are discarded.
- Parsing answers without recognizable boundaries.
- Using stop sequences that trigger too early because they are not anchored.
- Treating logprobs as stable deterministic values.
- Designing labels that share first tokens and distort classification.
- Hardcoding a model choice so it cannot be swapped after evals.
- Fine-tuning without enough high-quality examples or without checking regression.

## Agent Studio Design Implications

- Completion extraction should be a first-class trace artifact.
- Model routes should preserve both raw completion and extracted result.
- Low-confidence or parser-failed completions should route to retry, stronger model, tool verification, or human review.
- Classification gates need calibrated thresholds and task-specific metrics.
- Fine-tuning proposals should include loss-mask policy, dataset readiness, model-capability risk, and serving-cost impact.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-generalist-agents-open-ended-worlds]] - Stanford CS25, "Generalist Agents in Open-Ended Worlds" ([YouTube](https://www.youtube.com/watch?v=wwQ1LQA3RCU)).
- [[../../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Introduction to Transformers" ([YouTube](https://www.youtube.com/watch?v=XfpMkf4rD6E)).
