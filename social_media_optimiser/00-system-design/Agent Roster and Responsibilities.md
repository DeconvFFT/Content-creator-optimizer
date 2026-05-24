---
type: agent-roster
project: agent-studio
status: draft
updated: 2026-05-17
---

# Agent Roster and Responsibilities

## Conversation and Routing

- Realtime Conversation Host: natural voice/text interaction, interruption handling, spoken response plans.
- Intent Router: maps dialogue into create, revise, research, route, clarify, or feedback actions.
- Forward Deployed Engineer: captures user feedback and turns it into structured system improvements.

## Engineering and Harness

- Principal Software Engineer: architecture, code quality, system boundaries.
- Backend Platform Engineer: FastAPI services, Postgres/pgvector, migrations, async APIs, backend consistency.
- Frontend Experience Engineer: conversational cockpit UI, browser voice controls, event streams, accessibility, source/artifact views.
- Scalability/Reliability Engineer: SLOs, capacity planning, backpressure, worker scheduling, graceful degradation.
- Inference Systems Engineer: OpenRouter/LiveKit/Kokoro realtime boundaries, legacy native-Gemma/HF context, reranker/model routing, latency/cost, provider smoke proof.
- Agent Harness Engineer: durable orchestration, resumability, checkpoints, worker profiles.
- A2A Protocol Agent: agent cards, handoffs, dependencies, task graph integrity.
- Context Engineering Agent: context packets, memory selection, source evidence, prompt budgets.
- Observability Agent: runtime health, provider ops, audit ledgers.

## Research and Retrieval

- Web Research Agent: provider-backed web search and source collection.
- Retrieval Intelligence Agent: first-class owner for hybrid retrieval, RRF, reranking, search optimization, precision/recall, and FP/FN reduction.
- Knowledge Graph Curator Agent: first-class owner for entity extraction, claim-source graph construction, graph traversal, and coverage.
- Source Ledger Agent: source quality, freshness, source-to-claim matrix.
- Claim Verification Agent: claim support, contradiction checks, unsupported labels.
- Data Analyst Agent: structured analysis and evidence summaries.

## Content

- Content Strategist: content plan, format selection, narrative direction.
- ELI5 Short-Form Writer: simple posts and reel scripts.
- Substack Essay Writer: detailed but readable long-form articles.
- Script Doctor: hook, pacing, and clarity revision.
- Editor-in-Chief: editorial quality gate.

## Growth and Distribution

- Platform Optimization Agent: canonical platform-specific distribution package with captions, CTAs, source dependencies, and platform variants.
- Influencer Strategy Agent: durable growth strategy for audience segments, keywords, hashtags, creator positioning, and phrases to avoid.
- Outreach Agent: durable growth strategy for community targets, collaboration pitches, engagement prompts, and outreach risk checks.

## Media

- Lead UI/UX Designer: product UI review and usability.
- Interactive Systems Designer: planning and system-design surface.
- Visual Director: visual direction and image prompts.
- Image Generation Agent: imagegen boundary and raster prompt packs.
- Audio Producer: voice style, TTS/realtime audio briefs.
- Video/Reel Producer: storyboard, timing, subtitles, reel packaging.

## Quality and Management

- Guardrails Agent: safety, provenance, unsupported-claim gates.
- Product Manager: priorities, scope, tradeoffs, sync pulse.
- Critic/Reviewer Agent: adversarial review and issue finding.
- Interactive Note-Taking Agent: Obsidian notes, review packets, revision history.
- Artifact Librarian: artifact index and publishing handoff.
- Sprint/Progress Agent: work tracking in Obsidian and run plans.
