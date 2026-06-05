---
type: official-open-cross-check
project: agent-studio-system-design
source_id: cs336-assignment5-safety-supplement
status: canon_ready
created: 2026-06-04
url: https://github.com/stanford-cs336/assignment5-alignment/commit/a8ad44f
source_class: official_open
extraction_method: direct_commit_inspection + pdftotext_pdf_extraction
related_notes:
  - 01-sources/official-open/cs336-assignment5-reasoning-rl-variants-cross-check.md
  - 01-sources/official-open/cs336-alignment-rl-systems-runtime-cross-check.md
---

# CS336 Spring 2026 — Assignment 5 Safety/RLHF Supplement (a8ad44f)

## Overview

On 2026-06-04 (~00:13 UTC), Steven released a **major new supplement** to the CS336 Assignment 5 alignment repo: commit `a8ad44f` — "2026 safety supplement published" — adding a full 17-page optional supplement on instruction tuning, safety evaluation, and Direct Preference Optimization (DPO).

**Version**: 26.0.0 (SemVer: the changelog transitioned from 2.0.1 to historical 26.x.x numbering — consistent with the Spring 2026 quarter starting at version 26.0.0).

**Scope**: An entirely optional supplement covering the safety/RLHF side of post-training. This is **not** a clarification to the required RL reasoning assignment — it is a **parallel track** using a different base model (Llama 3.1 8B vs the required assignment's Olmo/Qwen), different benchmarks (MMLU/GSM8K/AlpacaEval/SimpleSafetyTests vs MATH/GSM8K), and different training methods (SFT+DPO vs GRPO/Dr.GRPO/RFT/MaxRL/GSPO).

## What Changed — Files

| File | Type | Lines | Purpose |
|---|---|---|---|
| `cs336_spring2026_assignment5_supplement_safety_rlhf.pdf` | **Added** (PDF) | 17 pages | Full handout: zero-shot, SFT, DPO, red-teaming |
| `cs336_alignment/modal_utils_safety.py` | **Added** | +83 | Modal helper with shared volume `cs336-a5-supplement` (Meta-Llama-3.1-8B, Llama-3.3-70B-Instruct judge, UltraChat-200K data) |
| `cs336_alignment/prompts_safety/` (5 files) | **Added** | 1-15 ea | Zero-shot prompts (alpaca_eval, gsm8k, mmlu, simple_safety_tests, system prompt) + SFT template |
| `data/alpaca_eval/alpaca_eval_gpt4_turbo.json` | **Added** | +4832 | GPT-4 Turbo reference annotations for AlpacaEval |
| `data/hh/*.jsonl.gz` (4 files) | **Added** | — | Anthropic HH dataset: harmless-base, helpful-online, helpful-base, helpful-rejection-sampled |
| `scripts/evaluate_safety.py` | **Modified** | +1/-1 | SimpleSafetyTests evaluator (Llama-3.3-70B-Instruct judge) |
| `tests/adapters.py` | **Removed** | -36 | Adapter tests removed (SFT test replaced by integrated approach) |
| `tests/test_sft.py` | **Removed** | -107 | Standalone SFT test removed |
| `cs336_spring2025_assignment5_supplement_safety_rlhf.pdf` | **Removed** | — | Old 2025 supplement replaced by 2026 version |
| `data/alpaca_eval/alpaca_eval.jsonl` | **Removed** | -805 | Replaced by GPT-4 Turbo annotated version |
| `CHANGELOG.md` | **Modified** | +11 | Documents all changes |
| `uv.lock` | **Modified** | +210 | Dependencies updated |
| `pyproject.toml` | **Modified** | +1 | Minor dep change |

## Handout Structure (17 pages)

### 1. Zero-Shot Evaluation (Pages 2–8)
Benchmarks Llama-3.1-8B base on 4 tasks before any training:

| Benchmark | What it measures | Prompt format | Evaluation metric |
|---|---|---|---|
| **MMLU** | Factual knowledge (57 subjects) | Zero-shot + system prompt → multiple-choice → `The correct answer is _` | Correct answer letter parsing |
| **GSM8K** | Math reasoning (word problems) | Task prompt in system template | Final number parsing |
| **AlpacaEval** | Chat quality (805 instructions) | Instruction-only in system template | Winrate vs GPT-4 Turbo (Llama-3.3-70B-Instruct annotator) |
| **SimpleSafetyTests** | Safety (100 hazardous prompts) | Instruction-only in system template | Safe proportion (Llama-3.3-70B-Instruct judge) |

Generation: greedy decoding (temperature=0.0, top-p=1.0) throughout.

### 2. Instruction Fine-Tuning / SFT (Pages 8–11)
- **Model**: Meta-Llama-3.1-8B (loaded in bfloat16, FlashAttention-2)
- **Data**: UltraChat-200K + SafetyTunedLlamas → single-turn format (`prompt`/`response` keys)
- **Template**: Alpaca instruction template (`alpaca_sft.prompt`) — *differs from zero-shot system prompt*
- **Data loading**: Packed sequences (consecutive non-overlapping chunks of length `m`, drop remainder), custom PyTorch Dataset
- **Training**: 1 epoch, seq_length=512, batch_size=32, lr=2e-5, cosine decay, 3% warmup, weight_decay=0.1, grad_clip=1.0, gradient accumulation
- **Restriction**: No Hugging Face Trainer allowed — implement from scratch

### 3. Post-SFT Evaluation (Pages 11–14)
Re-evaluates on all 4 benchmarks with **Alpaca template** (not zero-shot system prompt). Includes red-teaming exercise.

### 4. DPO (Pages 14–18)
- **Theory**: Derives DPO from RLHF (reward model → policy reparameterization). Covers the standard per-instance DPO loss (Equation 3).
- **Data**: Anthropic HH dataset (harmless-base, helpful-base, helpful-online, helpful-rejection-sampled). Single-turn only (2+ human messages filtered).
- **Implementation**: Reference model on one GPU, trained model on another. No batching — gradient accumulation only. RMSprop (not AdamW) unless quantization used.
- **Hyperparameters**: effective batch_size=64, β=0.1, lr=1e-6
- **Training**: 1 epoch over HH. Track validation classification accuracy (chosen > rejected log-probability).
- **Evaluation**: AlpacaEval, SimpleSafetyTests, GSM8K, MMLU — to detect alignment tax.

### 5. Bibliography
Cites Hendrycks (MMLU), Cobbe (GSM8K), Li (AlpacaEval), Vidgen (SimpleSafetyTests), Ganguli (red-teaming), Ouyang (RLHF/InstructGPT), Rafailov (DPO).

## Operational Implications for System-Design Vault

### A. SFT Data Pipeline — Implicit Design Decisions
1. **Packed sequence semantics**: Training data = concatenated prompt-response documents with EOS delimiter, split into fixed-length chunks (no padding). This means **document boundaries cross batch positions** — individual sequences are NOT aligned with document boundaries. The language modeling loss over a packed sequence sees mixed-document windows, where one token's labels come from a different document. This is a standard tradeoff for throughput but affects loss interpretation (perplexity on packed sequences ≠ per-document perplexity).
2. **Shuffled documents** before packing: every epoch produces different packing-boundary locations. Training is deterministic only within a given shuffle seed.
3. **Gradient accumulation** at `gradient_accumulation_steps=4` (for seq_length=512 with per-device microbatch capacity giving batch_size=32): average over microbatches, not sum (divide loss by `gradient_accumulation_steps` before backward).

### B. DPO Training Architecture — GPU Topology
- **2 GPUs required** (one for trained model π_θ, one for reference model π_ref). On B200: 2-device setup is the default.
- **No batching**: each example processed individually (no batch-level log-probability vectorization). Loss accumulated over `effective_batch_size=64` individual-example gradient accumulations.
- **Prompt + chosen and prompt + rejected**: each DPO instance processes TWO response-completions through both models (4 forward passes per example: π_θ through chosen+rejected, π_ref through chosen+rejected). Prompt log-probabilities cancel in the difference.
- **RMSprop vs AdamW**: The supplement explicitly chooses RMSprop over AdamW unless quantization is used. This avoids the memory overhead of AdamW's momentum buffers at 8B scale.

### C. Evaluation Protocol — Dual Prompt Regime
The evaluation uses a **Dual Prompt Regime**:
- **Zero-shot**: system prompt (`zero_shot_system_prompt.prompt`) + task-specific prompt
- **Post-SFT**: Alpaca SFT template (`alpaca_sft.prompt`) wrapping the task-specific prompt
This means SFT performance comparison is NOT an apple-to-apple comparison on prompt format alone — the post-SFT evaluation uses a DIFFERENT prompt template (the one the model was trained with), so format-matching is an intentional confound.

### D. Safety Evaluation — Judge-Based Proxy
- **SimpleSafetyTests** (100 hazardous prompts): judge via Llama-3.3-70B-Instruct with a `True`/`False` binary classification system prompt
- **SimpleSafetyTests limits**: 100 examples only — small sample, potential type-II errors from judge bias
- **System prompt includes safety instructions** (`...must not contain any fake, harmful, unethical, racist, sexist, toxic...`) — the zero-shot safety evaluation tests whether this instruction alone (without training) is sufficient

### E. Alignment Tax Detection
DPO evaluation explicitly checks GSM8K and MMLU for capability degradation — the accepted "alignment tax" from preference optimization. The vault's existing RL cross-check notes (silent defaults, token-level surrogate objectives, finite-group baseline shrinkage) should be referenced here as orthogonal concerns (DPO alignment tax is about capability loss on held-out benchmarks, not about reward-hacking or objective-misspecification in the training signal).

### F. A5-Due Date Coincidence
The supplement was published on the **A5 due date** (Wed June 3 / 00:13 UTC June 4). This timing suggests the supplement was part of the course's planned materials for the optional completion window, not a last-minute addition.

## Connections to Existing Vault Notes

- **Extends** `01-sources/official-open/cs336-assignment5-reasoning-rl-variants-cross-check.md`: that note covers the required RL part (GRPO/Dr.GRPO/RFT/MaxRL/GSPO with reasoning models). This supplement covers the OPTIONAL safety/RLHF track (SFT+DPO with generalist models). Together they form the full CS336 post-training coverage.
- **Extends** `01-sources/official-open/cs336-alignment-rl-systems-runtime-cross-check.md`: the runtime note covers A5 infrastructure (Modal topology, adapters, GRPO training step). The safety Modal utils (`modal_utils_safety.py`) follow the same infrastructure pattern with a dedicated shared volume for safety models.

## Next Steps for Vault

- Expand SFT data loading implementation details (packed dataset semantics, cross-document boundary behavior).
- Expand DPO loss equation with reference-scaled advantage interpretation.
- Cross-reference DPO against the existing vault's PPO/GRPO silent-default analysis — DPO has far fewer implementation pitfalls (no KL anchor, no clipping, no off-policy correction, no importance sampling) but its alignment tax is a real system-design concern.