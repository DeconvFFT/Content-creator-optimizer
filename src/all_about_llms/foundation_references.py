from all_about_llms.contracts import FoundationReference, FoundationReferenceResult


FOUNDATION_REFERENCES: tuple[FoundationReference, ...] = (
    FoundationReference(
        reference_id="google-agent-protocols-a2a",
        title="Developer's Guide to AI Agent Protocols",
        publisher="Google Developers Blog",
        url="https://developers.googleblog.com/en/developers-guide-to-ai-agent-protocols/",
        reference_type="agent_protocol_guide",
        applies_to=["a2a-protocol-agent", "intent-router", "agent-harness-engineer"],
        architecture_decisions=[
            "A2A-style agent cards are the public contract for specialist agents.",
            "Agent handoffs are durable AgentMessage records rather than hidden prompt text.",
        ],
        agent_implications=[
            "A2A Protocol Agent audits cards, handoffs, tool permissions, and model permissions.",
            "Intent Router emits structured recipient/task decisions before specialist work starts.",
        ],
        freshness_policy="Refresh before changing A2A card fields, handoff rules, or remote-agent interoperability.",
        last_verified="2026-05-16",
    ),
    FoundationReference(
        reference_id="google-adk-long-running-agents",
        title="Build Long-running AI agents that pause, resume, and never lose context with ADK",
        publisher="Google Developers Blog",
        url="https://developers.googleblog.com/build-long-running-ai-agents-that-pause-resume-and-never-lose-context-with-adk/",
        reference_type="long_running_agent_guide",
        applies_to=["agent-harness-engineer", "context-engineering-agent", "observability-agent"],
        architecture_decisions=[
            "Runs need checkpoints, event cursors, human gates, and resumable worker profiles.",
            "Paused agents resume from durable state, not from assumed model memory.",
        ],
        agent_implications=[
            "Agent Harness Engineer owns resume plans and checkpointed recovery context.",
            "Context Engineering Agent creates budgeted context packets for resumed specialists.",
        ],
        freshness_policy="Refresh before changing resume gates, checkpoint records, or always-on worker profile semantics.",
        last_verified="2026-05-16",
    ),
    FoundationReference(
        reference_id="langgraph-postgres-persistence",
        title="LangGraph persistence",
        publisher="LangChain",
        url="https://docs.langchain.com/oss/python/langgraph/persistence",
        reference_type="orchestration_persistence_guide",
        applies_to=["agent-harness-engineer", "principal-software-engineer"],
        architecture_decisions=[
            "LangGraph-style orchestration uses Postgres checkpointing for resumable state machines.",
            "Checkpoint state complements the application event log instead of replacing it.",
        ],
        agent_implications=[
            "Agent Harness Engineer keeps state-machine recovery separate from product artifacts.",
            "Principal Software Engineer reviews checkpoint and event-log boundaries together.",
        ],
        freshness_policy="Refresh before upgrading LangGraph, checkpoint schemas, or time-travel/debug behavior.",
        last_verified="2026-05-16",
    ),
    FoundationReference(
        reference_id="pgvector-postgres-memory",
        title="pgvector",
        publisher="pgvector",
        url="https://github.com/pgvector/pgvector",
        reference_type="vector_memory_reference",
        applies_to=["context-engineering-agent", "source-ledger-agent"],
        architecture_decisions=[
            "Postgres plus pgvector is the v1 durability and semantic memory foundation.",
            "No local SQLite fallback is allowed for runs, memories, events, or checkpoints.",
        ],
        agent_implications=[
            "Context Engineering Agent retrieves run and global memories through pgvector-backed search.",
            "Source Ledger Agent keeps provenance in the same operational database as run state.",
        ],
        freshness_policy="Refresh before changing embedding dimensions, vector indexes, or memory retrieval ranking.",
        last_verified="2026-05-16",
    ),
    FoundationReference(
        reference_id="huggingface-gemma4-transformers",
        title="Gemma4 Transformers model documentation",
        publisher="Hugging Face",
        url="https://huggingface.co/docs/transformers/model_doc/gemma4",
        reference_type="model_capability_reference",
        applies_to=[
            "content-strategist",
            "eli5-short-form-writer",
            "substack-essay-writer",
            "script-doctor",
            "editor-in-chief",
            "principal-software-engineer",
            "visual-director",
            "audio-producer",
        ],
        architecture_decisions=[
            "Gemma 4 is the expert-agent model family, not the realtime voice transport.",
            "Gemma 4 model routing separates deep synthesis, fast routing, and multimodal specialist tasks.",
        ],
        agent_implications=[
            "Specialist workers must pass model policy checks before using Hugging Face Gemma endpoints.",
            "Multimodal and long-context work routes to the configured Gemma 4 endpoint class.",
        ],
        freshness_policy="Refresh before changing Gemma 4 model ids, modality assumptions, or context-window policy.",
        last_verified="2026-05-16",
    ),
    FoundationReference(
        reference_id="livekit-turns-interruptions",
        title="LiveKit turns and interruption handling",
        publisher="LiveKit",
        url="https://docs.livekit.io/agents/logic/turns/",
        reference_type="realtime_audio_reference",
        applies_to=["realtime-conversation-host", "audio-producer"],
        architecture_decisions=[
            "LiveKit handles production realtime media transport, turn lifecycle, and interruption plumbing.",
            "Realtime room/session secrets are never persisted in source ledgers, artifacts, or public events.",
        ],
        agent_implications=[
            "Realtime Conversation Host records session metadata without leaking client secrets.",
            "Audio Producer keeps spoken status, context pruning, and interruption/resume checks explicit.",
        ],
        freshness_policy="Refresh before changing realtime session creation, LiveKit transport, or spoken-output policy.",
        last_verified="2026-05-17",
    ),
    FoundationReference(
        reference_id="pipecat-transports",
        title="Pipecat transport guide",
        publisher="Pipecat",
        url="https://docs.pipecat.ai/pipecat/learn/transports",
        reference_type="realtime_audio_reference",
        applies_to=["realtime-conversation-host", "audio-producer"],
        architecture_decisions=[
            "Use WebRTC/LiveKit for browser and mobile realtime conversations; keep raw WebSockets to server-to-server/prototyping boundaries.",
            "Keep bot logic transport-modular so Gemma/Kokoro adapters can run behind different production transports.",
        ],
        agent_implications=[
            "Realtime Conversation Host should issue room/session data, not raw production audio sockets.",
            "Audio Producer and Observability Agent track transport type, latency, interruption, and playout evidence.",
        ],
        freshness_policy="Refresh before adding Pipecat processors or changing browser voice transport.",
        last_verified="2026-05-17",
    ),
    FoundationReference(
        reference_id="kokoro-82m-tts",
        title="Kokoro-82M text-to-speech model card",
        publisher="Hugging Face",
        url="https://huggingface.co/hexgrad/Kokoro-82M",
        reference_type="tts_provider_reference",
        applies_to=["audio-producer", "realtime-conversation-host"],
        architecture_decisions=[
            "Kokoro-82M is the default open-weight TTS layer for spoken responses and narration drafts.",
            "Kokoro output buffers must be cancellable when the user barges in.",
        ],
        agent_implications=[
            "Audio Producer records Kokoro voice preset, chunking policy, and output-buffer cancellation evidence.",
            "Realtime Conversation Host routes spoken output through the Gemma/Kokoro voice runtime by default.",
        ],
        freshness_policy="Refresh before changing default TTS model, supported voice presets, or streaming-buffer policy.",
        last_verified="2026-05-17",
    ),
    FoundationReference(
        reference_id="elevenlabs-tts-docs",
        title="ElevenLabs Text to Speech documentation",
        publisher="ElevenLabs",
        url="https://elevenlabs.io/docs/capabilities/text-to-speech",
        reference_type="tts_provider_reference",
        applies_to=["audio-producer", "realtime-conversation-host"],
        architecture_decisions=[
            "High-quality narration and TTS output are provider-pluggable rather than hard-coded to one model.",
            "Provider readiness reports show voice provider configuration without exposing secrets.",
        ],
        agent_implications=[
            "Audio Producer can plan polished narration separately from live dialogue transport.",
            "Observability Agent tracks provider fallback and missing configuration events.",
        ],
        freshness_policy="Refresh before changing ElevenLabs session setup, supported voice metadata, or TTS QA assumptions.",
        last_verified="2026-05-16",
    ),
    FoundationReference(
        reference_id="cartesia-tts-websocket",
        title="Cartesia Text to Speech WebSocket API",
        publisher="Cartesia",
        url="https://docs.cartesia.ai/api-reference/tts/tts",
        reference_type="tts_websocket_reference",
        applies_to=["audio-producer", "realtime-conversation-host"],
        architecture_decisions=[
            "Low-latency TTS is a pluggable realtime audio provider boundary.",
            "The product app records provider metadata and durable turns, not provider-specific secret state.",
        ],
        agent_implications=[
            "Audio Producer includes latency and resume criteria in audio briefs.",
            "Realtime Conversation Host keeps provider state visible in conversation briefs.",
        ],
        freshness_policy="Refresh before changing Cartesia WebSocket setup, voice ids, or latency assumptions.",
        last_verified="2026-05-16",
    ),
    FoundationReference(
        reference_id="anthropic-claude-subagents",
        title="Claude Code subagents",
        publisher="Anthropic",
        url="https://docs.anthropic.com/en/docs/claude-code/sub-agents",
        reference_type="subagent_context_reference",
        applies_to=["agent-harness-engineer", "context-engineering-agent", "critic-reviewer-agent"],
        architecture_decisions=[
            "Specialist agents need explicit roles, tool permissions, and isolated task context.",
            "Delegated work returns structured results to the main run instead of overwriting shared state.",
        ],
        agent_implications=[
            "Agent cards expose allowed tools, allowed models, inputs, outputs, and guardrails.",
            "Critic and reviewer agents operate as separate specialist contexts.",
        ],
        freshness_policy="Refresh before changing agent skill files, allowed tool policy, or specialist context boundaries.",
        last_verified="2026-05-16",
    ),
    FoundationReference(
        reference_id="ddia-data-intensive-systems",
        title="Designing Data-Intensive Applications",
        publisher="Martin Kleppmann",
        url="https://martin.kleppmann.com/2017/03/27/designing-data-intensive-applications.html",
        reference_type="data_system_design_reference",
        applies_to=[
            "principal-software-engineer",
            "backend-platform-engineer",
            "scalability-reliability-engineer",
            "observability-agent",
        ],
        architecture_decisions=[
            "The system separates source-of-truth data, durable events, checkpoints, derived read views, and generated artifacts.",
            "Reliability, scalability, maintainability, consistency, and fault tolerance are explicit design gates.",
        ],
        agent_implications=[
            "Backend Platform Engineer reviews schema evolution, idempotency, replay, and data consistency.",
            "Scalability/Reliability Engineer reviews load, backpressure, and degradation paths before always-on operation.",
        ],
        freshness_policy="Refresh before changing event-log semantics, durability boundaries, or high-scale data flow assumptions.",
        last_verified="2026-05-17",
    ),
    FoundationReference(
        reference_id="chip-huyen-ml-systems",
        title="Designing Machine Learning Systems",
        publisher="O'Reilly",
        url="https://www.oreilly.com/library/view/designing-machine-learning/9781098107956/",
        reference_type="ml_system_design_reference",
        applies_to=[
            "context-engineering-agent",
            "retrieval-intelligence-agent",
            "data-analyst-agent",
            "inference-systems-engineer",
            "observability-agent",
        ],
        architecture_decisions=[
            "ML and AI system quality depends on data quality, monitoring, evaluation, feedback loops, and production constraints.",
            "Retrieval and memory evaluation track precision, recall, false positives, false negatives, and drift.",
        ],
        agent_implications=[
            "Context Engineering Agent records memory health and retrieval metrics before long-running use.",
            "Retrieval Intelligence Agent treats FP/FN reduction and coverage gaps as first-class ledgers.",
        ],
        freshness_policy="Refresh before changing retrieval evaluation, memory policy gates, or model monitoring assumptions.",
        last_verified="2026-05-17",
    ),
    FoundationReference(
        reference_id="baseten-inference-engineering",
        title="Inference Engineering",
        publisher="Baseten",
        url="https://www.baseten.co/inference-engineering/",
        reference_type="inference_engineering_reference",
        applies_to=[
            "inference-systems-engineer",
            "audio-producer",
            "scalability-reliability-engineer",
            "observability-agent",
        ],
        architecture_decisions=[
            "Inference routes need latency and cost budgets before provider or model selection.",
            "Streaming, batching, cache reuse, model routing, and fallback policy are production concerns, not afterthoughts.",
        ],
        agent_implications=[
            "Inference Systems Engineer owns latency/cost budgets and provider-backed smoke plans.",
            "Observability Agent records provider fallback, latency, and readiness evidence in run ledgers.",
        ],
        freshness_policy="Refresh before changing model routing, batching, streaming, cache, or provider-fallback policy.",
        last_verified="2026-05-17",
    ),
    FoundationReference(
        reference_id="anthropic-effective-agents",
        title="Building effective agents",
        publisher="Anthropic",
        url="https://www.anthropic.com/engineering/building-effective-agents",
        reference_type="agent_architecture_reference",
        applies_to=[
            "agent-harness-engineer",
            "intent-router",
            "a2a-protocol-agent",
            "critic-reviewer-agent",
            "guardrails-agent",
        ],
        architecture_decisions=[
            "Use simple workflows and explicit routing before increasing autonomous complexity.",
            "Agents need clear success criteria, tool specifications, feedback loops, and human oversight.",
        ],
        agent_implications=[
            "Intent Router decomposes work into typed specialist paths rather than one giant autonomous prompt.",
            "Critic/Reviewer Agent and Guardrails Agent provide independent review before publishing.",
        ],
        freshness_policy="Refresh before changing orchestration patterns, reviewer loops, or autonomous-work criteria.",
        last_verified="2026-05-17",
    ),
    FoundationReference(
        reference_id="openai-practical-agents-guardrails",
        title="A practical guide to building agents",
        publisher="OpenAI",
        url="https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/",
        reference_type="agent_guardrails_reference",
        applies_to=[
            "guardrails-agent",
            "product-manager",
            "realtime-conversation-host",
            "observability-agent",
        ],
        architecture_decisions=[
            "Guardrails are layered across input, tool use, model output, data privacy, and approval gates.",
            "Human feedback and operational edge cases should evolve guardrails over time.",
        ],
        agent_implications=[
            "Guardrails Agent blocks unsupported claims, unsafe content, and provenance gaps before final output.",
            "Product Manager keeps user feedback gates and acceptance criteria visible in run state.",
        ],
        freshness_policy="Refresh before changing guardrail gates, approval criteria, or realtime session safety controls.",
        last_verified="2026-05-17",
    ),
    FoundationReference(
        reference_id="aws-ml-lens",
        title="Machine Learning Lens - AWS Well-Architected Framework",
        publisher="AWS",
        url="https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/machine-learning-lens.html",
        reference_type="well_architected_ml_reference",
        applies_to=[
            "scalability-reliability-engineer",
            "backend-platform-engineer",
            "observability-agent",
            "product-manager",
        ],
        architecture_decisions=[
            "ML workloads need explicit operational excellence, reliability, security, cost, and performance reviews.",
            "Production readiness includes workload design, deployment, monitoring, and continuous improvement.",
        ],
        agent_implications=[
            "Scalability/Reliability Engineer treats cost, performance, and reliability as acceptance gates.",
            "Observability Agent records runtime health and provider readiness as operational evidence.",
        ],
        freshness_policy="Refresh before changing production-readiness, cost, or reliability gates for ML workloads.",
        last_verified="2026-05-17",
    ),
    FoundationReference(
        reference_id="google-cloud-ai-ml-reliability",
        title="AI and ML perspective: Reliability",
        publisher="Google Cloud",
        url="https://docs.cloud.google.com/architecture/framework/perspectives/ai-ml/reliability",
        reference_type="ai_ml_reliability_reference",
        applies_to=[
            "scalability-reliability-engineer",
            "inference-systems-engineer",
            "observability-agent",
            "agent-harness-engineer",
        ],
        architecture_decisions=[
            "AI/ML systems should be modular, loosely coupled, observable, governed, scalable, and highly available.",
            "Always-on agents need SRE-style reliability practices and automated runtime evidence.",
        ],
        agent_implications=[
            "Scalability/Reliability Engineer owns SLOs, capacity, and high-availability assumptions.",
            "Agent Harness Engineer stops autonomous work when runtime or memory policy gates are unsafe.",
        ],
        freshness_policy="Refresh before changing SLOs, autonomous runtime gates, or high-availability assumptions.",
        last_verified="2026-05-17",
    ),
    FoundationReference(
        reference_id="uber-michelangelo-ml-platform",
        title="Meet Michelangelo: Uber's Machine Learning Platform",
        publisher="Uber Engineering",
        url="https://www.uber.com/ie/en/blog/michelangelo-machine-learning-platform/",
        reference_type="ml_platform_reference",
        applies_to=[
            "context-engineering-agent",
            "retrieval-intelligence-agent",
            "data-analyst-agent",
            "artifact-librarian",
        ],
        architecture_decisions=[
            "Shared curated data and feature layers reduce duplicated ML work and improve consistency.",
            "Model, data, feature, and artifact provenance should be versioned and discoverable.",
        ],
        agent_implications=[
            "Artifact Librarian indexes sources, artifacts, memory, and model provenance for reuse.",
            "Data Analyst Agent structures evidence so content and retrieval agents reuse canonical facts.",
        ],
        freshness_policy="Refresh before changing shared memory, feature-like evidence stores, or artifact provenance policy.",
        last_verified="2026-05-17",
    ),
    FoundationReference(
        reference_id="netflix-metaflow-ml-platform",
        title="What is Metaflow",
        publisher="Metaflow/Netflix",
        url="https://docs.metaflow.org/introduction/what-is-metaflow",
        reference_type="workflow_platform_reference",
        applies_to=[
            "agent-harness-engineer",
            "backend-platform-engineer",
            "context-engineering-agent",
            "artifact-librarian",
        ],
        architecture_decisions=[
            "Data-intensive ML/AI work benefits from workflow abstractions that bridge prototype and production.",
            "Artifacts, data, code, compute, and deployment state should remain traceable across lifecycle stages.",
        ],
        agent_implications=[
            "Agent Harness Engineer keeps worker profiles, checkpoints, and run artifacts tied to durable workflows.",
            "Context Engineering Agent and Artifact Librarian keep context and artifacts reusable across runs.",
        ],
        freshness_policy="Refresh before changing workflow lifecycle, artifact storage, or production deployment assumptions.",
        last_verified="2026-05-17",
    ),
)


def list_foundation_references() -> FoundationReferenceResult:
    publishers = sorted({reference.publisher for reference in FOUNDATION_REFERENCES})
    decisions = sorted(
        {
            decision
            for reference in FOUNDATION_REFERENCES
            for decision in reference.architecture_decisions
        }
    )
    return FoundationReferenceResult(
        references=list(FOUNDATION_REFERENCES),
        required_publishers=publishers,
        covered_decisions=decisions,
        summary=(
            f"{len(FOUNDATION_REFERENCES)} official foundation reference(s) "
            "map provider, protocol, persistence, memory, realtime audio, "
            "subagent, data-system, ML-system, inference, and reliability "
            "guidance to architecture decisions."
        ),
    )
