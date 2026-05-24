---
type: lecture-note
project: agent-studio-system-design
status: canon_ready
source_title: "Stanford CS25 Transformers United V6"
lecture_title: "Advancing Science and Medicine with Collaborative AI Agents"
speaker: "Vivek Natarajan, Google DeepMind"
source_status: official_public
updated: 2026-05-18
sources:
  - https://web.stanford.edu/class/cs25/
  - https://research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist/
  - https://arxiv.org/abs/2502.18864
  - https://deepmind.google/blog/ai-co-clinician/
  - https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/
related:
  - "[[cs25-generalist-agents-open-ended-worlds]]"
  - "[[../../03-patterns/agent-systems/agent-route-architecture-canon]]"
  - "[[../../03-patterns/evaluation/eval-design-canon]]"
  - "[[../../03-patterns/security/genai-security-canon]]"
---

# CS25 - Collaborative AI Agents For Science And Medicine

## Reading Status

Canon-ready direct read of the official Stanford CS25 V6 lecture listing for the May 14 talk, plus official Google Research and Google DeepMind materials for AI co-scientist, AI co-clinician, and agent-system scaling, rechecked on 2026-05-18. This note does not claim video-level coverage unless a recording is later watched directly, and it stores no transcript text, article body, or long excerpts.

## Why This Matters

The CS25 talk description is a useful bridge between general multi-agent architecture and high-stakes collaborative systems. The relevant Agent Studio lesson is not medicine itself. It is the product architecture pattern: agents become useful when they coordinate around a hard workflow, expose evidence, use domain-specific evaluators, and keep humans in the loop for decisions that require judgment.

Agent Studio should borrow the architecture pattern, not the clinical claims.

## Core Pattern

The AI co-scientist materials describe a multi-agent system for scientific hypothesis generation. The important system shape is:

- a user-specified research goal;
- a supervisor that turns the goal into a work plan;
- specialized workers for generation, reflection, ranking, evolution, proximity, and meta-review;
- iterative improvement through automated feedback;
- tool use and search for grounding;
- expert-in-the-loop feedback and experimental validation.

Agent Studio implication: multi-agent workflows should be routed by task structure. A research or content route can use specialist roles only when each role owns a distinct check, transformation, search surface, or evaluation signal. Specialist names alone do not justify extra agents.

## Hypothesis And Artifact Generation

AI co-scientist is useful to Agent Studio because it treats outputs as hypotheses that must be proposed, compared, refined, and validated. A generated script, storyboard, architecture decision, carousel outline, or publishing strategy should be treated the same way: as a candidate artifact with evidence and tests, not a final answer.

Agent Studio implication:

- store candidate artifacts separately from approved artifacts;
- keep accepted and rejected candidates for future evals;
- require ranking or critique traces when multiple candidates are generated;
- attach source IDs and claim IDs to generated claims;
- separate ideation routes from publication routes.

## Debate, Ranking, And Evolution

The co-scientist design uses debate/ranking/evolution-style loops to improve hypotheses. The transferable design rule is that iterative agent loops need explicit stopping conditions and measurable value. Google Research's agent-scaling work adds the warning: multi-agent coordination helps when work can be parallelized, but can degrade sequential tasks through communication overhead and error propagation.

Agent Studio implication:

- use independent or parallel specialist agents for decomposable research, candidate generation, and source discovery;
- use centralized orchestration when synthesis, policy, or publication risk matters;
- avoid decentralized debate for linear editing or deterministic transformations unless evals show value;
- bound debate/evolution loops by cost, latency, quality gain, and reviewer fatigue;
- record why a multi-agent topology was chosen over a single-agent route.

## Safety-Critical Collaboration

AI co-clinician is explicitly framed as research and not as a deployed replacement for clinical judgment. Its architecture is still useful as a safety pattern: a conversation agent can be paired with a planner/checker module that monitors boundaries, evidence, and task completion. The system also emphasizes scenario-tailored evaluation and citation/evidence checks.

Agent Studio implication:

- for high-risk routes, split "talker/generator" behavior from "planner/checker" behavior;
- require route-specific rubrics rather than generic helpfulness scores;
- attach evidence verification to source-backed claims;
- keep human review as a product state, not an afterthought;
- make domain restrictions visible in the route release.

## Design Implications For Agent Studio

Add these requirements to agent route design:

| Requirement | Reason |
|---|---|
| `task_decomposition_evidence` | Proves the task benefits from multiple workers or loops. |
| `candidate_pool` | Preserves generated alternatives, rejected options, and ranking evidence. |
| `critique_loop` | Records which agent or evaluator improved the artifact and why. |
| `domain_safety_boundary` | Declares what the route may not decide, publish, or claim. |
| `human_expert_gate` | Captures who must approve high-stakes or public decisions. |
| `loop_stop_policy` | Prevents unbounded debate, ranking, or self-improvement loops. |
| `collaborative_agent_topology_release_gate` | Promotion gate proving that a multi-agent topology is task-fit, measurable, error-contained, domain-bounded, and human-governed before it replaces a simpler route. |

The operating principle: collaborative agents are a governed workflow topology. They are not a substitute for source quality, evaluation design, or human authority.

## Release Gate Contract

`collaborative_agent_topology_release_gate` is required before Agent Studio promotes a multi-agent, debate, critique, ranking, evolution, meta-review, planner/checker, or expert-collaboration topology for research, content, scientific, medical, or other high-stakes routes.

The gate rejects promotion unless the release record binds:

- task decomposition evidence showing whether the task is parallelizable, sequential, tool-heavy, safety-critical, or expertise-heavy;
- selected topology and rejected alternatives: single-agent, independent parallel agents, centralized orchestrator, decentralized debate, hybrid coordination, generator-checker, or human-review workflow;
- measurable topology rationale: expected value, communication overhead, tool-coordination cost, latency/cost budget, reviewer-fatigue budget, and error-propagation risk;
- role contracts for generator, reflection, ranking, evolution, proximity/search, meta-review, planner, checker, and human expert where used;
- candidate pool policy preserving generated alternatives, rejected candidates, ranking signals, critique traces, source evidence, and final selection rationale;
- loop stop policy with iteration, cost, quality-gain, confidence, safety, and human-escalation limits;
- domain safety boundary defining what the route may not diagnose, recommend, publish, claim, or execute;
- evidence verification and scenario-specific eval rubrics for source-backed claims, tool outputs, safety-critical claims, and publication-ready artifacts;
- human expert gate, approval state, fallback simpler route, rollback target, and incident feedback path.

## Open Follow-Up

- Add video-level notes only if the official CS25 recording or official transcript is available and directly watched/read.
- Cross-check the pattern against additional official agent-orchestration docs before promoting this source slice to canon.
