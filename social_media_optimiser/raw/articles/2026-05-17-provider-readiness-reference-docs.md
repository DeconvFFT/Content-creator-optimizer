---
type: raw-source
project: agent-studio
status: captured
updated: 2026-05-17
source_title: Provider readiness reference docs for Gemma, realtime audio, and search
accessed: 2026-05-17
copyright_note: Metadata and paraphrased implementation observations only. Full documentation text is not stored.
derived_wiki:
  - [[../../00-system-design/LLD - Agent Studio]]
  - [[../../wiki/ops/active-codex-context]]
---

# Raw Source - Provider Readiness Reference Docs

## Sources

- Hugging Face Gemma 4 docs: https://huggingface.co/docs/transformers/model_doc/gemma4
- OpenAI Realtime docs: https://platform.openai.com/docs/guides/realtime
- ElevenLabs signed URL docs: https://elevenlabs.io/docs/conversational-ai/api-reference/conversations/get-signed-url
- Cartesia TTS WebSocket docs: https://docs.cartesia.ai/api-reference/tts/websocket
- Tavily Search docs: https://docs.tavily.com/documentation/api-reference/endpoint/search
- SerpAPI Search API docs: https://serpapi.com/search-api

## Paraphrased Observations

- Gemma 4 remains the expert reasoning and multimodal model family, not the live audio transport layer.
- OpenAI Realtime smoke checks should prove session creation, turn-taking, interruptions, spoken output planning, and durable realtime events.
- ElevenLabs conversational-agent smoke checks should prove server-side signed URL creation without exposing API keys to the browser.
- Cartesia smoke checks should prove low-latency WebSocket TTS setup and context handling for spoken output.
- Search-provider smoke checks should prove source candidates enter the source ledger before claim verification or writing.
- Provider readiness should not expose secrets. It should show configured env names, missing env names, documentation links, and expected durable evidence.

## Applied Design Implication

The cockpit Provider Readiness panel should render a smoke walkthrough, not only a static missing-config report. A provider-backed run is ready only when Gemma primary, the selected realtime provider, the selected web-search provider, and local reranking are configured, with Postgres + pgvector running for durable evidence capture.
