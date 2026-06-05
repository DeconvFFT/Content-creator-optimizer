---
type: official-open-cross-check
status: canon_ready
source_id: huggingface-datasets
chapter: trl-grpo-data-pipeline-defaults
extraction_method: installed_package_code_analysis
local_source: /opt/miniconda3/lib/python3.13/site-packages/datasets/
---

# Datasets Library Silent Defaults: GRPO Data Pipeline Cross-Check

## Purpose

Trace datasets library default parameters through the TRL `GRPOTrainer` data pipeline to identify composition-level silent failure modes that individual-library cross-checks (TRL silent-defaults, HF TrainingArguments silent-defaults) do not catch. A GRPO training run inherits defaults from **datasets → transformers → TRL** simultaneously; composition risks only appear at the library boundaries.

## High-Risk Defaults: Datasets → GRPO Pipeline

### 1. `load_from_cache_file=None` → `True` (caching resolution chain)

- **Source:** `arrow_dataset.py:3404`, `fingerprint.py:40`
- **Default:** `None` → `is_caching_enabled()` → `_CACHING_ENABLED = True`
- **GRPO effect:** Any `Dataset.map()` call reuses cached results from previous runs. Changing tokenizer arguments, preprocessing function behavior, or `fn_kwargs` silently ignored while stale cache exists.
- **TRL compensation:** **None.** GRPOTrainer does not call `map()` internally, but the `_prepare_dataset` method loads pre-processed datasets containing cached maps.
- **Risk level:** HIGH — Stale cache can mask buggy preprocessing changes

### 2. `map(batched=False)` — Single-row processing

- **Default:** `False`
- **GRPO effect:** Tokenization calls expecting batched input (e.g., `padding=True`, `truncation=True/max_length`) silently produce wrong padding or truncation per-example instead of per-batch.
- **TRL compensation:** **None** — users call `map()` in their own preprocessing; GRPOTrainer does not intervene.
- **Risk level:** HIGH — Silent wrong tokenization output

### 3. `map(remove_columns=None)` — Column accumulation

- **Default:** `None` (no removal)
- **GRPO effect:** Raw text columns accumulate alongside tokenized columns through each `map()` call. Cache files grow; column lookups slow. Extra columns pass through to GRPOTrainer's reward functions via `reward_kwargs` — which is intentional for custom reward functions, but unexpected columns (e.g., `messages`, `response`) can accidentally reach reward dispatch.
- **TRL compensation:** `remove_unused_columns=False` (preserves extra columns for reward functions) + signature columns `["prompt", "image", "images"]`. This is a **correct** override but means columns are never automatically cleaned.
- **Risk level:** HIGH — Column bloat and accidental reward-function surface contamination

### 4. `train_test_split(shuffle=True, seed=None)` — Non-reproducible splits

- **Default:** `shuffle=True, seed=None`
- **GRPO effect:** Each run produces different train/eval splits. GRPO experiment comparisons across runs are not reproducible. With `test_size=None` → `0.25`, silently loses 25% of data to eval.
- **TRL compensation:** **None** — `trl/scripts/utils.py` calls `combined_dataset.train_test_split(test_size=mixture_config.test_split_size)` but does not set a fixed seed.
- **Risk level:** HIGH — Non-reproducible experiments, silent data loss

### 5. `select()` — Mandatory disk caching

- **Source:** `arrow_dataset.py:4353–4360`
- **Finding:** `Dataset.select()` has **no `load_from_cache_file` parameter** — always writes indices mapping to disk. No way to skip.
- **GRPO effect:** TRL's eval callback (`trl/trainer/callbacks.py:297`) calls `self.eval_dataset.select(range(num_prompts))` — every eval step writes a cache file.
- **TRL compensation:** **None** — does not pass `keep_in_memory=True`.
- **Risk level:** MEDIUM — Accumulated disk cache during long runs

### 6. `shard(contiguous=True)` — Distribution bias

- **Default:** `contiguous=True`
- **GRPO effect:** Contiguous sharding means shards are **not** uniformly distributed. If the dataset has ordering bias (sorted by difficulty), each distributed worker gets systematically different data, affecting reward normalization baselines.
- **TRL compensation:** Does not call `shard()` directly, but `to_iterable_dataset(num_shards=N)` internally uses `shard()` with `contiguous=True`.
- **Risk level:** HIGH — Shard-specific bias in distributed training

### 7. `IterableDataset.shuffle(buffer_size=1000)` — Approximate shuffling

- **Default:** 1000-example buffer
- **GRPO effect:** Not directly applicable — GRPOTrainer rejects `IterableDataset` (`not yet supported`). But relevant for streaming use cases.
- **Risk level:** MEDIUM — Only if pushing streaming boundaries

## Composition Risk Matrix

| Default | Datasets lib | TRL override? | Transformers override? | Net effect |
|---------|-------------|---------------|----------------------|------------|
| `load_from_cache_file=True` | Silent stale cache | ❌ None | ❌ None | Composition: silent stale preprocessing |
| `batched=False` | Single-row processing | ❌ None | ❌ None | Composition: wrong padding/truncation |
| `remove_columns=None` | Column bloat | ✅ `remove_unused_columns=False` | ❌ None | Composition: intentional pass-through, but reward function risks |
| `seed=None` | Non-reproducible | ❌ None | ❌ None | Composition: experiments not comparable |
| `caching_enabled=True` | Global cache | ❌ None | ❌ None | Composition: disk accumulation |
| `contiguous=True` | Shard bias | ❌ None | ❌ None | Composition: distribution skew |

## GRPOTrainer Dataset Pipeline Trace

```
User preprocessing (map with inherited defaults)
  → load_from_cache_file=True → stale cache risk ✓
  → batched=False → single-row risk ✓
  → remove_columns=None → column bloat ✓
  → _set_signature_columns(["prompt","image","images"])
  → remove_unused_columns=False → columns preserved ✓
  → RepeatSampler → HF DataLoader
    → _generate_and_score_completions() → x["prompt"] per batch
    → reward_fn(**reward_kwargs) → extra columns surface ✓
```

## Key Finding

The datasets library's caching system (`_CACHING_ENABLED = True`) combined with TRL's lack of explicit `load_from_cache_file=False` creates a **silent staleness risk**: neither library independently signals that a map's output was loaded from cache rather than recomputed. A tokenization change that doesn't change the dataset fingerprint silently produces the old output, and the GRPO trainer observes different reward dynamics without any warning.

This is distinct from the TRL-only silent-defaults (where `beta=0.0` disables KL anchoring without warning) and the HF TrainingArguments silent-defaults (where `_BaseConfig` flips `bf16` silently). It lives at the **library boundary** — neither library's individual defaults cross-check catches it.