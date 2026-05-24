---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_id: local_books.generative_deep_learning
chapter: "7"
chapter_title: "Energy-Based Models"
extraction_method: pdftotext_direct_read
local_source: "/Users/saumyamehta/DS interview prep/books/Generative-Deep-Learning.pdf"
pages: "pp.191-204"
official_sources:
  - https://www.oreilly.com/library/view/generative-deep-learning/9781098134174/
  - https://github.com/dasautopilot/Generative-Deep-Learning
cross_check_status: pending_official_doc_cross_check
related:
  - "[[../generative-model-taxonomy-and-multimodal-controls]]"
  - "[[ch06-normalizing-flows]]"
  - "[[ch08-diffusion-models]]"
---

# Chapter 7: Energy-Based Models

## Core Concept: Boltzmann Distribution

Energy-Based Models (EBMs) model the data distribution using a **Boltzmann distribution**:

**p(x) = e^{-E(x)} / Z**, where Z = ∫_{x ∈ X} e^{-E(x)} dx

E(x) is a scalar **energy function** (implemented as a neural network). Low energy = plausible observation (p(x) close to 1). High energy = unlikely observation (p(x) close to 0).

**Two fundamental challenges:**
1. **Intractable normalizing denominator Z** — the integral is impossible to compute for high-dimensional data. Prevents direct maximum likelihood estimation.
2. **No obvious sampling mechanism** — the network scores inputs but doesn't generate them.

EBMs sidestep both problems via **contrastive divergence** (training) and **Langevin dynamics** (sampling), following Du & Mordatch 2019 ("Implicit Generation and Modeling with Energy-Based Models").

---

## Energy Function Design

The energy network E_θ(x) maps input → scalar:

- Stacked Conv2D layers (5×5 stride 2 → 3×3 stride 2 repeated) with increasing channels (16 → 32 → 64 → 64)
- Final layer: single fully-connected unit with **linear activation** (outputs range (−∞, ∞))
- **Swish activation** throughout: swish(x) = x · sigmoid(x) = x / (e^{-x} + 1). Smooth, non-monotonic, alleviates vanishing gradients — critical for EBMs where gradients flow through the input during Langevin sampling
- MNIST dataset (32×32 padded, pixel range [-1, 1])

---

## Sampling: Langevin Dynamics

EBMs use **stochastic gradient Langevin dynamics** to generate samples — gradient descent on the energy landscape with respect to the **input** (not network weights):

**x_k = x_{k-1} − η ∇_x E_θ(x_{k-1}) + ω**, where ω ∼ N(0, σ), x₀ ∼ U(-1, 1)

Key properties:
- η (step size) is critical — too large jumps over minima, too slow never converges
- Noise injection ω prevents falling into local minima
- Start from random uniform noise, iteratively "roll downhill" along the energy gradient
- 1,000 steps typical for final generation (60 steps used during training for efficiency)
- Gradient clipping at ±0.03 stabilizes the walk

**Critical distinction from normal NN training:**
| Aspect | NN training | Langevin sampling |
|--------|-------------|-------------------|
| Gradient w.r.t. | network weights θ | input x |
| What updates | parameters | generated image |
| Weights | change | frozen |

The process transforms random noise into recognizable digits through iterative energy minimization (Fig 7-7, 7-8 in the book show progressive emergence from noise).

---

## Training: Contrastive Divergence

Cannot use MLE because E(x) doesn't output a probability. Instead, **contrastive divergence** (Hinton, 2002) minimizes:

**∇_θ L = E_{x∼data}[∇_θ E_θ(x)] − E_{x∼model}[∇_θ E_θ(x)]**

Intuition: push down energy of real observations, pull up energy of generated (fake) observations — maximize the contrast.

**Loss formulation (implemented):**
- `cdiv_loss = mean(fake_out) − mean(real_out)` — the contrastive divergence term
- `reg_loss = α · mean(real_out² + fake_out²)` — L2 regularization (α=0.1) prevents scores from diverging to ±∞
- `loss = cdiv_loss + reg_loss`

### Sample Buffer (Persistent Contrastive Divergence)

A **replay buffer** of past generated samples speeds up training:
- Initialize with 128 random uniform images
- Each training step: ~5% fresh random noise, ~95% drawn from existing buffer
- Run 60 Langevin steps on the mix → add results to buffer
- Trim buffer to max 8,192 examples
- This reuse means each Langevin chain continues from where it left off, requiring far fewer steps per iteration

### Validation Metric

Training loss stays flat (model improves but so do buffer samples). Instead, validation computes contrastive divergence between **pure random noise** and real data — falling validation loss = genuine improvement.

### Architectural Detail: Training Step

```
Real images → add small noise (σ=0.005, prevents overfitting) → score via E(·) → real_out
Buffer → 60-step Langevin → fake images → score via E(·) → fake_out
Loss = mean(fake_out) − mean(real_out) + α(real_out² + fake_out²)
Backpropagate through E(·) weights
```

---

## Mermaid: EBM Training and Sampling Flow

```mermaid
flowchart TD
    subgraph Training["Training Loop"]
        A[Real batch<br/>from dataset] --> B[Add small noise<br/>σ=0.005]
        B --> C[Score via E_θ<br/>→ real_out]
        
        D[Sample Buffer<br/>8,192 capacity] --> E[5% fresh noise<br/>95% buffer draw]
        E --> F[60-step Langevin<br/>dynamics]
        F --> G[Generated<br/>fake images]
        G --> H[Score via E_θ<br/>(frozen weights)<br/>→ fake_out]
        G --> I[Update buffer<br/>append + trim]
        
        C --> J{Contrastive<br/>Divergence Loss}
        H --> J
        J --> K[L = mean(fake_out)<br/>− mean(real_out)<br/>+ α·L2 reg]
        K --> L[Backprop into<br/>E_θ weights]
        L --> A
    end

    subgraph Sampling["Generation (inference)"]
        M[Random noise<br/>x₀ ~ U(-1,1)] --> N[Langevin loop<br/>k=1 to 1000]
        N --> O[x_k = x_{k-1}<br/>− η·∇_x E_θ<br/>+ N(0,σ)]
        O --> P{Converged?}
        P -- no --> N
        P -- yes --> Q[Generated<br/>sample x*]
    end

    subgraph Landscape["Energy Landscape"]
        R[High energy<br/>unlikely] --> S[Gradient descent<br/>along ∇_x E_θ]
        S --> T[Low energy<br/>plausible]
    end
```

---

## Historical Context and Related Architectures

### Boltzmann Machine (1985)
- Fully connected undirected NN with binary **visible** (v) and **hidden** (h) units
- Energy: E_θ(v, h) = −½(v^T L v + h^T J h + v^T W h)
- Training: contrastive divergence via **Gibbs sampling** alternating v and h until equilibrium
- Impractically slow for large hidden layers

### Restricted Boltzmann Machine (RBM)
- Removes connections between same-type units → bipartite graph (v ↔ h only)
- Stackable into **deep belief networks**
- Still impractical for high-dimensional data — Gibbs sampling requires long mixing times

### Score Matching → Diffusion Models (Key Evolution Lineage)
EBMs → **score matching** (directly estimate ∇_x log p(x), the score function) → **noise conditional score networks (NCSN)** (Song & Ermon, multiple noise scales for low-density regions) → **Denoising Diffusion Probabilistic Models (DDPM, 2020)** → DALL·E 2, ImageGen

The score function ∇_x log p(x) = −∇_x E_θ(x) — the gradient the Langevin sampler follows. This is the direct conceptual bridge from EBMs to diffusion models (covered in Chapter 8).

---

## Sampling vs. Density Tradeoff

| Aspect | EBMs | Normalizing Flows | VAEs |
|--------|------|-------------------|------|
| Density evaluation | Intractable (Z unknown) | Tractable (exact) | Tractable (ELBO lower bound) |
| Sampling | MCMC (Langevin, expensive) | Direct (one forward pass) | Direct (decoder pass) |
| Architecture constraints | None (any differentiable net) | Invertible+Jacobian (severe) | Mild (reparameterization) |
| Training stability | Delicate (MCMC chain quality) | Stable | Stable |
| Mode coverage | Good (MCMC explores) | Weak (bottleneck) | Moderate |

EBMs sacrifice tractable likelihood for architectural freedom. The energy function can be any neural network; no invertibility constraints. The cost is expensive MCMC-based sampling at inference time.

---

## Operational Implications for Agent Studio Generative-Model Routes

1. **Latency budget**: EBM-based routes (via Langevin) are high-latency: 60-1,000 sequential gradient steps per sample. Not suitable for real-time streaming or chatbot-quality generation. Better for offline batch generation where quality > speed.

2. **Score-based routing**: EBM energy scores can serve as a **discriminator/rejection criterion** in a multi-model pipeline. The energy function evaluates candidate outputs from faster models (e.g., distilled diffusion, autoregressive) and rejects low-quality generations. This is analogous to using the EBM as a quality filter without generating through it.

3. **No quality-quantity tradeoff knob**: Unlike VAEs (β-VAE) or diffusion (step count), EBMs don't offer a continuous fidelity-vs-speed dial. You pay the full Langevin cost or you don't generate. For Agent Studio, this means EBM routes are **all-or-nothing** — use them as a standalone premium tier or a secondary verifier, not a tunable middle ground.

4. **MCMC warm-starting**: The persistent buffer technique mirrors an Agent Studio pattern of maintaining a **generation cache** from prior invocations. Chaining from previous samples rather than random noise cuts steps by ~10×. This is directly applicable to any MCMC-based service: cache past latents to reduce per-query compute.

5. **Unnormalized scoring for anomaly detection**: The Boltzmann form (no Z needed) makes EBMs natural for **out-of-distribution detection** without retraining. An Agent Studio security route could score each input and flag high-energy (low-probability) prompts as potentially adversarial — cheaper than per-query retraining or ensembling.

6. **Connection to diffusion routes**: Any Agent Studio route using diffusion models (DALL·E, Stable Diffusion, Imagen) is implicitly using the EBM score-matching lineage. The U-Net's noise predictor is a learned score function. Understanding EBMs clarifies why denoising steps work (they're Langevin dynamics in the reverse process) and why step count affects quality (shorter walks don't converge to the true energy minimum).

7. **Compute profile**: Training an EBM requires running the full Langevin chain within each training step — this is computationally expensive compared to GANs or VAEs. For Agent Studio model development: EBM training is ~5-10× more expensive per epoch than equivalent GAN training, but inference can be parallelized across Langevin chains (batch generation).

---

## Key Implementation Details

- **Swish activation**: essential for smooth gradient flow through the input during Langevin sampling
- **Input noise (σ=0.005)**: added to real images during training to prevent energy function from memorizing exact pixel locations (overfitting)
- **Gradient clipping (±0.03)**: prevents explosive updates during Langevin sampling
- **Buffer refresh (5% per step)**: keeps diversity; prevents the sampler from getting stuck in the same low-energy region
- **Learning rate**: Adam, lr=0.0001, 60 epochs
- **Langevin step size η**: tuned to 10 (relative to [-1,1] pixel range); step size is the most sensitive hyperparameter

---

## References (from book)

1. Du & Mordatch, "Implicit Generation and Modeling with Energy-Based Models," 2019. https://arxiv.org/abs/1903.08689
2. Ramachandran et al., "Searching for Activation Functions," 2017. https://arxiv.org/abs/1710.05941v2 (Swish)
3. Welling & Teh, "Bayesian Learning via Stochastic Gradient Langevin Dynamics," 2011.
4. Hinton, "Training Products of Experts by Minimizing Contrastive Divergence," 2002.
5. Woodford, "Notes on Contrastive Divergence," 2006.
6. Ackley et al., "A Learning Algorithm for Boltzmann Machines," 1985, Cognitive Science 9(1).
7. Lecun et al., "A Tutorial on Energy-Based Learning," 2006.