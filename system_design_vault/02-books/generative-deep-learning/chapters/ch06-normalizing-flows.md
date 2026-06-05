# Chapter 6: Normalizing Flows

## Change of Variables

Normalizing flows are built on the **change of variables** formula:

**p_X(x) = p_Z(z) × |det(J)|**

where:
- p_X(x) = probability density of data point x
- p_Z(z) = probability density of latent variable z (typically Gaussian)
- J = Jacobian matrix of the transformation f at point x: J_ij = ∂f_i / ∂x_j
- det(J) = determinant of the Jacobian

The density p_X(x) is computed exactly (not approximated) — this is the key advantage over VAEs.

## Forward and Inverse

Normalizing flows define two functions:

- **Forward f (x → z):** Maps data to latent space (normalizing direction). Used for density estimation.
- **Inverse g = f^{-1} (z → x):** Maps latent to data (generating direction). Used for sampling.

Both must be **invertible** and **differentiable** — the defining constraint of normalizing flows.

## RealNVP Coupling Layers

RealNVP (Real-valued Non-Volume Preserving) uses **affine coupling layers**:

1. Split the input into two halves: x_a and x_b
2. x_a passes through **unchanged**
3. Use x_a to compute **scale** s(x_a) and **shift** t(x_a) via neural networks
4. Transform x_b: y_b = x_b * exp(s(x_a)) + t(x_a)
5. Concatenate: y = [x_a, y_b]

### Alternating Masks

To ensure every dimension gets transformed, masks are **alternated**:
- **Even mask:** First half unchanged, second half transformed
- **Odd mask:** Second half unchanged, first half transformed

Stacking coupling layers with alternating masks ensures full mixing.

## Tractable Jacobian

The Jacobian of a coupling layer is **lower-triangular**:
- First half (unchanged values): Jacobian = Identity matrix (determinant = 1)
- Second half: Derivatives of scale/shift w.r.t. first half are zeroed out by the binary mask structure

**Result:** det(J) = product of diagonal entries = exp(sum of s(x_a))

This makes the determinant computation **tractable** — O(d) instead of O(d^3).

## GLOW: Generative Flow

GLOW improves on RealNVP by replacing **fixed channel ordering** with **learnable 1×1 convolutions**:

- Instead of manually deciding which channels pass through unchanged, a 1×1 conv with a learned rotation matrix is applied before splitting
- This ensures every dimension gets transformed regardless of the splitting pattern
- Also introduces **actnorm** (activation normalization) for training stability

GLOW can generate high-quality images (faces, bedrooms) but is computationally expensive.

## FFJORD: Continuous-Time Flows

FFJORD (Free-form Jacobian of Reversible Dynamics) takes a different approach:

- Parameterizes the transformation as a **continuous-time ODE**: dz/dt = f(z(t), t)
- Instead of discrete coupling layers, the flow follows an ODE trajectory
- **Infinite steps** → **infinitesimal step size**
- Uses the **instantaneous change of variables**: d/dt [log p(z(t))] = -tr(∂f/∂z)

FFJORD is more flexible than coupling layers but requires an ODE solver, making training slower.

## Comparison: Flows vs VAE vs Diffusion

| Property | Normalizing Flows | VAE | Diffusion |
|----------|-------------------|-----|-----------|
| Likelihood | **Exact** | Approximate (ELBO) | Approximate (ELBO bound) |
| Sampling | Fast (one forward pass) | Fast | Slow (iterative denoising) |
| Invertibility | Required | Not required | Not required |
| Architecture | Coupling layers | Encoder-Decoder | UNet |
| Latent space | Same dim as data | Compressed | Same dim as data |
| Computational cost | High (Jacobian) | Moderate | High (many steps) |

```mermaid
graph LR
    subgraph "RealNVP Coupling Layer"
        X[Input x] --> S1[Split]
        S1 --> XA[x_a<br/>Pass through unchanged]
        S1 --> XB[x_b]

        XA --> NN[Neural Network]
        NN --> S[Scale s(x_a)]
        NN --> T[Shift t(x_a)]

        XB --> M1[Multiply]
        S --> M1
        M1 --> A1[Add]
        T --> A1

        A1 --> YB[y_b = x_b * exp(s) + t]
        XA --> CONCAT[Concat]
        YB --> CONCAT
        CONCAT --> Y[Output y]
    end

    subgraph "Jacobian Structure"
        J[Jacobian<br/>Lower Triangular] --> DET[det(J) = prod(diagonal)<br/>Tractable!]
    end

    style X fill:#3498db,color:#fff
    style Y fill:#e74c3c,color:#fff
    style DET fill:#2ecc71,color:#fff
    style NN fill:#f39c12,color:#fff
```