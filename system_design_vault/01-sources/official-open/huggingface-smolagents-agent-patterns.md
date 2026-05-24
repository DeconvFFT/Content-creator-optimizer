---
type: official-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_class: official_source_note
rights_status: official_public
source_urls:
  - https://huggingface.co/docs/smolagents/index
  - https://huggingface.co/docs/smolagents/conceptual_guides/intro_agents
  - https://huggingface.co/docs/smolagents/conceptual_guides/react
  - https://huggingface.co/docs/smolagents/en/reference/agents
  - https://huggingface.co/docs/smolagents/tutorials/building_good_agents
  - https://huggingface.co/docs/smolagents/tutorials/inspect_runs
  - https://huggingface.co/docs/smolagents/tutorials/tools
  - https://huggingface.co/docs/smolagents/tutorials/secure_code_execution
  - https://huggingface.co/docs/smolagents/tutorials/memory
  - https://huggingface.co/docs/smolagents/examples/rag
  - https://huggingface.co/docs/smolagents/examples/multiagents
  - https://huggingface.co/docs/smolagents/examples/plan_customization
---

# Hugging Face Smolagents Agent Patterns

## Direct-Read Scope

This note is original synthesis from the official Hugging Face smolagents documentation and Hugging Face Agents Course entry points. It covers the current smolagents documentation pages for agent concepts, multi-step/ReAct execution, CodeAgent and ToolCallingAgent API behavior, tool design, MCP tools, secure code execution, run telemetry, memory inspection, agentic RAG, hierarchical multi-agent orchestration, and human-in-the-loop plan customization.

No raw source text, copied code blocks, transcripts, or long excerpts are stored here.

Current-doc check on 2026-05-18: smolagents docs identify v1.25.0 as the latest listed version and still position the library as a small open-source Python agent framework with first-class `CodeAgent`, `ToolCallingAgent`, Hub/Space tools, MCP tools, multimodal inputs, and model-agnostic backends. The docs still define agency as a spectrum of LLM control over workflow, describe `MultiStepAgent` as a ReAct loop with memory, parsed actions, execution, observations, and callbacks, and warn that local Python sandboxes cannot be treated as complete security boundaries. The official tool docs also now make structured MCP output support explicit, with `structured_output` still opt-in for backwards compatibility.

## Core Reading

Smolagents frames agency as a spectrum: deterministic code, routers, tool calls, multi-step loops, multi-agent delegation, and code-writing agents give the model increasing control over program flow. The important Agent Studio lesson is not "use smolagents"; it is to make agency level explicit and to prefer the simplest workflow that solves the task.

The library's agent model centers on a ReAct-style loop. A run starts with system/task memory, writes memory into model-readable messages, asks a model for an action, parses that action as either code or JSON tool calls, executes it, records observations/errors, then optionally repeats. Planning steps and callbacks can interrupt or revise the loop. This maps cleanly to Agent Studio's route graph: each loop step should be a durable event with model input, action proposal, tool execution boundary, observation, error, callback decision, and stop condition.

Smolagents exposes two important route shapes:

- `CodeAgent`: model actions are executable Python snippets. This is expressive for composition, loops, object handling, and computation-heavy routes.
- `ToolCallingAgent`: model actions are structured tool calls. This is easier to constrain when the workflow requires simple side-effect boundaries, browser waits, or provider-standard tool semantics.

Agent Studio should treat this as a design choice, not a library preference. Code-style action routes need stronger sandbox, import, secret, filesystem, network, and output-capture policies. JSON/tool-call routes need strict schemas, ergonomic descriptions, validation, and trace-gradeable tool-call items.

## Best-Practice Implications

Hugging Face's "building good agents" guidance reinforces the same rule found in Anthropic and OpenAI sources: reduce unnecessary LLM-controlled steps. Combine deterministic substeps into one well-scoped tool when that reduces calls, latency, and error exposure. Prefer deterministic functions for known logic, and reserve agent loops for ambiguity, tool choice, recovery, or iterative evidence gathering.

Tool design is a model-facing interface. Poor parameter names, ambiguous date formats, silent failures, opaque outputs, and missing error detail force the model to infer tool behavior. A production tool should expose clear argument constraints, meaningful error messages, concise structured outputs, and enough observations for self-repair. Agent Studio should therefore store tool descriptions, output schemas, example failures, and model-facing usability tests as release artifacts.

MCP integration makes tool sourcing dynamic. Smolagents can import tools from stdio or streamable HTTP MCP servers, and its docs warn that MCP servers must be trusted because local transports can execute code and remote transports still expose model-visible capabilities. For Agent Studio this means MCP imports are not just runtime convenience: they are governed capability changes with source, transport, auth, trustedness, output schema, and disconnect lifecycle.

Structured tool outputs matter. When an MCP tool or local tool has an output schema, the agent can reason over result shape before and after the call. Agent Studio should not flatten every tool response into text. It should preserve structured tool outputs, validation status, content artifacts, and error class in the trace.

## Security And Isolation

Code agents are powerful because code is expressive, but that also turns generated actions into executable risk. The secure-execution docs identify local code execution, prompt injection, public-agent abuse, supply-chain compromise, filesystem damage, credential exposure, network abuse, and cloud/API misuse as surfaces that have to be controlled outside the prompt.

Agent Studio should require a `code_execution_policy` before any route can execute model-written code. At minimum, the policy should declare executor type, filesystem scope, network policy, authorized imports, secret access, package installation allowance, wall-clock and token limits, cleanup behavior, trace capture, and human approval requirements for side effects.

Sandbox choice changes route topology. Local execution may be acceptable for private offline analysis with no secrets and no write surface. Remote sandboxes such as E2B, Modal, Blaxel, Docker, or equivalent isolation make more sense for untrusted browsing, public inputs, or code-producing agents, but multi-agent setups can require different credential-placement and execution-boundary decisions. The route release should state where the model call happens, where generated code runs, which secrets are present, and what crosses the boundary.

The Hub/Space/tool-loading path is another supply-chain boundary. Loading agents or tools from a hub can execute downloaded code. Agent Studio should treat external tool packages, Spaces-as-tools, and imported agent definitions as dependencies with provenance, hash/revision, review state, and allowed runtime scope.

## Memory, Replay, And HITL

Smolagents memory records system prompts, tasks, action steps, planning steps, observations, errors, and optionally rich media. It supports replay, full/succinct step extraction, callback-driven memory mutation, and one-step-at-a-time execution.

For Agent Studio, this confirms that memory is not a chat transcript blob. A durable run should distinguish:

- system/task memory;
- planning steps;
- action proposals;
- tool executions and observations;
- error observations;
- callback decisions;
- memory mutations;
- media observations;
- final-answer checks.

HITL plan customization is implemented through planning callbacks that pause after a plan, let a human approve/modify/cancel, then resume with memory preserved. Agent Studio should model this as a first-class approval edge. The user should be able to inspect a plan, edit it, cancel execution, and resume without losing the trace that explains why the plan changed.

## Agentic RAG And Multi-Agent Routing

The agentic RAG example separates rigid one-shot retrieval from an agent equipped with retrieval tools. The useful pattern is iterative query reformulation, multiple retrieval attempts, self-critique, and synthesis across retrieved evidence. This is valuable for Agent Studio research routes, but it raises eval requirements: record query rewrites, retrieval attempts, retrieved candidates, rejected evidence, stop criteria, and final citation mapping.

The multi-agent example uses a manager agent that delegates to a web-search agent through `managed_agents`. This is a hierarchical pattern, not a decentralized swarm. The child agent needs a name and description so the manager can call it correctly, and the manager should be the route that owns planning and synthesis.

Agent Studio should prefer hierarchical managed-agent routing for research and content-studio work because it creates a clear authority chain: manager owns task decomposition and final synthesis, specialist owns bounded tool execution, and every delegation can be traced as a task contract. Multi-agent routes should not be promoted unless the trace proves the specialist split reduced context/tool confusion or improved eval results.

## Observability

Smolagents supports OpenTelemetry instrumentation through OpenInference integrations and examples for Phoenix and Langfuse. The docs emphasize that agent runs are hard to inspect because unpredictable workflows generate large, noisy logs and many recoverable model/tool errors.

Agent Studio should store both high-level route traces and step-level agent telemetry. The trace should preserve enough to debug tool selection, recovery, and plan changes, while content-capture policy controls sensitive prompts, screenshots, retrieved chunks, and tool outputs. Span records should distinguish model calls, agent invocations, tool calls, managed-agent calls, code-executor runs, and final-answer checks.

## Agent Studio Datastore Additions

- `agent_agency_level`: route, selected agency level, rejected simpler level, reason, risk/cost burden, and eval evidence.
- `agent_loop_step`: run, step number, memory input refs, model output ref, parsed action type, observation refs, error refs, callback refs, and terminal flag.
- `agent_action_format_policy`: code, JSON tool call, provider-native tool call, or hybrid action format with rationale and constraints.
- `code_execution_policy`: executor type, filesystem/network/secret/import/package scopes, time/resource limits, cleanup behavior, and approval policy.
- `code_execution_run`: generated code hash, executor/sandbox ref, input/output artifacts, allowed imports, stdout/stderr refs, error class, cleanup state, and side-effect refs.
- `agent_memory_step`: system/task/planning/action/observation/error/media/final-answer memory record with redaction and retention policy.
- `agent_memory_mutation`: callback or human edit that changed memory, including before/after refs, actor, reason, and replay impact.
- `planning_interrupt_record`: plan, trigger step, human decision, modifications, cancel/resume state, and resulting memory refs.
- `managed_agent_call`: manager route, specialist route, delegated task contract, child run ref, returned summary/artifacts, failure policy, and synthesis decision.
- `agent_final_answer_check`: validation function/rubric, checked artifact, result, failure reason, recovery action, and release gate link.
- `agent_telemetry_config`: OpenTelemetry/OpenInference exporter, backend, sampled span classes, content-capture policy, retention, and redaction review.
- `external_tool_dependency`: Hub Space, package, remote tool, MCP server, or imported agent dependency with source, revision/hash, trust tier, review state, and allowed runtime scope.

## Agent Action Runtime Release Gate

Promote a smolagents-style route only after an `agent_action_runtime_release_gate` is approved. The gate should bind route ID, selected agency level, rejected simpler workflow, action format, framework/library version, model/provider binding, tool list snapshot, tool description and schema tests, MCP server refs, structured-output mode, Hub/Space/imported dependency revisions, code-execution policy, sandbox profile, authorized imports, network/filesystem/secret policy, memory schema, callback and interrupt policy, managed-agent task contracts, agentic-RAG retrieval trace policy, telemetry/exporter config, content-capture/redaction policy, eval evidence, failure/retry policy, and rollback target.

The gate is separate from generic route release because changing action format, tool descriptions, structured-output defaults, authorized imports, memory rewriting callbacks, or manager/specialist descriptions can change model behavior without changing the user-facing task.

## Design Commitments

- Agent Studio route proposals must declare agency level and simpler rejected alternatives.
- Smolagents-style routes should be blocked until an agent action runtime release gate proves the framework version, action format, tool/MCP/Hub dependency surface, memory/callback behavior, sandbox posture, telemetry policy, eval evidence, and rollback target.
- Code-action routes are blocked until a code-execution policy and sandbox evidence exist.
- Tool descriptions and output schemas are release artifacts and need model-facing usability tests.
- MCP and Hub-imported tools require capability snapshots, trusted-source review, and structured-output validation before exposure to a route.
- HITL plan review should preserve memory and resume state rather than restart the run.
- Agentic RAG traces should store query rewrites, retrieval attempts, rejected evidence, and citation mapping.
- Hierarchical multi-agent routes need managed-agent task contracts and measured benefit over a single-agent route.
- Agent observability should use OTel-aligned spans but respect trace content policy for private sources and screenshots.
