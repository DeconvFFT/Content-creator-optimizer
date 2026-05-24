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
  number: 6
  title: "Constraint Satisfaction Problems"
extraction:
  method: pdftotext
  physical_pages: "180-203"
  pdf_pages: "191-216"
  temp_extract: "/private/tmp/aima_ch6_constraint_satisfaction.txt"
stores_raw_source_text: false
related:
  - "[[../agent-planning-foundations]]"
  - "[[./4-search-in-complex-environments]]"
  - "[[./5-adversarial-search-and-games]]"
  - "[[../../../03-patterns/agent-systems/agent-route-architecture-canon]]"
  - "[[../../../03-patterns/system-design/production-agent-studio-canon]]"
  - "[[../../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]"
---

# Chapter 6 - Constraint Satisfaction Problems

## Reading Scope

This is a direct-read chapter synthesis from the local user-provided Artificial Intelligence: A Modern Approach PDF. It covers Chapter 6 only: CSP definitions, variables, domains, constraints, constraint graphs, job-shop scheduling, higher-order and global constraints, constraint propagation, node/arc/path/k-consistency, Sudoku as a propagation example, backtracking search, variable and value ordering, forward checking, maintaining arc consistency, conflict-directed backjumping, constraint learning, local search with min-conflicts, graph-structure decomposition, cutset conditioning, tree decomposition, tree width, and value symmetry.

This note stores compact original synthesis and Agent Studio implications only. It does not store copied chapter text, algorithms, figures, tables, or long excerpts.

## Why This Chapter Matters

Agent Studio will fail operationally if constraints live only inside prompts. Production routes need machine-checkable limits: source rights, tool permissions, model capability, latency budget, platform policy, reviewer availability, dependency order, publish windows, artifact formats, account permissions, and cross-agent resource contention.

The product rule: if a route can be invalidated by an assignment of agents, tools, sources, deadlines, permissions, or artifacts, model it as a constraint satisfaction problem before execution.

## CSP Contract

A CSP separates variables, domains, and constraints. The useful architecture lesson is that the route state is not one opaque blob; it is a structured assignment problem where invalid combinations can be pruned before the agent spends tokens or mutates artifacts.

Agent Studio implications:

- represent route-planning surfaces with a `constraint_problem_record`, not only a prose checklist;
- store variables such as selected source, model, tool, reviewer, asset type, destination platform, deadline, budget, and approval state;
- distinguish variable domains from preferences. A model can be eligible or ineligible before it is scored as better or worse;
- make constraints typed and testable so schedulers, route controllers, and release gates can reject impossible plans without asking an LLM to reason from scratch.

## Constraint Graphs And Dependency Shape

The chapter's constraint graph gives a compact way to see where variables interact. For Agent Studio, this is the difference between independent subtasks that can run in parallel and tightly coupled subtasks that need coordinated assignment.

Agent Studio implications:

- maintain a `constraint_graph_record` for each nontrivial route plan;
- use graph structure to identify independent content branches, disconnected source groups, and subplans that can be scheduled separately;
- treat dense constraint clusters as risk zones because a local change can invalidate many downstream assignments;
- record higher-order constraints directly when a rule involves more than two variables instead of exploding everything into unreadable pairwise checks.

## Constraint Propagation

Constraint propagation removes impossible domain values before or during search. Node consistency removes values invalid for a single variable, arc consistency removes values unsupported by neighboring variables, and stronger consistency checks catch failures that pairwise checks may miss.

Agent Studio implications:

- run constraint propagation before route launch and again after material state changes such as new source access, failed extraction, reviewer rejection, or platform-policy update;
- store `constraint_propagation_event` records that show which domain values were removed and which constraint caused removal;
- use `arc_consistency_record` for pairwise constraints such as source-platform compatibility, tool-permission compatibility, model-capability compatibility, and reviewer-skill compatibility;
- promote global constraints for all-different reviewer assignment, total budget, total latency, account-level rate limits, and publish-calendar capacity.

## Backtracking Search And Ordering

Backtracking search assigns one variable at a time and retreats when no legal assignment remains. The chapter's variable and value heuristics are product design tools: choose the most constrained variable first, break ties with high-degree variables, and prefer values that leave future options open.

Agent Studio implications:

- schedulers should assign scarce or highly constrained resources first: rights-sensitive sources, specialized reviewers, limited tool slots, platform-specific formats, and deadlines;
- use a `constraint_solver_policy` to declare variable ordering, value ordering, inference level, backtracking behavior, and timeout policy;
- least-constraining-value ordering should prefer route choices that preserve fallback models, fallback reviewers, fallback sources, and fallback publish windows;
- backtracking traces should be stored for release-critical failures so the system can explain why no valid route exists.

## Search Plus Inference

The chapter shows that inference can be interleaved with search. Forward checking catches immediate future failures after an assignment; maintaining arc consistency continues propagation more aggressively after each assignment.

Agent Studio implications:

- every accepted assignment in a route plan should trigger a lightweight feasibility refresh on affected variables;
- a scheduler that picks a model should immediately prune tools, latency classes, evaluator types, and output formats that no longer fit;
- high-risk or dense plans should use stronger propagation than simple forward checking because local feasibility can hide downstream impossibility;
- release gates should distinguish "currently no violated constraint" from "the remaining plan is still globally feasible."

## Conflict Sets, Backjumping, And Constraint Learning

Naive backtracking may retreat one step at a time even when the real cause of failure is earlier. Conflict-directed backjumping records which assignments caused failure, and constraint learning stores a no-good pattern so the search does not repeat the same contradiction.

Agent Studio implications:

- failed route plans need `constraint_conflict_set_record` entries that identify the responsible assignments, not just a generic "planner failed";
- store `constraint_no_good_record` when a combination is known invalid, such as a source rights class plus platform plus asset type;
- use learned no-goods to prevent repeated agent loops that rediscover the same impossible plan with different wording;
- expose unsatisfied constraints and conflict sets to humans so a user can change the right variable instead of guessing.

## Local Search And Repair

Local search starts with a complete assignment and repairs conflicts by changing values. This matters for long-running Agent Studio work because production routes often need repair, not a full rebuild: one reviewer is unavailable, one source fails extraction, one output format is rejected, or one platform slot moves.

Agent Studio implications:

- use `constraint_repair_record` for online schedule and route repair after a small state change;
- prefer minimal-change repairs when a route is already partially executed and artifacts have accumulated review context;
- use min-conflicts-style scoring to pick the assignment change that removes the most violations while preserving approved work;
- keep repair policies separate from initial planning policies because the optimization target changes once work is in flight.

## Structure, Decomposition, And Symmetry

Problem structure determines tractability. Tree-structured CSPs are easy; nearly tree-structured problems can be solved through cutset conditioning; tree decomposition trades memory for time; value symmetry can waste search on equivalent assignments.

Agent Studio implications:

- decompose route constraint graphs into independent or tree-like subproblems before launching a large multi-agent run;
- use `constraint_decomposition_record` to explain which variables were grouped, removed, or conditioned on;
- monitor tree width or a simpler coupling proxy so operators can spot route plans likely to explode in search cost;
- add symmetry-breaking constraints when interchangeable agents, reviewers, formats, or asset slots create duplicate equivalent plans.

## Datastore Objects Promoted By This Chapter

| Object | Role |
|---|---|
| `constraint_problem_record` | Declares route variables, domains, constraints, objective/preference boundary, and solver status. |
| `constraint_variable_record` | One assignable route variable such as model, source, tool, reviewer, deadline, platform, artifact type, or budget bucket. |
| `constraint_domain_record` | Allowed values for a variable with eligibility evidence, removed values, and removal reasons. |
| `constraint_relation_record` | Typed unary, binary, higher-order, or global constraint with enforcement policy and violation severity. |
| `constraint_graph_record` | Graph or hypergraph of variables and constraints used for scheduling, decomposition, and risk inspection. |
| `partial_assignment_record` | Current planner assignment with assigned variables, remaining domains, unresolved constraints, and feasibility status. |
| `constraint_propagation_event` | Domain-pruning event caused by node, arc, path, k-consistency, global constraint, or forward-checking inference. |
| `arc_consistency_record` | Pairwise support check between two variables, removed values, and remaining compatible value pairs. |
| `constraint_conflict_set_record` | Assignments responsible for a detected failure or empty domain. |
| `constraint_no_good_record` | Learned invalid assignment combination that should be pruned in future search. |
| `constraint_solver_policy` | Variable-ordering, value-ordering, inference, backtracking, learning, local-search, and timeout policy. |
| `constraint_search_trace` | Backtracking, propagation, backjumping, learned no-good, or local-search trajectory for a route-planning run. |
| `constraint_repair_record` | Minimal-change repair after source, reviewer, tool, schedule, policy, or artifact state changes. |
| `constraint_decomposition_record` | Cutset, tree-decomposition, independent-subproblem, or symmetry-breaking decision with cost tradeoffs. |
| `constraint_release_gate` | Promotion gate proving that route constraints are explicit, propagated, conflict-explainable, repairable, and reviewed. |

## Agent Studio Design Implications

- Do not encode hard constraints only in prompts; store them as typed records that the scheduler and release gates can check.
- Separate hard feasibility constraints from ranking preferences and creative taste.
- Run propagation before execution, after each material assignment, and after any external state change.
- Assign scarce and highly connected variables early; preserve fallback options with least-constraining choices.
- Treat "no plan found" as an explainable conflict-set result, not a vague model failure.
- Use local repair when a long-running route is mostly valid but one assignment changes.
- Decompose large multi-agent plans before launch; dense constraint graphs require tighter budgets and stronger review.
- Promote route-planning changes only after a `constraint_release_gate` proves hard constraints, global constraints, conflict learning, repair behavior, human override, fallback, and rollback.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-generalist-agents-open-ended-worlds]] - Stanford CS25, "Generalist Agents in Open-Ended Worlds" ([YouTube](https://www.youtube.com/watch?v=wwQ1LQA3RCU)).
- [[../../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
