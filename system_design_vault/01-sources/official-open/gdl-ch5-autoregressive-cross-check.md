---
type: cross-check
status: canon_ready
source_id: generative-deep-learning-ch5
chapter: 5
title: Autoregressive Models Cross-Check
source_class: local_book
---

# Autoregressive Models Cross-Check: GDL Ch5 × DL Ch10 × AI Engineering

## Coverage Matrix

| Topic | GDL Ch5 | DL Ch10 | AI Eng Ch9 |
|---|---|---|---|
| LSTM 6-step gate mechanics | ✓ Detailed cell-level | ✓ Long-dependency failure | — |
| Cell state vs hidden state | ✓ Explicit comparison | ✓ Gated recurrence | — |
| GRU simplifications | ✓ 2-gate comparison | — | — |
| Temperature sampling | ✓ Practical code | — | ✓ Inference optimization |
| Embedding layers | ✓ Lookup table, trainable | — | — |
| Production serving | — | — | ✓ Batching, KV cache |
| Autoregressive bottleneck | Implicit (seq decode) | — | ✓ Sequential decode cost |

## Corroboration

- **DL Ch10** (Deep Learning book): Confirms the cell state gradient highway solves vanishing gradients, extending reliable learning to hundreds of timesteps. Adds the echo-state-network perspective (reservoir computing) and multi-timescale RNNs that GDL doesn't cover.
- **AI Engineering Ch9**: Covers production inference optimization and batch serving of autoregressive models — key system-design bridge that GDL (ML-research-focused) omits entirely.
- **GDL Ch9** (Transformers): Provides the transition path from LSTM/PixelCNN to Transformer-based autoregressive models — the practical successor architecture that dominates modern text generation.

## Key Gaps in GDL Ch5 for System Design

1. **Training vs inference asymmetry**: GDL trains with teacher forcing (ground truth input at each timestep) but generates with model output as input → distribution shift at inference.
2. **No production metrics**: No discussion of latency, throughput, or memory for autoregressive generation.
3. **PixelCNN not system-relevant**: The PixelCNN section (CNN-based per-pixel autoregressive generation) is valuable as ML knowledge but not directly relevant to LLM system design.

## Status: canon_ready

This note corroborates GDL Ch5 against the vault's existing DL Ch10 and AI Engineering Ch9 coverage. The GDL Ch5 content fills a practical-implementation gap that DL Ch10 (theory-focused) and AI Engineering Ch9 (production-focused) leave open.
