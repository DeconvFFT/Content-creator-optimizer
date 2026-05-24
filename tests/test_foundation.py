import json
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from all_about_llms.agents import (
    AGENT_ROSTER,
    SKILL_CARDS,
    get_agent_card,
    get_skill_card,
    skill_cards_for_agent,
)
from all_about_llms.app import app
from all_about_llms.foundation_references import list_foundation_references
from all_about_llms.model_routing import list_model_routes
from all_about_llms.orchestration import (
    CONCRETE_WORKER_EXECUTOR_AGENT_IDS,
    DEFAULT_WORKER_AGENT_IDS,
    build_foundation_graph,
)


ROOT = Path(__file__).resolve().parents[1]


def test_agent_roster_contains_all_foundation_agents():
    assert len(AGENT_ROSTER) == 38
    assert get_agent_card("realtime-conversation-host") is not None
    assert get_agent_card("image-generation-agent").allowed_tools == ["imagegen"]
    assert get_agent_card("backend-platform-engineer") is not None
    assert get_agent_card("frontend-experience-engineer") is not None
    assert get_agent_card("scalability-reliability-engineer") is not None
    assert get_agent_card("inference-systems-engineer") is not None
    assert get_agent_card("retrieval-intelligence-agent") is not None
    assert get_agent_card("knowledge-graph-curator-agent") is not None
    assert get_agent_card("sprint-progress-agent") is not None
    assert all(agent.skill_ids for agent in AGENT_ROSTER)


def test_default_worker_roster_requires_concrete_executor_coverage():
    roster_agent_ids = {agent.id for agent in AGENT_ROSTER}
    default_worker_agent_ids = set(DEFAULT_WORKER_AGENT_IDS)
    assert default_worker_agent_ids == roster_agent_ids
    assert CONCRETE_WORKER_EXECUTOR_AGENT_IDS == roster_agent_ids
    assert "retrieval-intelligence-agent" in CONCRETE_WORKER_EXECUTOR_AGENT_IDS
    assert "knowledge-graph-curator-agent" in CONCRETE_WORKER_EXECUTOR_AGENT_IDS


def test_agent_cards_have_required_a2a_fields():
    required_fields = {
        "id",
        "name",
        "role",
        "capabilities",
        "allowed_models",
        "allowed_tools",
        "inputs",
        "outputs",
        "handoff_rules",
        "guardrails",
        "skill_ids",
    }
    for agent in AGENT_ROSTER:
        payload = agent.model_dump()
        assert required_fields <= payload.keys()
        assert payload["capabilities"]
        assert payload["outputs"]
        assert payload["guardrails"]
        assert payload["skill_ids"]


def test_agent_skill_cards_map_project_skills_to_agents():
    assert len(SKILL_CARDS) == 9
    assert get_skill_card("agent-studio-content-production") is not None
    assert get_skill_card("agent-studio-retrieval-intelligence") is not None
    assert get_skill_card("agent-studio-system-architecture") is not None
    assert get_skill_card("agent-studio-frontend-engineering") is not None
    assert get_skill_card("agent-studio-inference-reliability") is not None
    assert {
        skill.id for skill in skill_cards_for_agent("content-strategist")
    } == {
        "agent-studio-content-production",
        "agent-studio-research-grounding",
    }
    assert {
        skill.id for skill in skill_cards_for_agent("retrieval-intelligence-agent")
    } == {
        "agent-studio-retrieval-intelligence",
        "agent-studio-research-grounding",
    }
    assert {
        skill.id for skill in skill_cards_for_agent("frontend-experience-engineer")
    } == {
        "agent-studio-frontend-engineering",
        "agent-studio-conversation-harness",
        "agent-studio-media-design",
    }
    for skill in SKILL_CARDS:
        assert skill.applies_to_agents
        assert skill.workflow_steps
        assert skill.source_path.startswith("skills/")
    covered_agents = {
        agent_id
        for skill in SKILL_CARDS
        for agent_id in skill.applies_to_agents
    }
    assert covered_agents == {agent.id for agent in AGENT_ROSTER}


def test_model_routes_keep_voice_and_openrouter_boundaries_separate():
    routes = {route.task: route for route in list_model_routes()}
    assert routes["live_conversation"].primary_model == (
        "OpenRouter deepseek/deepseek-v4-flash plus hexgrad/Kokoro-82M over LiveKit"
    )
    assert routes["deep_reasoning_and_planning"].primary_model == (
        "OpenRouter deepseek/deepseek-v4-flash"
    )
    assert "voice transport" in routes["live_conversation"].provider_boundary
    assert "raw microphone PCM" in routes["live_conversation"].provider_boundary
    assert "Kokoro handles speech output" in routes[
        "live_conversation"
    ].provider_boundary


def test_fastapi_app_exposes_foundation_routes():
    paths = set(app.openapi()["paths"].keys())
    assert "/api/agents" in paths
    assert "/.well-known/agent-card.json" in paths
    assert "/.well-known/agent-cards.json" in paths
    assert "/.well-known/agent-skills.json" in paths
    assert "/api/a2a" in paths
    assert "/api/skills" in paths
    assert "/api/skills/{skill_id}" in paths
    assert "/api/a2a/agents/{agent_id}/card" in paths
    assert "/api/a2a/agents/{agent_id}/skills" in paths
    assert "/api/a2a/messages" in paths
    assert "/api/a2a/messages/{message_id}" in paths
    assert "/api/a2a/messages/{message_id}/status" in paths
    assert "/api/a2a/messages/{message_id}/retry" in paths
    assert "/api/a2a/messages/{message_id}/dependencies/repair" in paths
    assert "/api/a2a/agents/{agent_id}/inbox" in paths
    assert "/api/a2a/workers/{agent_id}/run" in paths
    assert "/api/a2a/workers/run-cycle" in paths
    assert "/api/conversation/turns" in paths
    assert "/api/provider-readiness" in paths
    assert "/api/foundation/references" in paths
    assert "/api/runs/{run_id}/worker-profiles" in paths
    assert "/api/worker-profiles/{profile_id}/start" in paths
    assert "/api/worker-profiles/{profile_id}/stop" in paths
    assert "/api/worker-profiles/{profile_id}/heartbeat" in paths
    assert "/api/runs/{run_id}/autopilot-launch" in paths
    assert "/api/worker-profiles/scheduler/run" in paths
    assert "/api/worker-scheduler-process" in paths
    assert "/api/worker-scheduler-process/start" in paths
    assert "/api/worker-scheduler-process/stop" in paths
    assert "/api/runs/{run_id}/agent-messages" in paths
    assert "/api/runs/{run_id}/checkpoints" in paths
    assert "/api/runs/{run_id}/resume-plan" in paths
    assert "/api/runs/{run_id}/resume" in paths
    assert "/api/runs/{run_id}/replay-ledger" in paths
    assert "/api/runs/{run_id}/work-plan" in paths
    assert "/api/runs/{run_id}/sync-pulse" in paths
    assert "/api/runs/{run_id}/context-packet" in paths
    assert "/api/runs/{run_id}/skill-usage-ledger" in paths
    assert "/api/model-routing" in paths
    assert "/api/boundaries" in paths
    assert "/api/runs" in paths
    assert "/api/runs/{run_id}/conversation-turns" in paths
    assert "/api/runs/{run_id}/human-feedback-gate" in paths
    assert "/api/runs/{run_id}/feedback" in paths
    assert "/api/feedback" in paths
    assert "/api/planning/feedback" in paths
    assert "/api/feedback/{feedback_id}/resolve" in paths
    assert "/api/runs/{run_id}/feedback-resolution-ledger" in paths
    assert "/api/runs/{run_id}/realtime-session" in paths
    assert "/api/runs/{run_id}/realtime-sessions" in paths
    assert "/api/runs/{run_id}/voice-setup-proof" in paths
    assert "/api/realtime-sessions/{realtime_session_id}/turns" in paths
    assert "/api/realtime-sessions/{realtime_session_id}/control" in paths
    assert "/api/realtime-sessions/{realtime_session_id}/status" in paths
    assert "/api/runs/{run_id}/events/stream" in paths
    assert "/api/orchestrations/content-studio" in paths
    assert "/api/runs/{run_id}/revision-loop" in paths
    assert "/api/runs/{run_id}/media-production" in paths
    assert "/api/runs/{run_id}/multimodal-intake" in paths
    assert "/api/runs/{run_id}/distribution-package" in paths
    assert "/api/runs/{run_id}/autonomous-pass" in paths
    assert "/api/runs/{run_id}/guardrail-audit" in paths
    assert "/api/runs/{run_id}/guardrail-audits" in paths
    assert "/api/runs/{run_id}/publish-readiness" in paths
    assert "/api/runs/{run_id}/sources" in paths
    assert "/api/runs/{run_id}/source-ledger" in paths
    assert "/api/runs/{run_id}/retrieval-quality-ledger" in paths
    assert "/api/runs/{run_id}/research-freshness-ledger" in paths
    assert "/api/runs/{run_id}/model-routing-ledger" in paths
    assert "/api/runs/{run_id}/provider-ops-ledger" in paths
    assert "/api/runs/{run_id}/realtime-dialogue-ledger" in paths
    assert "/api/runs/{run_id}/runtime-health-ledger" in paths
    assert "/api/runs/{run_id}/foundation-audit" in paths
    assert "/api/runs/{run_id}/claims" in paths
    assert "/api/runs/{run_id}/artifacts" in paths
    assert "/api/runs/{run_id}/interactive-note" in paths
    assert "/api/runs/{run_id}/obsidian-review-note" in paths
    assert "/api/memories" in paths
    assert "/api/memories/search" in paths


def test_foundation_graph_compiles():
    graph = build_foundation_graph()
    assert graph is not None


def test_foundation_reference_ledger_covers_required_sources():
    result = list_foundation_references()
    publishers = set(result.required_publishers)
    assert {
        "Google Developers Blog",
        "LangChain",
        "pgvector",
        "Hugging Face",
        "OpenAI",
        "ElevenLabs",
        "Cartesia",
        "Anthropic",
        "Martin Kleppmann",
        "O'Reilly",
        "Baseten",
        "AWS",
        "Google Cloud",
        "Uber Engineering",
        "Metaflow/Netflix",
        "LiveKit",
        "Pipecat",
    } <= publishers
    references = {reference.reference_id: reference for reference in result.references}
    assert references["google-agent-protocols-a2a"].url.startswith(
        "https://developers.googleblog.com/"
    )
    assert references["ddia-data-intensive-systems"].publisher == "Martin Kleppmann"
    assert references["baseten-inference-engineering"].publisher == "Baseten"
    assert references["google-adk-long-running-agents"].reference_type == (
        "long_running_agent_guide"
    )
    assert "agent-harness-engineer" in references[
        "langgraph-postgres-persistence"
    ].applies_to
    assert "context-engineering-agent" in references["pgvector-postgres-memory"].applies_to
    assert "audio-producer" in references["livekit-turns-interruptions"].applies_to
    assert "realtime-conversation-host" in references["pipecat-transports"].applies_to
    assert "audio-producer" in references["kokoro-82m-tts"].applies_to
    assert all(
        reference.last_verified in {"2026-05-16", "2026-05-17"}
        for reference in result.references
    )


def test_postgres_schema_uses_pgvector_and_not_sqlite():
    schema = (ROOT / "infra/postgres/001_foundation.sql").read_text()
    assert "create extension if not exists vector" in schema
    assert "agent_memories" in schema
    assert "agent_messages" in schema
    assert "guardrail_audits" in schema
    assert "run_checkpoints" in schema
    assert "realtime_sessions" in schema
    assert "retrieval_candidates" in schema
    assert "retrieval_rerank_decisions" in schema
    assert "knowledge_graph_nodes" in schema
    assert "knowledge_graph_edges" in schema
    assert "retrieval_evaluations" in schema
    assert "execution_mode text not null default 'worker_cycle'" in schema
    assert "heartbeat_lease_until timestamptz" in schema
    assert "idx_worker_profiles_heartbeat_lease" in schema
    assert "sqlite" not in schema.lower()


def test_postgres_agent_message_jsonb_mutations_cast_runtime_parameters():
    postgres = (ROOT / "src/all_about_llms/storage/postgres.py").read_text()
    assert "'recovered_by', %s::text" in postgres
    assert "'blocked_by', %s::text" in postgres
    assert "'authorized_by', %s::text" in postgres
    assert "'reset_attempt_count', %s::boolean" in postgres
    assert "'authorized_max_attempts', %s::integer" in postgres
    assert "'repaired_by', %s::text" in postgres
    assert "result = %s::jsonb" in postgres


def test_admin_cli_and_migrations_have_no_sqlite_fallback():
    cli = (ROOT / "src/all_about_llms/cli.py").read_text()
    agent_worker = (
        ROOT / "src/all_about_llms/orchestration/agent_worker.py"
    ).read_text()
    migrations = (ROOT / "src/all_about_llms/storage/migrations.py").read_text()
    checkpointer = (
        ROOT / "src/all_about_llms/orchestration/checkpointing.py"
    ).read_text()
    assert "setup-durable-storage" in cli
    assert "run-agent-cycle" in cli
    assert "run-worker-profile" in cli
    assert "run-worker-scheduler" in cli
    assert "--execution-mode" in cli
    assert "--max-iterations" in cli
    assert "_worker_scheduler_request_from_args" in cli
    assert '"requested_run_id": requested_run_id' in agent_worker
    assert '"idle_reason": "no_due_profiles"' in agent_worker
    assert "run-autonomous-pass" in cli
    assert "skip-runtime-health" in cli
    assert "ignore-runtime-health-block" in cli
    assert "skip-research-freshness" in cli
    assert "skip-research-source-refresh" in cli
    assert "ignore-research-freshness-block" in cli
    assert "skip-a2a-graph" in cli
    assert "ignore-a2a-graph-block" in cli
    assert "ignore-open-feedback-block" in cli
    assert "skip-multimodal-followups" in cli
    assert "multimodal-followup-rounds" in cli
    assert "build-runtime-health-ledger" in cli
    assert "skip-live-store-evidence" in cli
    assert "build-provider-smoke-ledger" in cli
    assert "skip-imagegen-boundary" in cli
    assert "realtime-provider" in cli
    assert "build-cockpit-walkthrough-ledger" in cli
    assert "skip-static-runtime-checks" in cli
    assert "build-distribution-package" in cli
    assert "resume-run" in cli
    assert "run-sync-pulse" in cli
    assert "skip-work-plan" in cli
    assert "skip-context-packet" in cli
    assert "context-packet-agent-id" in cli
    assert "skip-skill-usage-ledger" in cli
    assert "skip-model-routing-ledger" in cli
    assert "skip-provider-smoke-ledger" in cli
    assert "provider-smoke-live" in cli
    assert "skip-provider-ops-ledger" in cli
    assert "skip-realtime-dialogue-ledger" in cli
    assert "skip-feedback-resolution-ledger" in cli
    assert "skip-artifact-index" in cli
    assert "skip-foundation-audit" in cli
    assert "skip-run-replay-ledger" in cli
    assert "include-replay-event-payloads" in cli
    assert "AsyncPostgresSaver" in checkpointer
    assert "setup_postgres_checkpointer" in migrations
    assert "sqlite" not in cli.lower()


def test_planning_html_is_separate_interactive_artifact():
    html = (ROOT / "planning/foundation-system-design.html").read_text()
    assert "foundation-data" in html
    assert "Product app: live voice/text studio" in html
    assert "This is the separate planning workspace" in html
    assert "Kanban" not in html

    json_blob = html.split('<script id="foundation-data" type="application/json">', 1)[
        1
    ].split("</script>", 1)[0]
    data = json.loads(json_blob)
    assert len(data["agents"]) == 38
    assert len(data["skills"]) == 9
    assert len(data["providers"]) == 4
    assert len(data["providerReadiness"]) == 4
    assert len(data["modelRoutingLedger"]) == 5
    assert len(data["providerOpsLedger"]) == 4
    assert len(data["runtimeHealthLedger"]) == 5
    assert len(data["researchFreshnessLedger"]) == 4
    assert len(data["foundationAudit"]) == 6
    assert len(data["foundationReferences"]) == 18
    assert len(data["realtimeSurface"]) == 5
    assert len(data["realtimeDialogueLedger"]) == 7
    assert len(data["feedbackResolutionLedger"]) == 6
    assert len(data["multimodalIntake"]) == 6
    assert len(data["conversationRouting"]) == 6
    assert len(data["workflow"]) == 5
    assert len(data["revisionLoop"]) == 4
    assert len(data["artifactGrounding"]) == 4
    assert len(data["feedbackRouting"]) == 5
    assert len(data["workPlan"]) == 5
    assert len(data["syncPulse"]) == 5
    assert len(data["a2aCollaborationGraph"]) == 6
    assert len(data["skillUsageLedger"]) == 5
    assert len(data["feedbackGates"]) == 4
    assert len(data["guardrailAudit"]) == 5
    assert len(data["publishReadiness"]) == 4
    assert len(data["sourceLedgerSnapshot"]) == 5
    assert len(data["resumeHarness"]) == 6
    assert len(data["runReplayLedger"]) == 4
    assert len(data["contextEngineering"]) == 6
    assert len(data["mediaProduction"]) == 4
    assert len(data["distributionPackage"]) == 4
    assert len(data["interactiveNotes"]) == 5
    assert len(data["taskLifecycle"]) == 9
    assert len(data["workerLoop"]) == 7
    assert len(data["workerExecutors"]) == 28
    assert "publishing handoff" in html
    assert len(data["multiAgentCycle"]) == 4
    assert len(data["autonomousPass"]) == 16
    assert len(data["workerProfiles"]) == 7
    assert len(data["profileScheduler"]) == 4
    assert len(data["planningProgressColumns"]) == 4
    assert len(data["planningProgressItems"]) == 4
    assert len(data["planningProgressRoutes"]) == 4
    assert len(data["planningFeedbackRoutes"]) == 5
    assert data["decisions"][0]["title"] == "No SQLite"
    assert "Host Brief Follow-up" in html
    assert "realtime_turn_followup_v1" in html
    assert "agent_message_dependencies_repaired" in html
    assert "dependencies_repaired" in html
    assert "A2A Graph Preflight" in html
    assert "Open Feedback Gate" in html
    assert "Evidence Ledgers" in html
    assert "Foundation Self-Audit" in html
    assert "post-audit-coordination-loop" in html
    assert "Post-Audit Context Refresh" in html
    assert "Post-Audit Work Plan" in html
    assert "Post-Audit Manager Sync" in html
    assert "work_plan_refresh_reason" in html
    assert "sync_pulse_refresh_reason" in html
    assert "foundation_audit_completed" in html
    assert "Replay Debug Ledger" in html
    assert "Autonomous Context Packet" in html
    assert "latest_coordination" in html
    assert "post-audit work-plan and manager-sync coordination digests" in html
    assert "planning-progress-board" in html
    assert "planning-progress-export" in html
    assert "agent-studio-planning-progress-v1" in html
    assert "draggable = true" in html
    assert "dataTransfer.setData" in html
    assert "planning-feedback-form" in html
    assert "planning-feedback-run-id" in html
    assert "planning-feedback-route" in html
    assert "/api/planning/feedback" in html
    assert "planning-feedback-export" in html
    assert "agent-studio-planning-feedback-v1" in html
    assert "feedback_routing_support_v1" in html
    assert "durable_support_task_message_ids" in html
    assert "Planning Surface Review" in html
    assert "Foundation Reference Ledger" in html
    assert "Model Routing Ledger" in html
    assert "model_routing_ledger_built" in html
    assert "model_routing_ledger" in html
    assert "Source Contract Audit" in html
    assert "Provider Operations Ledger" in html
    assert "provider_operations_ledger_built" in html
    assert "Realtime Dialogue Ledger" in html
    assert "realtime_dialogue_ledger_built" in html
    assert "Feedback Resolution Ledger" in html
    assert "feedback_resolution_ledger_built" in html
    assert "targeted artifact/source/claim context" in html
    assert "explicit artifact/source/claim ids" in html
    assert "Provenance Completeness" in html
    assert "Runtime Health Ledger" in html
    assert "runtime_health_ledger_built" in html
    assert "provider_operations_ledger" in html
    assert "Research Freshness Ledger" in html
    assert "research_freshness_ledger_built" in html
    assert "research_freshness_ledger" in html
    assert "web_research_completed" in html
    assert "Web Research Agent worker provider searches" in html
    assert "source_evidence" in html
    assert "latest_web_research" in html
    assert "Retrieval Intelligence Agent" in html
    assert "Knowledge Graph Curator Agent" in html
    assert "agent-studio-retrieval-intelligence" in html
    assert "Foundation Audit" in html
    assert "foundation_audit_built" in html
    assert "foundation_audit" in html
    assert "Claude Code subagents" in html
    assert "Build Long-running AI agents" in html
    assert "foundation_reference" in html
    assert "Realtime Conversation Brief" in html
    assert "Conversation Handoff" in html
    assert "conversation_handoff" in html
    assert "Run Replay Ledger" in html
    assert "run_replay_ledger_built" in html
    assert "run_replay_ledger" in html
    assert "Multimodal Intake Ledger" in html
    assert "Dialogue-Attached Assets" in html
    assert "Specialist Review Artifact" in html
    assert "multimodal_intake_recorded" in html
    assert "multimodal_intake_review_recorded" in html
    assert "gemma_multimodal_review_completed" in html
    assert "Review Follow-up Handoffs" in html
    assert "Autonomous Continuation Proof" in html
    assert "imagegen_prompt_pack" in html
    assert "multimodal_review_followups_materialized" in html
    assert "autonomous_multimodal_followups_continued" in html
    assert "multimodal_intake_ledger" in html
    assert "multimodal_review" in html
    assert "Intent Route Plan" in html
    assert "Targeted Revision" in html
    assert "target_artifact_ids" in html
    assert "Artifact Grounding Contract" in html
    assert "artifact_grounding_contract_recorded" in html
    assert "Visual Brief" in html
    assert "Imagegen Prompt Pack" in html
    assert "Realtime Audio Brief" in html
    assert "Reel Storyboard" in html
    assert "targeted feedback context" in html
    assert "revise only the implicated draft lineage" in html


def test_product_cockpit_is_separate_from_planning_workspace():
    html = (ROOT / "frontend/cockpit/index.html").read_text()
    assert 'data-product-boundary="live-conversational-studio"' in html
    assert "foundation-data" not in html
    assert "This is the separate planning workspace" not in html
    assert "Kanban" not in html
    assert "/api/orchestrations/content-studio" in html
    assert "create-demo-run" in html
    assert "/api/demo/cockpit-run" in html
    assert "createDemoRun" in html
    assert "cockpit_demo_run_seeded" in html
    assert "/api/conversation/turns" in html
    assert "send-conversation" in html
    assert "conversation-log" in html
    assert "responds_to_turn_id" in html
    assert "provider-readiness" in html
    assert "/api/provider-readiness" in html
    assert "missing_env" in html
    assert "Provider-backed smoke" in html
    assert "smoke_test_plan" in html
    assert "demo_walkthrough" in html
    assert "expected_evidence" in html
    assert "realtime-session" in html
    assert "route-realtime-turn" in html
    assert "end-realtime" in html
    assert "auto-route-voice" in html
    assert "speak-replies" in html
    assert "realtime-dry-run" in html
    assert "dry_run" in html
    assert "provider_under_test" in html
    assert "interrupt-voice" in html
    assert "/control" in html
    assert "realtime_session_control_recorded" in html
    assert "speechSynthesis" in html
    assert "auto_voice_route" in html
    assert "interruptNextVoiceTurn" in html
    assert "/realtime-sessions/" in html
    assert "realtime_turn_routed" in html
    assert "create_realtime_brief_task" in html
    assert "realtime_conversation_brief_task_created" in html
    assert "realtime_session_status_updated" in html
    assert "revision-loop" in html
    assert "build-media-plan" in html
    assert "/media-production" in html
    assert "media_production_plan_built" in html
    assert "record-multimodal-intake" in html
    assert "attach-multimodal-assets" in html
    assert "dialogueMultimodalAssets" in html
    assert "/multimodal-intake" in html
    assert "multimodal_intake_recorded" in html
    assert "build-distribution-package" in html
    assert "/distribution-package" in html
    assert "distribution_package_built" in html
    assert "distribution_package_reused" in html
    assert "run-autonomous-pass" in html
    assert "/autonomous-pass" in html
    assert "run_runtime_health_check" in html
    assert "block_on_runtime_health_blocked" in html

    assert "runtime_health_status" in html
    assert "build_a2a_collaboration_graph" in html
    assert "block_on_a2a_graph_blocked" in html
    assert "a2a_graph_blocked" in html
    assert "block_on_open_feedback" in html
    assert "open_feedback_blocked" in html
    assert "build_research_freshness_ledger" in html
    assert "auto_refresh_research_sources" in html
    assert "block_on_research_freshness_blocked" in html
    assert "research_freshness_status" in html
    assert "research_freshness_artifact_id" in html
    assert "research_refresh_processed" in html
    assert "build_context_packet" in html
    assert "context_packet_artifact_id" in html
    assert "research_refresh_idle" in html
    assert "autonomous_studio_pass_completed" in html
    assert "build_skill_usage_ledger" in html
    assert "build_model_routing_ledger" in html
    assert "build_provider_ops_ledger" in html
    assert "build_foundation_audit" in html
    assert "foundation_audit_status" in html
    assert "build_run_replay_ledger" in html
    assert "skill_usage_artifact_id" in html
    assert "model_routing_artifact_id" in html
    assert "model_routing_boundary_violation_count" in html
    assert "provider_ops_artifact_id" in html
    assert "run_replay_artifact_id" in html
    assert "evidence-row" in html
    assert "evidence-chip" in html
    assert "postAuditEvidenceFromPayload" in html
    assert "work plan refresh" in html
    assert "sync pulse refresh" in html
    assert "context refresh" in html
    assert "context_packet_latest_foundation_audit_artifact_id" in html
    assert "context_packet_foundation_audit_remediation_count" in html
    assert "work_plan_foundation_audit_remediation_count" in html
    assert "resolve_foundation_audit_finding" in html
    assert "foundation-remediation" in html
    assert "foundation_audit_remediation" in html
    assert "approve-feedback" in html
    assert "feedback_resolved" in html
    assert "/api/feedback/" in html
    assert "feedback_routed" in html
    assert "memory_recorded" in html
    assert "events/stream" in html
    assert "agent-messages" in html
    assert "/api/a2a/messages/${message.message_id}/retry" in html
    assert "Authorize retry" in html
    assert "/api/a2a/messages/${message.message_id}/dependencies/repair" in html
    assert "Repair deps" in html
    assert "agent_message_retry_authorized" in html
    assert "agent_message_retry_exhausted" in html
    assert "agent_message_dependencies_repaired" in html
    assert "agent_message_recovered" in html
    assert "worker-agent" in html
    assert "run-worker-cycle" in html
    assert "save-worker-profile" in html
    assert "launch-worker-autopilot" in html
    assert "/api/runs/${runId}/autopilot-launch" in html
    assert "autopilot_launch_recorded" in html
    assert "refreshWorkerProfiles" in html
    assert "Autopilot ran its first autonomous heartbeat" in html
    assert "worker-profile-mode" in html
    assert "autonomous_pass" in html
    assert "execution_mode" in html
    assert "autonomous_pass_result" in html
    assert "skipped_reason" in html
    assert "worker_profile_heartbeat_blocked" in html
    assert "heartbeat-worker-profile" in html
    assert "worker-profile-ledger" in html
    assert "heartbeat_ledger_artifact" in html
    assert "worker_profile_heartbeat_ledger" in html
    assert "run-worker-scheduler" in html
    assert "/api/a2a/workers/run-cycle" in html
    assert "/worker-profiles" in html
    assert "check-readiness" in html
    assert "/publish-readiness" in html
    assert "build_artifact_index" in html
    assert "artifact_index_processed_tasks" in html
    assert "artifact_index_publishing_handoff_status" in html
    assert "build-source-ledger" in html
    assert "/source-ledger" in html
    assert "source_ledger_snapshot_built" in html
    assert "claim_source_matrix_count" in html
    assert "claim_source_verdict_counts" in html
    assert "claim_source_matrix" in html
    assert "source-evidence-drilldown" in html
    assert "renderSourceEvidenceDrilldown" in html
    assert "accepted retrieval evidence" in html
    assert "claim coverage" in html
    assert "accepted_for_context" in html
    assert "accepted_retrieval_source_count" in html
    assert "build-research-freshness" in html
    assert "/research-freshness-ledger" in html
    assert "research_freshness_ledger_built" in html
    assert "build-provider-ops-ledger" in html
    assert "build-model-routing-ledger" in html
    assert "build-realtime-dialogue-ledger" in html
    assert "realtime_spoken_response_planned" in html
    assert "spoken_response_plan_count" in html
    assert "spoken_response" in html
    assert "build-feedback-resolution-ledger" in html
    assert "target_artifact_selection" in html
    assert "target_artifact_ids" in html
    assert "target_source_ids" in html
    assert "target_claim_ids" in html
    assert "feedback_entries" in html
    assert "targeted_feedback_count" in html
    assert "feedback_outcomes" in html
    assert "accepted_feedback_count" in html
    assert "revised_feedback_count" in html
    assert "held_feedback_count" in html
    assert "failed_linked_task_count" in html
    assert "failed_task_ids" in html
    assert "/model-routing-ledger" in html
    assert "model_routing_ledger_built" in html
    assert "/provider-ops-ledger" in html
    assert "provider_operations_ledger_built" in html
    assert "/realtime-dialogue-ledger" in html
    assert "/feedback-resolution-ledger" in html
    assert "build-runtime-health-ledger" in html
    assert "/runtime-health-ledger" in html
    assert "runtime_health_ledger_built" in html
    assert "runtime_health_live_postgres_connected" in html
    assert "build-cockpit-walkthrough" in html
    assert "/cockpit-walkthrough-ledger" in html
    assert "cockpit_walkthrough_ledger_built" in html
    assert "build-foundation-audit" in html
    assert "/foundation-audit" in html
    assert "foundation_audit_built" in html
    assert "source_grounding_repaired" in html
    assert "a2a_protocol_audit_recorded" in html
    assert "data_analysis_artifact_created" in html
    assert "content_writer_artifacts_created" in html
    assert "script_doctor_artifacts_created" in html
    assert "source_quality" in html
    assert "retrieval-quality-ledger" in html
    assert "retrieval_quality_ledger_built" in html
    assert "weak_source_ids" in html
    assert "build-resume-plan" in html
    assert "/resume-plan" in html
    assert "resume-run" in html
    assert "/resume" in html
    assert "build-replay-ledger" in html
    assert "/replay-ledger" in html
    assert "run_checkpoint_recorded" in html
    assert "resume_plan_built" in html
    assert "latest_web_research" in html
    assert "source_evidence snippets/dates" in html
    assert "run_resume_started" in html
    assert "run_resume_blocked" in html
    assert "run_resume_completed" in html
    assert "dependency_cycle_agent_tasks" in html
    assert "run_replay_ledger_built" in html
    assert "build-work-plan" in html
    assert "/work-plan" in html
    assert "run_work_plan_built" in html
    assert "in_dependency_cycle" in html
    assert "dependency_cycles" in html
    assert "build-sync-pulse" in html
    assert "/sync-pulse" in html
    assert "multi_agent_sync_pulse_recorded" in html
    assert "dependency_cycle" in html
    assert "build-a2a-graph" in html
    assert "/a2a-collaboration-graph" in html
    assert "a2a_collaboration_graph_built" in html
    assert "dependency_cycle_message_ids" in html
    assert "dependency_cycles" in html
    assert "build-skill-usage-ledger" in html
    assert "/skill-usage-ledger" in html
    assert "skill_source_contract_issue_count" in html
    assert "agent_skill_invocation_recorded" in html
    assert "agent_skill_usage_ledger_built" in html
    assert "agent_message_status_updated" in html
    assert "agent_tool_use_approved" in html
    assert "agent_tool_use_denied" in html
    assert "agent_model_use_approved" in html
    assert "agent_model_use_denied" in html
    assert "editorial_review_completed" in html
    assert "conversation_turn_routed" in html
    assert "conversation_handoff_recorded" in html
    assert "agent_worker_cycle_completed" in html
    assert "observability_report_recorded" in html
    assert "worker_profile_heartbeat" in html
    assert "worker_profile_heartbeat_ledger_recorded" in html
    assert "worker_scheduler_pass_completed" in html
    assert "publish_readiness_checked" in html
    assert "publishing-handoff" in html
    assert "renderPublishingHandoff" in html
    assert "publishing_handoff_status" in html
    assert "context_packet_latest_publishing_handoff_status" in html
    assert "latest_publish_readiness_status" in html
    assert "publish_channel_checks" in html
    assert "context-packet" in html
    assert "context_manifest" in html
    assert "context_risks" in html
    assert "recommended_fetches" in html
    assert "memory-policy" in html
    assert "build-memory-policy" in html
    assert "/project-memory/retrieval" in html
    assert "memory-policy-relevant-tags" in html
    assert "memory-policy-relevant-wiki-notes" in html
    assert "memory-policy-relevant-memory-ids" in html
    assert "relevant_memory_ids" in html
    assert "relevant_tags" in html
    assert "relevant_target_wiki_notes" in html
    assert "parseListInput" in html
    assert "record-project-memory" in html
    assert "project-memory-kind" in html
    assert "project-memory-scope" in html
    assert "project-memory-confidence" in html
    assert "project-memory-content" in html
    assert "project-memory-target-wiki-notes" in html
    assert "project-memory-source-artifact-ids" in html
    assert "project-memory-records" in html
    assert "recordProjectMemoryFromCockpit" in html
    assert "renderProjectMemoryRecord" in html
    assert "/project-memory" in html
    assert "project_memory_recorded" in html
    assert "cockpit_user_confirmed_memory" in html
    assert "user_preference" in html
    assert "project_decision" in html
    assert "projectMemoryPolicyStatus" in html
    assert "project_memory_policy_confirmation" in html
    assert "project_memory_policy_status" in html
    assert "context_packet_artifact_created" in html
    assert "latest_coordination" in html
    assert "guardrail-audit" in html
    assert "guardrail-audits" in html
    assert "interactive-note" in html
    assert "generate-note" in html
    assert "interactive_note_generated" in html

    client = TestClient(app)
    response = client.get("/cockpit")
    assert response.status_code == 200
    assert "All About LLMs Studio Cockpit" in response.text


def test_next_voice_panel_uses_gemma_kokoro_transport_contract():
    panel = (
        ROOT / "frontend/next-app/components/voice/RealtimeVoicePanel.tsx"
    ).read_text()
    livekit_runtime = (
        ROOT / "frontend/next-app/lib/voice/livekitRuntime.ts"
    ).read_text()
    package_json = json.loads(
        (ROOT / "frontend/next-app/package.json").read_text()
    )
    config = (ROOT / "src/all_about_llms/config.py").read_text()
    provider = (ROOT / "src/all_about_llms/providers/realtime.py").read_text()
    readiness = (ROOT / "src/all_about_llms/voice_agent/readiness.py").read_text()
    docker_compose = (ROOT / "docker-compose.yml").read_text()
    env_example = (ROOT / ".env.example").read_text()
    readme = (ROOT / "README.md").read_text()
    rehearsal = (
        ROOT / "frontend/next-app/lib/voice/rehearsal.ts"
    ).read_text()
    followup = (
        ROOT / "frontend/next-app/lib/voice/followup.ts"
    ).read_text()
    autopilot_profile = (
        ROOT / "frontend/next-app/lib/state/autopilotProfile.ts"
    ).read_text()

    assert "OpenRouter DeepSeek + Kokoro" in panel
    assert 'type VoiceProvider = "openrouter_livekit" | "local_rehearsal"' in panel
    assert 'id: "openrouter_livekit"' in panel
    assert 'useState<VoiceProvider>("openrouter_livekit")' in panel
    assert 'provider: "openrouter_livekit"' in panel
    assert "joinLiveKitRuntime" in panel
    assert "Join voice room" in panel
    assert "livekit-client" in package_json["dependencies"]
    assert "new Room" in livekit_runtime
    assert "setMicrophoneEnabled" in livekit_runtime
    assert "setMicrophonePublishing" in livekit_runtime
    assert "RoomEvent.TrackSubscribed" in livekit_runtime
    assert "RoomEvent.DataReceived" in livekit_runtime
    assert "agent.voice.event" in livekit_runtime
    assert "normalizeAgentVoiceEvent" in livekit_runtime
    assert "recordRealtimeVoiceEvent" in panel
    assert "followup_task_message_id" in panel
    assert "onVoiceFollowupReady" in panel
    assert "voiceFollowupContinuationForEvent" in panel
    assert "Voice follow-up queued" in followup
    assert "Voice follow-up continuation failed" in followup
    assert "Provider recovery queued" in followup
    assert "provider_failure_recovery" in followup
    assert "Voice timing persistence failed" in panel
    assert "onAgentEvent" in panel
    assert "activeRealtimeSessionIdRef" in panel
    assert "activeRealtimeSessionIdRef.current !== session.realtime_session_id" in panel
    assert "handleRuntimeEvent(runtimeEvent)" in panel
    assert "next_livekit_data_channel" in panel
    assert "buildVoiceProviderSmoke" in panel
    assert "buildLiveVoiceProofPath" in panel
    assert "handleLiveVoiceProofPathAction" in panel
    assert "liveVoiceProofActionSequenceRef" in panel
    assert "shouldContinue: () => isCurrentProofAction" in panel
    assert "liveVoiceProofPath.primaryActionLabel" in panel
    assert "buildRealtimeVoiceTimingLedger" in panel
    assert "Voice proof" in panel
    assert "Live voice proof path" in panel
    assert "Runtime smoke" in panel
    assert "Timing ledger" in panel
    assert "Captured audio proof" in panel
    assert "Realtime voice timing proof" in panel
    assert "Latest voice turn timing" in panel
    assert "voice-audio-proof" in panel
    assert "voice-timing-proof" in panel
    assert "buildVoiceAudioFixtureProof" in panel
    assert "buildVoiceStreamingProviderProof" in panel
    assert "findGemmaKokoroStreamingSmokeStep" in panel
    assert 'data-smoke-proof-id="openrouter-kokoro-transport"' in panel
    assert 'data-smoke-proof-id="openrouter-kokoro-captured-audio"' in panel
    assert 'data-smoke-proof-id="gemma-kokoro-captured-audio"' not in panel
    assert "Rust VAD cancels OpenRouter/Kokoro output" in panel
    assert "Gemma inference" not in panel
    assert "Gemma audio input" not in panel
    assert "Gemma 4 E4B handles audio understanding" not in panel
    assert "buildVoiceTimingStageProofs" in panel
    assert "buildVoiceTimingTurnProof" in panel
    assert "voice-stage-strip" in panel
    assert "Realtime state" in panel
    assert "voice-transcript-grid" in panel
    assert "Live voice captions" in panel
    assert "liveVoiceTranscriptFromAgentEvent" in panel
    assert "setLiveTranscript(EMPTY_LIVE_VOICE_TRANSCRIPT)" in panel
    live_transcript = (
        ROOT / "frontend/next-app/lib/voice/liveTranscript.ts"
    ).read_text()
    assert "voice_user_turn_committed" in live_transcript
    assert "assistant_text_delta" in live_transcript
    assert "text_delta" in live_transcript
    assert "assistant_response_completed" in live_transcript
    assert "MAX_ASSISTANT_CAPTION_CHARS" in live_transcript
    assert "Cancellation acknowledgement" in panel
    assert "cancellationProofFromVoiceAgentEvent" in panel
    assert "failedCancellationProofFromControlError" in panel
    assert "setCancellationProof(IDLE_CANCELLATION_PROOF)" in panel
    assert "stageFromVoiceAgentEvent" in panel
    assert "stageFromRuntimeEvent" in panel
    assert "Microphone publishing enabled" in livekit_runtime
    assert "Microphone publishing disabled" in livekit_runtime
    assert "handleToggleMicrophone" in panel
    assert "microphoneControlSequenceRef" in panel
    microphone_helper = (
        ROOT / "frontend/next-app/lib/voice/microphone.ts"
    ).read_text()
    assert "isMicrophoneControlCurrent" in panel
    assert "controlToken === activeControlToken" in microphone_helper
    assert "microphoneControlLabel" in panel
    assert "microphoneStatusLabel" in panel
    assert "Mute mic" in microphone_helper
    assert "Unmute mic" in microphone_helper
    assert "MicOff" in panel
    assert "!isReady || isRehearsalSession || microphoneControlLoading" in panel
    assert "onMicrophonePublishingChanged" in livekit_runtime
    assert "RoomEvent.LocalTrackPublished" in livekit_runtime
    assert "RoomEvent.LocalTrackUnpublished" in livekit_runtime
    assert "RoomEvent.TrackMuted" in livekit_runtime
    assert "RoomEvent.TrackUnmuted" in livekit_runtime
    assert "sendTranscriptTurn" in livekit_runtime
    assert "buildLiveTextTurnPayload" in livekit_runtime
    assert "Send text to live voice agent" in panel
    assert "handleSendLiveTextTurn" in panel
    assert "isLiveTextTurnCurrent" in panel
    live_text_turn = (
        ROOT / "frontend/next-app/lib/voice/liveTextTurn.ts"
    ).read_text()
    assert "LIVEKIT_AGENT_CONTROL_TOPIC" in live_text_turn
    assert "transcript_turn" in live_text_turn
    assert "next_livekit_text_turn" in live_text_turn
    assert "newLiveTextTurnId" in live_text_turn
    assert "voice-readiness-missing" in panel
    assert "readinessMissingEnv" in panel
    assert "readinessNextAction" in panel
    assert "Start transcript rehearsal" in panel
    assert "Route rehearsal turn" in panel
    assert "Transcript rehearsal ready" in panel
    assert "Not production audio" in panel
    assert "buildTranscriptRehearsalTurnInput" in panel
    assert "provider_backed_realtime: false" in rehearsal
    assert "rehearsal_only: true" in rehearsal
    assert "transport.token" in livekit_runtime
    assert "token_persisted" in livekit_runtime
    assert "clearRemoteAudio" in livekit_runtime
    assert "interruptAgent" in livekit_runtime
    assert "voice_interrupt" in livekit_runtime
    assert "Agent interrupt control sent" in livekit_runtime
    assert "control_binding_token" in livekit_runtime
    livekit_app = (ROOT / "src/all_about_llms/voice_agent/livekit_app.py").read_text()
    assert "_livekit_data_message_topic" in livekit_app
    assert 'topic != "agent.voice.control"' in livekit_app
    assert "raw_run_id is None or raw_session_id is None" in livekit_app
    assert "participant_identity != state.participant_identity" in livekit_app
    assert "verify_livekit_control_binding_token" in livekit_app
    assert 'action: "stop_output"' in panel
    assert "createFollowupTask: false" in panel
    assert "buildRealtimeAgentControlMetadata" in panel
    assert "isCurrentStop" in panel
    assert "startSequenceRef.current === stopSequence" in panel
    assert "presenceMonitorSequenceRef" in panel
    assert "VOICE_AGENT_PRESENCE_MONITOR_INTERVAL_MS" in panel
    assert "shouldProbeVoiceAgentPresence" in panel
    assert "Voice-agent liveness refreshed" in panel
    assert "Voice-agent liveness missing" in panel
    assert "voice_manual_interrupt_received" in (
        ROOT / "frontend/next-app/lib/voice/cancellation.ts"
    ).read_text()
    control_metadata = (
        ROOT / "frontend/next-app/lib/voice/controlMetadata.ts"
    ).read_text()
    assert "GEMMA_KOKORO_STOP_RUNTIME_ACTIONS" in control_metadata
    assert "livekit_agent_control_sent" in control_metadata
    assert "livekit_agent_control_id" in control_metadata
    assert "livekit_agent_control_error" in control_metadata
    assert "drop_outbound_audio_packets" in control_metadata
    assert "deepseek/deepseek-v4-flash" in config
    assert "hexgrad/Kokoro-82M" in config
    assert 'gemma4_realtime_transport_framework: str = "livekit"' in config
    assert "raw_websocket_production_allowed" in provider
    assert "prune_after_turns" in provider
    assert "cancel_gemma_inference" in provider
    assert "clear_kokoro_tts_buffer" in provider
    assert "silero-vad-rust" in config
    assert "livekit_agent_name" in config
    assert "livekit-agent-participant" in readiness
    assert "startup_preflight_performed" in readiness
    assert "build_livekit_voice_agent_server" in readiness
    assert "all-about-llms-admin run-voice-agent" in readiness
    assert "livekit-server --dev" in readiness
    assert "docker compose --profile voice up -d livekit" in readiness
    assert "docker compose --profile voice up livekit" in readiness
    assert "configured_for_local_dev" in readiness
    assert "_preflight_livekit_room_service" in readiness
    assert "RoomService/ListRooms" in readiness
    assert "connectivity_preflight_performed" in readiness
    assert "LIVEKIT_LOCAL_DEV_DOCS" in readiness
    assert "profiles:" in docker_compose
    assert "voice" in docker_compose
    assert "livekit/livekit-server:latest" in docker_compose
    assert '"--dev", "--bind", "0.0.0.0"' in docker_compose
    assert "docker compose --profile voice up livekit" in env_example
    assert "LIVEKIT_API_KEY=<local-livekit-api-key>" in readme
    assert "LIVEKIT_API_SECRET=<local-livekit-api-secret>" in readme
    assert "LIVEKIT_API_KEY=devkey" not in readme
    assert "LIVEKIT_API_SECRET=secret" not in readme
    assert "OPENROUTER_LIVEKIT_URL" in provider
    assert "is not configured for LiveKit production transport" in provider
    assert "GEMMA4_REALTIME_LIVEKIT_URL or GEMMA4_REALTIME_WS_URL is not configured" not in provider
    local_provider_template = (
        ROOT / ".secrets/local_provider_config.json.template"
    ).read_text()
    assert "OPENROUTER_LIVEKIT_URL" in local_provider_template
    assert "local MLX stack" not in local_provider_template
    client = (ROOT / "frontend/next-app/lib/api/client.ts").read_text()
    assert "/api/runs/${input.runId}/provider-smoke" in client
    assert "/api/runs/${input.runId}/realtime-voice-timing-ledger" in client
    assert "/api/runs/${input.runId}/voice-setup-proof" in client
    assert "recordVoiceSetupProof" in client
    assert "/api/realtime-sessions/${input.realtimeSessionId}/turns" in client
    assert "preflight_livekit" in client
    assert "preflightLivekit" in panel
    assert "getLocalLiveKitProcessStatus" in panel
    assert "startLocalLiveKitProcess" in panel
    assert "stopLocalLiveKitProcess" in panel
    assert "Start LiveKit" in panel
    assert "Local LiveKit transport" in panel
    assert "shouldAutoStartLocalLiveKitProcess" in panel
    assert "/api/local-livekit-process/start" in client
    assert "preflight_agent" in client
    assert "preflightAgent" in panel
    assert "execute_live_calls: input.executeLiveCalls ?? false" in client
    assert 'realtime_provider: "openrouter_livekit"' in client
    assert "include_gemma: false" in client
    assert "include_realtime: true" in client
    assert "include_web_search: false" in client
    assert "include_reranker: false" in client
    assert "include_imagegen_boundary: false" in client
    page = (ROOT / "frontend/next-app/app/page.tsx").read_text()
    activity_panel = (
        ROOT / "frontend/next-app/components/run/ActivityPanel.tsx"
    ).read_text()
    production_panel = (
        ROOT / "frontend/next-app/components/production/ProductionPanel.tsx"
    ).read_text()
    draft_board = (
        ROOT / "frontend/next-app/components/drafts/DraftBoard.tsx"
    ).read_text()
    run_event_stream = (
        ROOT / "frontend/next-app/lib/state/runEventStream.ts"
    ).read_text()
    run_event_refresh = (
        ROOT / "frontend/next-app/lib/state/runEventRefresh.ts"
    ).read_text()
    shell = (ROOT / "frontend/next-app/components/layout/AppShell.tsx").read_text()
    assert "runAgentWorkerCycle" in client
    assert "/api/a2a/workers/run-cycle" in client
    assert "getProviderReadiness" in client
    assert "/api/provider-readiness" in client
    assert "launchAutopilot" in client
    assert "/api/runs/${input.runId}/autopilot-launch" in client
    assert "listWorkerProfiles" in client
    assert "/api/runs/${runId}/worker-profiles" in client
    assert "stopWorkerProfile" in client
    assert "/api/worker-profiles/${profileId}/stop" in client
    assert "heartbeatWorkerProfile" in client
    assert "/api/worker-profiles/${profileId}/heartbeat" in client
    assert "runWorkerScheduler" in client
    assert "/api/worker-profiles/scheduler/run" in client
    assert "run_id: input.runId ?? null" in client
    assert "execution_mode: input.executionMode ?? null" in client
    assert "getWorkerSchedulerProcessStatus" in client
    assert "/api/worker-scheduler-process" in client
    assert "startWorkerSchedulerProcess" in client
    assert "/api/worker-scheduler-process/start" in client
    assert "stopWorkerSchedulerProcess" in client
    assert "/api/worker-scheduler-process/stop" in client
    assert "Continuing specialist agents" in page
    assert "Continuing live voice agents" in page
    assert "Starting always-on studio" in page
    assert "Stopping always-on studio" in page
    assert "Starting background runner" in page
    assert "Stopping background runner" in page
    assert "workerProfiles" in page
    assert "workerSchedulerProcess" in page
    assert "artifacts={artifacts as ArtifactRecord[]}" in page
    assert "sourceEvidence={state.context?.source_evidence ?? []}" in page
    assert "handleLaunchAutopilot" in page
    assert "handleRunAutopilotScheduler" in page
    assert "handleHeartbeatAutopilot" in page
    assert "handleStopAutopilot" in page
    assert "Checking due always-on work" in page
    assert 'executionMode: "autonomous_pass"' in page
    assert "autopilotSchedulerInFlightRunsRef" in page
    assert "autopilotSchedulerInFlightRunsRef.current.has(runId)" in page
    assert "autopilotSchedulerInFlightRunsRef.current.delete(runId)" in page
    assert "Always-on studio check is already running." in page
    assert "No active always-on studio run is available for the background check." in page
    assert "Running specialist pulse" in page
    assert "autopilotHeartbeatInFlightRef" in page
    assert "Specialist pulse is already running." in page
    assert "The selected always-on studio run is no longer active." in page
    assert "runId: undefined" in page
    assert "context: undefined" in page
    assert "buildAutopilotScheduleStatus" in activity_panel
    assert "autopilotSchedule" in activity_panel
    assert "heartbeat_lease_until" in (
        ROOT / "frontend/next-app/lib/state/autopilotSchedule.ts"
    ).read_text()
    assert "buildAutopilotAutoWakeDecision" in page
    assert "consumeRunEventStream" in page
    assert "mergeRecentRunEvents" in page
    assert "latestRunEventIdRef" in page
    assert "shouldRefreshRunForStreamEvent" in page
    assert "STREAMED_RUN_REFRESH_DEBOUNCE_MS" in page
    assert "{ silent: true }" in page
    assert "Auto continue" in page
    assert "Auto continue" in activity_panel
    assert "Live updates" in activity_panel
    assert "run-event-stream-status" in activity_panel
    assert "parseSseFrames" in run_event_stream
    assert "buildRunEventStreamUrl" in run_event_stream
    assert "/events/stream" in run_event_stream
    assert "EventSource" not in run_event_stream
    assert '"_completed"' in run_event_refresh
    assert "agent_message_dependency_waiting" in run_event_refresh
    assert "agent_message_recovered" in run_event_refresh
    assert "agent_message_retry_exhausted" in run_event_refresh
    assert "assistant_text_delta" in run_event_refresh
    assert "expectedVersion?: number" in page
    assert "composeVersion" in page
    assert "clearBusyForRun" in page
    assert "clearBusyForOwnedRun" in page
    assert "isRunOwnerCurrent" in page
    assert "isRunVersionCurrent" in page
    assert "isActiveRunOwner" in page
    assert "continueAgents(result.run_id, result.summary, composeVersion)" in page
    assert 'refreshRun(runId, "Run state refreshed.", runVersion)' in page
    assert "isRunVersionCurrent(runVersion, runVersionRef.current)" in page
    assert "activeRunIdRef" in page
    assert "activeRunIdRef.current = undefined" in page
    assert "activeRunIdRef.current !== realtimeSession.run_id" in page
    assert "target_artifact_ids: selectedArtifacts.map((artifact) => artifact.artifact_id)" in page
    assert page.count("artifactIds: selectedArtifacts.map((artifact) => artifact.artifact_id)") >= 4
    assert "selectedCount={selectedArtifacts.length}" in page
    assert "buildContentReadinessSnapshot" in page
    assert "contentReadiness={contentReadiness}" in page
    assert "selectedArtifactIds={selectedArtifacts.map((artifact) => artifact.artifact_id)}" in page
    assert "!artifact || !isContentArtifact(artifact)" in page
    assert "isPublishableArtifact" in draft_board
    assert "contentReadiness?.status === \"blocked\"" in production_panel
    assert "contentReadiness?.status === \"no_content\"" in production_panel
    assert "Content readiness" in production_panel
    assert 'key={state.runId ?? "new-voice-session"}' in page
    assert "handleVoiceFollowupReady" in page
    assert "LiveKit cleanup failed" in panel
    assert "currentRunIdRef" in panel
    assert "startSequenceRef" in panel
    assert "voiceSmokeSequenceRef" in panel
    assert "voiceTimingSequenceRef" in panel
    assert "voiceSetupActionSequenceRef" in panel
    assert "isCurrentSetupAction" in panel
    assert "persistVoiceSetupProof" in panel
    assert "Voice setup proof recorded" in panel
    assert "voiceSetupProofStepPayload" in panel
    assert "voiceSetupReadinessProofStatus(readinessResult.status)" in panel
    assert "const smokeOutcome = await handleVoiceSmoke({ live: true });" in panel
    assert "const smokeProviderReleaseGate = buildVoiceProviderReleaseGate" in panel
    assert "providerReleaseGate: smokeProviderReleaseGate" in panel
    assert "steps: smokeSteps" in panel
    assert "blocker: smokeBlocker" in panel
    assert "voiceSetupProofStatus(smokeBlocker)" in panel
    assert "isRunBoundRequestCurrent" in panel
    assert "currentRunIdRef.current === startRunId" in panel
    assert "currentRunIdRef.current" in panel
    assert "Discarded stale OpenRouter/Kokoro voice session after the active run changed." in panel
    assert "agentCycleInFlightRef" in page
    assert "runVersionRef" in page
    assert "useGemmaAgentCycle" in page
    assert "continueAgents" in page
    assert "Continue specialists" in activity_panel
    assert "Gemma experts" in activity_panel
    assert "Always-on studio" in activity_panel
    assert "buildAutopilotEvidence" in activity_panel
    assert "Specialist pulse" in activity_panel
    assert "Background check" in activity_panel
    assert "workerProfiles" in activity_panel
    assert "artifacts" in activity_panel
    assert "onLaunchAutopilot" in activity_panel
    assert "onRunAutopilotScheduler" in activity_panel
    assert "Check due work" in activity_panel
    assert "Technical proof" in activity_panel
    assert "Background check" in activity_panel
    assert "requested_run_id" in activity_panel
    assert "idle_reason" in activity_panel
    assert "onHeartbeatAutopilot" in activity_panel
    assert "Run pulse" in activity_panel
    assert "onStopAutopilot" in activity_panel
    assert "latestActiveAutopilotProfile" in activity_panel
    assert "latestAutopilotProfile" in activity_panel
    assert "ACTIVE_AUTOPILOT_STATUSES" in autopilot_profile
    assert '"running"' in autopilot_profile
    assert '"started"' in autopilot_profile
    assert "onContinueAgents" in activity_panel
    assert "onUseGemmaChange" in activity_panel
    assert "disabled={Boolean(busyLabel)}" in shell
    assert "window.confirm" in panel
    assert "Run live OpenRouter/Kokoro provider smoke" in panel
    assert "Provider-backed voice release gate" in panel
    assert "buildVoiceProviderReleaseGate" in panel
    assert "Provider readiness" in panel
    assert "new WebSocket" not in panel
    assert "new WebSocket" not in livekit_runtime


def test_next_run_ownership_race_policy_executes():
    result = subprocess.run(
        ["npm", "run", "test:race"],
        cwd=ROOT / "frontend/next-app",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_product_app_is_creator_surface_not_cockpit():
    app_html = (ROOT / "frontend/app/index.html").read_text()
    cockpit_html = (ROOT / "frontend/cockpit/index.html").read_text()
    assert app_html != cockpit_html
    assert "All About LLMs Content Generator" in app_html
    assert "Topic and brief" in app_html
    assert "Voice or text input" in app_html
    assert "Ready-to-edit Post, Reel, and Substack copy" in app_html
    assert "Sources" in app_html
    assert "Feedback" in app_html
    assert "/api/orchestrations/content-studio" in app_html
    assert "/api/conversation/turns" in app_html
    assert "/revision-loop" in app_html
    assert "/sources" in app_html
    assert "/feedback" in app_html
    assert 'data-product-boundary="live-conversational-studio"' not in app_html
    assert "All About LLMs Studio Cockpit" in cockpit_html

    client = TestClient(app)
    response = client.get("/app")
    assert response.status_code == 200
    assert "All About LLMs Content Generator" in response.text
    assert "All About LLMs Studio Cockpit" not in response.text


def test_product_app_excludes_cockpit_only_controls():
    html = (ROOT / "frontend/app/index.html").read_text()
    cockpit_only_tokens = {
        "create-demo-run",
        "provider-readiness",
        "Provider-backed smoke",
        "smoke_test_plan",
        "worker-profile",
        "worker-profile-ledger",
        "run-worker-cycle",
        "save-worker-profile",
        "launch-worker-autopilot",
        "run-worker-scheduler",
        "events/stream",
        "agent-messages",
        "Authorize retry",
        "Repair deps",
        "build-source-ledger",
        "source-evidence-drilldown",
        "build-model-routing-ledger",
        "build-provider-ops-ledger",
        "build-realtime-dialogue-ledger",
        "run_runtime_health_check",
        "runtime_health_status",
        "build_a2a_collaboration_graph",
        "a2a_graph_blocked",
        "scheduler",
        "runtime health",
        "run ID",
    }
    for token in cockpit_only_tokens:
        assert token not in html


def test_obsidian_vault_contains_interactive_design_and_tracking_artifacts():
    vault = ROOT / "social_media_optimiser"
    assert (vault / ".obsidian").is_dir()
    home = (vault / "agent-studio-vault-home.html").read_text()
    design = (vault / "00-system-design/agent-studio-hld-lld.html").read_text()
    a2a_map = (vault / "00-system-design/agent-studio-a2a-map.html").read_text()
    skill_matrix = (
        vault / "00-system-design/agent-studio-skill-matrix.html"
    ).read_text()
    proof_readiness = (
        vault / "01-work-tracking/agent-studio-proof-readiness.html"
    ).read_text()
    feedback_loop_map = (
        vault / "03-review-packets/agent-studio-feedback-loop-map.html"
    ).read_text()
    publication_boundary = (
        vault / "03-review-packets/agent-studio-publication-boundary-map.html"
    ).read_text()
    gemma_voice_boundary = (
        vault / "02-research/gemma-voice-boundary-map.html"
    ).read_text()
    tracker = (vault / "01-work-tracking/agent-studio-work-tracker.html").read_text()
    kanban = (vault / "01-work-tracking/Agent Studio Kanban.md").read_text()
    objective_audit = (
        vault / "01-work-tracking/Agent Studio Objective Completion Audit.md"
    ).read_text()
    active_context = (vault / "wiki/ops/active-codex-context.md").read_text()
    research = (vault / "02-research/retrieval-quality-research.html").read_text()
    moc = (vault / "Agent Studio MOC.md").read_text()
    index = (vault / "wiki/_index.md").read_text()
    hld = (vault / "00-system-design/HLD - Agent Studio.md").read_text()
    lld = (vault / "00-system-design/LLD - Agent Studio.md").read_text()
    system_design_hld = (
        ROOT
        / "system_design_vault/04-agent-studio-implications/HLD - Agent Studio System Design.md"
    ).read_text()
    system_design_lld = (
        ROOT
        / "system_design_vault/04-agent-studio-implications/LLD - Agent Studio System Design.md"
    ).read_text()
    system_design_moc = (ROOT / "system_design_vault/MOC.md").read_text()
    system_design_home = (
        ROOT / "system_design_vault/agent-studio-system-design-home.html"
    ).read_text()
    system_design_source_map_viewer = (
        ROOT / "system_design_vault/output/viewers/system-design-source-map.html"
    ).read_text()
    system_design_objective_audit = (
        ROOT
        / "system_design_vault/04-agent-studio-implications/agent-studio-objective-completion-audit.md"
    ).read_text()
    roster = (
        vault / "00-system-design/Agent Roster and Responsibilities.md"
    ).read_text()
    sprint = (vault / "01-work-tracking/Current Sprint.md").read_text()
    log = (vault / "log.md").read_text()
    next_app_readme = (ROOT / "frontend/next-app/README.md").read_text()
    decisions = (vault / "01-work-tracking/Decision Log.md").read_text()
    retrieval_note = (
        vault / "02-research/Retrieval Intelligence and Knowledge Graph Research.md"
    ).read_text()
    feedback = (vault / "03-review-packets/Feedback Inbox.md").read_text()

    for body in [
        home,
        design,
        a2a_map,
        skill_matrix,
        proof_readiness,
        feedback_loop_map,
        publication_boundary,
        gemma_voice_boundary,
        tracker,
        research,
        system_design_home,
        system_design_source_map_viewer,
    ]:
        assert body.lower().startswith("<!doctype html>")
        assert "Kanban" not in body

    for body in [
        moc,
        index,
        kanban,
        objective_audit,
        active_context,
        hld,
        lld,
        roster,
        sprint,
        decisions,
        retrieval_note,
        feedback,
    ]:
        assert body.startswith("---\n")

    for body in [hld, lld, roster, decisions, retrieval_note, feedback]:
        assert "Kanban" not in body

    assert "Obsidian vault control surface" in home
    assert "Open Agent Studio Memory OS" in home
    assert "output/viewers/agent-studio-memory-os-viewer.html" in home
    assert "Open Agent Studio System Design Viewer" in home
    assert "output/viewers/agent-studio-system-design-viewer.html" in home
    assert "Open System Design Source Map Viewer" in home
    assert "../system_design_vault/output/viewers/system-design-source-map.html" in home
    assert "Open Agent Studio A2A Map" in home
    assert "00-system-design/agent-studio-a2a-map.html" in home
    assert "Open Agent Studio Skill Matrix" in home
    assert "00-system-design/agent-studio-skill-matrix.html" in home
    assert "Open Agent Studio Proof Readiness" in home
    assert "01-work-tracking/agent-studio-proof-readiness.html" in home
    assert "proof-plan packets" in home
    assert "proof_plan" in home
    assert "proof_plan.operator_proof_packet" in home
    assert "compact provider-proof-plan packet" in home
    assert "current-proof-status.md" in home
    assert "current-blocker-matrix.json" in home
    assert "operator-unblocker-checklist.md" in home
    assert "Open Agent Studio Feedback Loop Map" in home
    assert "03-review-packets/agent-studio-feedback-loop-map.html" in home
    assert "Open Agent Studio Publication Boundary Map" in home
    assert "03-review-packets/agent-studio-publication-boundary-map.html" in home
    assert "Open OpenRouter LiveKit Voice Boundary Map" in home
    assert "02-research/gemma-voice-boundary-map.html" in home
    assert "[[00-system-design/HLD - Agent Studio]]" in moc
    assert "[[00-system-design/LLD - Agent Studio]]" in moc
    assert "[[01-work-tracking/Agent Studio Kanban]]" in moc
    assert "[[01-work-tracking/Agent Studio Objective Completion Audit]]" in moc
    assert "Skill Matrix HTML: `00-system-design/agent-studio-skill-matrix.html`" in moc
    assert "A2A Map HTML: `00-system-design/agent-studio-a2a-map.html`" in moc
    assert "Proof Readiness HTML: `01-work-tracking/agent-studio-proof-readiness.html`" in moc
    assert "proof_plan proof-plan packets" in moc
    assert "proof_plan.operator_proof_packet" in moc
    assert "compact provider-proof-plan packet" in moc
    assert "current-proof-status.md" in moc
    assert "current-blocker-matrix.json" in moc
    assert "operator-unblocker-checklist.md" in moc
    assert "Feedback Loop Map HTML: `03-review-packets/agent-studio-feedback-loop-map.html`" in moc
    assert "Publication Boundary HTML: `03-review-packets/agent-studio-publication-boundary-map.html`" in moc
    assert "OpenRouter LiveKit Voice Boundary HTML: `02-research/gemma-voice-boundary-map.html`" in moc
    assert "System Design Source Map Viewer: `../system_design_vault/output/viewers/system-design-source-map.html`" in moc
    assert "[[../01-work-tracking/Agent Studio Kanban]]" in index
    assert "[[../01-work-tracking/Agent Studio Objective Completion Audit]]" in index
    assert "proof_plan proof-plan packets" in index
    assert "proof_plan.operator_proof_packet" in index
    assert "compact provider-proof-plan packet" in index
    assert "current-proof-status.md" in index
    assert "current-blocker-matrix.json" in index
    assert "operator-unblocker-checklist.md" in index
    assert "updated: 2026-05-21" in moc
    assert "updated: 2026-05-21" in index
    assert "type: kanban" in kanban
    assert "boundary: planning-vault-only" in kanban
    assert "## Backlog" in kanban
    assert "## Ready" in kanban
    assert "## In Progress" in kanban
    assert "## Blocked" in kanban
    assert "## Done" in kanban
    assert "## Review Watch" in kanban
    assert "Review-watch heartbeat alignment current" in kanban
    assert "Leibniz latest status: no Critical/Important findings" in kanban
    assert "Conversation-turn durable event redaction added" in kanban
    assert "conversation_turn_recorded" in kanban
    assert "safe_realtime_metadata" in kanban
    assert "Feedback and memory durable event redaction added" in kanban
    assert "FeedbackRoutingWorkflow" in kanban
    assert "RevisionWorkflow" in kanban
    assert "feedback_recorded" in kanban
    assert "memory_recorded" in kanban
    assert "Project-memory and publish-readiness durable event redaction added" in kanban
    assert "ProjectMemoryWorkflow" in kanban
    assert "PublishReadinessWorkflow" in kanban
    assert "project_memory_recorded" in kanban
    assert "publish_readiness_checked" in kanban
    assert "A2A skill-invocation event redaction added" in kanban
    assert "agent_skill_invocation_recorded" in kanban
    assert "public_a2a_skill_invocation_event_payload" in kanban
    assert "A2A context-packet event redaction added" in kanban
    assert "context_packet_built" in kanban
    assert "public_a2a_context_packet_event_payload" in kanban
    assert "A2A stale-recovery event redaction added" in kanban
    assert "agent_message_recovered" in kanban
    assert "public_a2a_recovered_event_payload" in kanban
    assert "A2A retry/dependency event redaction added" in kanban
    assert "agent_message_retry_authorized" in kanban
    assert "agent_message_dependencies_repaired" in kanban
    assert "public_a2a_retry_event_payload" in kanban
    assert "agent_message_dependency_waiting" in kanban
    assert "agent_message_retry_exhausted" in kanban
    assert "A2A status-event redaction added" in kanban
    assert "agent_message_status_updated" in kanban
    assert "worker `skill_ids`" in kanban
    assert "A2A accepted-message event redaction added" in kanban
    assert "agent_message_accepted" in kanban
    assert "claimed_by_agent_id" in kanban
    assert "redact_realtime_string" in kanban
    assert "A2A graph trace identity fix-back" in kanban
    assert "trace actor/action/status" in kanban
    assert "Keep vault-sync/review-watch heartbeat aligned with code-review output." not in kanban
    assert "Product app must not render this board" in kanban
    assert "current-proof-status.md" in kanban
    assert "current-blocker-matrix.json" in kanban
    assert "operator-unblocker-checklist.md" in kanban
    assert "Proof-plan operator packet handoff added" in kanban
    assert "proof_plan.operator_proof_packet" in kanban
    assert "proof_plan_operator_packet" in kanban
    assert "compact provider-proof-plan packet" in kanban
    assert "Report-only operator-input retry chain" in kanban
    assert "Guarded operator-input retry chain" in kanban
    assert "Objective completion audit added" in kanban
    assert "System-design-vault browser index proof added" in kanban
    assert "tests/test_system_design_vault_home_browser.py" in kanban
    assert "Vault home generated-viewer navigation proof added" in kanban
    assert "tests/test_vault_home_browser.py" in kanban
    assert "Retrieval research browser filter proof added" in kanban
    assert "Graph" in kanban
    assert "HLD/LLD design-review browser interaction proof added" in kanban
    assert "Codex Browser Proof" in kanban
    assert "agent-studio-hld-lld" in kanban
    assert "Work tracker browser interaction proof added" in kanban
    assert "Functional Content Studio Cockpit" in kanban
    assert "agent-studio-work-tracker" in kanban
    assert "Generated Memory OS viewer browser interaction proof added" in kanban
    assert "Output Memory" in kanban
    assert "Work-plan execution browser single-flight proof added" in kanban
    assert "Run next steps" in kanban
    assert "work-plan materialization" in kanban
    assert "post-run next-action refresh" in kanban
    assert "Source-refresh browser single-flight proof added" in kanban
    assert "A2A source-refresh message" in kanban
    assert "Web Research / Claim Verification worker cycle" in kanban
    assert "Always-on/background-runner browser status proof added" in kanban
    assert "Start always-on" in kanban
    assert "Start runner" in kanban
    assert "Activity retry browser single-flight proof added" in kanban
    assert "Queue and run" in kanban
    assert "Skill matrix browser proof added" in kanban
    assert "tests/test_skill_matrix_browser.py" in kanban
    assert "Proof readiness browser proof added" in kanban
    assert "tests/test_proof_readiness_browser.py" in kanban
    assert "A2A map browser proof added" in kanban
    assert "tests/test_a2a_map_browser.py" in kanban
    assert "Feedback loop map browser proof added" in kanban
    assert "tests/test_feedback_loop_map_browser.py" in kanban
    assert "Feedback loop map review-watch escalation added" in kanban
    assert "System-design vault entry links to review and generated viewer added" in kanban
    assert "System-design source-map viewer browser proof added" in kanban
    assert "design implications, implication search, visible record counts, no-match states, and clickable source-note paths" in kanban
    assert "OpenRouter LiveKit voice boundary browser proof added" in kanban
    assert "tests/test_gemma_voice_boundary_browser.py" in kanban
    assert "Publication boundary browser proof added" in kanban
    assert "tests/test_publication_boundary_browser.py" in kanban
    assert "type: objective-completion-audit" in objective_audit
    assert "Requirement Coverage" in objective_audit
    assert "Long-running autonomous multi-agent content loop" in objective_audit
    assert "OpenRouter DeepSeek V4 Flash over LiveKit with Kokoro output" in objective_audit
    assert "Realtime audio system" in objective_audit
    assert "A2A-style collaboration" in objective_audit
    assert "Latest conversation-turn durable event redaction update" in objective_audit
    assert "conversation_turn_recorded" in objective_audit
    assert "ConversationTurn" in objective_audit
    assert "Latest feedback and memory durable event redaction update" in objective_audit
    assert "FeedbackRoutingWorkflow" in objective_audit
    assert "RevisionWorkflow" in objective_audit
    assert "FeedbackItem" in objective_audit
    assert "AgentMemory" in objective_audit
    assert "Latest project-memory and publish-readiness durable event redaction update" in objective_audit
    assert "ProjectMemoryWorkflow" in objective_audit
    assert "PublishReadinessWorkflow" in objective_audit
    assert "project_memory_recorded" in objective_audit
    assert "publish_readiness_checked" in objective_audit
    assert "A2A skill-invocation event redaction" in objective_audit
    assert "public_a2a_skill_invocation_event_payload" in objective_audit
    assert "A2A context-packet event redaction" in objective_audit
    assert "public_a2a_context_packet_event_payload" in objective_audit
    assert "A2A stale-recovery event redaction" in objective_audit
    assert "public_a2a_recovered_event_payload" in objective_audit
    assert "A2A retry/dependency event redaction" in objective_audit
    assert "public_a2a_retry_event_payload" in objective_audit
    assert "public_a2a_dependency_repair_event_payload" in objective_audit
    assert "public_a2a_dependency_waiting_event_payload" in objective_audit
    assert "public_a2a_retry_exhausted_event_payload" in objective_audit
    assert "A2A status-event redaction" in objective_audit
    assert "public_a2a_status_event_payload" in objective_audit
    assert "A2A accepted-message event redaction" in objective_audit
    assert "agent-message-public-projection-v1" in objective_audit
    assert "claimed_by_agent_id" in objective_audit
    assert "A2A collaboration graph trace-note redaction" in objective_audit
    assert "trace actor/action/status" in objective_audit
    assert "A2A map browser proof" in objective_audit
    assert "agent-studio-a2a-map.html" in objective_audit
    assert "Interactive HTML knowledge surfaces" in objective_audit
    assert "system-design-vault Agent Studio index" in objective_audit
    assert "system-design vault entry links to review and generated viewer" in objective_audit
    assert "Project HLD/LLD Review Surface" in objective_audit
    assert "Project System Design Viewer" in objective_audit
    assert "generated viewer inspection" in objective_audit
    assert "system-design source-map viewer browser proof" in objective_audit
    assert "tests/test_system_design_source_map_viewer_browser.py" in objective_audit
    assert "source records, source groups, policy lists, first-slice items, search, kind filter, and coverage-granularity filter" in objective_audit
    assert "design implications, implication search, visible record counts, no-match states, and clickable source-note paths" in objective_audit
    assert "vault-home generated-viewer navigation" in objective_audit
    assert "retrieval research filtering" in objective_audit
    assert "Kanban tracking" in objective_audit
    assert "HLD/LLD comment export" in objective_audit
    assert "work-tracker export loop" in objective_audit
    assert "status advancement and export" in objective_audit
    assert "Agent skills and roster" in objective_audit
    assert "skill matrix browser proof" in objective_audit
    assert "agent-studio-skill-matrix.html" in objective_audit
    assert "Guardrails, source quality, and publish gates" in objective_audit
    assert "Feedback loops" in objective_audit
    assert "feedback loop map browser proof" in objective_audit
    assert "agent-studio-feedback-loop-map.html" in objective_audit
    assert "leibniz-review-watch-escalation" in objective_audit
    assert "019e3899-5ab3-7171-9d3c-32e7c57bbde7" in objective_audit
    assert "severity, files, and next action" in objective_audit
    assert "OpenRouter LiveKit voice boundary browser proof" in objective_audit
    assert "gemma-voice-boundary-map.html" in objective_audit
    assert "publication boundary browser proof" in objective_audit
    assert "agent-studio-publication-boundary-map.html" in objective_audit
    assert "provider-backed live voice proof" in objective_audit
    assert "external publication proof" in objective_audit
    assert "proof-readiness browser surface" in objective_audit
    assert "agent-studio-proof-readiness.html" in objective_audit
    assert "one work-plan materialization plus one bounded planned worker cycle" in objective_audit
    assert "source-refresh browser single-flight proof" in objective_audit
    assert "This audit does not mark the objective complete" in objective_audit
    assert "Do not call the goal complete" in objective_audit
    assert "Start always-on and Start runner" in objective_audit
    assert "Activity retry browser single-flight proof" in objective_audit
    assert "source_vault_note" in system_design_objective_audit
    assert "social_media_optimiser/01-work-tracking/Agent Studio Objective Completion Audit.md" in system_design_objective_audit
    assert "same-session LiveKit/reasoning/Kokoro proof" in system_design_objective_audit
    assert "OpenRouter text reasoning" in system_design_objective_audit
    assert "without `GEMMA4_MULTIMODAL_ENDPOINT_URL`" in system_design_objective_audit
    assert "system-design-vault Agent Studio index" in system_design_objective_audit
    assert "system-design-vault home links to the project HLD/LLD review surface" in system_design_objective_audit
    assert "Project HLD/LLD Review Surface" in system_design_objective_audit
    assert "Project System Design Viewer" in system_design_objective_audit
    assert "generated viewer inspection" in system_design_objective_audit
    assert "system-design source-map viewer browser proof" in system_design_objective_audit
    assert "tests/test_system_design_source_map_viewer_browser.py" in system_design_objective_audit
    assert "design implications, implication search, visible record counts, no-match states, and clickable source-note paths" in system_design_objective_audit
    assert "objective-audit mirror" in system_design_objective_audit
    assert "vault-home navigation to generated viewers" in system_design_objective_audit
    assert "retrieval research filter surface" in system_design_objective_audit
    assert "HLD/LLD design-review surface" in system_design_objective_audit
    assert "exported comment packets" in system_design_objective_audit
    assert "Obsidian work tracker" in system_design_objective_audit
    assert "exported tracker packets" in system_design_objective_audit
    assert "Run next steps" in system_design_objective_audit
    assert "bounded planned worker cycle" in system_design_objective_audit
    assert "Run web research" in system_design_objective_audit
    assert "A2A source-refresh message" in system_design_objective_audit
    assert "Start always-on and Start runner" in system_design_objective_audit
    assert "Activity retry browser single-flight proof" in system_design_objective_audit
    assert "skill matrix browser proof" in system_design_objective_audit
    assert "proof-readiness browser surface" in system_design_objective_audit
    assert "proof_plan_operator_packet" in system_design_objective_audit
    assert "compact provider-proof-plan packet" in system_design_objective_audit
    assert "richer current-matrix operator packet" in system_design_objective_audit
    assert "conversation-turn durable event redaction" in system_design_objective_audit
    assert "conversation_turn_recorded" in system_design_objective_audit
    assert "safe_realtime_metadata" in system_design_objective_audit
    assert "feedback and memory durable event redaction" in system_design_objective_audit
    assert "FeedbackRoutingWorkflow" in system_design_objective_audit
    assert "RevisionWorkflow" in system_design_objective_audit
    assert "FeedbackItem" in system_design_objective_audit
    assert "AgentMemory" in system_design_objective_audit
    assert "project-memory and publish-readiness durable event redaction" in system_design_objective_audit
    assert "ProjectMemoryWorkflow" in system_design_objective_audit
    assert "PublishReadinessWorkflow" in system_design_objective_audit
    assert "project_memory_recorded" in system_design_objective_audit
    assert "publish_readiness_checked" in system_design_objective_audit
    assert "A2A status-event redaction" in system_design_objective_audit
    assert "A2A skill-invocation event redaction" in system_design_objective_audit
    assert "public_a2a_skill_invocation_event_payload" in system_design_objective_audit
    assert "A2A context-packet event redaction" in system_design_objective_audit
    assert "public_a2a_context_packet_event_payload" in system_design_objective_audit
    assert "A2A stale-recovery event redaction" in system_design_objective_audit
    assert "public_a2a_recovered_event_payload" in system_design_objective_audit
    assert "A2A retry/dependency event redaction" in system_design_objective_audit
    assert "agent_message_retry_authorized" in system_design_objective_audit
    assert "agent_message_dependencies_repaired" in system_design_objective_audit
    assert "public_a2a_dependency_repair_event_payload" in system_design_objective_audit
    assert "public_a2a_retry_exhausted_event_payload" in system_design_objective_audit
    assert "agent_message_status_updated" in system_design_objective_audit
    assert "A2A accepted-message event redaction" in system_design_objective_audit
    assert "durable accepted-message events" in system_design_objective_audit
    assert "claimant" in system_design_objective_audit
    assert "A2A map browser proof" in system_design_objective_audit
    assert "feedback loop map browser proof" in system_design_objective_audit
    assert "leibniz-review-watch-escalation" in system_design_objective_audit
    assert "019e3899-5ab3-7171-9d3c-32e7c57bbde7" in system_design_objective_audit
    assert "severity, files, and next action" in system_design_objective_audit
    assert "OpenRouter LiveKit voice boundary browser proof" in system_design_objective_audit
    assert "publication boundary browser proof" in system_design_objective_audit
    assert "agent-studio-system-design-home.html" in system_design_moc
    assert (
        "../social_media_optimiser/01-work-tracking/agent-studio-proof-readiness.html"
        in system_design_moc
    )
    assert (
        "../social_media_optimiser/01-work-tracking/Agent Studio Kanban.md"
        in system_design_moc
    )
    assert (
        "../social_media_optimiser/01-work-tracking/agent-studio-work-tracker.html"
        in system_design_moc
    )
    assert (
        "../social_media_optimiser/00-system-design/agent-studio-a2a-map.html"
        in system_design_moc
    )
    assert (
        "../social_media_optimiser/00-system-design/agent-studio-skill-matrix.html"
        in system_design_moc
    )
    assert (
        "../social_media_optimiser/00-system-design/agent-studio-hld-lld.html"
        in system_design_moc
    )
    assert (
        "../social_media_optimiser/output/viewers/agent-studio-system-design-viewer.html"
        in system_design_moc
    )
    assert "comment export" in system_design_moc
    assert "generated viewer" in system_design_moc
    assert (
        "../social_media_optimiser/03-review-packets/agent-studio-feedback-loop-map.html"
        in system_design_moc
    )
    assert "leibniz-review-watch-escalation" in system_design_moc
    assert "proof_plan proof-plan packets" in system_design_moc
    assert "proof_plan.operator_proof_packet" in system_design_moc
    assert "proof_plan_operator_packet" in system_design_moc
    assert "compact provider-proof-plan packet" in system_design_moc
    assert "current-proof-status.md" in system_design_moc
    assert "current-blocker-matrix.json" in system_design_moc
    assert "operator-unblocker-checklist.md" in system_design_moc
    assert "[[04-agent-studio-implications/agent-studio-objective-completion-audit]]" in system_design_moc
    ready_lane = kanban.split("## Ready", 1)[1].split("## In Progress", 1)[0]
    assert "compact operator handoff" not in ready_lane
    assert kanban.count("Compact Kanban handoff added to active Codex context") == 1
    assert "## Kanban Handoff" in active_context
    assert "[[../../01-work-tracking/Agent Studio Kanban]]" in active_context
    kanban_handoff = active_context.split("## Kanban Handoff", 1)[1].split(
        "## Implementation Workflow Rule", 1
    )[0]
    assert "current-proof-status.md" in kanban_handoff
    assert "current-blocker-matrix.json" in kanban_handoff
    assert "operator-unblocker-checklist.md" in kanban_handoff
    assert "proof_plan.operator_proof_packet" in kanban_handoff
    assert "proof_plan_operator_packet" in kanban_handoff
    assert "compact provider-proof-plan packet" in kanban_handoff
    assert "Next board item:" in active_context
    next_board_handoff = active_context.split("- Next board item:", 1)[1].split(
        "## Current Implementation State", 1
    )[0]
    assert "select the next bounded implementation slice" in next_board_handoff
    assert "failing-first test" in next_board_handoff
    assert "implementation target" in next_board_handoff
    assert "validation plan" in next_board_handoff
    assert "small product/proof hardening patch" in next_board_handoff
    assert "credential-gated publication proof remains blocked" in next_board_handoff
    assert "current review-watch status" in next_board_handoff
    assert "compact proof-plan provenance verification finishes" not in next_board_handoff
    assert "system-design-vault browser index proof" in active_context
    assert "agent-studio-system-design-home.html" in active_context
    uuid_run_log = next(
        line
        for line in log.splitlines()
        if "Captured the first actual UUID-backed provider-proof product run" in line
    )
    assert "current live-dialogue path is OpenRouter `deepseek/deepseek-v4-flash`" in uuid_run_log
    assert "no live-voice operator-input blockers" in uuid_run_log
    assert "provider-backed live-voice proof is accepted" in uuid_run_log
    assert "external publication proof remains open" in uuid_run_log
    assert "LiveKit, and Kokoro readiness" not in uuid_run_log
    assert "blocked_by_missing_accepted_proof" not in uuid_run_log
    assert "System-design Objective Completion Audit routes now render required evidence after unblock" in log
    assert "Added project-memory and publish-readiness durable event redaction" in log
    assert "Added feedback and memory durable event redaction" in log
    assert "feedback_recorded" in log
    assert "memory_recorded" in log
    assert "status=blocked_by_operator_inputs" in log
    assert "Added review-watch escalation coverage to the Agent Studio feedback loop map" in log
    assert "leibniz-review-watch-escalation" in log
    assert "system-design vault entry links now route reviewers" in log
    assert "Project HLD/LLD Review Surface" in log
    assert "Project System Design Viewer" in log
    assert "system-design source-map viewer browser proof" in log
    assert "source records, source groups, policy lists, first-slice items, search, kind filter, and coverage-granularity filter" in log
    assert "design implications, implication search, visible record counts, no-match states, and clickable source-note paths" in log
    assert "Project Proof Readiness Surface" in system_design_home
    assert "../social_media_optimiser/01-work-tracking/agent-studio-proof-readiness.html" in system_design_home
    assert "Project Work Tracker" in system_design_home
    assert "../social_media_optimiser/01-work-tracking/agent-studio-work-tracker.html" in system_design_home
    assert "planning board stays out of product UI" in system_design_home
    assert "Project A2A Map" in system_design_home
    assert "../social_media_optimiser/00-system-design/agent-studio-a2a-map.html" in system_design_home
    assert "projection=public" in system_design_home
    assert "Project Skill Matrix" in system_design_home
    assert "../social_media_optimiser/00-system-design/agent-studio-skill-matrix.html" in system_design_home
    assert "agent-studio-guardrails-review" in system_design_home
    assert "Project HLD/LLD Review Surface" in system_design_home
    assert "../social_media_optimiser/00-system-design/agent-studio-hld-lld.html" in system_design_home
    assert "Project System Design Viewer" in system_design_home
    assert "../social_media_optimiser/output/viewers/agent-studio-system-design-viewer.html" in system_design_home
    assert "comment export" in system_design_home
    assert "generated viewer" in system_design_home
    assert "Project OpenRouter LiveKit Voice Boundary Map" in system_design_home
    assert "../social_media_optimiser/02-research/gemma-voice-boundary-map.html" in system_design_home
    assert "Project Publication Boundary Map" in system_design_home
    assert "../social_media_optimiser/03-review-packets/agent-studio-publication-boundary-map.html" in system_design_home
    assert "Project Feedback Loop Map" in system_design_home
    assert "../social_media_optimiser/03-review-packets/agent-studio-feedback-loop-map.html" in system_design_home
    assert "leibniz-review-watch-escalation" in system_design_home
    assert "severity, files, and next action" in system_design_home
    assert "credential snapshot exports" in system_design_home
    assert "proof-plan packets" in system_design_home
    assert "proof_plan" in system_design_home
    assert "proof_plan.operator_proof_packet" in system_design_home
    assert "proof_plan_operator_packet" in system_design_home
    assert "compact provider-proof-plan packet" in system_design_home
    assert "current-proof-status.md" in system_design_home
    assert "current-blocker-matrix.json" in system_design_home
    assert "operator-unblocker-checklist.md" in system_design_home
    assert "secret_values_printed=false" in system_design_home
    assert "vault home generated-viewer navigation proof" in active_context
    assert "System Design Viewer" in active_context
    assert "retrieval research browser filter proof" in active_context
    assert "Graph research area" in active_context
    assert "HLD/LLD design-review browser interaction proof" in active_context
    assert "Codex Browser Proof" in active_context
    assert "agent-studio-hld-lld" in active_context
    assert "routing action" in active_context
    assert "work tracker browser interaction proof" in active_context
    assert "Functional Content Studio Cockpit" in active_context
    assert "agent-studio-work-tracker" in active_context
    assert "requested planning action" in active_context
    assert "generated Memory OS viewer browser interaction proof" in active_context
    assert "Output Memory" in active_context
    assert "work-plan execution browser single-flight proof" in active_context
    assert "Run next steps" in active_context
    assert "work-plan materialization" in active_context
    assert "bounded planned worker cycle" in active_context
    assert "post-run next-action refresh" in active_context
    assert "source-refresh browser single-flight proof" in active_context
    assert "Run web research" in active_context
    assert "A2A source-refresh message" in active_context
    assert "Web Research / Claim Verification worker cycle" in active_context
    assert "always-on/background-runner browser status proof" in active_context
    assert "Start always-on" in active_context
    assert "Start runner" in active_context
    assert "Always-on studio launch recorded" in active_context
    assert "Background runner is running" in active_context
    assert "Activity retry browser single-flight proof" in active_context
    assert "Queue and run" in active_context
    assert "skill matrix browser proof" in active_context
    assert "agent-studio-skill-matrix.html" in active_context
    assert "proof readiness browser proof" in active_context
    assert "agent-studio-proof-readiness.html" in active_context
    assert "A2A map browser proof" in active_context
    assert "agent-studio-a2a-map.html" in active_context
    a2a_current_state = next(
        line
        for line in active_context.splitlines()
        if line.startswith("- A2A discovery now has a public")
    )
    assert "`/.well-known/agent-card.json`" in a2a_current_state
    assert "`/api/a2a`" in a2a_current_state
    assert "`projection=public`" in a2a_current_state
    assert "`agent-message-public-projection-v1`" in a2a_current_state
    assert "`getTask`" in a2a_current_state
    assert "`listRunMessages`" in a2a_current_state
    assert "`agentInbox`" in a2a_current_state
    assert "feedback loop map browser proof" in active_context
    assert "agent-studio-feedback-loop-map.html" in active_context
    assert "system-design vault entry links to the HLD/LLD review surface" in active_context
    assert "Project System Design Viewer" in active_context
    assert "system-design source-map viewer browser proof" in active_context
    assert "system-design-source-map.html" in active_context
    assert "design implications, implication search, visible record counts, no-match states, and clickable source-note paths" in active_context
    assert "OpenRouter LiveKit voice boundary browser proof" in active_context
    assert "gemma-voice-boundary-map.html" in active_context
    assert "publication boundary browser proof" in active_context
    assert "agent-studio-publication-boundary-map.html" in active_context
    assert "objective completion audit added" in active_context
    assert "Agent Studio Objective Completion Audit.md" in active_context
    assert "creator-visible always-on/background-runner copy tightening" in active_context
    assert "Always-on studio started" in active_context
    assert "Specialist pulse finished" in active_context
    assert "Creator always-on studio" in active_context
    assert "raw backend result summaries" in active_context
    assert "Starting background runner" in active_context
    assert "browser-level interaction coverage" in active_context
    assert "source-contract action single-flight guards" in active_context
    assert "rapidly double-clicks Generate" in active_context
    assert "Run web research" in active_context
    assert "Run next steps" in active_context
    assert "Queue and run" in active_context
    assert "each guarded path must create exactly one backend action" in active_context
    assert "mocked stale backend summaries" in next_app_readme
    assert "A2A message creation" in next_app_readme
    assert "work-plan materialization" in next_app_readme
    assert "planned worker execution" in next_app_readme
    assert "post-run plan refresh" in next_app_readme
    assert "targeted retry worker cycle" in next_app_readme
    assert "Queue and run" in next_app_readme
    assert "bounded worker cycle" in next_app_readme
    assert "Always-on studio and Background runner" in next_app_readme
    assert "provider-backed live-voice proof record is now accepted" in active_context
    assert "Publication inputs remain blocked on LinkedIn credential" in active_context
    assert "focused review packet to `Leibniz`" in active_context
    assert "Current conversation-turn durable event boundary" in active_context
    assert "conversation_turn_recorded" in active_context
    assert "safe_realtime_metadata" in active_context
    assert "Current project-memory and publish-readiness durable event boundary" in active_context
    assert "project_memory_recorded" in active_context
    assert "publish_readiness_checked" in active_context
    assert "Current feedback and memory durable event boundary" in active_context
    assert "feedback_recorded" in active_context
    assert "memory_recorded" in active_context
    assert "FeedbackItem" in active_context
    assert "AgentMemory" in active_context
    assert "A2A skill-invocation event redaction" in active_context
    assert "agent_skill_invocation_recorded" in active_context
    assert "public_a2a_skill_invocation_event_payload" in active_context
    assert "A2A context-packet event redaction" in active_context
    assert "public_a2a_context_packet_event_payload" in active_context
    assert "A2A stale-recovery event redaction" in active_context
    assert "public_a2a_recovered_event_payload" in active_context
    assert "A2A retry/dependency event redaction" in active_context
    assert "public_a2a_dependency_repair_event_payload" in active_context
    assert "public_a2a_retry_exhausted_event_payload" in active_context
    assert "A2A status-event redaction" in active_context
    assert "public_a2a_status_event_payload" in active_context
    assert "worker `skill_ids`" in active_context
    assert "A2A accepted-message event redaction" in active_context
    assert "src/all_about_llms/orchestration/a2a_projection.py" in active_context
    assert "claimed_by_agent_id" in active_context
    assert "redact_realtime_string" in active_context
    assert "A2A graph trace identity fix-back" in active_context
    assert "compact `Local scheduler` proof" not in active_context
    assert "Start/Stop scheduler controls" not in active_context
    assert "compact `Background runner` proof" in active_context
    assert "Start/Stop background-runner controls" in active_context
    assert "Obsidian-native notes first" in decisions
    assert "focus more on using Obsidian" in feedback
    assert "Realtime Dialogue Layer" in hld
    assert "Retrieval Intelligence" in hld
    assert "well-known Agent Card" in hld
    assert "`/.well-known/agent-card.json`" in hld
    assert "`/api/a2a`" in hld
    assert "`projection=public`" in hld
    assert "`agent-message-public-projection-v1`" in hld
    assert "`getTask`" in hld
    assert "`listRunMessages`" in hld
    assert "`agentInbox`" in hld
    assert "Leibniz review-watch escalation loop" in hld
    assert "019e3899-5ab3-7171-9d3c-32e7c57bbde7" in hld
    assert "severity, files, and next action" in hld
    assert "agent-studio-feedback-loop-map.html" in hld
    assert "well-known Agent Card" in system_design_hld
    assert "`/.well-known/agent-card.json`" in system_design_hld
    assert "`/api/a2a`" in system_design_hld
    assert "`projection=public`" in system_design_hld
    assert "`agent-message-public-projection-v1`" in system_design_hld
    assert "`getTask`" in system_design_hld
    assert "`listRunMessages`" in system_design_hld
    assert "`agentInbox`" in system_design_hld
    assert "Leibniz review-watch escalation loop" in system_design_hld
    assert "019e3899-5ab3-7171-9d3c-32e7c57bbde7" in system_design_hld
    assert "severity, files, and next action" in system_design_hld
    assert "agent-studio-feedback-loop-map.html" in system_design_hld
    assert "RetrievalCandidate" in lld
    assert "KnowledgeGraphNode" in lld
    assert "creator Activity rail can show `Local scheduler` status" not in lld
    assert "creator Activity rail shows `Background runner` status" in lld
    assert (
        "creator Activity rail can show `Local scheduler` status"
        not in system_design_lld
    )
    assert "creator Activity rail shows `Background runner` status" in system_design_lld
    assert "Retrieval Intelligence Agent" in roster
    assert "Current Sprint" in sprint
    assert "browser-openable Agent Studio index" in sprint
    assert "system_design_vault/agent-studio-system-design-home.html" in sprint
    assert "vault home" in sprint
    assert "generated Memory OS and System Design Viewer links" in sprint
    assert "Retrieval Quality Research HTML surface" in sprint
    assert "Graph research area" in sprint
    assert "Added browser-level interaction proof for the Agent Studio HLD/LLD design-review surface" in sprint
    assert "Codex Browser Proof" in sprint
    assert "Added browser-level interaction proof for the Agent Studio work tracker HTML" in sprint
    assert "exported tracker packet" in sprint
    assert "Added browser-level interaction proof for the Agent Studio skill matrix" in sprint
    assert "feedback_resolution_ledger" in sprint
    assert "Added browser-level interaction proof for the Agent Studio proof readiness surface" in sprint
    assert "provider-backed-live-voice-proof" in sprint
    assert "Added browser-level interaction proof for the Agent Studio A2A map" in sprint
    assert "public-a2a-discovery-boundary" in sprint
    assert "conversation-turn durable event redaction" in sprint
    assert "conversation_turn_recorded" in sprint
    assert "safe_realtime_metadata" in sprint
    assert "project-memory and publish-readiness durable event redaction" in sprint
    assert "ProjectMemoryWorkflow" in sprint
    assert "PublishReadinessWorkflow" in sprint
    assert "feedback and memory durable event redaction" in sprint
    assert "FeedbackRoutingWorkflow" in sprint
    assert "RevisionWorkflow" in sprint
    assert "feedback_recorded" in sprint
    assert "memory_recorded" in sprint
    assert "A2A skill-invocation event redaction" in sprint
    assert "agent_skill_invocation_recorded" in sprint
    assert "public_a2a_skill_invocation_event_payload" in sprint
    assert "A2A context-packet event redaction" in sprint
    assert "context_packet_built" in sprint
    assert "public_a2a_context_packet_event_payload" in sprint
    assert "A2A stale-recovery event redaction" in sprint
    assert "agent_message_recovered" in sprint
    assert "public_a2a_recovered_event_payload" in sprint
    assert "A2A retry/dependency event redaction" in sprint
    assert "agent_message_dependencies_repaired" in sprint
    assert "agent_message_retry_exhausted" in sprint
    assert "public_a2a_retry_event_payload" in sprint
    assert "A2A status-event redaction" in sprint
    assert "agent_message_status_updated" in sprint
    assert "A2A accepted-message event redaction" in sprint
    assert "agent_message_accepted" in sprint
    assert "claimed_by_agent_id" in sprint
    assert "A2A collaboration graph trace-note redaction" in sprint
    assert "Bearer [redacted]" in sprint
    assert "trace actor/action/status" in sprint
    assert "Added browser-level interaction proof for the Agent Studio feedback loop map" in sprint
    assert "guardrails-feedback-resolution" in sprint
    assert "Added review-watch escalation coverage to the Agent Studio feedback loop map" in sprint
    assert "leibniz-review-watch-escalation" in sprint
    assert "severity, files, and next action" in sprint
    assert "Added system-design vault entry links to the HLD/LLD review surface" in sprint
    assert "Project HLD/LLD Review Surface" in sprint
    assert "Project System Design Viewer" in sprint
    assert "Added browser-level proof for the system-design source-map viewer" in sprint
    assert "tests/test_system_design_source_map_viewer_browser.py" in sprint
    assert "design implications, implication search, visible record counts, no-match states, and clickable source-note paths" in sprint
    assert "Added browser-level interaction proof for the OpenRouter LiveKit voice boundary map" in sprint
    assert "OPENROUTER_LIVEKIT_URL" in sprint
    assert "provider-backed-live-voice-proof" in sprint
    assert "Added browser-level interaction proof for the Agent Studio publication boundary map" in sprint
    assert "non-live-channel-smoke" in sprint
    assert "Extended the persistent browser single-flight smoke to cover work-plan execution" in sprint
    assert "one work-plan materialization" in sprint
    assert "one bounded planned worker cycle" in sprint
    assert "Extended the persistent browser single-flight smoke to cover source refresh" in sprint
    assert "one A2A source-refresh message" in sprint
    assert "Extended the browser single-flight smoke" in sprint
    assert "Queue and run" in sprint
    assert "targeted retry worker cycle" in sprint
    assert "Chromium browser smoke" in sprint
    assert "Proof-plan operator packet handoff" in sprint
    assert "proof_plan.operator_proof_packet" in sprint
    assert "proof_plan_operator_packet" in sprint
    assert "compact provider-proof-plan packet" in sprint
    assert "Reciprocal Rank Fusion" in retrieval_note
    assert "High-Level Design" in design
    assert "Low-Level Design" in design
    assert "Comments and Decisions" in design
    assert "localStorage" in design
    assert "agent-studio-hld-lld" in design
    assert "Route comments to the right design or implementation agent" in design
    assert "Retrieval Intelligence Agent" in design
    assert "Knowledge Graph Curator Agent" in design
    assert "No SQLite" in design
    assert "Postgres + pgvector" in design
    assert "Agent Studio A2A Map" in a2a_map
    assert "Planning memory only" in a2a_map
    assert "public-a2a-discovery-boundary" in a2a_map
    assert "/.well-known/agent-card.json" in a2a_map
    assert "/api/a2a/messages/{message_id}/dependencies/repair" in a2a_map
    assert "fullA2AProtocolServer=false" in a2a_map
    assert "JSON/text HTTP+JSON only" in a2a_map
    assert "method-aware endpoint records" in a2a_map
    assert "Realtime audio and image modes remain internal extension metadata" in a2a_map
    assert "a2a_collaboration_graph_built" in a2a_map
    assert "dependency_cycle_message_ids" in a2a_map
    assert "default-roster fallback is not valid repair" in a2a_map
    assert "agent-studio-skill-matrix" in a2a_map
    assert "Agent Studio Work Tracker" in tracker
    assert "Operating Rule" in tracker
    assert "agent-studio-work-tracker" in tracker
    assert "Use this tracker as the active planning state" in tracker
    assert "Agent Studio Skill Matrix" in skill_matrix
    assert "Planning memory only" in skill_matrix
    assert "agent-studio-guardrails-review" in skill_matrix
    assert "feedback_resolution_ledger" in skill_matrix
    assert "skills/agent-studio-guardrails-review/SKILL.md" in skill_matrix
    assert "agent-studio-inference-reliability" in skill_matrix
    assert "Agent Studio Proof Readiness" in proof_readiness
    assert "Planning memory only" in proof_readiness
    assert "provider-backed-live-voice-proof" in proof_readiness
    assert "external-publication-proof" in proof_readiness
    assert "GEMMA4_MULTIMODAL_ENDPOINT_URL" not in proof_readiness
    assert "KOKORO_TTS_ENDPOINT_URL" not in proof_readiness
    assert "GEMMA4_REALTIME_LIVEKIT_URL" not in proof_readiness
    assert "OPENROUTER_API_KEY_FILE" in proof_readiness
    assert "OPENROUTER_LIVEKIT_URL" in proof_readiness
    assert "LIVEKIT_API_KEY_FILE or LIVEKIT_API_KEY" in proof_readiness
    assert "LIVEKIT_API_SECRET_FILE or LIVEKIT_API_SECRET" in proof_readiness
    assert "provider-smoke ledger with execute_live_calls=true" in proof_readiness
    assert "realtime_voice_timing_ledger" in proof_readiness
    assert "participant presence" in proof_readiness
    assert "INSTAGRAM_ACCESS_TOKEN" not in proof_readiness
    assert "INSTAGRAM_ACCESS_TOKEN_FILE" not in proof_readiness
    assert "LINKEDIN_ACCESS_TOKEN" in proof_readiness
    assert "LINKEDIN_ACCESS_TOKEN_FILE" in proof_readiness
    assert "X_ACCESS_TOKEN" not in proof_readiness
    assert "X_ACCESS_TOKEN_FILE" not in proof_readiness
    assert "X_API_KEY" not in proof_readiness
    assert "X_API_KEY_FILE" not in proof_readiness
    assert "SUBSTACK_API_TOKEN" not in proof_readiness
    assert "SUBSTACK_API_TOKEN_FILE" not in proof_readiness
    assert "channel policy acknowledgement" in proof_readiness
    assert "durable platform ID or URL" in proof_readiness
    assert "rollback, delete, private, or correction path" in proof_readiness
    assert "Agent Studio Feedback Loop Map" in feedback_loop_map
    assert "Planning memory only" in feedback_loop_map
    assert "guardrails-feedback-resolution" in feedback_loop_map
    assert "feedback_resolution_ledger" in feedback_loop_map
    assert "accepted/revised/held/rejected" in feedback_loop_map
    assert "held_feedback_count" in feedback_loop_map
    assert "failed linked task ids" in feedback_loop_map
    assert "publish-readiness-feedback-gate" in feedback_loop_map
    assert "publish_readiness_checked" in feedback_loop_map
    assert "unsupported_claims" in feedback_loop_map
    assert "blocked_guardrail_audit" in feedback_loop_map
    assert "publish_channel_checks" in feedback_loop_map
    assert "missing accepted evidence" in feedback_loop_map
    assert "external publication proof remains blocked" in feedback_loop_map
    assert "source-quality-feedback-loop" in feedback_loop_map
    assert "revision-loop-closure" in feedback_loop_map
    assert "post-run-planning-feedback" in feedback_loop_map
    assert "leibniz-review-watch-escalation" in feedback_loop_map
    assert "standing reviewer 019e3899-5ab3-7171-9d3c-32e7c57bbde7" in feedback_loop_map
    assert "severity, files, and next action" in feedback_loop_map
    assert (
        "feedback-loop map now includes the Leibniz review-watch escalation loop"
        in active_context
    )
    assert "Agent Studio Publication Boundary Map" in publication_boundary
    assert "Planning memory only" in publication_boundary
    assert "artifact-and-claim-readiness-gates" in publication_boundary
    assert "non-live-channel-smoke" in publication_boundary
    assert "publish_channel_checks" in publication_boundary
    assert "missing_publish_channel_credentials" in publication_boundary
    assert "publish_channel_policy_review_required" in publication_boundary
    assert "not real API publish proof" in publication_boundary
    assert "credential-scope-and-account-identity" in publication_boundary
    assert "INSTAGRAM_ACCESS_TOKEN" not in publication_boundary
    assert "INSTAGRAM_ACCESS_TOKEN_FILE" not in publication_boundary
    assert "LINKEDIN_ACCESS_TOKEN" in publication_boundary
    assert "LINKEDIN_ACCESS_TOKEN_FILE" in publication_boundary
    assert "X_ACCESS_TOKEN" not in publication_boundary
    assert "X_ACCESS_TOKEN_FILE" not in publication_boundary
    assert "X_API_KEY" not in publication_boundary
    assert "X_API_KEY_FILE" not in publication_boundary
    assert "SUBSTACK_API_TOKEN" not in publication_boundary
    assert "SUBSTACK_API_TOKEN_FILE" not in publication_boundary
    assert "channel-policy-review" in publication_boundary
    assert "exact destination set" in publication_boundary
    assert "external-publication-proof" in publication_boundary
    assert "durable platform ID or URL" in publication_boundary
    assert "API response proof or manual-completion proof" in publication_boundary
    assert "postcondition monitoring" in publication_boundary
    assert "live or approved manual destination evidence" in publication_boundary
    assert "rollback proof" in publication_boundary
    assert "external publication proof remains blocked" in publication_boundary
    assert "rollback-and-correction-path" in publication_boundary
    assert "publish_rollback_record" in publication_boundary
    assert "OpenRouter LiveKit Voice Boundary Map" in gemma_voice_boundary
    assert "Planning memory only" in gemma_voice_boundary
    assert "openrouter-deepseek-reasoning" in gemma_voice_boundary
    assert "OpenRouter DeepSeek Reasoning" in gemma_voice_boundary
    assert "https://router.huggingface.co/v1/chat/completions" in gemma_voice_boundary
    assert "google/gemma-4-31b-it" in gemma_voice_boundary
    assert "not native-audio proof" in gemma_voice_boundary
    assert "google/gemma-4-E4B-it" in gemma_voice_boundary
    assert "Legacy Gemma audio understanding" in gemma_voice_boundary
    assert "not the current default proof path" in gemma_voice_boundary
    assert "hexgrad/Kokoro-82M" in gemma_voice_boundary
    assert "Kokoro owns speech synthesis" in gemma_voice_boundary
    assert "livekit-transport-presence" in gemma_voice_boundary
    assert "rust-edge-and-timing-ledgers" in gemma_voice_boundary
    assert "provider-backed-live-voice-proof" in gemma_voice_boundary
    assert "OPENROUTER_LIVEKIT_URL" in gemma_voice_boundary
    assert "LIVEKIT_API_SECRET_FILE" in gemma_voice_boundary
    assert "realtime_voice_timing_ledger" in gemma_voice_boundary
    assert "provider-smoke ledger with live calls enabled" in gemma_voice_boundary
    assert "Retrieval Quality Research" in research
    assert "Research Areas" in research
    assert 'data-filter="graph"' in research
    assert 'id="research-count"' in research
    assert "Reciprocal Rank Fusion" in research
    assert "CrossEncoder" in research
    assert "GraphRAG" in research
    assert "Agent Studio System Design Vault" in system_design_home
    assert "Planning memory only" in system_design_home
    assert "04-agent-studio-implications/agent-studio-objective-completion-audit.md" in system_design_home
    assert "01-sources/official-open/gemma4-and-realtime-sources.md" in system_design_home
    assert "01-sources/official-open/social-publishing-api-governance.md" in system_design_home
    assert "03-patterns/system-design/production-agent-studio-canon.md" in system_design_home
    assert "00-index/source-map.md" in system_design_home
    assert "System Design Source Map Viewer" in system_design_home
    assert "output/viewers/system-design-source-map.html" in system_design_home
    assert "generated source-map viewer" in system_design_home
    assert "output/viewers/system-design-source-map.html" in system_design_moc
    assert "[System Design Source Map Viewer](output/viewers/system-design-source-map.html)" in system_design_moc
    assert "Agent Studio Source Map" in system_design_source_map_viewer
    assert "Search source records" in system_design_source_map_viewer
    assert "Filter by source kind" in system_design_source_map_viewer
    assert "Filter by local book coverage granularity" in system_design_source_map_viewer
    assert "renderRecords" in system_design_source_map_viewer
    assert "Design Implications" in system_design_source_map_viewer
    assert "Search design implications" in system_design_source_map_viewer
    assert "implication-count" in system_design_source_map_viewer
    assert "renderImplications" in system_design_source_map_viewer
    assert "coverageGranularity" in system_design_source_map_viewer
    assert "provider-backed live voice path is OpenRouter + LiveKit + Kokoro" in system_design_home
    assert "External publication proof remains blocked" in system_design_home


def test_current_vault_knowledge_graph_does_not_reopen_accepted_live_voice_gate():
    project_kg = (
        ROOT / "system_design_vault/06-project-knowledge-graph/agent-studio-project-kg.md"
    ).read_text()
    architecture_map = (
        ROOT / "system_design_vault/06-project-knowledge-graph/agent-studio-architecture-map.html"
    ).read_text()
    objective_audit = (
        ROOT
        / "social_media_optimiser/01-work-tracking/Agent Studio Objective Completion Audit.md"
    ).read_text()
    current_surfaces = "\n".join([project_kg, architecture_map, objective_audit])

    assert "Provider-backed live voice | accepted" in project_kg
    assert "accepted live proof" in project_kg
    assert "Provider-backed live voice is accepted" in objective_audit
    assert "needs accepted proof record" not in current_surfaces
    assert "needs accepted record capture/recheck" not in current_surfaces
    assert "LiveKit proof pending" not in current_surfaces
    assert "voice blocked on provider creds" not in current_surfaces
    assert "live voice is waiting on accepted OpenRouter LiveKit proof-record" not in (
        objective_audit
    )


def test_system_design_viewer_projection_is_refreshed_from_latest_lld():
    viewer_json_path = (
        ROOT / "social_media_optimiser/output/viewers/agent-studio-system-design.json"
    )
    viewer_html_path = (
        ROOT
        / "social_media_optimiser/output/viewers/agent-studio-system-design-viewer.html"
    )
    projection = json.loads(viewer_json_path.read_text())
    html = viewer_html_path.read_text()
    embedded_json = html.split('<script id="system-design-data" type="application/json">', 1)[
        1
    ].split("</script>", 1)[0]
    embedded_projection = json.loads(embedded_json)

    serialized_projection = json.dumps(projection)
    assert projection["updated"] == "2026-05-20"
    assert (
        "01-work-tracking/Agent Studio Objective Completion Audit.md"
        in projection["canonical_sources"]
    )
    assert embedded_projection["updated"] == projection["updated"]
    assert embedded_projection == projection
    assert "Background runner" in serialized_projection
    assert "Always-on studio" in serialized_projection
    assert "Specialist pulse" in serialized_projection
    assert "Objective Completion Audit" in serialized_projection
    assert "provider-backed live voice proof" in serialized_projection
    assert "external publication proof" in serialized_projection
    assert "proof_plan" in serialized_projection
    assert "provider-proof-plan" in serialized_projection
    assert "current-proof-status.md" in serialized_projection
    assert "current-blocker-matrix.json" in serialized_projection
    assert "operator-unblocker-checklist.md" in serialized_projection
    assert "Do not call the goal complete" in serialized_projection
    assert "creator Activity rail can show `Local scheduler` status" not in serialized_projection
    assert "Background runner" in embedded_json
    assert "Local scheduler" not in embedded_json


def test_system_design_source_map_viewer_embeds_current_json_projection():
    viewer_json_path = (
        ROOT / "system_design_vault/output/viewers/system-design-source-map.json"
    )
    viewer_html_path = (
        ROOT / "system_design_vault/output/viewers/system-design-source-map.html"
    )
    projection = json.loads(viewer_json_path.read_text())
    html = viewer_html_path.read_text()
    embedded_json = html.split('<script type="application/json" id="source-data">', 1)[
        1
    ].split("</script>", 1)[0]
    embedded_projection = json.loads(embedded_json)

    assert embedded_projection == projection
    assert projection["updated"] == "2026-05-19"
    assert len(projection["sourceGroups"]) == 11
    assert len(projection["records"]) == 175
    assert len(projection["designImplications"]) == 126


def test_memory_os_viewer_embeds_current_standalone_projection():
    viewer_json_path = (
        ROOT / "social_media_optimiser/output/viewers/agent-studio-memory-os.json"
    )
    viewer_html_path = (
        ROOT
        / "social_media_optimiser/output/viewers/agent-studio-memory-os-viewer.html"
    )
    projection = json.loads(viewer_json_path.read_text())
    html = viewer_html_path.read_text()
    embedded_json = html.split('<script id="memory-data" type="application/json">', 1)[
        1
    ].split("</script>", 1)[0]
    embedded_projection = json.loads(embedded_json)

    assert embedded_projection == projection
    assert "provider_free_realtime_rehearsal" in embedded_json
    assert "linked_notes" in embedded_json


def test_project_agent_skills_are_valid_and_todo_free():
    skill_root = ROOT / "skills"
    skills = sorted(path for path in skill_root.iterdir() if path.is_dir())
    assert [path.name for path in skills] == [
        "agent-studio-ci-scaffold",
        "agent-studio-content-production",
        "agent-studio-conversation-harness",
        "agent-studio-frontend-engineering",
        "agent-studio-guardrails-review",
        "agent-studio-inference-reliability",
        "agent-studio-local-bootstrap",
        "agent-studio-media-design",
        "agent-studio-provider-proof-capture",
        "agent-studio-research-grounding",
        "agent-studio-retrieval-intelligence",
        "agent-studio-ship-gate",
        "agent-studio-system-architecture",
    ]
    for skill in skills:
        body = (skill / "SKILL.md").read_text()
        assert body.startswith("---\nname: ")
        assert "description: " in body
        assert "TODO" not in body
        assert (skill / "agents/openai.yaml").exists()

    guardrails_skill = (
        skill_root / "agent-studio-guardrails-review/SKILL.md"
    ).read_text()
    assert "feedback_resolution_ledger" in guardrails_skill
    assert "accepted`, `revised`, `held`, or `rejected" in guardrails_skill
    assert "failed or canceled linked tasks" in guardrails_skill
    assert "must stay held" in guardrails_skill
