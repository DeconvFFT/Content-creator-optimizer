# Demystifying Evals for AI Agents

**Source:** Anthropic Engineering Blog, Jan 9, 2026
**URL:** https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents

## Core Thesis

Agent evaluations are essential for shipping confidently, catching issues before production, and avoiding reactive "guess and check" debugging loops. Evals compound in value over the agent lifecycle.

## Key Vocabulary

| Term | Definition |
|---|---|
| Task | A single test with defined inputs and success criteria |
| Trial | One attempt at a task (multiple trials needed due to non-determinism) |
| Grader | Logic that scores some aspect of agent performance |
| Transcript (trace) | Complete record of a trial (outputs, tool calls, reasoning) |
| Outcome | Final state in the environment (not what the agent *says* but what *happened*) |
| Evaluation harness | Infrastructure that runs evals end-to-end |
| Agent harness (scaffold) | System enabling model to act as agent (harness + model = agent) |
| Eval suite | Collection of tasks for specific capabilities or behaviors |

## Types of Graders

### Code-Based Graders
- **Methods:** String match, binary tests (fail-to-pass, pass-to-pass), static analysis (lint, type, security), outcome verification, tool calls verification, transcript analysis
- **Strengths:** Fast, cheap, objective, reproducible, easy to debug
- **Weaknesses:** Brittle to valid variations, lacking nuance, limited for subjective tasks

### Model-Based Graders
- **Methods:** Rubric-based scoring, natural language assertions, pairwise comparison, reference-based evaluation, multi-judge consensus
- **Strengths:** Flexible, scalable, captures nuance, handles open-ended output
- **Weaknesses:** Non-deterministic, more expensive, requires calibration with human graders

### Human Graders
- **Methods:** SME review, crowdsourced judgment, spot-check sampling, A/B testing, inter-annotator agreement
- **Strengths:** Gold standard quality, matches expert user judgment, calibrates model-based graders
- **Weaknesses:** Expensive, slow, needs access to experts at scale

## Capability vs. Regression Evals

| Type | Question | Pass Rate | Purpose |
|---|---|---|---|
| Capability | "What can this agent do well?" | Start low, hill-climb | Push boundaries |
| Regression | "Does it still handle old tasks?" | Near 100% | Protect against backsliding |

After launch, capability evals with high pass rates "graduate" into regression suites.

## Agent-Specific Eval Techniques

### Coding Agents
- **Deterministic graders** are natural: does code run, do tests pass?
- SWE-bench Verified: GitHub issues, grade by running test suite (fix without breaking existing tests)
- Terminal-Bench: end-to-end technical tasks (building kernel from source, training ML model)
- Grade both outcome AND transcript: heuristics for code quality, rubric for tool-calling behavior
- **Example eval YAML:** unit tests + LLM rubric + static analysis + state check + tool call verification

### Conversational Agents
- Success is multidimensional: ticket resolved (state check), <10 turns (transcript constraint), tone appropriate (LLM rubric)
- Often need a second LLM to simulate the user
- τ-Bench/τ2-Bench: simulate multi-turn interactions across retail, airline booking domains
- **Example eval YAML:** LLM rubric (empathy, clarity, groundedness) + state check + tool calls required + max_turns

### Research Agents
- Quality is relative to context (market scan vs scientific report)
- Combine: groundedness checks (claims supported by sources), coverage checks (key facts included), source quality checks
- Experts may disagree on "comprehensive"
- LLM rubrics need frequent calibration against human judgment

### Computer Use Agents
- Run in real or sandboxed environment
- WebArena: URL + page state checks + backend state verification
- OSWorld: file system state, app configs, DB contents, UI element properties
- **Token efficiency balance:** DOM-based (fast, token-heavy) vs screenshot-based (slower, token-efficient)

## Thinking About Non-Determinism

- `pass@k`: likelihood agent gets right in k attempts
- Run multiple trials (3-10+) for stable results
- `pass@1` measures reliability; `pass@k` measures capability

## Operational Takeaways

- Start with code-based graders (cheap, objective)
- Add LLM graders for nuance, calibrate against humans
- Capability evals first, then regression evals to protect wins
- Always grade OUTCOME, not just transcript (what happened vs what agent said)
- Track token usage, latency, cost per task as built-in metrics
- Evals are your highest-bandwidth communication channel between product and research teams