# Harness Engineering Vault — Index

A machine-first knowledge base collecting the best public research on harness engineering.

## Sources

| Note | Source | Published | Key Idea |
|---|---|---|---|
| [[sources/context-engineering]] | Anthropic | Sep 2025 | Context is finite with diminishing returns; just-in-time retrieval beats pre-loading |
| [[sources/demystifying-evals]] | Anthropic | Jan 2026 | Code-based > model-based > human graders; capability vs regression distinction |
| [[sources/effective-harnesses-long-running]] | Anthropic (Justin Young) | Nov 2025 | Initializer + coding agent + feature list JSON for multi-session work |
| [[sources/harness-design-long-running]] | Anthropic (Prithvi Rajasekaran) | Mar 2026 | GAN-inspired generator-evaluator triad for long-running coding |
| [[sources/addy-harness-engineering]] | Addy Osmani | Apr 2026 | Comprehensive survey: agent = model + harness, ratchet principle, HaaS |

## Patterns

See [[patterns/catalog]] for all reusable patterns.

- Generator-Evaluator Loop
- Planner → Generator → Evaluator Triad
- Initializer + Coding Agent
- Ralph Loop
- Sprint Contract Pattern
- Just-in-Time Context Retrieval
- Compaction with Tool Result Clearing
- Sprint-Based Evaluator (Playwright E2E)
- Silent Success / Verbose Failure Hooks
- Capability-to-Regression Pipeline

## Synthesis

[[synthesis/core-principles]] — Cross-cutting principles across all sources.

## References

(Linked from model-harness-engineering skill at `~/.hermes/skills/mlops/model-harness-engineering/`)

## New Content

| When | What | Why |
|---|---|---|
| This session | Vault creation + 5 source notes + patterns + synthesis | Initial scaffolding from deep reading of 5 articles |