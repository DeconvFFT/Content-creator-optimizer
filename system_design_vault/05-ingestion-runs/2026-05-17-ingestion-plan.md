---
type: ingestion-run
project: agent-studio-system-design
status: active
updated: 2026-05-18
background_agent: Feynman
background_agent_id: 019e3769-b776-7d21-9159-914322afc8dc
---

# 2026-05-17 Ingestion Plan

## Current Status

- Background scout relaunched as `Feynman` with a legal/source-safe ingestion classification task.
- `Feynman` now owns the ingestion lane autonomously and should only interrupt the main implementation loop for concrete blockers.
- Local book folder found at `/Users/saumyamehta/DS interview prep/books`.
- Files with explicit Anna's Archive, Z-Library, and LibGen origin markers are excluded from automated ingestion.
- User explicitly asked to use `/Users/saumyamehta/DS interview prep/books`; local files without explicit shadow-library markers are treated as `user_provided_local` for compact notes and design implications.
- User asked to keep only PDF, JPEG/JPG, DOC, and DOCX files in the local books corpus. The disallowed `.DS_Store` file was removed.
- User expanded ingestion scope to official websites, official YouTube lectures, official docs, and white papers.
- The ingestion workflow still avoids raw text dumps and long verbatim excerpts.
- Official/public sources can be synthesized now.
- Obsidian workflow updated after direct Chrome reading of the public X article on automated Codex/Obsidian vaults: passive capture is allowed only as a source queue, while direct reading, cross-checking, and canon promotion remain separate gates.
- `Designing Machine Learning Systems` scaffolds were refreshed to point at the actual local file now present on disk: `/Users/saumyamehta/DS interview prep/books/Designing machine learning systems - an iterative process.pdf`.
- `Inference Engineering` chapter scaffolds and a manifest were generated from the local corpus.
- Compact book-synthesis notes now exist for `AI Engineering`, `Designing Machine Learning Systems`, `Inference Engineering`, `LLM Engineers Handbook`, and `Building Machine Learning Powered Applications`.
- Cross-source system-design synthesis now lives at `03-patterns/system-design/production-agent-studio-canon.md`.

## Immediate Ingestion Targets

1. Baseten Inference Engineering official book page.
2. OpenAI Practical Guide to Building Agents.
3. Anthropic Building Effective Agents.
4. Google Developer Guide to AI Agent Protocols.
5. Google ADK resume docs.
6. LangChain memory and LangGraph checkpointer docs.
7. Hugging Face Gemma 4 docs.
8. OpenAI Realtime and Agents SDK guardrail docs.
9. Google Cloud AI/ML reliability guidance.
10. Uber Michelangelo and Metaflow public docs.
11. Local books corpus priority queue: `AI Engineering.pdf`, `Designing machine learning systems - an iterative process.pdf`, `Inference Engineering.pdf`, `Practical MLOps_ Operationalizing Machine Learning Models.pdf`, `LLM Engineers Handbook.pdf`, `building-machine-learning-powered-applications-going-from-idea-to-product.pdf`, plus official/open verification for ISLP, Bishop PRML, and Deep Learning.
12. Stanford official courses: CS329S, CS224N, CS25, CS324, CS336, and CS231n.
13. Official docs and white papers: OpenAI evals/agent evals/prompting, Anthropic prompting, Google Cloud RAG and GenAI operations, AWS Well-Architected Generative AI Lens, and AWS GenAI security.
14. Official YouTube playlist worklist from Stanford course pages, stored as links and compact Obsidian notes only.

## Blocked

- Long-form substitute notes that reproduce the value of a copyrighted book.
- Raw extracted text stored in tracked vault files.
- Any local file with explicit Anna's Archive, Z-Library, LibGen, or similar origin marker unless replaced by another local/user-provided copy without that marker or by official/open material.
- Non-PDF/JPEG/JPG/DOC/DOCX files in the local book corpus.

## Excluded

- Any Anna's Archive, Z-Library, or LibGen-marked PDFs.
- GitHub/IPFS PDFs unless official or rights-authorized.

## Next Notes To Add

- `02-books/practical-mlops/book-synthesis.md`
- `02-books/openai-practical-agents/chapter-map.md`
- `02-books/designing-data-intensive-applications/official-toc-map.md`
- `02-books/designing-machine-learning-systems/official-toc-map.md`
- `03-patterns/knowledge-graphs/entity-claim-source-graph.md`
- `03-patterns/evaluation/agent-evals-and-regression-gates.md`
- `03-patterns/security/genai-threat-model-and-tool-guardrails.md`
