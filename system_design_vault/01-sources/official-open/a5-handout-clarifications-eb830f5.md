---
type: cross-check
status: canon_ready
source_id: stanford_cs336_a5_handout_clarifications
source_class: official_open
chapter: GRPO-Review
extraction_method: code_analysis
local_source: assignment5-alignment/cs336_spring2026_assignment5_alignment.pdf
commit: eb830f5
updated: 2026-05-27
---

# CS336 Assignment 5 — Handout Clarifications (Commit `eb830f5`)

**Commit message**: "Clarifications (split gt before grading, batch size counts responses, few steps -> 50 steps)"  
**Author**: Steven Cao  
**Date**: 2026-05-26T22:14:54Z  

This note documents three concrete clarifications in the CS336 Spring 2026 Assignment 5 handout that materially sharpen the GRPO/RL system-design cross-check notes. Each has operational implications for training-run interpretation.

## 1. Batch size counts responses, not prompts

The original handout had ambiguous batch-size semantics. The clarification in the latest PDF (line 1251) is explicit:

> Note that `rollout_batch_size` and `train_batch_size` count responses, not prompts. So `rollout_batch_size = train_batch_size = 256` means 32 prompts with 8 rollouts each.

**Operational implication**: This confirms the GRPO grouped-semantics mapping: $B$ (per the notation table) = number of prompts, $G$ = generations per prompt. The training batch is $B \times G$ responses. The per-rollout-batch configuration `rollout_batch_size = 256, group_size = 8` means `n_prompts_per_rollout_batch = 32`. Any agent or system that assumes batch=prompts gets the gradient normalization wrong by a factor of $G$.

This aligns perfectly with the existing cross-check notes on grouped-advantage semantics and baseline shrinkage — the group size $G=8$ means self-including mean baselines rescale by $(G-1)/G = 7/8$, a non-trivial 12.5% effect.

## 2. Ground truth split before grading (GSM8K format)

The updated handout clarifies (line 283-284):

> To extract the answer from ground truth responses in the GSM8K dataset, which contain `{rationale} #### {answer}`, you should split on `####` and strip whitespace.

**Operational implication**: This confirms GSM8K ground truth parsing is a simple string split on a terminal delimiter — no regex, no semantic parsing. The grading function receives ONLY the answer portion (after `####`), not the rationale. This makes the reward function strictly answer-correctness based, with no partial-credit signal from the reasoning chain.

**Reward function contract**: `r1_zero_reward_fn(response, ground_truth)` and `question_only_reward_fn(response, ground_truth)` both return `dict` with keys `reward`, `format_reward`, `answer_reward`. The `answer_reward` component requires correct answer extraction from the response's `</answer>` tags AND exact match against the extracted ground truth.

## 3. 50 training steps (concrete duration)

The clarification changes the training script guidance from the earlier vague "run the script for a few steps" to a concrete target (line 1291):

> Run the script for roughly **50 steps** and confirm that you see validation rewards improving.

**Operational implication**: With `rollout_batch_size = 256`, `gradient_accumulation_steps = 32`, and `num_rollout_steps = 200`, the total token budget per run is: 50 steps × 200 rollout tokens × 256 responses = **2.56M generation tokens** plus 50 optimizer steps. The 32× gradient accumulation means each optimizer step aggregates over 256/32 = 8 microbatches. The 50-step duration is short enough for rapid iteration (est. ~30-60 min on a single GPU) but long enough for the RL signal to converge.

## Key Config Constants (from handout)

| Parameter | Value | Notes |
|---|---|---|
| `batch_size` | 256 (responses) | 32 prompts × 8 generations |
| `group_size` | 8 | $G = 8$ |
| `gradient_accumulation_steps` | 32 | Microbatches of 8 responses |
| `num_rollout_steps` | 200 | Tokens per response |
| `temperature` | 1.0 | |
| `top_p` | 1.0 | No nucleus sampling |
| `max_gen_length` | 512 | |
| `n_grpo_steps` | 50 | Training steps (epochs) |
| `baseline` | "mean" | Default (GRPO standard) |
| `advantage_normalizer` | "std" | Group std normalization |
| `loss_normalization` | "sequence" | Average per-sequence then cross-sequence |

## Relevance to Existing Cross-Checks

This clarification confirms the **grouped-advantage semantics** (per `01-sources/official-open/dapo-grpo-grouped-advantage-cross-check.md`): the advantage baseline $\mu_i$ averages over $G=8$ responses per prompt, and the std normalizer creates the $(G-1)/G$ baseline shrinkage effect.

The **grading-function split** (reward vs format vs answer) aligns with `01-sources/official-open/reward-function-contract-cross-check.md` — the reward function returns a structured dict with explicitly separated components, confirming the triple-output reward design.

The **50-step concrete duration** and **256-response batch** provide exact scale anchors for the training-loop cross-checks.
