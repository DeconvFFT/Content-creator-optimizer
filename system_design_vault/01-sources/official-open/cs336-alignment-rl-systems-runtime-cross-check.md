---
type: source-cross-check
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-24
source_id: official_open.cs336_alignment_rl_systems_runtime_cross_check
topic: "CS336 alignment RL systems and runtime governance"
stores_raw_source_text: false
source_urls:
  - https://cs336.stanford.edu/
  - https://github.com/stanford-cs336/assignment5-alignment
  - https://arxiv.org/abs/2501.12948
  - https://arxiv.org/abs/2203.02155
  - https://arxiv.org/abs/2305.20050
  - https://huggingface.co/docs/trl/main/en/grpo_trainer
  - https://github.com/OpenRLHF/OpenRLHF
related:
  - "[[../../02-lectures/stanford/cs336-data-and-alignment]]"
  - "[[cs336-lecture16-rlvr-cross-check]]"
  - "[[../../03-patterns/alignment/preference-alignment-systems-canon]]"
---

# CS336 Alignment RL Systems Runtime Cross-Check

## Scope
This note hardens the CS336 alignment canon around runtime topology, verifier governance, rollout cost, and release discipline while current 2026 Lecture 17 public materials remain unavailable. It does not claim current-2026 Lecture 17 ingestion.

## Why this cross-check exists
The direct-read Stanford Lecture 16 note already covers RLVR, GRPO caveats, verifier scope, and reward overoptimization. The remaining gap is more operational: what an RL post-training stack actually looks like in production once rewards, rollouts, reference policies, and regressions have to be managed as infrastructure.

## Runtime topology
```mermaid
flowchart LR
    P[Prompt batch] --> G[Rollout generation]
    G --> V[Verifier / reward stack]
    V --> N[Group normalize / rank / score]
    N --> U[Policy update with KL control]
    U --> E[Held-out eval and regression gates]
    E --> R{Release?}
    R -- yes --> C[Candidate route]
    R -- no --> B[Rollback / reject]
```

## Core corroboration

### 1. Reasoning RL is usually multi-stage, not one clean online loop
DeepSeek-R1 is the best open evidence that reasoning RL becomes a staged system: cold-start data, rule-based reward, rejection-sampling refresh, another supervised pass, and a broader alignment follow-through stage.

**Implementation meaning:** treat RL runs as route-program changes with multiple artifacts, not as a single trainer invocation.

### 2. KL control is an operational brake, not theory garnish
InstructGPT remains the canonical systems reference for reward-model plus PPO training with a per-token KL penalty to the SFT reference policy.

**Implementation meaning:** KL drift belongs in release dashboards and rollback policy. A route that “wins reward” while breaking grounding, tone, or tool reliability is a failed alignment run.

### 3. Verifier scope is part of the alignment contract
Let's Verify Step by Step shows that outcome-only reward can miss brittle reasoning; process supervision can materially outperform answer-only reward.

**Implementation meaning:** the reward record must say whether the checker validates only the final answer, output format, intermediate steps, citations/tool traces, or some combination.

### 4. Rollout generation is a systems bottleneck
OpenRLHF's runtime design makes the systems point explicit: online RL is dominated by sample generation and therefore depends on a distributed serving/training topology, not just optimizer settings.

**Implementation meaning:** capacity planning for RL must track prompt count, samples per prompt, trace length, verifier latency, and GPU placement for generator, reference, reward, and optional critic roles.

### 5. GRPO removes one subsystem but not the governance burden
Open-source GRPO implementations simplify PPO by removing the value model, but the hard parts remain: grouped rollouts, reward normalization, KL/reference control, length effects, and regression measurement.

**Implementation meaning:** “no critic” is not “simple training.” Group size, normalization mode, and length policy still change what behavior gets reinforced.

### 6. Assignment 5 shows that rollout infrastructure is part of the public contract
The current public CS336 Assignment 5 surface makes the RL-systems story concrete before current 2026 Lecture 17 is visibly published. The handout and repo expose prompt-family choice (`question_only`, `r1_zero`, few-shot variants), answer-versus-format reward separation, GRPO-family variants, token-level versus sequence-level clipping, and vLLM-backed generation utilities with explicit weight-sync concerns.

**Implementation meaning:** version prompt family, reward decomposition, clipping granularity, rollout engine, and weight-sync topology as release artifacts. Those choices are not trainer plumbing; they decide what data the optimizer sees and how stable the online loop remains.

### 7. Reasoning RL should be recorded as a stage in a larger post-training pipeline
The official Lecture 16 material and the public Assignment 5 surface are stronger together than separately: verifier-backed reasoning RL is best treated as a capability-building stage, not as the whole deployed alignment recipe. Public examples such as R1-style stacks show a reasoning-focused RL stage followed by broader SFT/alignment follow-through that can widen the behavior surface while also changing or partially weakening some narrow reasoning gains.

**Implementation meaning:** record the stage order, not just the optimizer. A release report should preserve what happened before RL, what happened during RL, what broad-alignment step came afterward, and which reasoning gains survived that downstream broadening.

### 8. PPO/GRPO stacks often carry two different policy identities, not one
The current public Stanford Assignment 5 surface plus open PPO/GRPO references make a subtle runtime fact explicit: the **old rollout policy** used for clipped importance ratios is not the same object as the **frozen reference policy** used for KL drift control. In practice the old rollout policy is the snapshot that actually generated the sampled batch, while the reference policy is a separate anchor, often the SFT-starting policy, that may or may not be active depending on the run.

**Implementation meaning:** do not flatten `old_policy_snapshot` and `reference_policy_snapshot` into one generic "baseline model" field. They answer different questions and fail in different ways.

### 9. Off-policy correction only means something if provenance and masking stay aligned
The public Assignment 5 adapter/test surface ties `old_log_probs`, `response_mask`, clipping mode, and loss aggregation into the same train-step contract. That means off-policy ratios are only interpretable when the run can prove both **which rollout snapshot produced the old log-probabilities** and **which response-token boundary those ratios were averaged over**.

**Implementation meaning:** provenance and token boundary are one contract. A bad mask or stale `old_log_probs` can masquerade as a training win even when the optimizer is behaving exactly as configured.

### 10. The real training unit is a prompt-group under a three-policy contract
The latest public Stanford Assignment 5 surfaces and open GRPO references sharpen one more systems detail that is easy to blur away in prose. There are usually **three policy identities**, not just one "model plus baseline": the **current learner policy** being updated now, the **old rollout snapshot** that actually generated the sampled responses used for clipped ratios, and the **frozen reference policy** used as the KL drift anchor when that branch is enabled. At the same time, GRPO-style optimization is not naturally indexed by single responses; the atomic unit is the **prompt-group** that binds one prompt, `group_size` completions, one verifier recipe, and one rollout-sync epoch into the same accounting object.

**Implementation meaning:** keep `train_policy_snapshot`, `old_policy_snapshot`, `reference_policy_snapshot`, `group_size`, `sync_epoch`, and verifier/reward recipe fields in the same release record. If a report only stores per-sample rewards and a generic "baseline model," it loses the provenance needed to tell real policy improvement from stale-rollout or baseline-mislabeling artifacts.

### 11. Microbatch accumulation is part of the objective contract, not memory plumbing
The public Assignment 5 handout and train-step adapter/test surface make one more production-relevant detail explicit: on-policy reasoning RL wants a large rollout batch for utilization, but the learner often cannot fit that whole batch into memory for one backward pass. The update is therefore split across microbatches and accumulated before a single optimizer step.

**Implementation meaning:** gradient accumulation is only comparable across runs if the system preserves **full-batch equivalence**. Record `rollout_batch_size`, `gradient_accumulation_steps`, `microbatch_partition_rule`, `loss_normalization`, `normalization_constant`, `response_mask_scope`, `grad_clip_point`, and `max_grad_norm` together. Otherwise a hardware-driven microbatch change can silently become an objective-scale change.

## High-value deltas to carry into the canon note
- Distinguish **generation cost** from **update cost**; rollout throughput is often the dominant bottleneck.
- Version runtime placement choices such as separate generation and training services because these choices can alter trace consistency and stability.
- Record **two policy baselines when present**: `old_policy_snapshot` for importance-ratio/clipping correctness and `reference_policy_snapshot` for KL control.
- Record whether the KL/reference branch was actually enabled (`reference_policy_enabled`, `beta`, `mean_kl_to_ref`) instead of assuming every PPO/GRPO run used the same drift anchor.
- Record whether the run uses outcome-only reward, process reward, or mixed reward.
- Separate logged instrumentation from optimized reward. Format/schema checks, parser success, and auxiliary metrics can be tracked without automatically becoming the scalar objective.
- Track clipping granularity explicitly: token-level versus sequence-level ratio control changes stability and what a reward gain means.
- Treat token-level PPO/GRPO clipping as the direct lineage default and sequence-level clipping as an exposed alternative that should be named explicitly rather than flattened into generic "clipping used" language.
- Keep `old_log_probs` lineage joined to `response_mask` provenance; ratio control and loss accounting should reference the same response-token boundary.
- Record the actively updated learner separately from the old rollout snapshot and the frozen KL reference; PPO/GRPO stacks are usually a **three-policy** system, not a two-object one.
- Treat `(prompt_id, group_index, sample_index, sync_epoch)` as the minimal rollout accounting key when grouped normalization or clipped updates are active.
- Add a `microbatch_update_contract` with `gradient_accumulation_steps`, `microbatch_partition_rule`, `loss_normalization`, `normalization_constant`, `response_mask_scope`, `grad_clip_point`, and `max_grad_norm`; memory-fit choices must not silently change the effective update.
- Treat rejection sampling / best-of-n as a separate lever from online RL; both may improve results, but they have different cost and governance implications.
- Require held-out regressions for grounding, citation validity, latency, and verbosity after any RL route change.
- Keep length-compression or verbosity penalties explicit; they are reward-shaping policy, not harmless cleanup.
- Distinguish outcome-side verifier decomposition from true process supervision. Logging answer reward and format reward separately is valuable, but it is still weaker evidence than explicit intermediate-step verification.
- Treat stage-order retention as part of the runtime contract: later broad-alignment cleanup can tax math/coding gains, so post-RL broadening must be evaluated as a possible capability-regression event.

## Agent Studio design implications
- Add `rl_runtime_recipe` fields for rollout engine, reference-policy source, verifier class, reward components, group size, normalization policy, trace-length cap, and eval bundle.
- Add `old_policy_snapshot`, `old_logprob_snapshot_time`, `reference_policy_snapshot`, `reference_policy_enabled`, and `policy_age_at_rollout` so PPO/GRPO runs preserve both clipping lineage and KL lineage.
- Add a `microbatch_update_contract` or `train_step_equivalence_contract` with `rollout_batch_size`, `gradient_accumulation_steps`, `microbatch_partition_rule`, `loss_normalization`, `normalization_constant`, `response_mask_scope`, `grad_clip_point`, and `max_grad_norm`.
- Add `rl_release_report` fields for reward gain, groundedness delta, citation-validity delta, latency delta, token-cost delta, and rollback recommendation.
- Add `post_rl_retention_check` fields for stage order, downstream broad-alignment step, retained math/coding gain, groundedness delta, and whether later alignment changed the apparent RL win.
- Separate `selection_only_improvement` from `policy_update_improvement` so pass@k gains are not mislabeled as training gains.
- Keep verifier-backed optimization isolated to narrow, auditable behaviors such as schema validity, citation resolution, tool success, or benchmark answer equivalence.
- Add `rollout_runtime_contract` fields for prompt family, rollout engine, weight-sync topology, clipping mode, and verifier latency budget so training wins can be reproduced as systems behavior rather than only optimizer settings.
- Add `response_mask_policy`, `old_logprob_source`, and `masked_ratio_scope` so sequence-level and token-level off-policy corrections can be audited against the exact response boundary used in training.

### 12. The live Assignment 5 repo proves a concrete vLLM weight-sync topology
The public `assignment5-alignment` repo (confirmed live 2026-05-24 during the course site migration to `cs336.stanford.edu`) exposes a complete online-RL weight-sync topology through `vllm_utils.py`. This is not generic speculation — it is the actual implementation Stanford students build against:

```mermaid
flowchart LR
    subgraph Learner
        L[PyTorch policy]
    end
    subgraph Generator
        V[vLLM server]
    end
    L -- "pause / update_weights / NCCL send / reset_prefix_cache / resume" --> V
    V -- "generate_completions()" --> R[Rollout batch]
```

The `VLLMServer` dataclass manages the full lifecycle:
- `start()`: launches vLLM with `--enable-prefix-caching`, `--weight-transfer-config '{"backend": "nccl"}'`, `--tensor-parallel-size 1`, `bfloat16`; waits for `/health` endpoint up to 600s
- `init_weight_sync(policy_device)`: creates an `NCCLWeightTransferEngine` via vLLM's distributed module, negotiating `master_address`, `master_port`, `rank_offset=1`, `world_size=(inference_world_size + 1)`. The trainer side calls `trainer_init()`, the generator side initializes via `POST /init_weight_transfer_engine`
- `generate_completions()`: batched `POST /v1/completions` with `temperature`, `max_tokens`, `n`, `seed`, `return_token_ids`, and optional `stop` + `include_stop_str_in_output`. Returns `VLLMCompletion` with `text`, `token_ids`, `finish_reason`
- `sync_policy_weights()`: `POST /pause` → `POST /update_weights` with NCCL `trainer_send_weights` (packed mode) → `POST /reset_prefix_cache` → `POST /resume`

**Implementation meaning:** the weight-sync topology is a provenance field, not an implementation detail. Every rollout epoch is bounded by a pause-sync-resume sequence. Generator freshness, cache-invalidation cost, and NCCL transfer bandwidth all affect how quickly the learner's update reaches the next batch of rollouts. Runs that batch multiple learner steps per sync (off-policy reuse) must preserve `old_logprob_source` and `sync_epoch` to distinguish fresh-rollout gains from stale-rollout correction artifacts.

### 13. The grader provenance is now confirmed as public open-source
The `drgrpo_grader.py` module in the live repo is attributed to `sail-sg/understand-r1-zero` (MIT license), confirming the grading cascade chain:
1. `grade_answer_mathd()` — Dan Hendrycks style normalized string match with 395+ unit text replacements, fraction/sqrt fixing, matrix normalization
2. `grade_answer_sympy()` — sympy structural equivalence with `signal.SIGALRM` 1s timeout, repetition-filter suffix-array guard (>20% = auto-fail), integer strictness, tuple/interval splitting, multiple-GT logical OR
3. `is_latex_equal()` — math_verify library (slow path, inactive during training)

The `question_only.prompt` template is confirmed as `{question} Please put your final answer within \boxed{{}}.` — the prompt-bound answer-extraction and stop contract is minimal.

### 14. The test surface confirms four algorithm variants under one train-step contract
The test suite (`tests/test_grpo.py`) parameterizes `grpo_train_step()` across:

| Variant | baseline | advantage_normalizer | loss_normalization | normalization_constant |
|---------|----------|---------------------|-------------------|----------------------|
| `grpo_constant` | mean | std | constant | 32 |
| `dr_grpo` | mean | none | constant | 32 |
| `rft` | none | none | constant | 32 |
| `maxrl` | mean | mean | constant | 32 |

All four share the same `gradient_accumulation_steps=2`, `max_grad_norm=1.0`, `group_size=2`, and reward function returning `{"reward", "format_reward", "answer_reward"}`.

**Implementation meaning:** the algorithm-family boundary is not a qualitative "GRPO vs RFT vs MaxRL" switch — it is a specific combination of baseline, advantage normalizer, and loss-normalization parameters. A release report that only states "we used GRPO" loses the parameter dimension that actually defines the training objective.

### 16. Prompt family → parser → reward contract: the concrete A5 topology

The live A5 repo exposes five distinct prompt templates, each defining a different output grammar and requiring a different parser/reward strategy. This is not a cosmetic detail — prompt change can silently change both parser hit rate and effective reward surface, because the output format determines which answers are extractable and thus which behavior gets optimized.

| Prompt template | Output grammar | Answer extraction | Reward function | Boundary contract |
|---|---|---|---|---|
| `question_only.prompt` | Free text + `\boxed{answer}` | `mathd_normalize_answer` scans for `\boxed{}`; `_strip_string` normalizes whitespace, frac/sqrt/repeating-decimal mathd transformations | `grade_answer_mathd()` — string equivalence after 395+ unit replacements | `{question} Please put your final answer within \boxed{}.` — the model must produce a parseable `\boxed{}` for any reward to register |
| `r1_zero.prompt` | `thinking ...` → `<answer> answer </answer>` | Parser looks for `<answer>` and `</answer>` tags; no `\boxed{}` fallback | Same `drgrpo_grader.py` cascade (mathd → sympy → latex_equal) but entry point is tag-based rather than box-based | Tag-separated reasoning/answer boundary. If the model omits `<answer>` tags or nests them incorrectly, reward is zero even with a correct answer |
| `r1_zero_three_shot_gsm8k.prompt` | Same `thinking/answer` format with 3 exemplars | Same tag-based parser | Same grader cascade | The 3 exemplars teach the exact tag structure, lowering format-failure risk but biasing toward GSM8K-style short-answer patterns |
| `alpaca_sft.prompt` | `### Response:\n{response}` | No answer extraction — SFT format | N/A (SFT loss, not RL reward) | Instruction-following format, not used for RL reward generation |
| `zero_shot_system_prompt.prompt` | `# Query: \`\`\`{instruction}\`\`\`\n# Answer: \`\`\`` | No answer extraction — safety/instruction context | N/A (used as system prompt context or safety evaluation) | Safety-aligned role format with code-fence boundaries |

**Output grammar → parser hit rate → effective reward surface.** The practical consequence is that a prompt-family swap (e.g. `question_only` → `r1_zero`) can change the parser's answer-recognition rate even when the model produces the same correct answer. If `question_only`'s `\boxed{}` format produces 90% parser coverage but `r1_zero`'s `<answer>` tag format only produces 70% coverage on the same response distribution, the apparent reward drops purely from extraction attrition. Future runs comparing these two prompt families need to separate parser-failure attrition from genuine answer-quality differences.

**provenance recommendation from the live code:** The A5 `adapters.py` `run_compute_rollout_rewards` is the function stub that would connect prompt-family choice to reward dispatch. In production, treat `(prompt_family_id, prompt_template_hash, parser_version, reward_fn_id)` as an immutable contract tuple — if any element changes, the reward surface is not comparable to previous runs. Record the concrete prompt file contents (not just "r1_zero" or "question_only") in the run manifest because whitespace, exemplar choice, and delimiter escape affect parser behavior.

**Implementation meaning:** Do not log "prompt: r1_zero" and call it done. Record:
- `prompt_template_hash`: SHA256 of the actual prompt file content
- `parser_entry`: which answer-extraction path was used (box-based vs tag-based vs regex)
- `parser_coverage`: ratio of responses where the parser successfully extracted an answer
- `reward_function_id`: which combination of mathd / sympy / latex_equal was applied
- `answer_extraction_failure_rate`: fraction of responses where parser returned None (these receive zero reward, lowering the apparent group average)
- `format_reward`: the format/shape compliance component (logged separately from answer correctness to distinguish extraction failures from wrong answers)

When comparing runs across prompt families, build a `parser_alignment_table` that cross-tabulates at minimum (prompt_family, parser_hit_rate, answer_reward_mean, format_reward_mean) so the attribution of reward differences is explicit.

### 15. Off-policy correction is a rollout-reuse budget with three proven modes
The test suite validates three off-policy importance reweighting methods at `cliprange=0.1`:
- `noclip`: importance-weighted without clipping (maximum reuse, highest variance)
- `grpo`: token-level PPO/GRPO clipping over `(batch, seq_len)` log-probability ratios
- `gspo`: sequence-level reweighting and clipping over response-masked tokens only

The `old_log_probs` for off-policy tests are constructed as `torch.linspace(-1.5, 0.5)` — non-trivial drift that makes clipping behavior testable. The `response_mask` is required for GSPO, confirming the sequence-level contract depends on correct response-boundary isolation.

### 17. The Modal deployment topology defines the real runtime budget

The live `cs336_alignment/modal_utils.py` (added 2026-05-21 in commit `115f8ff`) makes the deployment infrastructure explicit — this is not generic speculation but the actual provisioned environment Stanford students build against:

```
GPU:             B200:2          # 2× B200 GPUs per container
MAX_CONTAINERS:  4               # max 4 parallel job instances  
RUN_TIMEOUT:     3600s (1 hour)  # per-job wall-clock limit
Base image:      nvidia/cuda:12.9.1-devel-ubuntu22.04 + Python 3.12 (uv)
Local dirs:      cs336_alignment/  data/  experiments/  scripts/
Local files:     pyproject.toml  uv.lock  AGENTS.md  CLAUDE.md
Observability:   W&B via Modal.Secret.from_name()
```

The topology has five governance-relevant properties:

**a) GPU budget is finite and shared.** Two B200 GPUs × 4 max containers = 8 GPU maximum parallelism. A run with large `rollout_batch_size` and many seeds (e.g. `seeds=0,1,2,3` as in the docstring example) spawns up to 4 parallel containers, each processing one seed's `scripts/grpo.py` independently. Container scheduling is Modal's responsibility — concurrent jobs may queue waiting for GPU availability.

**b) The 1-hour timeout is a hard braking constraint.** `RUN_TIMEOUT_SECONDS = 60 * 60` means any RL trial that exceeds 1 hour gets preempted. For a training loop where each step involves vLLM rollout generation → NCCL weight transfer → GRPO update → logging, the timeout forces the student to make algorithmic choices (group size, rollout count, microbatch steps, GPUs) that fit within 3600 seconds. In production, this translates to: **the RL pipeline's unit of compute is not "one training run" but "one wall-clock-constrained trial."** Experiments that don't converge within the budget produce no results.

**c) The `submit_commands` pattern is a parallel batch scheduler with failure isolation.** Commands are submitted via `run_command.map()` (Modal's parallel map), and each result is checked for exceptions. Failed commands are counted and cause `SystemExit(1)`. This means a single seed failure (e.g. OOM, timeout, NaN loss) kills the entire multi-seed batch run. **Implementation meaning:** runs with multiple seeds or hyperparameter sweeps should record per-seed exit status independently and preserve partial results rather than treating a batch as atomic.

**d) The Modal image includes `AGENTS.md` and `CLAUDE.md`.** These files provide AI-assisted development context for the assignment — a sign that the deployment environment anticipates agent-driven or AI-assisted development workflows on the remote cluster. For a production RL pipeline, this means the deployment artifact should record what auxiliary context (agent instructions, runbooks, observability dashboards) is shipped alongside the training code.

**e) W&B integration is production-level.** The `wandb_secret` is a named Modal secret, meaning weigths-and-biases logging is not an optional add-on but part of the provisioned image. All parallel containers share the same W&B project (`cs336-a5-rlvr-{SUNET_ID}`). In production, this means experiment tracking identity, run-name collision prevention, and secret rotation are part of the RL infrastructure contract.

```mermaid
flowchart LR
    subgraph Modal_Cloud
        subgraph Container_0[Container 0: seed=0]
            C0[grpo.py]\n-- B200:2\n-- 3600s timeout\n-- W&B log
        end
        subgraph Container_1[Container 1: seed=1]
            C1[grpo.py]\n-- B200:2\n-- 3600s timeout\n-- W&B log
        end
        subgraph Container_2[Container 2: seed=2]
            C2[grpo.py]\n-- B200:2\n-- 3600s timeout\n-- W&B log
        end
        subgraph Container_3[Container 3: seed=3]
            C3[grpo.py]\n-- B200:2\n-- 3600s timeout\n-- W&B log
        end
    end
    S[submit_commands] -->|run_command.map| Container_0
    S -->|run_command.map| Container_1
    S -->|run_command.map| Container_2
    S -->|run_command.map| Container_3
    Container_0 -->|W&B log| WB[W&B project:\ncs336-a5-rlvr-{SUNET_ID}]
    Container_1 -->|W&B log| WB
    Container_2 -->|W&B log| WB
    Container_3 -->|W&B log| WB
    C0 -.->|failure → SystemExit(1)| F[Batch abort on\nsingle failure]
```

**Implementation meaning:** add `deployment_topology` fields to the RL runtime record:
- `gpu_type`, `gpu_count_per_container`, `max_containers`, `container_timeout_s`
- `parallel_batch_size`: number of concurrent job instances
- `failure_isolation`: whether single-instance failure aborts the full batch
- `observability_backend`: `wandb` / `mlflow` / `none` + project name
- `deployment_aux_context`: whether agent instructions or runbooks are shipped with the training artifact
- `container_scheduling`: managed vs dedicated (Modal manages scheduling; a dedicated cluster has different contention patterns)

Without these fields, a run report that says "we trained for 1 hour on 4 seeds with GRPO" is indistinguishable from "we trained for 4 non-overlapping hours on 4 sequential seeds with GRPO" — and the batch-parallel version has different GPU contention, timeout risk, and failure semantics than the sequential version.

## Stop-string / answer-extraction coupling — silent reward-collapse surface

The public Assignment 5 codebase makes one more production-relevant detail explicit: **the vLLM `include_stop_str_in_output` default (`False`) is incompatible with the `r1_zero_reward_fn`'s answer-extraction path when `</answer>` is used as a stop string.**

### The concrete failure mode

The vLLM completion API (`vllm_utils.py`, line 204-206) defers to the client:

```python
payload["include_stop_str_in_output"] = sampling_params.get("include_stop_str_in_output", False)
```

Default is `False`. When `r1_zero` prompt templates use `</answer>` as a stop string with this default, the vLLM response ends *before* `</answer>`. But `r1_zero_reward_fn` (line 1009) checks:

```python
if " response <answer>" in response and "</answer>" in response:
```

If `</answer>` is excluded from output, this check fails and the function returns `format_reward=0.0, answer_reward=0.0, reward=0.0` for every rollout (line 1041-1045). **The model gets zero gradient signal from any correctly-generated-but-trimmed rollout.**

### Prompt-family coupling

| Prompt family | Stop string | `include_stop_str_in_output` requirement | Parser dependency |
|---|---|---|---|
| `r1_zero`, `r1_zero_three_shot` | `</answer>` | Must be `True` — default `False` causes zero reward | `r1_zero_reward_fn` checks for `</answer>` presence, then extracts `<answer>...</answer>` content and optionally `\boxed{}` from within |
| `question_only` | None (natural stop) | Irrelevant — no stop string | `question_only_reward_fn` calls `extract_answer()` which searches for `\boxed{}`, bold text, and other LaTeX patterns |

### Why this matters for governance

- **A silent default mismatch is indistinguishable from policy failure.** If a run reports flat zero reward, the operator cannot tell whether the model failed to learn or `include_stop_str_in_output` was just set wrong.
- **Prompt-family swaps inherit their predecessor's stop config.** If the training loop is templated and a prior run used `question_only` (no stop string), the next run switching to `r1_zero` must add `stop=["</answer>"]` **and** `include_stop_str_in_output=True`. Forgetting either silently kills the RL signal.
- **The `question_only` family has its own fragile path.** `extract_answer` (line 985-987) first tries `\boxed{}` extraction, falls through to bold/LaTeX patterns, and returns `None` if nothing matches — also a zero-reward outcome. The difference is that `question_only` is parsing-ambiguous (multiple fallback strategies may extract something) whereas `r1_zero` with wrong stop config is deterministically dead.

**Provenance recommendation:** Add a `rollout_termination_contract` to the run manifest with:
- `stop_strings` (list, empty if none)
- `include_stop_str_in_output` (bool, required field — never omit the default)
- `response_mask_scope` (which tokens count as the "response" for loss computation)
- `parser_entry_check` (the exact condition the reward function checks to decide "formatted or unformatted")
- `parser_fallthrough_behavior` (what happens when the parser entry check fails — zero reward vs partial credit vs fallback parser)

Recording `include_stop_str_in_output` as an explicit field rather than relying on a silent default is the minimum governance step. A run that reports `stop_strings=["</answer>"], include_stop_str_in_output=True` can be distinguished from one that silently defaults to `False`.
![[../../02-lectures/stanford/assets/cs336-stop-string-answer-extraction-coupling.svg]]

## Checkpoint-to-release-gate provenance

The public Assignment 5 surface reveals a structural gap between what a training checkpoint saves and what a deployable release candidate needs. A5 has no built-in checkpoint saver — `checkpoint.py` is only a model/tokenizer loader, and students write their own save logic. The adapter contract captures hyperparameters (group_size, baseline mode, advantage normalizer, clip range, loss normalization) but does not preserve the three-policy snapshot (learner, frozen reference, old rollout policy) that RL release gates depend on.

### What A5 records (per run)

| Category | Fields |
|---|---|
| **Training hyperparameters** | `grad_accum_steps`, `max_grad_norm`, `group_size`, `baseline`, `advantage_normalizer`, `importance_reweighting_method`, `loss_normalization`, `normalization_constant`, `cliprange` |
| **Sampling config** | `temperature`, `seed`, `max_tokens`, `stop` strings |
| **Reward signals** | `reward`, `format_reward`, `answer_reward` via `drgrpo_grader` (sail-sg/understand-r1-zero) |
| **Prompt templates** | 5 tracked families, each with distinct extraction/stop contracts |
| **Infra** | B200:2 × up to 4 containers, 3600s timeout, W&B project, Modal batch scheduling |

### What's missing for release-gate readiness

| Gap | Why it matters |
|---|---|
| **No reference/KL policy snapshot** | Release evaluators need to verify KL drift between the new checkpoint and the original model, not just between consecutive checkpoints |
| **No old_policy snapshot** | Off-policy importance correction becomes unverifiable when the old rollout distribution is discarded |
| **No optimizer state** | Mid-training evaluation cannot distinguish "can't improve further" from "lost optimizer momentum" |
| **No eval harness at save time** | Checkpoint reward/loss curves are training metrics, not eval metrics — they conflate policy improvement with dataset/exposure effects |
| **No prompt hash / prompt_family_id** | A checkpoint at step N rewards are bundled across all prompt families; without family-level provenance, a reward jump may be a prompt-mix artifact, not policy improvement |
| **No grader version / parser coverage** | Two runs using different grader normalization rule sets see different reward surfaces even with the same model weights |
| **No sync_epoch / rollout generation timestamp** | Without the learner-generation clock, a checkpoint could be evaluated with rollouts up to 3 sync cycles stale |

### Proposed governance fields for the checkpoint record

A release-gate-ready checkpoint record should bundle:

**Snapshot cartel** (4 components, not 1):
- `learner_weights_path`, `reference_model_path`, `old_policy_logprobs_sha`
- `optimizer_state_path` with last-val-loss, `optimizer_momentum_snapshot`

**Config provenance** (must survive checkpoint → release transition):
- `baseline_mode`, `advantage_normalizer_fn`, `loss_normalization_mode`, `normalization_constant`
- `cliprange_value`, `group_size`, `grad_accum_steps`
- `stop_strings`, `max_tokens`, `temperature`, `seed`

**Reward/grader provenance** (not just scalar histories):
- `reward_fn_id`, `grader_sha`, `parser_path`, `parser_coverage_pct`
- `answer_normalization_ruleset` (e.g., sympy / math_verify / string-match)

**Eval provenance** (separate from training metrics):
- `dataset_hash`, `dataset_version`, `eval_grader_version`
- `eval_batch_size`, `eval_seed`, `eval_timeout_s`
- `held_out_score`, `failure_slice_scores` (by difficulty, length, prompt family)

**Release provenance** (added at promotion, not training time):
- `reward_curve_slope_last_N_steps` — is the policy still improving?
- `val_loss_divergence_since_checkpoint` — overfitting or reward-hacking signal?
- `rollback_recommendation` — which prior checkpoint to roll back to

**Implementation meaning:** A "checkpoint" is not a release candidate until all four snapshot components exist, grader provenance is verifiable, and the eval record is independent from training metrics. The Assignment 5 runtime surface makes this gap explicit by being a training-only system — nothing in the adapter contract or `checkpoint.py` bridge to deployable release gate metadata.
![[../../02-lectures/stanford/assets/cs336-lecture16-rollout-runtime-contract.svg]]

## Practical note
This cross-check uses official/open artifacts only and intentionally stops short of claiming current 2026 Lecture 17 source coverage. The live 2026-05-24 recheck still shows Lecture 16 as the visible official anchor (`lecture_16.pdf` still linked on the schedule, `cs336.stanford.edu` now live, old `cs336.stanford.edu` github.io redirects resolved) and keeps Lecture 17 blocked until the official course page exposes a public material link for the May 27 slot. The Assignment 5 repo (aligned to Spring 2026 as of the `2026 version` commit history) is confirmed live and publicly forkable.
