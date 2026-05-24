---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - https://research.google/pubs/model-cards-for-model-reporting/
  - https://arxiv.org/abs/1803.09010
  - https://www.nist.gov/itl/ai-risk-management-framework
  - https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10
  - https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf
---

# Model, Dataset, And Route Card Governance

## Source Boundary

This note synthesizes official/open governance sources: Google Research's Model Cards publication page, the open Datasheets for Datasets paper record, and NIST's AI RMF plus Generative AI Profile. It turns model cards, dataset/source datasheets, route cards, and risk records into Agent Studio datastore requirements. It stores no raw paper text or long excerpts.

Current-source check on 2026-05-18: Google Research still presents model cards as transparent model reporting for intended use, evaluation conditions, subgroup and intersectional performance, limitations, and context. The Datasheets for Datasets arXiv record remains the open source for dataset documentation covering motivation, composition, collection, recommended uses, and accountability. NIST's AI RMF page still frames AI risk management as voluntary, trustworthiness-oriented practice across design, development, use, and evaluation, with the GenAI Profile adding generative-AI risks around provenance, supplier/value-chain controls, pre-deployment testing, human-AI configuration, incident disclosure, and monitoring. NIST also now lists an April 7, 2026 concept note for a critical-infrastructure AI RMF profile; Agent Studio should treat that as future follow-up context, not as a current route requirement unless a route targets critical infrastructure.

## Core Design Lessons

Documentation is release evidence, not a launch afterthought. Model Cards argues that model releases should carry intended-use context, evaluation procedures, performance across relevant conditions, and limitations. Datasheets for Datasets applies the same discipline to datasets: motivation, composition, collection, recommended use, and other lifecycle facts should travel with the data. NIST AI RMF turns this into an operating loop: govern, map, measure, and manage risk across design, deployment, monitoring, and incident response.

Agent Studio should generalize these ideas from models and datasets to routes. A route is a product-facing system: prompt, model, retrieval index, tools, memory, evals, guardrails, UI surface, and publishing side effects. A route card should explain what the route is for, what it must not be used for, which sources and tools it depends on, what evidence supports release, which slices are weak, and which fallback or rollback path exists.

Aggregate metrics are not enough. Model Cards emphasizes evaluation under conditions relevant to intended use. For Agent Studio, that means cards must record slices such as platform, audience, language, source family, freshness requirement, media type, tool side-effect class, privacy class, and high-impact workflow. A route with high average score but poor citation validity on legal, medical, financial, or private-source tasks should not be promoted.

Datasheets make source reuse safer. A source snapshot, eval dataset, retrieval corpus, or feedback-derived dataset should carry purpose, collection path, rights/provenance, composition, transformations, excluded material, known bias, stale regions, and recommended/non-recommended uses. This prevents a corpus built for explanation examples from silently becoming tuning data, production retrieval evidence, or benchmark truth.

NIST's GenAI Profile adds product risk surfaces that cards should explicitly track: governance, pre-deployment testing, content provenance, incident disclosure, third-party dependencies, human-AI configuration, data provenance, monitoring, secure development, stakeholder engagement, synthetic-content labeling, and acceptable-use policy. These are not independent checklists; they become release gates and monitoring requirements for each route.

## Agent Studio Implications

Every production route should have four linked card families:

- source or dataset datasheet: what the source/data is, where it came from, what changed during extraction/filtering, and where it may be used;
- model/provider card: what model/runtime is being used, intended use, limitations, training/data disclosures where available, license or access terms, and safety notes;
- route card: how prompt, model, retrieval, tools, memory, evals, guardrails, and UI surface combine into one product behavior;
- risk card or risk register entry: the route's misuse, privacy, security, quality, provenance, and operational risks with controls and review cadence.

Cards should be generated from durable records where possible, then reviewed as human-readable notes. The Markdown card is a projection; the datastore records are the source of truth. This keeps cards from drifting away from route release state, eval outcomes, incident reports, and source snapshots.

Route cards should block production promotion when required evidence is missing:

- no source datasheet for a retrieval corpus;
- no model/provider card for a generator or analyzer;
- no slice evaluation for the route's target use;
- no content provenance policy for generated media or publishing;
- no human approval policy for side effects;
- no risk owner or review cadence for high-impact routes;
- no incident feedback loop from failures back to eval cases and release gates.

## Datastore Requirements

Agent Studio needs governance-card records for:

- source datasheet: motivation, owner, composition, acquisition path, rights status, transformations, excluded material, known gaps, freshness, recommended uses, prohibited uses, and review status;
- model/provider card: model/provider identity, version, license/access terms, intended use, limitations, evaluation slices, safety notes, dataset disclosure, data-boundary caveats, allowed product surfaces, and review status;
- route card: route objective, prompt/model/retrieval/tool/memory/eval dependencies, supported and unsupported uses, release state, slice metrics, fallbacks, rollback plan, and governance state;
- risk register entry: risk family, affected routes, likelihood, impact, controls, measurement signal, owner, review cadence, and status;
- card review event: reviewer, evidence checked, missing evidence, approved limitations, expiry or review date, and release decision;
- incident feedback link: incident or near miss, affected card, resulting eval case, route-change proposal, and mitigation state.

## Card Projection Release Gate

`card_projection_release_gate` is the promotion gate for any production source snapshot, model/provider dependency, route, generated-media lane, publishing lane, or high-impact eval suite that needs a human-readable card. The gate proves the Markdown card is a current projection from durable records rather than a stale narrative artifact.

Required evidence:

- `gate_id`, `subject_ref`, `subject_type`, `release_ref`, `source_datasheet_refs`, `model_provider_card_refs`, `route_card_refs`, `risk_register_refs`, and `card_artifact_refs`;
- `intended_use_refs`, `unsupported_use_refs`, `stakeholder_requirement_refs`, `affected_population_or_audience_refs`, and `high_impact_surface_refs`;
- `source_provenance_refs`, `rights_policy_refs`, `dataset_composition_refs`, `transform_refs`, `excluded_material_refs`, `known_gap_refs`, and `freshness_policy_refs`;
- `model_or_provider_version_refs`, `training_or_data_disclosure_refs`, `license_or_access_refs`, `data_boundary_refs`, and `allowed_product_surface_refs`;
- `eval_slice_refs`, `subgroup_or_intersectional_slice_refs`, `metric_refs`, `calibration_refs`, `known_limitation_refs`, and `approved_limitation_refs`;
- `content_provenance_policy_refs`, `human_approval_policy_refs`, `security_privacy_control_refs`, `supplier_or_third_party_refs`, `monitoring_refs`, `incident_feedback_refs`, `review_cadence`, `reviewer_refs`, `decision`, and `reviewed_at`.

Do not promote a card-backed subject when:

- a Markdown card exists but the durable source/model/route/eval/risk records are missing or stale;
- intended use and unsupported use are vague enough that route misuse cannot be evaluated;
- aggregate metrics are present but relevant slice, subgroup, audience, language, media, privacy, or side-effect surfaces are untested;
- a source or dataset is reused outside the recommended use documented in its datasheet;
- provider/model cards omit license, access, data-boundary, version, or allowed-surface review;
- incidents, near misses, user reports, or monitoring findings do not feed back into eval cases and card updates;
- a high-impact or critical-infrastructure route lacks an explicit NIST-style risk owner, measurement signal, review cadence, fallback, and escalation path.

## Operating Rule

A route, dataset, source snapshot, model provider, generated-media lane, or publishing lane is not production-ready merely because its implementation works. It needs a current card projection backed by durable evidence, slice-specific eval results, provenance state, risk ownership, and a review decision.
