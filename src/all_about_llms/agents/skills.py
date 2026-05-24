from all_about_llms.contracts import AgentSkillCard


CONVERSATION_HARNESS = "agent-studio-conversation-harness"
RESEARCH_GROUNDING = "agent-studio-research-grounding"
RETRIEVAL_INTELLIGENCE = "agent-studio-retrieval-intelligence"
CONTENT_PRODUCTION = "agent-studio-content-production"
MEDIA_DESIGN = "agent-studio-media-design"
GUARDRAILS_REVIEW = "agent-studio-guardrails-review"
SYSTEM_ARCHITECTURE = "agent-studio-system-architecture"
FRONTEND_ENGINEERING = "agent-studio-frontend-engineering"
INFERENCE_RELIABILITY = "agent-studio-inference-reliability"


AGENT_SKILL_IDS: dict[str, tuple[str, ...]] = {
    "realtime-conversation-host": (CONVERSATION_HARNESS,),
    "intent-router": (CONVERSATION_HARNESS,),
    "forward-deployed-engineer": (CONVERSATION_HARNESS, CONTENT_PRODUCTION),
    "principal-software-engineer": (
        SYSTEM_ARCHITECTURE,
        CONVERSATION_HARNESS,
        GUARDRAILS_REVIEW,
    ),
    "backend-platform-engineer": (
        SYSTEM_ARCHITECTURE,
        CONVERSATION_HARNESS,
        GUARDRAILS_REVIEW,
    ),
    "frontend-experience-engineer": (
        FRONTEND_ENGINEERING,
        CONVERSATION_HARNESS,
        MEDIA_DESIGN,
    ),
    "scalability-reliability-engineer": (
        SYSTEM_ARCHITECTURE,
        INFERENCE_RELIABILITY,
        GUARDRAILS_REVIEW,
    ),
    "inference-systems-engineer": (
        INFERENCE_RELIABILITY,
        SYSTEM_ARCHITECTURE,
        CONVERSATION_HARNESS,
    ),
    "agent-harness-engineer": (
        SYSTEM_ARCHITECTURE,
        CONVERSATION_HARNESS,
        GUARDRAILS_REVIEW,
    ),
    "a2a-protocol-agent": (SYSTEM_ARCHITECTURE, CONVERSATION_HARNESS),
    "context-engineering-agent": (
        SYSTEM_ARCHITECTURE,
        CONVERSATION_HARNESS,
        RESEARCH_GROUNDING,
    ),
    "web-research-agent": (RESEARCH_GROUNDING, RETRIEVAL_INTELLIGENCE),
    "retrieval-intelligence-agent": (RETRIEVAL_INTELLIGENCE, RESEARCH_GROUNDING),
    "knowledge-graph-curator-agent": (RETRIEVAL_INTELLIGENCE, RESEARCH_GROUNDING),
    "source-ledger-agent": (RESEARCH_GROUNDING, RETRIEVAL_INTELLIGENCE),
    "claim-verification-agent": (
        RESEARCH_GROUNDING,
        RETRIEVAL_INTELLIGENCE,
        GUARDRAILS_REVIEW,
    ),
    "data-analyst-agent": (RESEARCH_GROUNDING, RETRIEVAL_INTELLIGENCE),
    "content-strategist": (CONTENT_PRODUCTION, RESEARCH_GROUNDING),
    "eli5-short-form-writer": (CONTENT_PRODUCTION,),
    "substack-essay-writer": (CONTENT_PRODUCTION,),
    "script-doctor": (CONTENT_PRODUCTION,),
    "editor-in-chief": (CONTENT_PRODUCTION, GUARDRAILS_REVIEW),
    "influencer-strategy-agent": (CONTENT_PRODUCTION,),
    "platform-optimization-agent": (CONTENT_PRODUCTION,),
    "outreach-agent": (CONTENT_PRODUCTION,),
    "lead-ui-ux-designer": (MEDIA_DESIGN, FRONTEND_ENGINEERING),
    "interactive-systems-designer": (MEDIA_DESIGN, FRONTEND_ENGINEERING),
    "visual-director": (MEDIA_DESIGN, CONTENT_PRODUCTION),
    "image-generation-agent": (MEDIA_DESIGN,),
    "audio-producer": (MEDIA_DESIGN, CONVERSATION_HARNESS, INFERENCE_RELIABILITY),
    "video-reel-producer": (MEDIA_DESIGN, CONTENT_PRODUCTION),
    "guardrails-agent": (GUARDRAILS_REVIEW,),
    "product-manager": (CONVERSATION_HARNESS, GUARDRAILS_REVIEW),
    "critic-reviewer-agent": (GUARDRAILS_REVIEW, CONTENT_PRODUCTION),
    "observability-agent": (
        GUARDRAILS_REVIEW,
        CONVERSATION_HARNESS,
        INFERENCE_RELIABILITY,
    ),
    "interactive-note-taking-agent": (MEDIA_DESIGN, CONVERSATION_HARNESS),
    "artifact-librarian": (MEDIA_DESIGN, RESEARCH_GROUNDING, RETRIEVAL_INTELLIGENCE),
    "sprint-progress-agent": (CONVERSATION_HARNESS, GUARDRAILS_REVIEW),
}


def _agents_for(skill_id: str) -> list[str]:
    return [
        agent_id
        for agent_id, skill_ids in AGENT_SKILL_IDS.items()
        if skill_id in skill_ids
    ]


SKILL_CARDS: tuple[AgentSkillCard, ...] = (
    AgentSkillCard(
        id=CONVERSATION_HARNESS,
        name="Agent Studio Conversation Harness",
        description=(
            "Routes natural voice/text dialogue into durable A2A messages, "
            "conversation turns, run events, feedback gates, and resumable worker "
            "activity."
        ),
        applies_to_agents=_agents_for(CONVERSATION_HARNESS),
        capabilities=[
            "natural_dialogue_routing",
            "realtime_session_briefing",
            "durable_intent_route_plans",
            "durable_turn_recording",
            "human_feedback_gates",
            "worker_status_updates",
        ],
        workflow_steps=[
            "Preserve the user's natural wording and modality.",
            "Record each meaningful turn with run metadata.",
            "Let Realtime Conversation Host worker tasks persist `realtime_conversation_brief` artifacts with session, interruption, voice feedback, and handoff state.",
            "Let specialists persist `multimodal_review` artifacts when they process routed `review_multimodal_intake` tasks.",
            "Materialize idempotent follow-up AgentMessage handoffs from completed multimodal reviews unless a human feedback gate is open.",
            "Route semantic work through the Intent Router or specialist A2A tasks.",
            "Persist `conversation_handoff` artifacts for live turns routed to the Intent Router.",
            "Let Intent Router worker tasks persist `intent_route_plan` artifacts and materialize specialist handoffs from live dialogue.",
            "Audit A2A agent cards, skills, model/tool boundaries, and handoffs when protocol tasks arrive.",
            "Route suggestions from the separate planning HTML through `/api/planning/feedback` when they should become durable agent work.",
            "Route referenced screenshots, images, audio, video, reels, documents, or text snippets through `/api/runs/{run_id}/multimodal-intake` when they need specialist analysis.",
            "Open or resolve feedback gates when human preference controls progress.",
            "Let Forward Deployed Engineer tasks persist feedback requirements, acceptance criteria, and specialist handoffs.",
            "Let Principal Software Engineer tasks persist architecture reviews across durability, worker coverage, and provider boundaries.",
            "Persist reusable context packet artifacts for long-running or resumed specialist agents.",
            "Let the Agent Harness Engineer create checkpointed run resume-plan artifacts when long-running work needs recovery context.",
            "Build run replay ledgers when checkpoint-to-event deltas are needed for time-travel debugging.",
            "Let Product Manager and Sprint/Progress worker tasks build sync pulses and work plans from durable run state.",
            "Let autonomous studio passes run a bounded multimodal follow-up continuation cycle when review follow-up tasks are pending.",
            "Emit timeline events for every durable state transition.",
        ],
        required_inputs=["user_transcript", "run_state", "modality"],
        outputs=[
            "conversation_turn",
            "conversation_handoff",
            "realtime_conversation_brief",
            "agent_message",
            "intent_route_plan",
            "a2a_contract_audit",
            "context_packet",
            "run_resume_plan",
            "run_replay_ledger",
            "multimodal_intake_ledger",
            "multimodal_review",
            "feedback_item",
            "feedback_requirements",
            "architecture_review",
            "sync_pulse",
            "work_plan",
            "run_event",
        ],
        guardrails=[
            "Keep the product app a live conversational studio.",
            "Keep planning HTML outside the product app.",
            "Use Postgres durability for run state and feedback.",
        ],
        source_path="skills/agent-studio-conversation-harness/SKILL.md",
    ),
    AgentSkillCard(
        id=RESEARCH_GROUNDING,
        name="Agent Studio Research Grounding",
        description=(
            "Grounds content in real sources, source ledgers, freshness checks, "
            "claim extraction, and evidence mapping before approval."
        ),
        applies_to_agents=_agents_for(RESEARCH_GROUNDING),
        capabilities=[
            "web_research",
            "source_ledger",
            "claim_extraction",
            "freshness_check",
            "unsupported_claim_marking",
        ],
        workflow_steps=[
            "Search current primary or high-quality sources before drafting.",
            "Record usable sources with citation ids and retrieval metadata.",
            "Extract important factual claims into durable claim records.",
            "Map claims to sources or mark them unsupported.",
            "Build research freshness ledgers after discovery or source repair.",
            "Let Source Ledger worker tasks refresh source, claim, artifact, quality, and freshness snapshots.",
            "Let Context Engineering worker tasks persist retrieval-aware context packets for target agents.",
            "Use the Data Analyst worker to turn sources, claims, and artifacts into a reusable data brief.",
            "Let Artifact Librarian worker tasks persist retrieval facets and provenance gaps as an artifact index.",
            "Pass grounded briefs to content and review agents.",
        ],
        required_inputs=["topic", "freshness_policy", "run_state"],
        outputs=[
            "research_brief",
            "research_freshness_ledger",
            "data_brief",
            "source_record",
            "source_ledger_snapshot",
            "artifact_index",
            "context_packet",
            "claim_record",
            "unsupported_claim_report",
        ],
        guardrails=[
            "Do not invent facts.",
            "Use current web search for time-sensitive claims.",
            "Keep citation ids stable within a run.",
        ],
        source_path="skills/agent-studio-research-grounding/SKILL.md",
    ),
    AgentSkillCard(
        id=CONTENT_PRODUCTION,
        name="Agent Studio Content Production",
        description=(
            "Turns grounded briefs into source-backed social posts, ELI5 reels, "
            "platform variants, and detailed-plus-ELI5 Substack drafts."
        ),
        applies_to_agents=_agents_for(CONTENT_PRODUCTION),
        capabilities=[
            "eli5_writing",
            "social_post_drafting",
            "reel_scripting",
            "substack_writing",
            "platform_packaging",
        ],
        workflow_steps=[
            "Start from a grounded brief and source ledger.",
            "Choose channel-native structure for post, reel, carousel, or Substack.",
            "Draft simple short-form and detailed long-form variants.",
            "Attach source citations, claim trace, prompt input, model/provider provenance, and initial guardrail review state to first-draft artifacts.",
            "Route hooks and pacing through Script Doctor.",
            "Use Forward Deployed Engineer requirement artifacts as the source of truth for feedback-driven revisions.",
            "Send drafts through editorial, claim, guardrail, and growth review.",
        ],
        required_inputs=["grounded_brief", "source_ids", "claim_ids", "user_goal"],
        outputs=[
            "post",
            "reel_script",
            "substack_draft",
            "platform_variants",
            "revision_notes",
            "feedback_requirements",
        ],
        guardrails=[
            "Keep unsupported claims out of final drafts.",
            "Preserve source and claim provenance.",
            "Record user feedback as revision history.",
        ],
        source_path="skills/agent-studio-content-production/SKILL.md",
    ),
    AgentSkillCard(
        id=RETRIEVAL_INTELLIGENCE,
        name="Agent Studio Retrieval Intelligence",
        description=(
            "Optimizes retrieval quality with query rewriting, hybrid search, "
            "rank fusion, reranking, graph traversal, knowledge graph coverage, "
            "and false-positive/false-negative reduction."
        ),
        applies_to_agents=_agents_for(RETRIEVAL_INTELLIGENCE),
        capabilities=[
            "query_rewriting",
            "hybrid_candidate_generation",
            "reciprocal_rank_fusion",
            "cross_encoder_reranking",
            "knowledge_graph_traversal",
            "coverage_gap_detection",
            "false_positive_false_negative_reduction",
        ],
        workflow_steps=[
            "Rewrite the user topic into exact, semantic, freshness, and entity-focused retrieval queries.",
            "Generate candidates from web search, sparse/full-text retrieval, dense pgvector retrieval, metadata filters, and graph traversal.",
            "Fuse candidate lists with Reciprocal Rank Fusion before expensive reranking.",
            "Rerank the fused top candidates with a cross-encoder, late-interaction model, or deterministic fallback score when providers are unavailable.",
            "Build entity, claim, source, artifact, and topic graph coverage records for multi-hop and source-diversity review.",
            "Record precision risks, recall gaps, stale/weak evidence, and missing coverage before synthesis.",
            "Pass only accepted evidence into context packets and drafting prompts; keep unsupported claims explicitly labeled.",
        ],
        required_inputs=["topic", "source_records", "claim_records", "artifact_records"],
        outputs=[
            "retrieval_quality_ledger",
            "retrieval_candidates",
            "rerank_decisions",
            "knowledge_graph_nodes",
            "knowledge_graph_edges",
            "coverage_gaps",
            "recommended_queries",
        ],
        guardrails=[
            "Do not let a single retrieval signal decide factual support.",
            "Do not hide low-precision or low-recall risks from content agents.",
            "Block final synthesis when accepted source coverage is below the configured threshold.",
        ],
        source_path="skills/agent-studio-retrieval-intelligence/SKILL.md",
    ),
    AgentSkillCard(
        id=MEDIA_DESIGN,
        name="Agent Studio Media Design",
        description=(
            "Plans visuals, audio, reels, image generation prompts, UI critique, "
            "and separate interactive HTML planning surfaces."
        ),
        applies_to_agents=_agents_for(MEDIA_DESIGN),
        capabilities=[
            "visual_direction",
            "storyboarding",
            "voice_direction",
            "imagegen_prompting",
            "interactive_html_planning",
        ],
        workflow_steps=[
            "Classify the work as product UI, media output, or planning HTML.",
            "Keep planning artifacts separate from the product app.",
            "Route saved planning HTML suggestions through the planning feedback intake when a run id is available.",
            "Generate Obsidian-native run review notes from durable run state when note-taking tasks arrive.",
            "Generate standalone interactive HTML run notes only as companion views.",
            "Use the Artifact Librarian worker to index artifact provenance, revision edges, media assets, and retrieval facets.",
            "Let Lead UI/UX Designer worker tasks persist UX reviews for cockpit flow, planning boundary, voice controls, feedback state, and source/artifact visibility.",
            "Let Interactive Systems Designer worker tasks persist planning-surface reviews from the standalone HTML, embedded JSON state, interactions, boundaries, and planning feedback.",
            "Record `multimodal_intake_ledger` artifacts when incoming screenshots, images, audio, voice, video, reels, or documents need analysis before media planning.",
            "Record `multimodal_review` artifacts when a specialist consumes those intake tasks and leaves asset-specific decisions.",
            "Create idempotent follow-up handoffs from completed multimodal reviews so the next specialist can continue the asset-aware workflow.",
            "Let Visual Director worker tasks persist source-linked visual briefs for thumbnails, diagrams, carousels, image prompts, and reel scenes.",
            "Let Image Generation Agent worker tasks persist source-linked imagegen prompt packs before raster generation is invoked.",
            "Let Audio Producer worker tasks persist source-linked realtime/TTS audio briefs before provider playback is invoked.",
            "Let Video/Reel Producer worker tasks persist source-linked reel storyboards with scene timing, subtitles, media dependencies, and QA checks.",
            "Route raster visual generation through the imagegen boundary.",
            "Specify storyboard, captions, timing, and asset requirements for reels.",
            "Define audio voice, pacing, pronunciation, and QA criteria.",
        ],
        required_inputs=["content_brief", "artifact_context", "surface_boundary"],
        outputs=[
            "visual_brief",
            "visual_system_brief",
            "imagegen_prompt",
            "imagegen_prompt_pack",
            "storyboard",
            "reel_storyboard",
            "audio_brief",
            "realtime_audio_plan",
            "multimodal_intake_ledger",
            "multimodal_review",
            "planning_html_spec",
            "obsidian_note",
            "interactive_note",
            "artifact_index",
            "ux_review",
            "planning_surface_review",
        ],
        guardrails=[
            "Use imagegen only for raster generation or editing.",
            "Do not place planning HTML inside the product app.",
            "Store prompt and asset provenance for generated media.",
        ],
        source_path="skills/agent-studio-media-design/SKILL.md",
    ),
    AgentSkillCard(
        id=SYSTEM_ARCHITECTURE,
        name="Agent Studio System Architecture",
        description=(
            "Applies production system-design patterns to service boundaries, "
            "durable data, orchestration, event logs, Postgres/pgvector, A2A "
            "contracts, reliability, and scale planning."
        ),
        applies_to_agents=_agents_for(SYSTEM_ARCHITECTURE),
        capabilities=[
            "data_intensive_architecture",
            "service_boundary_design",
            "durable_event_contracts",
            "schema_evolution",
            "fault_tolerance",
            "architecture_decision_records",
        ],
        workflow_steps=[
            "Start from the Obsidian HLD, LLD, Decision Log, and current sprint before changing architecture.",
            "Separate source-of-truth state, event streams, checkpoints, derived artifacts, and generated planning views.",
            "Design every write path for idempotency, provenance, schema evolution, replay, and failure recovery.",
            "Keep Postgres + pgvector as the local-first durable store; do not add SQLite or local JSON state substitutes.",
            "Use A2A-style contracts for specialist boundaries and explicit handoff rules.",
            "Define reliability, scalability, maintainability, and operability impacts before introducing a new component.",
            "Record architecture decisions in Obsidian and surface implementation evidence through foundation audits.",
        ],
        required_inputs=["hld", "lld", "run_state", "decision_log"],
        outputs=[
            "architecture_decision",
            "service_contract",
            "data_flow_review",
            "failure_mode_review",
            "scalability_plan",
            "foundation_audit_evidence",
        ],
        guardrails=[
            "Do not introduce a second source of truth for run state.",
            "Do not hide irreversible architecture decisions in chat.",
            "Block designs that cannot be resumed, replayed, or audited.",
        ],
        source_path="skills/agent-studio-system-architecture/SKILL.md",
    ),
    AgentSkillCard(
        id=FRONTEND_ENGINEERING,
        name="Agent Studio Frontend Engineering",
        description=(
            "Implements the conversational studio UI, voice controls, source "
            "ledger views, artifact previews, feedback gates, accessibility, "
            "and generated planning viewers as separate surfaces."
        ),
        applies_to_agents=_agents_for(FRONTEND_ENGINEERING),
        capabilities=[
            "conversational_cockpit_ui",
            "voice_control_ui",
            "event_stream_rendering",
            "source_ledger_drilldowns",
            "feedback_gate_controls",
            "accessibility_review",
        ],
        workflow_steps=[
            "Treat the product app as a live voice/text content studio, not a planning tracker.",
            "Keep Obsidian planning views and generated HTML viewers outside the product workflow.",
            "Render provider readiness, run timeline, source ledger, artifact state, and feedback gates from durable APIs.",
            "Use responsive, accessible controls for voice, text, source inspection, and approvals.",
            "Validate frontend changes with syntax checks and browser smoke tests when UI files change.",
            "Record UI boundary decisions and operator feedback in Obsidian before broad redesigns.",
        ],
        required_inputs=["ui_goal", "run_state", "artifact_records", "feedback_items"],
        outputs=[
            "frontend_implementation_plan",
            "ui_state_contract",
            "accessibility_notes",
            "cockpit_surface_review",
            "browser_smoke_result",
        ],
        guardrails=[
            "Do not add a project-management board to the product app.",
            "Do not mix planning workspace controls into the end-user cockpit.",
            "Keep visible UI text concise and task-oriented.",
        ],
        source_path="skills/agent-studio-frontend-engineering/SKILL.md",
    ),
    AgentSkillCard(
        id=INFERENCE_RELIABILITY,
        name="Agent Studio Inference Reliability",
        description=(
            "Owns model/provider routing, latency and cost budgets, streaming, "
            "batching, caching, fallback policy, provider readiness, realtime "
            "audio smoke tests, and Gemma/HF inference operations."
        ),
        applies_to_agents=_agents_for(INFERENCE_RELIABILITY),
        capabilities=[
            "model_routing",
            "latency_budgeting",
            "provider_readiness",
            "streaming_inference",
            "fallback_policy",
            "cost_and_capacity_review",
        ],
        workflow_steps=[
            "Define latency, cost, quality, and modality requirements before selecting a provider or model route.",
            "Keep realtime speech transport separate from Gemma expert reasoning and multimodal synthesis.",
            "Use provider-backed smoke evidence for the Gemma/Kokoro LiveKit voice path, optional Pipecat processors, optional proprietary voice providers, HF/Gemma, web search, and reranking readiness.",
            "Track batching, streaming, cache, warm-pool, fallback, timeout, and retry implications for each route.",
            "Record provider provenance, fallback decisions, and smoke results in ledgers before marking a route production-ready.",
            "Escalate to human review when provider evidence is rehearsal-only or when a fallback changes artifact quality.",
        ],
        required_inputs=["provider_config", "run_state", "model_route", "latency_budget"],
        outputs=[
            "inference_route_review",
            "provider_smoke_plan",
            "latency_cost_budget",
            "fallback_decision",
            "provider_operations_ledger",
            "model_routing_ledger",
        ],
        guardrails=[
            "Do not count provider-free rehearsal as provider-backed readiness.",
            "Do not let Gemma own realtime voice transport.",
            "Do not persist provider secrets in events, artifacts, or source ledgers.",
        ],
        source_path="skills/agent-studio-inference-reliability/SKILL.md",
    ),
    AgentSkillCard(
        id=GUARDRAILS_REVIEW,
        name="Agent Studio Guardrails Review",
        description=(
            "Checks source coverage, unsupported claims, provenance, safety, "
            "copyright risk, model/tool boundaries, and approval readiness."
        ),
        applies_to_agents=_agents_for(GUARDRAILS_REVIEW),
        capabilities=[
            "source_coverage_review",
            "provenance_review",
            "unsupported_claim_detection",
            "safety_review",
            "approval_gate_decision",
        ],
        workflow_steps=[
            "Check that important claims link to sources or are marked unsupported.",
            "Verify artifact provenance includes inputs, model/tool, and reviewers.",
            "Confirm unresolved feedback blocks final approval.",
            "Check model/tool boundary violations.",
            "Record architecture reviews when durability, worker coverage, provider boundary, or feedback-gate risks need engineering triage.",
            "Record run health reports when failures, fallbacks, denials, or open blockers appear.",
            "Build skill usage ledgers when worker invocation evidence or skill source/card alignment needs review.",
            "Build model routing ledgers when Gemma/HF expert use, realtime audio, web search, or imagegen boundaries need review.",
            "Build provider operations ledgers when model/tool decisions, provider fallbacks, realtime sessions, or provider provenance need manager review.",
            "Build foundation audits when architecture completeness or implementation readiness needs requirement-level evidence.",
            "Return approved, approved_with_notes, needs_revision, or blocked.",
        ],
        required_inputs=["artifact_records", "claim_records", "feedback_items"],
        outputs=[
            "guardrails_report",
            "review_decision",
            "blocking_issues",
            "architecture_review",
            "run_health_report",
            "skill_usage_ledger",
            "model_routing_ledger",
            "provider_operations_ledger",
            "foundation_audit",
            "next_action",
        ],
        guardrails=[
            "Do not approve artifacts with missing source dependencies.",
            "Do not hide weak evidence in prose.",
            "Escalate unresolved user feedback to a human gate.",
        ],
        source_path="skills/agent-studio-guardrails-review/SKILL.md",
    ),
)

SKILL_CARD_BY_ID = {skill.id: skill for skill in SKILL_CARDS}


def list_skill_cards() -> tuple[AgentSkillCard, ...]:
    return SKILL_CARDS


def get_skill_card(skill_id: str) -> AgentSkillCard | None:
    return SKILL_CARD_BY_ID.get(skill_id)


def skill_ids_for_agent(agent_id: str) -> list[str]:
    return list(AGENT_SKILL_IDS.get(agent_id, ()))


def skill_cards_for_agent(agent_id: str) -> list[AgentSkillCard]:
    return [
        SKILL_CARD_BY_ID[skill_id]
        for skill_id in skill_ids_for_agent(agent_id)
        if skill_id in SKILL_CARD_BY_ID
    ]
