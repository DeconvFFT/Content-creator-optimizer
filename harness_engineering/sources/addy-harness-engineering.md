# Agent Harness Engineering (Addy Osmani)

**Source:** addyosmani.com, April 19, 2026
**URL:** https://addyosmani.com/blog/agent-harness-engineering/

## Core Thesis

A coding agent = model + harness. A decent model with a great harness beats a great model with a bad harness. The interesting engineering is in designing the scaffolding, not picking the model.

## Fundamental Equation

```
coding agent = AI model(s) + harness
```

**Agent = Model + Harness** (Viv Trivedy's formulation). If you're not the model, you're the harness.

## What a Harness Includes

- System prompts, CLAUDE.md, AGENTS.md, skill files, subagent prompts
- Tools, skills, MCP servers, and their descriptions
- Bundled infrastructure (filesystem, sandbox, browser)
- Orchestration logic (subagent spawning, handoffs, model routing)
- Hooks and middleware for deterministic execution (compaction, continuation, lint checks)
- Observability (logs, traces, cost and latency metering)

## The "Skill Issue" Reframe

When the agent does something dumb, the default reaction is "wait for the next model version." The harness-engineering mindset rejects that. The failure is usually legible and fixable via harness changes:

| Failure | Harness Fix |
|---|---|
| Agent didn't know a convention | Add to AGENTS.md |
| Agent ran destructive command | Add hook that blocks it |
| Agent got lost in 40-step task | Split into planner + executor |
| Agent kept "finishing" broken code | Wire typecheck back-pressure into loop |

**Key data point:** Viv's team moved a coding agent from Top 30 to Top 5 on Terminal Bench 2.0 by changing ONLY the harness. Same model.

## The Ratchet: Every Mistake Becomes a Rule

> You only add constraints when you've seen a real failure. You only remove them when a capable model has made them redundant.

Every line in a good AGENTS.md should be traceable back to a specific thing that went wrong.

## Harness Primitives

### Filesystem and Git (Durable State)
The most foundational primitive. Gives agent workspace to read/write/coordinate. Git gives versioning for free.

### Bash and Code Execution (General-Purpose Tool)
The main agent loop is ReAct: reason → tool call → observe → repeat. For actions you haven't pre-built, give the agent bash. "Teaching someone to use a single kitchen gadget vs handing them a kitchen."

### Sandboxes
Isolated execution environments. Pre-installed runtimes, packages, Git, test CLIs, headless browser. Allow-list commands, enforce network isolation.

### Memory and Search (Continual Learning)
AGENTS.md files get injected every start. Agent edits file → harness reloads it → knowledge carries across sessions. Crude but effective continual learning.

### Battling Context Rot
Three techniques:
1. **Compaction** — summarize when window gets full
2. **Tool-call offloading** — keep head/tail of large outputs, offload full text to filesystem
3. **Skills with progressive disclosure** — only load tools when task calls for them

Addy also endorses Anthropic's **context resets** for really long jobs.

### Long-Horizon Execution

**Ralph Loop:** Hook intercepts agent's attempt to exit → re-injects original prompt into fresh context → agent continues against completion goal.

**Planning:** Model decomposes goal into steps → writes plan file → agent checks work via self-verification (hooks run test suite, loop failures back).

**Planner/Generator/Evaluator splits** — Addy endorses Anthropic's finding that separating generation from evaluation outperforms self-evaluation.

### Hooks — The Enforcement Layer
Hooks run at specific lifecycle points (before tool call, after edit, before commit, on session start). Right place for things the agent should never forget.

**Principle:** Success is silent, failures are verbose.

### AGENTS.md Best Practices
- Keep it short (HumanLayer keeps theirs under 60 lines)
- Earn each line — trace to specific past failure or hard constraint
- Ratchet, don't brainstorm
- Same discipline for tools: 10 focused tools > 50 overlapping ones

## Harnesses Don't Shrink, They Move

As models improve, the space of interesting harness combinations doesn't shrink — it moves. The anxiety scaffolding goes away, but in its place you need multi-day memory policies, specialized agents, design quality evaluators.

> "Every component in a harness encodes an assumption about what the model can't do on its own."

## Model-Harness Training Loop

Models are post-trained with specific harnesses in the loop. Opus 4.6 feels different inside Claude Code vs inside someone else's harness. Co-training creates overfitting.

**Practical implication:** The "best" harness isn't the one the model was trained inside; it's the one designed for your task.

## Harness-as-a-Service (HaaS)

We're moving from building on LLM APIs (completion) to building on harness APIs (runtime). Claude Agent SDK, Codex SDK, OpenAI Agents SDK all point in the same direction.