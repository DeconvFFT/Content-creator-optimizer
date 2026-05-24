---
type: official-source-cross-check
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-20
cross_checks:
  - source_title: "GANs in Action (Langr, Bok)"
    scope: "Chapter 10 adversarial examples, iterative attacks, robustness limits, and adversarial training"
anchor_note: "02-books/gans-in-action/gan-synthetic-media-controls.md"
sources:
  - https://arxiv.org/abs/1412.6572
  - https://openreview.net/forum?id=JcRbuE7FCJ
  - https://arxiv.org/abs/1608.04644
  - https://proceedings.mlr.press/v80/athalye18a.html
  - https://arxiv.org/abs/1705.07204
related:
  - "[[../../02-books/gans-in-action/gan-synthetic-media-controls]]"
  - "[[../../02-books/gans-in-action/chapters/ch10-adversarial-examples-transferability-and-robustness-gates]]"
  - "[[../../01-sources/official-open/gan-evaluation-training-cross-check]]"
---

# GAN Adversarial Examples And Robustness - Official Cross-Check

## Scope

This cross-check deepens the focused GANs in Action Chapter 10 note with primary/open evidence for adversarial examples, stronger first-order attacks, robustness-evaluation failure modes, and adversarial training limits. It deliberately avoids duplicating the existing GAN evaluation/training cross-check, which already covers FID, KID, spectral normalization, TTUR, and StyleGAN3.

## Cross-check result

The chapter note is directionally correct and should remain canon-ready. Primary sources sharpen four points:

1. adversarial examples are a systematic property rather than a rare curiosity;
2. iterative first-order attacks are the minimum serious robustness baseline;
3. many apparent defenses fail because they hide gradients rather than improve real robustness;
4. adversarial training helps only relative to the attacks and threat model it actually covers.

## Confirmation matrix

| Chapter theme | Official/open confirmation | Agent Studio implication |
|---|---|---|
| Small perturbations can break predictions | Goodfellow, Shlens, and Szegedy (2015) show that adversarial examples arise from small worst-case perturbations and explain why linear behavior in high-dimensional models makes them common enough to matter in practice. | Visual routes should not treat clean-set confidence as reliability evidence. Add perturbation cases to routine evals. |
| Iterative attacks are the practical robustness baseline | Madry et al. frame robustness as a min-max optimization problem and make projected-gradient first-order attacks the baseline adversary for empirical robustness testing. | `adversarial_media_eval_case` should record `epsilon_budget`, `attack_method`, `attack_steps`, `step_size`, `random_restarts`, and access mode. |
| Stronger attacks routinely break weak defenses | Carlini and Wagner show that defenses looking robust under weaker attacks can fail under stronger optimization-based attacks. | Release evidence should name attack strength explicitly; passing a one-step attack is not enough for promotion. |
| Gradient masking produces false confidence | Athalye, Carlini, and Wagner show that randomness, non-differentiability, and awkward preprocessing often create only the illusion of defense. | Robustness claims should include a gradient-masking check and adaptive-attack review before being trusted. |
| Adversarial training is useful but threat-model bounded | Goodfellow et al. introduce adversarial training; Tramèr et al. show that weak single-step training can converge to degenerate behavior and remain vulnerable to transfer attacks. | If a route uses adversarial training, metadata should distinguish `fgsm_style`, `pgd_style`, or `ensemble` training and document the held-out evaluation threat model. |
| GAN-style adversarial training and classifier robustness are related but not identical | Madry-style robust optimization reinforces the same two-player lesson as GANs: quality depends on the adversary/critic being strong enough and correctly specified. | Stable GAN training does not automatically harden downstream OCR, moderation, or classifier gates; robustness must be tested separately. |

## Canon decisions

- Keep both the GAN anchor note and the new Chapter 10 chapter note `canon_ready`.
- Add to `adversarial_media_eval_case`: `threat_model`, `epsilon_budget`, `attack_method`, `attack_steps`, `step_size`, `random_restarts`, `attack_access`, and `gradient_masking_check`.
- Add to visual-route or generated-media route metadata: `robust_training_method`, `robust_training_budget`, and `robust_eval_reference`.
- Do not accept robustness claims based only on one-step attacks, confidence shifts, or nondifferentiable preprocessing.
- Treat GAN-family generator stability and classifier robustness as separate release surfaces.

## New Agent Studio design rules

1. **Attack strength is part of the evidence.** Robustness claims are incomplete without method, budget, steps, restarts, and threat model.
2. **Iterative first-order attacks are the default baseline.** One-step attacks are screening probes, not final release evidence.
3. **Gradient masking is a failure mode, not a defense.** Randomization or awkward preprocessing must survive adaptive evaluation.
4. **Adversarial training must name its adversary.** Record whether training was FGSM-style, PGD-style, or ensemble-based and evaluate against stronger held-out attacks.
5. **GAN training stability does not imply downstream robustness.** Generated-media routes still need explicit OCR, moderation, and classifier stress tests.

## Remaining refinement

- A later pass can cross-check content-authenticity and watermark detectors against adversarial examples once synthetic-media detection becomes a more central route surface.
- If a route starts using adversarially trained or regeneration-based defenses operationally, add a focused note for adaptive-attack evaluation and defense regression policy.
