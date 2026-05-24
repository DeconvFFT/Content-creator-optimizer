---
type: pattern-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
sources:
  - [[../../01-sources/official-open/openai-responses-state-tools]]
  - [[../../01-sources/official-open/anthropic-effective-agents]]
  - [[../../01-sources/official-open/anthropic-tool-computer-use-runtime]]
  - [[../../01-sources/official-open/openai-practical-agents]]
  - [[../../01-sources/official-open/anthropic-eval-design]]
  - [[../../01-sources/official-open/aws-genai-security-and-observability]]
  - [[../../01-sources/official-open/openai-apps-sdk-chatgpt-apps]]
  - [[../../01-sources/official-open/openai-agent-builder-chatkit-product-integration]]
  - [[../../01-sources/official-open/code-execution-sandbox-runtime]]
  - [[../../02-lectures/stanford/cs25-world-modeling-jepa]]
  - [[../../02-lectures/stanford/cs25-collaborative-ai-agents-science-medicine]]
  - [[../../02-lectures/stanford/cs224n-rag-agents-reasoning]]
  - [[../../02-lectures/stanford/cs224g-building-scaling-llm-apps]]
  - [[../../02-lectures/stanford/cs224r-reward-reasoning-world-models]]
  - [[../../02-lectures/stanford/cs329x-human-centered-llms]]
  - [[../../02-books/aima/agent-planning-foundations]]
  - [[../../02-books/aima/chapters/5-adversarial-search-and-games]]
  - [[../../02-books/aima/chapters/6-constraint-satisfaction-problems]]
  - [[../../02-books/aima/chapters/11-automated-planning]]
  - [[../../02-books/aima/chapters/17-making-complex-decisions]]
  - [[../../02-books/aima/chapters/18-multiagent-decision-making]]
  - [[../../02-books/prml/chapters/8-graphical-models-route-evidence]]
  - [[../../01-sources/official-open/google-a2a-protocols]]
  - [[../../01-sources/official-open/google-cloud-agentic-architecture-patterns]]
  - [[../../01-sources/official-open/google-secure-ai-agents-model-armor]]
  - [[../../01-sources/official-open/model-context-protocol-tooling]]
  - [[../../01-sources/official-open/langchain-memory-and-persistence]]
  - [[../../01-sources/official-open/langsmith-agent-server-deployment-runtime]]
  - [[../../01-sources/official-open/crewai-crews-flows-agent-runtime]]
  - [[../../01-sources/official-open/huggingface-smolagents-agent-patterns]]
  - [[../../01-sources/official-open/llamaindex-agent-workflows-rag-eval]]
  - [[../../01-sources/official-open/microsoft-agent-framework-autogen]]
  - [[../../01-sources/official-open/aws-bedrock-agentcore-managed-runtime]]
  - [[../../01-sources/official-open/google-agent-platform-managed-runtime]]
  - [[../../01-sources/official-open/uber-ml-platform-agentic-governance]]
  - [[../../01-sources/official-open/uber-prd-reviewer-agent]]
  - [[../../01-sources/official-open/annotation-human-feedback-data-ops]]
  - [[../../04-agent-studio-implications/Route Change Proposal Template]]
  - [[../../04-agent-studio-implications/Datastore Schema - Agent Studio Source and Route Ledger]]
---

# Agent Route Architecture Canon

## Scope

Cross-check synthesis from OpenAI practical agents / AgentKit, Anthropic eval design, AWS GenAI security and observability, and the existing Agent Studio route-change/datastore notes. This note records durable architecture decisions only. It stores no raw source text or long excerpts.

## Canon Decision

Agent Studio should model production agents as versioned routes with explicit justification, typed workflow graphs, tool contracts, trust boundaries, trace-gradeable runs, eval gates, and rollback paths. An agent is not a prompt and not merely a chat session. It is a route release that owns model choice, tools, instructions, graph edges, state, guardrails, traces, evals, and human approval policy.

## When A Route Should Be Agentic

Agentic routing is justified when the workflow involves ambiguity, unstructured evidence, tool choice, multi-step recovery, exception handling, or expensive-to-maintain rules. If the task is stable, deterministic, and low ambiguity, Agent Studio should prefer deterministic code, retrieval, prompt-only transformation, or a simpler workflow.

Anthropic's effective-agents guidance turns this into a topology ladder. A route should declare whether it is an augmented single call, prompt chain, router, parallel workflow, orchestrator-worker graph, evaluator-optimizer loop, or autonomous agent. The selected topology must include rejected simpler alternatives and the evidence that the added latency, cost, state, and coordination burden is worth it.

Required route field:

- `agent_justification`: why this route needs model-controlled workflow execution rather than deterministic automation.
- `workflow_pattern_fit`: selected pattern, rejected simpler pattern, task ambiguity, expected benefit, latency/cost burden, and release gate.

## Single-Agent First

The default escalation ladder is:

1. deterministic workflow or retrieval repair;
2. prompt/template repair;
3. tool schema/description repair;
4. single-agent route with clearly scoped tools;
5. manager-pattern multi-agent route;
6. decentralized handoff graph.

Multi-agent topology requires evidence. Valid evidence includes repeated tool-selection errors, prompt overload, conflicting specialist policies, graph-state complexity, or eval failures that simpler interventions did not solve.

CS25's collaborative science-agent slice tightens this rule: a multi-agent route should match the task shape. Parallel agents fit decomposable search, candidate generation, and independent critique. Centralized orchestration fits synthesis, policy, publication, and high-risk approval. Decentralized debate or evolution loops require measured benefit because coordination overhead and error propagation can erase the gain.

CS25's world-modeling slice adds a state requirement: agentic routes should maintain typed state, relations, and predicted consequences, not just a rolling chat summary. A route that edits artifacts, mutates source indexes, changes route configs, or prepares publishing should record what state will change and which approvals/evals become stale.

AIMA Chapter 2 adds the task-environment requirement: before a route is called agentic, it should declare its percept/input channels, actuator/tool channels, performance measure, observability, determinism, sequentiality, dynamics, knownness, and multiagent character. This prevents the product from choosing autonomous loops where the environment actually calls for deterministic code, a fixed workflow, HITL review, or explicit replanning. Chapter 2 also makes feedback mutation a governed learning-agent problem: reviewer, user, grader, and environment signals should pass through feedback capture, performance-measure review, scoped learning updates, eval, approval, and rollback rather than directly rewriting production behavior.

AIMA's search chapter adds the route-search requirement: model-controlled exploration should separate the world state from the search node, track the frontier and reached states, and make duplicate-state checks visible. A research, critique, repair, or planning loop can revisit the same state through different wording; without reached-state tracking, the agent may look busy while expanding redundant paths. Heuristic routing is allowed, but it needs a policy: what cost it estimates, which constraints it relaxes, whether it is greedy, weighted, or completeness-oriented, and what quality/cost risk the release accepts.

AIMA Chapter 4 adds the complex-environment requirement: when route actions can fail, reveal new information, or change unknown state, the route should use conditional plans, belief-state updates, online search budgets, and safe-exploration policy rather than a fixed open-loop action sequence. Retry loops need an explicit transient-failure assumption and diagnosis trigger because repeated failure may indicate hidden persistent state, not harmless nondeterminism. Candidate-generation routes also need diversity and missed-candidate audits before treating a locally best output as enough.

AIMA Chapter 5 adds the adversarial-search requirement: when another agent, user, model, evaluator, platform, or route can strategically counter the desired outcome, the route should declare a game surface rather than treating the behavior as ordinary nondeterminism. Debate, reviewer panels, red-team simulations, prompt-injection tests, adversarial retrieval cases, and local-metric gaming evals need player/action/utility contracts, information-state records, worst-case search traces, pruning rationale, cutoff-evaluator caveats, rollout records, and metareasoning stop conditions.

AIMA Chapter 6 adds the constraint-satisfaction requirement: before a scheduler, route planner, or multi-agent controller commits to agents, tools, sources, reviewers, deadlines, budgets, formats, or platforms, it should declare variables, domains, hard constraints, soft preferences, and constraint graph structure. Feasibility should be machine-checkable through propagation, assignment traces, conflict sets, learned no-goods, repair records, and decomposition evidence rather than hidden in prompt text.

AIMA Chapter 11 adds the automated-planning requirement: route actions should have explicit schemas with preconditions, add/delete effects, side-effect class, monitoring expectations, and rollback policy. The route should record whether it used progression, regression, bounded SAT/CSP encoding, HTN refinement, contingent planning, online repair, or portfolio planning, and should keep relaxed heuristics separate from final approval evidence.

AIMA Chapter 17 adds the stochastic sequential-decision requirement: high-autonomy routes should declare whether they are MDP-like or POMDP-like. A route needs state variables, actions, transition evidence, rewards/utilities, horizon/discount policy, terminal states, belief-state update policy, and information-gathering rationale before it makes repeated decisions under uncertainty. Bandit-style exploration, selection experiments, and queue scheduling are different decision problems and should not share one hidden "try the best thing" heuristic.

AIMA Chapter 18 adds the multiagent decision requirement: a multi-agent route must declare what kind of multiagent system it is before naming specialists. Centralized multi-actor execution, shared-goal coordination, non-cooperative strategic interaction, cooperative coalition formation, contract-net allocation, auction allocation, voting aggregation, and bargaining have different safety and eval surfaces. The benevolent-agent assumption must be explicit and tested whenever agents differ in prompts, tools, memories, models, permissions, local metrics, or information access.

PRML Chapter 8 adds the graph-semantics requirement: a workflow DAG is not enough for evidence-bearing route design. Agent Studio should distinguish execution edges, evidence-dependency edges, factor edges, explanation edges, and conditional-independence claims. Cyclic critique or refinement loops are approximation zones unless a route records message schedule, convergence policy, stale-message handling, fallback, and rollback.

CS224N's agents/RAG/reasoning slice adds the execution-environment requirement: action loops need versioned environments, typed observations, tool execution boundaries, agent data lineage, and eval environments. Evaluation should include trajectory validity, tool safety, recovery behavior, human-review burden, and artifact quality, not just final task success.

CS224G adds a product-route requirement: agentic complexity should be selected inside a shipped application loop, not as an isolated prompt pattern. A route should show its compiled context, topology, deployment/observability loop, and feedback data path. Multi-agent routes still need measured evidence because specialist partitioning helps only when it reduces context overload, role/tool confusion, or review burden.

CS224G's data-strategy lecture also makes feedback quality part of route architecture. The route should say which feedback forms it captures, whether users receive immediate value from corrections, how LLM-extracted memories are reviewed, which contributor classes are trusted for which slices, and how representation gaps are audited before feedback changes shared memory, ranking, tuning, or evals.

Google Cloud's agentic architecture guidance adds a component-selection requirement: a route topology decision should not be separated from frontend mode, agent framework, tool pattern, memory policy, agent runtime, model runtime, latency class, cost budget, and human-involvement need. The same workflow can be non-agentic, single-agent, sequential, parallel, orchestrated, iterative, or custom HITL depending on those constraints.

Agentic topology changes need their own release gate. Before a route moves from deterministic code or a bounded single agent into workflow agents, manager specialists, decentralized handoffs, or iterative refinement, the release should link component choice, pattern decision, rejected simpler alternatives, a single-agent baseline, runtime/model/tool/memory split, scoped permissions, HITL policy, simulation runs, coordination-failure evals, observability traces, fallback or simpler-route option, and rollback target.

OpenAI Apps SDK adds the app-distribution boundary: an agent route exposed through ChatGPT is a server/tool/UI contract, not just a backend tool. The route needs MCP server identity, app tool descriptors, output schemas, UI template/resource refs, bridge-event handling, state-scope policy, OAuth/scope enforcement, discovery evals, and launch-review evidence before it can be treated as production-ready.

ChatGPT app promotion needs a dedicated release gate because the host decides tool selection and widget rendering while the app server owns authorization and side effects. The gate should prove MCP server identity, tool descriptor versions, output schemas, widget templates, CSP/network policy, structured-content versus `_meta` boundary tests, bridge-event coverage, state ownership, file authorization, OAuth/scopes, discovery evals, handler tests, UX/mobile screenshots, privacy/retention review, dependency review, submission status, fallback behavior, and rollback target.

OpenAI Agent Builder and ChatKit add the product-embedding boundary: a route can be a published workflow with a workflow ID/version and typed visual graph, then embedded in a product chat session. Agent Studio should preserve workflow graph versions, node/edge contracts, trace grader results, session issuance, user identity binding, client-secret issuance metadata, widget definitions, action events, and hosted-versus-custom backend ownership.

Product-embedded chat promotion needs a release gate separate from app distribution. The gate should bind the published workflow snapshot, node/edge contracts, preview traces, trace graders, ChatKit integration mode, backend session endpoint, authenticated user/workspace binding, client-secret expiry posture, widget definitions, action schemas, action validation/auth/idempotency tests, thread item lineage, UI/mobile tests, support handoff, fallback behavior, and rollback target.

For Agent Studio, this strengthens the single-agent-first rule. A multi-agent route should show why one bounded agent with a refined prompt/tool set is insufficient, then choose the least dynamic pattern that fits. Sequential and parallel workflow agents are preferable when order or fan-out is known; model-orchestrated delegation is reserved for tasks whose next step genuinely depends on runtime evidence.

Hugging Face smolagents adds an agency-level requirement: route review should distinguish deterministic code, routers, tool calls, multi-step loops, managed-agent delegation, and code-action agents. Each step upward gives the model more control over program flow and therefore needs stronger evidence, observability, and containment. A route that merely needs a fixed tool sequence should not be promoted to a ReAct loop; a route that needs a manager/specialist split should prove that the split reduced context overload, tool confusion, or eval failures.

Smolagents also separates action format from topology. Code-style actions are useful for computation, object handling, and composition, but require sandbox and import policies. JSON/provider-style tool calls are easier to constrain but need model-facing schema and output ergonomics. Agent Studio should store that action-format decision as a release artifact.

Smolagents-style runtime promotion needs its own gate because framework version, action format, structured-output mode, tool descriptions, MCP imports, Hub dependencies, authorized imports, memory callbacks, managed-agent descriptions, and telemetry settings can all change route behavior. The release should prove the selected agency level, rejected simpler workflow, tool/schema tests, code-execution and sandbox policy, memory/callback semantics, managed-agent task contracts, agentic-RAG trace policy, OTel/OpenInference export policy, eval evidence, failure policy, and rollback target.

Google's secure-agent guidance adds an authority requirement: an agentic route needs a controller, limited powers, and observable planning/actions before it gets privileged tools. A topology decision is incomplete if it names specialists but omits who controls them, which authority they have, which gateway enforces it, and which action observations prove they stayed inside scope.

OpenAI Responses adds a provider-runtime requirement: a route can emit typed output items, provider-side response state, tool calls, MCP import events, background lifecycle states, and streaming events. Agent Studio should preserve those provider objects, but not rely on them as the only audit/replay mechanism.

Anthropic's tool and computer-use docs add the execution-owner requirement: model-visible tools may run in the product, on provider infrastructure, in a sandboxed desktop, in a persistent shell, through a text editor, or through a remote MCP connector. A route should not be approved until it declares who executes the action, where state persists, what can be seen, what can be changed, which credentials and domains are reachable, and which retention policy applies.

OpenAI, Modal, and E2B sandbox docs make code execution a separate route class. A code-action route needs a sandbox profile, concrete sandbox instance, file bindings, process runs, network/filesystem policy, artifact export gate, recovery policy, and cleanup proof. Provider-hosted code interpreter is an executor option, not the route ledger.

CS329X adds the human-agency requirement: an agent route should declare whether it is autonomous, user-steered, reviewer-gated, approval-gated, or shared-workspace collaborative. Those modes are not UX labels; they change the eval surface. A collaborative route should measure process quality, user effort, repair behavior, intervention points, initiative balance, and preservation of user control in addition to final artifact quality.

CS224R adds the reward/task-conditioning requirement: an agent route should declare the task family, objective, reward/proxy signals, and reusable feedback boundary before learning from outcomes or sharing feedback across tasks. A generalist route is only reviewable when the task condition says which state, action, tool, source, and reward surfaces are active.

Annotation data-ops sources add the feedback-origin requirement: route feedback must preserve whether it came from an independent human response, a reviewer-edited model suggestion, a weak label, an active-learning batch, or an SME correction. Agent Studio should not learn from feedback until the annotation schema version, guideline version, assignment policy, reviewer class, suggestion source, and dataset-promotion status are visible.

Required route fields:

- `task_decomposition_evidence`: why the work is parallelizable or benefits from specialist roles;
- `loop_stop_policy`: cost, latency, quality-gain, and reviewer-fatigue limits for critique/debate/evolution loops;
- `candidate_pool_policy`: how generated alternatives, rejected candidates, rankings, and critique traces are retained.
- `agent_complexity_gate`: eval slices or trace failures proving that the simpler route is insufficient.
- `agent_training_data_record`: human, synthetic, simulated, or rejection-sampled trajectory lineage.
- `agent_eval_environment_record`: versioned task environment, fixtures, allowed actions, success criteria, and human-judgment policy.
- `search_node_record`: candidate path node with world-state ref, parent node, action, path cost, heuristic score, evaluation score, depth, and status.
- `search_frontier_snapshot`: frontier, reached states, expanded nodes, duplicate states, queue policy, and timestamp for search-style routes.
- `heuristic_policy_record`: heuristic name, estimated cost surface, relaxed constraints, weight, admissibility/consistency claim, known biases, and eval refs.
- `route_search_performance_record`: completeness expectation, optimality or satisficing policy, time/context budget, branching estimate, effective branching factor, duplicate-state rate, and missed-candidate audit refs.
- `game_surface_record`: strategic route surface with players/agents, state representation, legal actions, turn policy, terminal test, and utility/payoff contract.
- `adversarial_search_trace`: minimax-style candidate/counteraction search with backed-up utilities, cutoff depth, pruned branches, and selected action.
- `pruned_branch_record`: skipped adversarial/search branch with bound or dominance rationale, risk class, and reviewer visibility.
- `cutoff_evaluation_record`: nonterminal heuristic evaluation with evaluator identity, feature/signal summary, score, calibration, and caveats.
- `monte_carlo_rollout_record`: simulated trajectory with environment version, rollout policy, terminal outcome, and utility.
- `search_budget_record`: depth/time/token/cost/reviewer budget for adversarial, debate, critique, or simulation search.
- `metareasoning_stop_record`: reasoned stop/prune/escalate decision based on expected decision improvement versus cost.
- `adversarial_route_release_gate`: promotion gate for debate, adversarial eval, strategic multiagent interaction, or self-play-style improvement.
- `constraint_problem_record`: route feasibility surface with variables, domains, constraints, preference boundary, and solver status.
- `constraint_variable_record`: assignable route variable such as model, source, tool, reviewer, deadline, platform, artifact type, or budget bucket.
- `constraint_domain_record`: allowed values with eligibility evidence, removed values, and removal reasons.
- `constraint_relation_record`: unary, binary, higher-order, or global constraint with enforcement policy and violation severity.
- `constraint_graph_record`: graph/hypergraph of route variables and constraints for scheduling, decomposition, and risk inspection.
- `partial_assignment_record`: current planner assignment with remaining domains and unresolved constraints.
- `constraint_propagation_event`: domain-pruning event caused by consistency checking, global constraint, or forward checking.
- `arc_consistency_record`: pairwise support check between variables with removed values and remaining compatible pairs.
- `constraint_conflict_set_record`: assignments responsible for an empty domain or detected infeasibility.
- `constraint_no_good_record`: learned invalid assignment combination to prune future route search.
- `constraint_solver_policy`: variable/value ordering, inference, backtracking, learning, local-search, and timeout policy.
- `constraint_search_trace`: backtracking, propagation, backjumping, learned no-good, or local-search trajectory.
- `constraint_repair_record`: minimal-change route repair after source, tool, reviewer, policy, schedule, or artifact state changes.
- `constraint_decomposition_record`: cutset, tree-decomposition, independent-subproblem, or symmetry-breaking decision with cost tradeoffs.
- `constraint_release_gate`: promotion gate proving constraints are explicit, propagated, conflict-explainable, repairable, and reviewed.
- `planning_domain_record`: reusable route state vocabulary, action schemas, and resource schemas for a route family.
- `planning_problem_record`: run-specific initial state, goals, forbidden states, and risk class.
- `planning_state_fact_record`: factored state fluent with observation source, confidence, and stale-after policy.
- `planning_mode_decision`: selected planner mode and rejected alternatives.
- `planning_heuristic_record`: relaxed planning heuristic, relaxed effects/constraints, caveats, and eval refs.
- `high_level_action_record`: abstract route action with allowed refinements and expected effects.
- `refinement_method_record`: decomposition method from a high-level action to lower-level route actions.
- `abstract_plan_reachability_record`: works/fails/needs-refinement evidence for abstract plans.
- `contingent_plan_branch_record`: observation-triggered branch with fallback and risk.
- `execution_monitoring_record`: expected effect, observed effect, deviation, repair, and escalation decision.
- `temporal_plan_record`: ordering, duration, earliest/latest start windows, critical path, and schedule status.
- `resource_pool_record`: reusable or consumable reviewer/tool/model/quota/budget resource capacity and commitments.
- `schedule_repair_record`: route schedule repair after timing or resource conflict.
- `planning_release_gate`: promotion gate proving action schemas, planner mode, heuristic caveats, hierarchy/refinement, contingent branches, resource schedule, monitoring, fallback, and rollback.
- `route_topology_decision`: selected deterministic/workflow/single-agent/multi-agent shape, rejected alternatives, evidence for escalation, observability requirements, and feedback data path.
- `collaborative_agent_topology_release_gate`: task decomposition, selected and rejected topology alternatives, coordination contract, expected value, communication/tool overhead, latency/cost budget, reviewer-fatigue budget, error-propagation risk, role contracts, candidate-pool retention, critique/ranking/source-evidence traces, loop-stop policy, domain boundary, scenario eval rubrics, human expert gate, fallback, rollback, and incident feedback before collaborative-agent topologies replace simpler routes.
- `multiagent_environment_record`: selected relationship model across centralized actors, shared-goal teams, strategic counterparts, coalitions, auctions, voting panels, or bargaining parties.
- `agent_payoff_contract`: local agent objective, metric, authority, information, and divergence from global product utility.
- `joint_action_record`: synchronized or concurrent action with participant set, mutual exclusion/resource constraints, communication needs, and expected combined effect.
- `coordination_protocol_record`: convention, manager authority, locks, synchronization states, and communication policy for shared-goal agents.
- `game_form_record`: strategic interaction with players, actions, information, payoffs, sequence/chance, commitment assumptions, and observability.
- `assistance_game_preference_record`: human-preference uncertainty, teaching/correction/demonstration evidence, defer/ask behavior, and override boundary.
- `contract_net_task_record`: task announcement, bids, award, contractor result, rejected bids, and recursive subtask expansion.
- `auction_allocation_record`: scarce-resource allocation with mechanism, bids/value reports, winner, cost/tax/price, truthfulness caveat, and collusion check.
- `social_choice_aggregation_record`: voting/ranking aggregation rule, voters, candidates, weights, agenda, tie-breaker, manipulation caveat, and minority objections.
- `negotiation_session_record`: bargaining conflict deal, feasible agreement set, concessions, discount/cost assumptions, and final agreement status.
- `strategic_manipulation_eval_case`: collusion, false bidding, agenda manipulation, hidden preference, non-credible threat, or misleading capability-report eval.
- `multiagent_decision_release_gate`: promotion gate for multi-agent, voting, auction, contract-net, negotiation, debate, reviewer-panel, and coalition routes.
- `route_context_assembly_record`: system/product/user instruction layers, memory, retrieval, uploaded data, tool definitions, parameters, truncation/summarization policy, trust labels, and token budget.
- `provider_state_policy`: provider response state, local reconstruction, persistent conversation, stateless encrypted reasoning, or hybrid state mode, with retention and replay caveats.
- `agentic_component_choice`: frontend, framework, tool pattern, memory, agent runtime, model runtime, rejected alternatives, workload rationale, and reassessment trigger.
- `agent_design_pattern_decision`: chosen topology, task characteristics, latency/cost budget, human-involvement need, rejected patterns, and release gate.
- `agentic_architecture_release_gate`: component choice, pattern decision, runtime/model/tool/memory split, rejected simpler alternatives, single-agent baseline, coordination contract where used, scoped permissions, HITL policy, simulation runs, coordination-failure evals, observability traces, fallback or simpler route, rollback target, and promotion decision.
- `agent_controller_record`: responsible human/workspace/organization controller, delegated reviewers, allowed autonomy, budget owner, and escalation path.
- `agent_authority_scope`: allowed tools, APIs, retrieval scopes, spending caps, external side effects, approval needs, and expiry.
- `human_agent_collaboration_session`: user, agent, shared workspace, task environment, autonomy mode, intervention policy, and terminal outcome.
- `user_agency_control`: pause, steer, approve, reject, rollback, and visibility affordances available for route actions.
- `collaboration_process_metric`: user effort, repair count, interruption count, initiative balance, clarification quality, satisfaction signal, and reviewer caveat.
- `agent_agency_level`: selected level of model control over program flow, rejected simpler levels, rationale, risk/cost burden, and eval evidence.
- `agent_action_format_policy`: code, JSON tool call, provider-native tool call, or hybrid action format, with constraints and containment policy.
- `task_condition_record`: task family, goal, state/action surfaces, reward specification, allowed tools, source policy, artifact type, memory policy, and status.
- `reward_specification_record`: route objective decomposition across success proxies, preferences, verifiers, grounding, style, safety, and known blind spots.
- `feedback_origin_record`: human response, edited suggestion, weak label, active-learning item, SME correction, production feedback, or synthetic/evaluator label with trust and reuse policy.
- `feedback_capture_event`: artifact-targeted label, rating, explanation, direct edit, passive signal, or expert review with route/source context and immediate-user-value evidence.
- `memory_extraction_review`: candidate memory extracted from feedback, its scope, privacy/rights review, expiry, edit/delete affordance, and promotion decision.
- `contributor_quality_profile`: privacy-safe evidence for expertise, consistency, hard-case accuracy, peer agreement, retention depth, and representation caveats used for feedback weighting.
- `feedback_reuse_policy`: allowed reuse surfaces, aggregation weight, representation audit, source-grounding check, and consent/terms status before feedback mutates routes or shared datasets.

## Typed Graph Edges

Agent Studio graph edges should be typed because different edges carry different risks and eval requirements:

- `typed_data_edge`: validated payload from one node to another;
- `tool_call_edge`: a route calls a tool or a specialist-as-tool;
- `handoff_edge`: control transfers to another specialist route with card/skill refs, task ID, context ID, and terminal state;
- `approval_edge`: human or policy confirmation is required before continuing;
- `guardrail_edge`: safety/source/privacy check gates a transition;
- `terminal_edge`: route completes, fails, escalates, or rolls back.

Every edge should declare input schema, output schema, trust level, failure policy, and trace fields.

## Tool Interface Contract

Anthropic's tool appendix adds a production review requirement: tool contracts must be tested as model-facing interfaces, not only validated as API schemas. Agent Studio should treat parameter names, descriptions, examples, output formats, edge cases, and overlap between similar tools as correctness surfaces.

Required records:

- `tool_interface_test`: example inputs, expected tool choice, observed mistakes, schema or description revision, and retest outcome.
- `tool_ergonomics_decision`: chosen output format, avoided format burden, parameter naming rationale, and known model failure modes.

This also constrains framework use. Frameworks can implement routing, checkpoints, and tool calling, but the route review surface must still show prompts, tool definitions, tool responses, model-visible state, and graph transitions.

## Agent Protocol Contract

Google's A2A/ADK guidance adds an interoperability contract to the route model. Agent Studio can stay local-first, but route releases should already model the objects needed for future A2A exposure:

- agent discovery through versioned card records;
- skill selection as a governed dependency;
- task lifecycle records instead of opaque specialist calls;
- typed artifact parts rather than chat-only outputs;
- streaming task-status and artifact-update events;
- push notification or webhook subscriptions for long-running tasks;
- durable session state and explicit resume requests;
- auth schemes, credential scopes, card freshness, and idempotency keys as release-gate fields.

This matters because multi-agent routes fail quietly when a remote or specialist agent changes capability, auth, output mode, or terminal-state semantics. Card hash, selected skill, task ID, and fallback policy should be captured in the run trace.

MCP adds a separate connector contract. A2A models specialist-agent identity and task handoff; MCP models server-exposed tools, resources, and prompts. Agent Studio should not collapse these layers. A route can call a specialist agent through A2A-style task records, while that specialist exposes project files, search, source ledgers, browser actions, or narrow APIs through MCP-style server records. Capability snapshots, list-change notifications, transport/session policy, and auth grants become release-gate evidence because a changed MCP tool/resource/prompt list can change model behavior without changing the route graph.

Uber's uSpec case adds a concrete work-surface pattern: the agent uses local MCP access to inspect authoritative design-system structure, combines that with versioned skill instructions and reference docs, and renders directly back into Figma. Agent Studio should prefer this pattern for Obsidian, browser, Figma, social-draft, and publishing surfaces: inspect structured source truth, apply domain skills, then write through constrained programmatic actions with validation and rollback evidence.

Uber's PRD Evaluator adds the upstream-review pattern: reviewer agents should strengthen an artifact before high-cost human review, not become the final approval authority. A reviewer route needs context assembly, risk classification, readiness dimensions, prioritized repair actions, and evidence for findings. A reviewer route should not influence release, canon, or publishing decisions until a first-pass review release gate proves the artifact, access-bounded context bundle, risk class, scorecard dimensions, critical gaps, repair actions, evidence refs, human-authority boundary, override policy, and post-review outcome policy.

OpenAI Responses makes MCP/connectors part of the model-visible runtime. Imported remote tools need tool-list snapshots, approval policies, server trust tier, output-sensitivity labels, and data-sharing logs. A changed remote tool definition can change model behavior without a route-code diff, so imported tool lists belong in release evidence.

Smolagents adds a concrete managed-agent trace requirement. A manager can call a named specialist agent with a description, and that specialist returns observations or artifacts to the manager for synthesis. Agent Studio should model this as `managed_agent_call`, not as anonymous nested chat. The manager owns task decomposition and final synthesis; the specialist owns bounded tool execution; both need failure policies and trace IDs.

LlamaIndex adds an event-driven workflow requirement. Agent Studio should model a route as typed events and steps, then render a graph projection for humans. This matters because real agent workflows contain loops, streaming events, human waits, checkpoint resumes, corrective retrieval branches, and multi-agent handoffs that do not fit cleanly into a static chain. A route release should preserve the event types a step accepts and emits, the context snapshot used at each checkpoint, and the human wait/response events that changed execution.

Microsoft Agent Framework sharpens the route-choice boundary: use a function for deterministic tasks, an agent for open-ended tool-using conversation, and a workflow when the business process has explicit steps, multiple components, human request/response waits, or checkpoint/resume requirements. AutoGen's lineage remains useful for team patterns, but production routes should preserve typed workflow executors, typed edges, session providers, and checkpoint state rather than relying on an opaque group chat transcript.

Agent Framework-style runtime promotion needs a dedicated gate because behavior can change through component choice, credential fallback, session/history/context provider wiring, audit-store position, typed edge schemas, HITL request/response waits, checkpoint semantics, A2A cards/capabilities/context IDs, streaming/background continuation, middleware, MCP/tool bindings, team pattern/stop policy, team edits, third-party dependencies, or responsible-AI mitigations. The release should prove those surfaces alongside benchmark/eval evidence, fallback, and rollback.

AWS Bedrock AgentCore adds the managed-runtime boundary. A route can run on local orchestration, an open-source framework, or a managed runtime, but the architecture still needs separate runtime, memory, gateway, registry, identity, tool-runtime, and observability records. Managed runtime convenience should not hide tool permissions, delegated identity, shared memory, browser/code execution, or gateway exposure from the route review.

Google Agent Platform adds the managed-runtime rollout boundary. Agent Studio should separate logical route releases from runtime deployment source, package spec, immutable revision, traffic split, per-agent identity, gateway binding, session state, Memory Bank, trace/log/metric configuration, and agent-eval feedback loop. A managed platform can make deployment easier, but route review still needs evidence for reproducibility, rollout state, least privilege, observability, redaction, and regression scoring.

LangSmith Agent Server adds the local/runtime execution boundary most relevant to Agent Studio's first implementation. Graphs, assistants, threads, runs, streams, interrupts, cron jobs, MCP/A2A endpoints, webhooks, and task queues are distinct runtime objects. A route release should not hide assistant config versions inside a graph deploy, or hide thread state inside long-term memory. Streaming and join/rejoin behavior should be a UI/runtime contract, not incidental SDK behavior.

CrewAI adds the role/task collaboration boundary. Crews are useful when specialist roles and task outputs are the main control surface; Flows are preferable when the branch/order/state is known. Agent Studio should record the difference. A role/task crew without expected-output evals, manager-authority policy, scoped knowledge, memory review, guardrails, and repeated test variance is not production-ready just because the agents can collaborate.

## Persistence And Memory Contract

LangGraph/LangChain adds a sharper state distinction to the route model:

- checkpointed thread state is the resumable execution state for one graph run;
- long-term memory is cross-thread state with explicit namespace, scope, write policy, and evidence;
- procedural memory is a governed skill or instruction bundle;
- organization memory is usually read-only policy, not agent-editable memory.

Agent Studio routes therefore need a memory contract before release. The route must declare which memory scopes it can read, which it can write, whether writes require interrupt/reviewer approval, how conflicts are resolved, how background consolidation works, and which trace/source evidence justifies a promoted memory. Checkpoint history, replay, and fork records are part of reviewability: a route change that cannot explain which checkpoint produced an artifact is not production-ready.

Smolagents' memory and plan-interrupt patterns add step-level replay requirements. Planning, action, observation, error, media observation, callback mutation, and final-answer validation should be discrete memory events. A human plan edit should create a `planning_interrupt_record` and `agent_memory_mutation`, then resume with preserved memory rather than losing the reason the route changed direction.

## Trust Boundaries

OpenAI and AWS converge on the same durable rule: untrusted content must not become privileged instruction. Retrieved chunks, browser text, uploads, comments, transcripts, captions, and social posts should enter as typed context or user-level data, then be extracted into constrained fields before they can drive tools or downstream decisions.

Required records:

- `trust_boundary_event`: untrusted input source, extraction schema, sanitizer/guardrail result, downstream fields populated, and reviewer override if any.
- `tool_permission`: side-effect class, credential scope, approval requirement, route/user role, and expiration.
- `trace_redaction_policy`: sensitivity and retention rules for prompts, traces, tool outputs, screenshots, and generated artifacts.

## Evaluation Contract

Anthropic's success-contract framing and OpenAI's trace grading converge on the same implementation pattern: route promotion requires both task success criteria and trace-level observability.

Required eval surfaces:

- final artifact quality;
- schema validity;
- source grounding and citation behavior;
- tool selection and tool argument precision;
- handoff accuracy;
- guardrail decision correctness;
- latency/cost regressions;
- trace-level failure slices.

Aggregate judge scores are insufficient. Promotion must expose regressions by surface.

## Human Approval

Human approval is a route-state primitive. It is required for external mutation, publishing, deletion, purchase, account action, sensitive-data exposure, and route changes that affect canon or production behavior.

Approval records should include approver, scope, risk class, decision, artifact/trace IDs reviewed, and rollback trigger.

For safety-critical or expertise-heavy routes, split generator behavior from checker/planner behavior. A route that produces public claims, medical/scientific explanations, legal-adjacent guidance, or brand-sensitive publishing should declare a `domain_safety_boundary` and a `human_expert_gate` before release.

## Datastore Implications

Add or strengthen these objects:

- `agent_route`: include `agent_justification`, `deterministic_alternative`, `risk_tier`, `approval_policy`, and `trust_boundary_policy`.
- `workflow_pattern_fit`: chosen Anthropic pattern, simpler alternatives rejected, task ambiguity, expected benefit, latency/cost burden, and required eval gate.
- `agent_complexity_gate`: route baseline, failed slices, added topology, measured improvement, added burden, and rollback condition.
- `task_environment_contract`: route performance measure, sensors/percepts, actuators/tools, observability, agent count, determinism, sequentiality, dynamics, knownness, and risk tier.
- `agent_architecture_record`: model, memory, sensor channels, tool contracts, actuator channels, state policy, and approval policy.
- `performance_measure_review`: metric shortcut, reward-hacking, blocked-tradeoff, and objective-uncertainty review before route promotion.
- `learning_update_record`: governed behavior change from feedback with provenance, scope, eval evidence, approval, and rollback.
- `planning_action_schema`: workflow/tool action preconditions, effects, side-effect class, failure modes, and rollback policy.
- `candidate_pool_snapshot`: local/beam/evolutionary candidate states, fitness, diversity, rejected alternatives, and missed-candidate audit refs.
- `local_search_policy_record`: neighborhood, objective, restart/annealing/beam/diversity policy, stop rule, and local-optimum caveats.
- `and_or_plan_record`: conditional plan separating route choices from environment outcome branches.
- `outcome_branch_record`: uncertain action result with branch action, fallback, or escalation policy.
- `cyclic_plan_retry_policy`: retry loop contract with transient-failure assumption, diagnosis trigger, retry budget, and stop condition.
- `belief_state_search_record`: search over possible hidden states with prediction/update and pruning evidence.
- `belief_state_update_event`: recursive state-estimation event from prior belief, action, observation, and updated belief.
- `localization_state_record`: UI/app/source/tool/environment localization belief for partially observable routes.
- `online_environment_map`: learned state/action/result map for unknown or dynamic route surfaces.
- `safe_exploration_policy`: reversibility, irreversible-action approval, exploration budget, and dead-end risk policy.
- `online_search_release_gate`: promotion gate for routes that interleave action, observation, state update, and planning in unknown or dynamic environments.
- `abstract_plan_record`: high-level plan, abstraction level, reachable status, refinement status, and owner.
- `contingency_branch_record`: trigger condition, observation evidence, branch actions, expected effect, and fallback route.
- `replanning_event_record`: previous plan, new plan, trigger, invalidated assumptions, and decision reference.
- `information_gathering_action`: uncertainty, candidate sources, expected decision impact, cost/latency, result, and stop reason.
- `sequential_decision_problem_record`: state/action/transition/reward/horizon/terminal contract for stochastic route decisions.
- `route_policy_record`: versioned state-to-action or belief-to-action policy with discount/horizon and approval boundary.
- `route_policy_execution_record`: selected action, rejected alternatives, expected utility, realized outcome, and trace refs.
- `transition_model_record`: empirical or specified route-state transition assumptions and calibration evidence.
- `reward_utility_contract`: reward components, long-term utility, terminal states, and forbidden reward-shaping shortcuts.
- `online_planning_trace`: lookahead depth, sampled outcomes, frontier states, heuristic, stop reason, and selected action.
- `bandit_policy_record`: exploration/exploitation policy for prompt, model, retriever, source, reviewer, or content-format allocation.
- `selection_problem_record`: best-option identification task with test budget, metric, stopping rule, and final choice.
- `opportunity_cost_record`: scheduling cost of attending to one source, eval, review, or publishing task while others wait.
- `pomdp_belief_state_record`: hidden-state belief separated from observed event trace and sensor model.
- `sensor_model_record`: reliability of observations such as extraction success, source freshness, tool status, or reviewer signal.
- `sequential_decision_release_gate`: promotion gate before stochastic sequential policies, bandits, online planning, or POMDP belief updates affect route behavior.
- `agent_environment_planning_release_gate`: task-environment contract, success/performance measure, sensors, actuators, planning action schemas, planning release gate, constraint release gate, abstract plans, contingencies, replanning policy, information-gathering policy, autonomy evals, human boundary, fallback, and rollback before a route claims agentic behavior.
- `candidate_pool`: generated alternatives, rejected candidates, ranking signals, critique traces, source evidence, and final selection rationale.
- `workflow_version`: include typed nodes, typed edges, schemas, graph ownership, and publish snapshot.
- `workflow_edge`: explicit edge type, source/target node, schemas, trust class, approval requirement, and failure policy.
- `provider_response_record`: provider response identity, model snapshot, request hash, store/background flags, previous-response ref, conversation ref, retention class, and terminal status.
- `provider_response_item`: typed output item from provider runtime, linked to content/artifact hashes and validation status.
- `provider_state_ref`: provider-side continuation pointer with retention/expiry, ZDR compatibility, and local fallback context refs.
- `tool_contract`: schema, examples, side-effect class, credential scope, owner, test coverage, and approval mode.
- `tool_definition_snapshot`: function/built-in/MCP tool definition, schema hash, strict mode, allowed-tools policy, owner, and route release.
- `tool_call_item`: model-requested tool call, arguments hash, approval ref, output artifact ref, error/status, latency, cost, and idempotency key.
- `tool_interface_test`: model-facing examples, edge cases, observed misuse, revised description/schema, retest result, and owner.
- `tool_ergonomics_decision`: output format, parameter naming rationale, avoided formatting overhead, and known caveats.
- `sandbox_profile`: route-release execution boundary for model-written code, including executor class, provider, resource limits, network/filesystem/secret/package policy, and artifact export policy.
- `sandbox_instance`: concrete code interpreter, container, VM, or cloud sandbox session used by one run.
- `sandbox_file_binding`: input or output file visibility inside the sandbox, linked to source/artifact refs and export approval.
- `sandbox_process_run`: command/cell/process execution record with timeout, stdout/stderr refs, error class, kill policy, and cleanup evidence.
- `sandbox_recovery_decision`: retry/resume/clean-sandbox/human-review/block decision when code execution fails, expires, times out, or leaves dirty state.
- `mcp_server_record`: server/process identity, transport, protocol version, capability snapshot, auth mode, trust tier, owner, and status.
- `mcp_tool_import_event`: imported remote tool-list event with server ref, transport, auth scope, allowed/rejected tool list, and review status.
- `mcp_tool_record`: MCP tool name, description hash, input/output schemas, annotations, task support, side-effect class, permission refs, and eval coverage.
- `mcp_resource_record`: MCP resource URI/template, mime type, annotations, source/rights linkage, subscription status, freshness, and sensitivity label.
- `mcp_prompt_record`: MCP prompt template identity, arguments, owner, version, intended user action, linked prompt artifact, and eval coverage.
- `mcp_work_surface_record`: local or remote work surface exposed to an agent with capability snapshot, data boundary, write permissions, and rollback support.
- `chatgpt_app_record`: ChatGPT app identity, MCP server refs, distribution status, owner, review state, and allowed workspace/surface policy.
- `app_tool_descriptor_record`: versioned app tool descriptor with schemas, output template/resource URI, visibility, file params, security schemes, and model-facing metadata hash.
- `app_widget_template_record`: iframe widget template, resource URI, CSP domains, bridge version, display constraints, and asset refs.
- `app_bridge_event_record`: MCP Apps bridge event with direction, method, widget/message/run refs, payload hash, model-visible flag, and error state.
- `app_state_scope_record`: ownership and lifetime record for backend business data, message-scoped UI state, and durable cross-session preferences.
- `app_discovery_eval_case`: positive, indirect, ambiguous, and negative prompt case for expected app/tool selection or rejection.
- `chatgpt_app_release_gate`: MCP server identity, tool descriptors, schemas, widget/CSP resources, model-visible data-boundary tests, bridge events, state scopes, file authorization, auth grants, discovery evals, launch review, fallback, and rollback evidence.
- `agent_builder_workflow_record`: published visual workflow snapshot with workflow ID/version, node/edge refs, owner, deploy target, and status.
- `workflow_node_contract_record`: node type, model/tool/agent binding, input/output schemas, guardrails, eval refs, and trace fields.
- `chatkit_integration_record`: product chat surface, hosted/custom backend mode, workflow ref, frontend embed config, backend session endpoint, enabled features, and owner.
- `chatkit_session_record`: end-user/workspace-bound session lifecycle with workflow version and client-secret issuance metadata.
- `chatkit_action_event`: widget or frontend action payload, sender item, validation/auth result, side-effect class, idempotency key, and generated thread refs.
- `product_chat_release_gate`: workflow snapshot, node/edge contracts, trace graders, ChatKit integration mode, session issuance, user/workspace binding, client-secret posture, widget/action schemas, action validation, thread lineage, UI tests, support handoff, fallback, and rollback evidence.
- `agent_action_runtime_release_gate`: agency level, rejected simpler workflow, action format, framework version, tool/MCP/Hub dependency snapshots, structured-output mode, code/sandbox policy, memory and callback semantics, managed-agent contracts, telemetry policy, eval evidence, failure policy, and rollback target.
- `agent_framework_runtime_release_gate`: framework version, component choice, rejected deterministic alternative, agent/workflow/team/A2A mode, credential/session/history/context/audit policy, typed executor/edge contracts, HITL waits, checkpoint policy, A2A card/capability/context mapping, streaming/background continuation, middleware/tool/MCP bindings, team pattern/stop/edit policy, observability, benchmark/eval evidence, third-party review, fallback, and rollback.
- `agent_skill_instruction_record`: versioned skill instructions, domain rules, reference docs, schemas, validation checks, and target surfaces.
- `artifact_render_action`: constrained write/render operation into a target artifact surface with validation state and rollback refs.
- `review_artifact_record`: submitted draft, route proposal, content packet, or release candidate under first-pass review.
- `context_assembly_record`: linked and discovered documents, prior experiments, policies, metrics, and adjacent artifacts used by a reviewer route.
- `proposal_risk_classification`: review-depth decision and reason for light, moderate, full, or specialized scrutiny.
- `readiness_scorecard`: structured readiness result with dimensions, evidence refs, prioritized fixes, and decision status.
- `agent_card_record`: local/remote agent identity, capabilities, skills, endpoint, version/hash, security schemes, modality support, freshness, and trust tier.
- `agent_skill_record`: card-bound callable skill, input/output modes, eval coverage, rate limits, and failure policy.
- `a2a_task_record`: specialist invocation with context ID, status, history refs, artifact refs, stream refs, cancellation state, and terminal outcome.
- `agent_artifact_part_record`: text/file/data output part with schema, storage ref, hash, rights/sensitivity label, and validation state.
- `agent_stream_event`: ordered task status or artifact delta that can be replayed by the UI and audit tools.
- `push_notification_subscription`: task webhook or async callback contract, delivery state, expiry, and revocation status.
- `session_store_record`: durable route/session state backend, checkpoint policy, hydration status, and retention/redaction policy.
- `human_resume_request`: pending approval or external fact required before a long-running route can continue.
- `protocol_security_scheme`: endpoint auth method, credential scope, storage policy, rotation cadence, and least-privilege review.
- `protocol_idempotency_record`: retryable operation key, request hash, first response, conflict policy, and expiry.
- `checkpoint_record`: thread/checkpoint/namespace identity, super-step, state hash, parent checkpoint, next nodes, task refs, interrupt refs, and created_at.
- `checkpoint_write_record`: node or task write, reducer policy, completion/error status, pending-write recovery state, and replay eligibility.
- `memory_scope_policy`: user/agent/org/project scope, namespace tuple, read/write permissions, approval requirement, retention, conflict policy, and redaction policy.
- `long_term_memory_item`: memory namespace/key/type, value hash, evidence refs, embedding policy, review status, created_at, and updated_at.
- `memory_consolidation_run`: recent-thread window, consolidation route version, memory writes, conflicts, rejected memories, evidence refs, and reviewer outcome.
- `interrupt_record`: runtime pause payload, checkpoint, node/task, reviewer/actor, decision or value ref, resume command, and final status.
- `replay_fork_record`: source checkpoint, state update summary, changed fields, downstream invalidations, and comparison outcome.
- `trace_metadata_record`: route version, environment, user/session refs, source snapshot, tags, anonymizer/redaction policy, and export destination.
- `graph_blueprint_record`: graph ID, code artifact, state schema, node/edge contracts, framework version, and compatibility status.
- `route_factor_node`: typed factor in a route decision graph, such as source support, citation validity, policy risk, style consistency, retrieval coverage, or reviewer signal.
- `route_variable_node`: observed or latent route-state variable with conditioning context and source refs.
- `conditional_independence_claim`: reviewed graph claim that variables can be separated under a named conditioning context.
- `markov_blanket_context`: minimal debug/retrieval context for a route variable, claim, or decision node.
- `graph_inference_trace`: message-passing or local-propagation trace with schedule, messages, convergence, and caveats.
- `loopy_route_approximation`: cyclic graph or iterative agent-loop approximation with stop criteria, diagnostics, failure modes, and fallback.
- `graph_structure_change_candidate`: proposed dependency/factor/edge change from traces or incidents, with eval and review status.
- `graph_route_release_gate`: graph-semantics promotion gate tying factors, variables, independence claims, message traces, approximation caveats, structure-change candidates, fallback, and rollback.
- `assistant_configuration`: assistant ID, graph ID, prompt/model/tool/config values, environment, personalization scope, and active status.
- `assistant_version_record`: assistant config hash, changed fields, eval refs, promoted/rollback state, creator, and timestamp.
- `thread_state_container`: thread ID, current checkpoint, status, metadata, TTL policy, privacy scope, and copied-from ref.
- `deployment_run_record`: run ID, thread ID, assistant version, input refs, stream mode, background flag, status, cost/latency summary, and terminal state.
- `run_stream_subscription`: run/thread stream, subscriber, stream modes, last event ID, reconnect policy, visibility policy, and retention.
- `scheduled_agent_job`: cron expression, UTC/timezone handling, assistant/thread/input refs, idempotency policy, owner, next run, and output policy.
- `crew_definition_record`: agents, tasks, process mode, manager LLM, function-calling LLM, memory/cache/rate-limit/tracing/security/checkpoint policy, and owner.
- `crew_task_record`: task description, expected output, assigned agent, allowed tools, async flag, guardrail refs, human-input requirement, callbacks, and output artifact refs.
- `flow_definition_record`: start/listen/router methods, state schema, called crews, terminal outputs, visualization ref, and owner.
- `agent_knowledge_scope`: crew-level or agent-level knowledge source refs, storage collection, embedder config, retrieval policy, rights, and visibility.
- `knowledge_retrieval_event`: original prompt hash, rewritten query hash, source collection, retrieved chunks, failure status, and trace refs.
- `crew_test_run`: crew version, iteration count, judge/model, task scores, crew score, execution time, variance, failed tasks, and promotion impact.
- `crew_flow_runtime_release_gate`: framework version, control-mode decision, crew/task/agent contracts, manager authority, flow state/events, checkpoint/callback policy, tool/MCP/app/skill dependencies, knowledge and memory policy, guardrail retry policy, human-input gates, structured outputs, trace/telemetry policy, repeated test variance, security/rate/cache policy, fallback, and rollback evidence.
- `run_trace`: node events, edge traversals, model calls, tool calls, handoffs, guardrails, approvals, stop reason, and redaction policy.
- `orchestrator_delegation_trace`: central plan, delegated worker, task contract, returned artifact, synthesis decision, and failure handling.
- `trace_grade`: target trace span, grader version, rubric, score/label, failure slice, and release-blocking flag.
- `trust_boundary_event`: untrusted input handling and extraction evidence.
- `world_state_record`: typed snapshot of source, artifact, workflow, route, approval, and publish state relevant to an agent run.
- `state_transition_record`: proposed action, predicted state changes, affected artifacts, invalidated approvals/evals, rollback path, and observed outcome.
- `artifact_dependency_graph`: source, chunk, claim, draft, media, eval, approval, and publication dependencies.
- `state_transition_release_gate`: initial world state, dependency graph, affected objects, predicted state deltas, invalidated approvals/evals, stale dependencies, transition evals, forbidden side effects, observed outcome capture, rollback, and incident feedback before routes mutate production state.

## Route Promotion Rule

A route cannot become canon or production-ready unless:

- the route has an agent justification or is explicitly marked non-agentic;
- the selected workflow pattern and rejected simpler alternatives are recorded;
- agentic complexity is backed by an eval or trace-based gate;
- the route declares its task environment and performance measure;
- autonomous or agentic promotion passes an `agent_environment_planning_release_gate`;
- state-changing workflow actions declare preconditions, effects, and rollback policy;
- information-gathering actions are linked to uncertainty that can affect the route decision;
- graph changes include typed edges and schemas;
- remote/specialist agent calls include card version/hash, selected skill, task lifecycle, auth scope, and fallback policy;
- long-running routes declare session persistence, resume triggers, idempotency behavior, and terminal-state handling;
- routes declare checkpoint persistence mode, replay/fork policy, memory scopes, write permissions, consolidation policy, and interrupt handling;
- tool permissions and approval requirements are declared;
- model-facing tool interface tests exist for tool-using routes;
- trust boundaries and redaction policy are declared;
- collaborative, personalized, privacy-sensitive, social-facing, or high-agency routes pass `human_centered_route_release_gate`;
- reward-learning, high-budget reasoning, world-model planning, or cross-task feedback reuse changes pass `reward_reasoning_world_model_release_gate`, including training-trace coverage, simulated rollout records, model error budgets, receding-horizon planning traces, and terminal-value estimator caveats when a world model influences actions;
- eval datasets cover final outputs and workflow traces;
- latest eval run is attached;
- rollback path is defined.
- state-changing actions declare predicted transitions, stale dependencies, and rollback policy.

## Agent Studio Design Implications

- The route editor should expose topology and trust boundaries, not only prompt text.
- The route ledger should reject untyped graph edges for tool-using workflows.
- Reviewers should be able to inspect why a route is agentic, what simpler alternatives failed, and which evals justify the topology.
- Trace grading should become the primary debugging path for multi-agent route changes.
- Source-backed content routes must pin source snapshot, retrieval index, graph schema, and eval suite before release.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.

- [[../../02-lectures/stanford/cs25-generalist-agents-open-ended-worlds]] - Stanford CS25, "Generalist Agents in Open-Ended Worlds" ([YouTube](https://www.youtube.com/watch?v=wwQ1LQA3RCU)).
- [[../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
- [[../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
