---
type: book-ingestion-plan
project: agent-studio-system-design
status: active
updated: 2026-05-17
---

# Legal Status And Chapter Plan

## Policy

Chapter-by-chapter notes are allowed for:

- public web books and official free PDFs,
- open-license books,
- official whitepapers and standards,
- papers from official repositories,
- local files the user confirms are lawfully obtained.

Chapter notes are not raw text dumps. Notes should capture:

- core idea,
- design pattern,
- failure mode,
- implementation implication,
- Agent Studio decision,
- source dependency.

## Book Targets

### Designing Data-Intensive Applications

Status: `needs_user_rights_confirmation` for full chapter ingestion.

Usable now:

- O'Reilly public page and table-of-contents metadata.
- Martin Kleppmann public talks/posts where official.
- Official/open synthesis note: [[../01-sources/official-open/ddia-distributed-systems-foundations]].

Agent Studio focus:

- durability,
- replication/recovery,
- transactions,
- event logs,
- stream processing,
- schema evolution,
- consistency tradeoffs.

Current boundary: no local DDIA book file is present, so the vault should use the official/open foundations note for architecture decisions and should not create chapter-level DDIA notes unless a lawful local copy is later provided or official/open chapter material is available.

### Designing Machine Learning Systems

Status: `user_provided_local` for compact local notes and design implications.

Usable now:

- O'Reilly public page and table-of-contents metadata.
- Chip Huyen public articles when official.
- Local chapter-note scaffolds at `02-books/designing-machine-learning-systems/chapters/`.

Agent Studio focus:

- product/ML objective split,
- data distribution shift,
- evaluation,
- monitoring,
- feedback loops,
- human process around ML systems.

### AI Engineering

Status: `user_provided_local` for compact local notes and design implications.

Usable now:

- O'Reilly public page and table-of-contents metadata.
- Local chapter-note scaffolds at `02-books/ai-engineering/chapters/`.

Agent Studio focus:

- foundation-model application stack,
- RAG and agents,
- evaluation,
- prompt/model/data adaptation,
- latency and cost bottlenecks.

### Inference Engineering

Status: `eligible`.

Usable now:

- Official Baseten book page and official digital download path.

Agent Studio focus:

- latency/cost budget ownership,
- model serving runtime,
- hardware/runtime/tooling split,
- multimodal inference,
- production serving reliability.

### Practical Guide To Building Agents

Status: `eligible`.

Usable now:

- Official OpenAI PDF.

Agent Studio focus:

- agent/workflow boundary,
- handoffs,
- tool access,
- human intervention,
- guardrail and evaluation loops.

## First Chapter Stub Set

Created:

1. `AI Engineering` - 10 chapter scaffolds.
2. `Designing Machine Learning Systems` - 11 chapter scaffolds.
3. `Practical MLOps` - 12 chapter scaffolds.
4. `LLM Engineers Handbook` - whole-document scaffold.
5. `Building Machine Learning Powered Applications` - whole-document scaffold.
6. `Inference Engineering` - 8 chapter scaffolds.

Next:

1. Practical MLOps compact synthesis.
2. OpenAI Practical Guide to Building Agents - section map from official PDF.
3. Anthropic Building Effective Agents - patterns.
4. Google A2A - agent-card and discovery pattern.
5. LangChain memory - three-tier project memory.
6. Google Cloud reliability - production ML reliability principles.
7. Uber Michelangelo - platform workflow standardization.
8. Retrieval and reranking canon - hybrid retrieval + reranking + KG traversal.

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../02-lectures/stanford/cs25-transformer-foundations]] - Stanford CS25, "Overview of Transformers" ([YouTube](https://www.youtube.com/watch?v=bHSDPgZYie0)).
- [[../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
