import os
from datetime import datetime, timezone

import pytest

from all_about_llms.config import get_settings
from all_about_llms.contracts import (
    AgentMessage,
    AgentMemory,
    AgentTaskStatus,
    AgentWorkerCycleRequest,
    AgentWorkerRunRequest,
    ArtifactRecord,
    ArtifactType,
    AutonomousStudioPassRequest,
    ClaimRecord,
    ClaimSupportStatus,
    ConversationRouteRequest,
    ConversationRouteIntent,
    ConversationTurn,
    FeedbackItem,
    FeedbackStatus,
    GuardrailAuditRequest,
    InteractiveRunNoteRequest,
    OrchestrationRequest,
    PublishReadinessRequest,
    RealtimeSessionRecord,
    RealtimeSessionStatus,
    MediaProductionRequest,
    MultimodalIntakeRequest,
    RevisionRequest,
    RunReplayLedgerRequest,
    RunResumePlanRequest,
    RunResumeRequest,
    RunEvent,
    RunState,
    RunStatus,
    RunSyncPulseRequest,
    RunWorkPlanRequest,
    SourceLedgerSnapshotRequest,
    SourceRecord,
    WorkerProfile,
    WorkerProfileStatus,
    WorkerSchedulerRunRequest,
)
from all_about_llms.orchestration import (
    AgentWorker,
    AutonomousStudioPassWorkflow,
    ConversationRouter,
    ContentStudioWorkflow,
    FeedbackRoutingWorkflow,
    GuardrailAuditWorkflow,
    InteractiveRunNoteWorkflow,
    MediaProductionWorkflow,
    MultimodalIntakeWorkflow,
    PublishReadinessWorkflow,
    RevisionWorkflow,
    RunReplayLedgerWorkflow,
    RunResumeWorkflow,
    RunSyncPulseWorkflow,
    RunWorkPlanWorkflow,
    SourceLedgerWorkflow,
)
from all_about_llms.orchestration.services import ContentWorkflowServices
from all_about_llms.providers.interfaces import SearchResult
from all_about_llms.storage import PostgresStore
from all_about_llms.storage.migrations import setup_durable_storage


pytestmark = pytest.mark.skipif(
    os.getenv("LIVE_POSTGRES") != "1",
    reason="Set LIVE_POSTGRES=1 to run against local Postgres/pgvector.",
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


class LiveFakeSearchProvider:
    async def search(self, request):
        return [
            SearchResult(
                title="Live source repair provider source",
                url="https://huggingface.co/docs/inference-providers/tasks/chat-completion",
                snippet="Provider-backed search result for source repair.",
                publisher="Hugging Face",
                published_at=datetime.now(timezone.utc).isoformat(),
                retrieved_at=datetime.now(timezone.utc).isoformat(),
            )
        ]


@pytest.mark.anyio
async def test_live_postgres_run_lifecycle():
    settings = get_settings()
    await setup_durable_storage(settings)
    store = await PostgresStore.from_settings(settings)
    try:
        run = await store.create_run(
            RunState(
                goal="Live DB smoke test for source-backed content generation",
                active_agents=["realtime-conversation-host", "intent-router"],
            )
        )
        await store.append_event(
            RunEvent(
                run_id=run.run_id,
                event_type="run_created",
                actor="realtime-conversation-host",
            )
        )
        message = await store.record_agent_message(
            AgentMessage(
                run_id=run.run_id,
                sender_agent_id="intent-router",
                recipient_agent_id="web-research-agent",
                task_type="research_topic",
                payload={"topic": "realtime audio"},
            )
        )
        source = await store.record_source(
            SourceRecord(
                run_id=run.run_id,
                citation_id="S1",
                title="OpenAI Realtime API",
                url="https://platform.openai.com/docs/guides/realtime/",
                publisher="OpenAI",
            )
        )
        await store.record_claim(
            ClaimRecord(
                run_id=run.run_id,
                claim_text="Realtime audio providers handle voice interaction.",
                support_status=ClaimSupportStatus.SUPPORTED,
                source_ids=[source.source_id],
                reviewer_agent_id="claim-verification-agent",
            )
        )
        await store.record_artifact(
            ArtifactRecord(
                run_id=run.run_id,
                artifact_type=ArtifactType.REEL_SCRIPT,
                title="Realtime studio smoke artifact",
                uri="artifacts/live-smoke/reel.json",
                source_ids=[source.source_id],
                provenance={"test": "live_postgres"},
            )
        )
        feedback = await store.record_feedback(
            FeedbackItem(
                run_id=run.run_id,
                feedback_text="Keep the interaction natural and iterative.",
            )
        )
        updated_feedback = await store.update_feedback_status(
            feedback_id=feedback.feedback_id,
            status=FeedbackStatus.RESOLVED,
            resolver="live-test",
            resolution_notes="Verified feedback resolution persists.",
        )
        assert updated_feedback is not None
        assert updated_feedback.status == FeedbackStatus.RESOLVED
        assert updated_feedback.resolved_by == "live-test"
        await store.record_memory(
            AgentMemory(
                agent_id="context-engineering-agent",
                run_id=run.run_id,
                memory_kind="test_memory",
                content="Live pgvector memory write works.",
                embedding=[0.1, 0.2, 0.3],
            )
        )
        realtime_session = await store.record_realtime_session(
            RealtimeSessionRecord(
                run_id=run.run_id,
                provider="openai_realtime",
                provider_session_id="live-realtime-session",
                voice="marin",
                audio_mode="speech_to_speech",
                instructions="Keep the live test conversation natural.",
                has_client_secret=True,
                has_websocket_url=False,
                metadata={"model": "test-realtime"},
            )
        )

        persisted_run = await store.get_run(run.run_id)
        assert persisted_run is not None
        messages = await store.list_agent_messages(run.run_id)
        assert len(messages) == 1
        assert messages[0].message_id == message.message_id
        inbox = await store.list_agent_messages(
            run.run_id,
            agent_id="web-research-agent",
            direction="inbox",
            status=AgentTaskStatus.ACCEPTED,
        )
        assert len(inbox) == 1
        updated_message = await store.update_agent_message_status(
            message_id=message.message_id,
            status=AgentTaskStatus.COMPLETED,
            agent_id="web-research-agent",
            result={"sources_found": 1},
        )
        assert updated_message is not None
        assert updated_message.status == AgentTaskStatus.COMPLETED
        assert updated_message.claimed_by_agent_id == "web-research-agent"
        assert updated_message.result == {"sources_found": 1}
        assert len(persisted_run.source_record_ids) == 1
        assert len(persisted_run.artifact_ids) == 1
        assert len(persisted_run.feedback_item_ids) == 1
        assert len(await store.list_sources(run.run_id)) == 1
        assert len(await store.list_claims(run.run_id)) == 1
        assert len(await store.list_artifacts(run.run_id)) == 1
        assert len(await store.list_events(run.run_id)) == 1
        assert len(await store.list_feedback(run.run_id)) == 1
        assert len(await store.list_feedback(run.run_id, status=FeedbackStatus.OPEN)) == 0
        memories = await store.list_memories(run_id=run.run_id)
        assert len(memories) == 1
        assert memories[0].embedding == [0.1, 0.2, 0.3]
        realtime_sessions = await store.list_realtime_sessions(run.run_id)
        assert len(realtime_sessions) == 1
        assert realtime_sessions[0].provider_session_id == "live-realtime-session"
        ended_session = await store.update_realtime_session_status(
            realtime_session.realtime_session_id,
            RealtimeSessionStatus.ENDED,
        )
        assert ended_session is not None
        assert ended_session.status == RealtimeSessionStatus.ENDED
        search_results = await store.search_memories(
            agent_id="context-engineering-agent",
            run_id=run.run_id,
            query_embedding=[0.1, 0.2, 0.3],
        )
        assert len(search_results) == 1
        assert search_results[0][1] == 0.0

        first_event = (await store.list_events(run.run_id, limit=1))[0]
        for index in range(125):
            await store.append_event(
                RunEvent(
                    run_id=run.run_id,
                    event_type="cursor_probe",
                    actor="observability-agent",
                    payload={"index": index},
                )
            )
        cursor_events = await store.list_events(
            run.run_id,
            after_event_id=first_event.event_id + 100,
            limit=5,
        )
        assert len(cursor_events) == 5
        assert cursor_events[0].payload["index"] == 100
        assert cursor_events[-1].payload["index"] == 104

        idempotent_event_key = f"live-run-lifecycle:{run.run_id}:proof"
        first_idempotent_event = await store.append_event_if_absent(
            RunEvent(
                run_id=run.run_id,
                event_type="live_idempotent_event",
                actor="live-test",
                payload={"feedback_id": str(feedback.feedback_id)},
            ),
            idempotency_key=idempotent_event_key,
        )
        replayed_idempotent_event = await store.append_event_if_absent(
            RunEvent(
                run_id=run.run_id,
                event_type="live_idempotent_event",
                actor="live-test",
                payload={"feedback_id": str(feedback.feedback_id)},
            ),
            idempotency_key=idempotent_event_key,
        )
        assert first_idempotent_event is not None
        assert replayed_idempotent_event is not None
        assert replayed_idempotent_event.event_id == first_idempotent_event.event_id
        idempotent_events = await store.list_events_by_type(
            run.run_id,
            "live_idempotent_event",
        )
        assert len(idempotent_events) == 1
        assert idempotent_events[0].payload["event_idempotency_key"] == (
            idempotent_event_key
        )
    finally:
        await store.close()


@pytest.mark.anyio
async def test_live_postgres_promotes_pending_voice_transcript():
    settings = get_settings()
    await setup_durable_storage(settings)
    store = await PostgresStore.from_settings(settings)
    try:
        run = await store.create_run(
            RunState(
                goal="Live DB voice transcript promotion smoke",
                active_agents=["realtime-conversation-host"],
            )
        )
        voice_turn_id = "live-voice-turn-transcript-promotion"
        pending = ConversationTurn(
            run_id=run.run_id,
            speaker="user",
            modality="voice",
            transcript="Live audio turn committed; transcript pending.",
            metadata={
                "voice_agent_event_type": "voice_user_turn_committed",
                "voice_agent_turn_id": voice_turn_id,
                "transcript_status": "pending",
            },
        )
        recorded = await store.record_voice_agent_conversation_turn_if_absent(
            pending,
            voice_turn_id=voice_turn_id,
        )
        assert recorded is not None

        final_turn = ConversationTurn(
            turn_id=recorded.turn_id,
            run_id=run.run_id,
            speaker="user",
            modality="voice",
            transcript="Create a source-backed LinkedIn post from this spoken idea.",
            metadata={
                "voice_agent_event_type": "voice_user_turn_committed",
                "voice_agent_turn_id": voice_turn_id,
                "voice_agent_event_id": 42,
                "transcript_status": "final",
                "audio_duration_ms": 500,
            },
        )
        updated = await store.promote_voice_user_transcript_if_pending(
            final_turn,
            voice_turn_id=voice_turn_id,
        )
        assert updated is not None
        duplicate = await store.promote_voice_user_transcript_if_pending(
            final_turn,
            voice_turn_id=voice_turn_id,
        )
        assert duplicate is None

        fetched = await store.find_voice_agent_conversation_turn(
            run.run_id,
            speaker="user",
            voice_turn_id=voice_turn_id,
        )
        assert fetched is not None
        assert fetched.transcript == (
            "Create a source-backed LinkedIn post from this spoken idea."
        )
        assert fetched.metadata["transcript_status"] == "final"
        assert fetched.metadata["transcript_promoted_from_pending"] is True
        assert fetched.metadata["transcript_promoted_event_id"] == 42
    finally:
        await store.close()


@pytest.mark.anyio
async def test_live_postgres_feedback_routing_records_task_and_memories():
    settings = get_settings()
    await setup_durable_storage(settings)
    store = await PostgresStore.from_settings(settings)
    try:
        run = await store.create_run(
            RunState(goal="Live feedback routing smoke", status=RunStatus.RUNNING)
        )
        result = await FeedbackRoutingWorkflow(store).run(
            FeedbackItem(
                run_id=run.run_id,
                author="live-test-user",
                feedback_text=(
                    "Improve the source citations and verify the claim before "
                    "the next draft."
                ),
                metadata={"focus": "claim", "priority": "high"},
            )
        )

        assert result.feedback.status == FeedbackStatus.ROUTED
        assert result.routed_agent_id == "claim-verification-agent"
        routed_feedback = await store.list_feedback(
            run.run_id,
            status=FeedbackStatus.ROUTED,
        )
        assert len(routed_feedback) == 1

        inbox = await store.list_agent_messages(
            run.run_id,
            agent_id="claim-verification-agent",
            direction="inbox",
            status=AgentTaskStatus.ACCEPTED,
        )
        assert len(inbox) == 1
        assert inbox[0].message_id == result.task_message_id
        assert inbox[0].payload["feedback_id"] == str(result.feedback.feedback_id)
        assert len(result.support_task_message_ids) == 2
        note_inbox = await store.list_agent_messages(
            run.run_id,
            agent_id="interactive-note-taking-agent",
            direction="inbox",
            status=AgentTaskStatus.ACCEPTED,
        )
        sprint_inbox = await store.list_agent_messages(
            run.run_id,
            agent_id="sprint-progress-agent",
            direction="inbox",
            status=AgentTaskStatus.ACCEPTED,
        )
        assert len(note_inbox) == 1
        assert len(sprint_inbox) == 1
        assert {
            note_inbox[0].message_id,
            sprint_inbox[0].message_id,
        } == set(result.support_task_message_ids)

        memories = await store.list_memories(run_id=run.run_id)
        assert {
            memory.agent_id for memory in memories
        } == {
            "claim-verification-agent",
            "interactive-note-taking-agent",
            "sprint-progress-agent",
        }
        assert {memory.memory_id for memory in memories} == set(result.memory_ids)

        event_types = [event.event_type for event in await store.list_events(run.run_id)]
        assert event_types == [
            "feedback_recorded",
            "agent_message_accepted",
            "agent_message_accepted",
            "agent_message_accepted",
            "memory_recorded",
            "memory_recorded",
            "memory_recorded",
            "feedback_routed",
        ]

        work_plan = await RunWorkPlanWorkflow(store).build(
            run.run_id,
            RunWorkPlanRequest(record_artifact=True),
        )
        assert work_plan.pending_task_count == 3
        assert work_plan.routed_feedback_count == 1
        assert work_plan.artifact_id is not None
        assert "claim-verification-agent" in work_plan.recommended_agent_ids
        assert "interactive-note-taking-agent" in work_plan.recommended_agent_ids
        assert "sprint-progress-agent" in work_plan.recommended_agent_ids
        assert any(
            item.item_type == "feedback_task"
            and item.owner_agent_id == "claim-verification-agent"
            for item in work_plan.plan_items
        )
        artifacts = await store.list_artifacts(run.run_id)
        assert artifacts[-1].artifact_type == ArtifactType.SYSTEM_PLAN
        assert artifacts[-1].content["pending_task_count"] == 3
        assert (
            [event.event_type for event in await store.list_events(run.run_id)][-1]
            == "run_work_plan_built"
        )

        sync_pulse = await RunSyncPulseWorkflow(store).build(
            run.run_id,
            RunSyncPulseRequest(record_artifact=True, build_work_plan=True),
        )
        assert sync_pulse.artifact_id is not None
        assert sync_pulse.work_plan is not None
        assert sync_pulse.work_plan.pending_task_count == 3
        assert "claim-verification-agent" in sync_pulse.recommended_agent_ids
        claim_state = next(
            state
            for state in sync_pulse.agent_states
            if state.agent_id == "claim-verification-agent"
        )
        assert claim_state.pending_message_ids
        assert claim_state.routed_feedback_ids
        artifacts = await store.list_artifacts(run.run_id)
        assert artifacts[-1].provenance["workflow"] == "run_sync_pulse_v1"
        assert (
            [event.event_type for event in await store.list_events(run.run_id)][-1]
            == "multi_agent_sync_pulse_recorded"
        )
    finally:
        await store.close()


@pytest.mark.anyio
async def test_live_postgres_multimodal_intake_ledger():
    settings = get_settings()
    await setup_durable_storage(settings)
    store = await PostgresStore.from_settings(settings)
    try:
        run = await store.create_run(
            RunState(goal="Multimodal intake live smoke", status=RunStatus.RUNNING)
        )
        result = await MultimodalIntakeWorkflow(store).record(
            run.run_id,
            MultimodalIntakeRequest(
                assets=[
                    {
                        "asset_uri": "artifact://uploads/reference-screen.png",
                        "modality": "screenshot",
                        "description": "Reference cockpit screen",
                    },
                    {
                        "asset_uri": "artifact://uploads/user-voice.wav",
                        "modality": "voice",
                        "description": "User voice note",
                    },
                ],
                record_artifact=True,
                create_agent_tasks=True,
            ),
        )

        assert result.asset_count == 2
        assert result.modality_counts == {"screenshot": 1, "voice": 1}
        assert result.intake_artifact_id is not None
        assert {
            "lead-ui-ux-designer",
            "visual-director",
            "audio-producer",
            "realtime-conversation-host",
        } <= set(result.recommended_agent_ids)
        messages = await store.list_agent_messages(run.run_id)
        assert len(messages) == 4
        assert {message.task_type for message in messages} == {
            "review_multimodal_intake"
        }
        worker_result = await AgentWorker(store).run(
            "lead-ui-ux-designer",
            AgentWorkerRunRequest(
                run_id=run.run_id,
                max_tasks=1,
                use_gemma=False,
            ),
        )
        assert worker_result.processed_tasks[0].generation_mode == (
            "multimodal_intake_review_worker"
        )
        cycle_result = await AgentWorker(store).run_cycle(
            AgentWorkerCycleRequest(
                run_id=run.run_id,
                agent_ids=[
                    "visual-director",
                    "image-generation-agent",
                    "product-manager",
                    "context-engineering-agent",
                ],
                max_tasks_per_agent=5,
                max_rounds=1,
                use_gemma=False,
            )
        )
        assert cycle_result.total_processed_tasks == 5
        artifacts = await store.list_artifacts(run.run_id)
        intake_artifact = next(
            artifact
            for artifact in artifacts
            if artifact.artifact_type == ArtifactType.MULTIMODAL_INTAKE_LEDGER
        )
        assert intake_artifact.provenance["workflow"] == "multimodal_intake_v1"
        review_artifacts = [
            artifact
            for artifact in artifacts
            if artifact.artifact_type == ArtifactType.MULTIMODAL_REVIEW
        ]
        assert {artifact.provenance["agent_id"] for artifact in review_artifacts} == {
            "lead-ui-ux-designer",
            "visual-director",
        }
        assert all(
            artifact.provenance["workflow"] == "multimodal_intake_review_worker_v1"
            for artifact in review_artifacts
        )
        assert all(artifact.content["followup_plan"] for artifact in review_artifacts)
        visual_review = next(
            artifact
            for artifact in review_artifacts
            if artifact.provenance["agent_id"] == "visual-director"
        )
        followup_messages = [
            message
            for message in await store.list_agent_messages(run.run_id)
            if message.payload.get("workflow") == "multimodal_review_followup_v1"
        ]
        assert {
            message.recipient_agent_id for message in followup_messages
        } >= {
            "context-engineering-agent",
            "product-manager",
            "image-generation-agent",
        }
        image_prompt_pack = next(
            artifact
            for artifact in artifacts
            if artifact.artifact_type == ArtifactType.IMAGE
            and artifact.provenance.get("workflow") == "image_generation_worker_v1"
        )
        assert image_prompt_pack.provenance["source_artifact_ids"] == [
            str(visual_review.artifact_id)
        ]
        context_packets = [
            artifact
            for artifact in artifacts
            if artifact.artifact_type == ArtifactType.CONTEXT_PACKET
        ]
        assert {
            packet.content["source_multimodal_review_artifact_id"]
            for packet in context_packets
        } == {str(artifact.artifact_id) for artifact in review_artifacts}
        assert any(
            artifact.provenance.get("workflow") == "run_sync_pulse_v1"
            for artifact in artifacts
        )
        event_types = [event.event_type for event in await store.list_events(run.run_id)]
        assert event_types.count("agent_message_accepted") == 8
        assert "artifact_recorded" in event_types
        assert "multimodal_intake_recorded" in event_types
        assert "multimodal_intake_review_recorded" in event_types
        assert "multimodal_review_followups_materialized" in event_types
        assert "image_generation_prompt_pack_created" in event_types
        assert "context_packet_artifact_created" in event_types
        assert "multi_agent_sync_pulse_recorded" in event_types
    finally:
        await store.close()


@pytest.mark.anyio
async def test_live_postgres_resume_plan_records_run_checkpoint():
    settings = get_settings()
    await setup_durable_storage(settings)
    store = await PostgresStore.from_settings(settings)
    try:
        run = await store.create_run(
            RunState(goal="Live resume plan checkpoint smoke", status=RunStatus.RUNNING)
        )
        await store.append_event(
            RunEvent(
                run_id=run.run_id,
                event_type="run_created",
                actor="realtime-conversation-host",
            )
        )
        await store.record_agent_message(
            AgentMessage(
                run_id=run.run_id,
                sender_agent_id="intent-router",
                recipient_agent_id="web-research-agent",
                task_type="research_resume_state",
                payload={"topic": "resumable agents"},
            )
        )
        feedback = await store.record_feedback(
            FeedbackItem(
                run_id=run.run_id,
                feedback_text="Approve before autonomous resume.",
            )
        )
        await store.record_worker_profile(
            WorkerProfile(
                run_id=run.run_id,
                name="Resume profile",
                agent_ids=["web-research-agent"],
                status=WorkerProfileStatus.ACTIVE,
            )
        )
        await store.record_memory(
            AgentMemory(
                agent_id="web-research-agent",
                run_id=run.run_id,
                memory_kind="resume_hint",
                content="Resume research first.",
            )
        )

        plan = await RunResumeWorkflow(store).build_resume_plan(
            run.run_id,
            RunResumePlanRequest(agent_id="web-research-agent"),
        )
        assert plan.resume_allowed is False
        assert plan.blocked_reasons == ["open_human_feedback"]
        assert plan.checkpoint is not None
        assert plan.context_summary["pending_agent_messages"] == 1
        assert plan.context_summary["open_feedback_items"] == 1
        assert plan.context_summary["active_worker_profiles"] == 1
        assert plan.context_summary["memories"] == 1
        checkpoints = await store.list_run_checkpoints(run.run_id)
        assert len(checkpoints) == 1
        assert checkpoints[0].checkpoint_id == plan.checkpoint.checkpoint_id
        event_types = [event.event_type for event in await store.list_events(run.run_id)]
        run_events = await store.list_events(run.run_id)
        assert plan.checkpoint.event_cursor == run_events[0].event_id
        assert event_types[-2:] == ["run_checkpoint_recorded", "resume_plan_built"]

        replay = await RunReplayLedgerWorkflow(store).build(
            run.run_id,
            RunReplayLedgerRequest(
                checkpoint_id=plan.checkpoint.checkpoint_id,
                include_event_payloads=False,
            ),
        )
        assert replay.checkpoint_id == plan.checkpoint.checkpoint_id
        assert replay.replay_after_event_id == plan.checkpoint.event_cursor
        assert replay.replay_event_count == 2
        assert replay.event_type_counts["run_checkpoint_recorded"] == 1
        assert replay.event_type_counts["resume_plan_built"] == 1
        assert replay.replay_artifact_id is not None

        blocked_resume = await RunResumeWorkflow(store).resume_run(
            run.run_id,
            RunResumeRequest(
                agent_id="web-research-agent",
                agent_ids=["web-research-agent"],
                build_work_plan=False,
                heartbeat_active_profiles=False,
                use_gemma=False,
            ),
        )
        assert blocked_resume.resumed is False
        assert blocked_resume.status_after == RunStatus.RUNNING
        assert blocked_resume.resume_plan.blocked_reasons == ["open_human_feedback"]

        await store.update_feedback_status(
            feedback_id=feedback.feedback_id,
            status=FeedbackStatus.RESOLVED,
            resolver="user",
            resolution_notes="Approved resume smoke task.",
        )
        allowed_resume = await RunResumeWorkflow(store).resume_run(
            run.run_id,
            RunResumeRequest(
                agent_id="web-research-agent",
                agent_ids=["web-research-agent"],
                build_work_plan=False,
                heartbeat_active_profiles=False,
                use_gemma=False,
            ),
        )
        assert allowed_resume.resumed is True
        assert allowed_resume.worker_cycle is not None
        assert allowed_resume.worker_cycle.total_processed_tasks == 1
        assert allowed_resume.status_after == RunStatus.RUNNING
        resumed_messages = await store.list_agent_messages(
            run.run_id,
            agent_id="web-research-agent",
            direction="inbox",
            status=AgentTaskStatus.COMPLETED,
        )
        assert len(resumed_messages) == 1
        event_types = [event.event_type for event in await store.list_events(run.run_id)]
        assert "run_resume_blocked" in event_types
        assert event_types[-1] == "run_resume_completed"
    finally:
        await store.close()


@pytest.mark.anyio
async def test_live_postgres_content_studio_orchestration():
    settings = get_settings()
    await setup_durable_storage(settings)
    store = await PostgresStore.from_settings(settings)
    try:
        workflow = ContentStudioWorkflow(store)
        result = await workflow.run(
            OrchestrationRequest(
                transcript=(
                    "Create a source-backed ELI5 social post, reel, and "
                    "Substack about realtime Gemma 4 agents."
                ),
                modality="voice",
                target_formats=["post", "reel", "substack"],
                require_human_feedback=False,
            )
        )

        run = await store.get_run(result.run_id)
        assert run is not None
        assert run.status.value == "completed"
        assert len(result.task_message_ids) == 4
        assert len(await store.list_agent_messages(result.run_id)) == 4
        assert len(
            await store.list_agent_messages(
                result.run_id,
                agent_id="intent-router",
                direction="outbox",
            )
        ) == 3
        assert len(await store.list_sources(result.run_id)) == 2
        assert len(await store.list_claims(result.run_id)) == 2
        artifacts = await store.list_artifacts(result.run_id)
        assert len(artifacts) == 3
        assert artifacts[0].content["generation_mode"] == "deterministic_fallback"
        assert [artifact.artifact_type.value for artifact in artifacts] == [
            "post",
            "reel_script",
            "substack_article",
        ]
        assert len(await store.list_conversation_turns(result.run_id)) == 1
        media_result = await MediaProductionWorkflow(store).run(
            result.run_id,
            MediaProductionRequest(),
        )
        assert len(media_result.media_artifact_ids) == 3
        media_artifacts = await store.list_artifacts(result.run_id)
        assert [artifact.artifact_type.value for artifact in media_artifacts[-3:]] == [
            "image",
            "audio",
            "video",
        ]
        assert media_artifacts[-1].provenance["workflow"] == "media_production_v1"

        worker_result = await AgentWorker(store).run(
            "web-research-agent",
            AgentWorkerRunRequest(
                run_id=result.run_id,
                max_tasks=1,
                use_gemma=False,
            ),
        )
        assert worker_result.idle is False
        assert worker_result.processed_tasks[0].status == AgentTaskStatus.COMPLETED
        worker_inbox = await store.list_agent_messages(
            result.run_id,
            agent_id="web-research-agent",
            direction="inbox",
            status=AgentTaskStatus.COMPLETED,
        )
        assert len(worker_inbox) == 1
        assert worker_inbox[0].result["generation_mode"] == (
            "web_search_provider_blocked"
        )
        assert worker_inbox[0].result["web_research"]["blocker"] == (
            "web_search_provider_missing"
        )
        profile = await store.record_worker_profile(
            WorkerProfile(
                run_id=result.run_id,
                name="Live worker profile",
                agent_ids=["claim-verification-agent"],
                status=WorkerProfileStatus.ACTIVE,
                max_rounds=1,
            )
        )
        due_profiles = await store.list_due_worker_profiles(limit=1000)
        assert profile.profile_id in {
            due_profile.profile_id for due_profile in due_profiles
        }
        profile_result = await AgentWorker(store).run_profile_heartbeat(
            profile.profile_id
        )
        assert profile_result.skipped is False
        assert profile_result.cycle_result is not None
        assert profile_result.cycle_result.total_processed_tasks == 1
        reviewed_claims = await store.list_claims(result.run_id)
        assert reviewed_claims[0].support_status == ClaimSupportStatus.NEEDS_REVIEW
        assert reviewed_claims[1].support_status == ClaimSupportStatus.SUPPORTED
        assert profile_result.work_plan is not None
        assert profile_result.work_plan.artifact_id is not None
        assert profile_result.work_plan.created_task_message_ids
        profiles = await store.list_worker_profiles(result.run_id)
        assert len(profiles) == 1
        assert profiles[0].last_heartbeat_at is not None
        scheduler_result = await AgentWorker(store).run_due_profile_scheduler(
            WorkerSchedulerRunRequest(max_profiles=10)
        )
        assert scheduler_result.checked_profiles <= 10
        assert all(
            heartbeat.work_plan is not None
            for heartbeat in scheduler_result.heartbeat_results
        )
        work_plan_created_message_count = len(
            profile_result.work_plan.created_task_message_ids
        )
        work_plan_created_message_count += sum(
            len(heartbeat.work_plan.created_task_message_ids)
            for heartbeat in scheduler_result.heartbeat_results
            if heartbeat.profile.run_id == result.run_id and heartbeat.work_plan is not None
        )

        audit_result = await GuardrailAuditWorkflow(store).run(
            result.run_id,
            GuardrailAuditRequest(open_feedback_gate=True),
        )
        assert audit_result.status.value == "needs_revision"
        assert audit_result.feedback_gate_opened is True
        assert len(audit_result.audits) == 6
        assert len(await store.list_guardrail_audits(result.run_id)) == 6

        event_types = [event.event_type for event in await store.list_events(result.run_id)]
        assert event_types[0] == "orchestration_started"
        assert (
            event_types.count("agent_message_accepted")
            == 8 + work_plan_created_message_count
        )
        assert event_types.count("source_recorded") == 2
        assert event_types.count("claim_recorded") == 2
        assert event_types.count("artifact_recorded") >= 6
        assert "media_production_plan_built" in event_types
        assert event_types.count("guardrail_audit_recorded") == 6

        revision_result = await RevisionWorkflow(store).run(
            result.run_id,
            RevisionRequest(
                feedback_text="Make the opening more concrete and keep the caveat obvious.",
                require_human_feedback=True,
            ),
        )

        assert revision_result.feedback_gate_opened is True
        assert len(revision_result.task_message_ids) == 4
        assert (
            len(await store.list_agent_messages(result.run_id))
            == 12 + work_plan_created_message_count
        )
        assert len(revision_result.revised_artifact_ids) == 6
        assert len(revision_result.review_decisions) == 12
        revised_run = await store.get_run(result.run_id)
        assert revised_run is not None
        assert revised_run.status.value == "waiting_for_human"
        revised_artifacts = await store.list_artifacts(result.run_id)
        assert len(revised_artifacts) >= 13
        assert any(
            artifact.artifact_type == ArtifactType.SYSTEM_PLAN
            and artifact.provenance["workflow"] == "run_work_plan_v1"
            for artifact in revised_artifacts
        )
        assert revised_artifacts[-1].provenance["workflow"] == "feedback_revision_v1"
        assert revised_artifacts[-1].content["revision_feedback"].startswith(
            "Make the opening"
        )

        revised_event_types = [
            event.event_type for event in await store.list_events(result.run_id)
        ]
        assert "revision_loop_started" in revised_event_types
        assert revised_event_types.count("feedback_recorded") == 1
        assert revised_event_types.count("artifact_revised") == 6
        assert revised_event_types.count("review_decision_recorded") == 12
        assert revised_event_types.count("human_feedback_gate_opened") == 2
    finally:
        await store.close()


@pytest.mark.anyio
async def test_live_postgres_publish_readiness_gate():
    settings = get_settings()
    await setup_durable_storage(settings)
    store = await PostgresStore.from_settings(settings)
    try:
        run = await store.create_run(
            RunState(goal="Publish readiness live smoke", status=RunStatus.RUNNING)
        )
        source = await store.record_source(
            SourceRecord(
                run_id=run.run_id,
                citation_id="S1",
                title="Publish readiness source",
                url="https://huggingface.co/docs/inference-providers/index",
                publisher="Hugging Face",
                metadata={"source_type": "official_documentation"},
            )
        )
        claim = await store.record_claim(
            ClaimRecord(
                run_id=run.run_id,
                claim_text="Publish readiness needs supported claim provenance.",
                support_status=ClaimSupportStatus.SUPPORTED,
                source_ids=[source.source_id],
                reviewer_agent_id="claim-verification-agent",
            )
        )
        artifact = await store.record_artifact(
            ArtifactRecord(
                run_id=run.run_id,
                artifact_type=ArtifactType.POST,
                title="Readiness post",
                uri="artifact://runs/readiness/post",
                content={
                    "body": "A grounded Gemma draft with durable provenance.",
                    "claim_ids": [str(claim.claim_id)],
                    "source_citations": ["S1"],
                    "prompt_input": "Explain publish readiness provenance.",
                },
                provenance={
                    "generation_mode": "gemma_provider",
                    "model_provider": "huggingface",
                    "model_id": "google/gemma-4-31b-it",
                    "prompt_input": "Explain publish readiness provenance.",
                    "claim_ids": [str(claim.claim_id)],
                    "source_ids": [str(source.source_id)],
                },
                source_ids=[source.source_id],
                reviewer_decisions=[
                    {
                        "reviewer_agent_id": "editor-in-chief",
                        "status": "approved",
                        "notes": "Live publish-readiness fixture approved.",
                    }
                ],
                revision_history=[
                    {
                        "actor": "content-strategist",
                        "note": "Initial Gemma provider-backed draft.",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                ],
            )
        )
        ledger = await SourceLedgerWorkflow(store).build(
            run.run_id,
            SourceLedgerSnapshotRequest(record_artifact=True),
        )
        assert ledger.source_count == 1
        assert ledger.claim_count == 1
        assert ledger.artifact_count == 1
        assert ledger.artifact_entries[0].coverage_status == "supported"
        assert ledger.ledger_artifact_id is not None

        audit_result = await GuardrailAuditWorkflow(store).run(
            run.run_id,
            GuardrailAuditRequest(open_feedback_gate=False),
        )
        assert audit_result.status.value == "approved"
        readiness = await PublishReadinessWorkflow(store).run(
            run.run_id,
            PublishReadinessRequest(
                open_feedback_gate=True,
                mark_run_completed_if_ready=True,
            ),
        )
        assert readiness.ready is True
        assert readiness.status.value == "ready"
        assert readiness.artifact_ids == [artifact.artifact_id]
        assert readiness.feedback_gate_opened is False
        assert readiness.blocking_issues == []
        updated_run = await store.get_run(run.run_id)
        assert updated_run is not None
        assert updated_run.status.value == "completed"
        event_types = [event.event_type for event in await store.list_events(run.run_id)]
        assert "source_ledger_snapshot_built" in event_types
        assert "publish_readiness_checked" in event_types
    finally:
        await store.close()


@pytest.mark.anyio
async def test_live_postgres_source_repair_keeps_model_gate_closed_for_fallback():
    settings = get_settings()
    await setup_durable_storage(settings)
    store = await PostgresStore.from_settings(settings)
    try:
        content_result = await ContentStudioWorkflow(store).run(
            OrchestrationRequest(
                transcript="Create source-backed content about source repair.",
                topic="source repair",
                require_human_feedback=False,
            )
        )
        original_source_ids = content_result.source_ids

        worker = AgentWorker(
            store,
            ContentWorkflowServices(search_provider=LiveFakeSearchProvider()),
        )
        research_result = await worker.run(
            "web-research-agent",
            AgentWorkerRunRequest(
                run_id=content_result.run_id,
                max_tasks=1,
                use_gemma=False,
            ),
        )
        assert research_result.processed_tasks[0].generation_mode == (
            "web_search_provider"
        )

        research_messages = await store.list_agent_messages(
            content_result.run_id,
            agent_id="web-research-agent",
            status=AgentTaskStatus.COMPLETED,
        )
        assert research_messages
        source_repair = research_messages[0].result["source_repair"]
        assert source_repair["claim_count"] == 1
        assert source_repair["artifact_count"] == 3
        assert research_messages[0].result["research_freshness_ledger"]["status"] == (
            "needs_refresh"
        )
        assert research_messages[0].result["research_freshness_ledger"][
            "ledger_artifact_id"
        ]

        repaired_claims = await store.list_claims(content_result.run_id)
        repaired_artifacts = await store.list_artifacts(content_result.run_id)
        assert original_source_ids[0] not in repaired_claims[0].source_ids
        publishable_artifacts = [
            artifact
            for artifact in repaired_artifacts
            if artifact.artifact_type
            in {
                ArtifactType.POST,
                ArtifactType.REEL_SCRIPT,
                ArtifactType.SUBSTACK_ARTICLE,
            }
        ]
        assert len(publishable_artifacts) == 3
        assert all(
            original_source_ids[0] not in artifact.source_ids
            for artifact in publishable_artifacts
        )
        assert all(
            "source_grounding_repairs" in artifact.provenance
            for artifact in publishable_artifacts
        )

        claim_result = await AgentWorker(store).run(
            "claim-verification-agent",
            AgentWorkerRunRequest(
                run_id=content_result.run_id,
                max_tasks=1,
                use_gemma=False,
            ),
        )
        assert claim_result.processed_tasks[0].generation_mode == (
            "claim_verification_worker"
        )
        verified_claims = await store.list_claims(content_result.run_id)
        assert any(
            claim.support_status == ClaimSupportStatus.UNSUPPORTED
            for claim in verified_claims
        )
        claim_messages = await store.list_agent_messages(
            content_result.run_id,
            agent_id="claim-verification-agent",
            status=AgentTaskStatus.COMPLETED,
        )
        assert claim_messages
        assert claim_messages[0].result["retrieval_evidence_required"] is True
        assert claim_messages[0].result["missing_accepted_retrieval_claim_ids"]

        audit_result = await GuardrailAuditWorkflow(store).run(
            content_result.run_id,
            GuardrailAuditRequest(open_feedback_gate=False),
        )
        assert audit_result.status.value == "blocked"
        assert all(
            "unsupported_claims" in audit.blocking_issues
            for audit in audit_result.audits
        )

        readiness = await PublishReadinessWorkflow(store).run(
            content_result.run_id,
            PublishReadinessRequest(
                open_feedback_gate=False,
                mark_run_completed_if_ready=True,
            ),
        )
        assert readiness.ready is False
        assert readiness.status.value == "blocked"
        assert "weak_source_records" not in readiness.blocking_issues
        assert "retrieval_quality_not_ready" in readiness.blocking_issues
        assert "unsupported_claims" in readiness.blocking_issues
        assert "blocked_guardrail_audit" in readiness.blocking_issues
        assert "deterministic_fallback_content_not_publishable" in (
            readiness.blocking_issues
        )

        event_types = [
            event.event_type
            for event in await store.list_events(content_result.run_id, limit=1000)
        ]
        assert event_types.count("agent_tool_use_approved") >= 2
        assert "source_grounding_repaired" in event_types
        assert "research_freshness_ledger_built" in event_types
        assert "claim_verification_completed" in event_types
        assert "publish_readiness_checked" in event_types
    finally:
        await store.close()


@pytest.mark.anyio
async def test_live_postgres_autonomous_studio_pass(tmp_path):
    settings = get_settings()
    await setup_durable_storage(settings)
    store = await PostgresStore.from_settings(settings)
    try:
        content_result = await ContentStudioWorkflow(store).run(
            OrchestrationRequest(
                transcript=(
                    "Create source-backed content about bounded autonomous "
                    "studio passes."
                ),
                topic="bounded autonomous studio passes",
                require_human_feedback=False,
            )
        )

        pass_result = await AutonomousStudioPassWorkflow(store, tmp_path).run(
            content_result.run_id,
            AutonomousStudioPassRequest(
                agent_ids=["web-research-agent", "claim-verification-agent"],
                max_tasks_per_agent=1,
                max_worker_rounds=1,
                use_gemma=False,
                open_feedback_gate=False,
                block_on_retrieval_quality_blocked=False,
                generate_interactive_note=True,
            ),
        )

        assert pass_result.checkpoint is not None
        assert pass_result.checkpoint.checkpoint_kind == "autonomous_studio_pass_start"
        assert pass_result.runtime_health is not None
        assert pass_result.runtime_health.status.value == "ready"
        assert pass_result.runtime_health.ledger_artifact_id is not None
        assert pass_result.research_freshness is not None
        assert pass_result.research_freshness.status.value == "needs_refresh"
        assert pass_result.research_freshness.ledger_artifact_id is not None
        assert pass_result.retrieval_quality is not None
        assert pass_result.retrieval_quality.status.value == "blocked"
        assert pass_result.worker_cycle is not None
        assert pass_result.worker_cycle.total_processed_tasks == 2
        assert pass_result.media_production is not None
        assert len(pass_result.media_production.media_artifact_ids) == 3
        assert pass_result.distribution_package is not None
        assert pass_result.distribution_package.distribution_artifact_id is not None
        assert "instagram_reel" in pass_result.distribution_package.platforms
        assert pass_result.source_ledger is not None
        assert pass_result.source_ledger.ledger_artifact_id is not None
        assert pass_result.guardrail_audit is not None
        assert len(pass_result.guardrail_audit.audits) == 7
        assert pass_result.publish_readiness is not None
        assert pass_result.publish_readiness.status.value == "blocked"
        assert "weak_source_records" in pass_result.publish_readiness.blocking_issues
        assert pass_result.work_plan is not None
        assert pass_result.work_plan.artifact_id is not None
        assert pass_result.work_plan.blocked_item_count >= 1
        assert pass_result.work_plan.created_task_message_ids
        assert pass_result.sync_pulse is not None
        assert pass_result.sync_pulse.artifact_id is not None
        assert pass_result.sync_pulse.agent_states
        assert pass_result.context_packet_artifact is not None
        assert pass_result.context_packet_artifact.artifact_id is not None
        assert pass_result.skill_usage_ledger is not None
        assert pass_result.skill_usage_ledger.skill_source_contract_issue_count == 0
        assert pass_result.model_routing_ledger is not None
        assert pass_result.model_routing_ledger.ledger_artifact_id is not None
        assert pass_result.model_routing_ledger.boundary_violation_count >= 3
        assert any(
            "deterministic_fallback_content_not_publishable" in violation
            for check in pass_result.model_routing_ledger.boundary_checks
            for violation in check.violations
        )
        assert pass_result.foundation_audit is not None
        assert pass_result.foundation_audit.audit_artifact_id is not None
        assert pass_result.interactive_note is not None
        assert pass_result.interactive_note.uri.endswith("/interactive-run-note.html")
        assert pass_result.run_replay_ledger is not None
        assert pass_result.run_replay_ledger.replay_artifact_id is not None
        assert pass_result.skipped_steps == []

        event_types = [
            event.event_type
            for event in await store.list_events(content_result.run_id, limit=1000)
        ]
        assert "autonomous_studio_pass_started" in event_types
        assert "runtime_health_live_postgres_connected" in event_types
        assert "runtime_health_ledger_built" in event_types
        assert "research_freshness_ledger_built" in event_types
        assert "distribution_package_built" in event_types
        assert "run_work_plan_built" in event_types
        assert "multi_agent_sync_pulse_recorded" in event_types
        assert "model_routing_ledger_built" in event_types
        assert "foundation_audit_built" in event_types
        assert "run_replay_ledger_built" in event_types
        assert "autonomous_studio_pass_completed" in event_types
        assert event_types.count("guardrail_audit_recorded") == 7
        artifacts = await store.list_artifacts(content_result.run_id)
        artifact_types = [artifact.artifact_type.value for artifact in artifacts]
        for expected_type in [
            "social_package",
            "source_ledger",
            "system_plan",
            "context_packet",
            "skill_usage_ledger",
            "model_routing_ledger",
            "provider_operations_ledger",
            "html_note",
            "foundation_audit",
            "run_replay_ledger",
        ]:
            assert expected_type in artifact_types
        assert any(
            artifact.provenance.get("workflow") == "run_sync_pulse_v1"
            for artifact in artifacts
        )
        assert any(
            artifact.provenance.get("workflow") == "foundation_audit_v1"
            for artifact in artifacts
        )
    finally:
        await store.close()


@pytest.mark.anyio
async def test_live_postgres_conversation_router_turns(tmp_path):
    settings = get_settings()
    await setup_durable_storage(settings)
    store = await PostgresStore.from_settings(settings)
    try:
        router = ConversationRouter(store)
        routed = await router.route(
            ConversationRouteRequest(
                transcript=(
                    "Create a grounded ELI5 social post, reel, and Substack "
                    "about natural dialogue routing."
                ),
                modality="voice",
                topic="natural dialogue routing",
                require_human_feedback=True,
            )
        )
        assert routed.created_run is True
        assert routed.routed_intent.value == "create_content"
        assert len(routed.artifact_ids) == 3

        revised = await router.route(
            ConversationRouteRequest(
                run_id=routed.run_id,
                transcript="Make the hook shorter and keep the source caveat obvious.",
                require_human_feedback=False,
            )
        )
        assert revised.created_run is False
        assert revised.routed_intent.value == "revise_content"
        assert revised.feedback_gate_opened is False
        assert len(revised.artifact_ids) == 1
        assert routed.response_turn_id is not None
        assert revised.response_turn_id is not None

        events = await store.list_events(routed.run_id)
        assert [event.event_type for event in events].count(
            "conversation_turn_routed"
        ) == 2
        conversation_turns = await store.list_conversation_turns(routed.run_id)
        assert len(conversation_turns) == 4
        assert [turn.speaker for turn in conversation_turns] == [
            "user",
            "assistant",
            "user",
            "assistant",
        ]
        assert conversation_turns[1].metadata["responds_to_turn_id"] == str(
            conversation_turns[0].turn_id
        )
        assert len(await store.list_artifacts(routed.run_id)) == 4

        multimodal_turn = await router.route(
            ConversationRouteRequest(
                run_id=routed.run_id,
                transcript="Use this screenshot and voice note as added context.",
                modality="voice",
                intent=ConversationRouteIntent.ROUTE_TASK,
                require_human_feedback=False,
                assets=[
                    {
                        "asset_uri": "artifact://uploads/live-screen.png",
                        "modality": "screenshot",
                        "description": "Live cockpit screen",
                    },
                    {
                        "asset_uri": "artifact://uploads/live-voice.wav",
                        "modality": "voice",
                        "description": "Live voice note",
                    },
                ],
            )
        )
        assert multimodal_turn.multimodal_intake is not None
        assert multimodal_turn.multimodal_intake.asset_count == 2
        assert multimodal_turn.artifact_ids[-1] == (
            multimodal_turn.multimodal_intake.intake_artifact_id
        )
        events = await store.list_events(routed.run_id)
        assert [event.event_type for event in events].count(
            "conversation_turn_routed"
        ) == 3
        assert "multimodal_intake_recorded" in [event.event_type for event in events]
        artifacts = await store.list_artifacts(routed.run_id)
        assert artifacts[-2].artifact_type == ArtifactType.MULTIMODAL_INTAKE_LEDGER
        assert artifacts[-1].artifact_type == ArtifactType.CONVERSATION_HANDOFF

        note_result = await InteractiveRunNoteWorkflow(store, tmp_path).generate(
            routed.run_id,
            InteractiveRunNoteRequest(title="Live interactive run note"),
        )
        assert note_result.uri.endswith("/interactive-run-note.html")
        assert "interactive-run-note.html" in note_result.file_path
        html_note_artifacts = [
            artifact
            for artifact in await store.list_artifacts(routed.run_id)
            if artifact.artifact_type == ArtifactType.HTML_NOTE
        ]
        assert len(html_note_artifacts) == 1
        assert html_note_artifacts[0].provenance["agent_id"] == (
            "interactive-note-taking-agent"
        )
    finally:
        await store.close()
