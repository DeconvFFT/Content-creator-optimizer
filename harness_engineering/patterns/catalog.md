# Harness Patterns Catalog

Reusable patterns extracted from all sources.

## 1. Generator-Evaluator Loop (GAN-Inspired)

**Source:** Harness Design for Long-Running Apps (Anthropic Labs)
**Best for:** Subjective quality tasks (design, creative coding)

Generator produces output → Evaluator interacts with output in real environment → scores against rubric → generator refines or pivots.

**Key details:**
- Evaluator should use real interaction tools (Playwright MCP for web)
- 5-15 iterations typical
- Generator makes strategic decision each cycle: refine or pivot
- Aspirational rubric language shapes output character

## 2. Planner → Generator → Evaluator Triad

**Source:** Harness Design for Long-Running Apps (Anthropic Labs)
**Best for:** Full-stack application development

Planner expands 1-4 sentence prompt into spec → Generator works one sprint at a time → Evaluator tests against contract.

**Key details:**
- Sprint contract negotiated before each sprint
- Communication via filesystem
- Hard thresholds on criteria (fail if below)
- Avoids over-specification by planner (stays at high altitude)

## 3. Initializer + Coding Agent

**Source:** Effective Harnesses for Long-Running Agents (Anthropic)
**Best for:** Multi-session web app development

Initializer creates seed environment + feature list → Every subsequent coding agent session picks one feature, works incrementally, leaves clean state.

**Key details:**
- Feature list in JSON (all initially "failing")
- Each session: pwd → git log → progress file → feature list → basic sanity test
- Agent self-verifies before marking feature "passing"
- init.sh for development server startup

## 4. Ralph Loop

**Source:** Addy Osmani
**Best for:** Multi-session continuation

Hook intercepts agent's attempt to exit → re-injects original prompt → agent continues in fresh context. Simple but effective.

**Key details:**
- Each iteration starts clean but reads state from previous via filesystem
- Replaces need for manual session management
- Contrast with context reset: Ralph loop is automated

## 5. Sprint Contract Pattern

**Source:** Harness Design for Long-Running Apps
**Best for:** Preventing scope drift

Before code is written, generator proposes what it will build and how success will be verified. Evaluator reviews and iterates until agreement.

**Key details:**
- File-based communication (write/read/respond)
- Caught more scope drift than any prompt change
- Ensures generator builds the right thing before coding

## 6. Just-in-Time Context Retrieval

**Source:** Context Engineering (Anthropic)
**Best for:** Token efficiency

Agent maintains lightweight identifiers (file paths, stored queries) and uses tools to dynamically load data. Mirrors human cognition.

**Key details:**
- Hybrid: pre-retrieve some data + autonomous exploration
- Progressive disclosure through exploration
- File sizes → complexity hints, naming conventions → purpose, timestamps → relevance

## 7. Compaction with Tool Result Clearing

**Source:** Context Engineering + Addy Osmani
**Best for:** First-line context management

Safest lightest-touch compaction: clear tool call results from history. Then keep head/tail of large output, offload full text to filesystem.

## 8. Sprint-Based Evaluator (Playwright End-to-End)

**Source:** Harness Design for Long-Running Apps
**Best for:** Verifying full-stack apps

Evaluator uses Playwright MCP to click through running app like a user. Tests UI, API endpoints, DB state. Sprint 3 had 27 criteria.

## 9. Silent Success / Verbose Failure Hooks

**Source:** Addy Osmani / HumanLayer
**Best for:** Cheap verification loops

If typecheck passes → agent hears nothing. If it fails → error text injected into loop for self-correction. Feedback loop free in common case.

## 10. Capability-to-Regression Pipeline

**Source:** Demystifying Evals (Anthropic)
**Best for:** Long-term quality maintenance

Capability evals start with low pass rate → hill-climb → when pass rate high enough → graduate to regression suite. Protects against backsliding.