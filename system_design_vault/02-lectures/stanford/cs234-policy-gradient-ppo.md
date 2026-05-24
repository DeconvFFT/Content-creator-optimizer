---
type: lecture-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_status: official_public
stores_raw_source_text: false
stores_long_excerpts: false
sources:
  - https://web.stanford.edu/class/cs234/modules.html
  - https://web.stanford.edu/class/cs234/slides/lecture6pre.pdf
related:
  - "[[cs224r-preference-optimization-rlhf-dpo]]"
  - "[[cs336-data-and-alignment]]"
  - "[[../../03-patterns/alignment/preference-alignment-systems-canon]]"
  - "[[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# CS234 - Policy Gradient And PPO Route Mechanics

## Reading Scope

Direct-read pass over official Stanford CS234 Winter 2026 Lecture 6, "Policy Gradient II," downloaded from the public Stanford course materials page to `/private/tmp` for local text extraction. This note stores compact original synthesis only. It does not store raw slide text, copied derivations, videos, or transcripts.

## Why This Matters

Agent Studio already has alignment notes for RLHF, DPO, verifiable rewards, and preference data. CS234 adds the algorithm-control layer underneath PPO-style optimization: policy-gradient variance, baseline/value estimates, advantage estimates, policy-space drift, KL control, clipped objectives, and sample-efficiency limits.

The product lesson is conservative. If Agent Studio ever optimizes a model, adapter, reranker, policy route, or agent behavior with PPO-style methods, the route ledger must preserve optimization mechanics, not only before/after eval scores.

## Baselines And Advantage Estimates

The lecture shows why policy-gradient methods use baselines: the baseline can reduce estimator variance without changing the expected gradient. In practice, the value estimate becomes the baseline, and the update is driven by an advantage estimate rather than raw return alone.

Agent Studio implication:

- alignment runs should store the baseline/value estimator used to compute advantages;
- reward gains are not interpretable without advantage-estimation and baseline-version context;
- high-variance feedback should not be treated as stable route-quality evidence;
- reviewer preference data, verifier rewards, and production feedback should remain separate until the route can show how they become advantages or training targets.

## On-Policy Data And Sample Efficiency

Vanilla policy gradient is sample-inefficient because data collected under the current policy is normally discarded after one update. Reusing old trajectories is attractive but creates stability questions because the data no longer exactly matches the current policy.

Agent Studio implication:

- optimization runs need `trajectory_batch_record` entries with policy version, rollout source, reward source, and reuse count;
- stale rollout reuse should be explicit, especially when the behavior being optimized affects source grounding, safety, or tool use;
- every run should record how many gradient/update steps were taken per collected batch;
- offline preference or production-feedback reuse needs a route-change gate, not silent training.

## Policy-Space Drift

The lecture emphasizes that small parameter changes are not necessarily small policy changes. For route governance, this is the key reason PPO-style methods include KL or clipping controls: the system needs to prevent behavior from moving too far from the reference policy in one update.

Agent Studio implication:

- an alignment route should track policy distance in behavior space, not just parameter diff or adapter version;
- KL/reference-policy records should be release evidence for PPO/RLHF-style changes;
- policy-distance checks should include task slices where source grounding, citation behavior, refusal behavior, tool-use conservatism, and verbosity can drift.

## PPO Control Surfaces

The lecture covers two PPO families:

- adaptive KL penalty, where a KL penalty coefficient is adjusted against a target divergence;
- clipped objective, where the update pessimistically limits gains from probability-ratio changes outside a small band.

Agent Studio implication:

- PPO-style optimization needs a `ppo_control_policy` record: target KL or clip range, penalty adaptation policy, batch/update settings, advantage estimator, and stop criteria;
- clipped-objective runs should still store observed KL and behavior-drift metrics; clipping is a control mechanism, not proof that route behavior stayed safe;
- adaptive KL runs should record target divergence, observed divergence, coefficient changes, and violations;
- source-backed routes should gate PPO-style behavior changes on grounding, citation, safety, latency, and cost regressions, not only reward improvement.

## Datastore Additions

| Object | Job | Minimum fields |
|---|---|---|
| `trajectory_batch_record` | Rollout or interaction batch used for policy optimization | `batch_id`, `route_id`, `policy_version`, `source`, `trajectory_refs`, `reward_signal_refs`, `advantage_estimator_ref`, `reuse_count`, `collection_time`, `rights_status` |
| `advantage_estimator_record` | Baseline/value setup for policy-gradient updates | `estimator_id`, `route_id`, `value_model_ref`, `baseline_policy`, `return_definition`, `normalization_policy`, `fit_data_ref`, `variance_diagnostic_refs`, `created_at` |
| `policy_distance_record` | Behavior-space drift evidence between reference and candidate policies | `distance_id`, `route_id`, `reference_policy_ref`, `candidate_policy_ref`, `metric`, `slice_refs`, `value`, `threshold`, `decision` |
| `ppo_control_policy` | PPO-specific update control surface | `ppo_policy_id`, `route_id`, `variant`, `target_kl`, `clip_range`, `penalty_coefficient_policy`, `minibatch_steps`, `optimizer_ref`, `stop_policy`, `status` |
| `ppo_update_record` | One PPO-style update event | `update_id`, `alignment_run_id`, `trajectory_batch_ref`, `advantage_estimator_ref`, `ppo_control_policy_ref`, `observed_kl`, `clip_fraction`, `reward_delta`, `regression_refs`, `decision` |

## Release Gate Contract

A PPO/RLHF-style route should not be promoted unless the release proves:

- reference policy identity and candidate policy identity;
- trajectory batch provenance, rights, collection policy, and reuse count;
- advantage estimator and baseline/value model version;
- PPO control policy: KL target or clip range, penalty adaptation, optimizer/update steps, and stop rule;
- observed KL, clip fraction or equivalent update-control diagnostics;
- reward improvement separated from grounding, safety, style, latency, and cost regressions;
- fixed eval slices for source-backed answers, tool behavior, refusals, verbosity, citation density, and reviewer burden;
- rollback route and incident-feedback path.

## Agent Studio Design Implications

- Treat PPO as an optimization subsystem, not a generic alignment label.
- Store rollouts, advantages, policy-distance checks, and update-control diagnostics as first-class route evidence.
- Prefer DPO or prompt/reranker repair for narrow behavior edits unless the route has enough rollout infrastructure and eval coverage to justify PPO-style optimization.
- Keep current CS336 Spring 2026 Lecture 16/17 on watch; CS234 fills general policy-gradient/PPO mechanics, not current CS336 alignment-systems coverage.
