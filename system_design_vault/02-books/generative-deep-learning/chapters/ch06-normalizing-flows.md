---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_id: local_books.generative_deep_learning
chapter: "6"
chapter_title: "Normalizing Flow Models"
extraction_method: pdftotext_direct_read
local_source: "/Users/saumyamehta/DS interview prep/books/Generative-Deep-Learning.pdf"
pages: "Ch6 pp.167-189"
official_sources:
  - https://arxiv.org/abs/1410.8516 (NICE, Dinh 2014)
  - https://arxiv.org/abs/1605.08803 (RealNVP, Dinh 2017)
  - https://arxiv.org/abs/1807.03039 (GLOW, Kingma & Dhariwal 2018)
  - https://arxiv.org/abs/1810.01367 (FFJORD, Grathwohl 2019)
cross_check_status: canon_ready
related:
  - "[[../generative-model-taxonomy-and-multimodal-controls]]"
  - "[[./ch05-autoregressive-models]]"
  - "[[./ch08-diffusion-models]]"
  - "[[./ch03-4-vae-gan-mechanics-latent-traversal]]"
---

# Chapter 6: Normalizing Flow Models

## Change of Variables — Exact Density

Normalizing flows are built on the **change of variables** formula, which gives an **exact** (not approximate) density:

**p_X(x) = p_Z(z) × |det(J)|**

where:
- **p_X(x)** = probability density of data point x
- **p_Z(z)** = probability density of latent variable z (typically standard Gaussian)
- **J** = Jacobian matrix of transformation f at point x: J_ij = ∂f_i / ∂x_j
- **|det(J)|** = absolute determinant of the Jacobian — the volume-scaling factor

The density p_X(x) is computed **exactly**, not approximated (unlike VAEs, which optimize an ELBO, or diffusion models, which optimize a variational bound). This is the defining advantage of normalizing flows — you get a true log-likelihood for the data.

### Why the Jacobian determinant matters

When transforming from domain X to domain Z, the probability mass must be conserved. If the transformation compresses volume (X → Z maps a larger area to a smaller one), the density in Z must be proportionally **higher** to keep the integral 1. The Jacobian determinant gives exactly this volume-change ratio.

For a simple 2D example scaling x₁ by 1/3 and x₂ by 1/2, the Jacobian determinant is 1/6 — the transformed distribution would integrate to 1/6 without the |det(J)| correction factor.

## The Two Practical Challenges

Applying change of variables at scale runs into two problems:

1. **O(d³) determinant cost**: For a D-dimensional space, the determinant of a dense D×D Jacobian costs O(D³). For a 32×32 grayscale image (1024 dimensions), this is computationally prohibitive.

2. **Neural networks are not invertible by default**: A standard feedforward network maps x → y but has no inverse y → x. Even if we could compute the inverse, the Jacobian would remain dense.

Both problems are solved by **coupling layers** — a specific architecture that constrains the Jacobian to be triangular.

## RealNVP Architecture

RealNVP (Real-valued Non-Volume Preserving, Dinh et al. 2017) uses **affine coupling layers** stacked with alternating masks.

### Affine Coupling Layer

Split the D-dimensional input into two halves — first d dimensions and remaining D-d dimensions — with a binary mask:

1. **Mask**: First d dimensions feed into a neural network (scale/translation subnet); remaining D-d dimensions are masked (set to zero)
2. **Forward transform**:
   - First d pass through unchanged: z_{1:d} = x_{1:d}
   - Remaining D-d are transformed: z_{d+1:D} = x_{d+1:D} ⊙ exp(s(x_{1:d})) + t(x_{1:d})
3. **Inverse** (rearrange):
   - x_{1:d} = z_{1:d}
   - x_{d+1:D} = (z_{d+1:D} - t(x_{1:d})) ⊙ exp(-s(x_{1:d}))

The s(·) and t(·) subnets are standard neural networks (stacked Dense layers for low-D, Conv2D for images) that learn the scale and translation. s is typically bounded with tanh activation for stability; t uses linear activation.

### Tractable Jacobian

The Jacobian of a coupling layer is **lower triangular**:

- Top-left d×d = Identity (z_{1:d} = x_{1:d})
- Top-right = 0 (z_{1:d} not dependent on x_{d+1:D})
- Bottom-right = diag(exp(s(x_{1:d}))) (z_{d+1:D} linearly depends on x_{d+1:D})
- Bottom-left = arbitrary (complex derivatives of s,t w.r.t. x_{1:d})

The determinant of a lower-triangular matrix is the **product of diagonal elements**:

**det(J) = exp(∑ sⱼ(x_{1:d}))**

This is O(d) to compute rather than O(d³) — the key tractability result.

### Alternating Mask Stacking

A single coupling layer leaves the first d dimensions unchanged. Stacking layers with **alternating masks** (even: first half unchanged; odd: second half unchanged) ensures every dimension eventually transforms.

Determinant of composition: det(A·B) = det(A)·det(B)
Inverse of composition: (f_b ∘ f_a)⁻¹ = f_a⁻¹ ∘ f_b⁻¹

### Training Objective

Minimize negative log-likelihood:
**−log p_X(x) = −log p_Z(z) − log |det(J)|**

where p_Z(z) is a standard Gaussian. The log determinant reduces to the **sum of scale factors** across all coupling layers, making the loss function cheap.

## GLOW: Generative Flow

GLOW (Kingma & Dhariwal 2018, NeurIPS) solves the channel permutation problem in RealNVP with two key innovations:

### Invertible 1×1 Convolutions

RealNVP relied on fixed channel-flipping between layers (reverse the order of channels). GLOW replaces this with a **learned 1×1 convolution** that acts as a general channel permutation. The 1×1 conv matrix is initialized as a rotation matrix with determinant = 1, and its log-determinant is tractable: log|det(W)| = log|det(W)| (trace-based computation for the convolutional case, O(c) for c channels).

### Actnorm (Activation Normalization)

An affine transformation per channel with learned scale and shift, initialized so the first minibatch has mean 0 and std 1 (data-dependent initialization). Actnorm functions as a channel-wise batch normalization with tractable log-determinant.

### Multi-Scale Architecture

GLOW uses a multi-scale (squeeze → flow → split) architecture where spatial dimensions are progressively compressed and channels are split off at each scale, reducing computational cost at deeper levels.

GLOW was the first normalizing flow to produce high-quality image samples (faces, bedrooms, CIFAR-10) with meaningful latent-space interpolation.

## FFJORD: Continuous-Time Flows

FFJORD (Free-form Jacobian of Reversible Dynamics, Grathwohl et al. 2019, ICLR) takes a fundamentally different approach:

### Neural ODE Formulation

Instead of discrete coupling layers stacked finitely, the transformation follows a **continuous-time** ODE:

dz(t)/dt = f_θ(z(t), t)

The forward pass solves the ODE from t₀ to t₁ using a black-box ODE solver. The log-density change follows the **instantaneous change of variables**:

d/dt[log p(z(t))] = −tr(∂f_θ/∂z)

This replaces the Jacobian determinant with a trace — O(d) rather than O(d³) — at the cost of requiring repeated solver evaluations during training.

### Tradeoffs

| Aspect | Discrete (RealNVP/GLOW) | Continuous (FFJORD) |
|--------|------------------------|---------------------|
| Number of transformations | Finite, fixed | Infinite, adaptive |
| Density computation | Product of coupling-layer determinants | ODE solver trace integral |
| Training speed | Fast (parallel coupling layers) | Slow (ODE solver per step) |
| Expressiveness | Limited by layer count | Theoretically unlimited |
| Exact inversion | Closed-form per layer | Requires ODE solver backward |

FFJORD is more expressive but significantly slower to train. It has not been widely adopted for production generative modeling.

## Normalizing Flows vs VAE vs Diffusion

| Property | Normalizing Flows | VAE | Diffusion |
|----------|-------------------|-----|-----------|
| Likelihood | **Exact** | Approximate (ELBO) | Approximate (ELBO bound) |
| Sampling | Fast (one forward pass) | Fast | Slow (iterative denoising) |
| Invertibility | Required | Not required | Not required |
| Architecture | Coupling layers | Encoder-Decoder | UNet |
| Latent space | Same dim as data | Compressed | Same dim as data |
| Computational cost | High (Jacobian/trace) | Moderate | High (many steps) |

## Production Release-Gate Notes

Normalizing flows are **not widely deployed in production** compared to VAEs and diffusion models. Key constraints for any production flow route:

1. **Latent-space dimension**: Flow latent space has the same dimensionality as data — no compression. For high-dimensional data (video, high-res images), this makes the model prohibitively large.

2. **Jacobian bottleneck**: Even with O(d) coupling-layer Jacobians, the scale/translation subnets must process the full input. For large inputs, the subnet size dominates.

3. **Expressiveness ceiling**: Stacked coupling layers struggle with highly multimodal distributions. GLOW's 1×1 convolutions help but the coupling-layer structure ultimately limits what the flow can represent.

4. **ODE training cost** (FFJORD): The ODE solver backpropagation through the solver steps is memory-intensive. Not practical at production image scales.

5. **Niche use cases**: Flows are used where exact likelihood matters — outlier detection, density estimation, and scientific simulation (not image/video generation). For generative media, diffusion models dominate.

```mermaid
graph LR
    subgraph "RealNVP Coupling Layer"
        X[Input x] --> S1[Split by mask]
        S1 --> XA[x_{1:d}<br/>Pass through unchanged]
        S1 --> XB[x_{d+1:D}]

        XA --> NN[Scale/Translation Subnet<br/>Stacked Dense/Conv2D]
        NN --> S[Scale s(x_{1:d})<br/>tanh activation]
        NN --> T[Shift t(x_{1:d})<br/>linear activation]

        XB --> M1[Multiply by exp(s)]
        S --> M1
        M1 --> A1[Add t]
        T --> A1

        A1 --> YB[z_{d+1:D} = x_{d+1:D} * exp(s) + t]
        XA --> CONCAT[Concat]
        YB --> CONCAT
        CONCAT --> Y[Output z]
    end

    subgraph "Jacobian Structure"
        J[Lower Triangular:<br/>det = ∏ diagonal = exp(∑ s)] --> DET[Tractable!<br/>O(d) instead of O(d³)]
    end

    subgraph "Stacked Layers"
        L1[Coupling 1<br/>Even Mask] --> L2[Coupling 2<br/>Odd Mask]
        L2 --> LN[... N layers<br/>Alternating]
        LN --> L_OUT[Fully transformed]
    end

    style X fill:#3498db,color:#fff
    style Y fill:#e74c3c,color:#fff
    style DET fill:#2ecc71,color:#fff
    style NN fill:#f39c12,color:#fff
    style J fill:#95a5a6,color:#fff