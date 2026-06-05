# Harness Design for Long-Running Application Development

**Source:** Anthropic Engineering Blog, Mar 24, 2026
**Author:** Prithvi Rajasekaran (Anthropic Labs)
**URL:** https://www.anthropic.com/engineering/harness-design-long-running-apps

## Core Thesis

GAN-inspired multi-agent architecture (generator + evaluator) dramatically outperforms single-agent systems for long-running coding tasks, though at 20x+ the cost.

## The Two Failure Modes

1. **Loss of coherence** on lengthy tasks as context window fills + "context anxiety" (model wraps up prematurely approaching perceived context limit)
2. **Self-evaluation leniency** — agents confidently praise their own work even when quality is mediocre

## Context Resets vs. Compaction

| Technique | What it does | When to use |
|---|---|---|
| Compaction | Summarize conversation in place, same agent continues | Mild context issues, continuity matters |
| Context reset | Tear down session, rebuild from hand-off file | Severe context anxiety, need clean slate |

Sonnet 4.5 needed resets. Opus 4.5 largely eliminated the behavior.

## GAN-Inspired Generator-Evaluator Architecture

### Frontend Design Application

**Four grading criteria (weighted by importance):**

1. **Design quality** (heaviest) — coherent whole vs collection of parts, distinct mood/identity
2. **Originality** — custom decisions vs template layouts/stock components/"AI slop" (purple gradients over white cards)
3. **Craft** — typography, spacing, color harmony, contrast (baseline competence check)
4. **Functionality** — usability independent of aesthetics

**Feedback loop:** Generator creates → Evaluator uses Playwright MCP to interact with live page → scores each criterion + detailed critique → generator refines or pivots

**Key findings:**
- Evaluator actively navigates page (not static screenshot scoring)
- 5-15 iterations per generation, each pushing toward more distinctive design
- Generator makes strategic decision: refine current direction or pivot
- NOT always linear — sometimes middle iteration beats final
- Including aspirational phrasing ("museum quality") steers character of output

### Full-Stack Coding Application

**Three-agent architecture:**

1. **Planner** — Takes 1-4 sentence prompt → full product spec (ambitious scope, high-level, avoid cascading errors from over-specifying)
2. **Generator** — Works in sprints, one feature at a time from spec (React/Vite/FastAPI/SQLite stack), self-evaluates each sprint
3. **Evaluator** — Uses Playwright MCP to click through running app, tests UI features/API endpoints/DB state, grades each sprint against hard thresholds

**Sprint contract** — Before each sprint, generator and evaluator negotiate what "done" looks like. Generator proposes → evaluator reviews → iterate until agreed. Communication via files.

**Results:** Solo = 20min/$9, full harness = 6hr/$200. Harness produced working game with AI-assisted features; solo produced broken game.

**Evaluator effectiveness:** Sprint 3 alone had 27 criteria covering the level editor. Findings were "specific enough to act on without extra investigation."

## Operational Takeaways

- **Separate generation from evaluation** — tuning a skeptical evaluator is far easier than making a generator critical of its own work
- **Sprint contracts** prevent scope drift before code is written
- **Playwright MCP** for evaluator to interact with real running app
- **File-based communication** between agents (write file → read file → respond)
- **Hard thresholds** for each criterion — if one falls below, sprint fails
- Cost: harness was 20x more than solo but produced working vs broken output