---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_id: local_books.generative_deep_learning
chapter: "8"
chapter_title: "Diffusion Models"
extraction_method: pdftotext_direct_read
local_source: "/Users/saumyamehta/DS interview prep/books/Generative-Deep-Learning.pdf"
pages: "pp.205-220"
official_sources:
  - https://www.oreilly.com/library/view/generative-deep-learning/9781098134174/
  - https://arxiv.org/abs/2011.13456 (Score SDE)
  - https://arxiv.org/abs/2303.01469 (Consistency Models)
  - https://arxiv.org/abs/2310.04378 (Latent Consistency Models)
  - https://arxiv.org/abs/2409.01296 (FLUX.1)
related:
  - "[[../generative-model-taxonomy-and-multimodal-controls]]"
  - "[[ch07-energy-based-models]]"
  - "[[ch06-normalizing-flows]]"
  - "[[../../01-sources/official-open/gdl-ch7-ch8-diffusion-ebm-cross-check]]"
---

# Chapter 8: Diffusion Models

## Forward Process (Diffusion)

The forward process gradually adds Gaussian noise over T time steps:

$$q(x_t | x_{t-1}) = \mathcal{N}(x_t; \sqrt{1-\beta_t} \cdot x_{t-1}, \beta_t \cdot I)$$

Key property: due to the Markov chain structure, we can sample **any** noisy version x_t directly:

$$x_t = \sqrt{\bar{\alpha}_t} \cdot x_0 + \sqrt{1-\bar{\alpha}_t} \cdot \epsilon$$

where α_t = 1 - β_t, α_bar_t = prod_{s=1}^t α_s, and ε ~ N(0, I).

At the final timestep T, the data distribution is completely destroyed into pure Gaussian noise.

## Reverse Process (Denoising)

The reverse process learns to **reverse the noising** — starting from pure noise and iteratively removing it:

$$p_\theta(x_{t-1} | x_t) = \mathcal{N}(x_{t-1}; \mu_\theta(x_t, t), \Sigma_\theta(x_t, t))$$

The model (typically a **UNet**) is trained to predict the **noise ε** at each timestep, not the image directly. Given the predicted noise, we can compute the denoised sample.

## DDPM: Denoising Diffusion Probabilistic Models

The standard DDPM training loop:

1. Sample a random timestep t from [1, T]
2. Sample noise ε ~ N(0, I)
3. Noise the image: x_t = sqrt(α_bar_t) * x_0 + sqrt(1 - α_bar_t) * ε
4. Predict the noise: ε_θ = UNet(x_t, t)
5. Loss: MSE(ε, ε_θ)

During sampling, we start from x_T ~ N(0, I) and iteratively denoise T steps using the predicted noise.

## DDIM: Accelerated Sampling

DDIM (Denoising Diffusion Implicit Models) introduces a **non-Markovian** forward process:

- Instead of T sequential steps, DDIM can skip steps during sampling
- The process is **deterministic** given the noise — the same noise produces the same image
- Can sample with as few as **10-50 steps** (vs 1000 for DDPM) with minimal quality loss
- Tradeoff: fewer steps = faster generation, slightly lower quality

## Scheduler

The **noise scheduler** defines how β_t changes over timesteps:

| Schedule | Properties |
|----------|-----------|
| **Linear** | β increases linearly from β_1 to β_T. Original DDPM. |
| **Cosine** | β_t ~ cos². Better for high-resolution images. Smoother. |
| **Scaled Linear** | Linear with scaling. Used in some practical implementations. |

The scheduler also controls the **sampling algorithm** (DDPM vs DDIM vs other ODE solvers).

## UNet Architecture

The UNet denoiser has a symmetric encoder-decoder structure:

- **Down blocks:** Convolutional layers that progressively downsample (via stride or pooling), increasing channel depth
- **Up blocks:** Transposed convolutions that upsample back to original resolution
- **Skip connections:** Direct connections between corresponding down/up blocks — preserve high-frequency detail
- **Attention:** Self-attention and cross-attention at **low-resolution** levels (typically 8×8 or 16×16 feature maps)

The time step t is injected via sinusoidal positional encoding (like in Transformers).

## Classifier-Free Guidance

Classifier-free guidance (CFG) steers generation toward a specific class without a separate classifier:

1. Train a **conditional model** ε_θ(x_t, t, c) and an **unconditional model** ε_θ(x_t, t, ∅)
2. During sampling, interpolate:
   $$ε = ε_θ(x_t, t, ∅) + w \cdot [ε_θ(x_t, t, c) - ε_θ(x_t, t, ∅)]$$
3. **guidance_scale w:** Higher values (7-15) → stronger conditional signal, less diversity
4. The unconditional model is obtained by setting a fixed percentage (e.g., 10%) of conditioning labels to a null token during training

## Latent Diffusion

Latent Diffusion Models (LDMs) operate in a compressed latent space:

1. **VAE Encoder:** Compresses the image by ~8× (e.g., 256×256×3 → 32×32×4)
2. **UNet denoises** in this compressed latent space (much cheaper than pixel space)
3. **VAE Decoder:** Decodes the denoised latent back to pixel space

This is the architecture behind **Stable Diffusion** — enables high-resolution generation on consumer GPUs.

## Modern Advances: SD3 / MMDiT / Rectified Flow

Recent diffusion models (Stable Diffusion 3, MDT-iT) break from the UNet tradition:

- **MMDiT (MM-DiT):** Uses a **Transformer-based** architecture instead of UNet
- **Rectified Flow:** Replaces the standard variance-preserving forward process with a **straight-line** path from data to noise
  - Benefits: faster sampling (fewer steps), simpler formulation
  - The flow path is "straightened" by repeatedly training the model on its own predictions

## Score-Based SDE Framework (Song et al. 2021)

A unified framework that connects score matching (EBM lineage, Ch7), DDPM, and DDIM under a single stochastic differential equation:

- **Forward SDE:** Data → noise via a continuous-time diffusion process (d x = f(t) d t + g(t) d w)
- **Reverse SDE:** Noise → data via the same process run backward, using a learned score function (∇_x log p_t(x))
- **Probability Flow ODE:** A deterministic ODE that shares the same marginal densities as the SDE — enables exact likelihood computation and fast deterministic sampling
- Three sampling strategies: predictor-corrector (highest quality), reverse diffusion (standard), and ODE-based (fastest)

**Key insight:** The score function in the SDE framework = the noise prediction ε_θ in DDPM = -∇_x E_θ(x) in the EBM formulation (Ch7). This unifies all three approaches: EBM score matching, diffusion denoising, and continuous-time SDE sampling.

## Consistency Models (Song et al. 2023, ICML 2023)

A new model family that learns a direct mapping from any point on the diffusion trajectory to the initial data point:

- **Single-step sampling:** Instead of iterating T denoising steps, a consistency model predicts x₀ directly from x_T in one forward pass
- **Training modes:** (a) distillation from a pretrained diffusion model, or (b) standalone training using score matching objectives
- **Multi-step refinement:** Quality can be improved by chaining 2-4 steps without reverting to full T-step diffusion
- **Tradeoff:** Single-step ≈ GAN speed but lower quality; 2-4 steps match full diffusion quality at ~10-50× speedup

**Relevance for Agent Studio:** Enables real-time generation on consumer hardware. Sub-1s inference from latent diffusion models is possible via consistency distillation.

## Latent Consistency Models (Luo et al. 2023)

Applies consistency distillation specifically to Stable Diffusion:

- **LCM-LoRA:** A parameter-efficient LoRA adapter that converts any SD checkpoint into a 2-4 step model without full fine-tuning
- Drop-in compatible: apply LCM-LoRA weights to any existing SD pipeline, swap scheduler to LCMScheduler
- Makes real-time text-to-image feasible on consumer GPUs (2-4 steps vs 25-50)

## FLUX.1 (Black Forest Labs, 2024)

Current state-of-the-art open diffusion model family:

- **12B parameters** with a transformer backbone (DiT-like, not UNet)
- **Rectified flow formulation:** straight-line noise→data paths trained via flow matching
- **Three variants:** FLUX.1-pro (full quality), FLUX.1-dev (open weights), FLUX.1-schnell (distilled, 1-4 steps)
- Outperforms Midjourney and DALL-E 3 in human evaluation

**Architecture shift implication:** The progression SDXL (UNet) → SD3 (MMDiT) → FLUX.1 (Transformer) shows a clear architecture migration from UNet to transformer-based denoisers. New routes should plan for transformer backbones.

## Sampling Speed Spectrum

| Approach | Steps | Quality | Use Case |
|----------|-------|---------|----------|
| DDPM (full) | 1000 | Best (converged) | Offline batch, highest quality |
| DDIM | 10-50 | Good | Standard inference |
| DPM Solvers | 5-20 | Good-Fair | Fast inference |
| LCM / Consistency | 2-4 | Fair-Good | Real-time, consumer GPU |
| FLUX-schnell | 1-4 | Good (SOTA variants) | Edge, real-time |
| Consistency Model (1-step) | 1 | Fair | Max speed

```mermaid
graph TD
    subgraph "DDPM: Forward Process (Diffusion)"
        X0[x₀<br/>Clean Image] -->|q(x₁|x₀)<br/>Add noise| X1[x₁]
        X1 -->|q(x₂|x₁)<br/>Add noise| X2[x₂]
        X2 -->|...| XT[x_T<br/>Pure Noise<br/>N(0,I)]
    end

    subgraph "DDPM: Reverse Process (Denoising)"
        XT -->|p_θ(x_{T-1}|x_T)<br/>UNet predicts ε| XT1[x_{T-1}]
        XT1 -->|p_θ(x_{T-2}|x_{T-1})| XT2[x_{T-2}]
        XT2 -->|...| X0Gen[x₀<br/>Generated]
    end

    subgraph "UNet Architecture"
        IN[Input x_t] --> DOWN1[Down Block 1]
        DOWN1 --> DOWN2[Down Block 2]
        DOWN2 --> DOWN3[Down Block 3<br/>+ Attention]
        DOWN3 --> BOT[Latent Bottleneck<br/>+ Self-Attention]
        BOT --> UP3[Up Block 3<br/>+ Skip from Down 3]
        UP3 --> UP2[Up Block 2<br/>+ Skip from Down 2]
        UP2 --> UP1[Up Block 1<br/>+ Skip from Down 1]
        UP1 --> OUT[Output ε_θ<br/>Predicted Noise]

        T[t] --> TIME_EMB[Time Embedding]
        TIME_EMB --> DOWN1
        TIME_EMB --> DOWN2
        TIME_EMB --> DOWN3
        TIME_EMB --> BOT
        TIME_EMB --> UP3
        TIME_EMB --> UP2
        TIME_EMB --> UP1
    end

    style X0 fill:#2ecc71,color:#fff
    style XT fill:#e74c3c,color:#fff
    style X0Gen fill:#2ecc71,color:#fff
    style OUT fill:#3498db,color:#fff
```