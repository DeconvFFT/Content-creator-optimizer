---
type: official-course-source-note
project: agent-studio-system-design
status: canon_ready
updated: 2026-05-18
source_status: official_stanford_course_page_and_public_playlist_canon_ready
sources:
  - https://web.stanford.edu/class/cs224n
  - https://web.stanford.edu/class/cs224n/
  - https://www.youtube.com/playlist?list=PLoROMvodv4rOaMFbaqxPDoLWjDaRAdP9D
related:
  - "[[cs224n-public-llm-systems-notes]]"
  - "[[../../03-patterns/llm-systems/nlp-llm-systems-canon]]"
---

# CS224N NLP and LLM Systems Source Map

## Reading Scope

Canon-ready course/source-map pass over Stanford CS224N Winter 2026 official course page, logistics, reference-text list, assignment/project structure, public-video pointers, and schedule, cross-linked to the now-canon CS224N public LLM systems note and CS224N RAG/agents/reasoning note. The source availability check was refreshed on 2026-05-18. This is a routing and scope-control note, not a claim of complete lecture/video comprehension. It stores compact original synthesis only and no raw slides, transcripts, assignments, or long excerpts.

## Course Signal

CS224N is a neural NLP course that now explicitly spans classic NLP, deep-learning foundations, transformers, LLM pretraining/post-training, prompting/PEFT, agents/tool use/RAG, benchmarking, reasoning, multilinguality, interpretability, risks, and multimodality. For Agent Studio, the important signal is not just "NLP basics"; it is the way Stanford sequences language-system competence from representation learning to transformer systems to evaluation and socially risky deployment.

## Public Source Boundaries

The 2026 lecture videos are limited to enrolled students through Canvas/Panopto. The official public path is the Spring 2024 CS224N YouTube playlist linked from the Stanford page, plus current public slides/notes as posted in the 2026 schedule. Agent Studio ingestion should therefore treat 2026 schedule/slides as current structure and use the official 2024 playlist only where video content is public.

## Topics Relevant To Agent Studio

- Word vectors and representation learning matter for retrieval quality because embedding spaces have geometry, bias, polysemy, and evaluation failure modes.
- Backpropagation, tensor derivatives, and PyTorch foundations matter when interpreting fine-tuning, adapter, and evaluation code rather than treating model training as a black box.
- Transformers and attention are the basis for long-context behavior, tool-use prompts, RAG context packing, and inference bottlenecks.
- Pretraining coverage includes scaling, systems, and data, which should inform source-quality ledgers and why data mixture decisions are architecture decisions.
- Post-training coverage includes SFT, RLHF, and DPO, which maps to Agent Studio preference pairs, reviewer feedback, and route-specific adaptation.
- Efficient adaptation covers prompting and PEFT, matching the route-change ladder: prompt first when controllable, retrieval or adapters when prompt-only changes cannot fix the failure.
- Agents, tool use, and RAG directly map to tool-call traces, retrieval evidence, graph handoffs, and source-grounded content generation.
- Benchmarking and evaluation provide the bridge from model-centric benchmarks to route-specific, workflow-specific evals.
- Reasoning lectures are relevant to planning agents, verifier loops, and test-time compute tradeoffs.
- Tokenization/multilinguality affects content portability, cost estimation, latency, and quality for international campaigns.
- Interpretability and broader-impact lectures belong in the safety/observability lane, especially for hidden failure modes in autonomous content workflows.
- Multimodality maps to Agent Studio visual QA, video/storyboard generation, image-grounded retrieval, and mixed-modal reward/evaluation.

## Agent Studio Design Implications

- Add CS224N as a separate source family instead of folding it into generic Stanford notes; its value is the NLP-to-LLM progression.
- Create one note per public lecture/video only after direct video or transcript reading, with separate tags for embeddings, transformers, post-training, RAG, evals, reasoning, safety, and multimodality.
- Treat assignments and final-project structure as evaluation-design inspiration, not as reusable code or solution material.
- Link CS224N representation and tokenization notes into retrieval, reranking, source chunking, and multilingual content planning.
- Link CS224N post-training notes into preference-data schemas, feedback events, and route adaptation decisions.
- Link CS224N agents/RAG/eval notes into prompt-workflow eval datasets and source-ledger gates.

## Canon Routing Map

- `cs224n-public-llm-systems-notes` owns representation learning, tokenization, transformers, pretraining, post-training, PEFT, benchmarking, multilinguality, interpretability, risk, and multimodal language-system foundations.
- `cs224n-rag-agents-reasoning` owns source authorization, retrieval/rerank evidence, packed context, citation validation, tool/action boundaries, task/eval environments, agent data lineage, reasoning traces, verifier strategies, test-time compute, long-context controls, and the `rag_agent_reasoning_release_gate`.
- `nlp-llm-systems-canon` is the cross-note production canon for tokenizer profiles, context assembly, adaptation candidates, reasoning traces, benchmark context, language coverage slices, multilingual token/cost regressions, and reasoning-loop bounds.
- CS224N public playlist/video work remains a separate direct-viewing queue; this source map only records the official public pointer and topic routing.

## Remaining Boundaries

- Create separate public-video notes from the Spring 2024 CS224N YouTube playlist only after direct full-video watching.
- Continue direct-reading public CS224N slides for multimodality, open questions, and any newly posted notes that affect Agent Studio architecture.
- Keep assignments and project materials as evaluation-design inspiration only; do not ingest protected solutions or student code.
- Keep 2026 Canvas/Panopto lecture videos out of the evidence chain unless lawful access is provided and a separate pass is requested.

## Related Official Video Sources

The current CS224N public course page points public viewers to the free Spring 2024 YouTube playlist while keeping 2026 lecture videos behind Canvas/Panopto. The playlist is a navigation source only until an individual video is watched directly in full; no transcript, caption, comment, or timestamp-derived note is stored here.

| Video source | URL | Topic note target | Status |
|---|---|---|---|
| CS224N Spring 2024 public YouTube playlist | https://www.youtube.com/playlist?list=PLoROMvodv4rOaMFbaqxPDoLWjDaRAdP9D | [[cs224n-public-llm-systems-notes]] | playlist candidate; individual videos not watched in full |
| CS224N Spring 2024 public YouTube playlist | https://www.youtube.com/playlist?list=PLoROMvodv4rOaMFbaqxPDoLWjDaRAdP9D | [[cs224n-rag-agents-reasoning]] | playlist candidate; individual videos not watched in full |
| CS224N Winter 2026 Canvas/Panopto recordings | Official course page only; enrolled-student access boundary | This source map and current public slide notes | gated; not ingested |

## Canon Promotion

Public CS224N notes and slides for representation, transformers, pretraining, post-training, PEFT, agents/RAG, reasoning, tokenization, multilinguality, and risks have been synthesized in [[cs224n-public-llm-systems-notes]]. The Agent Studio architecture decisions from that pass are promoted in [[../../03-patterns/llm-systems/nlp-llm-systems-canon]], especially tokenizer profiles, context assembly traces, adaptation candidates, reasoning traces, benchmark context, and language coverage slices.
