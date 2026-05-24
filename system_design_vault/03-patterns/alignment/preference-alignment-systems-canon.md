---
type: pattern-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-20
sources:
  - "[[../../02-lectures/stanford/cs25-aligning-open-language-models]]"
  - "[[../../02-lectures/stanford/cs234-policy-gradient-ppo]]"
  - "[[../../02-lectures/stanford/cs336-data-and-alignment]]"
  - "[[../../02-lectures/stanford/cs224r-preference-optimization-rlhf-dpo]]"
  - "[[../../02-lectures/stanford/cs224r-reward-reasoning-world-models]]"
  - "[[../../02-books/llm-engineers-handbook/chapters/6-fine-tuning-with-preference-alignment]]"
  - "[[../evaluation/eval-design-canon]]"
  - "[[../llm-systems/nlp-llm-systems-canon]]"
  - https://cs336.stanford.edu/
  - https://raw.githubusercontent.com/stanford-cs336/lectures/main/lecture_15.pdf
  - https://github.com/stanford-cs336/lectures/blob/main/lecture_16.pdf
  - https://cs336.stanford.edu/spring2025/index.html
  - https://github.com/stanford-cs336/assignment5-alignment
  - https://github.com/stanford-cs336/spring2025-lectures/blob/61eddac004df975466cff0329b615f2d24230069/nonexecutable/2025%20Lecture%2015%20-%20RLHF%20Alignment.pdf
  - https://github.com/stanford-cs336/spring2025-lectures/blob/e94e33f433985e57036b25215dff2a4292e67a4f/nonexecutable/2025%20Lecture%2016%20-%20RLVR.pdf
  - https://raw.githubusercontent.com/stanford-cs336/spring2025-lectures/main/lecture_17.py
  - https://cs224r.stanford.edu/
  - https://cs224r.stanford.edu/slides/09_cs224r_rlhf_2026.pdf
  - https://web.stanford.edu/class/cs234/modules.html
  - https://web.stanford.edu/class/cs234/slides/lecture6pre.pdf
related:
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
  - "[[../../03-patterns/evaluation/prompt-workflow-eval-datasets]]"
---

# Preference Alignment Systems Canon

## Scope

This canon note consolidates Agent Studio alignment decisions from the CS336 data/alignment note, the local LLM Engineers Handbook preference-alignment chapter, and the existing eval-design canon. It now includes direct-read current Spring 2026 CS336 Lecture 15 public material on mid/post-training, SFT, RLHF data, PPO, DPO, and reward-overoptimization caveats, plus direct-read current Spring 2026 Lecture 16 public material on RLVR, GRPO caveats, verifier design, and reasoning-RL boundaries. It still uses the official Spring 2025 CS336 alignment archive as corroboration for RLVR and as the current official baseline for RL systems coverage. Lecture 17 current-2026 RL-systems material is now visibly public on the official course page, but it has not been directly ingested in this pass, so this note does not claim current 2026 RL-systems lecture coverage.

This note stores original synthesis only. It does not store slide text, assignment solutions, raw book text, or long excerpts.

The CS224R Spring 2026 preference-optimization, reward-learning, and reasoning lectures now provide current official Stanford post-training coverage for RLHF, DPO, reward-model fragility, verifiable rewards, reward blind spots, behavior/style drift, test-time compute, and long-horizon eval budgets. CS234 Winter 2026 adds the policy-gradient/PPO mechanics layer: baselines, advantage estimates, on-policy data limits, policy-space drift, adaptive KL penalties, and clipped-objective controls. CS25's "Aligning Open Language Models" recording entry plus Ai2 Tülu 3 / RewardBench / DPO / InstructGPT open materials add the open-recipe lens: models, data, code, evaluation, decontamination, negative results, and reproducibility artifacts. Together they complement the now-public CS336 Spring 2026 Lecture 16 RLVR material while Lecture 17 remains direct-read pending.

## Canon Decision

Agent Studio should treat feedback, preferences, reward signals, and eval grades as governed data products. They can improve routes only after provenance, rubric, source context, task slice, and regression gates are attached.

The practical rule: never optimize directly from raw thumbs-up, engagement, judge scores, or aggregate reward without preserving the trace that produced the signal.

## Feedback Is Data

CS336's data lectures frame source pipelines as lifecycle objects, and the alignment material extends that logic to feedback. A reviewer decision is not merely an annotation; it is a datapoint with origin, context, route version, source evidence, task difficulty, and downstream use.

Agent Studio commitments:

- store feedback as structured `feedback_event` records before using it as memory;
- preserve chosen and rejected artifacts for preference learning;
- attach source IDs, retrieval traces, route version, model/provider, and rubric to high-value feedback;
- separate factual correction, editorial preference, safety concern, tool failure, retrieval failure, and UI/workflow issue.

## Preference Pairs

Preference alignment is useful when two outputs are both plausible but one better matches product intent. It should not be used as a knowledge update mechanism. For source-backed work, the chosen answer must win for the right reason: grounding, completeness, clarity, safety, usefulness, platform fit, or reviewer intent.

Agent Studio commitments:

- `preference_pair` records include candidate order and evaluator type;
- model-judged pairs record judge model, rubric, calibration state, and bias mitigations;
- synthetic or model-generated pairs are labeled separately from human/editor pairs;
- style, length, citation behavior, and safety-policy labels are preserved so preference wins can be audited;
- annotator or judge source is preserved because demographics, expertise, model family, and prompt instructions can shift the route being learned;
- pairwise preference data is evaluated on held-out route tasks before promotion.

## Reward Signals

CS336 alignment mechanics distinguish verifiable rewards from preference rewards. Agent Studio should follow the same separation.

| Reward type | Examples | Use carefully because |
|---|---|---|
| Verifiable reward | JSON validity, citation exists, tool call succeeded, test passed | The metric can be gamed if it misses semantic correctness. |
| Source-grounding reward | claim supported, citation valid, retrieval coverage sufficient | Requires source snapshot and retrieval trace. |
| Preference reward | editor preferred draft A over B | Captures taste but can encode bias and instability. |
| Safety reward | policy complied, sensitive data redacted, unsafe action blocked | Needs adversarial cases and human escalation. |
| Operational reward | lower latency or cost | Must not hide quality, grounding, or safety regressions. |
| Verifier reward | tests pass, answer equivalence holds, artifact validates | Works only when the verifier actually captures the desired behavior. |

## Optimization Boundaries

Alignment optimization should be a route-change proposal, not an invisible background mutation. Whether the intervention is prompt repair, reranker tuning, DPO/adapter tuning, SFT, RLVR-style tuning, or policy change, it must bind the same artifacts:

- baseline route and candidate route;
- dataset and source snapshot;
- preference/reward records used;
- eval suite and regression budget;
- safety and grounding slices;
- rollback route.

Agent Studio should prefer lighter interventions first. DPO or other tuning is appropriate only when prompt/RAG/tool/schema changes cannot fix the measured failure and the preference data is representative.

RLVR-style optimization is narrower: it is appropriate when the route has a trustworthy verifier or test harness. It should not be used for broad editorial quality unless the broad goal is decomposed into measurable slices and human-reviewed rubric gates.

CS224R tightens the DPO boundary: removing the explicit reward-model/RL loop lowers system complexity but does not remove alignment risk. DPO still needs a reference-policy assumption, pair-quality checks, behavior-drift evals, and regression gates for grounding, safety, source diversity, style, latency, and cost.

CS25 open-alignment coverage adds a reproducibility boundary: a tuned open model is only production-understandable when its base model, data, code, eval suite, decontamination process, recipe, checkpoints, and negative results are tracked. Agent Studio should apply the same discipline to route-level behavior changes, even when the change is a prompt, retrieval policy, judge rubric, or reranker rather than a model checkpoint. An `open_model_post_training_release_gate` should block promotion until base-model identity, license/terms, architecture/context assumptions, post-training recipe, released artifacts, capability slices, reward-model/judge/verifier evals, behavior-regression evidence, decontamination, negative results, fallback, rollback, and human approval are linked to the release.

The current 2026 CS336 Lecture 15 adds a sharper data-governance rule: post-training examples encode many hidden variables. Instruction datasets differ in style, length, factual density, citation behavior, safety content, tool-use traces, and scale. Preference datasets add annotator demographics, expertise, compensation, AI-assistance, verification effort, model-judge correlation, length bias, and style bias. Agent Studio should therefore refuse to treat "preference data" or "instruction data" as one generic dataset type.

This creates two additional release requirements. First, any midtraining or two-phase behavior mixture must be represented separately from SFT and preference optimization because it changes broad model behavior and can create different forgetting, reuse, rights, and rollback risks. Second, preference-pair promotion needs a bias audit before it can steer routes: length effects, style effects, annotator distribution, expert/generalist split, AI-assistance rate, model-judge agreement, and factual/source-grounding slices.

## Reward Hacking And Regression Risk

Every reward creates a failure mode. More citations can produce irrelevant citations. Short-answer rewards can omit caveats. Engagement can reward sensationalism. A style reward can erode grounding. A judge-model score can prefer its own model family or longer answers.

Agent Studio commitments:

- use blocked tradeoffs in route success contracts;
- inspect failure slices, not only aggregate reward;
- keep KL-style product constraints: improved target behavior must not destroy grounding, safety, source diversity, tone, latency, or cost;
- inspect length and entropy/mode-collapse signals when preference or RL optimization changes response shape;
- keep reward curves, rollout samples, and failed verifier cases, not only the final tuned checkpoint;
- turn reward-hacking discoveries into new eval cases.

## Datastore Objects

Add or strengthen:

| Object | Purpose |
|---|---|
| `feedback_event` | Raw human/system feedback with route, artifact, severity, decision, and routing status. |
| `preference_pair` | Chosen/rejected contrastive data with evaluator, rubric, candidate order, source evidence, and provenance. |
| `reward_signal` | Computed reward with reward type, source trace, rubric/test, scorer, calibration state, and caveats. |
| `alignment_dataset` | Curated set of feedback, preference, SFT, or reward examples with rights/provenance and intended use. |
| `midtraining_mixture_record` | Two-phase behavior mixture with source-family weights, caps, reuse limits, rights policy, scale-transfer caveat, forgetting evals, and rollback target. |
| `alignment_run` | Optimization run over prompts, policies, rerankers, adapters, or models with baseline, candidate, data, parameters, and eval outputs. |
| `policy_update_record` | Approved behavior/policy change with rationale, affected routes, eval gates, rollback, and reviewer decision. |
| `trajectory_batch_record` | Rollout or interaction batch used for policy optimization with policy version, trajectory refs, reward refs, advantage-estimator ref, reuse count, collection time, and rights status. |
| `advantage_estimator_record` | Baseline/value estimator used to turn returns into policy-gradient advantage estimates. |
| `policy_distance_record` | Behavior-space drift evidence between reference and candidate policies on route-critical slices. |
| `ppo_control_policy` | PPO control surface: adaptive KL or clipped objective, target KL or clip range, penalty adaptation, optimizer/update settings, and stop policy. |
| `ppo_update_record` | PPO-style update event with trajectory batch, advantage estimator, observed KL, clip fraction, reward delta, regressions, and decision. |
| `annotator_profile` | Reviewer, user, crowdworker, or model-judge provenance and calibration context. |
| `verifier_reward_record` | Deterministic or semi-deterministic reward with verifier version, input, output, expected condition, and failure caveats. |
| `rollout_group_record` | Candidate generations used for RLVR or best-of-n comparison with reward, length, verifier, and source-trace metadata. |
| `alignment_regression_slice` | Guardrail slice for grounding, safety, source diversity, style, length, latency, cost, and over-refusal regressions. |
| `preference_optimization_method` | Selected post-training or lighter intervention method, including SFT, RLHF, DPO, verifier-driven RL, prompt repair, reranker tuning, or no tuning. |
| `preference_data_quality_check` | Pair balance, task coverage, evaluator distribution, order bias, style/length confounds, source-evidence coverage, and leakage checks. |
| `preference_bias_audit` | Length/style effects, annotator distribution, expertise skew, AI-assistance rate, model-judge agreement, factuality slices, and source-grounding slices before preference data can steer a route. |
| `reward_overoptimization_check` | Evidence that reward gains did not hide grounding, safety, source diversity, style, latency, or cost regressions. |
| `behavior_style_shift_metric` | Length, confidence, politeness, abstention, citation density, formatting, and sycophancy drift after alignment optimization. |
| `verifiable_task_record` | Task slice with a verifier and explicit statement of what the verifier proves and what it misses. |
| `reference_policy_record` | Baseline/reference route or model used for KL-style and DPO-style comparison assumptions. |
| `base_model_record` | Base open or closed model identity, license, architecture, context limits, training disclosure, route eligibility, and deployment constraints. |
| `post_training_recipe_record` | Staged behavior-change recipe: prompt curation, demonstrations, preference data, reward/verifier method, eval suite, decontamination, and artifacts. |
| `post_training_artifact_release` | Released model/data/code/eval/checkpoint/decontamination artifact with rights status, hash, owner, and reproducibility caveats. |
| `negative_result_record` | Failed or regressing post-training, data, reward, prompt, or route-optimization attempt with reason and future-avoidance notes. |
| `capability_slice_target` | Skill slice targeted by alignment or route optimization: reasoning, coding, math, safety, chat, multilingual, citation, tool use, or platform style. |
| `reward_model_eval_record` | Reward model or judge evaluation with benchmark slice, preference type, safety/refusal behavior, OOD caveats, and calibration status. |
| `decontamination_record` | Evidence that eval, training, prompt, and retrieval data overlap was checked and mitigated. |

## Release Gates

No alignment-derived route change can ship unless:

- preference/reward data has provenance and rights status;
- source-backed examples carry source snapshots and retrieval traces;
- baseline and candidate are compared on fixed route eval slices;
- model judges are calibrated or marked advisory;
- reward signals are separated by type and not collapsed into one score;
- length/style effects and annotator/judge provenance are visible;
- midtraining mixtures are separated from SFT, preference pairs, and verifier-labeled examples;
- preference bias audits cover length, style, annotator distribution, model-judge agreement, factuality, and source-grounding slices;
- verifier rewards name the verifier version and known blind spots;
- safety, grounding, latency, and cost regressions are visible;
- pair-quality, reference-policy, and reward-overoptimization checks pass for DPO or RLHF changes;
- PPO-style updates include trajectory batch provenance, advantage-estimator records, PPO control policy, observed policy-distance/KL evidence, update diagnostics, and regression slices;
- behavior/style drift metrics show no release-blocking shift in confidence, length, abstention, citation behavior, or sycophancy risk;
- open-model or route-level post-training changes have base-model, recipe, release-artifact, decontamination, capability-slice, and negative-result records where applicable;
- rollback route and incident feedback path exist.

## Agent Studio Implications

- Feedback capture UI should ask "why" when a user rejects or accepts a generated artifact.
- Eval failures should create structured feedback and candidate eval cases.
- Preference tuning should remain downstream of source-ledger and retrieval correctness.
- Product analytics should not become alignment data until it is reviewed and task-labeled.
- The 2026 CS336 alignment refresh should be revisited after the now-visible official Lecture 17 material is directly read into the canon note.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.

- [[../../02-lectures/stanford/cs25-aligning-open-language-models]] - Stanford CS25, "Aligning Open Language Models" ([YouTube](https://www.youtube.com/watch?v=AdLgPmcrXwQ)).
- [[../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
