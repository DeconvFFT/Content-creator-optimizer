# Agent Monitoring

Tools to see what background Cursor subagents are doing in this workspace.

## Cursor Canvas (side panel)

Open the live status board beside chat:

```
/Users/saumyamehta/.cursor/projects/Users-saumyamehta-Gen-AI-all-about-llms/canvases/agent-status-board.canvas.tsx
```

Click the file path in Cursor to open it as a **Canvas** — a panel next to chat showing agent status, tool activity, and per-agent logs parsed from transcript files.

## Terminal watch script

```bash
cd "/Users/saumyamehta/Gen AI/all-about-llms"
chmod +x scripts/watch-agent-transcripts.sh

# List all subagents in this session
./scripts/watch-agent-transcripts.sh list

# Live tail one agent (open in a separate terminal tab)
./scripts/watch-agent-transcripts.sh tail fd7b525b

# Tail all agents at once
./scripts/watch-agent-transcripts.sh tail-all
```

Transcript files live at:

```
~/.cursor/projects/Users-saumyamehta-Gen-AI-all-about-llms/agent-transcripts/dc541605-3c57-402f-bbbd-538d6748fe61/subagents/
```

## What you can and cannot see

| Visible | Not visible |
|---------|-------------|
| Tool calls (Read, Shell, Grep, etc.) | Full chain-of-thought / reasoning |
| `UpdateCurrentStep` progress labels | Subagent internal deliberation |
| Deliverable markers (e.g. "Delivered final report") | `[REDACTED]` thinking blocks |
| Message and tool-call counts | Parent coordinator thinking |

Cursor stores subagent thinking as `[REDACTED]` in JSONL transcripts by design. There is no setting to expose full reasoning traces for background agents.

## Current session agents (2026-05-23)

| ID prefix | Type | Task | Status |
|-----------|------|------|--------|
| `fd7b525b` | explore | Repo architecture | Completed |
| `59e319d8` | generalPurpose | Final ship-readiness synthesis | Completed |
| `34554887` | code-reviewer | Security review | Stalled |
| `c602aa68` | generalPurpose | Functional testing | Stalled |
| `74997cfb` | generalPurpose | Synthesis v1 | Stalled |
| `5cfe3007` | generalPurpose | Status board build | Stalled (superseded by manual build) |

## Refresh the canvas

The canvas embeds a snapshot of transcript data. Re-run the build agent or ask the coordinator to regenerate `agent-status-board.canvas.tsx` after new subagents complete.
