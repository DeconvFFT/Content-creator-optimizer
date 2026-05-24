import asyncio
import hmac
import inspect
import json
import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock
from urllib.parse import urlparse
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from all_about_llms.a2a_discovery import (
    build_a2a_http_json_interface,
    build_public_a2a_agent_card,
)
from all_about_llms.agents import (
    AGENT_ROSTER,
    get_agent_card,
    get_skill_card,
    list_skill_cards,
    skill_cards_for_agent,
)
from all_about_llms.config import Settings, get_settings
from all_about_llms.local_provider_config import (
    LocalProviderConfigEnvName,
    LocalProviderConfigValidationError,
    local_provider_config_field_name,
    sanitized_local_provider_config_for_write,
    validate_local_provider_config_value,
)
from all_about_llms.realtime_safety import (
    normalize_realtime_metadata_key,
    realtime_metadata_key_is_sensitive,
    redact_realtime_string,
    safe_realtime_metadata,
    safe_realtime_metadata_value,
)
from all_about_llms.contracts import (
    AgentMessage,
    AgentMessageResponse,
    AgentMessageRetryRequest,
    AgentMessageRetryResponse,
    AgentMessageDetailResponse,
    AgentMessagePublicProjection,
    AgentMemory,
    AgentMemoryCreate,
    A2ACollaborationGraphRequest,
    A2ACollaborationGraphResult,
    AgentMessageDependencyRepairRequest,
    AgentMessageDependencyRepairResponse,
    ArtifactRecord,
    ArtifactRecordCreate,
    ArtifactType,
    AutopilotLaunchRequest,
    AutopilotLaunchResult,
    AutonomousStudioPassRequest,
    AutonomousStudioPassResult,
    AgentMessageStatusResponse,
    AgentMessageStatusUpdate,
    AgentTaskStatus,
    AgentWorkerCycleRequest,
    AgentWorkerCycleResult,
    AgentWorkerRunRequest,
    AgentWorkerRunResult,
    ClaimRecord,
    ClaimRecordCreate,
    ClaimSupportStatus,
    CockpitWalkthroughLedgerRequest,
    CockpitWalkthroughLedgerResult,
    ConversationRouteRequest,
    ConversationRouteResult,
    ConversationTurn,
    ConversationTurnCreate,
    DistributionPackageRequest,
    DistributionPackageResult,
    FeedbackItem,
    FeedbackResolutionLedgerRequest,
    FeedbackResolutionLedgerResult,
    FeedbackResolutionRequest,
    FeedbackResolutionResult,
    FeedbackRoutingResult,
    FeedbackStatus,
    FoundationAuditRequest,
    FoundationAuditResult,
    FoundationReferenceResult,
    GrowthPackageResult,
    GuardrailAuditRequest,
    GuardrailAuditResult,
    InteractiveRunNoteRequest,
    InteractiveRunNoteResult,
    LocalLiveKitDevConfigResult,
    LocalLiveKitProcessStartRequest,
    LocalLiveKitProcessStatusResult,
    LocalProviderConfigWriteRequest,
    LocalProviderConfigWriteResult,
    LocalSecretFileEnvName,
    LocalSecretFileWriteRequest,
    LocalSecretFileWriteResult,
    MemorySearchRequest,
    MemorySearchResult,
    MediaProductionRequest,
    MediaProductionResult,
    MultimodalIntakeRequest,
    MultimodalIntakeResult,
    ModelRoutingLedgerRequest,
    ModelRoutingLedgerResult,
    ObsidianMemoryPromotionRequest,
    ObsidianMemoryPromotionResult,
    ObsidianReviewNoteRequest,
    ObsidianReviewNoteResult,
    OrchestrationRequest,
    OrchestrationResult,
    PlanningFeedbackIngestRequest,
    PlanningFeedbackIngestResult,
    PlanningFeedbackRoutedItem,
    ProviderOperationsLedgerRequest,
    ProviderOperationsLedgerResult,
    ProviderSmokeRunRequest,
    ProviderSmokeRunResult,
    ProjectMemoryKind,
    ProjectMemoryRecordRequest,
    ProjectMemoryRecordResult,
    ProjectMemoryRetrievalRequest,
    ProjectMemoryRetrievalResult,
    ProjectMemoryScope,
    ProviderReadinessResult,
    PublishReadinessRequest,
    PublishReadinessResult,
    RealtimeControlAction,
    RealtimeVoiceAgentEventCreate,
    RealtimeVoiceAgentEventRecordResult,
    RealtimeDialogueLedgerRequest,
    RealtimeDialogueLedgerResult,
    RealtimeVoiceTimingLedgerRequest,
    RealtimeVoiceTimingLedgerResult,
    RealtimeSpokenResponsePlan,
    RealtimeSessionControlRequest,
    RealtimeSessionControlResult,
    RealtimeSessionCreateRequest,
    RealtimeSessionCreateResult,
    RealtimeSessionRecord,
    RealtimeSessionStatusUpdate,
    RealtimeTransportGrant,
    RealtimeTurnCreate,
    RealtimeTurnResult,
    ResearchFreshnessLedgerRequest,
    ResearchFreshnessLedgerResult,
    RetrievalQualityLedgerRequest,
    RetrievalQualityLedgerResult,
    RevisionRequest,
    RevisionResult,
    RunCheckpointCreate,
    RunCheckpointResult,
    RunContextPacket,
    RunContextPacketRequest,
    RunCreateRequest,
    RunEvent,
    RunReplayLedgerRequest,
    RunReplayLedgerResult,
    RunResumePlan,
    RunResumePlanRequest,
    RunResumeRequest,
    RunResumeResult,
    RunState,
    RunStatus,
    RunSyncPulseRequest,
    RunSyncPulseResult,
    RunWorkPlanRequest,
    RunWorkPlanResult,
    RuntimeHealthLedgerRequest,
    RuntimeHealthLedgerResult,
    SourceRecord,
    SourceRecordCreate,
    SourceLedgerSnapshotRequest,
    SourceLedgerSnapshotResult,
    SkillUsageLedgerRequest,
    SkillUsageLedgerResult,
    VoiceAgentPresenceResult,
    VoiceAgentPresenceStatus,
    VoiceAgentProcessStartRequest,
    VoiceAgentProcessStatusResult,
    VoiceRuntimeReadinessResult,
    VoiceSetupProofRequest,
    VoiceSetupProofResult,
    WorkerProfile,
    WorkerProfileCreate,
    WorkerProfileHeartbeatResult,
    WorkerProfileStatus,
    WorkerProfileStatusUpdate,
    WorkerSchedulerProcessStartRequest,
    WorkerSchedulerProcessStatusResult,
    WorkerSchedulerRunRequest,
    WorkerSchedulerRunResult,
)
from all_about_llms.foundation_references import list_foundation_references
from all_about_llms.model_routing import list_model_routes
from all_about_llms.orchestration import (
    AgentWorker,
    AgentWorkerAgentNotFoundError,
    AgentWorkerRunNotFoundError,
    A2ACollaborationGraphRunNotFoundError,
    A2ACollaborationGraphWorkflow,
    AutonomousStudioPassRunNotFoundError,
    AutonomousStudioPassWorkflow,
    AutopilotLaunchAgentNotFoundError,
    AutopilotLaunchRunNotFoundError,
    AutopilotLaunchWorkflow,
    CockpitWalkthroughLedgerRunNotFoundError,
    CockpitWalkthroughLedgerWorkflow,
    ConversationRouter,
    ConversationRouterRevisionUnavailableError,
    ConversationRouterRunNotFoundError,
    DistributionPackageRunNotFoundError,
    DistributionPackageWorkflow,
    WorkerProfileNotFoundError,
    ContentStudioWorkflow,
    FeedbackRoutingAgentNotFoundError,
    FeedbackRoutingRunNotFoundError,
    FeedbackRoutingWorkflow,
    FeedbackResolutionLedgerRunNotFoundError,
    FeedbackResolutionLedgerWorkflow,
    FoundationAuditRunNotFoundError,
    FoundationAuditWorkflow,
    GuardrailAuditRunNotFoundError,
    GuardrailAuditWorkflow,
    InteractiveRunNoteRunNotFoundError,
    InteractiveRunNoteWorkflow,
    MediaProductionRunNotFoundError,
    MediaProductionWorkflow,
    MultimodalIntakeRunNotFoundError,
    MultimodalIntakeWorkflow,
    ModelRoutingLedgerRunNotFoundError,
    ModelRoutingLedgerWorkflow,
    NoArtifactsForDistributionPackageError,
    NoArtifactsForMediaProductionError,
    NoArtifactsToReviseError,
    NoArtifactsToAuditError,
    ObsidianReviewNoteRunNotFoundError,
    ObsidianReviewNoteWorkflow,
    ObsidianMemoryPromotionRunNotFoundError,
    ObsidianMemoryPromotionWorkflow,
    PublishReadinessRunNotFoundError,
    PublishReadinessWorkflow,
    ProviderOperationsLedgerRunNotFoundError,
    ProviderOperationsLedgerWorkflow,
    ProviderSmokeRunNotFoundError,
    ProviderSmokeWorkflow,
    ProjectMemoryAgentNotFoundError,
    ProjectMemoryRetrievalAgentNotFoundError,
    ProjectMemoryRetrievalRunNotFoundError,
    ProjectMemoryRetrievalWorkflow,
    ProjectMemoryRunNotFoundError,
    ProjectMemoryWorkflow,
    RealtimeDialogueLedgerRunNotFoundError,
    RealtimeDialogueLedgerWorkflow,
    RealtimeVoiceTimingLedgerRunNotFoundError,
    RealtimeVoiceTimingLedgerWorkflow,
    ResearchFreshnessLedgerRunNotFoundError,
    ResearchFreshnessLedgerWorkflow,
    RetrievalQualityLedgerRunNotFoundError,
    RetrievalQualityLedgerWorkflow,
    RevisionWorkflow,
    RunNotFoundError,
    RunResumeRunNotFoundError,
    RunResumeWorkflow,
    RuntimeHealthLedgerRunNotFoundError,
    RuntimeHealthLedgerWorkflow,
    RunReplayLedgerCheckpointNotFoundError,
    RunReplayLedgerRunNotFoundError,
    RunReplayLedgerWorkflow,
    RunSyncPulseRunNotFoundError,
    RunSyncPulseWorkflow,
    RunWorkPlanRunNotFoundError,
    RunWorkPlanWorkflow,
    SourceLedgerRunNotFoundError,
    SourceLedgerWorkflow,
    SkillUsageLedgerRunNotFoundError,
    SkillUsageLedgerWorkflow,
)
from all_about_llms.orchestration.a2a_projection import (
    public_a2a_context_packet_event_payload,
    public_a2a_dependency_repair_event_payload,
    public_a2a_message_event_payload,
    public_a2a_message_projection,
    public_a2a_retry_event_payload,
    public_a2a_status_event_payload,
)
from all_about_llms.orchestration.context_engineering import (
    build_context_engineering_payload,
)
from all_about_llms.orchestration.agent_worker import (
    _build_influencer_strategy_artifact,
    _build_outreach_strategy_artifact,
)
from all_about_llms.orchestration.distribution_package import _normalized_platforms
from all_about_llms.orchestration.project_memory_retrieval import (
    project_memory_retrieval_digest,
)
from all_about_llms.orchestration.services import ContentWorkflowServices
from all_about_llms.orchestration.scheduler_supervisor import (
    LocalWorkerSchedulerSupervisor,
)
from all_about_llms.providers.factory import (
    build_gemma_provider,
    build_realtime_provider,
    build_reranker_provider,
    build_search_provider,
)
from all_about_llms.providers.interfaces import (
    ProviderConfigurationError,
    RealtimeSessionRequest,
)
from all_about_llms.providers.readiness import build_provider_readiness
from all_about_llms.storage import PostgresStore
from all_about_llms.voice_agent.readiness import build_voice_runtime_readiness
from all_about_llms.voice_agent.supervisor import (
    LocalLiveKitDevServerSupervisor,
    LocalVoiceAgentSupervisor,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
COCKPIT_PATH = PROJECT_ROOT / "frontend" / "cockpit" / "index.html"
APP_PATH = PROJECT_ROOT / "frontend" / "app" / "index.html"


async def _run_event_stream(
    *,
    store: PostgresStore,
    run_id: UUID,
    after_event_id: int | None = None,
    once: bool = False,
    poll_interval_seconds: float = 1.0,
) -> AsyncIterator[str]:
    last_event_id = after_event_id or 0
    while True:
        events = await store.list_events(
            run_id,
            after_event_id=last_event_id,
            limit=100,
        )
        for event in events:
            last_event_id = event.event_id or last_event_id
            yield (
                f"id: {last_event_id}\n"
                f"event: {event.event_type}\n"
                f"data: {json.dumps(event.model_dump(mode='json'))}\n\n"
            )
        if once:
            break
        if not events:
            yield 'event: heartbeat\ndata: {"status":"connected"}\n\n'
        await asyncio.sleep(poll_interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.store = None
    app.state.voice_agent_supervisor = None
    yield
    voice_agent_supervisor = getattr(app.state, "voice_agent_supervisor", None)
    if voice_agent_supervisor is not None:
        await voice_agent_supervisor.stop()
    local_livekit_supervisor = getattr(app.state, "local_livekit_supervisor", None)
    if local_livekit_supervisor is not None:
        await local_livekit_supervisor.stop()
    store = getattr(app.state, "store", None)
    if store is not None:
        await store.close()


app = FastAPI(
    title="All About LLMs Realtime Agent Studio",
    version="0.1.0",
    lifespan=lifespan,
)

VOICE_PROVIDER_FAILURE_RECOVERY_AGENT_IDS = [
    "inference-systems-engineer",
    "observability-agent",
    "agent-harness-engineer",
]
_LOCAL_PROVIDER_CONFIG_LOCK = Lock()
_LOCAL_LIVEKIT_DEV_URL = "ws://127.0.0.1:7880"
_LOCAL_LIVEKIT_DEV_API_KEY = "devkey"
_LOCAL_LIVEKIT_DEV_API_SECRET = "secret"
_LOCAL_ENVIRONMENTS = {"local", "dev", "development", "test"}
_PRODUCTION_ADMIN_AUTH_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _is_local_environment(settings: Settings) -> bool:
    return settings.environment.strip().lower() in _LOCAL_ENVIRONMENTS


def _request_admin_bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization", "")
    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer":
        return None
    stripped_token = token.strip()
    return stripped_token or None


async def _request_settings(request: Request) -> Settings:
    settings_provider = request.app.dependency_overrides.get(get_settings, get_settings)
    settings = settings_provider()
    if inspect.isawaitable(settings):
        settings = await settings
    return settings


@app.middleware("http")
async def require_production_admin_auth(request: Request, call_next):
    settings = await _request_settings(request)
    if (
        _is_local_environment(settings)
        or request.method.upper() not in _PRODUCTION_ADMIN_AUTH_METHODS
    ):
        return await call_next(request)

    expected_token = (settings.admin_api_token or "").strip()
    if not expected_token:
        return JSONResponse(
            status_code=503,
            content={"detail": "Production admin token is not configured."},
        )
    request_token = _request_admin_bearer_token(request)
    if request_token is None or not hmac.compare_digest(
        request_token.encode("utf-8"),
        expected_token.encode("utf-8"),
    ):
        return JSONResponse(
            status_code=401,
            content={"detail": "Production admin authentication required."},
        )
    return await call_next(request)


async def get_store(settings: Settings = Depends(get_settings)) -> PostgresStore:
    if getattr(app.state, "store", None) is None:
        app.state.store = await PostgresStore.from_settings(settings)
    return app.state.store


async def get_content_workflow_services(
    settings: Settings = Depends(get_settings),
) -> ContentWorkflowServices:
    return ContentWorkflowServices(
        search_provider=build_search_provider(settings),
        gemma_provider=build_gemma_provider(settings),
        reranker_provider=build_reranker_provider(settings),
    )


async def get_realtime_provider_factory(settings: Settings = Depends(get_settings)):
    def factory(provider: str | None = None):
        return build_realtime_provider(settings, provider)

    return factory


async def get_voice_agent_supervisor(
    settings: Settings = Depends(get_settings),
) -> LocalVoiceAgentSupervisor:
    if getattr(app.state, "voice_agent_supervisor", None) is None:
        app.state.voice_agent_supervisor = LocalVoiceAgentSupervisor(settings)
    return app.state.voice_agent_supervisor


async def get_local_livekit_supervisor(
    settings: Settings = Depends(get_settings),
) -> LocalLiveKitDevServerSupervisor:
    if getattr(app.state, "local_livekit_supervisor", None) is None:
        app.state.local_livekit_supervisor = LocalLiveKitDevServerSupervisor(settings)
    return app.state.local_livekit_supervisor


async def get_worker_scheduler_supervisor(
    settings: Settings = Depends(get_settings),
) -> LocalWorkerSchedulerSupervisor:
    if getattr(app.state, "worker_scheduler_supervisor", None) is None:
        app.state.worker_scheduler_supervisor = LocalWorkerSchedulerSupervisor(settings)
    return app.state.worker_scheduler_supervisor


@app.get("/health")
async def health(settings: Settings = Depends(get_settings)) -> dict[str, object]:
    return {
        "status": "ok",
        "database": "postgres",
        "vector_store": "pgvector",
        "app_artifact": "frontend/app/index.html",
        "cockpit_artifact": str(settings.cockpit_artifact_path),
        "planning_artifact": str(settings.planning_artifact_path),
        "realtime_providers_configured": settings.configured_realtime_providers(),
    }


@app.get("/", include_in_schema=False)
async def root_cockpit():
    return FileResponse(COCKPIT_PATH)


@app.get("/app", include_in_schema=False)
async def content_agent_app():
    return FileResponse(APP_PATH)


@app.get("/cockpit", include_in_schema=False)
async def product_cockpit():
    return FileResponse(COCKPIT_PATH)


@app.get("/artifacts/{artifact_path:path}", include_in_schema=False)
async def serve_artifact_file(
    artifact_path: str,
    settings: Settings = Depends(get_settings),
):
    root = _resolve_artifacts_root(settings).resolve()
    target = (root / artifact_path).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Artifact not found") from exc
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(target)


@app.get("/api/agents")
async def list_agents():
    return {"agents": [agent.model_dump() for agent in AGENT_ROSTER]}


@app.get("/.well-known/agent-cards.json")
async def well_known_agent_cards():
    return {
        "protocol": "a2a-style-agent-cards",
        "agents": [agent.model_dump() for agent in AGENT_ROSTER],
    }


@app.get("/.well-known/agent-card.json")
async def well_known_a2a_agent_card(request: Request):
    return build_public_a2a_agent_card(
        a2a_url=str(request.url_for("a2a_http_json_interface")),
        documentation_url=str(request.url_for("openapi")),
    )


@app.get("/.well-known/agent-skills.json")
async def well_known_agent_skills():
    return {
        "protocol": "agent-studio-skill-cards",
        "skills": [skill.model_dump() for skill in list_skill_cards()],
    }


@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    agent = get_agent_card(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@app.get("/api/a2a/agents/{agent_id}/card")
async def get_a2a_agent_card(agent_id: str):
    agent = get_agent_card(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"protocol": "a2a-style-agent-card", "card": agent.model_dump()}


@app.get("/api/a2a/agents/{agent_id}/skills")
async def get_a2a_agent_skills(agent_id: str):
    agent = get_agent_card(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {
        "agent_id": agent_id,
        "skill_ids": agent.skill_ids,
        "skills": [
            skill.model_dump() for skill in skill_cards_for_agent(agent_id)
        ],
    }


@app.get("/api/skills")
async def list_skills():
    return {"skills": [skill.model_dump() for skill in list_skill_cards()]}


@app.get("/api/skills/{skill_id}")
async def get_skill(skill_id: str):
    skill = get_skill_card(skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@app.get("/api/a2a")
async def a2a_http_json_interface(request: Request):
    return build_a2a_http_json_interface(
        agent_card_url=str(request.url_for("well_known_a2a_agent_card")),
    )


@app.get("/api/model-routing")
async def model_routing():
    return {"routes": [route.model_dump() for route in list_model_routes()]}


@app.get("/api/provider-readiness")
async def provider_readiness(
    settings: Settings = Depends(get_settings),
) -> ProviderReadinessResult:
    return build_provider_readiness(settings)


@app.post("/api/local-secret-files")
async def write_local_secret_file(
    request: LocalSecretFileWriteRequest,
    settings: Settings = Depends(get_settings),
) -> LocalSecretFileWriteResult:
    if settings.environment.strip().lower() not in {
        "local",
        "dev",
        "development",
        "test",
    }:
        raise HTTPException(
            status_code=403,
            detail="Local secret-file writes are allowed only in local/dev/test environments.",
        )
    secret_value = request.secret_value.strip()
    if not secret_value:
        raise HTTPException(status_code=400, detail="Secret value cannot be blank.")

    field_name, file_field_name, file_env_name = _local_secret_file_target(
        request.env_name
    )
    secret_file = getattr(settings, file_field_name)
    if secret_file is None:
        raise HTTPException(
            status_code=400,
            detail=f"{file_env_name} is not configured for local secret-file writes.",
        )
    target_path = secret_file if secret_file.is_absolute() else PROJECT_ROOT / secret_file
    try:
        with _LOCAL_PROVIDER_CONFIG_LOCK:
            _write_local_secret_file(target_path, secret_value)
            object.__setattr__(settings, field_name, secret_value)
            get_settings.cache_clear()
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not write {file_env_name} secret file.",
        ) from exc

    return LocalSecretFileWriteResult(
        env_name=request.env_name,
        file_env_name=file_env_name,
        status="loaded",
        configured=True,
        path=str(target_path),
        detail=f"{file_env_name} is configured with a readable non-empty file.",
    )


def _local_secret_file_target(
    env_name: LocalSecretFileEnvName,
) -> tuple[str, str, str]:
    if env_name == LocalSecretFileEnvName.HF_TOKEN:
        return "hf_token", "hf_token_file", "HF_TOKEN_FILE"
    if env_name == LocalSecretFileEnvName.LIVEKIT_API_KEY:
        return "livekit_api_key", "livekit_api_key_file", "LIVEKIT_API_KEY_FILE"
    if env_name == LocalSecretFileEnvName.LIVEKIT_API_SECRET:
        return (
            "livekit_api_secret",
            "livekit_api_secret_file",
            "LIVEKIT_API_SECRET_FILE",
        )
    if env_name == LocalSecretFileEnvName.TAVILY_API_KEY:
        return "tavily_api_key", "tavily_api_key_file", "TAVILY_API_KEY_FILE"
    if env_name == LocalSecretFileEnvName.INSTAGRAM_ACCESS_TOKEN:
        return (
            "instagram_access_token",
            "instagram_access_token_file",
            "INSTAGRAM_ACCESS_TOKEN_FILE",
        )
    if env_name == LocalSecretFileEnvName.LINKEDIN_ACCESS_TOKEN:
        return (
            "linkedin_access_token",
            "linkedin_access_token_file",
            "LINKEDIN_ACCESS_TOKEN_FILE",
        )
    if env_name == LocalSecretFileEnvName.X_ACCESS_TOKEN:
        return "x_access_token", "x_access_token_file", "X_ACCESS_TOKEN_FILE"
    if env_name == LocalSecretFileEnvName.X_API_KEY:
        return "x_api_key", "x_api_key_file", "X_API_KEY_FILE"
    if env_name == LocalSecretFileEnvName.SUBSTACK_API_TOKEN:
        return (
            "substack_api_token",
            "substack_api_token_file",
            "SUBSTACK_API_TOKEN_FILE",
        )
    raise HTTPException(status_code=400, detail="Unsupported local secret.")


def _write_local_secret_file(target_path: Path, secret_value: str) -> None:
    parent_path = target_path.parent
    parent_existed = parent_path.exists()
    parent_path.mkdir(parents=True, mode=0o700, exist_ok=True)
    if not parent_existed or parent_path == PROJECT_ROOT / ".secrets":
        os.chmod(parent_path, 0o700)
    temp_path = target_path.with_name(f".{target_path.name}.tmp-{uuid4().hex}")
    fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(secret_value)
            handle.write("\n")
        os.replace(temp_path, target_path)
        os.chmod(target_path, 0o600)
    except Exception:
        try:
            temp_path.unlink(missing_ok=True)
        finally:
            raise


@app.post("/api/local-provider-config")
async def write_local_provider_config(
    request: LocalProviderConfigWriteRequest,
    settings: Settings = Depends(get_settings),
) -> LocalProviderConfigWriteResult:
    if settings.environment.strip().lower() not in {
        "local",
        "dev",
        "development",
        "test",
    }:
        raise HTTPException(
            status_code=403,
            detail="Local provider configuration writes are allowed only in local/dev/test environments.",
        )
    try:
        config_value = validate_local_provider_config_value(
            request.env_name,
            request.config_value,
        )
    except LocalProviderConfigValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    field_name = _local_provider_config_target(request.env_name)
    config_file = settings.local_provider_config_file
    if config_file is None:
        raise HTTPException(
            status_code=400,
            detail="LOCAL_PROVIDER_CONFIG_FILE is not configured for local provider setup.",
        )
    target_path = config_file if config_file.is_absolute() else PROJECT_ROOT / config_file
    try:
        with _LOCAL_PROVIDER_CONFIG_LOCK:
            current_config = sanitized_local_provider_config_for_write(
                _read_local_provider_config_file(target_path)
            )
            current_config[str(request.env_name)] = config_value
            _write_local_provider_config_file(target_path, current_config)
            object.__setattr__(settings, field_name, config_value)
            get_settings.cache_clear()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not write LOCAL_PROVIDER_CONFIG_FILE.",
        ) from exc

    return LocalProviderConfigWriteResult(
        env_name=request.env_name,
        status="configured",
        configured=True,
        config_file_env_name="LOCAL_PROVIDER_CONFIG_FILE",
        path=str(target_path),
        detail=(
            f"{request.env_name} is configured in LOCAL_PROVIDER_CONFIG_FILE "
            "without exposing the value."
        ),
    )


def _local_provider_config_target(
    env_name: LocalProviderConfigEnvName | str,
) -> str:
    try:
        return local_provider_config_field_name(LocalProviderConfigEnvName(str(env_name)))
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Unsupported local provider config.",
        ) from exc


def _read_local_provider_config_file(target_path: Path) -> dict[str, str]:
    try:
        raw_text = target_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    raw_config = json.loads(raw_text)
    if not isinstance(raw_config, dict):
        raise ValueError("LOCAL_PROVIDER_CONFIG_FILE must contain a JSON object.")
    config: dict[str, str] = {}
    for key, value in raw_config.items():
        if isinstance(key, str) and isinstance(value, str):
            config[key] = value
    return config


def _write_local_provider_config_file(
    target_path: Path,
    config: dict[str, str],
) -> None:
    parent_path = target_path.parent
    parent_existed = parent_path.exists()
    parent_path.mkdir(parents=True, mode=0o700, exist_ok=True)
    if not parent_existed or parent_path == PROJECT_ROOT / ".secrets":
        os.chmod(parent_path, 0o700)
    temp_path = target_path.with_name(f".{target_path.name}.tmp-{uuid4().hex}")
    fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(config, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temp_path, target_path)
        os.chmod(target_path, 0o600)
    except Exception:
        try:
            temp_path.unlink(missing_ok=True)
        finally:
            raise


@app.post("/api/local-livekit-dev-config")
async def configure_local_livekit_dev(
    settings: Settings = Depends(get_settings),
) -> LocalLiveKitDevConfigResult:
    if settings.environment.strip().lower() not in {
        "local",
        "dev",
        "development",
        "test",
    }:
        raise HTTPException(
            status_code=403,
            detail="Local LiveKit dev configuration is allowed only in local/dev/test environments.",
        )
    config_file = settings.local_provider_config_file
    if config_file is None:
        raise HTTPException(
            status_code=400,
            detail="LOCAL_PROVIDER_CONFIG_FILE is not configured for local LiveKit dev setup.",
        )
    if settings.livekit_api_key_file is None:
        raise HTTPException(
            status_code=400,
            detail="LIVEKIT_API_KEY_FILE is not configured for local LiveKit dev setup.",
        )
    if settings.livekit_api_secret_file is None:
        raise HTTPException(
            status_code=400,
            detail="LIVEKIT_API_SECRET_FILE is not configured for local LiveKit dev setup.",
        )
    existing_conflicts = _local_livekit_dev_config_conflicts(settings)
    if existing_conflicts:
        raise HTTPException(
            status_code=409,
            detail=(
                "Local LiveKit dev setup would overwrite existing non-dev LiveKit "
                f"configuration: {', '.join(existing_conflicts)}."
            ),
        )

    livekit_url = validate_local_provider_config_value(
        LocalProviderConfigEnvName.OPENROUTER_LIVEKIT_URL,
        _LOCAL_LIVEKIT_DEV_URL,
    )
    config_path = config_file if config_file.is_absolute() else PROJECT_ROOT / config_file
    api_key_path = (
        settings.livekit_api_key_file
        if settings.livekit_api_key_file.is_absolute()
        else PROJECT_ROOT / settings.livekit_api_key_file
    )
    api_secret_path = (
        settings.livekit_api_secret_file
        if settings.livekit_api_secret_file.is_absolute()
        else PROJECT_ROOT / settings.livekit_api_secret_file
    )

    try:
        with _LOCAL_PROVIDER_CONFIG_LOCK:
            raw_current_config = _read_local_provider_config_file(config_path)
            current_config = sanitized_local_provider_config_for_write(
                raw_current_config
            )
            current_conflicts = _local_livekit_dev_file_conflicts(
                raw_current_config,
                api_key_path,
                api_secret_path,
            )
            if current_conflicts:
                raise LocalLiveKitDevConfigConflict(current_conflicts)
            touched_paths = [
                path
                for path in (api_key_path, api_secret_path, config_path)
                if not path.exists()
            ]
            backups = {
                path: path.read_bytes()
                for path in (api_key_path, api_secret_path, config_path)
                if path.exists()
            }
            current_config[
                str(LocalProviderConfigEnvName.OPENROUTER_LIVEKIT_URL)
            ] = livekit_url
            try:
                _write_local_secret_file(api_key_path, _LOCAL_LIVEKIT_DEV_API_KEY)
                _write_local_secret_file(
                    api_secret_path,
                    _LOCAL_LIVEKIT_DEV_API_SECRET,
                )
                _write_local_provider_config_file(config_path, current_config)
            except OSError:
                _rollback_local_livekit_dev_writes(touched_paths, backups)
                raise
            object.__setattr__(settings, "openrouter_livekit_url", livekit_url)
            object.__setattr__(settings, "livekit_api_key", _LOCAL_LIVEKIT_DEV_API_KEY)
            object.__setattr__(
                settings,
                "livekit_api_secret",
                _LOCAL_LIVEKIT_DEV_API_SECRET,
            )
            get_settings.cache_clear()
    except LocalLiveKitDevConfigConflict as exc:
        raise HTTPException(
            status_code=409,
            detail=(
                "Local LiveKit dev setup would overwrite existing non-dev LiveKit "
                f"configuration: {', '.join(exc.conflicts)}."
            ),
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not write local LiveKit dev configuration files.",
        ) from exc

    return LocalLiveKitDevConfigResult(
        status="configured",
        configured=True,
        configured_env=[
            "OPENROUTER_LIVEKIT_URL",
            "LIVEKIT_API_KEY",
            "LIVEKIT_API_SECRET",
        ],
        config_file_env_name="LOCAL_PROVIDER_CONFIG_FILE",
        secret_file_env_names=["LIVEKIT_API_KEY_FILE", "LIVEKIT_API_SECRET_FILE"],
        paths={
            "LOCAL_PROVIDER_CONFIG_FILE": str(config_path),
            "LIVEKIT_API_KEY_FILE": str(api_key_path),
            "LIVEKIT_API_SECRET_FILE": str(api_secret_path),
        },
        detail=(
            "Local LiveKit dev transport defaults are configured in ignored local files "
            "without returning credential values."
        ),
    )


class LocalLiveKitDevConfigConflict(ValueError):
    def __init__(self, conflicts: list[str]):
        super().__init__(", ".join(conflicts))
        self.conflicts = conflicts


def _local_livekit_dev_config_conflicts(settings: Settings) -> list[str]:
    conflicts: list[str] = []
    if settings.openrouter_livekit_url and not _is_local_livekit_dev_url(
        str(settings.openrouter_livekit_url)
    ):
        conflicts.append("OPENROUTER_LIVEKIT_URL")
    if settings.gemma4_realtime_livekit_url and not _is_local_livekit_dev_url(
        str(settings.gemma4_realtime_livekit_url)
    ):
        conflicts.append("GEMMA4_REALTIME_LIVEKIT_URL")
    if settings.livekit_api_key and settings.livekit_api_key != _LOCAL_LIVEKIT_DEV_API_KEY:
        conflicts.append("LIVEKIT_API_KEY")
    if (
        settings.livekit_api_secret
        and settings.livekit_api_secret != _LOCAL_LIVEKIT_DEV_API_SECRET
    ):
        conflicts.append("LIVEKIT_API_SECRET")
    return conflicts


def _local_livekit_dev_file_conflicts(
    current_config: dict[str, str],
    api_key_path: Path,
    api_secret_path: Path,
) -> list[str]:
    conflicts: list[str] = []
    for env_name in (
        LocalProviderConfigEnvName.OPENROUTER_LIVEKIT_URL,
        LocalProviderConfigEnvName.GEMMA4_REALTIME_LIVEKIT_URL,
    ):
        configured_url = current_config.get(str(env_name))
        if configured_url and not _is_local_livekit_dev_url(configured_url):
            conflicts.append(str(env_name))
    api_key = _read_optional_local_file(api_key_path)
    if api_key and api_key != _LOCAL_LIVEKIT_DEV_API_KEY:
        conflicts.append("LIVEKIT_API_KEY_FILE")
    api_secret = _read_optional_local_file(api_secret_path)
    if api_secret and api_secret != _LOCAL_LIVEKIT_DEV_API_SECRET:
        conflicts.append("LIVEKIT_API_SECRET_FILE")
    return conflicts


def _read_optional_local_file(path: Path) -> str | None:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value or None


def _rollback_local_livekit_dev_writes(
    touched_paths: list[Path],
    backups: dict[Path, bytes],
) -> None:
    for path in touched_paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
    for path, data in backups.items():
        try:
            _restore_file_bytes(path, data)
        except OSError:
            pass


def _restore_file_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(data)
    try:
        os.replace(temp_path, path)
        os.chmod(path, 0o600)
    except Exception:
        try:
            temp_path.unlink(missing_ok=True)
        finally:
            raise


def _is_local_livekit_dev_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return (
        parsed.scheme in {"ws", "wss", "http", "https"}
        and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        and (parsed.port or 7880) == 7880
        and parsed.path in {"", "/"}
        and not parsed.query
        and not parsed.fragment
    )


@app.get("/api/voice-runtime-readiness")
async def voice_runtime_readiness(
    preflight_livekit: bool = Query(default=False),
    preflight_edge: bool = Query(default=False),
    preflight_agent: bool = Query(default=False),
    preflight_gemma: bool = Query(default=False),
    preflight_tts: bool = Query(default=False),
    settings: Settings = Depends(get_settings),
) -> VoiceRuntimeReadinessResult:
    return await build_voice_runtime_readiness(
        settings,
        preflight_livekit=preflight_livekit,
        preflight_edge=preflight_edge,
        preflight_agent=preflight_agent,
        preflight_gemma=preflight_gemma,
        preflight_tts=preflight_tts,
    )


@app.get("/api/voice-agent-process")
async def get_voice_agent_process_status(
    supervisor: LocalVoiceAgentSupervisor = Depends(get_voice_agent_supervisor),
) -> VoiceAgentProcessStatusResult:
    return await supervisor.status()


@app.post("/api/voice-agent-process/start")
async def start_voice_agent_process(
    request: VoiceAgentProcessStartRequest,
    supervisor: LocalVoiceAgentSupervisor = Depends(get_voice_agent_supervisor),
) -> VoiceAgentProcessStatusResult:
    return await supervisor.start(request)


@app.post("/api/voice-agent-process/stop")
async def stop_voice_agent_process(
    supervisor: LocalVoiceAgentSupervisor = Depends(get_voice_agent_supervisor),
) -> VoiceAgentProcessStatusResult:
    return await supervisor.stop()


@app.get("/api/local-livekit-process")
async def get_local_livekit_process_status(
    supervisor: LocalLiveKitDevServerSupervisor = Depends(get_local_livekit_supervisor),
) -> LocalLiveKitProcessStatusResult:
    return await supervisor.status()


@app.post("/api/local-livekit-process/start")
async def start_local_livekit_process(
    request: LocalLiveKitProcessStartRequest,
    supervisor: LocalLiveKitDevServerSupervisor = Depends(get_local_livekit_supervisor),
) -> LocalLiveKitProcessStatusResult:
    return await supervisor.start(request)


@app.post("/api/local-livekit-process/stop")
async def stop_local_livekit_process(
    supervisor: LocalLiveKitDevServerSupervisor = Depends(get_local_livekit_supervisor),
) -> LocalLiveKitProcessStatusResult:
    return await supervisor.stop()


@app.get("/api/worker-scheduler-process")
async def get_worker_scheduler_process_status(
    supervisor: LocalWorkerSchedulerSupervisor = Depends(
        get_worker_scheduler_supervisor
    ),
) -> WorkerSchedulerProcessStatusResult:
    return await supervisor.status()


@app.post("/api/worker-scheduler-process/start")
async def start_worker_scheduler_process(
    request: WorkerSchedulerProcessStartRequest,
    supervisor: LocalWorkerSchedulerSupervisor = Depends(
        get_worker_scheduler_supervisor
    ),
) -> WorkerSchedulerProcessStatusResult:
    return await supervisor.start(request)


@app.post("/api/worker-scheduler-process/stop")
async def stop_worker_scheduler_process(
    supervisor: LocalWorkerSchedulerSupervisor = Depends(
        get_worker_scheduler_supervisor
    ),
) -> WorkerSchedulerProcessStatusResult:
    return await supervisor.stop()


@app.post("/api/runs/{run_id}/voice-setup-proof")
async def record_voice_setup_proof(
    run_id: UUID,
    request: VoiceSetupProofRequest,
    store: PostgresStore = Depends(get_store),
) -> VoiceSetupProofResult:
    if await store.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")

    content = {
        "workflow": "voice_setup_proof_v1",
        **request.model_dump(mode="json", exclude={"record_artifact"}),
    }
    primary_blocker = content.get("primary_blocker")
    if isinstance(primary_blocker, dict) and primary_blocker.get("label"):
        blocker_text = f"{primary_blocker['label']}: {primary_blocker.get('detail', '')}".strip()
    else:
        blocker_text = "No blocking prerequisite."
    summary = (
        request.event_summary
        or f"Voice setup `{request.action}` recorded with status `{request.status}`. {blocker_text}"
    )
    artifact: ArtifactRecord | None = None
    if request.record_artifact:
        artifact_id = uuid4()
        artifact = ArtifactRecord(
            artifact_id=artifact_id,
            run_id=run_id,
            artifact_type=ArtifactType.VOICE_SETUP_PROOF,
            title=f"Voice setup proof: {request.action}",
            uri=f"artifact://runs/{run_id}/voice-setup-proof/{artifact_id}",
            content={**content, "summary": summary},
            provenance={
                "actor": "realtime-conversation-host",
                "source": "creator_voice_panel",
                "workflow": "voice_setup_proof_v1",
            },
        )
        await store.record_artifact(artifact)

    event = await store.append_event(
        RunEvent(
            run_id=run_id,
            event_type="voice_setup_proof_recorded",
            actor="realtime-conversation-host",
            payload={
                **content,
                "summary": summary,
                "artifact_id": str(artifact.artifact_id) if artifact else None,
            },
        )
    )
    return VoiceSetupProofResult(
        run_id=run_id,
        status=request.status,
        action=request.action,
        artifact_id=artifact.artifact_id if artifact else None,
        event_id=event.event_id,
        summary=summary,
        artifact=artifact,
    )


@app.get("/api/foundation/references")
async def foundation_references() -> FoundationReferenceResult:
    return list_foundation_references()


@app.post("/api/runs")
async def create_run(
    request: RunCreateRequest, store: PostgresStore = Depends(get_store)
) -> RunState:
    run = RunState(
        goal=request.goal,
        conversation_state={
            "input_mode": request.input_mode,
            "initial_context": request.initial_context,
        },
        active_agents=["realtime-conversation-host", "intent-router"],
    )
    await store.create_run(run)
    await store.append_event(
        RunEvent(
            run_id=run.run_id,
            event_type="run_created",
            actor="realtime-conversation-host",
            payload={"goal": request.goal, "input_mode": request.input_mode},
        )
    )
    return run


@app.post("/api/demo/cockpit-run")
async def create_cockpit_demo_run(
    store: PostgresStore = Depends(get_store),
    services: ContentWorkflowServices = Depends(get_content_workflow_services),
) -> dict[str, object]:
    """Seed a provider-free run that exercises the cockpit's core surfaces."""

    now = datetime.now(timezone.utc)
    goal = (
        "Demo: source-backed OpenRouter DeepSeek LiveKit agent studio with "
        "retrieval, claim coverage, feedback, and project memory."
    )
    run = RunState(
        goal=goal,
        status=RunStatus.RUNNING,
        conversation_state={
            "input_mode": "text",
            "initial_context": {
                "cockpit_demo": True,
                "provider_keys_required": False,
                "topic": "OpenRouter DeepSeek LiveKit agent studio",
            },
        },
        active_agents=[
            "realtime-conversation-host",
            "intent-router",
            "retrieval-intelligence-agent",
            "source-ledger-agent",
            "claim-verification-agent",
            "content-strategist",
            "eli5-short-form-writer",
            "substack-essay-writer",
            "editor-in-chief",
            "interactive-note-taking-agent",
        ],
    )
    await store.create_run(run)
    await store.append_event(
        RunEvent(
            run_id=run.run_id,
            event_type="run_created",
            actor="realtime-conversation-host",
            payload={
                "goal": goal,
                "input_mode": "text",
                "cockpit_demo": True,
                "provider_keys_required": False,
            },
        )
    )

    turn = ConversationTurn(
        run_id=run.run_id,
        speaker="user",
        modality="text",
        transcript=(
            "Create grounded ELI5 post, reel, and Substack drafts about an "
            "OpenRouter DeepSeek LiveKit agent studio."
        ),
        metadata={"source": "cockpit_demo", "seeded": True},
    )
    await store.record_conversation_turn(turn)
    await store.append_event(
        RunEvent(
            run_id=run.run_id,
            event_type="conversation_turn_recorded",
            actor="realtime-conversation-host",
            payload=_safe_realtime_metadata(turn.model_dump(mode="json")),
        )
    )

    source_specs = [
        {
            "citation_id": "S1",
            "title": "OpenRouter provider routing documentation",
            "url": "https://openrouter.ai/docs/features/provider-routing",
            "publisher": "OpenRouter",
            "search_rank": 1,
            "search_query": "OpenRouter provider routing documentation",
            "retriever": "seeded_openrouter_docs",
            "coverage_topics": [
                "OpenRouter provider routing",
                "live dialogue reasoning",
            ],
            "snippet": "OpenRouter routing anchors the active live-dialogue reasoning provider path.",
        },
        {
            "citation_id": "S2",
            "title": "LiveKit turns and interruption handling",
            "url": "https://docs.livekit.io/agents/logic/turns/",
            "publisher": "LiveKit",
            "search_rank": 2,
            "search_query": "LiveKit turn detection interruption handling",
            "retriever": "seeded_livekit_docs",
            "coverage_topics": ["realtime audio", "turn detection", "barge-in"],
            "snippet": "LiveKit turn handling anchors low-latency voice dialogue, interruption, and spoken responses.",
        },
        {
            "citation_id": "S3",
            "title": "pgvector project",
            "url": "https://github.com/pgvector/pgvector",
            "publisher": "pgvector",
            "search_rank": 3,
            "search_query": "pgvector Postgres semantic memory retrieval",
            "retriever": "seeded_pgvector_docs",
            "coverage_topics": ["semantic memory", "Postgres vector retrieval"],
            "snippet": "pgvector anchors local-first semantic memory in Postgres without introducing SQLite.",
        },
    ]
    sources: list[SourceRecord] = []
    for spec in source_specs:
        source = SourceRecord(
            run_id=run.run_id,
            citation_id=spec["citation_id"],
            title=spec["title"],
            url=spec["url"],
            publisher=spec["publisher"],
            published_at=now,
            metadata={
                "source": "cockpit_demo",
                "source_type": "official_documentation",
                "search_query": spec["search_query"],
                "retriever": spec["retriever"],
                "search_rank": spec["search_rank"],
                "coverage_topics": spec["coverage_topics"],
                "snippet": spec["snippet"],
            },
        )
        await store.record_source(source)
        await store.append_event(
            RunEvent(
                run_id=run.run_id,
                event_type="source_recorded",
                actor="source-ledger-agent",
                payload=source.model_dump(mode="json"),
            )
        )
        sources.append(source)

    claims: list[ClaimRecord] = []
    claim_specs = [
        (
            "OpenRouter DeepSeek is the active live-dialogue reasoning layer, while LiveKit owns realtime transport and Kokoro owns spoken output.",
            [sources[0].source_id, sources[1].source_id],
        ),
        (
            "The durable local-first run state should use Postgres plus pgvector for source ledgers, memories, checkpoints, and semantic retrieval.",
            [sources[2].source_id],
        ),
    ]
    for claim_text, source_ids in claim_specs:
        claim = ClaimRecord(
            run_id=run.run_id,
            claim_text=claim_text,
            support_status=ClaimSupportStatus.SUPPORTED,
            source_ids=source_ids,
            reviewer_agent_id="claim-verification-agent",
            notes="Seeded demo claim with accepted source dependencies.",
        )
        await store.record_claim(claim)
        await store.append_event(
            RunEvent(
                run_id=run.run_id,
                event_type="claim_recorded",
                actor="claim-verification-agent",
                payload=claim.model_dump(mode="json"),
            )
        )
        claims.append(claim)

    claim_ids = [claim.claim_id for claim in claims]
    artifacts: list[ArtifactRecord] = []
    artifact_specs = [
        (
            ArtifactType.POST,
            "Demo LinkedIn post",
            "ELI5: the studio is a small expert newsroom where LiveKit carries the conversation, OpenRouter DeepSeek thinks through the work, Kokoro speaks back, and Postgres remembers the evidence.",
        ),
        (
            ArtifactType.REEL_SCRIPT,
            "Demo reel script",
            "Hook: Your AI content studio should talk naturally, research carefully, and remember what you approved. Cut to expert agents passing verified source cards.",
        ),
        (
            ArtifactType.SUBSTACK_ARTICLE,
            "Demo Substack article",
            "A realtime multi-agent content studio separates voice transport, expert reasoning, source retrieval, and durable memory so every draft can be traced back to evidence.",
        ),
    ]
    for artifact_type, title, draft_text in artifact_specs:
        artifact = ArtifactRecord(
            run_id=run.run_id,
            artifact_type=artifact_type,
            title=title,
            uri=f"artifact://runs/{run.run_id}/demo/{artifact_type.value}",
            content={
                "draft": draft_text,
                "summary": draft_text,
                "claim_ids": [str(claim_id) for claim_id in claim_ids],
                "claim_dependency_ids": [str(claim_id) for claim_id in claim_ids],
                "claim_trace": [
                    {
                        "claim_id": str(claim.claim_id),
                        "support_status": claim.support_status.value,
                        "source_ids": [str(source_id) for source_id in claim.source_ids],
                    }
                    for claim in claims
                ],
                "source_citations": [source.citation_id for source in sources],
                "demo_seeded": True,
            },
            provenance={
                "workflow": "cockpit_demo_seed_v1",
                "agent_id": "content-strategist",
                "model_provider": "seeded_local_demo",
                "source": "cockpit_demo",
                "claim_ids": [str(claim_id) for claim_id in claim_ids],
            },
            source_ids=[source.source_id for source in sources],
            reviewer_decisions=[
                {
                    "reviewer": "editor-in-chief",
                    "decision": "approved_with_notes",
                    "notes": "Demo artifact is source-linked and ready for cockpit inspection.",
                }
            ],
            revision_history=[
                {
                    "actor": "content-strategist",
                    "workflow": "cockpit_demo_seed_v1",
                    "note": "Seeded provider-free draft artifact for cockpit demo.",
                }
            ],
        )
        await store.record_artifact(artifact)
        await store.append_event(
            RunEvent(
                run_id=run.run_id,
                event_type="artifact_recorded",
                actor="artifact-librarian",
                payload=artifact.model_dump(mode="json"),
            )
        )
        artifacts.append(artifact)

    retrieval_quality = await RetrievalQualityLedgerWorkflow(
        store,
        services.reranker_provider,
    ).build(
        run.run_id,
        RetrievalQualityLedgerRequest(
            record_artifact=True,
            topic="OpenRouter DeepSeek LiveKit agent studio",
            candidate_window=30,
            min_accepted_sources=2,
            require_reranking=True,
            require_graph_coverage=True,
        ),
    )
    if retrieval_quality.ledger_artifact_id is not None:
        retrieval_artifacts = [
            artifact
            for artifact in await store.list_artifacts(run.run_id)
            if artifact.artifact_id == retrieval_quality.ledger_artifact_id
        ]
        if retrieval_artifacts:
            retrieval_artifact = retrieval_artifacts[0]
            retrieval_artifact.content["claim_ids"] = [
                str(claim_id) for claim_id in claim_ids
            ]
            retrieval_artifact.provenance["claim_ids"] = [
                str(claim_id) for claim_id in claim_ids
            ]
            await store.update_artifact(retrieval_artifact)

    source_ledger = await SourceLedgerWorkflow(store).build(
        run.run_id,
        SourceLedgerSnapshotRequest(
            record_artifact=True,
            include_artifact_content=False,
        ),
    )

    feedback_item = FeedbackItem(
        run_id=run.run_id,
        author="demo",
        target_agent_id="forward-deployed-engineer",
        feedback_text=(
            "Demo gate: confirm the source-ledger drilldown and recorded project "
            "memory before publishing."
        ),
        status=FeedbackStatus.OPEN,
        metadata={
            "source": "cockpit_demo",
            "gate": "demo_review_gate",
            "source_ledger_artifact_id": str(source_ledger.ledger_artifact_id),
            "retrieval_quality_artifact_id": str(retrieval_quality.ledger_artifact_id),
        },
    )
    await store.record_feedback(feedback_item)
    await store.update_run_status(run.run_id, RunStatus.WAITING_FOR_HUMAN)
    await store.append_event(
        RunEvent(
            run_id=run.run_id,
            event_type="human_feedback_gate_opened",
            actor="forward-deployed-engineer",
            payload=feedback_item.model_dump(mode="json"),
        )
    )

    project_memory = await ProjectMemoryWorkflow(store).record(
        run.run_id,
        ProjectMemoryRecordRequest(
            memory_kind=ProjectMemoryKind.PROJECT_DECISION,
            content=(
                "Demo decision: the cockpit can seed a complete provider-free run "
                "with sources, claims, artifacts, accepted evidence, feedback, and "
                "project memory for review."
            ),
            agent_id="product-manager",
            scope=ProjectMemoryScope.GLOBAL,
            confidence="high",
            tags=["cockpit-demo", "source-ledger", "project-memory"],
            source_artifact_ids=[
                artifact_id
                for artifact_id in [
                    artifacts[0].artifact_id,
                    source_ledger.ledger_artifact_id,
                ]
                if artifact_id is not None
            ],
            target_wiki_notes=[
                "wiki/product/agent-studio-memory-layer.md",
                "00-system-design/LLD - Agent Studio.md",
            ],
            metadata={"source": "cockpit_demo", "recorded_from": "demo_seed"},
        ),
    )
    final_event = await store.append_event(
        RunEvent(
            run_id=run.run_id,
            event_type="cockpit_demo_run_seeded",
            actor="product-manager",
            payload={
                "run_id": str(run.run_id),
                "source_count": len(sources),
                "claim_count": len(claims),
                "artifact_count": len(artifacts),
                "accepted_retrieval_source_count": (
                    source_ledger.accepted_retrieval_source_count
                ),
                "project_memory_id": str(project_memory.memory.memory_id),
                "feedback_id": str(feedback_item.feedback_id),
            },
        )
    )
    run.status = RunStatus.WAITING_FOR_HUMAN

    all_artifacts = await store.list_artifacts(run.run_id)
    return {
        "run": run.model_dump(mode="json"),
        "turn": turn.model_dump(mode="json"),
        "sources": [source.model_dump(mode="json") for source in sources],
        "claims": [claim.model_dump(mode="json") for claim in claims],
        "artifacts": [artifact.model_dump(mode="json") for artifact in all_artifacts],
        "retrieval_quality": retrieval_quality.model_dump(mode="json"),
        "source_ledger": source_ledger.model_dump(mode="json"),
        "feedback_item": feedback_item.model_dump(mode="json"),
        "project_memory": project_memory.model_dump(mode="json"),
        "event_id": final_event.event_id,
        "summary": (
            "Seeded a provider-free cockpit demo run with sources, claims, "
            "draft artifacts, accepted retrieval evidence, feedback, and project memory."
        ),
    }


@app.post("/api/orchestrations/content-studio")
async def run_content_studio_orchestration(
    request: OrchestrationRequest,
    store: PostgresStore = Depends(get_store),
    services: ContentWorkflowServices = Depends(get_content_workflow_services),
) -> OrchestrationResult:
    workflow = ContentStudioWorkflow(store, services)
    return await workflow.run(request)


@app.post("/api/conversation/turns")
async def route_conversation_turn(
    request: ConversationRouteRequest,
    store: PostgresStore = Depends(get_store),
    services: ContentWorkflowServices = Depends(get_content_workflow_services),
) -> ConversationRouteResult:
    router = ConversationRouter(store, services)
    try:
        return await router.route(request)
    except ConversationRouterRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    except ConversationRouterRevisionUnavailableError as exc:
        raise HTTPException(
            status_code=400, detail="No content artifacts available for revision"
        ) from exc
    except NoArtifactsToReviseError as exc:
        raise HTTPException(
            status_code=400, detail="No content artifacts available for revision"
        ) from exc


@app.post("/api/runs/{run_id}/revision-loop")
async def run_revision_loop(
    run_id: UUID,
    request: RevisionRequest,
    store: PostgresStore = Depends(get_store),
    services: ContentWorkflowServices = Depends(get_content_workflow_services),
) -> RevisionResult:
    workflow = RevisionWorkflow(store, services)
    try:
        return await workflow.run(run_id, request)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    except NoArtifactsToReviseError as exc:
        raise HTTPException(
            status_code=400, detail="No content artifacts available for revision"
        ) from exc


@app.post("/api/runs/{run_id}/media-production")
async def run_media_production(
    run_id: UUID,
    request: MediaProductionRequest,
    store: PostgresStore = Depends(get_store),
) -> MediaProductionResult:
    workflow = MediaProductionWorkflow(store)
    try:
        return await workflow.run(run_id, request)
    except MediaProductionRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    except NoArtifactsForMediaProductionError as exc:
        raise HTTPException(
            status_code=400,
            detail="No content artifacts available for media production",
        ) from exc


@app.post("/api/runs/{run_id}/multimodal-intake")
async def record_multimodal_intake(
    run_id: UUID,
    request: MultimodalIntakeRequest,
    store: PostgresStore = Depends(get_store),
) -> MultimodalIntakeResult:
    workflow = MultimodalIntakeWorkflow(store)
    try:
        return await workflow.record(run_id, request)
    except MultimodalIntakeRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.post("/api/runs/{run_id}/distribution-package")
async def build_distribution_package(
    run_id: UUID,
    request: DistributionPackageRequest,
    store: PostgresStore = Depends(get_store),
) -> DistributionPackageResult:
    workflow = DistributionPackageWorkflow(store)
    try:
        return await workflow.run(run_id, request)
    except DistributionPackageRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    except NoArtifactsForDistributionPackageError as exc:
        raise HTTPException(
            status_code=400,
            detail="No content artifacts available for distribution packaging",
        ) from exc


@app.post("/api/runs/{run_id}/growth-package")
async def build_growth_package(
    run_id: UUID,
    request: DistributionPackageRequest,
    store: PostgresStore = Depends(get_store),
) -> GrowthPackageResult:
    initiated_by_agent_id = request.initiated_by_agent_id or "product-manager"
    if get_agent_card(initiated_by_agent_id) is None:
        raise HTTPException(status_code=404, detail="Initiating agent not found")
    if await store.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    workflow = DistributionPackageWorkflow(store)
    package_request = request.model_copy(
        update={
            "created_by_agent_id": "platform-optimization-agent",
            "initiated_by_agent_id": initiated_by_agent_id,
            "include_outreach": True,
        }
    )
    artifacts = await store.list_artifacts(run_id)
    source_artifacts = _growth_package_source_artifacts(
        artifacts=artifacts,
        target_artifact_ids=package_request.target_artifact_ids,
    )
    if not source_artifacts:
        raise HTTPException(
            status_code=400,
            detail="No content artifacts available for growth packaging",
        )
    package_request = package_request.model_copy(
        update={
            "target_artifact_ids": [
                source_artifact.artifact_id for source_artifact in source_artifacts
            ]
        }
    )
    package = _current_product_growth_distribution_package(
        artifacts=artifacts,
        source_artifacts=source_artifacts,
        request=package_request,
    )
    if package is None:
        try:
            package_artifact_id = _product_growth_distribution_artifact_id(
                run_id=run_id,
                source_artifacts=source_artifacts,
                request=package_request,
            )
            distribution, recorded_package = await workflow.run_idempotent(
                run_id,
                package_request,
                artifact_id=package_artifact_id,
            )
        except DistributionPackageRunNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Run not found") from exc
        except NoArtifactsForDistributionPackageError as exc:
            raise HTTPException(
                status_code=400,
                detail="No content artifacts available for growth packaging",
            ) from exc
        artifacts = await store.list_artifacts(run_id)
        if not recorded_package:
            package = next(
                (
                    artifact
                    for artifact in artifacts
                    if artifact.artifact_id == distribution.distribution_artifact_id
                ),
                None,
            )
            if package is None:
                raise HTTPException(
                    status_code=500,
                    detail="Distribution package artifact was not persisted",
                )
            reuse_event = await store.append_event(
                RunEvent(
                    run_id=run_id,
                    event_type="distribution_package_reused",
                    actor=initiated_by_agent_id,
                    payload={
                        "distribution_artifact_id": str(package.artifact_id),
                        "source_artifact_ids": [
                            str(source_artifact.artifact_id)
                            for source_artifact in source_artifacts
                        ],
                        "platforms": distribution.platforms,
                        "initiated_by_agent_id": initiated_by_agent_id,
                        "reason": "idempotent_growth_package_conflict",
                    },
                )
            )
            distribution = distribution.model_copy(
                update={
                    "event_id": reuse_event.event_id,
                    "summary": (
                        "Reused current source-backed distribution package for "
                        "growth strategy."
                    ),
                }
            )
    else:
        platforms = _growth_distribution_package_platforms(package)
        reuse_event = await store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="distribution_package_reused",
                actor=initiated_by_agent_id,
                payload={
                    "distribution_artifact_id": str(package.artifact_id),
                    "source_artifact_ids": [
                        str(source_artifact.artifact_id)
                        for source_artifact in source_artifacts
                    ],
                    "platforms": platforms,
                    "initiated_by_agent_id": initiated_by_agent_id,
                },
            )
        )
        distribution = DistributionPackageResult(
            run_id=run_id,
            source_artifact_ids=[
                source_artifact.artifact_id for source_artifact in source_artifacts
            ],
            distribution_artifact_id=package.artifact_id,
            platforms=platforms,
            event_id=reuse_event.event_id,
            summary=(
                "Reused current source-backed distribution package for growth "
                "strategy."
            ),
        )

    artifact_by_id = {artifact.artifact_id: artifact for artifact in artifacts}
    package = artifact_by_id.get(distribution.distribution_artifact_id)
    if package is None:
        raise HTTPException(
            status_code=500,
            detail="Distribution package artifact was not persisted",
        )
    source_artifacts = [
        artifact_by_id[artifact_id]
        for artifact_id in distribution.source_artifact_ids
        if artifact_id in artifact_by_id
    ]
    if not source_artifacts:
        raise HTTPException(
            status_code=500,
            detail="Distribution package source artifacts were not persisted",
        )

    influencer_message_id, influencer_strategy_id = (
        await _record_product_growth_strategy(
            store=store,
            run_id=run_id,
            package=package,
            source_artifacts=source_artifacts,
            sender_agent_id=initiated_by_agent_id,
            recipient_agent_id="influencer-strategy-agent",
            task_type="plan_keywords_and_hashtags",
            event_type="influencer_strategy_recorded",
            reused_event_type="influencer_strategy_reused",
            build_artifact=_build_influencer_strategy_artifact,
        )
    )
    outreach_message_id, outreach_strategy_id = await _record_product_growth_strategy(
        store=store,
        run_id=run_id,
        package=package,
        source_artifacts=source_artifacts,
        sender_agent_id=initiated_by_agent_id,
        recipient_agent_id="outreach-agent",
        task_type="plan_outreach_angles",
        event_type="outreach_strategy_recorded",
        reused_event_type="outreach_strategy_reused",
        build_artifact=_build_outreach_strategy_artifact,
    )
    event = await store.append_event(
        RunEvent(
            run_id=run_id,
            event_type="growth_package_built",
            actor=initiated_by_agent_id,
            payload={
                "distribution_artifact_id": str(distribution.distribution_artifact_id),
                "strategy_artifact_ids": [
                    str(influencer_strategy_id),
                    str(outreach_strategy_id),
                ],
                "agent_message_ids": [
                    str(influencer_message_id),
                    str(outreach_message_id),
                ],
                "platforms": distribution.platforms,
                "initiated_by_agent_id": initiated_by_agent_id,
            },
        )
    )
    return GrowthPackageResult(
        run_id=run_id,
        source_artifact_ids=distribution.source_artifact_ids,
        distribution_artifact_id=distribution.distribution_artifact_id,
        platforms=distribution.platforms,
        influencer_strategy_artifact_id=influencer_strategy_id,
        outreach_strategy_artifact_id=outreach_strategy_id,
        strategy_artifact_ids=[influencer_strategy_id, outreach_strategy_id],
        agent_message_ids=[influencer_message_id, outreach_message_id],
        event_id=event.event_id,
        summary=(
            "Created growth package with platform distribution, influencer "
            "strategy, and outreach strategy artifacts."
        ),
    )


@app.post("/api/runs/{run_id}/autonomous-pass")
async def run_autonomous_studio_pass(
    run_id: UUID,
    request: AutonomousStudioPassRequest,
    store: PostgresStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
    services: ContentWorkflowServices = Depends(get_content_workflow_services),
    provider_factory=Depends(get_realtime_provider_factory),
) -> AutonomousStudioPassResult:
    workflow = AutonomousStudioPassWorkflow(
        store,
        artifacts_root=_resolve_artifacts_root(settings),
        services=services,
        obsidian_vault_path=settings.obsidian_vault_path,
        settings=settings,
        realtime_provider_factory=provider_factory,
    )
    try:
        return await workflow.run(run_id, request)
    except AutonomousStudioPassRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.post("/api/runs/{run_id}/guardrail-audit")
async def run_guardrail_audit(
    run_id: UUID,
    request: GuardrailAuditRequest,
    store: PostgresStore = Depends(get_store),
) -> GuardrailAuditResult:
    workflow = GuardrailAuditWorkflow(store)
    try:
        return await workflow.run(run_id, request)
    except GuardrailAuditRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    except NoArtifactsToAuditError as exc:
        raise HTTPException(
            status_code=400, detail="No artifacts available for audit"
        ) from exc


@app.post("/api/a2a/messages")
async def send_agent_message(
    message: AgentMessage, store: PostgresStore = Depends(get_store)
) -> AgentMessageResponse:
    if get_agent_card(message.sender_agent_id) is None:
        raise HTTPException(status_code=404, detail="Sender agent not found")
    if get_agent_card(message.recipient_agent_id) is None:
        raise HTTPException(status_code=404, detail="Recipient agent not found")
    if await store.get_run(message.run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")

    await store.record_agent_message(message)
    event = await store.append_event(
        RunEvent(
            run_id=message.run_id,
            event_type="agent_message_accepted",
            actor=message.sender_agent_id,
            payload=public_a2a_message_event_payload(message),
        )
    )
    if message.requires_human_feedback:
        await store.update_run_status(message.run_id, RunStatus.WAITING_FOR_HUMAN)
        await store.append_event(
            RunEvent(
                run_id=message.run_id,
                event_type="human_feedback_gate_opened",
                actor=message.recipient_agent_id,
                payload={"message_id": str(message.message_id)},
            )
        )
    return AgentMessageResponse(
        message_id=message.message_id,
        run_id=message.run_id,
        accepted=True,
        recipient_agent_id=message.recipient_agent_id,
        event_id=event.event_id,
        status="accepted",
    )


@app.get("/api/runs/{run_id}/agent-messages")
async def get_run_agent_messages(
    run_id: UUID,
    agent_id: str | None = None,
    direction: str = "all",
    status: AgentTaskStatus | None = None,
    projection: str = "private",
    store: PostgresStore = Depends(get_store),
) -> dict[str, object]:
    if direction not in {"all", "inbox", "outbox"}:
        raise HTTPException(status_code=400, detail="Invalid message direction")
    if projection not in {"private", "public"}:
        raise HTTPException(status_code=400, detail="Invalid A2A message projection")
    if await store.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    messages = await store.list_agent_messages(
        run_id,
        agent_id=agent_id,
        direction=direction,
        status=status,
    )
    if projection == "public":
        return {
            "messages": [
                _public_a2a_message_projection(message).model_dump(mode="json")
                for message in messages
            ],
            "projection": "public",
        }
    return {
        "messages": [message.model_dump(mode="json") for message in messages],
        "projection": "private",
    }


@app.get("/api/a2a/messages/{message_id}")
async def get_a2a_agent_message(
    message_id: UUID,
    projection: str = "private",
    store: PostgresStore = Depends(get_store),
) -> AgentMessageDetailResponse:
    if projection not in {"private", "public"}:
        raise HTTPException(status_code=400, detail="Invalid A2A message projection")
    message = await store.get_agent_message(message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Agent message not found")
    if projection == "public":
        return AgentMessageDetailResponse(
            message=_public_a2a_message_projection(message),
            projection="public",
        )
    return AgentMessageDetailResponse(message=message, projection="private")


def _public_a2a_message_projection(message: AgentMessage) -> AgentMessagePublicProjection:
    return public_a2a_message_projection(message)


@app.get("/api/a2a/agents/{agent_id}/inbox")
async def get_agent_inbox(
    agent_id: str,
    run_id: UUID,
    status: AgentTaskStatus | None = AgentTaskStatus.ACCEPTED,
    projection: str = "private",
    store: PostgresStore = Depends(get_store),
) -> dict[str, object]:
    if get_agent_card(agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    if projection not in {"private", "public"}:
        raise HTTPException(status_code=400, detail="Invalid A2A message projection")
    if await store.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    messages = await store.list_agent_messages(
        run_id,
        agent_id=agent_id,
        direction="inbox",
        status=status,
    )
    if projection == "public":
        return {
            "messages": [
                _public_a2a_message_projection(message).model_dump(mode="json")
                for message in messages
            ],
            "projection": "public",
        }
    return {
        "messages": [message.model_dump(mode="json") for message in messages],
        "projection": "private",
    }


@app.post("/api/a2a/messages/{message_id}/status")
async def update_agent_message_status(
    message_id: UUID,
    request: AgentMessageStatusUpdate,
    store: PostgresStore = Depends(get_store),
) -> AgentMessageStatusResponse:
    if get_agent_card(request.agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    message = await store.get_agent_message(message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Agent message not found")
    if request.agent_id not in {
        message.sender_agent_id,
        message.recipient_agent_id,
        message.claimed_by_agent_id,
    }:
        raise HTTPException(status_code=403, detail="Agent cannot update this message")

    updated_message = await store.update_agent_message_status(
        message_id=message_id,
        status=request.status,
        agent_id=request.agent_id,
        result=request.result,
        notes=request.notes,
        error=request.error,
    )
    if updated_message is None:
        raise HTTPException(status_code=404, detail="Agent message not found")

    if request.status in {AgentTaskStatus.WAITING_FOR_HUMAN, AgentTaskStatus.BLOCKED}:
        await store.update_run_status(message.run_id, RunStatus.WAITING_FOR_HUMAN)

    event = await store.append_event(
        RunEvent(
            run_id=message.run_id,
            event_type="agent_message_status_updated",
            actor=request.agent_id,
            payload=public_a2a_status_event_payload(
                message=message,
                from_status=message.status,
                to_status=request.status,
                notes=request.notes,
                has_result=bool(request.result),
                has_error=request.error is not None,
            ),
        )
    )
    return AgentMessageStatusResponse(message=updated_message, event_id=event.event_id)


@app.post("/api/a2a/messages/{message_id}/retry")
async def authorize_agent_message_retry(
    message_id: UUID,
    request: AgentMessageRetryRequest,
    store: PostgresStore = Depends(get_store),
) -> AgentMessageRetryResponse:
    if get_agent_card(request.agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    message = await store.get_agent_message(message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Agent message not found")
    if request.agent_id not in {
        message.sender_agent_id,
        message.recipient_agent_id,
        message.claimed_by_agent_id,
        "agent-harness-engineer",
        "forward-deployed-engineer",
        "product-manager",
    }:
        raise HTTPException(
            status_code=403,
            detail="Agent cannot authorize retry for this message",
        )
    if message.status not in {
        AgentTaskStatus.BLOCKED,
        AgentTaskStatus.FAILED,
        AgentTaskStatus.CANCELED,
    }:
        raise HTTPException(
            status_code=400,
            detail="Only blocked, failed, or canceled messages can be retried",
        )

    previous_status = message.status
    previous_attempt_count = message.attempt_count
    previous_max_attempts = message.max_attempts
    updated_message = await store.authorize_agent_message_retry(
        message_id,
        agent_id=request.agent_id,
        reason=request.reason,
        reset_attempt_count=request.reset_attempt_count,
        max_attempts=request.max_attempts,
    )
    if updated_message is None:
        raise HTTPException(status_code=404, detail="Agent message not found")
    await store.update_run_status(message.run_id, RunStatus.RUNNING)
    event = await store.append_event(
        RunEvent(
            run_id=message.run_id,
            event_type="agent_message_retry_authorized",
            actor=request.agent_id,
            payload=public_a2a_retry_event_payload(
                message=message,
                from_status=previous_status,
                to_status=updated_message.status,
                previous_attempt_count=previous_attempt_count,
                attempt_count=updated_message.attempt_count,
                previous_max_attempts=previous_max_attempts,
                max_attempts=updated_message.max_attempts,
                reset_attempt_count=request.reset_attempt_count,
                reason=request.reason,
            ),
        )
    )
    return AgentMessageRetryResponse(
        message=updated_message,
        event_id=event.event_id,
        summary=(
            f"Retry authorized for {message.recipient_agent_id} task "
            f"{message.task_type}."
        ),
    )


@app.post("/api/a2a/messages/{message_id}/dependencies/repair")
async def repair_agent_message_dependencies(
    message_id: UUID,
    request: AgentMessageDependencyRepairRequest,
    store: PostgresStore = Depends(get_store),
) -> AgentMessageDependencyRepairResponse:
    if get_agent_card(request.agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    message = await store.get_agent_message(message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Agent message not found")
    if request.agent_id not in {
        message.sender_agent_id,
        message.recipient_agent_id,
        message.claimed_by_agent_id,
        "agent-harness-engineer",
        "forward-deployed-engineer",
        "product-manager",
        "a2a-protocol-agent",
    }:
        raise HTTPException(
            status_code=403,
            detail="Agent cannot repair dependencies for this message",
        )

    requested_dependency_ids = set(request.remove_dependency_message_ids)
    removed_dependency_ids = [
        dependency_id
        for dependency_id in message.depends_on_message_ids
        if dependency_id in requested_dependency_ids
    ]
    if not removed_dependency_ids:
        raise HTTPException(
            status_code=400,
            detail="No requested dependency ids are attached to this message",
        )

    updated_message = await store.repair_agent_message_dependencies(
        message_id,
        agent_id=request.agent_id,
        remove_dependency_message_ids=request.remove_dependency_message_ids,
        reason=request.reason,
    )
    if updated_message is None:
        raise HTTPException(status_code=404, detail="Agent message not found")

    remaining_dependency_ids = updated_message.depends_on_message_ids
    await store.update_run_status(message.run_id, RunStatus.RUNNING)
    event = await store.append_event(
        RunEvent(
            run_id=message.run_id,
            event_type="agent_message_dependencies_repaired",
            actor=request.agent_id,
            payload=public_a2a_dependency_repair_event_payload(
                message=message,
                removed_dependency_message_ids=removed_dependency_ids,
                remaining_dependency_message_ids=remaining_dependency_ids,
                reason=request.reason,
            ),
        )
    )
    return AgentMessageDependencyRepairResponse(
        message=updated_message,
        removed_dependency_message_ids=removed_dependency_ids,
        remaining_dependency_message_ids=remaining_dependency_ids,
        event_id=event.event_id,
        summary=(
            f"Repaired {len(removed_dependency_ids)} dependencies for "
            f"{message.recipient_agent_id} task {message.task_type}."
        ),
    )


@app.post("/api/a2a/workers/{agent_id}/run")
async def run_agent_worker(
    agent_id: str,
    request: AgentWorkerRunRequest,
    store: PostgresStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
    services: ContentWorkflowServices = Depends(get_content_workflow_services),
) -> AgentWorkerRunResult:
    worker = AgentWorker(
        store,
        services,
        artifacts_root=_resolve_artifacts_root(settings),
        obsidian_vault_path=settings.obsidian_vault_path,
    )
    try:
        return await worker.run(agent_id, request)
    except AgentWorkerAgentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Agent not found") from exc
    except AgentWorkerRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.post("/api/a2a/workers/run-cycle")
async def run_agent_worker_cycle(
    request: AgentWorkerCycleRequest,
    store: PostgresStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
    services: ContentWorkflowServices = Depends(get_content_workflow_services),
) -> AgentWorkerCycleResult:
    worker = AgentWorker(
        store,
        services,
        artifacts_root=_resolve_artifacts_root(settings),
        obsidian_vault_path=settings.obsidian_vault_path,
    )
    try:
        return await worker.run_cycle(request)
    except AgentWorkerAgentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AgentWorkerRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.post("/api/runs/{run_id}/worker-profiles")
async def create_worker_profile(
    run_id: UUID,
    request: WorkerProfileCreate,
    store: PostgresStore = Depends(get_store),
) -> WorkerProfile:
    if await store.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    for agent_id in request.agent_ids:
        if get_agent_card(agent_id) is None:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    if (
        request.autonomous_memory_summary_agent_id is not None
        and get_agent_card(request.autonomous_memory_summary_agent_id) is None
    ):
        raise HTTPException(
            status_code=404,
            detail=(
                "Agent not found: "
                f"{request.autonomous_memory_summary_agent_id}"
            ),
        )
    profile = WorkerProfile(run_id=run_id, **request.model_dump())
    await store.record_worker_profile(profile)
    await store.append_event(
        RunEvent(
            run_id=run_id,
            event_type="worker_profile_created",
            actor="agent-harness-engineer",
            payload=profile.model_dump(mode="json"),
        )
    )
    return profile


@app.get("/api/runs/{run_id}/worker-profiles")
async def list_worker_profiles(
    run_id: UUID,
    store: PostgresStore = Depends(get_store),
) -> dict[str, object]:
    if await store.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    profiles = await store.list_worker_profiles(run_id)
    return {"profiles": [profile.model_dump(mode="json") for profile in profiles]}


@app.post("/api/worker-profiles/{profile_id}/status")
async def update_worker_profile_status(
    profile_id: UUID,
    request: WorkerProfileStatusUpdate,
    store: PostgresStore = Depends(get_store),
) -> WorkerProfile:
    profile = await store.update_worker_profile_status(profile_id, request.status)
    if profile is None:
        raise HTTPException(status_code=404, detail="Worker profile not found")
    await store.append_event(
        RunEvent(
            run_id=profile.run_id,
            event_type=f"worker_profile_{profile.status.value}",
            actor="agent-harness-engineer",
            payload=profile.model_dump(mode="json"),
        )
    )
    return profile


@app.post("/api/worker-profiles/{profile_id}/start")
async def start_worker_profile(
    profile_id: UUID,
    store: PostgresStore = Depends(get_store),
) -> WorkerProfile:
    return await update_worker_profile_status(
        profile_id,
        WorkerProfileStatusUpdate(status=WorkerProfileStatus.ACTIVE),
        store,
    )


@app.post("/api/worker-profiles/{profile_id}/stop")
async def stop_worker_profile(
    profile_id: UUID,
    store: PostgresStore = Depends(get_store),
) -> WorkerProfile:
    return await update_worker_profile_status(
        profile_id,
        WorkerProfileStatusUpdate(status=WorkerProfileStatus.STOPPED),
        store,
    )


@app.post("/api/worker-profiles/{profile_id}/heartbeat")
async def heartbeat_worker_profile(
    profile_id: UUID,
    store: PostgresStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
    services: ContentWorkflowServices = Depends(get_content_workflow_services),
) -> WorkerProfileHeartbeatResult:
    worker = AgentWorker(
        store,
        services,
        artifacts_root=_resolve_artifacts_root(settings),
        obsidian_vault_path=settings.obsidian_vault_path,
    )
    try:
        return await worker.run_profile_heartbeat(profile_id)
    except WorkerProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Worker profile not found") from exc


@app.post("/api/runs/{run_id}/autopilot-launch")
async def launch_run_autopilot(
    run_id: UUID,
    request: AutopilotLaunchRequest,
    store: PostgresStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
    services: ContentWorkflowServices = Depends(get_content_workflow_services),
) -> AutopilotLaunchResult:
    worker = AgentWorker(
        store,
        services,
        artifacts_root=_resolve_artifacts_root(settings),
        obsidian_vault_path=settings.obsidian_vault_path,
    )
    try:
        return await AutopilotLaunchWorkflow(store, worker).launch(run_id, request)
    except AutopilotLaunchAgentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AutopilotLaunchRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.post("/api/worker-profiles/scheduler/run")
async def run_worker_profile_scheduler(
    request: WorkerSchedulerRunRequest,
    store: PostgresStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
    services: ContentWorkflowServices = Depends(get_content_workflow_services),
) -> WorkerSchedulerRunResult:
    worker = AgentWorker(
        store,
        services,
        artifacts_root=_resolve_artifacts_root(settings),
        obsidian_vault_path=settings.obsidian_vault_path,
    )
    return await worker.run_due_profile_scheduler(request)


@app.get("/api/runs/{run_id}")
async def get_run(run_id: UUID, store: PostgresStore = Depends(get_store)) -> RunState:
    run = await store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@app.post("/api/runs/{run_id}/checkpoints")
async def create_run_checkpoint(
    run_id: UUID,
    request: RunCheckpointCreate,
    store: PostgresStore = Depends(get_store),
) -> RunCheckpointResult:
    workflow = RunResumeWorkflow(store)
    try:
        return await workflow.create_checkpoint(run_id, request)
    except RunResumeRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.get("/api/runs/{run_id}/checkpoints")
async def list_run_checkpoints(
    run_id: UUID,
    limit: int = Query(default=25, ge=1, le=100),
    store: PostgresStore = Depends(get_store),
) -> dict[str, object]:
    workflow = RunResumeWorkflow(store)
    try:
        checkpoints = await workflow.list_checkpoints(run_id, limit=limit)
    except RunResumeRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    return {
        "checkpoints": [
            checkpoint.model_dump(mode="json") for checkpoint in checkpoints
        ]
    }


@app.post("/api/runs/{run_id}/resume-plan")
async def build_run_resume_plan(
    run_id: UUID,
    request: RunResumePlanRequest,
    store: PostgresStore = Depends(get_store),
) -> RunResumePlan:
    if request.agent_id and get_agent_card(request.agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    workflow = RunResumeWorkflow(store)
    try:
        return await workflow.build_resume_plan(run_id, request)
    except RunResumeRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.post("/api/runs/{run_id}/resume")
async def resume_run(
    run_id: UUID,
    request: RunResumeRequest,
    store: PostgresStore = Depends(get_store),
    services: ContentWorkflowServices = Depends(get_content_workflow_services),
) -> RunResumeResult:
    if request.agent_id and get_agent_card(request.agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    for agent_id in request.agent_ids:
        if get_agent_card(agent_id) is None:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    workflow = RunResumeWorkflow(store)
    try:
        return await workflow.resume_run(run_id, request, services)
    except RunResumeRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    except AgentWorkerAgentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/runs/{run_id}/replay-ledger")
async def build_run_replay_ledger(
    run_id: UUID,
    request: RunReplayLedgerRequest,
    store: PostgresStore = Depends(get_store),
) -> RunReplayLedgerResult:
    workflow = RunReplayLedgerWorkflow(store)
    try:
        return await workflow.build(run_id, request)
    except RunReplayLedgerRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    except RunReplayLedgerCheckpointNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Checkpoint not found") from exc


@app.post("/api/runs/{run_id}/work-plan")
async def build_run_work_plan(
    run_id: UUID,
    request: RunWorkPlanRequest,
    store: PostgresStore = Depends(get_store),
) -> RunWorkPlanResult:
    workflow = RunWorkPlanWorkflow(store)
    try:
        return await workflow.build(run_id, request)
    except RunWorkPlanRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.post("/api/runs/{run_id}/sync-pulse")
async def build_run_sync_pulse(
    run_id: UUID,
    request: RunSyncPulseRequest,
    store: PostgresStore = Depends(get_store),
) -> RunSyncPulseResult:
    workflow = RunSyncPulseWorkflow(store)
    try:
        return await workflow.build(run_id, request)
    except RunSyncPulseRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.post("/api/runs/{run_id}/context-packet")
async def build_run_context_packet(
    run_id: UUID,
    request: RunContextPacketRequest,
    store: PostgresStore = Depends(get_store),
) -> RunContextPacket:
    run = await store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if request.agent_id and get_agent_card(request.agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    memory_results = await store.search_memories(
        agent_id=request.agent_id,
        run_id=run_id,
        include_global_memories=request.include_global_memories,
        query_embedding=request.query_embedding,
        limit=request.memory_limit,
    )
    project_memory_retrieval = None
    if request.include_project_memory_retrieval:
        project_memory_retrieval = await ProjectMemoryRetrievalWorkflow(
            store
        ).retrieve(
            run_id,
            ProjectMemoryRetrievalRequest(
                query=request.project_memory_query or run.goal,
                agent_id=request.agent_id,
                query_embedding=request.query_embedding,
                include_global_memories=request.include_global_memories,
                seed_limit=request.project_memory_seed_limit,
                memory_limit=request.project_memory_retrieval_limit,
                graph_depth=request.project_memory_graph_depth,
                record_artifact=False,
            ),
        )
    recent_events = await store.list_events(
        run_id,
        limit=request.event_limit,
        latest=True,
    )
    packet = RunContextPacket(
        run=run,
        conversation_turns=await store.list_conversation_turns(run_id),
        agent_messages=await store.list_agent_messages(run_id, agent_id=request.agent_id),
        recent_events=recent_events,
        sources=await store.list_sources(run_id),
        claims=await store.list_claims(run_id),
        artifacts=await store.list_artifacts(run_id),
        guardrail_audits=await store.list_guardrail_audits(run_id),
        feedback_items=await store.list_feedback(run_id),
        memories=[
            MemorySearchResult(memory=memory, distance=distance)
            for memory, distance in memory_results
        ],
        summary={},
    )
    context_payload = build_context_engineering_payload(
        run=packet.run,
        conversation_turns=packet.conversation_turns,
        agent_messages=packet.agent_messages,
        recent_events=packet.recent_events,
        sources=packet.sources,
        claims=packet.claims,
        artifacts=packet.artifacts,
        guardrail_audits=packet.guardrail_audits,
        feedback_items=packet.feedback_items,
        memories=packet.memories,
        agent_id=request.agent_id,
        max_manifest_items=request.max_manifest_items,
        max_context_tokens=request.max_context_tokens,
        project_memory_retrieval=project_memory_retrieval_digest(
            project_memory_retrieval
        ),
    )
    packet.context_manifest = context_payload["context_manifest"]
    packet.context_risks = context_payload["context_risks"]
    packet.recommended_fetches = context_payload["recommended_fetches"]
    packet.source_evidence = context_payload["source_evidence"]
    packet.summary.update(
        {
            "run_id": str(run_id),
            "agent_id": request.agent_id,
            "skill_ids": (
                [
                    skill.id
                    for skill in skill_cards_for_agent(request.agent_id)
                ]
                if request.agent_id
                else []
            ),
            "conversation_turns": len(packet.conversation_turns),
            "agent_messages": len(packet.agent_messages),
            "sources": len(packet.sources),
            "claims": len(packet.claims),
            "artifacts": len(packet.artifacts),
            "guardrail_audits": len(packet.guardrail_audits),
            "feedback_items": len(packet.feedback_items),
            "memories": len(packet.memories),
        }
    )
    packet.summary.update(context_payload["summary"])
    if request.record_event:
        await store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="context_packet_built",
                actor=request.agent_id or "context-engineering-agent",
                payload=public_a2a_context_packet_event_payload(packet.summary),
            )
        )
    return packet


@app.post("/api/runs/{run_id}/conversation-turns")
async def record_conversation_turn(
    run_id: UUID,
    request: ConversationTurnCreate,
    store: PostgresStore = Depends(get_store),
) -> ConversationTurn:
    if await store.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    turn = ConversationTurn(run_id=run_id, **request.model_dump())
    await store.record_conversation_turn(turn)
    await store.append_event(
        RunEvent(
            run_id=run_id,
            event_type="conversation_turn_recorded",
            actor=request.speaker,
            payload=_safe_realtime_metadata(turn.model_dump(mode="json")),
        )
    )
    return turn


@app.get("/api/runs/{run_id}/conversation-turns")
async def get_conversation_turns(
    run_id: UUID, store: PostgresStore = Depends(get_store)
) -> dict[str, object]:
    turns = await store.list_conversation_turns(run_id)
    return {"turns": [turn.model_dump(mode="json") for turn in turns]}


@app.post("/api/runs/{run_id}/human-feedback-gate")
async def open_human_feedback_gate(
    run_id: UUID, store: PostgresStore = Depends(get_store)
) -> dict[str, object]:
    if await store.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    feedback = FeedbackItem(
        run_id=run_id,
        author="system",
        target_agent_id="forward-deployed-engineer",
        feedback_text="Human approval or correction is required before continuing.",
        metadata={"gate": "manual", "source": "human_feedback_gate_endpoint"},
    )
    await store.record_feedback(feedback)
    await store.update_run_status(run_id, RunStatus.WAITING_FOR_HUMAN)
    event = await store.append_event(
        RunEvent(
            run_id=run_id,
            event_type="human_feedback_gate_opened",
            actor="forward-deployed-engineer",
            payload={"feedback_id": str(feedback.feedback_id)},
        )
    )
    return {
        "run_id": run_id,
        "status": RunStatus.WAITING_FOR_HUMAN,
        "feedback_item": feedback.model_dump(mode="json"),
        "event_id": event.event_id,
    }


@app.post("/api/runs/{run_id}/realtime-session")
async def create_realtime_session(
    run_id: UUID,
    request: RealtimeSessionCreateRequest,
    store: PostgresStore = Depends(get_store),
    provider_factory=Depends(get_realtime_provider_factory),
) -> RealtimeSessionCreateResult:
    run = await store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    provider_name = request.provider or "default"
    instructions = request.instructions or _default_realtime_instructions(run.goal)
    audio_mode = str(request.metadata.get("audio_mode") or "speech_to_speech")
    requested_room_name = request.room_name or f"agent-studio-{run_id}"
    requested_participant_identity = (
        request.participant_identity or f"creator-{run_id}"
    )
    requested_agent_identity = (
        request.agent_participant_identity or f"gemma4-kokoro-agent-{run_id}"
    )
    realtime_session_id = uuid4()
    if request.dry_run:
        transport = RealtimeTransportGrant(
            framework=request.transport_framework or "local_rehearsal",
            room_name=requested_room_name,
            participant_identity=requested_participant_identity,
            agent_identity=requested_agent_identity,
            has_token=False,
            token_persisted=False,
            metadata={"purpose": "provider_free_realtime_dialogue_rehearsal"},
        )
        realtime_metadata = _safe_realtime_metadata(
            {
                **request.metadata,
                "dry_run": True,
                "not_provider_backed": True,
                "provider_under_test": provider_name,
                "transport": _safe_transport_payload(transport),
                "transport_framework": transport.framework,
                "room_name": transport.room_name,
                "participant_identity": transport.participant_identity,
                "agent_participant_identity": transport.agent_identity,
                "has_transport_token": transport.has_token,
                "context_window_turns": request.context_window_turns,
                "summarize_after_turns": request.summarize_after_turns,
                "purpose": "provider_free_realtime_dialogue_rehearsal",
                "latency_class": "realtime_interrupt",
                "smoke_proof_status": "rehearsal_only",
            }
        )
        session_record = RealtimeSessionRecord(
            run_id=run_id,
            provider="local_realtime_rehearsal",
            provider_session_id=f"rehearsal-{run_id}",
            voice=request.voice,
            audio_mode=audio_mode,
            instructions=instructions,
            has_client_secret=False,
            has_websocket_url=False,
            transport_framework=transport.framework,
            room_name=transport.room_name,
            participant_identity=transport.participant_identity,
            agent_participant_identity=transport.agent_identity,
            has_transport_token=transport.has_token,
            context_window_turns=request.context_window_turns,
            summarize_after_turns=request.summarize_after_turns,
            metadata=realtime_metadata,
        )
        await store.record_realtime_session(session_record)
        event = await store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="realtime_rehearsal_session_created",
                actor="realtime-conversation-host",
                payload={
                    "realtime_session_id": str(session_record.realtime_session_id),
                    "provider": session_record.provider,
                    "provider_under_test": provider_name,
                    "voice": request.voice,
                    "audio_mode": audio_mode,
                    "dry_run": True,
                    "not_provider_backed": True,
                    "transport": _safe_transport_payload(transport),
                    "latency_class": "realtime_interrupt",
                    "smoke_proof_status": "rehearsal_only",
                    "metadata": session_record.metadata,
                },
            )
        )
        return RealtimeSessionCreateResult(
            run_id=run_id,
            realtime_session_id=session_record.realtime_session_id,
            provider=session_record.provider,
            session_id=session_record.provider_session_id,
            transport=transport,
            event_id=event.event_id,
            metadata=session_record.metadata,
        )

    provider = provider_factory(request.provider)
    provider_started = time.perf_counter()
    try:
        provider_response = await provider.create_session(
            RealtimeSessionRequest(
                provider=provider_name,
                run_id=str(run_id),
                voice=request.voice,
                instructions=instructions,
                metadata={
                    **request.metadata,
                    "transport_framework": request.transport_framework,
                    "room_name": requested_room_name,
                    "participant_identity": requested_participant_identity,
                    "agent_participant_identity": requested_agent_identity,
                    "realtime_session_id": str(realtime_session_id),
                    "context_window_turns": request.context_window_turns,
                    "summarize_after_turns": request.summarize_after_turns,
                },
            )
        )
        provider_latency_ms = round((time.perf_counter() - provider_started) * 1000, 3)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ProviderConfigurationError as exc:
        provider_latency_ms = round((time.perf_counter() - provider_started) * 1000, 3)
        safe_reason = _redact_realtime_string(str(exc))
        await store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="realtime_session_configuration_failed",
                actor="realtime-conversation-host",
                payload={
                    "provider": provider_name,
                    "reason": safe_reason,
                    "voice": request.voice,
                    "latency_class": "realtime_interrupt",
                    "provider_latency_ms": provider_latency_ms,
                    "smoke_proof_status": "configuration_failed",
                },
            )
        )
        raise HTTPException(status_code=503, detail=safe_reason) from exc

    transport = _transport_grant_from_provider_response(
        provider_response=provider_response,
        request=request,
        run_id=run_id,
        default_room_name=requested_room_name,
        default_participant_identity=requested_participant_identity,
        default_agent_identity=requested_agent_identity,
    )
    realtime_metadata = _safe_realtime_metadata(
        {
            **provider_response.metadata,
            "transport": _safe_transport_payload(transport),
            "transport_framework": transport.framework,
            "room_name": transport.room_name,
            "participant_identity": transport.participant_identity,
            "agent_participant_identity": transport.agent_identity,
            "has_transport_token": transport.has_token,
            "context_window_turns": request.context_window_turns,
            "summarize_after_turns": request.summarize_after_turns,
            "latency_class": "realtime_interrupt",
            "provider_latency_ms": provider_latency_ms,
            "smoke_proof_status": "provider_backed",
        }
    )
    session_record = RealtimeSessionRecord(
        realtime_session_id=realtime_session_id,
        run_id=run_id,
        provider=provider_response.provider,
        provider_session_id=provider_response.session_id,
        voice=request.voice,
        audio_mode=audio_mode,
        instructions=instructions,
        has_client_secret=provider_response.client_secret is not None,
        has_websocket_url=provider_response.websocket_url is not None,
        transport_framework=transport.framework,
        room_name=transport.room_name,
        participant_identity=transport.participant_identity,
        agent_participant_identity=transport.agent_identity,
        has_transport_token=transport.has_token,
        context_window_turns=request.context_window_turns,
        summarize_after_turns=request.summarize_after_turns,
        expires_at_unix=provider_response.expires_at_unix,
        metadata=realtime_metadata,
    )
    await store.record_realtime_session(session_record)
    event = await store.append_event(
        RunEvent(
            run_id=run_id,
            event_type="realtime_session_created",
            actor="realtime-conversation-host",
            payload={
                "realtime_session_id": str(session_record.realtime_session_id),
                "provider": provider_response.provider,
                "session_id": provider_response.session_id,
                "voice": request.voice,
                "audio_mode": audio_mode,
                "has_client_secret": provider_response.client_secret is not None,
                "has_websocket_url": provider_response.websocket_url is not None,
                "transport": _safe_transport_payload(transport),
                "expires_at_unix": provider_response.expires_at_unix,
                "latency_class": "realtime_interrupt",
                "provider_latency_ms": provider_latency_ms,
                "smoke_proof_status": "provider_backed",
                "metadata": realtime_metadata,
            },
        )
    )
    return RealtimeSessionCreateResult(
        run_id=run_id,
        realtime_session_id=session_record.realtime_session_id,
        provider=provider_response.provider,
        session_id=provider_response.session_id,
        client_secret=provider_response.client_secret,
        websocket_url=provider_response.websocket_url,
        transport=transport,
        expires_at_unix=provider_response.expires_at_unix,
        event_id=event.event_id,
        metadata=realtime_metadata,
    )


@app.get("/api/runs/{run_id}/realtime-sessions")
async def get_run_realtime_sessions(
    run_id: UUID,
    store: PostgresStore = Depends(get_store),
) -> dict[str, object]:
    if await store.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    sessions = await store.list_realtime_sessions(run_id)
    return {"sessions": [session.model_dump(mode="json") for session in sessions]}


@app.get("/api/runs/{run_id}/voice-agent-presence")
async def get_run_voice_agent_presence(
    run_id: UUID,
    realtime_session_id: UUID | None = Query(default=None),
    probe_id: str | None = Query(default=None, min_length=1),
    stale_after_seconds: int = Query(default=60, ge=5, le=3600),
    store: PostgresStore = Depends(get_store),
) -> VoiceAgentPresenceResult:
    if await store.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    sessions = await store.list_realtime_sessions(run_id)
    if realtime_session_id is not None and not any(
        session.realtime_session_id == realtime_session_id for session in sessions
    ):
        raise HTTPException(status_code=404, detail="Realtime session not found")
    events = await store.list_events(run_id, limit=1000)
    return _build_voice_agent_presence(
        run_id=run_id,
        sessions=sessions,
        events=events,
        realtime_session_id=realtime_session_id,
        probe_id=probe_id,
        stale_after_seconds=stale_after_seconds,
    )


@app.post("/api/realtime-sessions/{realtime_session_id}/turns")
async def record_realtime_turn(
    realtime_session_id: UUID,
    request: RealtimeTurnCreate,
    store: PostgresStore = Depends(get_store),
    services: ContentWorkflowServices = Depends(get_content_workflow_services),
) -> RealtimeTurnResult:
    session = await store.get_realtime_session(realtime_session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Realtime session not found")
    transcript = request.transcript.strip() if request.transcript else ""
    if request.route_turn and request.speaker == "user" and not transcript:
        raise HTTPException(
            status_code=400,
            detail=(
                "Routed realtime turns require a finalized transcript from the "
                "voice agent. Set route_turn=false for media-only turn commits."
            ),
        )
    interruption_control_event_id = (
        await _latest_unresolved_interruption_control_event_id(store, session)
        if request.interrupted
        else None
    )
    metadata = {
        **request.metadata,
        "realtime_session_id": str(session.realtime_session_id),
        "provider": session.provider,
        "provider_session_id": session.provider_session_id,
        "audio_mode": session.audio_mode,
        "interrupted": request.interrupted,
        "latency_class": "realtime_interrupt",
        "transport_framework": session.transport_framework,
        "room_name": session.room_name,
        "transcript_status": "final" if transcript else "pending",
    }
    if interruption_control_event_id is not None:
        metadata["interruption_control_event_id"] = interruption_control_event_id
    event = None
    brief_task_message_id = None
    if request.route_turn and request.speaker == "user":
        router = ConversationRouter(store, services)
        try:
            routed = await router.route(
                ConversationRouteRequest(
                    run_id=session.run_id,
                    transcript=transcript,
                    modality=request.modality,
                    speaker=request.speaker,
                    audio_uri=request.audio_uri,
                    assets=request.assets,
                    record_multimodal_intake=request.record_multimodal_intake,
                    topic=request.topic,
                    target_formats=request.target_formats,
                    intent=request.intent,
                    require_human_feedback=request.require_human_feedback,
                    metadata=metadata,
                )
            )
        except ConversationRouterRunNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Run not found") from exc
        spoken_response = _build_realtime_spoken_response_plan(
            session=session,
            request=request,
            routed=routed,
            interruption_control_event_id=interruption_control_event_id,
        )
        if request.create_realtime_brief_task:
            brief_task_message_id = await _create_realtime_brief_task(
                store=store,
                session=session,
                request=request,
                source_turn_id=routed.turn_id,
                response_turn_id=routed.response_turn_id,
                routed_intent=routed.routed_intent.value,
                artifact_ids=[str(artifact_id) for artifact_id in routed.artifact_ids],
                spoken_response=spoken_response,
            )
        await store.append_event(
            RunEvent(
                run_id=session.run_id,
                event_type="realtime_spoken_response_planned",
                actor="realtime-conversation-host",
                payload={
                    **spoken_response.model_dump(mode="json"),
                    "brief_task_message_id": (
                        str(brief_task_message_id)
                        if brief_task_message_id
                        else None
                    ),
                },
            )
        )
        event = await store.append_event(
            RunEvent(
                run_id=session.run_id,
                event_type="realtime_turn_routed",
                actor="realtime-conversation-host",
                payload={
                    "realtime_session_id": str(session.realtime_session_id),
                    "turn_id": str(routed.turn_id),
                    "response_turn_id": (
                        str(routed.response_turn_id)
                        if routed.response_turn_id
                        else None
                    ),
                    "routed_intent": routed.routed_intent.value,
                    "artifact_ids": [
                        str(artifact_id) for artifact_id in routed.artifact_ids
                    ],
                    "provider": session.provider,
                    "provider_session_id": session.provider_session_id,
                    "latency_class": "realtime_interrupt",
                    "smoke_proof_status": (
                        "rehearsal_only"
                        if session.metadata.get("not_provider_backed")
                        else "provider_backed"
                    ),
                    "response_text": routed.response_text,
                    "spoken_response": spoken_response.model_dump(mode="json"),
                    "interrupted": request.interrupted,
                    "interruption_control_event_id": interruption_control_event_id,
                },
            )
        )
        return RealtimeTurnResult(
            realtime_session=session,
            routed_result=routed,
            spoken_response=spoken_response,
            brief_task_message_id=brief_task_message_id,
            event_id=event.event_id,
            summary=(
                f"Routed realtime {request.modality} turn as "
                f"{routed.routed_intent.value}."
            ),
        )

    turn = ConversationTurn(
        run_id=session.run_id,
        speaker=request.speaker,
        modality=request.modality,
        transcript=transcript or "Live audio turn committed; transcript pending.",
        audio_uri=request.audio_uri,
        metadata=metadata,
    )
    await store.record_conversation_turn(turn)
    if request.speaker == "user" and request.create_realtime_brief_task:
        brief_task_message_id = await _create_realtime_brief_task(
            store=store,
            session=session,
            request=request,
            source_turn_id=turn.turn_id,
            response_turn_id=None,
            routed_intent=None,
            artifact_ids=[],
        )
    event = await store.append_event(
        RunEvent(
            run_id=session.run_id,
            event_type="realtime_turn_recorded",
            actor=request.speaker,
            payload={
                "realtime_session_id": str(session.realtime_session_id),
                "turn_id": str(turn.turn_id),
                "speaker": request.speaker,
                "modality": request.modality,
                "provider": session.provider,
                "provider_session_id": session.provider_session_id,
                "latency_class": "realtime_interrupt",
                "smoke_proof_status": (
                    "rehearsal_only"
                    if session.metadata.get("not_provider_backed")
                    else "provider_backed"
                ),
                "interrupted": request.interrupted,
                "interruption_control_event_id": interruption_control_event_id,
            },
        )
    )
    return RealtimeTurnResult(
        realtime_session=session,
        conversation_turn=turn,
        brief_task_message_id=brief_task_message_id,
        event_id=event.event_id,
        summary=f"Recorded realtime {request.modality} turn.",
    )


@app.post("/api/realtime-sessions/{realtime_session_id}/control")
async def record_realtime_session_control(
    realtime_session_id: UUID,
    request: RealtimeSessionControlRequest,
    store: PostgresStore = Depends(get_store),
) -> RealtimeSessionControlResult:
    session = await store.get_realtime_session(realtime_session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Realtime session not found")
    cancel_gemma = (
        request.cancel_gemma
        if request.cancel_gemma is not None
        else request.action == RealtimeControlAction.INTERRUPT
    )
    clear_kokoro_buffers = (
        request.clear_kokoro_buffers
        if request.clear_kokoro_buffers is not None
        else request.action == RealtimeControlAction.INTERRUPT
    )
    stop_livekit_audio = (
        request.stop_livekit_audio
        if request.stop_livekit_audio is not None
        else request.action
        in {RealtimeControlAction.INTERRUPT, RealtimeControlAction.STOP_OUTPUT}
    )
    cancellation_contract = {
        "cancel_gemma": cancel_gemma,
        "clear_kokoro_buffers": clear_kokoro_buffers,
        "stop_livekit_audio": stop_livekit_audio,
        "interrupted_response_id": request.interrupted_response_id,
        "client_audio_timestamp_ms": request.client_audio_timestamp_ms,
        "transport_framework": session.transport_framework,
        "room_name": session.room_name,
        "agent_participant_identity": session.agent_participant_identity,
    }
    safe_request_metadata = _safe_realtime_metadata(request.metadata)

    followup_task_message_id = None
    if request.create_followup_task:
        message = AgentMessage(
            run_id=session.run_id,
            sender_agent_id="realtime-conversation-host",
            recipient_agent_id="realtime-conversation-host",
            task_type="handle_realtime_session_control",
            payload={
                "workflow": "realtime_session_control_v1",
                "realtime_session_id": str(session.realtime_session_id),
                "provider": session.provider,
                "provider_session_id": session.provider_session_id,
                "audio_mode": session.audio_mode,
                "voice": session.voice,
                "action": request.action.value,
                "reason": request.reason,
                "cancellation_contract": cancellation_contract,
                "metadata": safe_request_metadata,
            },
        )
        await store.record_agent_message(message)
        followup_task_message_id = message.message_id
        await store.append_event(
            RunEvent(
                run_id=session.run_id,
                event_type="agent_message_accepted",
                actor=message.sender_agent_id,
                payload=public_a2a_message_event_payload(message),
            )
        )

    event = await store.append_event(
        RunEvent(
            run_id=session.run_id,
            event_type="realtime_session_control_recorded",
            actor="realtime-conversation-host",
            payload={
                "realtime_session_id": str(session.realtime_session_id),
                "provider": session.provider,
                "provider_session_id": session.provider_session_id,
                "audio_mode": session.audio_mode,
                "voice": session.voice,
                "action": request.action.value,
                "reason": request.reason,
                "cancellation_contract": cancellation_contract,
                "cancel_gemma": cancel_gemma,
                "clear_kokoro_buffers": clear_kokoro_buffers,
                "stop_livekit_audio": stop_livekit_audio,
                "interrupted_response_id": request.interrupted_response_id,
                "client_audio_timestamp_ms": request.client_audio_timestamp_ms,
                "followup_task_message_id": (
                    str(followup_task_message_id)
                    if followup_task_message_id
                    else None
                ),
                "metadata": safe_request_metadata,
            },
        )
    )
    return RealtimeSessionControlResult(
        run_id=session.run_id,
        realtime_session_id=session.realtime_session_id,
        action=request.action,
        event_id=event.event_id,
        followup_task_message_id=followup_task_message_id,
        summary=(
            f"Recorded realtime session control `{request.action.value}` for "
            f"{session.provider}."
        ),
    )


@app.post("/api/realtime-sessions/{realtime_session_id}/voice-events")
async def record_realtime_voice_agent_event(
    realtime_session_id: UUID,
    request: RealtimeVoiceAgentEventCreate,
    store: PostgresStore = Depends(get_store),
) -> RealtimeVoiceAgentEventRecordResult:
    session = await store.get_realtime_session(realtime_session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Realtime session not found")
    safe_payload = _safe_realtime_metadata(request.payload)
    voice_agent_event_uid = _voice_agent_event_uid(request, safe_payload)
    if voice_agent_event_uid:
        safe_payload["voice_agent_event_uid"] = voice_agent_event_uid
        duplicate_event = await store.find_event_by_voice_agent_event_uid(
            session.run_id,
            request.event_type,
            voice_agent_event_uid,
        )
        if duplicate_event is not None:
            materialized_turn, followup_task_message_id = (
                await _recover_duplicate_voice_agent_event_effects(
                    store=store,
                    session=session,
                    event=duplicate_event,
                    event_type=request.event_type,
                    payload=safe_payload,
                )
            )
            followup_kind, followup_worker_agent_ids, followup_worker_use_gemma = (
                _voice_agent_event_followup_worker_hint(
                    event_type=request.event_type,
                    followup_task_message_id=followup_task_message_id,
                )
            )
            return RealtimeVoiceAgentEventRecordResult(
                run_id=session.run_id,
                realtime_session_id=session.realtime_session_id,
                event_id=duplicate_event.event_id or 0,
                event_type=request.event_type,
                materialized_turn_id=(
                    materialized_turn.turn_id if materialized_turn is not None else None
                ),
                materialized_speaker=(
                    materialized_turn.speaker if materialized_turn is not None else None
                ),
                followup_task_message_id=followup_task_message_id,
                followup_kind=followup_kind,
                followup_worker_agent_ids=followup_worker_agent_ids,
                followup_worker_use_gemma=followup_worker_use_gemma,
                summary=(
                    "Ignored duplicate realtime voice-agent event "
                    f"`{request.event_type}` from {request.source}"
                    + (
                        " and returned existing continuation hints."
                        if followup_task_message_id is not None
                        else "."
                    )
                ),
            )
    if request.agent_created_at is not None:
        safe_payload["agent_created_at"] = request.agent_created_at.isoformat()
    safe_payload.update(
        {
            "realtime_session_id": str(session.realtime_session_id),
            "provider": session.provider,
            "provider_session_id": session.provider_session_id,
            "transport_framework": session.transport_framework,
            "room_name": session.room_name,
            "voice_agent_event_source": request.source,
            "latency_class": "realtime_interrupt",
            "smoke_proof_status": (
                "rehearsal_only"
                if session.metadata.get("not_provider_backed")
                else "provider_backed"
            ),
        }
    )
    event = await store.append_event(
        RunEvent(
            run_id=session.run_id,
            event_type=request.event_type,
            actor="gemma-kokoro-livekit-agent",
            payload=safe_payload,
        )
    )
    materialized_turn = await _materialize_voice_agent_conversation_turn(
        store=store,
        session=session,
        event=event,
        event_type=request.event_type,
        payload=safe_payload,
    )
    followup_task_message_id = await _create_voice_agent_event_followup_task(
        store=store,
        session=session,
        event=event,
        event_type=request.event_type,
        payload=safe_payload,
        materialized_turn=materialized_turn,
    )
    followup_kind, followup_worker_agent_ids, followup_worker_use_gemma = (
        _voice_agent_event_followup_worker_hint(
            event_type=request.event_type,
            followup_task_message_id=followup_task_message_id,
        )
    )
    return RealtimeVoiceAgentEventRecordResult(
        run_id=session.run_id,
        realtime_session_id=session.realtime_session_id,
        event_id=event.event_id or 0,
        event_type=request.event_type,
        materialized_turn_id=(
            materialized_turn.turn_id if materialized_turn is not None else None
        ),
        materialized_speaker=(
            materialized_turn.speaker if materialized_turn is not None else None
        ),
        followup_task_message_id=followup_task_message_id,
        followup_kind=followup_kind,
        followup_worker_agent_ids=followup_worker_agent_ids,
        followup_worker_use_gemma=followup_worker_use_gemma,
        summary=(
            f"Recorded realtime voice-agent event `{request.event_type}`"
            + (
                f" and materialized {materialized_turn.speaker} dialogue"
                if materialized_turn is not None
                else "."
            )
            + (
                " with host follow-up."
                if followup_task_message_id is not None
                else "."
                if materialized_turn is not None
                else ""
            )
        ),
    )


async def _recover_duplicate_voice_agent_event_effects(
    *,
    store: PostgresStore,
    session: RealtimeSessionRecord,
    event: RunEvent,
    event_type: str,
    payload: dict[str, object],
) -> tuple[ConversationTurn | None, UUID | None]:
    materialized_turn = await _find_existing_voice_agent_materialized_turn(
        store=store,
        session=session,
        event_type=event_type,
        payload=payload,
    )
    if materialized_turn is None:
        materialized_turn = await _materialize_voice_agent_conversation_turn(
            store=store,
            session=session,
            event=event,
            event_type=event_type,
            payload=payload,
        )
    elif (
        event_type == "voice_user_turn_committed"
        and _optional_str(payload.get("transcript"))
    ):
        promoted_turn = await _materialize_voice_agent_conversation_turn(
            store=store,
            session=session,
            event=event,
            event_type=event_type,
            payload=payload,
        )
        if promoted_turn is not None:
            materialized_turn = promoted_turn
    followup_message = await _find_existing_voice_agent_followup_message(
        store=store,
        session=session,
        event=event,
        event_type=event_type,
        payload=payload,
        materialized_turn=materialized_turn,
    )
    if followup_message is not None:
        return materialized_turn, followup_message.message_id
    followup_id = await _create_voice_agent_event_followup_task(
        store=store,
        session=session,
        event=event,
        event_type=event_type,
        payload=payload,
        materialized_turn=materialized_turn,
    )
    return materialized_turn, followup_id


async def _find_existing_voice_agent_materialized_turn(
    *,
    store: PostgresStore,
    session: RealtimeSessionRecord,
    event_type: str,
    payload: dict[str, object],
) -> ConversationTurn | None:
    finder = getattr(store, "find_voice_agent_conversation_turn", None)
    if not callable(finder):
        return None
    if event_type == "voice_user_turn_committed":
        voice_turn_id = _optional_str(payload.get("turn_id"))
        if not voice_turn_id:
            return None
        return await finder(
            session.run_id,
            speaker="user",
            voice_turn_id=voice_turn_id,
        )
    if event_type == "assistant_response_completed":
        response_id = _optional_str(payload.get("response_id"))
        if not response_id:
            return None
        return await finder(
            session.run_id,
            speaker="assistant",
            response_id=response_id,
        )
    return None


async def _find_existing_voice_agent_followup_message(
    *,
    store: PostgresStore,
    session: RealtimeSessionRecord,
    event: RunEvent,
    event_type: str,
    payload: dict[str, object],
    materialized_turn: ConversationTurn | None,
) -> AgentMessage | None:
    if event_type == "assistant_response_completed":
        response_id = _optional_str(payload.get("response_id"))
        target_turn = materialized_turn
        if target_turn is None and response_id:
            finder = getattr(store, "find_voice_agent_conversation_turn", None)
            if callable(finder):
                target_turn = await finder(
                    session.run_id,
                    speaker="assistant",
                    response_id=response_id,
                )
        if target_turn is None:
            return None
        return await _find_voice_agent_event_followup_task(
            store=store,
            session=session,
            response_id=response_id,
            response_turn_id=target_turn.turn_id,
        )
    if event_type == "gemma_kokoro_voice_turn_failed":
        message_id = _voice_agent_failure_followup_message_id(
            session=session,
            response_id=_optional_str(payload.get("response_id")),
            turn_id=_optional_str(payload.get("turn_id")),
            event_id=event.event_id,
        )
        getter = getattr(store, "get_agent_message", None)
        if callable(getter):
            return await getter(message_id)
    return None


def _voice_agent_event_uid(
    request: RealtimeVoiceAgentEventCreate,
    payload: dict[str, object],
) -> str | None:
    raw_uid = request.voice_agent_event_uid or payload.get("voice_agent_event_uid")
    if not isinstance(raw_uid, str):
        return None
    uid = raw_uid.strip()
    if not uid:
        return None
    return uid[:200]


def _voice_agent_event_followup_worker_hint(
    *,
    event_type: str,
    followup_task_message_id: UUID | None,
) -> tuple[str | None, list[str], bool | None]:
    if followup_task_message_id is None:
        return None, [], None
    if event_type == "gemma_kokoro_voice_turn_failed":
        return (
            "provider_failure_recovery",
            list(VOICE_PROVIDER_FAILURE_RECOVERY_AGENT_IDS),
            False,
        )
    return "realtime_turn_context", [], None


def _build_voice_agent_presence(
    *,
    run_id: UUID,
    sessions: list[RealtimeSessionRecord],
    events: list[RunEvent],
    realtime_session_id: UUID | None,
    probe_id: str | None,
    stale_after_seconds: int,
) -> VoiceAgentPresenceResult:
    latest_event = _latest_voice_agent_ready_event(
        events,
        realtime_session_id=realtime_session_id,
        probe_id=probe_id,
    )
    selected_session = _select_presence_session(
        sessions,
        realtime_session_id=realtime_session_id,
        latest_event=latest_event,
    )
    now = datetime.now(timezone.utc)
    event_age_seconds = (
        max(
            0.0,
            (
                now - _aware_utc(latest_event.created_at)
            ).total_seconds(),
        )
        if latest_event is not None
        else None
    )
    is_stale = (
        event_age_seconds is not None and event_age_seconds > stale_after_seconds
    )
    status = (
        VoiceAgentPresenceStatus.MISSING
        if latest_event is None
        else VoiceAgentPresenceStatus.STALE
        if is_stale
        else VoiceAgentPresenceStatus.READY
    )
    payload = latest_event.payload if latest_event is not None else {}
    result_session_id = (
        realtime_session_id
        or _event_realtime_session_id(latest_event)
        or (selected_session.realtime_session_id if selected_session else None)
    )
    room_name = _optional_str(payload.get("room_name")) or (
        selected_session.room_name if selected_session else None
    )
    agent_identity = (
        _optional_str(payload.get("agent_participant_identity"))
        or _optional_str(payload.get("agent_identity"))
        or _optional_str(payload.get("agent_name"))
        or (selected_session.agent_participant_identity if selected_session else None)
    )
    livekit_sender_identity = _optional_str(payload.get("livekit_sender_identity"))
    evidence: list[str] = []
    missing_evidence: list[str] = []
    next_actions: list[str] = []
    if latest_event is not None:
        evidence.append(
            "Observed durable gemma_kokoro_voice_agent_ready event "
            f"{latest_event.event_id or 'unknown'}."
        )
        if livekit_sender_identity:
            evidence.append(
                f"LiveKit data event came from participant {livekit_sender_identity}."
            )
        if room_name:
            evidence.append(f"Presence was observed in LiveKit room {room_name}.")
        if is_stale:
            missing_evidence.append(
                "The latest voice-agent-ready event is older than the configured "
                f"{stale_after_seconds}s freshness window."
            )
            next_actions.append(
                "Restart or reconnect the OpenRouter/Kokoro LiveKit agent and send a fresh presence probe."
            )
    else:
        missing_evidence.append(
            "No durable gemma_kokoro_voice_agent_ready event has been recorded for this run/session."
        )
        if selected_session is None:
            missing_evidence.append(
                "No realtime LiveKit session exists for this run yet."
            )
            next_actions.append(
                "Create an OpenRouter/Kokoro LiveKit voice session before checking participant presence."
            )
        else:
            next_actions.append(
                "Start all-about-llms-admin run-voice-agent and join the LiveKit voice room."
            )
            next_actions.append(
                "Send the frontend voice-agent presence probe and persist the returned ready event."
            )

    provider = selected_session.provider if selected_session else None
    provider_session_id = (
        selected_session.provider_session_id if selected_session else None
    )
    transport_framework = (
        selected_session.transport_framework if selected_session else None
    )
    summary = (
        "OpenRouter/Kokoro voice-agent participant is observed and fresh."
        if status == VoiceAgentPresenceStatus.READY
        else "OpenRouter/Kokoro voice-agent participant was observed but the proof is stale."
        if status == VoiceAgentPresenceStatus.STALE
        else "OpenRouter/Kokoro voice-agent participant has not been durably observed."
    )
    return VoiceAgentPresenceResult(
        run_id=run_id,
        realtime_session_id=result_session_id,
        status=status,
        observed=latest_event is not None,
        stale=is_stale,
        stale_after_seconds=stale_after_seconds,
        event_age_seconds=(
            round(event_age_seconds, 3)
            if event_age_seconds is not None
            else None
        ),
        latest_event_id=latest_event.event_id if latest_event else None,
        latest_event_type=latest_event.event_type if latest_event else None,
        latest_event_created_at=latest_event.created_at if latest_event else None,
        provider=provider,
        provider_session_id=provider_session_id,
        transport_framework=transport_framework,
        room_name=room_name,
        agent_participant_identity=agent_identity,
        livekit_sender_identity=livekit_sender_identity,
        probe_id=_optional_str(payload.get("probe_id")),
        audio_input_model=_optional_str(payload.get("audio_input_model")),
        reasoning_model=_optional_str(payload.get("reasoning_model")),
        audio_output_model=_optional_str(payload.get("audio_output_model")),
        evidence=evidence,
        missing_evidence=missing_evidence,
        next_actions=next_actions,
        summary=summary,
    )


def _latest_voice_agent_ready_event(
    events: list[RunEvent],
    *,
    realtime_session_id: UUID | None,
    probe_id: str | None,
) -> RunEvent | None:
    candidates = [
        event
        for event in events
        if event.event_type == "gemma_kokoro_voice_agent_ready"
        and (
            realtime_session_id is None
            or _event_realtime_session_id(event) == realtime_session_id
        )
        and (
            probe_id is None
            or _optional_str(event.payload.get("probe_id")) == probe_id
        )
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda event: (_aware_utc(event.created_at), event.event_id or 0),
    )


def _select_presence_session(
    sessions: list[RealtimeSessionRecord],
    *,
    realtime_session_id: UUID | None,
    latest_event: RunEvent | None,
) -> RealtimeSessionRecord | None:
    if realtime_session_id is not None:
        return next(
            (
                session
                for session in sessions
                if session.realtime_session_id == realtime_session_id
            ),
            None,
        )
    event_session_id = _event_realtime_session_id(latest_event)
    if latest_event is not None:
        if event_session_id is None:
            return None
        return next(
            (
                session
                for session in sessions
                if session.realtime_session_id == event_session_id
            ),
            None,
        )
    if not sessions:
        return None
    return max(sessions, key=lambda session: _aware_utc(session.created_at))


def _event_realtime_session_id(event: RunEvent | None) -> UUID | None:
    if event is None:
        return None
    return _uuid_or_none(_optional_str(event.payload.get("realtime_session_id")))


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def _materialize_voice_agent_conversation_turn(
    *,
    store: PostgresStore,
    session: RealtimeSessionRecord,
    event: RunEvent,
    event_type: str,
    payload: dict[str, object],
) -> ConversationTurn | None:
    if event_type == "voice_user_turn_committed":
        return await _materialize_voice_user_turn(
            store=store,
            session=session,
            event=event,
            payload=payload,
        )
    if event_type == "assistant_response_completed":
        return await _materialize_voice_assistant_turn(
            store=store,
            session=session,
            event=event,
            payload=payload,
        )
    return None


async def _materialize_voice_user_turn(
    *,
    store: PostgresStore,
    session: RealtimeSessionRecord,
    event: RunEvent,
    payload: dict[str, object],
) -> ConversationTurn | None:
    voice_turn_id = _optional_str(payload.get("turn_id"))
    if not voice_turn_id:
        return None
    turn_uuid = _uuid_or_none(voice_turn_id)
    if turn_uuid is None:
        return None
    transcript = _optional_str(payload.get("transcript"))
    transcript_status = "final" if transcript else "pending"
    turn = ConversationTurn(
        turn_id=turn_uuid,
        run_id=session.run_id,
        speaker="user",
        modality=_optional_str(payload.get("input_modality")) or "voice",
        transcript=transcript or "Live audio turn committed; transcript pending.",
        audio_uri=_optional_str(payload.get("audio_uri"))
        or _optional_str(payload.get("audio_ref"))
        or _optional_str(payload.get("audio_artifact_uri")),
        metadata={
            "realtime_session_id": str(session.realtime_session_id),
            "provider": session.provider,
            "provider_session_id": session.provider_session_id,
            "transport_framework": session.transport_framework,
            "room_name": session.room_name,
            "voice_agent_event_id": event.event_id,
            "voice_agent_event_type": "voice_user_turn_committed",
            "voice_agent_turn_id": voice_turn_id,
            "transcript_status": transcript_status,
            "audio_duration_ms": payload.get("audio_duration_ms"),
            "audio_bytes": payload.get("audio_bytes"),
            "audio_artifact_uri": payload.get("audio_artifact_uri"),
            "audio_artifact_relative_path": payload.get(
                "audio_artifact_relative_path"
            ),
            "audio_artifact_sha256": payload.get("audio_artifact_sha256"),
            "audio_artifact_bytes": payload.get("audio_artifact_bytes"),
            "audio_artifact_persisted": payload.get("audio_artifact_persisted"),
            "audio_artifact_skip_reason": payload.get(
                "audio_artifact_skip_reason"
            ),
            "windowing": payload.get("windowing"),
            "source": "livekit_voice_agent_event",
        },
    )
    return await _record_voice_agent_conversation_turn_if_absent(
        store,
        turn,
        voice_turn_id=voice_turn_id,
        response_id=None,
    )


async def _materialize_voice_assistant_turn(
    *,
    store: PostgresStore,
    session: RealtimeSessionRecord,
    event: RunEvent,
    payload: dict[str, object],
) -> ConversationTurn | None:
    response_id = _optional_str(payload.get("response_id"))
    assistant_text = _optional_str(payload.get("assistant_text"))
    if not response_id or not assistant_text:
        return None
    turn = ConversationTurn(
        run_id=session.run_id,
        speaker="assistant",
        modality="voice",
        transcript=assistant_text,
        metadata={
            "realtime_session_id": str(session.realtime_session_id),
            "provider": session.provider,
            "provider_session_id": session.provider_session_id,
            "transport_framework": session.transport_framework,
            "room_name": session.room_name,
            "voice_agent_event_id": event.event_id,
            "voice_agent_event_type": "assistant_response_completed",
            "voice_agent_turn_id": _optional_str(payload.get("turn_id")),
            "voice_agent_response_id": response_id,
            "responds_to_voice_turn_id": _optional_str(payload.get("turn_id")),
            "audio_chunk_count": payload.get("audio_chunk_count"),
            "assistant_text_chars": payload.get("assistant_text_chars"),
            "livekit_audio_track_id": payload.get("livekit_audio_track_id"),
            "heard_by_user": True,
            "source": "livekit_voice_agent_event",
        },
    )
    return await _record_voice_agent_conversation_turn_if_absent(
        store,
        turn,
        voice_turn_id=None,
        response_id=response_id,
    )


async def _record_voice_agent_conversation_turn_if_absent(
    store: PostgresStore,
    turn: ConversationTurn,
    voice_turn_id: str | None,
    response_id: str | None,
) -> ConversationTurn | None:
    if not voice_turn_id and not response_id:
        return None
    recorder = getattr(store, "record_voice_agent_conversation_turn_if_absent", None)
    if callable(recorder):
        recorded = await recorder(
            turn,
            voice_turn_id=voice_turn_id,
            response_id=response_id,
        )
        if recorded is not None:
            return recorded
        if voice_turn_id and turn.speaker == "user":
            return await _promote_pending_voice_user_transcript(
                store=store,
                turn=turn,
                voice_turn_id=voice_turn_id,
            )
        return None
    return None


async def _promote_pending_voice_user_transcript(
    *,
    store: PostgresStore,
    turn: ConversationTurn,
    voice_turn_id: str,
) -> ConversationTurn | None:
    transcript = _optional_str(turn.transcript)
    if not transcript or transcript == "Live audio turn committed; transcript pending.":
        return None
    promoter = getattr(store, "promote_voice_user_transcript_if_pending", None)
    if callable(promoter):
        promoted = await promoter(turn, voice_turn_id=voice_turn_id)
        if promoted is not None:
            await _sync_voice_followup_tasks_for_promoted_source_turn(
                store=store,
                promoted_turn=promoted,
                promoted_event_id=turn.metadata.get("voice_agent_event_id"),
            )
            await store.append_event(
                RunEvent(
                    run_id=turn.run_id,
                    event_type="voice_user_transcript_promoted",
                    actor="gemma-kokoro-livekit-agent",
                    payload={
                        "turn_id": str(promoted.turn_id),
                        "voice_agent_turn_id": voice_turn_id,
                        "voice_agent_event_id": turn.metadata.get(
                            "voice_agent_event_id"
                        ),
                        "realtime_session_id": promoted.metadata.get(
                            "realtime_session_id"
                        ),
                        "transcript_status": "final",
                        "transcript_chars": len(transcript),
                    },
                )
            )
            return promoted
        finder = getattr(store, "find_voice_agent_conversation_turn", None)
        if callable(finder):
            existing = await finder(
                turn.run_id,
                speaker="user",
                voice_turn_id=voice_turn_id,
            )
            if (
                existing is not None
                and existing.metadata.get("transcript_status") == "final"
                and existing.transcript == transcript
            ):
                await _sync_voice_followup_tasks_for_promoted_source_turn(
                    store=store,
                    promoted_turn=existing,
                    promoted_event_id=turn.metadata.get("voice_agent_event_id"),
                )
                return existing
        return None
    finder = getattr(store, "find_voice_agent_conversation_turn", None)
    updater = getattr(store, "update_conversation_turn", None)
    if not callable(finder) or not callable(updater):
        return None
    existing = await finder(
        turn.run_id,
        speaker="user",
        voice_turn_id=voice_turn_id,
    )
    if existing is None:
        return None
    existing_status = _optional_str(existing.metadata.get("transcript_status"))
    if existing_status == "final" and existing.transcript == transcript:
        await _sync_voice_followup_tasks_for_promoted_source_turn(
            store=store,
            promoted_turn=existing,
            promoted_event_id=turn.metadata.get("voice_agent_event_id"),
        )
        return existing
    if existing_status == "final" and existing.transcript != transcript:
        return existing
    merged_metadata = _merge_voice_turn_metadata(existing.metadata, turn.metadata)
    promoted_event_id = turn.metadata.get("voice_agent_event_id")
    merged_metadata.update(
        {
            "transcript_status": "final",
            "transcript_promoted_from_pending": existing_status != "final",
            "transcript_promoted_event_id": promoted_event_id,
            "transcript_promoted_at": datetime.now(timezone.utc).isoformat(),
            "transcript_source": "voice_user_turn_committed",
        }
    )
    promoted = existing.model_copy(
        update={
            "transcript": transcript,
            "audio_uri": turn.audio_uri or existing.audio_uri,
            "metadata": merged_metadata,
        }
    )
    updated = await updater(promoted)
    if updated is None:
        return None
    await _sync_voice_followup_tasks_for_promoted_source_turn(
        store=store,
        promoted_turn=updated,
        promoted_event_id=promoted_event_id,
    )
    await store.append_event(
        RunEvent(
            run_id=turn.run_id,
            event_type="voice_user_transcript_promoted",
            actor="gemma-kokoro-livekit-agent",
            payload={
                "turn_id": str(updated.turn_id),
                "voice_agent_turn_id": voice_turn_id,
                "voice_agent_event_id": promoted_event_id,
                "realtime_session_id": updated.metadata.get("realtime_session_id"),
                "transcript_status": "final",
                "transcript_chars": len(transcript),
            },
        )
    )
    return updated


async def _sync_voice_followup_tasks_for_promoted_source_turn(
    *,
    store: PostgresStore,
    promoted_turn: ConversationTurn,
    promoted_event_id: object,
) -> int:
    lister = getattr(store, "list_agent_messages", None)
    payload_updater = getattr(store, "update_agent_message_payload", None)
    if not callable(lister) or not callable(payload_updater):
        return 0
    messages = await lister(
        promoted_turn.run_id,
        agent_id="realtime-conversation-host",
        direction="all",
        limit=1000,
    )
    source_turn_id = str(promoted_turn.turn_id)
    transcript_excerpt = promoted_turn.transcript[:240]
    updated_message_ids: list[str] = []
    updated_at = datetime.now(timezone.utc)
    for message in messages:
        payload = message.payload or {}
        if message.task_type != "summarize_realtime_turn_context":
            continue
        if payload.get("workflow") != "realtime_voice_agent_event_followup_v1":
            continue
        if payload.get("source_turn_id") != source_turn_id:
            continue
        if (
            payload.get("transcript_status") == "final_user_transcript"
            and payload.get("source_transcript_excerpt") == transcript_excerpt
        ):
            continue
        refreshed_payload = dict(payload)
        refreshed_payload.update(
            {
                "transcript_status": "final_user_transcript",
                "source_transcript_excerpt": transcript_excerpt,
                "source_transcript_promoted_from_pending": True,
                "source_transcript_promoted_event_id": promoted_event_id,
                "source_transcript_promoted_at": updated_at.isoformat(),
            }
        )
        refreshed_message = await payload_updater(
            message.message_id,
            refreshed_payload,
            updated_at=updated_at,
        )
        if refreshed_message is not None:
            updated_message_ids.append(str(message.message_id))
    if updated_message_ids:
        await store.append_event(
            RunEvent(
                run_id=promoted_turn.run_id,
                event_type="realtime_voice_agent_followup_task_source_transcript_promoted",
                actor="realtime-conversation-host",
                payload={
                    "source_turn_id": source_turn_id,
                    "message_ids": updated_message_ids,
                    "voice_agent_turn_id": promoted_turn.metadata.get(
                        "voice_agent_turn_id"
                    ),
                    "voice_agent_event_id": promoted_event_id,
                    "transcript_status": "final_user_transcript",
                    "transcript_chars": len(promoted_turn.transcript),
                },
            )
        )
    return len(updated_message_ids)


def _merge_voice_turn_metadata(
    existing_metadata: dict[str, object],
    incoming_metadata: dict[str, object],
) -> dict[str, object]:
    merged = dict(existing_metadata)
    for key, value in incoming_metadata.items():
        if value is not None:
            merged[key] = value
    return merged


async def _create_voice_agent_event_followup_task(
    *,
    store: PostgresStore,
    session: RealtimeSessionRecord,
    event: RunEvent,
    event_type: str,
    payload: dict[str, object],
    materialized_turn: ConversationTurn | None,
) -> UUID | None:
    if event_type == "gemma_kokoro_voice_turn_failed":
        return await _create_voice_agent_failure_followup_task(
            store=store,
            session=session,
            event=event,
            event_type=event_type,
            payload=payload,
        )
    if event_type != "assistant_response_completed":
        return None
    response_id = _optional_str(payload.get("response_id"))
    target_turn = materialized_turn
    if target_turn is None and response_id:
        finder = getattr(store, "find_voice_agent_conversation_turn", None)
        if callable(finder):
            target_turn = await finder(
                session.run_id,
                speaker="assistant",
                response_id=response_id,
            )
    if target_turn is None or target_turn.speaker != "assistant":
        return None
    existing_followup = await _find_voice_agent_event_followup_task(
        store=store,
        session=session,
        response_id=response_id,
        response_turn_id=target_turn.turn_id,
    )
    if existing_followup is not None:
        return None
    message_id = _voice_agent_event_followup_message_id(
        session=session,
        response_id=response_id,
        response_turn_id=target_turn.turn_id,
    )

    source_turn_id_text = _optional_str(payload.get("turn_id"))
    source_turn_id = _uuid_or_none(source_turn_id_text)
    source_turn = await _find_voice_source_user_turn(
        store=store,
        session=session,
        voice_turn_id=source_turn_id_text,
    )
    source_transcript_status = _voice_source_transcript_status(
        source_turn=source_turn,
        source_turn_id=source_turn_id,
    )
    message = AgentMessage(
        message_id=message_id,
        run_id=session.run_id,
        sender_agent_id="realtime-conversation-host",
        recipient_agent_id="realtime-conversation-host",
        task_type="summarize_realtime_turn_context",
        payload={
            "workflow": "realtime_voice_agent_event_followup_v1",
            "topic": "live voice exchange",
            "realtime_session_id": str(session.realtime_session_id),
            "provider": session.provider,
            "provider_session_id": session.provider_session_id,
            "audio_mode": session.audio_mode,
            "voice": session.voice,
            "transport_framework": session.transport_framework,
            "room_name": session.room_name,
            "source_turn_id": str(source_turn_id) if source_turn_id else None,
            "response_turn_id": str(target_turn.turn_id),
            "routed_intent": None,
            "artifact_ids": [],
            "speaker": target_turn.speaker,
            "modality": target_turn.modality,
            "interrupted": False,
            "transcript_excerpt": target_turn.transcript[:240],
            "source_transcript_excerpt": (
                source_turn.transcript[:240]
                if source_transcript_status == "final_user_transcript"
                and source_turn is not None
                else None
            ),
            "voice_agent_event_id": event.event_id,
            "voice_agent_event_type": event_type,
            "voice_agent_response_id": response_id,
            "transcript_status": source_transcript_status,
            "routing_policy": (
                "summarize_or_route_without_treating_raw_audio_as_verified_text"
            ),
        },
    )
    recorded_message = await _record_agent_message_if_absent(store, message)
    if recorded_message is None:
        return None
    await store.append_event(
        RunEvent(
            run_id=session.run_id,
            event_type="agent_message_accepted",
            actor=message.sender_agent_id,
            payload=public_a2a_message_event_payload(message),
        )
    )
    await store.append_event(
        RunEvent(
            run_id=session.run_id,
            event_type="realtime_voice_agent_followup_task_created",
            actor="realtime-conversation-host",
            payload={
                "message_id": str(message.message_id),
                "realtime_session_id": str(session.realtime_session_id),
                "voice_agent_event_id": event.event_id,
                "voice_agent_event_type": event_type,
                "source_turn_id": str(source_turn_id) if source_turn_id else None,
                "response_turn_id": str(target_turn.turn_id),
                "voice_agent_response_id": response_id,
                "routing_policy": message.payload["routing_policy"],
            },
        )
    )
    return message.message_id


async def _find_voice_source_user_turn(
    *,
    store: PostgresStore,
    session: RealtimeSessionRecord,
    voice_turn_id: str | None,
) -> ConversationTurn | None:
    if not voice_turn_id:
        return None
    finder = getattr(store, "find_voice_agent_conversation_turn", None)
    if not callable(finder):
        return None
    return await finder(
        session.run_id,
        speaker="user",
        voice_turn_id=voice_turn_id,
    )


def _voice_source_transcript_status(
    *,
    source_turn: ConversationTurn | None,
    source_turn_id: UUID | None,
) -> str:
    if source_turn is None:
        return "pending_user_transcript" if source_turn_id else "unknown_source_turn"
    metadata_status = _optional_str(source_turn.metadata.get("transcript_status"))
    if (
        metadata_status == "final"
        and source_turn.transcript != "Live audio turn committed; transcript pending."
    ):
        return "final_user_transcript"
    return "pending_user_transcript"


async def _create_voice_agent_failure_followup_task(
    *,
    store: PostgresStore,
    session: RealtimeSessionRecord,
    event: RunEvent,
    event_type: str,
    payload: dict[str, object],
) -> UUID | None:
    response_id = _optional_str(payload.get("response_id"))
    turn_id = _optional_str(payload.get("turn_id"))
    message_id = _voice_agent_failure_followup_message_id(
        session=session,
        response_id=response_id,
        turn_id=turn_id,
        event_id=event.event_id,
    )
    getter = getattr(store, "get_agent_message", None)
    if callable(getter) and await getter(message_id) is not None:
        return None
    failure_stage = _optional_str(payload.get("failure_stage")) or "unknown"
    failure_reason = _safe_voice_failure_reason(
        _optional_str(payload.get("failure_reason"))
        or _optional_str(payload.get("reason"))
        or "Unknown OpenRouter/Kokoro provider failure."
    )
    message = AgentMessage(
        message_id=message_id,
        run_id=session.run_id,
        sender_agent_id="realtime-conversation-host",
        recipient_agent_id="inference-systems-engineer",
        task_type="review_realtime_provider_failure",
        payload={
            "workflow": "realtime_voice_agent_failure_followup_v1",
            "topic": "OpenRouter/Kokoro voice provider failure",
            "realtime_session_id": str(session.realtime_session_id),
            "provider": session.provider,
            "provider_session_id": session.provider_session_id,
            "transport_framework": session.transport_framework,
            "room_name": session.room_name,
            "voice": session.voice,
            "voice_agent_event_id": event.event_id,
            "voice_agent_event_type": event_type,
            "voice_agent_turn_id": turn_id,
            "voice_agent_response_id": response_id,
            "failure_stage": failure_stage,
            "failure_reason": failure_reason,
            "assistant_text_chars": payload.get("assistant_text_chars"),
            "audio_chunk_count": payload.get("audio_chunk_count"),
            "required_action": (
                "Review Gemma/HF streaming, Kokoro TTS, LiveKit output, "
                "provider smoke proof, and recovery instructions before "
                "marking voice ready."
            ),
            "recommended_worker_agent_ids": VOICE_PROVIDER_FAILURE_RECOVERY_AGENT_IDS,
            "recommended_worker_use_gemma": False,
        },
    )
    recorded_message = await _record_agent_message_if_absent(store, message)
    if recorded_message is None:
        return None
    await store.append_event(
        RunEvent(
            run_id=session.run_id,
            event_type="agent_message_accepted",
            actor=message.sender_agent_id,
            payload=public_a2a_message_event_payload(message),
        )
    )
    await store.append_event(
        RunEvent(
            run_id=session.run_id,
            event_type="realtime_voice_agent_failure_followup_task_created",
            actor="realtime-conversation-host",
            payload={
                "message_id": str(message.message_id),
                "recipient_agent_id": message.recipient_agent_id,
                "task_type": message.task_type,
                "realtime_session_id": str(session.realtime_session_id),
                "voice_agent_event_id": event.event_id,
                "voice_agent_event_type": event_type,
                "voice_agent_turn_id": turn_id,
                "voice_agent_response_id": response_id,
                "failure_stage": failure_stage,
                "recommended_worker_agent_ids": VOICE_PROVIDER_FAILURE_RECOVERY_AGENT_IDS,
                "recommended_worker_use_gemma": False,
            },
        )
    )
    return message.message_id


async def _record_agent_message_if_absent(
    store: PostgresStore,
    message: AgentMessage,
) -> AgentMessage | None:
    recorder = getattr(store, "record_agent_message_if_absent", None)
    if callable(recorder):
        return await recorder(message)
    return None


async def _record_product_growth_strategy(
    *,
    store: PostgresStore,
    run_id: UUID,
    package: ArtifactRecord,
    source_artifacts: list[ArtifactRecord],
    sender_agent_id: str,
    recipient_agent_id: str,
    task_type: str,
    event_type: str,
    reused_event_type: str,
    build_artifact,
) -> tuple[UUID, UUID]:
    message = AgentMessage(
        message_id=_product_growth_message_id(
            run_id=run_id,
            distribution_artifact_id=package.artifact_id,
            recipient_agent_id=recipient_agent_id,
            task_type=task_type,
        ),
        run_id=run_id,
        sender_agent_id=sender_agent_id,
        recipient_agent_id=recipient_agent_id,
        task_type=task_type,
        payload={
            "topic": package.content.get("topic"),
            "distribution_artifact_id": str(package.artifact_id),
            "target_artifact_ids": [
                str(source_artifact.artifact_id)
                for source_artifact in source_artifacts
            ],
            "source_artifact_ids": [
                str(source_artifact.artifact_id)
                for source_artifact in source_artifacts
            ],
        },
    )
    recorded_message = await _record_agent_message_if_absent(store, message)
    if recorded_message is not None:
        await store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="agent_message_accepted",
                actor=sender_agent_id,
                payload=public_a2a_message_event_payload(recorded_message),
            )
        )
    existing_message = recorded_message or await store.get_agent_message(
        message.message_id
    )
    message_for_artifact = existing_message or message
    artifact = build_artifact(
        message=message_for_artifact,
        package=package,
        source_artifacts=source_artifacts,
        strategy_context={
            "summary": (
                "Product growth package action requested a concrete specialist "
                f"strategy from {recipient_agent_id}."
            )
        },
    )
    recorder = getattr(store, "record_artifact_if_absent", None)
    recorded_artifact = await recorder(artifact) if callable(recorder) else None
    if recorded_artifact is not None:
        await store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="artifact_recorded",
                actor="artifact-librarian",
                payload=recorded_artifact.model_dump(mode="json"),
            )
        )
    reused_existing = recorded_artifact is None
    await store.append_event(
        RunEvent(
            run_id=run_id,
            event_type=reused_event_type if reused_existing else event_type,
            actor=recipient_agent_id,
            payload={
                "message_id": str(message.message_id),
                "strategy_artifact_id": str(artifact.artifact_id),
                "distribution_artifact_id": str(package.artifact_id),
                "source_artifact_ids": [
                    str(source_artifact.artifact_id)
                    for source_artifact in source_artifacts
                ],
                "reused_existing": reused_existing,
            },
        )
    )
    updater = getattr(store, "update_agent_message_status", None)
    if callable(updater):
        await updater(
            message.message_id,
            AgentTaskStatus.COMPLETED,
            recipient_agent_id,
            result={
                "generation_mode": "product_growth_package_route",
                "materialized_agent_id": recipient_agent_id,
                "strategy_artifact_id": str(artifact.artifact_id),
                "distribution_artifact_id": str(package.artifact_id),
                "source_artifact_ids": [
                    str(source_artifact.artifact_id)
                    for source_artifact in source_artifacts
                ],
                "reused_existing": reused_existing,
            },
            notes="Product growth package strategy artifact recorded.",
        )
    return message.message_id, artifact.artifact_id


def _product_growth_message_id(
    *,
    run_id: UUID,
    distribution_artifact_id: UUID,
    recipient_agent_id: str,
    task_type: str,
) -> UUID:
    return uuid5(
        NAMESPACE_URL,
        (
            "all-about-llms:product_growth_package:"
            f"{run_id}:{distribution_artifact_id}:{recipient_agent_id}:{task_type}"
        ),
    )


def _product_growth_distribution_artifact_id(
    *,
    run_id: UUID,
    source_artifacts: list[ArtifactRecord],
    request: DistributionPackageRequest,
) -> UUID:
    source_ids = sorted(str(artifact.artifact_id) for artifact in source_artifacts)
    platforms = _normalized_platforms(request.platforms)
    return uuid5(
        NAMESPACE_URL,
        (
            "all-about-llms:product_growth_distribution_package:"
            f"{run_id}:{','.join(source_ids)}:"
            f"{','.join(platforms)}:{request.audience}:"
            f"{request.campaign_goal}:{request.include_outreach}:"
            f"{request.created_by_agent_id}"
        ),
    )


def _growth_package_source_artifacts(
    *,
    artifacts: list[ArtifactRecord],
    target_artifact_ids: list[UUID],
) -> list[ArtifactRecord]:
    parent_ids = set()
    for artifact in artifacts:
        parent_id = artifact.provenance.get("parent_artifact_id")
        if isinstance(parent_id, str):
            try:
                parent_ids.add(UUID(parent_id))
            except ValueError:
                continue
    source_artifacts = [
        artifact
        for artifact in artifacts
        if artifact.artifact_type
        in {
            ArtifactType.POST,
            ArtifactType.REEL_SCRIPT,
            ArtifactType.SUBSTACK_ARTICLE,
        }
        and artifact.artifact_id not in parent_ids
    ]
    if not target_artifact_ids:
        return source_artifacts
    target_ids = set(target_artifact_ids)
    return [
        artifact for artifact in source_artifacts if artifact.artifact_id in target_ids
    ]


def _current_product_growth_distribution_package(
    *,
    artifacts: list[ArtifactRecord],
    source_artifacts: list[ArtifactRecord],
    request: DistributionPackageRequest,
) -> ArtifactRecord | None:
    source_artifact_ids = {
        str(source_artifact.artifact_id) for source_artifact in source_artifacts
    }
    platforms = _normalized_platforms(request.platforms)
    for artifact in reversed(artifacts):
        if (
            artifact.artifact_type == ArtifactType.SOCIAL_PACKAGE
            and artifact.provenance.get("workflow") == "distribution_package_v1"
            and set(artifact.provenance.get("source_artifact_ids", []))
            == source_artifact_ids
            and artifact.provenance.get("created_by_agent_id")
            == request.created_by_agent_id
            and _growth_distribution_package_platforms(artifact) == platforms
            and _growth_distribution_package_audience(artifact) == request.audience
            and _growth_distribution_package_campaign_goal(artifact)
            == request.campaign_goal
            and _growth_distribution_package_include_outreach(artifact)
            == request.include_outreach
        ):
            return artifact
    return None


def _growth_distribution_package_audience(package: ArtifactRecord) -> str | None:
    audience = package.provenance.get("audience")
    if isinstance(audience, str):
        return audience
    content_audience = package.content.get("audience")
    return content_audience if isinstance(content_audience, str) else None


def _growth_distribution_package_campaign_goal(package: ArtifactRecord) -> str | None:
    campaign_goal = package.provenance.get("campaign_goal")
    if isinstance(campaign_goal, str):
        return campaign_goal
    content_campaign_goal = package.content.get("campaign_goal")
    return (
        content_campaign_goal if isinstance(content_campaign_goal, str) else None
    )


def _growth_distribution_package_include_outreach(package: ArtifactRecord) -> bool:
    include_outreach = package.provenance.get("include_outreach")
    if isinstance(include_outreach, bool):
        return include_outreach
    return package.content.get("outreach") is not None


def _growth_distribution_package_platforms(package: ArtifactRecord) -> list[str]:
    raw_platforms = package.provenance.get("platforms")
    if isinstance(raw_platforms, list):
        platforms = [str(platform) for platform in raw_platforms if str(platform)]
        if platforms:
            return platforms
    content_platforms = package.content.get("platforms")
    if isinstance(content_platforms, list):
        platforms = []
        for platform in content_platforms:
            if isinstance(platform, dict) and platform.get("platform"):
                platforms.append(str(platform["platform"]))
            elif isinstance(platform, str) and platform:
                platforms.append(platform)
        if platforms:
            return platforms
    return []


async def _find_voice_agent_event_followup_task(
    *,
    store: PostgresStore,
    session: RealtimeSessionRecord,
    response_id: str | None,
    response_turn_id: UUID,
) -> AgentMessage | None:
    message_id = _voice_agent_event_followup_message_id(
        session=session,
        response_id=response_id,
        response_turn_id=response_turn_id,
    )
    getter = getattr(store, "get_agent_message", None)
    if callable(getter):
        existing = await getter(message_id)
        if existing is not None:
            return existing
    lister = getattr(store, "list_agent_messages", None)
    if not callable(lister):
        return None
    messages = await lister(
        session.run_id,
        agent_id="realtime-conversation-host",
        direction="all",
        limit=1000,
    )
    for message in reversed(messages):
        payload = message.payload or {}
        if message.task_type != "summarize_realtime_turn_context":
            continue
        if payload.get("workflow") != "realtime_voice_agent_event_followup_v1":
            continue
        if payload.get("realtime_session_id") != str(session.realtime_session_id):
            continue
        if response_id and payload.get("voice_agent_response_id") == response_id:
            return message
        if payload.get("response_turn_id") == str(response_turn_id):
            return message
    return None


def _voice_agent_event_followup_message_id(
    *,
    session: RealtimeSessionRecord,
    response_id: str | None,
    response_turn_id: UUID,
) -> UUID:
    stable_response_key = response_id or str(response_turn_id)
    return uuid5(
        NAMESPACE_URL,
        (
            "all-about-llms:realtime_voice_agent_event_followup:"
            f"{session.run_id}:{session.realtime_session_id}:{stable_response_key}"
        ),
    )


def _voice_agent_failure_followup_message_id(
    *,
    session: RealtimeSessionRecord,
    response_id: str | None,
    turn_id: str | None,
    event_id: int | None,
) -> UUID:
    stable_failure_key = response_id or turn_id or str(event_id or "unknown")
    return uuid5(
        NAMESPACE_URL,
        (
            "all-about-llms:realtime_voice_agent_failure_followup:"
            f"{session.run_id}:{session.realtime_session_id}:{stable_failure_key}"
        ),
    )


def _safe_voice_failure_reason(reason: str) -> str:
    return _redact_realtime_string(reason)[:500]


def _redact_realtime_string(value: str) -> str:
    return redact_realtime_string(value)


def _uuid_or_none(value: str | None) -> UUID | None:
    try:
        return UUID(str(value)) if value else None
    except (TypeError, ValueError):
        return None


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


@app.post("/api/realtime-sessions/{realtime_session_id}/status")
async def update_realtime_session_status(
    realtime_session_id: UUID,
    request: RealtimeSessionStatusUpdate,
    store: PostgresStore = Depends(get_store),
) -> RealtimeSessionRecord:
    session = await store.update_realtime_session_status(
        realtime_session_id,
        request.status,
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Realtime session not found")
    await store.append_event(
        RunEvent(
            run_id=session.run_id,
            event_type="realtime_session_status_updated",
            actor="realtime-conversation-host",
            payload={
                "realtime_session_id": str(session.realtime_session_id),
                "status": session.status.value,
                "reason": request.reason,
            },
        )
    )
    return session


async def _latest_unresolved_interruption_control_event_id(
    store: PostgresStore, session: RealtimeSessionRecord
) -> int | None:
    events = await store.list_events(session.run_id, limit=500)
    turns = await store.list_conversation_turns(session.run_id)
    resolved_event_ids = {
        int(str(event_id))
        for turn in turns
        for event_id in [turn.metadata.get("interruption_control_event_id")]
        if _is_int_like(event_id)
    }
    control_events = [
        event
        for event in events
        if event.event_type == "realtime_session_control_recorded"
        and event.event_id is not None
        and event.event_id not in resolved_event_ids
        and (event.payload or {}).get("action") == "interrupt"
        and (event.payload or {}).get("realtime_session_id")
        == str(session.realtime_session_id)
    ]
    if not control_events:
        return None
    latest = max(control_events, key=lambda event: event.event_id or -1)
    return latest.event_id


def _is_int_like(value) -> bool:
    try:
        int(str(value))
    except (TypeError, ValueError):
        return False
    return True


async def _create_realtime_brief_task(
    *,
    store: PostgresStore,
    session: RealtimeSessionRecord,
    request: RealtimeTurnCreate,
    source_turn_id: UUID,
    response_turn_id: UUID | None,
    routed_intent: str | None,
    artifact_ids: list[str],
    spoken_response: RealtimeSpokenResponsePlan | None = None,
) -> UUID:
    message = AgentMessage(
        run_id=session.run_id,
        sender_agent_id="realtime-conversation-host",
        recipient_agent_id="realtime-conversation-host",
        task_type="summarize_realtime_turn_context",
        payload={
            "workflow": "realtime_turn_followup_v1",
            "topic": request.topic or "realtime conversation turn",
            "realtime_session_id": str(session.realtime_session_id),
            "provider": session.provider,
            "provider_session_id": session.provider_session_id,
            "audio_mode": session.audio_mode,
            "voice": session.voice,
            "source_turn_id": str(source_turn_id),
            "response_turn_id": str(response_turn_id) if response_turn_id else None,
            "routed_intent": routed_intent,
            "artifact_ids": artifact_ids,
            "speaker": request.speaker,
            "modality": request.modality,
            "interrupted": request.interrupted,
            "asset_count": len(request.assets),
            "transcript_excerpt": (request.transcript or "")[:240],
            "spoken_response": (
                spoken_response.model_dump(mode="json") if spoken_response else None
            ),
        },
    )
    await store.record_agent_message(message)
    await store.append_event(
        RunEvent(
            run_id=session.run_id,
            event_type="agent_message_accepted",
            actor=message.sender_agent_id,
            payload=public_a2a_message_event_payload(message),
        )
    )
    await store.append_event(
        RunEvent(
            run_id=session.run_id,
            event_type="realtime_conversation_brief_task_created",
            actor="realtime-conversation-host",
            payload={
                "message_id": str(message.message_id),
                "realtime_session_id": str(session.realtime_session_id),
                "source_turn_id": str(source_turn_id),
                "response_turn_id": str(response_turn_id) if response_turn_id else None,
                "routed_intent": routed_intent,
                "interrupted": request.interrupted,
                "modality": request.modality,
            },
        )
    )
    return message.message_id


def _build_realtime_spoken_response_plan(
    *,
    session: RealtimeSessionRecord,
    request: RealtimeTurnCreate,
    routed: ConversationRouteResult,
    interruption_control_event_id: int | None,
) -> RealtimeSpokenResponsePlan:
    output_channel = _realtime_output_channel(session.provider, session.audio_mode)
    interrupt_previous = request.interrupted or interruption_control_event_id is not None
    provider_payload = {
        "provider": session.provider,
        "transport": output_channel,
        "text": routed.response_text,
        "voice": session.voice,
        "audio_mode": session.audio_mode,
        "interrupt_previous": interrupt_previous,
        "source_turn_id": str(routed.turn_id),
        "response_turn_id": (
            str(routed.response_turn_id) if routed.response_turn_id else None
        ),
        "latency_class": "realtime_interrupt",
        "smoke_proof_status": (
            "rehearsal_only"
            if session.metadata.get("not_provider_backed")
            else "provider_backed"
        ),
    }
    if session.provider == "gemma4_realtime":
        provider_payload["command"] = "gemma4_kokoro.voice_turn"
        provider_payload["transport_framework"] = session.metadata.get(
            "transport_framework", "livekit"
        )
        provider_payload["response_id"] = str(routed.response_turn_id or routed.turn_id)
        provider_payload["gemma_generation_id"] = f"gemma-{routed.turn_id}"
        provider_payload["kokoro_buffer_id"] = f"kokoro-{routed.turn_id}"
        provider_payload["audio_track_id"] = f"livekit-audio-{session.realtime_session_id}"
        provider_payload["runtime_actions"] = [
            "drop_outbound_audio_on_barge_in",
            "cancel_gemma_generation",
            "clear_kokoro_output_buffer",
        ]
    elif session.provider == "openai_realtime":
        provider_payload["command"] = "response.create"
        provider_payload["modalities"] = ["audio", "text"]
    elif session.provider == "elevenlabs":
        provider_payload["command"] = "conversation.response"
        provider_payload["websocket_url_required"] = session.has_websocket_url
    elif session.provider == "cartesia":
        provider_payload["command"] = "tts.websocket.speak"
        provider_payload["websocket_url_required"] = session.has_websocket_url
    else:
        provider_payload["command"] = "browser.speech_synthesis.speak"

    return RealtimeSpokenResponsePlan(
        realtime_session_id=session.realtime_session_id,
        provider=session.provider,
        provider_session_id=session.provider_session_id,
        voice=session.voice,
        audio_mode=session.audio_mode,
        output_channel=output_channel,
        source_turn_id=routed.turn_id,
        response_turn_id=routed.response_turn_id,
        text=routed.response_text,
        interrupt_previous=interrupt_previous,
        gemma_generation_id=provider_payload.get("gemma_generation_id"),
        kokoro_buffer_id=provider_payload.get("kokoro_buffer_id"),
        audio_track_id=provider_payload.get("audio_track_id"),
        provider_payload=provider_payload,
        metadata={
            "workflow": "realtime_spoken_response_plan_v1",
            "routed_intent": routed.routed_intent.value,
            "interruption_control_event_id": interruption_control_event_id,
            "latency_class": "realtime_interrupt",
            "smoke_proof_status": (
                "rehearsal_only"
                if session.metadata.get("not_provider_backed")
                else "provider_backed"
            ),
            "browser_speech_recognition": bool(
                request.metadata.get("browser_speech_recognition")
            ),
            "auto_voice_route": bool(request.metadata.get("auto_voice_route")),
        },
    )


def _realtime_output_channel(provider: str, audio_mode: str) -> str:
    if audio_mode == "text_to_speech":
        return "tts_output"
    if provider == "gemma4_realtime":
        return "gemma4_kokoro_livekit_audio"
    if provider == "openai_realtime":
        return "openai_realtime_response"
    if provider == "elevenlabs":
        return "elevenlabs_conversation_audio"
    if provider == "cartesia":
        return "cartesia_tts_websocket"
    return "browser_speech_synthesis"


@app.get("/api/runs/{run_id}/events")
async def get_run_events(
    run_id: UUID,
    after_event_id: int | None = Query(default=None, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    store: PostgresStore = Depends(get_store),
) -> dict[str, object]:
    events = await store.list_events(
        run_id,
        limit=limit,
        after_event_id=after_event_id,
    )
    return {"events": [event.model_dump(mode="json") for event in events]}


@app.post("/api/runs/{run_id}/sources")
async def record_source(
    run_id: UUID,
    request: SourceRecordCreate,
    store: PostgresStore = Depends(get_store),
) -> SourceRecord:
    if await store.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    source = SourceRecord(run_id=run_id, **request.model_dump())
    await store.record_source(source)
    await store.append_event(
        RunEvent(
            run_id=run_id,
            event_type="source_recorded",
            actor="source-ledger-agent",
            payload=source.model_dump(mode="json"),
        )
    )
    return source


@app.get("/api/runs/{run_id}/sources")
async def get_sources(
    run_id: UUID, store: PostgresStore = Depends(get_store)
) -> dict[str, object]:
    sources = await store.list_sources(run_id)
    return {"sources": [source.model_dump(mode="json") for source in sources]}


@app.post("/api/runs/{run_id}/source-ledger")
async def build_source_ledger_snapshot(
    run_id: UUID,
    request: SourceLedgerSnapshotRequest,
    store: PostgresStore = Depends(get_store),
) -> SourceLedgerSnapshotResult:
    workflow = SourceLedgerWorkflow(store)
    try:
        return await workflow.build(run_id, request)
    except SourceLedgerRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.post("/api/runs/{run_id}/retrieval-quality-ledger")
async def build_retrieval_quality_ledger(
    run_id: UUID,
    request: RetrievalQualityLedgerRequest,
    store: PostgresStore = Depends(get_store),
    services: ContentWorkflowServices = Depends(get_content_workflow_services),
) -> RetrievalQualityLedgerResult:
    workflow = RetrievalQualityLedgerWorkflow(store, services.reranker_provider)
    try:
        return await workflow.build(run_id, request)
    except RetrievalQualityLedgerRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.post("/api/runs/{run_id}/provider-ops-ledger")
async def build_provider_operations_ledger(
    run_id: UUID,
    request: ProviderOperationsLedgerRequest,
    store: PostgresStore = Depends(get_store),
) -> ProviderOperationsLedgerResult:
    workflow = ProviderOperationsLedgerWorkflow(store)
    try:
        return await workflow.build(run_id, request)
    except ProviderOperationsLedgerRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.post("/api/runs/{run_id}/provider-smoke")
async def build_provider_smoke_ledger(
    run_id: UUID,
    request: ProviderSmokeRunRequest,
    store: PostgresStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
    services: ContentWorkflowServices = Depends(get_content_workflow_services),
    provider_factory=Depends(get_realtime_provider_factory),
) -> ProviderSmokeRunResult:
    workflow = ProviderSmokeWorkflow(
        store,
        settings,
        services,
        realtime_provider_factory=provider_factory,
    )
    try:
        return await workflow.build(run_id, request)
    except ProviderSmokeRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.post("/api/runs/{run_id}/realtime-dialogue-ledger")
async def build_realtime_dialogue_ledger(
    run_id: UUID,
    request: RealtimeDialogueLedgerRequest,
    store: PostgresStore = Depends(get_store),
) -> RealtimeDialogueLedgerResult:
    workflow = RealtimeDialogueLedgerWorkflow(store)
    try:
        return await workflow.build(run_id, request)
    except RealtimeDialogueLedgerRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.post("/api/runs/{run_id}/realtime-voice-timing-ledger")
async def build_realtime_voice_timing_ledger(
    run_id: UUID,
    request: RealtimeVoiceTimingLedgerRequest,
    store: PostgresStore = Depends(get_store),
) -> RealtimeVoiceTimingLedgerResult:
    workflow = RealtimeVoiceTimingLedgerWorkflow(store)
    try:
        return await workflow.build(run_id, request)
    except RealtimeVoiceTimingLedgerRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.post("/api/runs/{run_id}/model-routing-ledger")
async def build_model_routing_ledger(
    run_id: UUID,
    request: ModelRoutingLedgerRequest,
    store: PostgresStore = Depends(get_store),
) -> ModelRoutingLedgerResult:
    workflow = ModelRoutingLedgerWorkflow(store)
    try:
        return await workflow.build(run_id, request)
    except ModelRoutingLedgerRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.post("/api/runs/{run_id}/a2a-collaboration-graph")
async def build_a2a_collaboration_graph(
    run_id: UUID,
    request: A2ACollaborationGraphRequest,
    store: PostgresStore = Depends(get_store),
) -> A2ACollaborationGraphResult:
    workflow = A2ACollaborationGraphWorkflow(store)
    try:
        return await workflow.build(run_id, request)
    except A2ACollaborationGraphRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.post("/api/runs/{run_id}/skill-usage-ledger")
async def build_skill_usage_ledger(
    run_id: UUID,
    request: SkillUsageLedgerRequest,
    store: PostgresStore = Depends(get_store),
) -> SkillUsageLedgerResult:
    workflow = SkillUsageLedgerWorkflow(store)
    try:
        return await workflow.build(run_id, request)
    except SkillUsageLedgerRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.post("/api/runs/{run_id}/runtime-health-ledger")
async def build_runtime_health_ledger(
    run_id: UUID,
    request: RuntimeHealthLedgerRequest,
    settings: Settings = Depends(get_settings),
    store: PostgresStore = Depends(get_store),
) -> RuntimeHealthLedgerResult:
    workflow = RuntimeHealthLedgerWorkflow(
        store,
        project_root=PROJECT_ROOT,
        settings=settings,
    )
    try:
        return await workflow.build(run_id, request)
    except RuntimeHealthLedgerRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.post("/api/runs/{run_id}/cockpit-walkthrough-ledger")
async def build_cockpit_walkthrough_ledger(
    run_id: UUID,
    request: CockpitWalkthroughLedgerRequest,
    settings: Settings = Depends(get_settings),
    store: PostgresStore = Depends(get_store),
) -> CockpitWalkthroughLedgerResult:
    workflow = CockpitWalkthroughLedgerWorkflow(store)
    try:
        return await workflow.build(
            run_id,
            request,
            provider_readiness=build_provider_readiness(settings),
        )
    except CockpitWalkthroughLedgerRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.post("/api/runs/{run_id}/research-freshness-ledger")
async def build_research_freshness_ledger(
    run_id: UUID,
    request: ResearchFreshnessLedgerRequest,
    store: PostgresStore = Depends(get_store),
) -> ResearchFreshnessLedgerResult:
    workflow = ResearchFreshnessLedgerWorkflow(store)
    try:
        return await workflow.build(run_id, request)
    except ResearchFreshnessLedgerRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.post("/api/runs/{run_id}/foundation-audit")
async def build_foundation_audit(
    run_id: UUID,
    request: FoundationAuditRequest,
    store: PostgresStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
) -> FoundationAuditResult:
    workflow = FoundationAuditWorkflow(store, settings=settings, project_root=PROJECT_ROOT)
    try:
        return await workflow.build(run_id, request)
    except FoundationAuditRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.post("/api/runs/{run_id}/claims")
async def record_claim(
    run_id: UUID,
    request: ClaimRecordCreate,
    store: PostgresStore = Depends(get_store),
) -> ClaimRecord:
    if await store.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    claim = ClaimRecord(run_id=run_id, **request.model_dump())
    await store.record_claim(claim)
    await store.append_event(
        RunEvent(
            run_id=run_id,
            event_type="claim_recorded",
            actor=request.reviewer_agent_id or "claim-verification-agent",
            payload=claim.model_dump(mode="json"),
        )
    )
    return claim


@app.get("/api/runs/{run_id}/claims")
async def get_claims(
    run_id: UUID, store: PostgresStore = Depends(get_store)
) -> dict[str, object]:
    claims = await store.list_claims(run_id)
    return {"claims": [claim.model_dump(mode="json") for claim in claims]}


@app.post("/api/runs/{run_id}/artifacts")
async def record_artifact(
    run_id: UUID,
    request: ArtifactRecordCreate,
    store: PostgresStore = Depends(get_store),
) -> ArtifactRecord:
    if await store.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    artifact = ArtifactRecord(run_id=run_id, **request.model_dump())
    await store.record_artifact(artifact)
    await store.append_event(
        RunEvent(
            run_id=run_id,
            event_type="artifact_recorded",
            actor="artifact-librarian",
            payload=artifact.model_dump(mode="json"),
        )
    )
    return artifact


@app.get("/api/runs/{run_id}/artifacts")
async def get_artifacts(
    run_id: UUID, store: PostgresStore = Depends(get_store)
) -> dict[str, object]:
    artifacts = await store.list_artifacts(run_id)
    return {
        "artifacts": [artifact.model_dump(mode="json") for artifact in artifacts]
    }


@app.post("/api/runs/{run_id}/interactive-note")
async def generate_interactive_run_note(
    run_id: UUID,
    request: InteractiveRunNoteRequest,
    store: PostgresStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
) -> InteractiveRunNoteResult:
    workflow = InteractiveRunNoteWorkflow(
        store,
        artifacts_root=_resolve_artifacts_root(settings),
    )
    try:
        return await workflow.generate(run_id, request)
    except InteractiveRunNoteRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.post("/api/runs/{run_id}/obsidian-review-note")
async def generate_obsidian_review_note(
    run_id: UUID,
    request: ObsidianReviewNoteRequest,
    store: PostgresStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
) -> ObsidianReviewNoteResult:
    workflow = ObsidianReviewNoteWorkflow(
        store,
        vault_path=settings.obsidian_vault_path,
    )
    try:
        return await workflow.generate(run_id, request)
    except ObsidianReviewNoteRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.post("/api/runs/{run_id}/obsidian-memory-promotion")
async def generate_obsidian_memory_promotion(
    run_id: UUID,
    request: ObsidianMemoryPromotionRequest,
    store: PostgresStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
) -> ObsidianMemoryPromotionResult:
    workflow = ObsidianMemoryPromotionWorkflow(
        store,
        vault_path=settings.obsidian_vault_path,
    )
    try:
        return await workflow.generate(run_id, request)
    except ObsidianMemoryPromotionRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.get("/api/runs/{run_id}/guardrail-audits")
async def get_guardrail_audits(
    run_id: UUID,
    artifact_id: UUID | None = None,
    store: PostgresStore = Depends(get_store),
) -> dict[str, object]:
    if await store.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    audits = await store.list_guardrail_audits(run_id, artifact_id=artifact_id)
    return {"audits": [audit.model_dump(mode="json") for audit in audits]}


@app.post("/api/runs/{run_id}/publish-readiness")
async def check_publish_readiness(
    run_id: UUID,
    request: PublishReadinessRequest,
    settings: Settings = Depends(get_settings),
    store: PostgresStore = Depends(get_store),
) -> PublishReadinessResult:
    workflow = PublishReadinessWorkflow(
        store,
        credential_env_values=settings.publication_credential_env_values(),
    )
    try:
        return await workflow.run(run_id, request)
    except PublishReadinessRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.get("/api/runs/{run_id}/feedback")
async def get_run_feedback(
    run_id: UUID,
    status: FeedbackStatus | None = None,
    store: PostgresStore = Depends(get_store),
) -> dict[str, object]:
    if await store.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    feedback_items = await store.list_feedback(run_id, status=status)
    return {
        "feedback": [item.model_dump(mode="json") for item in feedback_items]
    }


@app.post("/api/runs/{run_id}/project-memory")
async def record_project_memory(
    run_id: UUID,
    request: ProjectMemoryRecordRequest,
    store: PostgresStore = Depends(get_store),
) -> ProjectMemoryRecordResult:
    workflow = ProjectMemoryWorkflow(store)
    try:
        return await workflow.record(run_id, request)
    except ProjectMemoryRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    except ProjectMemoryAgentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Agent not found") from exc


@app.post("/api/runs/{run_id}/project-memory/retrieval")
async def retrieve_project_memory(
    run_id: UUID,
    request: ProjectMemoryRetrievalRequest,
    store: PostgresStore = Depends(get_store),
) -> ProjectMemoryRetrievalResult:
    workflow = ProjectMemoryRetrievalWorkflow(store)
    try:
        return await workflow.retrieve(run_id, request)
    except ProjectMemoryRetrievalRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    except ProjectMemoryRetrievalAgentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Agent not found") from exc


@app.post("/api/runs/{run_id}/feedback-resolution-ledger")
async def build_feedback_resolution_ledger(
    run_id: UUID,
    request: FeedbackResolutionLedgerRequest,
    store: PostgresStore = Depends(get_store),
) -> FeedbackResolutionLedgerResult:
    workflow = FeedbackResolutionLedgerWorkflow(store)
    try:
        return await workflow.build(run_id, request)
    except FeedbackResolutionLedgerRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.post("/api/memories")
async def record_memory(
    request: AgentMemoryCreate, store: PostgresStore = Depends(get_store)
) -> AgentMemory:
    if request.run_id and await store.get_run(request.run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if get_agent_card(request.agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    memory = AgentMemory(**request.model_dump())
    await store.record_memory(memory)
    if memory.run_id:
        await store.append_event(
            RunEvent(
                run_id=memory.run_id,
                event_type="memory_recorded",
                actor=memory.agent_id,
                payload=safe_realtime_metadata(memory.model_dump(mode="json")),
            )
        )
    return memory


@app.post("/api/memories/search")
async def search_memories(
    request: MemorySearchRequest, store: PostgresStore = Depends(get_store)
) -> dict[str, object]:
    if request.agent_id and get_agent_card(request.agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    if request.run_id and await store.get_run(request.run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    results = await store.search_memories(
        agent_id=request.agent_id,
        run_id=request.run_id,
        include_global_memories=request.include_global_memories,
        query_embedding=request.query_embedding,
        limit=request.limit,
    )
    return {
        "memories": [
            MemorySearchResult(memory=memory, distance=distance).model_dump(mode="json")
            for memory, distance in results
        ]
    }


@app.get("/api/memories")
async def get_memories(
    agent_id: str | None = None,
    run_id: UUID | None = None,
    store: PostgresStore = Depends(get_store),
) -> dict[str, object]:
    memories = await store.list_memories(agent_id=agent_id, run_id=run_id)
    return {"memories": [memory.model_dump(mode="json") for memory in memories]}


@app.get("/api/runs/{run_id}/events/stream")
async def stream_run_events(
    run_id: UUID,
    after_event_id: int | None = Query(default=None, ge=0),
    once: bool = False,
    store: PostgresStore = Depends(get_store),
):
    if await store.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return StreamingResponse(
        _run_event_stream(
            store=store,
            run_id=run_id,
            after_event_id=after_event_id,
            once=once,
        ),
        media_type="text/event-stream",
    )


@app.post("/api/feedback")
async def record_feedback(
    feedback: FeedbackItem, store: PostgresStore = Depends(get_store)
) -> FeedbackRoutingResult:
    workflow = FeedbackRoutingWorkflow(store)
    try:
        return await workflow.run(feedback)
    except FeedbackRoutingRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    except FeedbackRoutingAgentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/planning/feedback")
async def ingest_planning_feedback(
    request: PlanningFeedbackIngestRequest,
    store: PostgresStore = Depends(get_store),
) -> PlanningFeedbackIngestResult:
    if await store.get_run(request.run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")

    workflow = FeedbackRoutingWorkflow(store)
    routed_items: list[PlanningFeedbackRoutedItem] = []
    for item in request.items:
        metadata = {
            "source": "planning_html_feedback",
            "surface": "separate_planning_html",
            "feedback_kind": "planning_surface_suggestion",
            "artifact": request.artifact,
            "planning_feedback_id": item.id,
            "planning_focus": item.focus,
            "focus": _normalize_planning_feedback_focus(item.focus),
            "priority": item.priority,
            "summary": item.summary,
            "captured_at": item.created_at,
        }
        try:
            routed = await workflow.run(
                FeedbackItem(
                    run_id=request.run_id,
                    author=request.author,
                    target_agent_id=item.route_to,
                    feedback_text=item.suggestion,
                    metadata=metadata,
                )
            )
        except FeedbackRoutingRunNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Run not found") from exc
        except FeedbackRoutingAgentNotFoundError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        routed_items.append(
            PlanningFeedbackRoutedItem(
                input_id=item.id,
                feedback_id=routed.feedback.feedback_id,
                routed_agent_id=routed.routed_agent_id,
                route_reason=routed.route_reason,
                task_message_id=routed.task_message_id,
                support_task_message_ids=routed.support_task_message_ids,
                status=routed.feedback.status,
            )
        )

    event = await store.append_event(
        RunEvent(
            run_id=request.run_id,
            event_type="planning_feedback_ingested",
            actor="forward-deployed-engineer",
            payload={
                "artifact": request.artifact,
                "routed_count": len(routed_items),
                "routed_items": [
                    routed_item.model_dump(mode="json")
                    for routed_item in routed_items
                ],
            },
        )
    )
    return PlanningFeedbackIngestResult(
        run_id=request.run_id,
        artifact=request.artifact,
        routed_count=len(routed_items),
        routed_items=routed_items,
        event_id=event.event_id,
        summary=(
            f"Routed {len(routed_items)} planning suggestion(s) from "
            f"{request.artifact} into durable agent feedback."
        ),
    )


@app.post("/api/feedback/{feedback_id}/resolve")
async def resolve_feedback(
    feedback_id: UUID,
    request: FeedbackResolutionRequest,
    store: PostgresStore = Depends(get_store),
) -> FeedbackResolutionResult:
    existing = await store.get_feedback(feedback_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Feedback item not found")
    updated = await store.update_feedback_status(
        feedback_id=feedback_id,
        status=request.status,
        resolver=request.resolver,
        resolution_notes=request.resolution_notes,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Feedback item not found")

    open_items = await store.list_feedback(existing.run_id, status=FeedbackStatus.OPEN)
    run = await store.get_run(existing.run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    next_status = request.run_status or run.status
    if (
        request.run_status is None
        and not open_items
        and request.status == FeedbackStatus.RESOLVED
    ):
        messages = await store.list_agent_messages(existing.run_id)
        has_pending_linked_tasks = any(
            _message_links_feedback(message, feedback_id)
            and message.status
            in {
                AgentTaskStatus.ACCEPTED,
                AgentTaskStatus.CLAIMED,
                AgentTaskStatus.IN_PROGRESS,
                AgentTaskStatus.WAITING_FOR_HUMAN,
                AgentTaskStatus.BLOCKED,
            }
            for message in messages
        )
        next_status = RunStatus.RUNNING if has_pending_linked_tasks else RunStatus.COMPLETED
    if next_status != run.status:
        await store.update_run_status(existing.run_id, next_status)

    event = await store.append_event(
        RunEvent(
            run_id=existing.run_id,
            event_type="feedback_resolved",
            actor="forward-deployed-engineer",
            payload={
                "feedback_id": str(feedback_id),
                "status": updated.status.value,
                "resolver": request.resolver,
                "run_status": next_status.value,
                "open_feedback_count": len(open_items),
            },
        )
    )
    resolution_ledger = None
    if request.build_resolution_ledger:
        resolution_ledger = await FeedbackResolutionLedgerWorkflow(store).build(
            existing.run_id,
            FeedbackResolutionLedgerRequest(record_artifact=True),
        )
    return FeedbackResolutionResult(
        feedback=updated,
        run_status=next_status,
        open_feedback_count=len(open_items),
        resolution_ledger=resolution_ledger,
        event_id=event.event_id,
        summary=(
            f"Feedback item {feedback_id} is {updated.status.value}; "
            f"{len(open_items)} open feedback item(s) remain."
        ),
    )


def _message_links_feedback(message: AgentMessage, feedback_id: UUID) -> bool:
    payload = message.payload or {}
    candidates = [
        payload.get("feedback_id"),
        payload.get("source_feedback_id"),
    ]
    if isinstance(payload.get("feedback"), dict):
        candidates.append(payload["feedback"].get("feedback_id"))
    if isinstance(payload.get("metadata"), dict):
        candidates.append(payload["metadata"].get("feedback_id"))
    return str(feedback_id) in {str(candidate) for candidate in candidates if candidate}


def _normalize_planning_feedback_focus(focus: str) -> str:
    return {
        "agent-roster": "protocol",
        "realtime-audio": "audio",
        "source-grounding": "source",
        "content-output": "content",
        "planning-html": "planning",
    }.get(focus, focus)


@app.get("/api/voice/providers")
async def voice_providers(settings: Settings = Depends(get_settings)):
    return {
        "default_provider": settings.realtime_default_provider,
        "configured_providers": settings.configured_realtime_providers(),
        "supported_providers": [
            "gemma4_realtime",
            "open_source_realtime",
            "openai_realtime",
            "elevenlabs",
            "cartesia",
        ],
    }


def _default_realtime_instructions(goal: str) -> str:
    return (
        "You are the realtime conversation host for a local-first multi-agent "
        "content studio. Keep dialogue natural, support interruption and "
        "clarification, summarize background agent progress briefly, and route "
        f"the user's goal into durable specialist work. Current run goal: {goal}"
    )


def _transport_grant_from_provider_response(
    *,
    provider_response,
    request: RealtimeSessionCreateRequest,
    run_id: UUID,
    default_room_name: str,
    default_participant_identity: str,
    default_agent_identity: str,
) -> RealtimeTransportGrant:
    raw_transport = provider_response.transport or {}
    metadata = provider_response.metadata or {}
    framework = (
        request.transport_framework
        or raw_transport.get("framework")
        or metadata.get("transport_framework")
        or metadata.get("connection_transport")
        or "livekit"
    )
    token = raw_transport.get("token")
    return RealtimeTransportGrant(
        framework=str(framework),
        url=raw_transport.get("url") or metadata.get("livekit_url"),
        room_name=raw_transport.get("room_name")
        or metadata.get("room_name")
        or default_room_name,
        participant_identity=raw_transport.get("participant_identity")
        or metadata.get("participant_identity")
        or default_participant_identity,
        agent_identity=raw_transport.get("agent_identity")
        or metadata.get("agent_participant_identity")
        or default_agent_identity,
        token=token,
        has_token=bool(token or raw_transport.get("has_token")),
        token_persisted=False,
        expires_at_unix=raw_transport.get("expires_at_unix")
        or provider_response.expires_at_unix,
        metadata=dict(raw_transport.get("metadata") or {}),
    )


def _safe_transport_payload(
    transport: RealtimeTransportGrant | None,
) -> dict[str, object] | None:
    if transport is None:
        return None
    payload = transport.model_dump(mode="json")
    payload["token"] = None
    payload["token_persisted"] = False
    safe_payload = _safe_realtime_metadata(payload)
    safe_payload["token"] = None
    safe_payload["token_persisted"] = False
    return safe_payload


def _safe_realtime_metadata(metadata: dict[str, object]) -> dict[str, object]:
    return safe_realtime_metadata(metadata)


def _safe_realtime_metadata_value(value: object) -> object:
    return safe_realtime_metadata_value(value)


def _realtime_metadata_key_is_sensitive(key: object) -> bool:
    return realtime_metadata_key_is_sensitive(key)


def _normalize_realtime_metadata_key(key: str) -> str:
    return normalize_realtime_metadata_key(key)


def _resolve_artifacts_root(settings: Settings) -> Path:
    root = settings.artifacts_root
    if root.is_absolute():
        return root
    return PROJECT_ROOT / root


@app.get("/api/boundaries")
async def boundaries():
    return {
        "product_app": [
            "voice_text_conversation",
            "draft_previews",
            "source_ledger",
            "artifact_browser",
            "feedback_controls",
            "voice_settings",
            "run_activity",
            "resume_controls",
        ],
        "planning_html": [
            "animated_architecture_maps",
            "agent_network",
            "model_routing_diagrams",
            "data_flow",
            "guardrail_loops",
            "open_decisions",
            "risks",
            "revision_history",
        ],
        "excluded": [
            "sqlite",
            "project_management_board",
            "planning_html_inside_product_app",
        ],
    }
