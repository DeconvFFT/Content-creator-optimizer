---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_status: official_google_public_security_sources
sources:
  - https://research.google/pubs/an-introduction-to-googles-approach-for-secure-ai-agents/
  - https://docs.cloud.google.com/model-armor/overview
  - https://blog.google/innovation-and-ai/technology/safety-security/introducing-googles-secure-ai-framework/
  - https://blog.google/innovation-and-ai/technology/safety-security/ai-security-frontier-strategy-tools/
  - https://cloud.google.com/solutions/apigee-ai
---

# Google Secure AI Agents And Model Armor

## Reading Scope

This note covers Google's public secure-agent framework, Google Cloud Model Armor overview, Secure AI Framework / SAIF 2.0 announcements, and Apigee AI gateway guidance. It is original synthesis only; it stores no raw paper text, product-page text, code, diagrams, or copied checklists.

## Core Thesis

Google's secure-agent framing is a useful systems rule for Agent Studio: an agent is safe only when its controller is defined, its powers are limited, and its planning and actions are observable. Model behavior alone is not a security boundary.

For Agent Studio, that means every privileged route needs a control plane outside the prompt:

- a human or organization controller;
- a bounded permission set;
- policy-enforced tool and API gateways;
- runtime scanning for prompts, responses, documents, and agent interactions;
- traceable plans, actions, approvals, and failures;
- feedback and vulnerability-report loops that update evals and controls.

## Current-Source Cross-Check

The current Google Research secure-agent page still states the three core principles this note depends on: well-defined human controllers, carefully limited powers, and observable planning/actions. The current Model Armor overview still supports prompt and response inspection, sensitive-data protection, prompt-injection and jailbreak detection, malicious URL checks, input/output template separation, inspect-only versus inspect-and-block enforcement, production threshold tuning, false-positive monitoring, and user feedback for blocked content.

The current SAIF material still frames AI security as secure foundations, AI-specific detection/response, automated defenses, consistent controls, continuous testing, and reporting loops. Google's 2025 AI-security update explicitly extends SAIF 2.0 to agent security, keeps the same controller/power/observability principles, and adds vulnerability reward/reporting paths with route metadata such as user context and model version. The Apigee AI gateway source still supports the gateway pattern for placing policy, quota, routing, sanitization, abuse detection, and observability outside the prompt.

## Human Controller Requirement

Agent Studio should attach every autonomous or semi-autonomous route to a responsible controller. The controller can be a user, workspace owner, reviewer role, or product governance owner, but it should not be implicit.

This matters for publishing, source ingestion, browser/computer use, private corpus access, account actions, and paid provider calls. A route without a controller cannot make defensible decisions about consent, budget, access, review, or rollback.

## Limited Powers Requirement

Google's "carefully limited powers" principle maps directly to route-scoped authorization:

- tools should expose narrow actions, not broad credentials;
- API access should pass through policy enforcement where feasible;
- side-effect tools need approvals, idempotency, rate limits, and rollback plans;
- retrieval access should be filtered before context assembly;
- generated code or model output should not become an executable authority;
- provider/model usage should be constrained by budget and quota policy.

Prompt policy is not enough. If a route can see credentials or call broad APIs, a prompt-injection failure becomes a system compromise.

## Observable Planning And Actions

Observability should include the plan/action boundary, not only the final answer. Agent Studio traces should show:

- which controller owned the run;
- which tools were available and which were selected;
- what permission scope authorized the call;
- what safety scan ran before or after the call;
- whether a human approval edge was required;
- what artifact or external effect was produced;
- which policy/eval case would catch the same failure later.

For privacy, store hashes, refs, labels, and compact explanations rather than raw private source text or raw prompts.

## Model Armor Runtime Boundary

Model Armor provides a concrete runtime-security pattern: prompts and responses can be screened for responsible-AI categories, prompt injection/jailbreak attempts, sensitive data, malicious URLs, and document-borne risks. It can operate across clouds/models and has explicit data-handling and logging implications.

Agent Studio implication: safety scanning should be a route-stage object with mode, filters, thresholds, language setting, document eligibility, skipped/blocked/sanitized result, and logging/retention policy. A route should not merely say "guardrails enabled"; it should record what was scanned, what was not scanned, and what happened when a filter skipped due to size, language, configuration, or regional constraint.

## AI Gateway Boundary

Apigee's AI-gateway framing is useful even if Agent Studio does not deploy Apigee. It separates model/API access from application prompts by adding gateway controls:

- authentication and authorization;
- API-key/OAuth/JWT validation;
- rate limits and quotas;
- prompt/response sanitization policy enforcement;
- abuse and anomaly detection;
- circuit breaking and graceful failure;
- model abstraction, routing, semantic cache, and token/cost visibility.

Agent Studio should mirror this as an internal provider/tool gateway. Provider calls, MCP tools, A2A tasks, publishing APIs, browser/computer tools, and retrieval services should pass through a policy surface that can enforce identity, quota, safety scan, logging, and revocation.

## SAIF Lifecycle Lesson

SAIF adds the organizational layer: AI security needs secure foundations, threat intelligence, automated defenses, consistent controls, continuous testing, and incident/user-feedback loops. Agent Studio should turn this into a maintenance loop:

1. map route risks and authority;
2. enforce deterministic controls before model reasoning;
3. observe actions and security outcomes;
4. accept vulnerability/user reports with enough route metadata to diagnose;
5. convert incidents and near misses into eval cases, policy changes, and route-release blockers.

## Agent Studio Datastore Implications

Add or strengthen these records:

- `agent_controller_record`: user/workspace/organization controller, delegated reviewer role, allowed autonomy, budget owner, and escalation path.
- `agent_authority_scope`: allowed tools, API surfaces, retrieval scopes, spending caps, external side effects, approval needs, and expiry.
- `ai_gateway_policy`: provider/tool/API gateway with auth method, quota, rate limit, safety scan policy, cache policy, circuit breaker, and logging policy.
- `safety_scan_policy`: filter categories, thresholds, languages, document types, input/output stages, skipped-result behavior, and retention/logging mode.
- `safety_scan_result`: route/run/span ref, content ref/hash, filter outcomes, blocked/sanitized/skipped state, reason, and follow-up policy.
- `agent_action_observation`: proposed action, authorized scope, safety scan refs, human approval ref, execution result, side-effect refs, and rollback status.
- `security_report_record`: user/researcher/operator report with affected route, model/provider version, trace refs, severity, triage owner, and linked regression evals.
- `policy_enforcement_point`: gateway, guardrail, tool wrapper, MCP server, A2A boundary, retrieval filter, or UI approval edge that enforces route policy outside the model prompt.
- `agent_security_release_gate`: route release, controller ref, authority scope, policy enforcement points, safety scan policy/results, action-observation coverage, approval edges, report channel, incident/eval backfill, and rollback condition.

## Design Commitments

- Never treat system prompts as the authority boundary for privileged routes.
- Attach every agentic route to a controller, authority scope, and observable action trail.
- Put provider/tool/API access behind gateway-style policy enforcement.
- Record safety scan coverage and skip reasons, not only pass/fail outcomes.
- Use runtime scanners as defense-in-depth, not as replacements for least privilege or human approval.
- Convert security reports, incidents, and reviewer overrides into eval cases and release blockers.
- Treat this note as canon-ready for Agent Studio privileged-agent routes because it has been cross-checked against the current Google secure-agent, Model Armor, SAIF/SAIF 2.0, and Apigee AI gateway sources.
