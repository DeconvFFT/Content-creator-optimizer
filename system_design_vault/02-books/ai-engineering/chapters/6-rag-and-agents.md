---
type: chapter-note
project: agent-studio-system-design
status: canon_ready
source_title: "AI Engineering"
authors: "Chip Huyen"
chapter: "6"
chapter_title: "RAG and Agents"
source_path: "/Users/saumyamehta/DS interview prep/books/AI Engineering.pdf"
rights_status: user_provided_local
updated: 2026-05-17
---

# 6 - RAG and Agents

## Reading Status

Direct source reading pass completed for the chapter RAG and agent sections. Cross-check pass completed against official Anthropic contextual retrieval guidance, Google Cloud RAG architecture guidance, pgvector documentation, LangChain reranking/compression documentation, and OpenAI agent-eval/trace guidance. This note is original synthesis only; it intentionally avoids raw text dumps, copied examples, and long excerpts.

## Core Idea

RAG and agents extend model capability by adding external context, tools, planning, memory, and reflection. The important system-design point is that each added capability creates a new measurable subsystem: retrieval quality, chunking/indexing, tool permissions, plan validity, execution state, reflection quality, and failure recovery.

## Design Patterns

- Keep term-based retrieval as a serious baseline. BM25-style retrieval remains fast, cheap, and strong when exact terms, product names, codes, or identifiers matter.
- Add embedding retrieval when semantic matching matters, but measure vector-search latency, index build cost, vector storage cost, and embedding quality.
- Use hybrid search for production RAG. Term search catches exact entities and error codes; embedding search catches semantic matches; fusion/reranking reconciles them.
- Evaluate retrieval separately from final answer quality. Track context precision, context recall where feasible, NDCG/MAP/MRR for ranking, embedding quality, and end-to-end answer quality.
- Choose chunking by retrieval use case, not convenience. Equal-size, recursive, paragraph, question-answer, code-aware, overlap, and token-aware chunking have different failure modes.
- Use reranking to reduce context bloat before generation. Reranking is especially valuable when the model context budget is smaller than the candidate evidence set.
- Rewrite conversational or underspecified queries into standalone retrieval queries; reject or clarify when identity resolution or missing facts make rewriting unsafe.
- Add contextual retrieval metadata around chunks: title, document summary, entities, tags, keywords, related questions, and short chunk context.
- Treat multimodal RAG and tabular RAG as distinct architectures. Image/video/audio retrieval needs captions or multimodal embeddings; tabular RAG needs schema selection, text-to-SQL, execution, and result-grounded response generation.
- Define agents by environment and action set. An agent is not just a prompt; it is a system that perceives an environment and can take allowed actions.
- Split tools into knowledge augmentation, capability extension, and write actions. Write actions require stronger trust, security, and human approval.
- Decouple planning from execution. Generate a plan, validate it, execute only allowed steps, evaluate outcomes, and replan if needed.
- Use hierarchical and natural-language planning where exact function names would make the planner brittle, but translate plans into executable tool calls through a narrower component.
- Evaluate tool selection through ablations, tool-call distributions, tool mistakes, and model-specific tool preferences.

## Failure Modes

- Semantic retrieval misses exact terms because embeddings blur identifiers.
- Term-based retrieval returns lexically matching but semantically wrong documents.
- Chunk boundaries cut away the context needed to answer correctly.
- Query rewriting hallucinates missing entities or converts an impossible question into a misleading answerable one.
- Vector databases become a major cost center through frequent embedding regeneration, storage growth, and query volume.
- RAG systems optimize only context precision because context recall is harder to measure.
- Multimodal RAG retrieves metadata rather than the actual visual/audio evidence needed by the query.
- Text-to-SQL agents use the wrong tables, generate invalid SQL, or execute a query that answers the wrong business question.
- Tool inventories grow until the model cannot choose reliably.
- Function calls use valid tools with invalid parameters or plausible but wrong parameter values.
- Long multi-step plans compound error probability; high per-step accuracy still collapses over many steps.
- Reflection incorrectly concludes a task is complete, causing the system to stop before the goal is satisfied.
- Write tools create real-world harm when permissions, confirmation, and audit trails are weak.

## Agent Studio Implications

- Retrieval Intelligence should maintain both lexical and vector retrieval paths, then fuse and rerank candidates before writers receive context.
- pgvector is appropriate as the durable local vector layer, but it must be paired with exact metadata filters, source IDs, document titles, entity tags, and freshness fields.
- The retrieval-quality ledger should store context precision, recall proxy, rank metrics when available, reranker version, accepted/rejected candidates, and rejection reasons.
- Context Engineering should own chunking policy per corpus: books, official docs, lecture notes, source articles, feedback, and run artifacts should not all share one chunking strategy.
- Query rewriting should produce an auditable rewritten query and a confidence/clarification flag. If identity resolution is needed and unavailable, the system should ask rather than guess.
- Source Ledger should separate retrieved evidence, accepted evidence, rejected evidence, and final cited evidence.
- Tool Policy should classify tools as read-only, capability extension, or write action. Write actions need explicit approval gates and stronger logging.
- Agent cards need allowed environment, allowed tools, parameter schema, automation level, and human-confirmation rules.
- Durable orchestration should represent plan generation, plan validation, tool execution, reflection, and replan as separate events so failures can be replayed.
- The cockpit should show tool calls and parameter values for inspectability, especially for file, web, database, and publishing actions.
- Agent evals must include planning failures, tool-use failures, goal failures, constraint failures, reflection failures, and efficiency/latency failures.
- Multi-agent architecture is justified when components have different responsibilities: planner, evaluator, executor, source verifier, and human feedback gate.

## Official Cross-Check

| Book theme | Official-source confirmation | Agent Studio design implication |
|---|---|---|
| Hybrid retrieval should be the default production baseline | Anthropic contextual retrieval reports that embeddings plus BM25 outperform embeddings alone in their tested knowledge-base settings. pgvector documentation explicitly supports combining vector search with Postgres full-text search and using RRF or cross-encoders to combine results. | Retrieval Intelligence should combine lexical, vector, metadata, and graph candidates before reranking rather than treating vector search as the only retrieval path. |
| Chunk context matters | Anthropic contextual retrieval adds short chunk-specific context before embedding and keyword indexing, and highlights chunk boundaries, chunk size, and overlap as implementation choices that affect retrieval performance. | Context Engineering should generate compact chunk context for book/docs corpora and store the policy/version that created it. |
| Reranking improves precision but adds latency/cost | Anthropic and LangChain retrieval/reranking guidance both treat reranking as a second-stage relevance filter over initially retrieved candidates, with runtime tradeoffs. | Reranking should be configurable by agent profile and query class, with latency and quality metrics captured per run. |
| RAG needs architecture choices, not just a library call | Google Cloud RAG guidance separates architectures for managed vector search, operational databases, Cloud SQL/AlloyDB, GKE, and GraphRAG. | Agent Studio should store retrieval backend, data freshness model, graph usage, operational-data boundary, and deployment profile as explicit source-system metadata. |
| Agent behavior should be trace-graded | OpenAI agent eval and trace grading guidance evaluates decisions, tool calls, and workflow behavior, not only final answers. | Agent evals should include planning, tool selection, retrieval, grounding, final answer quality, and efficiency checks. |
| Tool use needs bounded permissions | Official agent safety guidance recommends approvals and layered controls for tool-capable agents. | Tool Policy should classify read-only, capability-extension, and write-action tools with different approval/audit requirements. |
| Current source citations must be verifiable | Anthropic citations/search-results features and Google RAG architectures emphasize grounded source use. | Source Ledger should separate retrieved evidence, accepted evidence, rejected evidence, and cited evidence, with source IDs and freshness metadata. |

## Follow-Up Questions

- What is the minimum retrieval evaluation bundle for local book notes versus public web/docs notes?
- Which actions in Agent Studio should be read-only by default, and which require human confirmation every time?
- Should query rewriting be handled by the Retrieval Intelligence Agent, Context Engineering Agent, or a dedicated query planner?
- What context recall proxy is acceptable when annotating every relevant document is impractical?
- How should the system expose retrieved-but-rejected evidence to users without overwhelming the cockpit?

## Related Official Video Sources

These are official Stanford/Stanford Online video listings for navigation only; none is marked as watched or ingested in the video ledger.
- [[../../../02-lectures/stanford/cs25-retrieval-augmented-language-models]] - Stanford CS25, "Retrieval Augmented Language Models" ([YouTube](https://www.youtube.com/watch?v=mE7IDf2SmJg)).
- [[../../../02-lectures/stanford/cs25-lm-intuition-future-ai]] - Stanford CS25, "Intuition on LMs, Shaping the Future of AI" ([YouTube](https://www.youtube.com/watch?v=3gb-ZkVRemQ)).
- [[../../../02-lectures/stanford/cs25-generalist-agents-open-ended-worlds]] - Stanford CS25, "Generalist Agents in Open-Ended Worlds" ([YouTube](https://www.youtube.com/watch?v=wwQ1LQA3RCU)).
