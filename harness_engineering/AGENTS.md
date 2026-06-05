# AGENTS.md — Harness Engineering Vault

This vault is a machine-first knowledge base for harness engineering. Every agent and subagent MUST follow the token efficiency and AGENTS.md best practices defined in the parent repo's AGENTS.md (at `/Users/saumyamehta/Gen AI/all-about-llms/AGENTS.md`).

Key rules:
- **Setup commands**: `uv run` for Python, `npm run` for frontend — do not guess
- **Token discipline**: state hypothesis before debugging, batch parallel work, compact subagent summaries (500-1000 chars)
- **Search first**: use search_files() over read_file() for code lookup — context is expensive
- **Narrowest test first**: never run full suite unless shared code changed
- **Subagents**: pass the parent AGENTS.md path in context and ensure they load domain-specific rules

## Vault Structure

- `sources/` — Deep notes on each primary source (Anthropic articles, Addy Osmani, Viv Trivedy, etc.)
- `patterns/` — Reusable harness patterns: compaction, context resets, planner/generator/evaluator, Ralph loops, sprint contracts
- `references/` — Tool-specific notes, config examples, MCP details
- `synthesis/` — Cross-cutting synthesis and integration notes

## Navigation Rules

- When asked "what is harness engineering?" → read synthesis/core-principles.md
- When asked "how to handle long-running agents" → check sources/effective-harnesses.md and patterns/
- When asked "how to build evals" → check sources/demystifying-evals.md
- When asked "context engineering tips" → check sources/context-engineering.md
- When asked "what patterns exist" → check patterns/ directory
- Never suggest generic filler. Enforce harness-specific actionable advice.