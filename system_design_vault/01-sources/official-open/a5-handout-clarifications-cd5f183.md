---
type: cross-check-note
source: stanford-cs336-assignment5
source_id: cs336_a5_handout_cd5f183
status: canon_ready
chapter: assignment5-alignment-handout
extraction_method: pdftotext + github-api
local_source: /Users/saumyamehta/DS interview prep/books/
commit: cd5f183
commit_date: 2026-05-29T21:03:05Z
author: Steven Cao
version: 26.0.0
---

# A5 Handout cd5f183 — `question_only` Prompt Clarification

## What Changed

Commit `cd5f183` (author: Steven Cao, 2026-05-29) adds a **`question_only` prompt variant** throughout the A5 handout. This is a clarification/methodology expansion within the same version (26.0.0), not a mechanism-level change.

## `question_only` Prompt Surface

| Aspect | Value |
|---|---|
| Prompt location | `cs336_alignment/prompts/question_only.prompt` |
| Reward function | `cs336_alignment.drgrpo_grader.question_only_reward_fn` |
| Answer format | Final answer inside `\boxed{}` |
| Stop string | None — model completes naturally with `<|end_of_text|>` |
| Comparison targets | `r1_zero` (zero-shot COT) and `r1_zero_three_shot` (few-shot COT) |
| Prompt ablation problem | Dedicated `grpo_prompt_ablation` comparing all three prompts |

## Operational Implications for System Design

### 1. Prompt-Family → Reward Function Binding

The handout now explicitly binds different prompt families to different reward functions:
- **r1_zero / r1_zero_three_shot** → `r1_zero_reward_fn` (looks for `</answer>` stop token)
- **question_only** → `question_only_reward_fn` (looks for `\boxed{}` answer)

This means the **prompt choice selects both the output grammar AND the evaluation function**. In a production RL training system, the prompt family, reward function, parser, and stop-string policy must be versioned as a unit. A prompt swap without corresponding reward-function changes changes the effective reward surface even when the optimizer is identical.

### 2. Stop-String Policy Separation

The `question_only` prompt does NOT use the `</answer>` stop string — it relies on natural completion. This changes:
- When the generation stops (natural EOS vs explicit stop token)
- Whether `include_stop_str_in_output` applies
- The effective response length distribution under training

This means the rollout-sampling contract (temperature, top-p, max-token ceiling, stop-string handling, finish-reason provenance) must be stored per-prompt-family, not globally.

### 3. Prompt Ablation as Training-Design Decision

The dedicated `grpo_prompt_ablation` problem (4 B200 hrs) validates that prompt choice shapes RL dynamics — not just accuracy but which rollouts the model explores. This formalizes the "prompt shapes RL dynamics" insight: bare question prompts produce different exploration distributions than COT prompts, and the best prompt for inference may not be the best prompt for RL training.

### 4. Reward Function API Contract

```python
# r1_zero_reward_fn: scores format + correctness, uses </answer> parsing
# question_only_reward_fn: scores correctness only, uses \boxed{} parsing
# Both return dict with keys: "reward", "format_reward", "answer_reward"
```

The `question_only_reward_fn` is a **correctness-only** scorer (format reward is for logging only), while `r1_zero_reward_fn` scores both format and correctness. This changes the effective reward sparsity.

## Related Control-Plane Files

- `01-sources/official-open/a5-handout-clarifications-eb830f5.md` — Previous A5 clarification (split ground truth before grading, batch size counts responses, 50 steps)
- This cross-check is a companion to the eb830f5 note, not a replacement

## Queue Impact

The A5 repo now has two substantive clarification commits (eb830f5 + cd5f183) since the initial handout. Future runs should compare `pushed_at` against the known sha `cd5f183`. The `question_only` prompt surface is now fully documented — no further A5 handout extraction needed unless the handout PDF changes again.
