---
type: official-source-cross-check
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-19
cross_checks:
  - source_title: "Probabilistic ML: Advanced Topics (Murphy)"
    scope: "Bayesian deep learning, uncertainty quantification, conformal prediction"
anchor_note: "02-books/probabilistic-ml-advanced/approximate-inference-shift-interpretability.md"
sources:
  - https://arxiv.org/abs/2107.07511
  - https://arxiv.org/abs/2002.03704
  - https://arxiv.org/abs/1506.02142
  - https://arxiv.org/abs/1706.02599
  - https://probml.github.io/pml-book/book2.html
related:
  - "[[../../02-books/probabilistic-ml-advanced/approximate-inference-shift-interpretability]]"
  - "[[../../02-books/probabilistic-ml-advanced/chapters/20-beyond-the-iid-assumption-distribution-shift-ood-continual-robustness]]"
  - "[[../../03-patterns/evaluation/eval-design-canon]]"
  - "[[../../04-agent-studio-implications/Capacity Estimation - Adaptation and Serving Decisions]]"
---

# Bayesian Uncertainty Deepening - Official Cross-Check

## Scope

This cross-check deepens the existing Probabilistic ML Advanced anchor note's coverage of Bayesian deep learning, uncertainty quantification, and calibration. The anchor covers approximate inference families, BNNs, GP surrogates, and distribution shift. This cross-check adds specific primary-source depth on conformal prediction as a distribution-free uncertainty framework, Bayesian deep learning's relationship to generalization, MC Dropout as a practical Bayesian approximation, and temperature scaling for calibration -- all of which materially sharpen the anchor's design rules for uncertainty-bearing routes.

## Cross-Check Result

The anchor note's design rules (separate prediction from uncertainty, store approximation metadata, label eval failures by shift class) are strongly reinforced by the primary sources. The cross-check adds four specific material deepening points: (1) conformal prediction provides distribution-free coverage guarantees that complement the anchor's Bayesian posterior approximations, (2) Bayesian deep learning connects uncertainty to generalization in a way the anchor mentions but does not formalize, (3) MC Dropout is a practical but imperfect Bayesian approximation whose failure modes the anchor should make explicit, and (4) calibration methods like temperature scaling address the anchor's warning about treating neural confidence as Bayesian confidence.

## Confirmation Matrix

| Probabilistic ML anchor theme | Official/open-source confirmation | Agent Studio design implication |
|---|---|---|
| A route confidence score is not calibrated posterior probability | Angelopoulos and Bates (arXiv:2107.07511, 2021) introduce conformal prediction as a distribution-free framework for creating statistically rigorous uncertainty sets. Conformal prediction works with any pre-trained model, provides explicit non-asymptotic coverage guarantees (e.g., 90% of prediction sets contain the true label), and does not require distributional assumptions. This directly addresses the anchor's failure mode: "a route confidence score is treated as calibrated posterior probability." | Agent Studio routes that make safety-critical or high-impact decisions should consider conformal prediction as a complement to Bayesian posteriors. Conformal sets give distribution-free coverage guarantees; Bayesian posteriors give distribution-conditioned uncertainty. Record which framework is used, its assumptions, and its failure mode: conformal prediction degrades under distribution shift (exchangeability violation) and produces conservative sets; Bayesian posteriors are only as good as the prior and approximation. |
| BNN/ensemble/MC-dropout ideas as uncertainty context | MC Dropout (Gal and Ghahramani, arXiv:1506.02142, 2016) interprets dropout at test time as approximate variational inference in Bayesian neural networks. This provides a practical uncertainty estimate without separate BNN training. However, MC Dropout is a specific variational approximation (Bernoulli variational distribution) that underestimates uncertainty in some settings and is sensitive to the dropout rate. | The anchor's requirement to "store whether uncertainty comes from a posterior approximation, ensemble variation, bootstrap, model judge disagreement, or empirical residuals" should add MC Dropout with its specific caveats: (1) dropout rate is a hyperparameter that affects uncertainty, (2) the variational family is restricted (Bernoulli), (3) it can underestimate uncertainty for out-of-distribution inputs. Record dropout rate, number of MC samples, and OOD uncertainty quality. |
| Many parameter settings can fit training data while generalizing differently | Wilson and Izmailov (arXiv:2002.03704, 2020) argue that Bayesian deep learning provides a probabilistic perspective on generalization: Bayesian model averaging over the posterior captures multiple generalization-compatible parameter settings, not just a single point estimate. This formalizes the anchor's observation that "many parameter settings can fit the training data while generalizing differently." | For high-risk Agent Studio routes, the design rule should be: record whether the route's confidence comes from a single point estimate, Bayesian model averaging, ensemble disagreement, or conformal prediction. Bayesian model averaging is theoretically strongest but computationally expensive; conformal prediction is computationally cheap but produces sets, not calibrated probabilities. |
| Neural confidence is not Bayesian confidence | Temperature scaling (Guo et al., arXiv:1706.02599, 2017) shows that modern neural networks are miscalibrated: their confidence scores do not reflect true posterior probabilities. A simple post-hoc recalibration (learning a scalar temperature on a validation set) substantially improves calibration. However, temperature scaling only calibrates in-distribution and can still be overconfident on out-of-distribution inputs. | The anchor's warning about "do not treat a single neural confidence value as Bayesian confidence" is sharpened: routes that use neural confidence for decisions should (1) record whether calibration was applied and which method (temperature scaling | Platt scaling | isotonic regression | conformal), (2) record calibration set provenance, (3) flag that calibration does not fix OOD overconfidence. |
| Distribution shift degrades uncertainty | Conformal prediction provides coverage guarantees under exchangeability, but exchangeability is violated under distribution shift. The Angelopoulos and Bates paper addresses this with weighted conformal prediction and conformal prediction under covariate shift, but the guarantees weaken. This reinforces the anchor's distribution-shift coverage requirement. | Routes that use conformal prediction should record: (1) the exchangeability assumption and when it is violated, (2) whether weighted/shift-adapted conformal is used, (3) the coverage gap under known shift scenarios. The anchor's `distribution_shift_record` should reference conformal coverage degradation under each shift class. |

## Canon Decisions

- The Probabilistic ML Advanced anchor note remains canon_ready. Its design rules are confirmed and sharpened.
- Add `conformal_prediction_record` to datastore: model, calibration set, coverage target, prediction set sizes, exchangeability flag, shift-adapted variant, and coverage quality under known shift.
- Expand `posterior_approximation_record` to include MC Dropout specifics: dropout rate, number of MC samples, variational family, and OOD uncertainty quality assessment.
- Expand `approximate_inference_record` to include calibration method (temperature_scaling | platt_scaling | isotonic_regression | none), calibration set provenance, and OOD calibration quality.
- Add a design rule: uncertainty-bearing routes should declare their uncertainty framework (Bayesian posterior | conformal prediction | ensemble | MC dropout | none) with its assumptions, coverage guarantees, and known failure modes.

## New Agent Studio Design Rules

1. **Uncertainty framework is a first-class route decision.** Conformal prediction (distribution-free, set-valued) and Bayesian posteriors (distribution-conditioned, probability-valued) serve different purposes. Record which framework, its assumptions, and its failure modes.
2. **Calibration is not optional for confidence-bearing routes.** Neural networks are miscalibrated by default. Record whether calibration was applied, which method, on what data, and whether OOD calibration was tested.
3. **MC Dropout is a practical but restricted Bayesian approximation.** Record dropout rate, MC sample count, and OOD uncertainty quality. Do not treat MC Dropout uncertainty as equivalent to full Bayesian posterior uncertainty.
4. **Conformal coverage degrades under distribution shift.** Record exchangeability assumptions and shift-adapted variants. Weight the conformal guarantee against the anchor's shift-class coverage.

## Remaining Refinement

- The anchor does not yet cover full Bayesian deep learning training methods (SWAG, deep ensembles, last-layer Laplace). A future cross-check should evaluate these as alternatives to MC Dropout for production uncertainty estimation.
- Conformal prediction for structured outputs (multi-label, sequence, set-valued) is an active research area. When Agent Studio routes produce structured outputs with uncertainty, evaluate whether conformal approaches extend naturally.
