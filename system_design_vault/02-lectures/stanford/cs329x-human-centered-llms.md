---
type: lecture-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_class: official_course_source_note
rights_status: official_open_course_page
sources:
  - https://web.stanford.edu/class/cs329x/
  - https://arxiv.org/abs/2412.15701
  - https://openreview.net/forum?id=hjDYJUn9l1
  - https://arxiv.org/abs/2409.00138
  - https://arxiv.org/abs/2508.10880
---

# Stanford CS329X Human-Centered LLMs

## Direct-Read Scope

Direct-read pass over the official Stanford CS329X Fall 2025 course page and selected official/open readings surfaced by that page for human-agent collaboration, human-language-model interaction evaluation, privacy norms in LLM agents, and simulated privacy-risk search. Current-source check on 2026-05-18 verified the live Stanford course page and open reading records.

This is not a video-ingestion note. The course page marks several guest lectures, slides, and readings, but this pass does not claim public video watching or transcript-level coverage.

## Course Signals

CS329X frames human-centered LLM systems as a design and deployment problem, not just an alignment method. The official course scope includes human-centered design, preference learning, personalization, UI/HCI integration, privacy and risk measurement, creativity, and future-of-work applications.

The schedule creates a useful Agent Studio coverage map:

- preference learning and pluralistic alignment should inform route objectives and reviewer disagreement handling;
- human-AI interaction and interaction evaluation should inform collaboration metrics, not just final artifact metrics;
- design thinking and participatory AI should inform product controls, onboarding, and review workflows;
- generative UI should inform adaptive cockpit surfaces, but only with state, audit, and user-control boundaries;
- privacy, anthropomorphism, companion behavior, and future-of-work topics should become release gates for agentic and social-facing routes.

## Human-Agent Collaboration

Collaborative Gym's core lesson is that collaborative agents are not just autonomous agents with a chat box. They operate in a shared task environment where humans, agents, and the environment each have state and actions. Evaluation must score both outcome quality and collaboration process quality.

Agent Studio implication: content-studio routes should distinguish:

- autonomous background work;
- user-steered collaboration;
- human review after the fact;
- human approval before side effects;
- shared-workspace co-editing where the user can intervene while the agent acts.

Those are different route classes with different telemetry and evals.

## Interaction Evaluation

HALIE-style human-language-model interaction evaluation adds a missing layer to normal LLM evals. For interactive systems, a single final output is too narrow. The product should measure the interaction loop: user intent clarity, agent initiative, repair behavior, suggestion usefulness, user effort, trust calibration, and whether the system preserves user agency.

Agent Studio implication: a reel/script/source-note route can pass final-answer grading while still failing interaction quality. If the user had to repeatedly restate intent, undo over-eager edits, or inspect hidden state manually, the route should produce a collaboration-regression signal.

## Privacy Norms And Agent Simulation

PrivacyLens and simulated privacy-risk search both matter because Agent Studio agents operate in social, source, and publishing contexts. Privacy failures often appear in action, not in static question answering: sending an email, drafting a post, quoting a local source, transferring context to another agent, or answering after a multi-turn persuasion attempt.

The privacy-risk-search framing is especially relevant for agent systems because attacks can evolve over multiple turns. Direct requests are only the easy case; impersonation, consent forgery, role pressure, and persistent probing require trajectory-level evals and identity/consent state machines.

Agent Studio implication: privacy evals should inspect full traces and role state, not just the final response. Sensitive information can leak through intermediate tool arguments, retrieval snippets, draft artifacts, annotations, screenshots, or handoff packets.

## Product Design Implications

- Treat user agency as a route-level objective. A route should declare whether it suggests, drafts, edits, publishes, delegates, or autonomously acts.
- Preserve intervention points. The user should be able to pause, steer, approve, reject, or roll back meaningful route actions.
- Model reviewer disagreement. Pluralistic and preference-sensitive work needs multiple reviewer perspectives, not a single hidden "human preference" scalar.
- Personalization needs a boundary. Store user preferences as scoped, reviewable memory with evidence, expiry, and undo.
- Avoid anthropomorphic overreach. The product should not imply companionship, certainty, authority, or social obligation where the route is a task tool.
- Evaluate collaboration process. Route success should include user effort, repair count, interruption count, handoff clarity, and final artifact quality.
- Red-team privacy through simulated trajectories. Static policy prompts are not enough for agents that can receive multi-turn social pressure.

## Datastore Additions

- `human_agent_collaboration_session`: route, user, agent, shared workspace, task environment, intervention policy, autonomy mode, and terminal outcome.
- `collaboration_process_metric`: session ref, user effort, repair count, interruption count, initiative balance, clarification quality, satisfaction signal, and reviewer caveat.
- `user_agency_control`: route action, available controls, pause/steer/approve/reject/rollback support, visibility level, and tested status.
- `preference_perspective_record`: reviewer/user group, value dimension, preference source, disagreement signal, aggregation policy, and protected caveats.
- `personalization_boundary_record`: memory item or preference, scope, evidence, consent basis, expiry, edit/delete affordance, and route eligibility.
- `privacy_norm_eval_case`: contextual norm, involved roles, sensitive attribute, allowed information flow, forbidden information flow, and expected behavior.
- `privacy_attack_simulation_run`: attacker role, defender role, data subject, trajectory refs, discovered tactic, defense policy, leakage outcome, and mitigation.
- `anthropomorphism_risk_record`: route surface, social cues, user population, dependency risk, misleading-affordance risk, mitigation, and review status.
- `human_centered_route_release_gate`: release gate for collaborative, personalized, privacy-sensitive, social-facing, or high-agency routes.

## Release Gate Contract

`human_centered_route_release_gate` is required before a route can collaborate with a user in a shared workspace, personalize from memory, expose social/companion-like cues, or take privacy-relevant actions with user or third-party information.

The gate should reject promotion unless:

- autonomy mode is explicit: autonomous background work, user-steered collaboration, reviewer-gated output, approval-gated side effect, or shared-workspace co-editing;
- user agency controls have been tested for pause, steer, approve, reject, rollback, and visible state inspection;
- collaboration metrics include user effort, repair count, interruption count, initiative balance, clarification quality, handoff clarity, and final artifact quality;
- pluralistic or preference-sensitive decisions preserve reviewer perspectives and disagreement signals instead of flattening them into one hidden preference score;
- personalization has scope, evidence, consent basis, expiry, edit/delete affordance, and route eligibility;
- privacy evals inspect full trajectories, role state, tool arguments, retrieval snippets, draft artifacts, handoff packets, and screenshots where applicable;
- simulated privacy attacks include impersonation, consent forgery, role pressure, persistent probing, and cross-agent context transfer;
- anthropomorphism review blocks misleading companionship, authority, certainty, emotional obligation, or dependency cues outside the route's task role;
- fallback and rollback paths are named before the route can publish, persist memory, transfer context, or call external tools.

## Open Caveats

The official page is a course map, not a full transcript or textbook. Treat this note as a canon-ready design synthesis from the public course page plus selected open readings, not as a complete lecture-by-lecture video digest.
