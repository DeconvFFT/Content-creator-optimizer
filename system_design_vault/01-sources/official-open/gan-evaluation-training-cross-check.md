---
type: official-source-cross-check
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-19
cross_checks:
  - source_title: "GANs in Action (Langr, Bok)"
    scope: "Adversarial generation, evaluation metrics, training stability"
anchor_note: "02-books/gans-in-action/gan-synthetic-media-controls.md"
sources:
  - https://arxiv.org/abs/2106.12423
  - https://arxiv.org/abs/1706.08500
  - https://arxiv.org/abs/1801.01473
  - https://arxiv.org/abs/1802.05957
  - https://github.com/NVlabs/stylegan3
related:
  - "[[../../02-books/gans-in-action/gan-synthetic-media-controls]]"
  - "[[../../02-books/generative-deep-learning/generative-model-taxonomy-and-multimodal-controls]]"
  - "[[../../02-books/hands-on-generative-ai/generative-media-pipelines]]"
  - "[[../../01-sources/official-open/content-provenance-synthetic-media-disclosure]]"
---

# GAN Evaluation And Training - Official Cross-Check

## Scope

This cross-check deepens the existing GANs in Action anchor note's coverage of training stability techniques, evaluation metrics, and architecture evolution beyond the book's 2019 publication date. The anchor note covers FID/IS conceptually and mentions Wasserstein-style framing, gradient penalties, and normalization as stability techniques. This cross-check adds specific primary-source depth on the FID paper's formal grounding, the KID alternative, spectral normalization, and the StyleGAN3 architecture evolution.

## Cross-Check Result

The anchor note's design rules (explicit critic surface, distribution-level metrics as signals not product tests, diversity checks, and conditioning contracts) are strongly reinforced by the primary sources. The cross-check adds four specific material deepening points: (1) FID's formal two-time-scale convergence proof and its implications for GAN evaluation, (2) KID as an unbiased alternative with different statistical properties, (3) spectral normalization as a principled Lipschitz constraint that subsumes earlier gradient-penalty approaches, and (4) StyleGAN3's alias-free architecture that addresses pixel-locking artifacts directly relevant to animation/video use.

## Confirmation Matrix

| GANs in Action anchor theme | Official/open-source confirmation | Agent Studio design implication |
|---|---|---|
| FID-style metrics are distribution-level signals, not product acceptance tests | Heusel et al. (NeurIPS 2017, arXiv:1706.08500) introduce FID alongside the Two Time-Scale Update Rule (TTUR). TTUR gives individual learning rates to discriminator and generator, and they prove convergence to a stationary local Nash equilibrium under mild assumptions. FID captures generated-vs-real image similarity better than Inception Score by comparing multivariate Gaussians in Inception feature space. Critically, FID is a distribution-level metric that does not evaluate individual sample quality, prompt compliance, or brand fit. | The anchor's warning that FID is "not a product acceptance test" is formally grounded. Agent Studio should record FID as one signal in a multi-signal eval: FID for distribution-level quality, prompt/condition compliance checks for per-sample correctness, diversity metrics for coverage, and human review for brand/safety/rights. Never promote a generated-media route on FID alone. |
| Training instability requires explicit stability controls | Spectral Normalization (Miyato et al. 2018, arXiv:1802.05957) normalizes each weight matrix by its spectral norm (largest singular value), enforcing a Lipschitz constraint on the discriminator. This is more principled than gradient penalties (WGAN-GP) because the constraint is exact per-layer rather than approximate from sampled gradients. It is simpler to implement and more stable in practice. | Generated-media route records should specify the discriminator stability method (spectral norm | gradient penalty | none) and its intended Lipschitz bound. Routes that omit stability controls should justify why (e.g., non-adversarial training). |
| Evaluation metrics have different statistical properties | KID (Bińkowski et al. 2018, arXiv:1801.01473) is an unbiased estimator of the Maximum Mean Discrepancy using polynomial kernels in Inception feature space. Unlike FID, KID does not assume Gaussian distributions, is unbiased (no need for held-out images), and provides a p-value for significance testing. However, KID and FID can disagree and neither captures per-sample quality. | Agent Studio's `generator_discriminator_eval` should record which distribution-level metric is used (FID | KID | IS | other), its statistical assumptions, whether it is biased or unbiased, and what it does not measure (per-sample compliance, brand fit, rights safety, identity preservation). |
| Latent space and conditioning control | StyleGAN3 / Alias-Free GAN (Karras et al. 2021, arXiv:2106.12423) identifies that typical GAN generators produce detail glued to pixel coordinates due to aliasing from careless signal processing. Their architectural changes enforce translation and rotation equivariance at subpixel scales. This matters directly for animation and video where generated content must move naturally. | The anchor's latent-interpolation trace requirement is sharpened: routes intended for animation, video, or spatial manipulation should specifically test for pixel-locking artifacts. A `latent_interpolation_trace` should include subpixel translation/rotation equivariance checks for animation-targeted routes, not just semantic smoothness. |
| GAN training dynamics need separate generator/discriminator learning rates | TTUR (Heusel et al.) proves that giving the discriminator and generator different learning rates, rather than alternating updates with the same rate, improves convergence. This is a specific instance of the anchor's concern about discriminator/generator balance. | Route records for adversarial or critic-based training should record separate learning rates and update ratios for generator and critic components. The balance is not a single knob but a two-dimensional control surface. |

## Canon Decisions

- The GANs in Action anchor note remains canon_ready. Its design rules are confirmed and sharpened.
- Add to `generator_discriminator_eval`: `stability_method` (spectral_norm | gradient_penalty | wasserstein | none), `lipschitz_bound_target`, and `distribution_metric_assumptions`.
- Add to `latent_interpolation_trace`: `equivariance_check` field (translation | rotation | subpixel) for routes targeting animation or video.
- Add to `gan_route_profile`: `discriminator_lr`, `generator_lr`, `update_ratio`, and `ttur_compliance` flag.
- Add `kid_eval_result` as an alternative to FID when unbiased estimation or significance testing is required.

## New Agent Studio Design Rules

1. **Discriminator stability method is a route contract.** Record whether spectral normalization, gradient penalty, or no constraint is applied, and the intended Lipschitz bound. Routes without stability controls need justification.
2. **Distribution-level metrics declare their assumptions.** FID assumes Gaussian feature distributions; KID does not. Record which metric, its assumptions, what it measures, and what it does not measure.
3. **Animation/video routes test for pixel-locking.** StyleGAN3 shows that aliasing causes detail to stick to pixel coordinates. Routes intended for animation need subpixel equivariance checks beyond semantic interpolation.
4. **Generator and critic learning rates are separate controls.** TTUR proves that different learning rates improve convergence. Record both rates and the update ratio as part of the training configuration.

## Remaining Refinement

- The anchor references StyleGAN2-era progressive growing but not StyleGAN3's alias-free architecture. A future pass should evaluate whether the anchor's latent-control section needs a StyleGAN3-specific addendum for animation/video routes.
- Diffusion model evaluation metrics (CLIP score, image-reward models) should be cross-checked against the GAN evaluation framework when the vault's generative media coverage expands to diffusion-first routes.
