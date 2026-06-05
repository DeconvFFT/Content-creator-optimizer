# Effective Harnesses for Long-Running Agents

**Source:** Anthropic Engineering Blog, Nov 26, 2025
**Author:** Justin Young
**URL:** https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents

## Core Thesis

Long-running agents need structured handoffs across context windows. Two-part solution: initializer agent (setup) + coding agent (incremental progress, clean artifacts for next session).

## The Long-Running Agent Problem

Even frontier models (Opus 4.5) on Claude Agent SDK in a loop fall short of building production-quality apps from a high-level prompt.

**Two failure modes:**

1. **One-shotting** — agent tries to do too much at once, runs out of context mid-implementation, leaves next session to guess
2. **Premature declaration of victory** — late-session agent sees progress made and declares the job done

## Two-Part Solution

### 1. Initializer Agent (first session only)
Sets up the environment:
- `init.sh` — development server startup script
- `claude-progress.txt` — log of what agents have done
- Initial git commit showing files added
- Feature list file (JSON format) — comprehensive list of features required

**Feature list JSON:**
```json
{
  "category": "functional",
  "description": "New chat button creates a fresh conversation",
  "steps": [
    "Navigate to main interface",
    "Click the 'New Chat' button",
    "Verify a new conversation is created",
    "Check that chat area shows welcome state",
    "Verify conversation appears in sidebar"
  ],
  "passes": false
}
```

JSON was chosen because the model is less likely to inappropriately change JSON files vs Markdown.

### 2. Coding Agent (every subsequent session)
Asked to work on ONE feature at a time. Must:
- Leave environment in clean state after changes
- Commit to git with descriptive messages
- Write summaries in progress file
- **Self-verify** all features — only mark as "passing" after careful testing
- Use browser automation tools (Puppeteer MCP) for end-to-end testing

## Typical Session Startup Sequence

1. `pwd` — get bearings
2. Read git logs and progress files
3. Read feature list, choose highest-priority undone feature
4. Check if `init.sh` exists to restart servers
5. Run basic end-to-end test before implementing
6. Start work on new feature

## Failure Mode × Solution Table

| Problem | Initializer Fix | Coding Agent Fix |
|---|---|---|
| Declares victory too early | Set up feature list (all marked failing) | Read feature list, pick single feature |
| Leaves buggy state | Initial git repo + progress notes | Read progress + git logs, run basic test, commit at end |
| Marks features done prematurely | Feature list file | Self-verify all features, only mark as passing after careful testing |
| Has to figure out how to run app | Write `init.sh` | Read `init.sh` at session start |

## Open Questions

- Single general-purpose coding agent vs multi-agent (testing agent, QA agent, code cleanup agent)?
- Can this generalize beyond full-stack web apps to scientific research or financial modeling?

## Operational Takeaways

- **Feature list in JSON** — comprehensive, all initially failing, agents only update `passes` field
- **Git discipline** — descriptive commits + progress file = easy session handoff
- **init.sh** ensures agent doesn't waste tokens figuring out how to run the app
- **Puppeteer MCP** for real end-to-end testing (screenshots to identify/fix bugs)
- **One feature at a time** is the critical constraint against the one-shotting failure mode
- Start each session with pwd + git log + progress file + feature list + basic sanity test