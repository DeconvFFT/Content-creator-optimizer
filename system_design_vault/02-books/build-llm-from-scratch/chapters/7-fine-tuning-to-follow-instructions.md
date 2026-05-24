---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "Build a Large Language Model (From Scratch)"
authors: "Sebastian Raschka"
chapter: "7"
chapter_title: "Fine-Tuning to Follow Instructions"
source_path: "/Users/saumyamehta/DS interview prep/books/Build a Large Language Model (From Scratch).pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 7 - Fine-Tuning To Follow Instructions

## Reading Status

Direct source reading pass completed for chapter 7 from the local user-provided PDF extraction span. This note is original synthesis only; it avoids raw text dumps, copied code listings, copied formulas, copied figures, and long excerpts.

## Core Idea

The chapter turns a pretrained completion model into an instruction-following model through supervised fine-tuning. The workflow covers instruction-response data formatting, batch collation, padding masks, loading a pretrained model, running the same core training loop used for language modeling, extracting held-out responses, and using another model as a response-quality judge.

Agent Studio implication: instruction fine-tuning is an adaptation route for broad behavior change, but it only works when the instruction data format, loss mask, evaluation method, and serving prompt format are treated as durable contracts.

## Instruction Data Shape

Each training example has an instruction, optional input, and expected output. The chapter formats these fields into an Alpaca-style prompt with a response section and notes that other prompt styles are possible.

Agent Studio implication: prompt format is training data schema. If the training format differs from the production chat/template format, the model may learn the wrong control tokens, section markers, or response boundary behavior.

## Dataset Split

The instruction examples are split into train, validation, and test sets. The held-out test set is later used for generated-response evaluation rather than only loss calculation.

Agent Studio implication: instruction-tuning runs need two evaluation layers: token-level validation loss and task-response quality on held-out prompts. The datastore should preserve the exact held-out prompt set and its expected-output references.

## Custom Collation

Instruction examples have variable lengths, so batching needs a custom collate function. The chapter pads examples within each batch, shifts targets by one token, optionally truncates to model context length, and masks padding tokens with an ignored target value so they do not contribute to loss.

Agent Studio implication: collation is a training-policy artifact. Batch padding, target shifting, ignored indices, context truncation, and device transfer can change both quality and cost. These details must be logged with fine-tune runs.

## Response vs Instruction Loss

The chapter discusses the choice of whether to mask instruction tokens and compute loss only over the response. It notes that this is an active design decision rather than a universal rule.

Agent Studio implication: loss scope should be explicit. For production content studio behavior, response-only loss can focus generation quality, while full-sequence loss may reinforce formatting and instruction structure. The choice needs eval evidence, not preference.

## Model Choice And Capacity

The chapter switches from a smaller GPT-2 variant to a medium-sized one for better instruction-following capacity. Smaller models may run faster but fail to learn sufficiently rich instruction behavior.

Agent Studio implication: model selection for instruction tuning should consider task complexity, expected style fidelity, latency, serving cost, and dataset size. Small models are attractive only if they pass the same behavioral eval gates.

## Training Signal

The fine-tuning loop minimizes next-token loss on formatted instruction-response examples. Loss decreases show that the model is learning the distribution, but the chapter still inspects generated validation responses because the goal is task success, not only lower loss.

Agent Studio implication: training curves are necessary telemetry but not product evidence. Route promotion requires generated examples, judge scores, human review slices, and failure analysis.

## Response Extraction

Generation returns the original prompt plus continuation, so the chapter removes the prompt prefix and stores only the model response for evaluation. It also saves generated responses into a structured JSON-style artifact.

Agent Studio implication: extraction boundaries are product-critical. Agent Studio should store prompt, raw generation, extracted answer, stop reason, parser version, and extraction errors separately. Otherwise evals can reward prompt echoing or miss truncated responses.

## Evaluation With A Judge Model

The chapter uses a separate local model through Ollama to score generated responses against references. It demonstrates both verbose judgments and integer-only scores, while warning that judge outputs can vary.

Agent Studio implication: model-as-judge evals are useful but need guardrails: deterministic settings where possible, judge-model versioning, prompt versioning, repeated scoring or consensus for important gates, and spot checks by humans.

## Improvement Levers

The chapter identifies common improvement paths: tune hyperparameters, expand/diversify instruction data, try different prompt formats, and use a larger base model. It also points to preference fine-tuning and parameter-efficient methods as next steps.

Agent Studio implication: adaptation should be an experiment tree. Each branch needs a reason, changed variable, evaluation target, cost estimate, rollback path, and source/data-rights review.

## Datastore Requirements

Agent Studio should store instruction-tuning records:

- `instruction_dataset`: instruction/input/output schema, prompt template id, source provenance, split ids, quality filters, license/rights status, and deduplication checks.
- `sft_training_run`: base model, tokenizer, prompt template, collate policy, loss-mask policy, context length, optimizer, hyperparameters, runtime, seed, and checkpoint lineage.
- `generation_extraction`: prompt text, raw model continuation, extracted response, stop token, parser version, and extraction failure flags.
- `judge_eval`: judge model, judge prompt, scoring rubric, temperature/seed, repeated-score policy, reference answer, score, rationale availability, and human audit status.
- `adaptation_decision`: whether to use prompt/RAG, classifier fine-tune, SFT, preference tuning, LoRA, distillation, or a larger hosted model.

## Failure Modes

- Treating prompt template formatting as cosmetic when it is part of the learned behavior.
- Computing low validation loss while generated answers still fail task intent.
- Letting padding tokens dominate or corrupt loss because ignore masks are wrong.
- Accidentally training the model to echo the prompt or response markers.
- Evaluating extracted responses without checking extraction/parsing correctness.
- Using a judge model without recording the judge prompt, version, settings, and instability.
- Fine-tuning broad instruction behavior from a small or narrow dataset, then deploying it as a general assistant.
- Ignoring data rights when turning local notes, books, or user content into instruction examples.

## Agent Studio Design Implications

- Instruction fine-tuning belongs behind a formal route-change proposal, not casual iteration.
- The route ledger should track prompt template compatibility between training, evaluation, and serving.
- Held-out response evals should include generated samples, model-judge scores, human review slices, and failure clusters.
- Use SFT when behavior needs to be internalized; use retrieval/tooling when the behavior depends on changing facts or source-grounded knowledge.
- Prefer parameter-efficient and reversible adaptation routes before full fine-tuning unless eval and cost evidence justify deeper modification.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-aligning-open-language-models]] - Stanford CS25, "Aligning Open Language Models" ([YouTube](https://www.youtube.com/watch?v=AdLgPmcrXwQ)).
- [[../../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Introduction to Transformers" ([YouTube](https://www.youtube.com/watch?v=XfpMkf4rD6E)).
- [[../../../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "How I Learned to Stop Worrying and Love the Transformer" ([YouTube](https://www.youtube.com/watch?v=1GbDTTK3aR4)).
