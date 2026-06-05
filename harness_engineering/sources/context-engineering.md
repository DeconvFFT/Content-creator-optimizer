# Effective Context Engineering for AI Agents

**Source:** Anthropic Engineering Blog, Sep 29, 2025
**URL:** https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

## Core Thesis

Context engineering is the natural evolution of prompt engineering. It shifts focus from writing clever prompts to curating the **entire token state** available to the LLM at inference time — system prompts, tools, MCP, external data, message history — and cyclically refining what goes into the limited context window.

## Key Concepts

### Context Rot
- As the number of tokens increases, the model's ability to accurately recall information decreases (needle-in-a-haystack degradation).
- Every new token depletes the model's "attention budget" — transformers use n² pairwise relationships for n tokens.
- Models develop attention patterns from training data where shorter sequences dominate → less experience with context-wide dependencies.
- **Key insight:** Context is a finite resource with diminishing marginal returns.

### Anatomy of Effective Context

The goal: **find the smallest possible set of high-signal tokens that maximize the likelihood of the desired outcome.**

| Component | Principle | Pitfall |
|---|---|---|
| System prompts | Extremely clear, simple, direct language at the "Goldilocks altitude" | Hardcoding brittle logic OR being too vague/falsely assuming shared context |
| Tools | Self-contained, minimal overlap, clear input params | Bloated tool sets with ambiguous decision points |
| Examples (few-shot) | Diverse canonical examples that portray expected behavior | Laundry list of edge cases |
| Message history | Aggressive curation, strip noise | Including everything |

### System Prompt Structure
- Organize into distinct sections: `<background_information>`, `<instructions>`, `## Tool guidance`, `## Output description`
- Use XML tagging or Markdown headers for delineation
- Start minimal, test with best model, add instructions only for observed failure modes

### Context Retrieval Strategies

1. **Pre-inference embedding retrieval** — Traditional RAG, surface important context before reasoning
2. **Just-in-time retrieval** — Agents maintain lightweight identifiers (file paths, stored queries, web links) and dynamically load data at runtime using tools. This mirrors human cognition.
3. **Hybrid strategy** — Pre-retrieve some data for speed, plus autonomous exploration at agent's discretion (Claude Code's model)

**Progressive disclosure:** Agents incrementally discover relevant context through exploration. Each interaction yields context that informs the next decision.

### Long-Horizon Techniques

#### 1. Compaction
Summarize conversation nearing context window limit, reinitiate new window with the summary. Preserve architectural decisions, unresolved bugs, implementation details. Discard redundant tool outputs.

**Best practice:** Start by maximizing recall (capture everything relevant), then iterate to improve precision (eliminate superfluous content). Safest lightest touch: tool result clearing.

#### 2. Structured Note-Taking (Agentic Memory)
Agent regularly writes notes persisted outside context window. Like Claude Code creating a to-do list or a NOTES.md file.

The Claude Playing Pokémon example: agent maintains precise tallies across thousands of game steps, remembers explored regions, tracks combat strategies — all through self-written notes.

#### 3. Sub-Agent Architectures
Specialized sub-agents handle focused tasks with clean context windows. Main agent coordinates while subagents return condensed summaries (1,000-2,000 tokens). Detailed search context remains isolated within subagents.

## Operational Takeaways for Harness

- **System prompts must be immutable across sessions** to maximize OpenRouter caching (90% discount on first ~4K tokens)
- **Append data at the tail** using XML dividers
- **Pre-extract context** to filesystem before passing to subagents — don't dump full files
- **Tool result clearing** is the safest first step for compaction
- **Just-in-time retrieval** (file paths, not file contents) saves massive token overhead
- Use **compaction for continuous flow**, **note-taking for milestone-based work**, **multi-agent for parallel exploration**