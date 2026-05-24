---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_status: official_public
stores_raw_source_text: false
stores_long_excerpts: false
sources:
  - https://www.uber.com/us/en/blog/first-pass-prd/
related:
  - "[[uber-ml-platform-agentic-governance]]"
  - "[[../../03-patterns/agent-systems/agent-route-architecture-canon]]"
  - "[[../../03-patterns/evaluation/eval-design-canon]]"
  - "[[../../04-agent-studio-implications/Route Change Proposal Template]]"
---

# Uber PRD Reviewer Agent

## Reading Scope

Direct-read pass over Uber Engineering's May 12, 2026 post on building a first-pass AI PRD reviewer, with a current-source check on May 18, 2026. The public article still identifies the evaluator as an upstream PRD review tool that assembles linked and adjacent context, calibrates review depth, evaluates readiness across dimensions, produces prioritized scorecards, and preserves human approval authority. This note stores compact original synthesis only. It does not copy screenshots, scorecards, tables, or long excerpts.

## Core Pattern

The PRD Evaluator is not positioned as an approval authority. It sits upstream of a high-cost human checkpoint and improves the artifact entering review. That distinction matters for Agent Studio: reviewer agents should make human review sharper, earlier, and more consistent, not silently replace expert approval.

The durable workflow is:

1. start from a draft artifact;
2. assemble relevant context from linked docs, prior experiments, cross-functional material, and preloaded local/domain principles;
3. classify the proposal so review depth matches risk;
4. evaluate launch readiness across structured dimensions;
5. produce a scorecard with the highest-priority fixes, evidence, and suggested rewrite/action items;
6. leave final judgment with humans.

## Agent Studio Implications

Agent Studio should use first-pass reviewer agents for route proposals, source-ingestion plans, content drafts, publishing packets, PRDs/ERDs, and release candidates. The agent's job is to expand the author's field of view, detect missing evidence, and convert critique into usable revision work.

Useful reviewer dimensions for Agent Studio:

- objective and hypothesis clarity;
- source/context sufficiency;
- product scope and release-readiness;
- user/audience impact and edge cases;
- metric, guardrail, and validation rigor;
- adjacent system dependencies;
- policy, rights, security, and governance sensitivity;
- prior experiment or similar-work retrieval;
- critical fixes versus optimizations.

## Design Lessons

Frameworks beat generic critique. A reviewer route should use explicit decision criteria and failure modes instead of open-ended "give feedback" prompting.

Context matters as much as wording. A polished artifact can still miss dependencies, prior experiments, unsupported assumptions, or policy-sensitive effects. The reviewer needs retrieval over linked and adjacent artifacts, not only the draft text.

Hard boundaries make output more honest. A reviewer should be able to say "not ready" when fundamentals are missing. It should not average away critical gaps with positive prose quality.

Prioritization is product behavior. A review route that flags everything equally creates noise. It should identify the first fix, critical requirements, and lower-priority improvements separately.

The best output improves human conversations. The measurable win is not a prettier scorecard; it is fewer avoidable review-room discoveries, sharper tradeoff discussion, and better human decision-making.

## Failure Modes

- Rewarding polished writing while missing unsupported assumptions or absent guardrails.
- Reviewing only the submitted artifact without retrieving adjacent docs, prior experiments, policies, and dependencies.
- Producing a long critique without an ordered action plan.
- Treating the reviewer score as approval instead of pre-review triage.
- Using one review depth for all proposals, including high-risk policy, pricing, marketplace, or publishing changes.
- Hiding evidence for findings, making the author unable to trust or act on the critique.

## Datastore Requirements

Add or strengthen:

| Object | Purpose |
|---|---|
| `review_artifact_record` | Draft PRD, route proposal, content packet, or release candidate submitted for first-pass review. |
| `context_assembly_record` | Linked and discovered documents, prior experiments, policies, metrics, and adjacent artifacts used by the reviewer. |
| `proposal_risk_classification` | Review-depth decision such as light, moderate, full, or specialized scrutiny. |
| `readiness_scorecard` | Structured launch/release readiness result with dimensions, evidence, priority, and decision status. |
| `critical_gap_record` | Blocking gap with missing evidence, affected dimension, suggested fix, and owner. |
| `revision_action_item` | Ordered repair task split into critical requirement or optimization. |
| `review_conversation_outcome` | Post-review evidence that tracks whether the AI first pass improved or distorted the later human review. |
| `first_pass_review_release_gate` | Promotion gate proving a reviewer route has the artifact, context bundle, risk class, scorecard dimensions, critical gaps, prioritized actions, evidence refs, human-authority boundary, and post-review outcome policy needed before it can influence release or canon decisions. |

## Release Gate Contract

Agent Studio should treat the first-pass reviewer as a pre-approval gate for production and canon-impacting artifacts. The gate is satisfied only when the reviewer route proves:

- the submitted artifact type and target review forum are explicit;
- linked and discovered context, prior experiments, policies, metric definitions, and adjacent dependencies were assembled within the author's access boundary;
- review depth is calibrated by risk, including specialized scrutiny for policy, pricing, marketplace, publishing, safety, rights, privacy, or external-side-effect changes;
- readiness dimensions are fixed before scoring, not invented after seeing the output;
- every critical gap names missing evidence, impact, owner, and a suggested repair;
- the first fix is separated from lower-priority optimizations;
- findings cite evidence refs rather than vague model judgment;
- the reviewer output cannot approve, publish, merge, or promote by itself;
- later human review records issues prevented, issues missed, reviewer override, and route-improvement follow-up.

Do not promote the gate when the route only proofreads prose, searches the submitted artifact without adjacent context, hides evidence for findings, collapses blocking gaps into an average score, or lets a scorecard substitute for accountable human approval.

## Canon Decision

Agent Studio reviewer agents should be pre-approval quality gates. They should retrieve context, classify risk, evaluate against explicit dimensions, produce prioritized evidence-backed repairs, and preserve final authority for human reviewers or governed release gates. Canon-impacting route proposals, ingestion plans, publishing packets, and release candidates should not treat a reviewer score as approval; they should require a `first_pass_review_release_gate` that records evidence, gaps, repair actions, override policy, and post-review outcomes.
