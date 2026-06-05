---
type: official-open-cross-check
status: canon_ready
source_id: trl-v1.4.0-grpo-reward-composition
chapter: reward-composition-cross-check
extraction_method: code_read_with_paper_corroboration
local_source: trl-v1.4.0
updated: 2026-05-25
---

# TRL GRPOTrainer — Reward Function Composition & Dispatch Cross-Check

## Source

- TRL v1.4.0 `/opt/miniconda3/lib/python3.13/site-packages/trl/trainer/grpo_trainer.py` (2732 lines) + `grpo_config.py` (952 lines)
- DeepSeekMath GRPO paper (arXiv 2402.03300), DAPO paper (arXiv 2503.14476), GDPO paper (arXiv 2601.05242)
- TRL docs at huggingface.co/docs/trl/main/en/grpo_trainer

## 1. Multi-Reward Dispatch Architecture

GRPOTrainer handles **N reward functions** via a dispatch pipeline in `_calculate_rewards` (L1196-1285) and `_generate_and_score_completions` (L2143-2186).

### Function types accepted (L118):

| Type | Handling | Use case |
|------|----------|----------|
| `str` (model ID) | Load via `AutoModelForSequenceClassification.from_pretrained` | Pre-trained reward models |
| `nn.Module` | Treated as seq-class reward model → `logits[:, 0]` | Custom PyTorch reward models |
| `Callable[..., list[float\|None]]` | Custom Python function | Rule-based / format / accuracy reward |

All reward outputs are **sequence-level scalars** — there is no per-token reward computation anywhere in GRPOTrainer.

### Weighting (L412-421)

```python
reward_weights = torch.tensor(args.reward_weights)  # default: all 1.0
```

Must match `len(reward_funcs)`. Applied as `Σ(w_k · reward_k)` for `sum_then_normalize`, or per-function normalization then `Σ(w_k · z_k)` for `normalize_then_sum`.

### Two aggregation modes (`GRPOConfig.multi_objective_aggregation`, default `"sum_then_normalize"`):

**`sum_then_normalize`** (L2143-2169): Sum weighted rewards per sample, then group-normalize the combined scalar. The combined reward loses per-function resolution — if one function dominates in scale, the others have negligible influence after normalization.

**`normalize_then_sum`** (L2171-2180, GDPO-inspired): Normalize each reward function **separately** within the group (per-function mean/std subtraction), then sum weighted z-scores. Prevents the signal-collapse problem documented by GDPO (arXiv 2601.05242). Always applies batch-level normalization to the final combined advantage.

```
sum_then_normalize:
    reward = Σ(w_k · r_k)                    # one scalar per sample
    Â = (reward - μ_group) / σ_group         # group-normalized
    
normalize_then_sum:
    z_k = (r_k - μ_k_group) / σ_k_group      # per-function group-normalized
    reward = Σ(w_k · z_k)                     # recomposed scalar
    Â = (reward - μ_batch) / σ_batch          # batch-normalized final
```

### NaN handling

`None` returns from reward functions → `torch.nan` (L1245-1246). `nansum`/`nanmean`/`nanstd` skip NaN values throughout. This supports multi-task reward functions where some functions are conditionally irrelevant.

## 2. Reward Normalization (Advantage Computation)

### Configured by `scale_rewards` (default: `"group"`)

| Mode | Formula | Line | Effect |
|------|---------|------|--------|
| `"group"` | `Â = (r_i - μ_group) / (σ_group + 1e-4)` | L2166-2169 | Per-question group normalization — matches original GRPO paper Eq 4.1.2 |
| `"batch"` | `Â = (r - μ_batch) / (σ_batch + 1e-4)` | L2155-2160 | Single global normalization — from "Tricks or Traps?" blog |
| `"none"` | `Â = r - μ_group` | L2166 | Mean-center only — no variance scaling |

**Group definition**: The `num_generations` (default: 8) completions sampled from the same prompt form one group.

**DeepSeekMath GRPO paper confirmation** (arXiv 2402.03300, Section 4.1.2): The original paper uses exactly group-level normalization: `Â_i,t = r̃_i = (r_i - mean(r)) / std(r)` where r = {r_1, ..., r_G}.

**Critical group-degeneracy case**: When all G completions receive identical reward (all correct or all incorrect), `σ_group = 0` and all advantages become zero — the gradient vanishes for that prompt. DAPO paper (arXiv 2503.14476) explicitly filters these cases via Dynamic Sampling. TRL does not implement this filter.

### Advantage is always sequence-level

```python
if advantages.dim() == 1:
    advantages = advantages.unsqueeze(1)  # (B,) → (B, 1)  (L2472-2473)
```

A single scalar advantage is broadcast to every token position in the completion. All GRPO variants do this — no variant computes per-token advantages from per-token rewards (contrast with PPO which uses GAE for per-token advantage estimation).

## 3. Token-Level vs Sequence-Level Loss Aggregation (by `loss_type`)

The key architectural difference between GRPO variants is not in how the **advantage** is computed (all sequence-level), but in how the **per-token loss** is reduced to a scalar.

| `loss_type` | Aggregation formula | Normalizer | Line | Length bias |
|-------------|-------------------|------------|------|-------------|
| `grpo`, `sapo` | `mean( Σ(loss·mask) / Σ(mask) )` | Sequence-length mean → batch mean | L2567-2568 | **High** — shorter sequences with positive advantage get disproportionately higher per-token gradient |
| `bnpo` | `Σ(loss·mask) / Σ(mask)` | Local batch active token count | L2572 | **Varies** by token distribution across processes |
| `dr_grpo` | `Σ(loss·mask) / (B · max_completion_length)` | Constant (max possible tokens) | L2576 | **Medium** — constant denominator |
| `dapo`, `cispo`, `vespo` | `Σ(loss·mask) / (num_items_in_batch / n_processes)` | Global active token count (across all processes) | L2579-2581 | **None** — each token has equal gradient weight |
| `luspo` | `mean(loss · Σ(mask))` | Length-weighted mean | L2583-2584 | **Inverse** — longer sequences have higher per-token weight |

### DAPO paper confirmation (arXiv 2503.14476, Section 3.3)

The DAPO paper explicitly criticizes GRPO's sample-level loss aggregation (Eq 3) where `1/G Σ_i 1/|o_i| Σ_t ...` gives each sequence equal weight regardless of length. DAPO replaces it with token-level normalization `1/Σ|o_i| Σ_i Σ_t ...`. TRL's `loss_type="dapo"` correctly implements this with global token count normalization.

**Important caveat**: DAPO also removes the KL penalty (`beta=0`) and adds Dynamic Sampling + Overlong Reward Shaping. TRL's DAPO mode implements the token-level normalization but **does not** implement Dynamic Sampling or Overlong Reward Shaping. The `beta` parameter remains configurable (L2563-2564).

## 4. Full Reward → Advantage → Loss Data Flow

```
Phase 1: REWARD COMPUTATION (_generate_and_score_completions L2124-2140)
  prompt/completion text
    → _calculate_rewards(inputs, prompts, completions, completion_ids)
      → for each reward_func_k:
          model: tokenize(prompt+completion), forward → logits[:, 0]
          callable: func(prompts=..., completions=..., **kwargs) → list[float|None]
       → all_gather(rewards_per_func) across processes
    → rewards_per_func: shape (B*G × K) where K=#funcs, G=num_generations

Phase 2: ADVANTAGE (_generate_and_score_completions L2143-2180)
  rewards_per_func
    → weighted sum (default mode) or per-function norm'd sum (GDPO mode)
    → group mean/subtract + variance scale → advantages: (B*G,)

Phase 3: SLICE BACK (L2189-2194)
  advantages → slice per-process → advantages: (B,) per process

Phase 4: LOSS (_compute_loss L2437-2588)
  per_token_logps = forward(model, prompt_ids+completion_ids)  # (B, T)
  log_ratio = per_token_logps - old_per_token_logps             # (B, T)
  coef_1 = exp(importance_sampling(log_ratio))                  # (B, T) or (B, 1)
  advantages unsqueezed to (B, 1)                                # (B, 1)
  per_token_loss = -min(coef_1·adv, clip(coef_1)·adv)           # (B, T)
  per_token_loss += beta * KL(ref || policy)                     # if beta != 0.0
  
  # Aggregation varies by loss_type (see §3)
  loss = reduce(per_token_loss * completion_mask)                # scalar

Phase 5: GRADIENT ACCUMULATION SCALING
  loss /= gradient_accumulation_steps                           # except dapo/cispo/vespo
```

## 5. Reward Function Interface Details

### Callable signature (L1241-1242):

```python
output_reward_func = reward_func(
    prompts=prompts,                 # list[str] — prompt text
    completions=completions,         # list[str] — generated response text
    completion_ids=completion_ids_list,  # list[list[int]] — token IDs
    **reward_kwargs                  # trainer_state, log_extra, log_metric, environments + all dataset cols
)
```

### NN Module interface (L1218-1233):

Receives **concatenated** prompt+completion text. The reward is `logits[:, 0]` — only the first logit is used. No prompt masking in the reward model — it sees the full sequence.

### Extra kwargs passed to ALL reward functions (L1204-1211):
- `trainer_state`: HuggingFace `TrainerState` for dynamic reward shaping
- `log_extra`: callback for logging extra columns per completion
- `log_metric`: callback for scalar metrics
- `environments`: simulation env references (if `environment_factory` provided)
- All dataset columns except `"prompt"`, `"completion"`, `"completion_ids"`

## 6. Score Caching and Recomputation

**Rewards are not cached separately** — they are part of the `_buffered_inputs` dict along with advantages, logprobs, and ref logprobs (L1153-1163).

Reuse pattern:
- `num_iterations` (µ in GRPO paper): same generation replayed through policy updates
- `steps_per_generation`: gradient accumulation steps sharing the same generation
- Fresh generation: every `steps_per_generation × num_iterations` steps (L1155, L2047)
- `old_per_token_logps`: stored once during generation (L2278-2279), re-read in loss (L2479)
- vLLM importance sampling correction: always computed fresh (L2064-2075)

## 7. System-Design Implications for Agent Studio

1. **Default `reward_weights` are uniform**: All reward functions weighted equally by default. Weight tuning is exposed via config but undocumented for common patterns.

2. **`sum_then_normalize` vs `normalize_then_sum` choice is structural**: The GDPO path prevents signal collapse but uses batch-level normalization on the recomposed signal — changing the per-prompt group structure. System designers must document which mode is active and why.

3. **DAPO loss_type without DAPO's Dynamic Sampling**: Using TRL's `loss_type="dapo"` inherits token-level normalization (good) but misses the all-correct/all-incorrect filter (degenerate gradient). If the training set has many easy or hard prompts, gradient signal degrades silently.

4. **Advantage broadcast hides per-token reward signal**: Since even token-level GRPO variants use sequence-level advantage broadcast, the loss cannot distinguish which tokens within a completion are good vs bad. Process supervision (per-step reward mirroring) is not supported in TRL's GRPOTrainer.

5. **Reward function kwargs leak**: All extra dataset columns are passed to every reward function. If a column contains large data (images, audio), each reward function call incurs the memory overhead — even functions that ignore it.

6. **Gradient accumulation bypass for DAPO family**: `dapo`/`cispo`/`vespo` bypass the Trainer's built-in gradient accumulation scaling (L656-657), using `num_items_in_batch` which already accounts for accumulation. Mixing these with other loss_types in the same pipeline would double-scale gradients.

## Mermaid Diagram: Reward → Advantage → Loss Pipeline

```mermaid
flowchart LR
    subgraph Reward["Reward Functions (K=1..N)"]
        RF1["Func 1: accuracy<br/>→ list[float|None]"]
        RF2["Func 2: format<br/>→ list[float|None]"]
        RFk["Func K: [model/callable]<br/>→ list[float|None]"]
    end

    subgraph Combine["Multi-Reward Combination"]
        W["Σ(w_k · r_k)<br/>reward_weights (default: all 1.0)"]
        ND["sum_then_normalize<br/>(default)"]
        NN["normalize_then_sum<br/>(GDPO mode)"]
        W --> ND & NN
        ND --> SUMMED["combined reward<br/>group-normalized"]
        NN --> PERFUNC["per-func z-scores<br/>summed, batch-normalized"]
    end

    subgraph Advantage["Advantage Computation"]
        G["group normalization<br/>(B*G completions / prompt)<br/>Â = (r - μ) / (σ + 1e-4)"]
        B["batch normalization<br/>Â = (r - μ_b) / (σ_b + 1e-4)"]
        N["mean-center only<br/>Â = r - μ"]
        G --- B --- N
    end

    subgraph Loss["Loss Aggregation (by loss_type)"]
        L_GRPO["grpo/sapo<br/>sequence-length mean<br/>HIGH length bias"]
        L_DAPO["dapo/cispo/vespo<br/>global token count<br/>NO length bias"]
        L_BNPO["bnpo<br/>local token count<br/>distributed-varies"]
        L_LUSPO["luspo<br/>length-weighted mean<br/>inverse bias"]
    end

    Combine -->|advantages: (B*G,)| Advantage
    Advantage -->|broadcast: (B,1)| Loss
    Advantage -.->|degenerate when<br/>all rewards identical| Deg["⚠️ σ=0 → zero gradient<br/>DAPO filters this (TRL does not)"]
    style Deg fill:#fdd,stroke:#f44
```