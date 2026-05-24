---
type: official-course-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
course: "Stanford CS329S Machine Learning Systems Design"
source_status: official_public
stores_raw_source_text: false
stores_long_excerpts: false
sources:
  - https://stanford-cs329s.github.io/index.html
  - https://stanford-cs329s.github.io/syllabus.html
  - https://stanford-cs329s.github.io/slides/cs329s_12_slides_sara_google.pdf
  - https://docs.google.com/presentation/d/1cshMKKSX24L0RL7LNzyOkZNQHD7N-Zyff8iffrLIVYM/export/txt
related:
  - "[[cs329s-ml-systems-design]]"
  - "[[cs329s-ml-infrastructure-platform]]"
  - "[[../../03-patterns/security/genai-security-canon]]"
  - "[[../../03-patterns/evaluation/eval-design-canon]]"
---

# CS329S Governance Fairness And Business

## Reading Scope

Direct-read pass over the official CS329S course overview and syllabus, plus the public Lecture 12 material for Sara Hooker's "ML beyond accuracy: Fairness, Security, Governance." Current-source check on 2026-05-18 verified the live course page, syllabus, and Lecture 12 public material pointers. The syllabus also lists the final "Integrating ML into business" guest lecture, but no public slide or note artifact was available from the official syllabus link at this pass, so this note only uses the syllabus signal for business-scope coverage and does not claim direct-read coverage of those guest talks.

This note stores compact original synthesis only. It does not store raw slide text, transcript dumps, full tables, or long excerpts.

## Core Read

CS329S frames ML systems design as stakeholder-driven engineering: different objectives create different system choices, and production systems must include human-side concerns such as team structure, business metrics, privacy, fairness, and security. Lecture 12 sharpens this into a governance rule: top-line accuracy is not a sufficient release objective because models can satisfy a narrow objective while violating the intended behavior of the product.

For Agent Studio, every route needs a success contract that names the product objective, the user or stakeholder affected, the business/user cost of errors, and the non-accuracy properties that matter. "Good answer quality" is too vague for a release gate; the route needs measurable behavior across source support, safety, privacy, cost, latency, fairness slices, and human-review burden.

## Beyond Top-Line Accuracy

The lecture's main systems lesson is under-specification. Average loss or benchmark accuracy can hide shortcut learning, privacy leakage, brittleness, and subgroup failures. This matters for Agent Studio because content routes can appear healthy while failing on less common topics, creators, languages, platforms, source types, or risk classes.

Agent Studio implication: source-backed routes should not ship with only aggregate eval scores. They need slice metrics for topic family, platform, audience, source freshness, source rights class, language, user intent, artifact type, and high-risk claim class. For generated media or voice routes, the same principle applies to modality, accent/language, visual attributes, and device/runtime class.

## Fairness And Label Reality

The lecture distinguishes known, comprehensive sensitive labels from incomplete or unknown bias settings. Known labels support direct intersectional auditing and targeted remedies. Incomplete labels require a different posture: use model signals, difficult-example mining, proxy-feature review, annotator disagreement, and human inspection to find where the system may be failing. The deeper governance point is that bias can come from both data and model/design choices, not from the dataset alone.

Agent Studio implication: the datastore should allow fairness and coverage checks even when ideal labels do not exist. It should record known slices, suspected proxy slices, missing-label caveats, annotator disagreement, and model-signal triage queues. For content generation, this maps to underrepresented source domains, long-tail creator niches, low-resource languages, ambiguous policy labels, and rare but important failure cases.

## Model And System Design Tradeoffs

The lecture treats compactness, interpretability, robustness, fairness, privacy, and security as interacting objectives rather than independent improvements. Compression, pruning, differential privacy, early stopping, and training stochasticity can change behavior unevenly across underrepresented examples. The operational lesson is not that these methods are bad; it is that route changes must be evaluated on the slices most likely to absorb the cost.

Agent Studio implication: optimization work such as smaller models, quantization, caching, reranking shortcuts, cheaper providers, and fast-path routing needs regression evidence on long-tail and high-risk slices. A cheaper route that preserves average quality but loses support for rare sources, niche audiences, or sensitive content classes is a product regression.

## Business Integration Signal

The syllabus places "Integrating ML into business" after infrastructure and final-project discussion. That placement is useful: business integration is not a marketing wrapper after model work. It is part of system design because value, go-to-market, stakeholder incentives, operational cost, and review capacity determine which model/system tradeoffs are acceptable.

Agent Studio implication: route proposals should include stakeholder, value metric, cost-of-error, reviewer-capacity, and rollout assumptions. A workflow that is technically impressive but requires unsustainable manual review, burns too much provider budget, or cannot be explained to the intended operator is not production-ready.

## Failure Modes To Guard Against

- Treating benchmark or eval-set averages as a release decision without slice analysis.
- Assuming fairness, privacy, robustness, interpretability, and latency improve independently.
- Calling a route fair because no protected label was available to measure unfairness.
- Moving to a smaller, faster, cheaper, or more private route without checking long-tail regressions.
- Treating governance as a policy document instead of route metadata, release gates, and incident feedback.
- Letting business metrics drive unsafe automation without explicit human-review and rollback policies.

## Datastore Requirements

Add or strengthen:

| Object | Purpose |
|---|---|
| `stakeholder_requirement_record` | Links route behavior to affected users, operators, business owners, reviewers, and policy constraints. |
| `governance_release_gate` | Release checklist for non-accuracy objectives: source support, safety, privacy, fairness, robustness, cost, latency, and human review. |
| `fairness_slice_eval` | Slice-level eval record for known, proxy, missing-label, and intersectional coverage risks. |
| `label_caveat_record` | Captures missing sensitive labels, proxy-feature risk, annotation disagreement, and legal/consent constraints. |
| `model_design_tradeoff_record` | Records expected and measured effects of compression, quantization, routing, privacy, robustness, and cost optimizations. |
| `business_value_metric` | Business or user-value metric tied to route objective, cost-of-error, reviewer capacity, and rollout decision. |

## Release Gate Contract

`governance_release_gate` is required before a route can increase autonomy, publish externally, alter model/provider/routing behavior, change source filtering, or become a canon-backed architecture decision.

The gate should reject promotion unless:

- stakeholder requirements name affected users, operators, reviewers, business owners, and policy constraints;
- success metrics include non-accuracy dimensions: source support, safety, privacy, fairness or coverage, robustness, cost, latency, and human-review burden;
- evals report slice results for topic family, platform, audience, source freshness, source rights class, language, artifact type, user intent, and high-risk claim class where relevant;
- missing-label and proxy-label caveats are explicit instead of treating unmeasured fairness as passed fairness;
- annotator disagreement and reviewer-capacity assumptions are recorded when labels or review decisions affect release;
- model/system tradeoffs show expected gain, affected slices, measured regressions, privacy/security notes, and rollback policy;
- business value metrics include cost-of-error, rollout decision, and sustainable reviewer capacity rather than only aggregate engagement or throughput;
- any approved tradeoff has an owner, review date, incident feedback path, and rollback target.

## Canon Decision

Agent Studio should treat governance as part of route design, not as after-the-fact review. Every production route needs stakeholder requirements, non-accuracy release gates, slice-level evidence, label caveats, model/system tradeoff records, and business-value metrics before optimization or autonomy increases.
