---
type: source-cross-check
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-20
book: Generative Deep Learning
books_source_id: local_books.generative_deep_learning
chapter: "10 - Advanced GANs"
notes: >
  Focused corroboration for the direct-read Chapter 10 note. Uses primary/open
  sources for ProGAN, StyleGAN, StyleGAN2, SAGAN, BigGAN, VQ-GAN, and
  ViT VQ-GAN to sharpen architecture and release-gate implications without
  storing raw source text or long excerpts.
---

# GDL Chapter 10 Cross-Check: Advanced GANs

## Why these sources were selected

The chapter's highest-value claims are about how image GANs evolved into controllable, artifact-aware, globally coherent, and tokenized media systems. The sources below were chosen because each one sharpens a specific operational decision that the book surfaces but does not fully separate into release-gate language.

## Source-by-source corroboration

### 1. ProGAN — Progressive Growing of GANs for Improved Quality, Stability, and Variation
- **URL:** https://arxiv.org/abs/1710.10196
- **What it sharpens:** progressive growing is a deliberate training curriculum for stabilizing high-resolution GANs, not just a convenience trick.
- **Route implication:** routes that rely on staged-resolution training should record the growth schedule, transition policy, and when the route can safely move to full-resolution evaluation.

### 2. StyleGAN — A Style-Based Generator Architecture for GANs
- **URL:** https://arxiv.org/abs/1812.04948
- **What it sharpens:** the mapping-network plus synthesis-network split is an architecture for disentangling semantic style from rendered detail.
- **Route implication:** latent interfaces can expose coarse/global versus fine/local controls, which is materially different from a single opaque conditioning vector.

### 3. StyleGAN2 — Analyzing and Improving the Image Quality of StyleGAN
- **URL:** https://arxiv.org/abs/1912.04958
- **What it sharpens:** weight modulation/demodulation is the practical fix for StyleGAN-family artifacts and removes the need to treat progressive growing as mandatory.
- **Route implication:** artifact review and latent-geometry smoothness are first-class release criteria for editable image routes.

### 4. SAGAN — Self-Attention Generative Adversarial Networks
- **URL:** https://arxiv.org/abs/1805.08318
- **What it sharpens:** GANs need explicit long-range dependency modeling when spatially distant regions must stay semantically coherent.
- **Route implication:** scene-level consistency checks should exist whenever the route claims structured object or composition fidelity.

### 5. BigGAN — Large Scale GAN Training for High Fidelity Natural Image Synthesis
- **URL:** https://arxiv.org/abs/1809.11096
- **What it sharpens:** scale and class conditioning can dramatically improve GAN fidelity, but the truncation trick exposes a direct diversity-versus-quality tradeoff.
- **Route implication:** quality benchmarks without diversity accounting can misstate route readiness.

### 6. VQ-GAN / Taming Transformers for High-Resolution Image Synthesis
- **URL:** https://arxiv.org/abs/2012.09841
- **What it sharpens:** a discrete visual codebook plus adversarial/perceptual reconstruction creates image tokens that are sharp enough for Transformer-based generation.
- **Route implication:** the tokenizer, codebook, and decoder become part of the media route contract rather than hidden pre-processing.

### 7. ViT VQ-GAN / Vector-quantized Image Modeling with Improved VQGAN
- **URL:** https://arxiv.org/abs/2110.04627
- **What it sharpens:** the tokenizer itself can move from conv-centric to Transformer-centric image processing while preserving discrete-token generation.
- **Route implication:** Transformer-native media stacks should track token formation quality, patch granularity, and decoder reconstruction behavior.

## Consolidated operational deltas

| Theme | Canonical source | Operational conclusion |
|---|---|---|
| staged-resolution stability | ProGAN | training schedule is evidence, not background detail |
| disentangled style control | StyleGAN | expose layer-wise or scale-wise control surfaces |
| artifact cleanup and smoother edits | StyleGAN2 | generator-family artifact tests are required |
| global object coherence | SAGAN | local realism alone is insufficient |
| conditional fidelity vs diversity | BigGAN | sampling knobs must be logged and reviewed |
| discrete image tokens | VQ-GAN | tokenizer/codebook lineage is product-surface evidence |
| Transformer-native visual tokenizer | ViT VQ-GAN | image generation can share sequence-style governance with multimodal systems |

## Agent Studio takeaways

1. **Architecture family is governance-relevant.** A StyleGAN2 route and a VQ-GAN route should not share the same release checklist because one is judged by latent editability and artifact behavior while the other is also judged by tokenizer/codebook behavior.
2. **Sampling policy affects product semantics.** BigGAN-style truncation can quietly optimize for prettier demos while reducing variety; that tradeoff belongs in route metadata.
3. **Tokenized image generation belongs with multimodal systems.** VQ-GAN and ViT VQ-GAN make image generation look more like sequence generation, so datastore and release-gate design should capture token vocabulary, codebook revision, and decoder lineage.
4. **Global coherence and local sharpness are separate gates.** SAGAN and StyleGAN2 solve different failure classes; routes need tests for both.
