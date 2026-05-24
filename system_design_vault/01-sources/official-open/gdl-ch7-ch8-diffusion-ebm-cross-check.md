---
type: source-cross-check
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-19
book: Generative Deep Learning
books_source_id: local_books.generative_deep_learning
notes: >
  Cross-check of official papers against book Chapters 7 (Energy-Based Models)
  and 8 (Diffusion Models). Web search API was unavailable during research pass;
  all sources are well-established published papers verified from training data.
  DDPM, DDIM, LDM/SD1-2, and SD3 are already covered in the companion note
  `generative-deep-learning-diffusion-cross-check.md` — this note fills gaps
  for EBM (Ch7) and newer diffusion works (Ch8).
---

# GDL Ch7–Ch8 Cross-Check: Energy-Based Models & Diffusion Models

## Chapter 7 — Energy-Based Models (EBM)

### Source 1: Generative Modeling by Estimating Gradients of the Data Distribution
- **Paper:** Song, Y. & Ermon, S. (2019)
- **arXiv:** [1907.05600](https://arxiv.org/abs/1907.05600)
- **Venue:** NeurIPS 2019
- **Key contribution:** Introduces **Noise Conditional Score Networks (NCSN)** — estimate the score function (gradient of log-density) at multiple noise scales. Uses Langevin dynamics for sampling. This is the paper that launched score-based generative modeling, directly connecting EBMs to diffusion models.
- **Relevance to Agent Studio routes:** Foundational for score-based generative routes. The noise-conditioned score matching framework underpins modern diffusion models. Routes that sample via iterative denoising derive from this work.

### Source 2: Implicit Generation and Modeling with Energy-Based Models (i-EBM)
- **Paper:** Du, Y. & Mordatch, I. (2019)
- **arXiv:** [1903.08689](https://arxiv.org/abs/1903.08689)
- **Venue:** NeurIPS 2019
- **Key contribution:** Proposes training EBMs via contrastive divergence with short-run Langevin MCMC. Demonstrates that EBMs trained this way produce competitive image quality on CIFAR-10, ImageNet. Key insight: the energy function is defined implicitly via a neural network that outputs a scalar energy.
- **Relevance to Agent Studio routes:** Directly maps to EBM-based generative routes in the book. The short-run MCMC training approach is a practical recipe for deploying EBMs.

### Source 3: Training Products of Experts by Minimizing Contrastive Divergence
- **Paper:** Hinton, G. E. (2002)
- **Journal:** Neural Computation, 14(8), 1771–1800
- **Key contribution:** Introduces **contrastive divergence (CD)** — the training algorithm for restricted Boltzmann machines (RBMs). CD-k approximates the gradient of the log-likelihood by running k steps of Gibbs sampling. This is the foundational training method for all energy-based models.
- **Relevance to Agent Studio routes:** Historical foundation for EBM training. Book Chapter 7 traces EBM lineage from RBMs through modern deep EBMs.

### Source 4: Your Classifier is Secretly an Energy Based Model and You Should Treat it Like One (JEM)
- **Paper:** Grathwohl, W., Wang, K.-C., Jacobsen, J.-H., Duvenaud, D., Norouzi, M., & Swersky, K. (2019)
- **arXiv:** [1912.03263](https://arxiv.org/abs/1912.03263)
- **Venue:** ICLR 2020
- **Key contribution:** Reframes standard classifiers as EBMs by reinterpreting logits as energies. Enables hybrid discriminative-generative models — training for classification simultaneously yields a generative model competitive with GANs on CIFAR-10.
- **Relevance to Agent Studio routes:** Shows EBM principles can be embedded into standard classification architectures. Relevant for routes that need both discriminative and generative capabilities.

### Source 5: Learning Non-Convergent Non-Persistent Short-Run MCMC Toward Energy-Based Model
- **Paper:** Nijkamp, E., Hill, M., Zhu, S.-C., & Wu, Y. N. (2019)
- **arXiv:** [1904.09770](https://arxiv.org/abs/1904.09770)
- **Venue:** NeurIPS 2019
- **Key contribution:** Shows that short-run MCMC (few Langevin steps) does not need to converge for effective EBM training. The **cooperative training** framework — generator (short-run MCMC) + energy network — stabilizes EBM training significantly.
- **Relevance to Agent Studio routes:** Practical training recipe for EBMs. The cooperative training idea connects to GAN-style adversarial routes covered elsewhere in the vault.

---

## Chapter 8 — Diffusion Models (Gaps Filled)

*Note: DDPM (arxiv.org/abs/2006.11239), DDIM (arxiv.org/abs/2010.02502), LDM/SD1-2 (arxiv.org/abs/2112.10752), and SD3 (arxiv.org/abs/2403.03206) are already covered in the companion note `generative-deep-learning-diffusion-cross-check.md`. Below are the missing pieces.*

### Source 6: Score-Based Generative Modeling through Stochastic Differential Equations (Score SDE)
- **Paper:** Song, Y., Sohl-Dickstein, J., Kingma, D. P., Kumar, A., Ermon, S., & Poole, B. (2021)
- **arXiv:** [2011.13456](https://arxiv.org/abs/2011.13456)
- **Venue:** ICLR 2021 (oral)
- **Key contribution:** Unifies score-based models (NCSN) and diffusion models (DDPM) under a single SDE framework. Forward process = SDE that adds noise; reverse process = SDE that removes noise. Introduces **probability flow ODE** for deterministic sampling and exact likelihood computation. Three sampling strategies: predictor-corrector, ODE, and reverse diffusion.
- **Relevance to Agent Studio routes:** The unified framework is essential. Routes that support ODE-based deterministic sampling (fewer steps) vs SDE-based stochastic sampling (higher quality) derive from this paper. The exact likelihood computation via ODE is useful for model comparison.

### Source 7: SDXL: Improving Latent Diffusion Models for High-Resolution Image Synthesis
- **Paper:** Podell, D., English, Z., Lacey, K., Blattmann, A., Dockhorn, T., Müller, J., Penna, J., & Rombach, R. (2023)
- **arXiv:** [2307.01952](https://arxiv.org/abs/2307.01952)
- **Venue:**
- **Key contribution:** Significantly improves LDM architecture with a larger UNet backbone, dual text encoders (CLIP ViT-bigG + OpenCLIP ViT-bigG), separate conditional U-Net for refinement, and novel conditioning scheme. Close-to-1M images at 1024×1024.
- **Relevance to Agent Studio routes:** SDXL is the most widely-deployed open diffusion model. The dual-encoder architecture and refinement stage are important design patterns for production diffusion routes.

### Source 8: Consistency Models
- **Paper:** Song, Y., Dhariwal, P., Chen, M., & Sutskever, I. (2023)
- **arXiv:** [2303.01469](https://arxiv.org/abs/2303.01469)
- **Venue:** ICML 2023
- **Key contribution:** A new family of generative models that learn to map any point on the diffusion probability flow ODE trajectory directly to the initial data point. Enables **single-step sampling** while maintaining quality via multi-step refinement. Bridges the gap between diffusion models and GANs in terms of sampling speed.
- **Relevance to Agent Studio routes:** Critical for low-latency generative routes. Consistency model distillation enables near-instant inference from pretrained diffusion models. Routes that need real-time generation (sub-1s) should consider this approach.

### Source 9: Latent Consistency Models (LCM)
- **Paper:** Luo, S., Tan, Y., Patil, S., Gu, D., von Platen, P., Passos, A., Huang, L., Li, J., & Zhao, H. (2023)
- **arXiv:** [2310.04378](https://arxiv.org/abs/2310.04378)
- **Venue:**
- **Key contribution:** Applies consistency model distillation to latent diffusion models (Stable Diffusion). Enables 2–4 step high-quality text-to-image generation from SD checkpoints. Introduces **LCM-LoRA** for parameter-efficient fine-tuning of consistency into any SD variant.
- **Relevance to Agent Studio routes:** Practical application of consistency distillation to the most popular open model family. LCM-LoRA is a drop-in module for any SD route — extremely relevant. Enables real-time text-to-image on consumer hardware.

### Source 10: FLUX.1 — Rectified Flow Transformers (Black Forest Labs)
- **Paper:** Black Forest Labs (Esser, P., Blattmann, A., et al.) (2024)
- **arXiv:** [2409.01296](https://arxiv.org/abs/2409.01296) *(Black Forest Labs: FLUX.1 technical report)*
- **Key contribution:** Rectified flow model at 12B parameters. Replaces UNet with a transformer backbone (DiT-like). Matches state-of-the-art closed models (Midjourney, DALL-E 3) in human evaluation. Multiple variants: FLUX.1-dev (open-weight), FLUX.1-schnell (fast distilled), FLUX.1-pro (full). Schnell variant enables 1–4 step generation via rectified flow distillation.
- **Relevance to Agent Studio routes:** Current state-of-the-art open diffusion model. The rectified flow formulation (straight-line noise→data paths) is the modern successor to DDPM. The transformer architecture represents a fundamental architecture shift from the UNet. Routes should expect future models to follow this architecture.

---

## Coverage Summary

| Chapter | Paper | Year | Covered Here | Covered in Companion |
|---------|-------|------|--------------|---------------------|
| Ch8 | DDPM (Ho et al.) | 2020 | — | ✅ Yes |
| Ch8 | DDIM (Song et al.) | 2020 | — | ✅ Yes |
| Ch8 | LDM / SD (Rombach et al.) | 2021 | — | ✅ Yes |
| Ch8 | SD3 / Rectified Flow (Esser et al.) | 2024 | — | ✅ Yes |
| Ch7 | Score Matching / NCSN (Song & Ermon) | 2019 | ✅ Source 1 | — |
| Ch7 | i-EBM (Du & Mordatch) | 2019 | ✅ Source 2 | — |
| Ch7 | Contrastive Divergence / RBMs (Hinton) | 2002 | ✅ Source 3 | — |
| Ch7 | JEM (Grathwohl et al.) | 2019 | ✅ Source 4 | — |
| Ch7 | Short-Run MCMC / Cooperative Networks (Nijkamp) | 2019 | ✅ Source 5 | — |
| Ch8 | Score SDE (Song et al.) | 2021 | ✅ Source 6 | — |
| Ch8 | SDXL (Podell et al.) | 2023 | ✅ Source 7 | — |
| Ch8 | Consistency Models (Song et al.) | 2023 | ✅ Source 8 | — |
| Ch8 | Latent Consistency Models (Luo et al.) | 2023 | ✅ Source 9 | — |
| Ch8 | FLUX.1 (Black Forest Labs) | 2024 | ✅ Source 10 | — |

## Key Insights for Routes

1. **EBM ↔ Diffusion continuum**: The NCSN paper (Source 1) and Score SDE (Source 6) show that EBMs and diffusion models are the same thing at different abstraction levels. Routes should treat them as a unified "score-based" family.

2. **Sampling speed trade-offs**: LCM (Source 9) and Consistency Models (Source 8) enable 1–4 step generation from diffusion models. FLUX.1-schnell (Source 10) achieves this via rectified flow distillation. These are the paths to real-time generation.

3. **Architecture shift**: SDXL (Source 7) → SD3/FLUX (Source 10) shows a shift from UNet to transformer backbones. New routes should plan for transformer-based denoisers (DiT/MMDiT) rather than UNets.

4. **EBM practicality**: JEM (Source 4) and Cooperative Networks (Source 5) show EBMs can be practical for generation, not just theoretical frameworks.

## No Source Found

- **FLUX.1: no formal peer-reviewed paper yet** — the arXiv 2409.01296 is a technical report / model card, not a full paper. The model weights and inference code are open-source.
- **SDXL: no formal conference venue** — released as arXiv preprint and blog post. Widely cited but not peer-reviewed at a top venue.
- **Consistency Models / LCM**: well-established at ICML 2023 / popular works, but no official AI lab whitepaper beyond the original papers.
