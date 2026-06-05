---
type: pattern-synthesis
source: claude-code-dynamic-workflows
author: "Thariq Shihipar & Sid Bidasaria (Anthropic)"
source_url: "https://x.com/trq212/status/2061907337154367865"
published: 2026-06-02
status: canon_ready
tags: [harness-engineering, dynamic-workflows, claude-code, subagent-orchestration, patterns]
related:
  - "[[../agent-systems/long-running-agent-patterns]]"
  - "[[../../02-books/llm-engineers-handbook/chapters/1-llm-twin-concept-and-architecture]]"
  - "[[../evaluation/agent-evaluation-frameworks]]"
---

# Dynamic Workflows in Claude Code: A Harness Engineering Deep Dive

> **TL;DR:** Claude Code's new dynamic workflows let Claude write a custom JavaScript harness on the fly — spawning subagents in isolated worktrees, orchestrating parallel tasks, and composing patterns (fan-out, tournament, adversarial verification). This is harness engineering in practice: the agent builds its own execution environment dynamically per task.

**Source:** [X Article by Thariq Shihipar (Anthropic)](https://x.com/trq212/status/2061907337154367865)
**PDF backup:** `assets/dynamic-workflows-article.pdf`

---

## 1. The Core Idea

Dynamic workflows let Claude Code write a **JavaScript file with special functions** that spawn and coordinate subagents. Instead of a fixed harness, Claude creates one custom-built for the task.

**Key insight:** The agent writes its own harness. This is the logical endpoint of harness engineering — the execution environment is generated dynamically, not predefined.

### What a Workflow JS File Can Do

- Spawn subagents with isolated context windows
- Route subagents to different models (cheap vs smart)
- Run subagents in separate worktrees (full isolation)
- Standard JS: JSON, Math, Array for data processing
- Resume from interruptions (context is saved)

---

## 2. Why Dynamic Workflows Exist: Three Failure Modes

The default single-context harness breaks down on long/complex tasks due to:

| Failure Mode | What Happens | Why |
|---|---|---|
| **Agentic Laziness** | Agent stops after partial progress (e.g., 20/50 items in a review) | Single context degrades over long runs |
| **Self-Preferential Bias** | Agent prefers its own results when asked to verify them | No external judge — same agent grades itself |
| **Goal Drift** | Gradual loss of original objective across turns/compaction | Each summarization step is lossy; "don't do X" constraints get dropped |

**Dynamic workflows fix this** by orchestrating separate agents with their own context windows and focused, isolated goals. Each subagent has a clean task boundary.

---

## 3. Dynamic vs Static Workflows

| Aspect | Static Workflow | Dynamic Workflow |
|---|---|---|
| Who writes it | Human (Claude Agent SDK or `claude -p`) | Claude autonomously (Opus 4.8+) |
| Generality | Generic — must handle all edge cases | Custom — tailor-made for the exact task |
| Complexity | Fixed structure | Composes patterns on the fly |
| Use case | Known, repetitive pipelines | Novel, complex, one-off tasks |

**Claude Opus 4.8** is the key enabler — intelligent enough to write a custom harness per use case.

---

## 4. Harness Patterns (The Core Catalog)

These are the composition patterns Claude uses to build workflows. Any agent building subagent orchestrations should know these:

### 4.1 Classify-and-Act
```
[Input] → Classifier Agent → Action Agent A
                           → Action Agent B
                           → Action Agent C
```
Use a classifier to decide task type, route to specialized agents. Also works as an output classifier.

**When to use:** Variable tasks where routing depends on content (triage, support, model selection)

### 4.2 Fan-out-and-Synthesize ⭐ (Most Common)
```
[Big Task]
     ↓
[Split into N steps]
     ↓
┌─ Agent1 ─┐  ┌─ Agent2 ─┐  ┌─ AgentN ─┐
│ step 1   │  │ step 2   │  │ step N   │  ← parallel, isolated contexts
└──────────┘  └──────────┘  └──────────┘
     ↓              ↓            ↓
     └────────Synthesizer────────┘
           [Merged result]
```
The synthesizer is a **barrier** — waits for all fan-out agents, then merges structured outputs.

**When to use:** Large numbers of small independent steps (migrations, sorting 1000 items, batch verification)

### 4.3 Adversarial Verification
```
Agent A (produces output) ←→ Agent B (adversarially verifies against rubric)
```
For each spawned agent, run a separate agent to adversarially verify its output. Prevents self-preferential bias.

**When to use:** Any output that needs quality assurance (code review, fact checking, rule adherence)

### 4.4 Generate-and-Filter
```
Generate N ideas → Filter by rubric → Dedupe → Return highest-quality
```
Generate broadly, then filter aggressively.

**When to use:** Brainstorming, design exploration, naming, creative tasks

### 4.5 Tournament
```
Spawn N agents → Each attempts task with different approach
              → Pairwise judging by rubric agent
              → Winner emerges
```
Instead of dividing work, have agents **compete** on the same task. Judging is pairwise comparative (more reliable than absolute scoring).

**When to use:** Subjective evaluation (best name, best design, best approach), qualitative sorting

### 4.6 Loop-Until-Done
```
Loop: spawn agent → check stop condition → continue or exit
Stop conditions: no new findings, no more errors, rubric satisfied
```
For tasks with unknown work volume. Combined with `/loop` for continuous operation.

**When to use:** Bug reproduction, log analysis, continuous triage, monitoring

---

## 5. Use Cases (With Agent-Friendly Prompts)

Each use case includes a ready-to-use prompt pattern that any agent can adapt:

### 5.1 Migrations & Refactors
```
"Break this [refactor] into N independent steps. Spawn a subagent per step in its own worktree.
Have a review agent adversarially verify each change. Merge passing ones."
```
**Reference:** Bun rewrote Zig → Rust using this exact pattern (Jarred's X thread).

**Token tip:** Tell the agent "don't use resource-intensive commands" to maximize parallelism.

### 5.2 Deep Research
Fan-out web searches → fetch sources → adversarially verify claims → synthesize cited report.

Claude Code ships a built-in `/deep-research` skill using this pattern.

### 5.3 Deep Verification
```
"Identify all factual claims in this document. Spin off one subagent per claim to verify it.
Add a verification agent that checks each source subagent's source quality."
```
Works for blog posts, reports, technical documentation.

### 5.4 Sorting (1000+ Items)
Bucket-rank in parallel → merge → pairwise comparison for ties. Each comparison is its own agent — the deterministic loop holds the bracket, only the running order stays in context.

### 5.5 Memory & Rule Adherence
```
"Create one verifier agent per rule from CLAUDE.md. Add a skeptic persona to prevent false positives.
Also mine the last 50 sessions for recurring corrections, cluster them, adversarially verify each,
and distill survivors into CLAUDE.md."
```

### 5.6 Root-Cause Investigation
Spawn separate hypothesis agents from disjoint evidence sources (logs, files, data). Each hypothesis faces a panel of verifiers and refuters. **Structurally prevents self-preferential bias.**

**Non-code applications:** Sales analysis (why did sales drop?), data pipeline failures, post-mortems.

### 5.7 Triaging at Scale
```
Classify each item → dedupe against existing tracking → attempt fix or escalate.
Use quarantine: agents reading untrusted content can't take privileged actions.
Pair with /loop for continuous operation.
```

### 5.8 Model & Intelligence Routing
```
Classifier agent researches task complexity → routes to Sonnet (simple) or Opus (complex).
```
Useful before tasks with many tool calls. The classifier researches first (file count, codebase shape), then routes.

### 5.9 Evals
```
Spawn agents in worktrees → each runs the task → comparison agents grade outputs against rubric.
```
Lightweight evals for skills, prompts, or agent configurations.

---

## 6. When NOT to Use Dynamic Workflows

- **Most regular coding tasks** — the default harness is already optimal
- **Simple operations** — "does it really need more compute?"
- **Token-sensitive contexts** — dynamic workflows use significantly more tokens
- **Avoid over-engineering** — "most traditional coding tasks do not need a panel of 5 reviewers"

**Decision heuristic:** Ask yourself — does this task suffer from agentic laziness, self-preferential bias, or goal drift? If no, use the default harness.

---

## 7. Implementation Tips

### Prompting for Workflows
- Be specific about the pattern: "Use a fan-out-and-synthesize workflow..."
- Use trigger word **"ultracode"** to force Claude Code to create a workflow
- For small tasks: "Create a quick workflow" (adversarial review of a single assumption)

### Combining with Other Features
- `/goal` — set hard completion requirements
- `/loop` — repeat at intervals for ongoing tasks (triage, research, verification)

### Token Budgets
- Set explicit caps: "use 10k tokens" — limits the workflow's total token usage
- Workflows cost more than single-context — plan accordingly

### Saving & Sharing
- Press `s` in the workflow menu to save
- Files go to `~/.claude/workflows/`
- Distribute via skills: put JS files in skill folder, reference in SKILL.md
- For flexibility: prompt Claude to treat the workflow as a **template**, not a verbatim script

---

## 8. Harness Engineering Principles Derived

These are the broader harness-engineering takeaways any agent should internalize:

| Principle | How Dynamic Workflows Apply It |
|---|---|
| **Isolation** | Each subagent gets its own context window and optional worktree — no cross-contamination |
| **Clear task boundaries** | Fan-out-and-synthesize has a barrier that waits for all agents before merging |
| **Adversarial review** | Separate agent for production vs. verification prevents self-preferential bias |
| **Dynamic composition** | Patterns are composed on the fly, not hardcoded — the harness fits the task |
| **Resumability** | Interrupted workflows pick up where they left off — no wasted work |
| **Model routing** | Different subagents can use different models — don't waste Opus on simple lookups |
| **Resource awareness** | Token budgets and parallelism limits prevent resource exhaustion |

---

## 9. Source Context

- **Authors:** Thariq Shihipar and Sid Bidasaria, Technical Staff at Anthropic (Claude Code team)
- **Published:** 2026-06-02 on X (via X Articles feature)
- **Cross-reference:** Also available on [Claude Blog](https://anthropic.com/claude-code)
- **Full PDF:** `assets/dynamic-workflows-article.pdf` (10 pages)
- **Screenshot:** `assets/article-full.png`
- **Excalidraw diagrams:**
  - `assets/dynamic-workflow-patterns.excalidraw.md` — Fan-out, Adversarial, Tournament, Loop patterns
  - `assets/three-failure-modes.excalidraw.md` — Failure modes with causes and fixes
- **Codex-generated images (DALL-E via Codex CLI):**
  - `assets/codex-three-failure-modes.png` — Three failure modes diagram
  - `assets/codex-harness-patterns.png` — Harness patterns architecture overview
  - `assets/codex-agent-architecture.png` — Agent architecture visualization
- **Related patterns in this vault:**
  - `[[../agent-systems/long-running-agent-patterns]]` — Long-running agent architecture
  - `[[../evaluation/agent-evaluation-frameworks]]` — Evals methodology
  - `[[../../02-books/llm-engineers-handbook/chapters/1-llm-twin-concept-and-architecture]]` — Agent system design

---

## 10. Agent Quick Reference

**For any agent reading this note:** When tasked with a complex multi-step operation, ask:

1. Will this suffer from agentic laziness, self-preferential bias, or goal drift?
2. If yes → design a dynamic workflow using the patterns above
3. If no → stay in single-context (cheaper, faster)
4. For the workflow: pick the right pattern(s) from Section 4
5. Set a token budget and isolation level (worktree or no worktree)
6. Include adversarial verification for quality gates
7. Combine with `/goal` and `/loop` for persistent tasks

**Best practice templates (copy-paste ready):**

```
"Use a fan-out-and-synthesize workflow for this task. Split [X] into [N] parts,
spawn one agent per part, then merge results."

"Use an adversarial verification workflow. First [do X], then have a separate
agent verify the output against [rubric]."

"Use a tournament workflow. Spawn [N] agents, each using a different approach.
Compare results pairwise to pick the best."
```
