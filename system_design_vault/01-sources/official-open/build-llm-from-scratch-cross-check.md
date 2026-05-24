---
type: official-source-cross-check
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-17
cross_checks:
  - source_title: "Build a Large Language Model (From Scratch)"
    chapters: "1-7"
sources:
  - https://cs336.stanford.edu/
  - https://developers.openai.com/api/docs/guides/model-optimization
  - https://developers.openai.com/api/docs/guides/supervised-fine-tuning
  - https://developers.openai.com/api/docs/guides/fine-tuning-best-practices
  - https://developers.openai.com/api/docs/guides/evaluation-best-practices
  - https://huggingface.co/docs/transformers/en/training
  - https://huggingface.co/docs/trl/en/sft_trainer
  - https://huggingface.co/docs/peft/en/index
  - https://docs.vllm.ai/en/stable/
---

# Build LLM From Scratch - Official Cross-Check

## Scope

This cross-check covers the full local `Build a Large Language Model (From Scratch).pdf` chapter set after direct reading of chapters 1-7. It promotes the notes where the book-level conclusions are reinforced by current official/open sources: Stanford CS336, OpenAI model optimization, OpenAI fine-tuning and eval guidance, Hugging Face training/SFT/PEFT docs, and vLLM serving docs. This note is original synthesis only and stores no raw book text or long excerpts.

## Cross-Check Result

The chapter set is canon-ready for Agent Studio system design. The official sources support the same implementation-level ladder: understand tokenization, transformer architecture, attention and context policy, training loops, evaluation, supervised fine-tuning, adaptation economics, and serving constraints. The strongest design consequence is that model behavior must be governed as a pipeline of data, templates, tokenizer, weights, loss masks, checkpoints, decoding, serving runtime, and eval gates.

## Confirmation Matrix

| Build LLM theme | Official/open-source confirmation | Agent Studio design implication |
|---|---|---|
| Language-model construction is a full stack | Stanford CS336 frames language modeling as tokenization, architecture, optimization, systems, data, evaluation, alignment, and inference. | Model routes need end-to-end lineage, not only provider/model name. |
| Tokenization and batching affect behavior | Stanford CS336 assignments and Hugging Face training docs treat tokenizer, data collator, and training config as core training components. | Store tokenizer, chunking, padding, truncation, collator, and context policy with every route and fine-tune run. |
| Attention/context policy is product policy | Stanford CS336 covers architecture, resource accounting, inference, evaluation, and data filtering; vLLM documents serving as a separate runtime surface. | Context length, KV/cache behavior, batching, and runtime profile belong in route metadata and capacity planning. |
| Training loss is not product quality | OpenAI evaluation guidance and fine-tuning best practices separate training/test statistics from post-training evals and model-quality checks. | Promotion gates need task evals, held-out cases, judge/human review, and failure slices alongside loss curves. |
| Fine-tuning starts with realistic data | OpenAI SFT guidance emphasizes realistic application examples; fine-tuning best practices emphasize data quality, balance, diversity, consistency, train/test split, and prompt format parity. | Fine-tune datasets need provenance, split integrity, label/schema consistency, distribution checks, and production-template compatibility. |
| Loss masking is an explicit training choice | Hugging Face TRL supports assistant-only and completion-only loss, making loss scope a configurable SFT policy. | Store whether loss is full sequence, assistant-only, completion-only, or custom masked; require eval evidence for the choice. |
| Parameter-efficient tuning is a first-class option | Hugging Face PEFT documents adapting pretrained models by training a small number of parameters to reduce compute and storage cost. | Route proposals should consider adapters/LoRA before full fine-tune when reversibility, cost, or multiple tenants matter. |
| Serving stack matters after training | vLLM positions itself as fast, low-cost LLM inference/serving, while CS336 includes inference and systems topics. | Checkpoints should not be canon without serving profile: runtime, precision, batching, latency, cost, and quality regression gates. |
| Model-as-judge is useful but bounded | OpenAI evaluation best practices cover LLM-as-judge/model graders while distinguishing scalable judging from human evaluation. | Judge evals require judge version, rubric, prompt, deterministic settings, repeatability policy, and human audit slices. |

## Canon Decisions

- Chapters 1-2 are canon for the source ledger fields around model lifecycle, tokenization, chunking, embeddings, positional policy, and context-window constraints.
- Chapter 3 is canon for attention, causal masking, multi-head design, and context-packing implications.
- Chapter 4 is canon for GPT architecture contracts, residual/normalization structure, parameter budgeting, and generation-loop metadata.
- Chapter 5 is canon for training run lineage, train/validation split governance, loss/perplexity limitations, checkpoint management, decoding policy, and memorization checks.
- Chapter 6 is canon for fixed-label classifier routes, label-schema contracts, class imbalance handling, trainable-layer policy, confusion-matrix evaluation, and preprocessing parity.
- Chapter 7 is canon for supervised instruction-tuning records, prompt-template compatibility, collate/loss-mask policy, response extraction, model-judge evaluation, and adaptation decision trees.

## Agent Studio Architecture Commitments

- Treat tokenizer, prompt template, data collator, loss mask, checkpoint, decoding policy, and serving runtime as versioned route artifacts.
- Add `adaptation_kind` values for prompt-only, retrieval/tool change, classifier fine-tune, supervised instruction fine-tune, preference tuning, PEFT adapter, distillation, and serving/runtime optimization.
- Require every fine-tune proposal to include dataset provenance, allowed use, split policy, quality checks, baseline route failure evidence, target evals, serving impact, and rollback plan.
- Store classifier routes separately from instruction-following routes because they have different output contracts, metrics, thresholds, and review policies.
- Store response extraction/parsing as an eval artifact; never score only raw continuations when production uses extracted answers.
- Require model-as-judge results to be accompanied by judge metadata, rubric, prompt version, and spot-check policy.
- Prefer reversible adaptation methods before full model modification unless the eval and capacity evidence justify deeper changes.

## Remaining Refinement

The next useful refinement is to deepen the Stanford CS336 alignment lecture notes after the May 2026 SFT/RLHF/RL materials are published, then connect preference tuning and RL-style adaptation to the existing route-change proposal template.
