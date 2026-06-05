---
type: official-open-cross-check
status: canon_ready
source_id: cs336_spring2026_l17_multimodal
chapter: Lecture 17
source: CS336 Spring 2026
local_source: stanford-cs336/lectures/lecture_17.py + var/traces/lecture_17.json
extraction_method: trace_viewer_source
extracted_at: 2026-05-27T19:26:00-0500
corroboration_for: cs336-data-and-alignment
corroboration_category: multimodal
related_sources:
  - ../../02-lectures/stanford/cs336-data-and-alignment
  - ../../01-sources/official-open/gdl-ch13-multimodal-models-cross-check
  - ../../02-lectures/stanford/cs231n-vision-language-grounding
topics:
  - multimodal-models
  - vision-language-models
  - clip
  - siglip
  - llava
  - qwen-vl
  - chameleon
---

# CS336 Spring 2026 — Lecture 17: Multimodal Models

Grounded in the official public `lecture_17.py` (13.9KB) and `var/traces/lecture_17.json` (192KB) from the `stanford-cs336/lectures` GitHub repository, first confirmed fetchable on 2026-05-27T19:26:00-0500.

> **Previous queue state**: L17 was tracked as "Alignment — RL (Percy)" under the assumption that the topic was RL systems. The course schedule actually labels Lecture 17 as "multimodality [Percy]." This note corrects that classification and adds a new multimodal-anchors dimension to the vault.

## 1. Lecture Structure

Percy Liang covers the progression from text-only LMs to multimodal/omni models through three questions:

1. How do we **input** non-text data (e.g., understand images)?
2. How do we **output** non-text data (e.g., generate audio)?
3. Can we do both with a single unified architecture?

The lecture walks through five architectural approaches in increasing sophistication.

## 2. CLIP — Contrastive Image-Text Pretraining

**Core recipe**: Learn a shared embedding space from 400M (image, caption) pairs using bidirectional contrastive loss.

- Batch of 32,768 (image, text) pairs; for each pair, maximize alignment vs 32,767 negatives
- Vision encoder: ViT-L/14@336px (Large, 14×14 patches, 336px resolution)
- Text encoder: GPT-2-style 63M Transformer (12 layers), [EOS] token activation as text embedding
- Data: 500K search queries → ~20K pairs/query, 400M total (not released; reproduced in OpenCLIP/LAION-5B)
- Preprocessing: bicubic resize (shorter side=336), center crop to 336×336
- **Headline**: zero-shot CLIP outperformed ResNet-50 trained on 1.2M ImageNet images
- **Key design**: Attention pooling (QKV with query=global average of activations); softmax over full batch
- **Ablation finding**: Predicting text from images directly is much less compute-efficient than ranking

> **Architecture implications**: CLIP treats the image encoder as a **frozen semantic backbone** — it captures enough semantics for classification but not fine-grained detail needed for generation. This is the fundamental design tension: comprehension (what's in this image?) vs generation (render this description).

## 3. SigLIP — Sigmoid Loss Variant

**Key change**: Replace CLIP's multi-class softmax with per-pair binary classification (aligned or not?).

- Sigmoid loss decouples batch size from the loss computation
- **Efficiency**: CLIP: 10 days on 256 TPUv3; SigLIP: 5 days on 32 TPUv4 (much faster)
- Better than CLIP for batch sizes < 16K; works up to 1M batch size but 32K is sufficient
- Data: WebLI — O(billion) image-text pairs scraped from internet, OCR text extraction, 10% quality filter, 100 languages

> **Architecture implications**: SigLIP's per-pair binary formulation removes the batch-size bottleneck that limits CLIP to large hardware budgets. The sigmoid loss makes vision-language pretraining tractable at smaller scale.

## 4. LLaVA — Vision Encoder + Projector + LM Template

**Architecture**: CLIP vision encoder → linear projection W → Vicuna (LLaMA fine-tuned on ShareGPT)

**Data**: MS COCO images + GPT-4 generated question/conversation pairs from captions and detected objects (158K examples)

**Training**:
- Stage 1 (alignment): freeze vision encoder and LM, train only projection W
- Stage 2 (fine-tuning): freeze vision encoder, train W + LM

> **Architecture implications**: LLaVA establishes the **standard VLM template** — a pretrained vision encoder, a lightweight adapter/projector, and a pretrained LM. The key insight is that most capability comes from the frozen backbones; the adapter only needs to learn cross-modal alignment. Flamingo/Q-Former use more complex cross-attention projectors but the principle is the same.

**LLaVA OneVision** (latest in the LLaVA series):
- Vision encoder: SigLIP (grid features before and after last Transformer layer)
- Text decoder: Qwen-2 72B
- Projector: 2-layer MLP
- **AnyRes**: break image into a×b pieces at vision encoder resolution, encode, concatenate
- Unified handling of single image (high res), multiple images (base res each), video (lower res per frame)
- **Transfer finding**: Single-image OCR generalizes to multi-image relational reasoning; visual prompting (circle) in single images generalizes to videos

## 5. Qwen-VL Family

**Qwen-VL**:
- Vision encoder: OpenCLIP ViT-bigC (14×14 patches)
- Adapter: 1-layer cross-attention with 2D positional encodings → fixed 256 tokens
- Special tokens: `<img>`, `<box>`, `<ref>` for referring and grounding
- 3-stage training: (1) large-scale low-quality data, freeze LM, train encoder+adapter; (2) higher-quality task-specific data, increased resolution, train all; (3) instruction tuning, freeze encoder, train adapter+LM

**Qwen2-VL**:
- Larger ViT (675M)
- **Dynamic resolution**: each 224×224 patch encoded with ViT/14, compress 2×2 → 66 tokens
- **MRoPE** (Multimodal Rotary Position Embedding): separate temporal/width/height axes in RoPE
- Video: sample 2 frames/sec, max 16384 tokens

**Qwen3-VL**:
- LM: Qwen-3 (dense and MoE up to 235B-A22B), 256K context
- Vision encoder: SigLIP-2
- **Interleaved MRoPE**: distribute t/w/h axes across frequency bands `[t w h t w h ...]` rather than `[t t t w w w h h h]`
- Explicit video timestamps as separate tokens (not in positional embeddings)
- **Square-root-normalized per-token loss**: balance text and multimodal data (long video examples don't dominate)
- **DeepStack adapter**: cross-layer fusion to inject visual info into multiple LM layers
- 4-stage pretraining (8K→32K→256K context), post-training SFT on long CoT + knowledge distillation + RL

> **Architecture implications**: The Qwen-VL progression shows how VLMs scale: (1) better vision encoders, (2) smarter resolution handling (dynamic resolution, AnyRes), (3) specialized positional encoding for multimodal axes (MRoPE), (4) loss balancing to prevent one modality from dominating.

## 6. Chameleon — Unified Discrete-Token Multimodal Model

**Different approach**: Instead of encoding images with CLIP/SigLIP and injecting into an LM (which can't generate images), map everything to **discrete tokens** so a single autoregressive Transformer can handle text and images uniformly.

- VQ-VAE encoder: map 512×512 image to 1024 discrete tokens (codebook size 8192)
- Train a new BPE tokenizer for multimodal tokens
- Training: 80% Stage 1 (2.9T text tokens + 1.5T text-image tokens + 400B interleaved), 20% Stage 2 (50% Stage 1 data + 50% high-quality)
- **Stability challenge**: text tokens have low entropy, image tokens have high entropy → norm growth + logit drift
  - Fixes: QK normalization, z-loss regularization

> **Architecture implications**: Chameleon is the most architecturally elegant approach (single model, single loss) but less performant than modular VLMs — discretization loses information (especially for OCR). The training stability issues from entropy imbalance across modalities are a fundamental challenge for discrete multimodal models.

## 7. Summary — The Multimodal Design Space

| Approach | Input | Output | Strength | Weakness |
|---|---|---|---|---|
| CLIP/SigLIP (contrastive) | Image → embedding | Classification only | Semantics, zero-shot | No generation |
| LLaVA (VLM template) | Encoder + adapter + LM | Text only | Comprehension, OCR | Can't generate images |
| Qwen-VL (advanced VLM) | MRoPE + dynamic res | Text + grounding | SOTA comprehension | Still text-only output |
| Chameleon (discrete tokens) | VQ-VAE → tokens | Text + image | Single model | Lower quality, training instability |

**Frontier direction**: Continuous encoders + Transformer + diffusion models for generation — combining the semantic understanding of VLMs with the generative quality of diffusion models.

## 8. Operational Implications for System Design

1. **Multimodal encoder choice is a system-design decision**: CLIP vs SigLIP vs ViT vs DFN changes the semantic granularity, resolution handling, and compute budget. The encoder's effective resolution determines what fine-grained details (OCR text, small objects) survive into the LM.

2. **Adapter/projector architecture governs cross-modal bandwidth**: Linear projection (LLaVA) is simplest but most capacity-limited. Cross-attention (Qwen-VL, Flamingo) or DeepStack (Qwen3-VL) trades simplicity for depth of visual understanding. The choice affects both comprehension quality and inference latency.

3. **Training stages encode a release-gate pattern**: Every VLM uses staged training (freeze→unfreeze→fine-tune). This is a release-gate pattern: verification gates should match training stages (alignment gate before full fine-tuning, instruction-tuning gate before deployment).

4. **Resolution handling is a latent architecture parameter**: Crop (CLIP), AnyRes (LLaVA OneVision), and dynamic resolution (Qwen2-VL) are not preprocessing trivia — they determine which visual information reaches the LM. OCR quality, small-object detection, and multi-image reasoning all depend on this choice.

5. **Entropy imbalance is a multiroute design constraint**: Chameleon's text-vs-image entropy imbalance (logit drift, norm growth) is not just a training curiosity — any system mixing low-entropy and high-entropy modalities needs per-modality normalization, loss scaling, or separate routes.

6. **The frontier trend is unified but modular**: The long-term direction is a single model handling all modalities (omni model), but the practical path uses modular encoders + adapter + LM + diffusion decoder. This means the release-gate surface includes four independently evolving components.

## Related Vault Notes

- [[../../02-lectures/stanford/cs336-data-and-alignment]] — parent CS336 alignment and data note, refreshed with multimodal anchor
- [[../../01-sources/official-open/gdl-ch13-multimodal-models-cross-check]] — GDL-based multimodal corroboration
- [[../../02-lectures/stanford/cs231n-vision-language-grounding]] — CS231n vision-language grounding
- [[../../02-lectures/stanford/cs231n-vision-language-multimodal-grounding-transcript]] — transcript-backed multimodal grounding
