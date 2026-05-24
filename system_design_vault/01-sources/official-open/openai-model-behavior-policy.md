---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
rights_status: official_public
provenance_status: official_openai_policy_and_safety_docs_direct_read
sources:
  - https://model-spec.openai.com/
  - https://model-spec.openai.com/2025-10-27.html
  - https://openai.com/index/our-approach-to-the-model-spec/
  - https://openai.com/policies/usage-policies/
  - https://developers.openai.com/api/docs/guides/safety-best-practices
  - https://developers.openai.com/api/docs/guides/safety-checks
  - https://openai.com/index/updating-our-preparedness-framework/
---

# OpenAI Model Behavior Policy

## Scope

Direct-read synthesis from official OpenAI Model Spec, Model Spec process, Usage Policies, API safety guidance, safety-check guidance, and Preparedness Framework sources. This note captures policy and model-behavior implications for Agent Studio. It stores no copied policy text, examples, code blocks, or long excerpts.

## Core Pattern

Model behavior is a versioned policy surface, not just prompt wording. OpenAI's Model Spec defines intended model behavior through an authority hierarchy, behavioral objectives, non-overridable safety boundaries, defaults, risky-situation handling, side-effect control, truthfulness, and untrusted-data treatment. Usage Policies define what people and applications may not use the service for. API safety docs turn those policy boundaries into product operations through red-teaming, moderation or equivalent filters, human review, user reporting, safety identifiers, and abuse-response paths.

Agent Studio should therefore separate three concerns:

- `model_behavior_policy`: what the assistant is expected to do when instructions conflict, the user asks for risky help, or the route has autonomy.
- `use_policy`: whether the route, source, user action, or generated artifact is allowed for the service and destination.
- `safety_operations`: how the product detects, blocks, reviews, escalates, and learns from risky behavior.

Without this split, a route can pass normal quality evals while still violating an instruction hierarchy, overstepping autonomy, mishandling untrusted content, automating a high-stakes decision, exposing private data, or lacking a user-reporting and abuse-response loop.

## Model Spec Implications

The Model Spec adds concrete route requirements beyond generic guardrails:

- authority hierarchy must be explicit: system, developer, user, tool output, retrieved text, browser content, uploaded files, captions, and generated media metadata do not have the same authority;
- untrusted content should remain evidence, not instruction, unless a higher-authority instruction explicitly delegates authority to it;
- autonomous routes need an agreed scope of autonomy, reversible action preference, communication of side effects, and approval before high-impact or irreversible actions;
- risky domains need safe completion behavior that remains helpful within boundaries rather than silently maximizing refusal rate;
- truthfulness, uncertainty, objectivity, and anti-sycophancy are behavior targets that need eval cases, not vague personality preferences;
- policy updates can move faster than model behavior, so a route record needs policy-version evidence and regression tests for behavior drift.

For Agent Studio, the model-behavior layer should be visible in route cards, eval datasets, reviewer UI, and incident reviews. A prompt diff that changes authority, refusal behavior, user autonomy, or external side effects is a policy change even when the model/provider stays the same.

## Usage Policy Implications

Usage Policies add an application-level boundary. Agent Studio should block or escalate routes involving:

- concrete harm, harassment, violence, self-harm promotion, weapons, illicit activity, abusive cyber activity, or evasion of safeguards;
- privacy-invasive collection, profiling, biometric/likeness misuse, sensitive-attribute inference, or unauthorized distribution of private information;
- minor-safety risk;
- deception, impersonation, scams, spam, political manipulation, or academic dishonesty;
- high-stakes automated decisions in areas such as employment, housing, finance, insurance, legal, medical, government services, national security, law enforcement, migration, critical infrastructure, education, and product safety without appropriate human review.

Agent Studio routes that draft public posts, publish media, advise creators, process local books, summarize private material, use browser/computer control, or call external APIs need this policy layer before execution, not only after a provider returns an error.

## Safety Operations

OpenAI safety docs convert policy into operations:

- adversarial and prompt-injection testing before launch;
- moderation or route-specific filters where unsafe content is plausible;
- human review for high-stakes, code-generation, publishing, source-critical, and externally mutating paths;
- constrained inputs and bounded output where the task allows it;
- stable privacy-preserving safety identifiers for broad user-facing model access;
- a human-monitored issue-reporting channel;
- user or organization-level abuse responses that include delay, block, warning, or access restriction.

Agent Studio should treat provider safety checks as an external control and still maintain its own route-local controls. A provider block is not a substitute for route-level input policy, tool permissions, approval UX, source-rights review, and incident-to-eval backfill.

## Preparedness Implications

The Preparedness Framework is aimed at frontier-capability risk, but it gives Agent Studio a useful release-governance pattern: define tracked risk categories, define capability thresholds, evaluate before release, review safeguards, reassess with new evidence, and publish or record enough decision evidence for accountability.

Agent Studio can apply that pattern at product scale without claiming frontier-model evaluation:

- route categories with severe-harm potential get stricter evaluation and review;
- new autonomy, tool, retrieval, publishing, or code-execution capability triggers a capability-risk review;
- safeguards are reviewed as a package, not as isolated filters;
- incidents and newly observed misuse update eval cases before similar routes are promoted again.

## Datastore Objects

- `model_behavior_policy_record`: policy source, version/date, route scope, authority levels, behavioral objectives, non-overridable boundaries, defaults, and owner.
- `instruction_authority_record`: per-context classification of system/developer/user/tool/retrieved/uploaded/browser/generated content authority and delegation rules.
- `untrusted_content_boundary`: rule set and trace evidence proving untrusted source text, webpages, tool output, comments, captions, and file content are treated as data.
- `safe_completion_policy`: route-specific behavior for restricted or risky requests, including allowed high-level help, refusal style, escalation, and fallback.
- `policy_eval_case`: test case with policy area, authority conflict, risky-domain class, expected behavior, trace assertions, and release-blocking severity.
- `usage_policy_review`: allowed/disallowed service-use decision for a route, source, user action, artifact, destination, or external side effect.
- `high_stakes_human_review_gate`: review requirement for regulated, sensitive, public-publishing, code, or externally mutating outputs before execution.
- `frontier_capability_risk_review`: product-scale risk review for new autonomy, tool, publishing, code-execution, retrieval, or model capability surfaces.
- `model_behavior_policy_release_gate`: release gate joining policy version, authority map, usage-policy review, safe-completion policy, safety operations, eval coverage, incident feedback, fallback, rollback, and human approval.

## Release Gates

Do not promote a route when:

- no current model-behavior policy version is attached;
- system/developer/user/tool/retrieved/uploaded/browser content authority is ambiguous;
- untrusted content can override instructions or tool permissions;
- risky-domain behavior lacks safe-completion/refusal evals;
- use-policy review is absent for public publishing, private-data processing, local source ingestion, regulated advice, identity-sensitive media, or external API mutation;
- high-stakes decisions or code/publishing outputs can bypass human review;
- safety identifiers, abuse reports, moderation/filtering, and incident-to-eval backfill are missing where broad user access exists;
- provider policy drift or Model Spec updates cannot be traced to route-change proposals.

## Agent Studio Decision

Treat model behavior as a governed release surface. Every public, externally mutating, private-data, retrieval-heavy, or autonomous route should record which model-behavior policy version it follows, how instruction authority is resolved, what usage-policy classes it permits or blocks, how it safely completes or refuses risky requests, what eval cases prove the behavior, and what human review or incident-feedback loop keeps the route aligned after release.
