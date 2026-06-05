# Core Principles — Harness Engineering

Synthesis of all 5 sources: Anthropic (×4) + Addy Osmani + Viv Trivedy framing.

## The Fundamental Equation

```
Agent = Model(s) + Harness
```

The harness is EVERYTHING that isn't the model: prompts, tools, context policies, hooks, sandboxes, subagents, feedback loops, recovery paths. If you're not the model provider, you're a harness engineer.

## The Ratchet Principle

Every mistake becomes a permanent signal. When an agent fails, engineer a solution so it never makes that mistake again. Every line in AGENTS.md should trace to a specific past failure.

## Separation of Concerns

### Generator ≠ Evaluator
Self-evaluation is unreliable — agents skew positive on their own work. **Always separate** the agent doing the work from the agent judging it. Tuning a skeptical evaluator is far easier than making a generator critical of its own work.

### Planner ≠ Executor
Don't let the agent plan AND execute in the same context. The planner creates the spec at high altitude (avoid cascading errors from over-specification). The executor works one feature at a time.

## Context Management Hierarchy

| Technique | Cost | When | Source |
|---|---|---|---|
| Tool result clearing | Lowest | Default first step | Context Engineering |
| Compaction | Low | Continuous flow | Context Engineering |
| Structured note-taking | Medium | Milestone-based work | Context Engineering |
| Context reset | High | Severe anxiety, clean break needed | Long-Running Apps |
| Ralph loop | Medium | Multi-session continuation | Addy Osmani |

## The Verification Stack

1. **Code-based graders** (cheap, objective) — unit tests, lint, typecheck
2. **Model-based graders** (flexible, nuanced) — rubrics for subjective quality
3. **Human calibration** — spot-check model graders periodically
4. **Sprint contracts** — negotiate what "done" means before coding
5. **End-to-end testing** — Playwright/browser automation against real running app

## Harness Component Checklist

| Component | What | Why |
|---|---|---|
| Filesystem | Workspace for read/write/coordinate | Most foundational primitive |
| Git | Versioning + session handoff context | Track progress, roll back errors |
| AGENTS.md | Root-level rulebook | Injected every turn, highest leverage |
| Hooks | Lifecycle enforcement | Success silent, failures verbose |
| Sandbox | Isolated execution | Safe bash, pre-installed runtimes |
| Memory | AGENTS.md edits = continual learning | Cross-session knowledge |
| Skills | Progressive disclosure | Don't load every tool at startup |

## When to Use Each Architecture

| Task Type | Best Approach |
|---|---|
| Single-session coding | Solo agent with good AGENTS.md + hooks |
| Multi-session coding | Initializer + coding agent + feature list JSON |
| Long-running full-stack | Planner → Generator → Evaluator triad |
| Design/subjective quality | Generator-Evaluator loop (GAN-inspired) |
| Research/synthesis | Sub-agent exploration + main agent synthesis |
| Conversational | Single agent + simulated user + LLM rubric |

## Key Token Minimization Rules (Cross-Cutting)

1. Pre-extract context to filesystem, not in subagent prompts
2. Static system prompts immutable across sessions (max cache hits)
3. Keep AGENTS.md under 60 lines
4. Ten focused tools beat fifty with overlap
5. Tool result clearing before compaction
6. Sprint contracts prevent expensive rework
7. Strip reasoning_content from multi-turn message history
8. Just-in-time retrieval (file paths) vs loading everything upfront