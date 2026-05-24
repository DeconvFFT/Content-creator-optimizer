---
type: book-chapter-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-19
source:
  local_path: /Users/saumyamehta/DS interview prep/books/Artificial Intelligence. A modern approach (Stuart Russell  Peter Norvig).pdf
  title: "Artificial Intelligence: A Modern Approach"
  authors: "Stuart Russell, Peter Norvig"
chapter:
  number: 11
  title: "Automated Planning"
extraction:
  method: pdftotext
  physical_pages: "344-379"
  pdf_pages: "357-392"
  temp_extract: "/private/tmp/aima_ch11_automated_planning.txt"
stores_raw_source_text: false
related:
  - "[[../agent-planning-foundations]]"
  - "[[./4-search-in-complex-environments]]"
  - "[[./6-constraint-satisfaction-problems]]"
  - "[[../../../03-patterns/agent-systems/agent-route-architecture-canon]]"
  - "[[../../../03-patterns/system-design/production-agent-studio-canon]]"
  - "[[../../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# Chapter 11 - Automated Planning

## Reading Scope

This is a direct-read chapter synthesis from the local user-provided Artificial Intelligence: A Modern Approach PDF. It covers Chapter 11 only: classical planning, PDDL-style factored state/action representation, action schemas, preconditions, add/delete effects, planning domains and problems, forward/progression search, backward/regression search, SAT/CSP/partial-order planning, planning heuristics, subgoal independence and relaxed problems, hierarchical task network planning, high-level actions, refinements, abstract planning with angelic semantics, sensorless/conformant planning, contingent planning, online planning and execution monitoring, temporal/resource scheduling, and planning-approach selection.

This note stores compact original synthesis and Agent Studio implications only. It does not store copied chapter text, algorithms, figures, tables, or long excerpts.

## Why This Chapter Matters

Agent Studio needs planning that is stricter than "ask an LLM for steps." A route plan changes source state, artifacts, memory, evaluator state, browser state, schedules, and publish readiness. If actions do not have explicit preconditions and effects, the system cannot know what is safe to run, what became stale, what needs repair, or why a route failed.

The product rule: every nontrivial autonomous route should represent actions as typed planning schemas before execution, then monitor whether the expected effects actually happened.

## Planning Domain Contract

Classical planning separates a domain from a problem. The domain defines action schemas; the problem provides initial state and goal. For Agent Studio, that becomes a reusable route grammar plus a run-specific state.

Agent Studio implications:

- store a `planning_domain_record` for each reusable route family: source ingestion, RAG answer, social post generation, reel production, eval run, publishing packet, or route repair;
- store `planning_problem_record` for each concrete run, with initial facts, goal facts, forbidden facts, and risk class;
- action schemas should include preconditions, add effects, delete effects, side-effect class, required permissions, and rollback behavior;
- closed-world assumptions must be explicit because missing evidence should not silently mean false when sources, files, or approvals might simply be unobserved.

## Progression, Regression, And Encoded Planning

Forward planning searches from the current state through applicable actions. Backward planning regresses from the goal through actions that could achieve it. SAT/CSP-style planning encodes bounded plan existence as a constraint or satisfiability problem.

Agent Studio implications:

- use progression for live tool execution where the next action depends on observed state;
- use regression when designing a release checklist from a required publish or approval goal;
- use bounded encoded planning for deterministic workflow validation, dependency ordering, and "is there any valid plan under these constraints?" checks;
- preserve the planning mode in route traces so reviewers know whether a plan was generated from current observations, goal regression, or a bounded solver.

## Planning Heuristics And Relaxations

Planning heuristics often come from relaxed versions of the problem, such as ignoring delete effects or assuming subgoal independence. These are useful for prioritizing search but dangerous if treated as final proof.

Agent Studio implications:

- record which constraints or negative effects a heuristic relaxed;
- do not let a relaxed plan approve publication, source mutation, or external side effects without final constraint/effect checks;
- use relaxed planning graphs for ranking candidate route plans, then validate the selected plan against real permissions, stale approvals, source rights, and resource conflicts;
- route-quality metrics should track missed negative interactions, not only plan length or apparent progress.

## Hierarchical Planning

Hierarchical task networks let high-level actions decompose into refinements until primitive actions are reached. This is a direct fit for Agent Studio: a campaign plan decomposes into source research, outline, draft, critique, visual plan, generation, QA, distribution, and publishing.

Agent Studio implications:

- store `high_level_action_record` for reusable route steps such as "produce source-backed post" or "refresh retrieval index";
- store `refinement_method_record` for each allowed decomposition, with preconditions, expected outputs, owner, and known failure modes;
- keep the plan hierarchy visible to reviewers so they can inspect both the abstract intent and the primitive tool calls;
- learned successful plans may become reusable methods only after generalization, eval, rights review, and rollback policy.

## Abstract Plans And Angelic Semantics

The chapter distinguishes hostile/nondeterministic outcomes from agent-chosen refinements. A high-level action can be useful because the agent chooses one implementation that works. Approximate descriptions can be optimistic or pessimistic: an abstract plan may definitely fail, definitely work, or require refinement.

Agent Studio implications:

- abstract route plans need `abstract_plan_reachability_record` with works, fails, or needs-refinement status;
- optimistic abstract plans can prioritize work but should not authorize side effects;
- pessimistic proof is stronger: if all remaining uncertainty still satisfies the goal, the route can proceed with less refinement;
- reviewers should see when a route is committing to a high-level plan versus still searching for an implementation.

## Sensorless, Contingent, And Online Planning

Planning changes when the world is partially observed or actions are nondeterministic. Sensorless planning searches over belief states without observations; contingent planning branches on future perceptions; online planning monitors execution and repairs the plan when the environment differs from the model.

Agent Studio implications:

- source availability, browser state, extraction quality, reviewer availability, and platform API behavior are often partially observable;
- route plans should contain contingent branches for predictable observation outcomes, such as extraction failed, source inaccessible, citation unsupported, reviewer rejects, or platform media container not ready;
- online routes need execution monitoring, effect checks, stale-plan detection, repair insertion, and escalation triggers;
- repeated unexpected outcomes should update the environment model instead of being treated as harmless randomness.

## Time, Schedules, And Resources

The chapter extends planning into scheduling with action durations, ordering constraints, reusable resources, consumable resources, and resource conflicts. Agent Studio has the same problem: agents, reviewers, provider quotas, GPU jobs, video/media generation, publish windows, and rate limits are limited resources.

Agent Studio implications:

- store `temporal_plan_record` for route action order, duration estimates, earliest/latest start windows, and critical path;
- store `resource_pool_record` for reviewer capacity, model/provider quota, GPU capacity, browser/computer-use surface, publishing account, and budget;
- planning and scheduling should be integrated when resource conflicts change which plan is easiest or safest;
- use minimum-slack-style priority for urgent constrained tasks, but validate against global quality and risk constraints.

## Portfolio Planning

No single planning method dominates. Some domains fit forward search, some goal regression, some SAT/CSP encodings, some HTN libraries, some online repair, and some portfolio selection.

Agent Studio implications:

- route planners should store why a planning method was selected and which alternatives were rejected;
- route families should carry empirical fit evidence: success rate, repair rate, plan length, latency, cost, reviewer burden, and side-effect failures;
- high-risk routes should keep a fallback planner or manual plan path rather than trusting one planning method.

## Datastore Objects Promoted By This Chapter

| Object | Role |
|---|---|
| `planning_domain_record` | Reusable action-schema family for a route class, including state vocabulary and supported action schemas. |
| `planning_problem_record` | Concrete run-specific planning problem with initial state, goal, forbidden states, risk class, and domain ref. |
| `planning_state_fact_record` | Factored state fluent with truth status, observation source, confidence, and stale-after policy. |
| `planning_action_schema` | Action name, parameters, preconditions, add/delete effects, side-effect class, failure modes, and rollback policy. |
| `planning_mode_decision` | Chosen planner mode: progression, regression, SAT/CSP encoding, partial-order, HTN, online repair, or portfolio. |
| `planning_heuristic_record` | Heuristic source, relaxed constraints/effects, admissibility caveat, known negative-interaction risks, and eval refs. |
| `high_level_action_record` | Abstract route action with refinement options, preconditions, expected effects, owner, and review status. |
| `refinement_method_record` | Allowed decomposition of a high-level action into lower-level actions or methods. |
| `abstract_plan_reachability_record` | Works/fails/needs-refinement status from optimistic, pessimistic, or exact abstract-plan analysis. |
| `contingent_plan_branch_record` | Branch selected by a future observation, with trigger, action sequence, fallback, and risk. |
| `execution_monitoring_record` | Expected effect, observed effect, deviation, model-error hypothesis, repair action, and escalation decision. |
| `temporal_plan_record` | Action durations, ordering constraints, earliest/latest start, critical path, and schedule status. |
| `resource_pool_record` | Reusable or consumable resource capacity, owner, constraints, current commitments, and refresh policy. |
| `schedule_repair_record` | Repair to ordering, timing, or resource allocation after a constraint/resource conflict or execution deviation. |
| `planning_release_gate` | Promotion gate proving action schemas, planner mode, heuristic caveats, hierarchy/refinement, contingent branches, resource schedule, monitoring, fallback, and rollback. |

## Agent Studio Design Implications

- Treat route plans as state/action/effect systems, not prose outlines.
- Use preconditions and effects to invalidate stale approvals, evals, source assumptions, and dependent artifacts.
- Select planning mode by route shape: live action, release checklist, bounded feasibility, reusable HTN method, online repair, or resource schedule.
- Keep relaxed-plan heuristics separate from final approval.
- Make high-level plans reviewable without hiding primitive tool calls.
- Add execution monitoring for every plan that mutates files, indexes, route configs, memory, publishing state, or external systems.
- Integrate planning and scheduling when scarce reviewers, quotas, GPU jobs, or publishing windows can change the best plan.
- Promote planning behavior only after a `planning_release_gate` proves schemas, refinements, contingent branches, resource handling, monitoring, fallback, rollback, and human authority.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-generalist-agents-open-ended-worlds]] - Stanford CS25, "Generalist Agents in Open-Ended Worlds" ([YouTube](https://www.youtube.com/watch?v=wwQ1LQA3RCU)).
- [[../../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
