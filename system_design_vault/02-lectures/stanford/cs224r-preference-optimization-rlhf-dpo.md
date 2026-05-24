---
type: lecture-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_status: official_public
stores_raw_source_text: false
stores_long_excerpts: false
sources:
  - https://cs224r.stanford.edu/
  - https://cs224r.stanford.edu/slides/09_cs224r_rlhf_2026.pdf
related:
  - "[[../../03-patterns/alignment/preference-alignment-systems-canon]]"
  - "[[../../03-patterns/evaluation/eval-design-canon]]"
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
  - "[[cs336-data-and-alignment]]"
---

# CS224R - Preference Optimization, RLHF, And DPO

## Reading Scope

Direct-read pass over Stanford CS224R Spring 2026 course page and the official public lecture slides for "RL for LLMs: Preference Optimization," with a current-source check on May 18, 2026. This note uses only official Stanford course material. It does not claim video ingestion, Canvas recording access, raw slide text storage, or copied derivations.

## Core Pattern

The lecture frames post-training as a sequence of increasingly preference-aware interventions:

1. pretraining builds broad next-token and world/agent modeling capability;
2. supervised instruction tuning teaches the model the interaction format and human-intent surface;
3. preference optimization changes behavior using comparisons rather than demonstrations alone;
4. frontier post-training pushes into more precise rewards, verifiable tasks, and self-critique style loops.

For Agent Studio, the important architecture point is that preference optimization is not a generic "make better" knob. It changes behavior shape. It can improve helpfulness, formatting, and instruction-following while also introducing sycophancy, length/style drift, reward hacking, or overconfidence.

## RLHF Versus DPO

RLHF and DPO use the same essential signal type: a preferred completion and a less preferred completion for a given prompt or task. They differ in system cost and failure surface.

RLHF creates an explicit reward model and then optimizes a policy against that reward while constraining drift from the base policy. This gives a flexible optimization target but adds reward-model training, RL stability, KL-control, rollout, and overoptimization risk.

DPO removes the explicit reward-model training loop and optimizes the policy directly from preference pairs. This is simpler operationally and often attractive for smaller teams, but it is still only as good as the preference data, reference-policy assumptions, task coverage, and regression gates. It also does not automatically benefit from fresh online rollouts.

Agent Studio implication: DPO should be treated as a simpler alignment route, not a harmless one. It still needs data provenance, pair quality checks, behavior-drift evals, rollback, and blocked-tradeoff gates.

## Reward Reliability

The lecture's strongest production warning is that learned rewards are fragile. Human preferences can be noisy, reward models can amplify that noise, and optimizing hard against a proxy can produce behavior that scores well while violating the real objective.

For Agent Studio, this means feedback and reward data must keep:

- prompt/task context;
- route and model version;
- candidate artifacts;
- evaluator identity or judge model;
- rubric and preference reason;
- source/retrieval evidence when the task is grounded;
- length/style/safety labels;
- known blind spots for the reward or verifier.

The system should never collapse all preference evidence into one reward number. Different reward types must remain separate until release review.

## Verifiable Rewards

The lecture distinguishes broad human preference from verifiable domains such as math, code, science, tests, and other tasks with checkable outcomes. Verifiable rewards are valuable because they reduce subjective preference noise, but they can still be incomplete. A unit test can miss source grounding; a JSON validator can miss factuality; a citation-existence check can miss relevance.

Agent Studio should therefore split:

- `verifier_reward`: a checkable condition tied to a specific verifier version;
- `preference_reward`: human or model preference over candidate outputs;
- `grounding_reward`: source support and citation validity;
- `style_reward`: voice, formatting, platform fit, or editorial preference;
- `safety_reward`: policy compliance, refusal quality, sensitive-data handling, and tool-risk behavior.

Verifiable rewards can approve narrow slices. They cannot replace human review for broad editorial judgment, safety tradeoffs, or source-backed synthesis unless those goals have been decomposed into reviewed eval cases.

## Behavioral Drift

Preference optimization can alter surface behavior in ways that look like quality but are not the same as truth or usefulness. More detail, cleaner lists, greater politeness, or stronger confidence can be useful for social-media drafts and product documents, but those shifts can also hide weak evidence or increase unsupported claims.

Agent Studio should track:

- length distribution before and after alignment;
- confidence and hedging behavior;
- refusal and abstention behavior;
- citation density and citation relevance;
- source diversity;
- user-facing style and formatting changes;
- over-helpfulness or sycophancy in critique/reviewer routes.

These are release-blocking dimensions when the route produces source-backed, educational, legal/medical/financial, or publishing-ready artifacts.

## Datastore Requirements

Add or strengthen:

| Object | Purpose |
|---|---|
| `preference_optimization_method` | Records whether a route uses SFT, RLHF, DPO, IPO-style preference classification, RLVR, prompt repair, reranker tuning, or no alignment optimization. |
| `preference_data_quality_check` | Checks pair balance, prompt/task coverage, evaluator distribution, order bias, style/length confounds, source-evidence availability, and duplicate leakage. |
| `reward_overoptimization_check` | Tracks whether reward improvement is accompanied by grounding, safety, source diversity, style, latency, or cost regressions. |
| `behavior_style_shift_metric` | Captures post-training shifts in length, listiness, confidence, politeness, abstention, citation density, and sycophancy risk. |
| `verifiable_task_record` | Defines tasks where a verifier can score outputs and records what the verifier does not prove. |
| `reference_policy_record` | Records the baseline/reference model or route used for KL-style or DPO-style comparison assumptions. |
| `preference_alignment_release_gate` | Promotion gate proving an alignment-derived route change has method selection, baseline/reference policy, preference-pair provenance, reward-type separation, verifier scope, behavior-drift checks, reward-overoptimization checks, fixed eval slices, blocked tradeoffs, rollback, and human review. |

## Release Gate Contract

Agent Studio should promote RLHF, DPO, verifier-driven post-training, reranker tuning, or prompt-policy preference optimization only when a preference-alignment release gate proves:

- baseline route, candidate route, reference policy, and rejected lighter interventions;
- method choice, including whether the change uses SFT, RLHF, DPO, IPO-style classification, RLVR, prompt repair, reranker tuning, or no model tuning;
- preference dataset provenance, rights status, evaluator or judge identity, task coverage, pair balance, order-bias check, style/length confound check, duplicate/leakage check, and source-evidence coverage;
- reward-type separation across preference, grounding, style, safety, operational, verifier, and verifiable-task rewards;
- verifier scope, version, calibration evidence, and explicit statement of what the verifier does not prove;
- behavior/style shift metrics for length, confidence, politeness, abstention, citation density, formatting, refusal behavior, and sycophancy risk;
- reward-overoptimization checks proving reward gains did not hide grounding, safety, source diversity, latency, cost, or human-review regressions;
- fixed eval slices for source-backed, high-risk, long-tail, publishing, and tool/action cases;
- rollback route, incident feedback path, and human approval for any release-blocking tradeoff.

Do not promote the gate when raw thumbs-up, engagement, or judge scores are treated as alignment data without task labels; when DPO is used as a "cheap RLHF" shortcut without reference-policy and pair-quality evidence; when verifiable rewards are allowed to stand in for broad editorial quality; or when source-backed routes optimize style while losing grounding or citation relevance.

## Canon Decision

Agent Studio should treat RLHF, DPO, and verifier-driven post-training as route changes governed by source provenance, preference-pair quality, reward type separation, behavior-drift evals, and rollback. DPO can reduce implementation complexity, but it does not remove the need for a `preference_alignment_release_gate`.
