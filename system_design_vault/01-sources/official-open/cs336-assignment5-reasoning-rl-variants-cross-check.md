---
type: source-cross-check
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-21
source_id: official_open.cs336_assignment5_reasoning_rl_variants_cross_check
topic: "Stanford CS336 Assignment 5 reasoning-RL variants and reward contract"
stores_raw_source_text: false
source_urls:
  - https://cs336.stanford.edu/
  - https://github.com/stanford-cs336/assignment5-alignment
  - https://raw.githubusercontent.com/stanford-cs336/assignment5-alignment/main/cs336_spring2026_assignment5_alignment.pdf
  - https://github.com/stanford-cs336/lectures/blob/main/lecture_16.pdf
  - https://arxiv.org/abs/2402.03300
  - https://arxiv.org/abs/2501.12948
  - https://arxiv.org/abs/2305.20050
  - https://huggingface.co/docs/trl/main/en/grpo_trainer
related:
  - "[[../../02-lectures/stanford/cs336-data-and-alignment]]"
  - "[[cs336-lecture16-rlvr-cross-check]]"
  - "[[cs336-alignment-rl-systems-runtime-cross-check]]"
  - "[[../../03-patterns/alignment/preference-alignment-systems-canon]]"
---

# CS336 Assignment 5 Reasoning-RL Variants Cross-Check

## Scope
This note hardens the current CS336 alignment canon with the public Spring 2026 Assignment 5 surface. It focuses on the operational contract exposed by the public repo and handout: prompt families, verifier-backed reward semantics, GRPO-family knobs, and off-policy clipping choices. It does not store handout text, solutions, or long excerpts.

## Why this note exists
Lecture 16 explains why RLVR is attractive for verifier-backed domains. The public Assignment 5 artifact shows how Stanford operationalizes that idea in a concrete training stack rather than leaving it at the level of algorithm slides.

## Core corroboration

### 1. The assignment is reasoning RL with verifiable reward, not generic “alignment”
The public Assignment 5 lane centers on math reasoning with a small public model, GSM8K-style tasks, rollout-based optimization, and answer verification. Safety-alignment work exists only as an optional supplement.

**Implementation meaning:** keep verifier-backed reasoning RL separate from broader helpfulness or safety tuning. They are related but not interchangeable release surfaces.

### 2. Prompt design is part of the RL contract
The public artifact exposes multiple prompt families such as `question_only`, `r1_zero`, and a three-shot GSM8K variant. That means prompt choice is part of exploration and rollout behavior, not just UI formatting.

**Implementation meaning:** version prompt template choice alongside reward and optimizer settings. A training delta caused by prompt structure should not be mislabeled as a pure optimizer win.

### 3. Reward instrumentation and optimization target are intentionally separated
The assignment exposes format reward and answer reward separately, while treating correctness as the actual optimization target rather than giving blended partial credit.

**Implementation meaning:** log parser/schema/format compliance, but keep the product reward record explicit about what is actually optimized. Instrumentation should not silently become reward.

### 3a. Prompt family, parser, and stop policy are one coupled reward-surface bundle
The public Assignment 5 handout and repo surface make a sharper point than "version your prompts." `r1_zero` and `r1_zero_three_shot` explicitly ask the model to emit `<think>` / `<answer>` tags, use a tag-aware `r1_zero_reward_fn`, and rely on an `</answer>` stop string with stop-text retention so the parser sees the closing answer tag. `question_only` uses a different prompt grammar, a different reward function, and must not inherit the tag-based stop contract.

**Implementation meaning:** prompt-family changes are not neutral front-end swaps. They can change parse hit rate, termination behavior, format telemetry, and the optimized reward surface even when the optimizer, verifier backend, and dataset stay fixed. The run record should therefore bind prompt grammar, reward function, and stop policy together rather than versioning them as unrelated knobs.

### 4. Stanford is teaching a family of GRPO-style choices, not one frozen recipe
The public tests/handout expose a meaningful variant set: GRPO, Dr. GRPO, RFT, and MaxRL, with different baseline and normalization combinations.

**Implementation meaning:** baseline choice, normalizer choice, and loss normalization belong in the release record because they materially affect what behavior the optimizer prefers.

### 5. Off-policy clipping granularity is a real design choice
The public interface distinguishes no clipping, token-level PPO/GRPO-style clipping, and sequence-level clipping over response tokens.

**Implementation meaning:** token-level and sequence-level ratio control should be tracked separately. They change stability, credit assignment, and the interpretation of reward gains.

The public Assignment 5 handout also makes the token-level path less neutral than a generic "reduced-variance PPO trick." Sequence-level importance reweighting is presented first as the unbiased correction for stale rollouts, but Stanford then derives that token-level reweighting optimizes a different surrogate objective: for timestep `t`, the prefix and suffix still come from the old rollout policy while only token `t` is sampled under the current learner. In other words, token-level off-policy GRPO/PPO is evaluating one current-policy action inside a mixed old/new trajectory rather than under fully current-policy continuations.

**Implementation meaning:** `importance_sampling_level = "token"` should imply a documented surrogate-objective contract, not just a variance/stability choice. The run record should preserve that prefixes and suffixes were judged under the stale rollout policy, because reward gains under token-level reweighting are not directly comparable to sequence-level or on-policy gains even when the verifier, reward, and clip epsilon are held fixed.

### 5a. GSPO's sequence ratio already carries a length-normalization contract
The public Assignment 5 handout makes the sequence-level option more specific than a generic "sequence clip": GSPO forms one response-level importance weight from the geometric mean of response-token ratios. That means the off-policy correction is already tied to a sequence-normalized objective rather than being a drop-in replacement for tokenwise PPO/GRPO clipping.

**Implementation meaning:** `importance_reweighting_method = "gspo"` must be versioned together with `importance_sampling_level`, `response_mask` scope, and the sequence-ratio exponent rule. Two runs can share the same reward and clip epsilon while still optimizing different effective objectives if the GSPO ratio or denominator policy changes.

### 5b. `clip_fraction` is not a mode-neutral drift metric
The public Assignment 5 handout explicitly asks students to compare clipping behavior across GRPO- and GSPO-style runs, but that telemetry is only meaningful once the clipped unit is named. In token-level GRPO/PPO-style clipping, `clip_fraction` counts response-token ratios that hit the trust-region bounds. In GSPO-style sequence clipping, the same field can instead count whole responses whose single geometric-mean ratio hit the bound.

**Implementation meaning:** `clip_fraction` needs provenance, not just a number. Record `clip_metric_unit` (`token` vs `sequence`), low-bound versus high-bound clipping if the trainer exposes both, and the response-mask scope used to define the clipped support. Otherwise two runs can report similar clip fractions while describing materially different learner-drift regimes.

### 6. Lecture 16’s GRPO caveats remain live even in the assignment lane
The lecture warns that group-std normalization can bias difficulty weighting and that length policy can distort apparent reasoning gains. The assignment’s exposed normalization knobs make those warnings operational rather than theoretical.

**Implementation meaning:** every reasoning-RL release should bind normalization mode, verbosity/trace-length policy, and the eval slices used to detect easy-question bias or length drift.

### 7. Rollout termination and loss normalization define the effective trajectory contract
The public Assignment 5 runtime surface shows that reasoning-RL behavior is shaped not only by reward and clipping, but by the exact boundary of what counts as the response. Stop-string policy, whether stop text is retained, the response mask, and the choice between sequence-normalized versus constant-normalized loss all change which tokens become optimization mass.

**Implementation meaning:** a reasoning-RL result is not reproducible unless the run record also versions rollout termination and loss accounting. The key fields are stop strings, whether stop text is kept in output, max-token ceiling, finish/stop reason, response-mask policy, and whether token losses are averaged per sequence or against a fixed denominator.

### 8. Advantage normalization is an implicit prompt-difficulty weighting policy
Lecture 16 warns that GRPO's group-standard-deviation normalization is not a neutral baseline trick and can distort difficulty weighting. The public Assignment 5 handout and test surface make that warning concrete by exposing controlled variants that change only the baseline/normalizer contract: GRPO, Dr. GRPO, RFT, and MaxRL.

**Implementation meaning:** the denominator is secretly a curriculum policy. Standard GRPO's group-std normalization can upweight both very easy and very hard prompts relative to middle-difficulty prompts, while mean-style normalization pushes training mass more directly toward harder prompts and no-normalizer variants keep the weighting flatter. Aggregate reward gains are therefore not interpretable unless the run record preserves the baseline mode, normalizer mode, group statistics, and the implied prompt-weighting policy.

### 8a. Self-including group-mean baselines silently rescale the objective by group size
The public Assignment 5 handout adds one sharper detail that is easy to miss when GRPO is described only as "subtract the group mean." Its derivation shows that the self-including per-group mean baseline preserves the policy-gradient expectation only **up to a `(G-1)/G` rescaling**, because each sampled response still participates in the baseline used to score itself.

**Implementation meaning:** `group_size` is not only a throughput or variance knob. It is part of the effective objective scale. Two runs can share the same reward, prompt family, clip mode, and verifier while still inducing different update magnitudes because their self-including group baseline shrinks the expected gradient by different amounts. Baseline lineage therefore needs to be tracked separately from normalizer lineage.

### 9. Prompt, decode, and stop policy define the effective rollout distribution
The public Assignment 5 surface hardens a subtle but high-value point: the RL data distribution is partly fixed before optimization begins. Prompt families already differ in output-shape expectations, and the runtime then binds those prompts to concrete decode and termination policy such as `temperature = 1.0`, `top_p = 1.0`, `max_generation_length = 512`, and for `r1_zero` a stop string on `</answer>` with stop-text retention enabled. The public helper/runtime surface also preserves termination outcome through finish-reason-style fields.

**Implementation meaning:** reward deltas are only comparable under a stable rollout sampling contract. If prompt family, temperature, top-p, max-token ceiling, stop strings, stop-text retention, or finish-reason handling changes, the system has changed the sampled trajectory distribution and parser hit rate, not merely the optimizer.

### 9a. Off-policy correction turns stale-rollout reuse into a first-class systems budget
The public Lecture 16 plus Assignment 5 handout make a practical point that is easy to flatten into generic "importance sampling": once the learner takes more than one gradient step on a generated batch, that batch is stale, but Stanford does **not** treat staleness as an immediate regenerate-or-fail boundary. The exposed interface instead allows multiple reuse policies — `none`, `noclip`, `grpo`, and `gspo` — over the same stored rollouts, which means off-policy correction is acting as a deliberate throughput contract for how many learner updates a single expensive generation pass can safely support.

**Implementation meaning:** stale-rollout reuse should be versioned as its own budget line, not hidden inside optimizer math. The run record needs fields such as `updates_per_inference_batch`, `rollout_reuse_budget`, `old_policy_snapshot`, `old_logprob_source`, and `clip_fraction` or equivalent drift indicators. Otherwise a wall-clock speedup from reusing old rollouts can be mistaken for a pure algorithm win even when the learner has already drifted far enough that clipping is saturating.

### 10. Verifier provenance is a multi-stage grading cascade, not a single correctness check
The public `drgrpo_grader.py` surface hardens a subtle point that the principles-only notes miss: Stanford's correctness reward is produced by a **three-stage grading cascade of escalating leniency**, not a single equivalence test. Each stage uses a different normalization and comparison strategy, and the fallback path between them is part of the effective reward function.

The concrete staging exposed by the public grader:

```
grade_answer_mathd()            # Stage 1: Strict (Dan Hendrycks-style)
  → normalize via mathd_normalize_answer()
  → exact string match only
  → Fast, no parsing dependencies

grade_answer_sympy()            # Stage 2: Symbolic equivalence
  → normalize via _normalize() (unit stripping, LaTeX→text, mixed numbers)
  → sympy structural comparison (simplify diff == 0)
  → Tuple/interval answer splitting with per-element grading
  → 1-second timeout guard (signal.SIGALRM) against sympy hangs
  → repeatness() filter: >20% repeated character patterns → auto-fail

is_latex_equal()                # Stage 3: math_verify library (slow path)
  → Full LaTeX parsing via latex2sympy2_extended + math_verify
  → Uses LatexExtractionConfig + ExprExtractionConfig
  → Only activated when fast=False (not used in training loop)
```

The `grade()` function orchestrates: `grade_answer_mathd() OR grade_answer_sympy()`, and only falls through to `is_latex_equal()` when `fast=False`. During training (the default `fast=True` path), the reward is determined entirely by stages 1 and 2.

**Implementation meaning:** the effective reward function during training is a strict-plus-symbolic hybrid, not a semantic-understanding verifier. Two runs using different normalizer versions (for example `mathd_normalize_answer` vs `_normalize` variant) will see different reward rates for the same model outputs even when the policy, prompt, and optimizer are identical.

### 10a. Answer extraction is prompt-family-dependent, not a single rule
The public `r1_zero_reward_fn` and `question_only_reward_fn` use fundamentally different extraction strategies:

| Aspect | r1_zero_reward_fn | question_only_reward_fn |
|---|---|---|
| Extraction target | `<answer>` tags | `\boxed{}` command |
| Secondary extraction | `extract_boxed_answer()` from extracted region | `extract_answer()` → `last_boxed_only_string()` |
| Format failure | No tags → format_reward=0 | No boxed → format_reward=0 |
| Format-but-wrong | Tags present, answer wrong → format_reward=1.0, answer=0 | Boxed present, answer wrong → format_reward=1.0, answer=0 |
| Multi-GT support | List of ground truths, OR across elements | Same |

**Implementation meaning:** the "same" reward function name (`r1_zero_reward_fn` vs `question_only_reward_fn`) implies a different extraction pipeline, and format reward semantics differ by extraction strategy. A prompt-family change that swaps the extraction method is a reward-surface change even when the optimizer and grading backend stay fixed.

### 10b. Normalization pipelines are multi-stage and version-sensitive
The grader exposes two distinct normalization pipelines:

- **`mathd_normalize_answer()`**: Dan Hendrycks lineage. Strips enclosing `\text{}`, applies `_strip_string()` which normalizes fractions (`\frac12` → `\frac{1}{2}`), removes units from known lists (395+ unit texts with plural forms), handles sqrt, matrices, `\left`/`\right`, dollar signs, percentages, commas in large numbers, mixed numbers (e.g. `7 3/4` → `7+3/4`), and decimal-to-fraction mapping (`0.5` → `\frac{1}{2}`).

- **`_normalize()`**: Independent pipeline. Removes `\text{}`, interprets `million/billion/trillion`, strips units (22 physical unit types with plural/es suffixes), removes `\circ`, converts LaTeX via `latex2text`, handles implicit mixed numbers, case-folds to lowercase, converts float-like integers to int form. Also falls back to `_parse_latex()` when `\\` is present.

The two pipelines diverge significantly: `mathd_normalize_answer` handles 395+ unit texts with aggressive pattern matching, while `_normalize` handles 22 concrete units with simpler regex. A string that passes one may fail the other.

The run path is: try `grade_answer_mathd` first (fast string match after mathd normalization). If that fails, try `grade_answer_sympy` (sympy structural equivalence after `_normalize`). Because the normalization pipelines differ, a model output can pass stage 2 with a semantically equivalent symbolic form after failing stage 1 on string mismatch — but crucially, only when both normalizers considered the output gradable.

**Implementation meaning:** `normalizer_version` must be part of the verifier recipe. If a future run switches from mathd to a different normalization strategy (or patches the unit list, fraction handling, or decimal mapping), the effective reward function changes.

### 10c. Edge-case handling is part of the reward contract
The public grader surface makes several edge-case policies explicit:

- **Repeated/template output detection**: `repeatness()` uses a suffix-array-based algorithm to compute a character-level repetition score. If >20% of character pairs repeat, the answer is automatically rejected regardless of content. This prevents the model from gaming the reward by emitting formulaic patterns.

- **Sympy timeout guard**: A 1-second `signal.SIGALRM` timeout wraps `is_latex_equal()` to prevent sympy hangs on pathological LaTeX input. In practice this means complex or malformed expressions silently score as incorrect rather than blocking the training loop.

- **Tuple/interval answer handling**: `split_tuple()` parses parenthesized/bracketed answers and grades each element independently. Symmetry-breaking: if the ground truth uses different bracket types than the model output, the tuple path is skipped entirely and the elements are compared as a single expression.

- **Integer strictness**: When the ground truth is an integer, sympy simplification is disabled and only strict string match is accepted. This prevents the grader from accepting algebraically equivalent but non-integer forms (e.g. `2/1` or `sqrt(4)` for `2`).

- **Multiple ground truth support**: Both reward functions support a `list` of ground truths, using logical OR across elements. This means one model output can match multiple valid answer forms — the effective reward surface shrinks when acceptable answer lists are pruned.

**Implementation meaning:** each edge-case policy is a fine-grained knob. Two verifier deployments with the same extraction method and normalizer can still produce different reward rates if they differ on repetition threshold, timeout duration, tuple-handling rules, integer-strictness mode, or valid-answer-list width.

## Why this matters for Agent Studio
- Length bias is not only a reward-design problem. It can also be injected later when loss aggregation gives longer traces more update mass.
- Sequence-level clipping and sequence-normalized loss both depend on a correct definition of “response tokens,” so mask/termination bugs can look like optimizer improvements.
- Output parsing and answer verification sit on the same boundary contract. A different stop policy can change both the extracted answer and the training signal.
- Prompt swaps can change the reward surface without touching the optimizer. If grammar, parser choice, or stop-text retention changes, an apparent RL gain may really be a parser-hit-rate gain.
- Rollout provenance should therefore keep `rollout_termination_contract` separate from `reward_contract`; otherwise reward changes and trajectory-boundary changes get conflated.
- Advantage magnitudes are not safely comparable across prompts once group-relative normalization is active. The run record needs raw reward statistics plus the baseline/normalizer contract, or prompt-local reweighting can masquerade as a broad reasoning gain.
- Group size is part of the optimization contract, not just batch economics. Under a self-including group-mean baseline, changing `group_size` changes the expected gradient scale by changing the `(G-1)/G` shrinkage factor.
- Decode defaults are part of alignment infrastructure. A temperature or stop-policy change can produce an apparent RL win by altering exploration or parser success before any gradient update changes the policy.
- Off-policy reuse is part of the runtime budget, not just the objective. Reusing one rollout batch for extra learner steps changes effective sample cost, freshness guarantees, and how much of the update sits near the clip boundary.

## High-value deltas to carry into the canon
- Treat `reasoning_rl_recipe` as a versioned artifact with prompt family, reward components, baseline mode, normalization mode, clipping mode, loss aggregation, and verifier scope.
- Add `rollout_sampling_contract` record with prompt family, decode parameters, max-token ceiling, stop strings, stop-text retention policy, and finish-reason policy.
- Add `prompt_output_grammar`, `prompt_bound_reward_fn`, `prompt_stop_contract`, and `parse_termination_compatibility_check` so prompt-family swaps that alter parser compatibility are recorded as reward-surface changes.
- Add a `rollout_reuse_contract` with `updates_per_inference_batch`, `rollout_reuse_budget`, `old_policy_snapshot`, `old_logprob_source`, `importance_reweighting_method`, and `clip_fraction` or equivalent drift telemetry.
- Add `clip_metric_unit`, `clip_bound_direction`, and `response_mask_scope` whenever clip telemetry is logged; a bare `clip_fraction` field is not comparable across token-level and sequence-level clipping modes.
- Add a `rollout_termination_contract` record with response-mask policy and loss-normalization mode so termination lineage stays separate from reward lineage.
- Add `importance_sampling_level`, `sequence_ratio_token_scope`, and `gspo_exponent_contract` whenever sequence-level GSPO is used; the ratio unit and exponent policy are part of the objective, not a trainer default.
- Add `advantage_variant`, `group_baseline_policy`, `advantage_normalizer`, `advantage_eps`, `raw_reward_retention_ref`, and `per_group_reward_stats_ref` so later readers know what the stored advantage magnitudes actually mean.
- Add `group_baseline_estimator`, `baseline_includes_self_sample`, and `group_size_shrinkage_factor` so grouped baselines preserve their finite-group objective semantics instead of being flattened into a generic `baseline = mean` label.
- Record an `implicit_prompt_weighting_policy` or `difficulty_weighting_note` field whenever grouped normalization is used; denominator choice is part of the optimization objective, not trainer trivia.
- Separate `selection_only_improvement` from `policy_update_improvement`; self-consistency or best-of-n gains are not evidence that the policy itself improved.
- Record whether the verifier checks only final answers, output format, tool/test execution, or mixed signals.
- Keep optional safety/DPO follow-through as a different alignment lane from the core math-verifier reasoning-RL lane.

## Compact operational diagram
![[../../02-lectures/stanford/assets/cs336-assignment5-reasoning-rl-variants.svg]]

![[../../02-lectures/stanford/assets/cs336-assignment5-gspo-sequence-ratio-contract.svg]]

![[../../02-lectures/stanford/assets/cs336-assignment5-group-baseline-shrinkage.svg]]

![[../../02-lectures/stanford/assets/cs336-assignment5-token-level-surrogate-objective.svg]]

![[../../02-lectures/stanford/assets/cs336-assignment5-stale-rollout-reuse-contract.svg]]

![[../../02-lectures/stanford/assets/cs336-assignment5-prompt-parser-stop-bundle.svg]]

![[../../02-lectures/stanford/assets/cs336-assignment5-grading-cascade-contract.svg]]

## Practical note
This note uses only official/public Stanford artifacts and official/open corroboration. It improves the current 2026 alignment lane without claiming current Lecture 17 RL-systems source coverage, which remains blocked until Stanford exposes a visible public material link.
