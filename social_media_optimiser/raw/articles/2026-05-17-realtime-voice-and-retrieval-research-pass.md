---
type: raw-source
project: agent-studio
status: captured
captured: 2026-05-17
owners:
  - inference-systems-engineer
  - retrieval-intelligence-agent
  - principal-software-engineer
---

# 2026-05-17 Realtime Voice And Retrieval Research Pass

## Scope

Research pass for the next Agent Studio implementation direction:

- realtime voice stack using Gemma 4 E4B, Kokoro, LiveKit, optional Pipecat, Rust, and Python;
- retrieval/reranking/knowledge-graph strategy for high precision, high recall, and source-backed content.

## Primary Sources Reviewed

- Gemma 4 E4B model card: https://huggingface.co/google/gemma-4-E4B-it
- Gemma 4 Transformers docs: https://huggingface.co/docs/transformers/v5.5.0/model_doc/gemma4
- Kokoro-82M model card: https://huggingface.co/hexgrad/Kokoro-82M
- LiveKit turn handling: https://docs.livekit.io/agents/logic/turns/
- LiveKit turn tuning: https://docs.livekit.io/agents/logic/turns/tuning/
- LiveKit pipeline types: https://docs.livekit.io/agents/models/pipelines/
- Pipecat pipeline docs: https://docs.pipecat.ai/guides/learn/pipeline
- Hugging Face Inference Endpoint autoscaling: https://huggingface.co/docs/inference-endpoints/guides/autoscaling
- Hugging Face TGI streaming: https://huggingface.co/docs/text-generation-inference/en/conceptual/streaming
- Qdrant hybrid search and reranking: https://qdrant.tech/documentation/search-precision/reranking-hybrid-search/
- Qdrant hybrid query concepts: https://qdrant.tech/documentation/concepts/hybrid-queries/
- Neo4j GraphRAG overview: https://neo4j.com/labs/genai-ecosystem/graphrag/
- LangGraph persistence: https://docs.langchain.com/oss/python/langgraph/persistence
- A2A specification: https://google-a2a.github.io/A2A/specification/
- Google ADK long-running agents: https://developers.googleblog.com/en/build-long-running-ai-agents-that-pause-resume-and-never-lose-context-with-adk/

## Voice Research Synthesis

Gemma 4 E4B is the correct Gemma model for the realtime voice input lane because it supports text, image, and audio inputs. It generates text output, not speech waveforms. Therefore the production stack is not a single-model speech-to-speech system. It is a half-cascade:

1. LiveKit handles live media transport and room/session lifecycle.
2. Rust handles high-frequency audio edge work: VAD, buffers, backpressure, interruption detection, and cancellation dispatch.
3. Python handles state, context pruning, Gemma 4 E4B audio/reasoning calls, Kokoro TTS, and durable events.
4. Kokoro-82M turns response text into audio chunks.
5. LiveKit publishes agent audio back to the user.

LiveKit should be the public browser/mobile transport. Custom browser WebSockets remain local-dev only. Pipecat is useful if pipeline processors reduce custom orchestration work, but it should not replace the LiveKit transport decision.

Gemma 4 E4B audio input has a 30-second per-audio practical limit from the model card guidance. Multi-turn voice memory must not keep raw audio indefinitely. Keep current and recent audio only, then convert older turns into transcript plus compact summary.

HF endpoint scale-to-zero is not acceptable for live voice sessions because cold starts break conversational latency. Live voice endpoints should run with a warm minimum replica or a prewarm strategy; scale-to-zero can remain acceptable for background/offline content generation.

Barge-in is not only a UI state. It is a distributed cancellation contract: Rust drops queued outbound audio immediately, sends cancellation to Python, Python cancels the active Gemma task and clears Kokoro buffers, and the durable event log records the interruption.

## Retrieval Research Synthesis

The retrieval stack should use multi-stage retrieval rather than a single vector query:

1. Query understanding and rewrite.
2. Parallel candidate generation from dense vectors, sparse/full-text search, web search, metadata filters, and knowledge graph neighborhoods.
3. Reciprocal-rank or weighted fusion to combine candidate lists.
4. Reranking over the fused top-K only, using cross-encoder or late-interaction scoring when available.
5. Evidence acceptance, contradiction checks, freshness/authority scoring, and coverage audits before content generation.

Dense retrieval alone causes false positives when semantic similarity is high but factual support is weak. Sparse/BM25 alone misses paraphrases and broader topic coverage. Graph traversal alone is fragile unless entity extraction and edge quality are strong. The robust direction is hybrid retrieval plus explicit rerank and evaluation ledgers.

Knowledge graph construction should focus on useful production entities first:

- source;
- claim;
- topic;
- entity;
- artifact;
- author/provider;
- dataset/model/tool;
- run;
- feedback item.

Graph traversal should be bounded and evidence-aware. Use graph neighborhoods to widen recall and explain coverage, not to bypass source-ledger proof. A graph edge never makes a claim true by itself; it only identifies candidate evidence to verify.

## Implementation Implications

- Continue with LiveKit frontend join, then Python Gemma/Kokoro agent engine, then Rust voice-edge sidecar.
- Add a live voice latency benchmark ledger before calling the voice system production-ready.
- Keep Postgres + pgvector as the canonical durable store, with provider interfaces that can later route candidate generation to Qdrant, Elasticsearch, Neo4j, or cloud search if benchmarks justify it.
- Retrieval quality ledgers must store candidate provenance, rerank reasons, accepted/rejected evidence, precision/recall metrics, false-positive ids, false-negative ids, and missing-coverage prompts.
- Context packets should consume accepted evidence first and should include retrieval-quality warnings when recall gaps or precision risks are unresolved.
