import os
from pathlib import Path
from uuid import UUID

from all_about_llms.config import Settings
from all_about_llms.contracts import (
    ArtifactRecord,
    ArtifactType,
    RunEvent,
    RuntimeHealthCheck,
    RuntimeHealthLedgerRequest,
    RuntimeHealthLedgerResult,
    RuntimeHealthStatus,
)
from all_about_llms.voice_agent.benchmark import (
    VoiceEdgeBenchmarkConfig,
    load_wav_pcm_s16le,
    run_voice_edge_benchmark,
)
from all_about_llms.voice_agent.edge import (
    FallbackVoiceEdgeClient,
    PersistentRustVoiceEdgeClient,
    RustVoiceEdgeHttpClient,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
LIVE_POSTGRES_EVIDENCE_EVENTS = {
    "durable_storage_setup_completed",
    "live_postgres_smoke_passed",
    "runtime_health_live_postgres_connected",
}


class RuntimeHealthLedgerError(RuntimeError):
    """Base error for runtime health ledger generation."""


class RuntimeHealthLedgerRunNotFoundError(RuntimeHealthLedgerError):
    """Raised when a run cannot be found for runtime health work."""


class RuntimeHealthLedgerWorkflow:
    """Build a local runtime health ledger without shelling out from the API path."""

    def __init__(
        self,
        store,
        *,
        project_root: Path | None = None,
        settings: Settings | None = None,
    ):
        self._store = store
        self._project_root = project_root or PROJECT_ROOT
        self._settings = settings

    async def build(
        self, run_id: UUID, request: RuntimeHealthLedgerRequest
    ) -> RuntimeHealthLedgerResult:
        run = await self._store.get_run(run_id)
        if run is None:
            raise RuntimeHealthLedgerRunNotFoundError(f"Run not found: {run_id}")

        events = []
        artifacts = []
        checkpoints = []
        if request.include_run_evidence:
            if request.record_live_store_evidence and _is_postgres_store(self._store):
                await self._store.append_event(
                    RunEvent(
                        run_id=run_id,
                        event_type="runtime_health_live_postgres_connected",
                        actor="observability-agent",
                        payload={
                            "store_class": self._store.__class__.__name__,
                            "evidence": (
                                "Runtime health request retrieved run state and "
                                "can write events through the Postgres-backed store."
                            ),
                            "docker_command_executed": False,
                            "pg_isready_executed": False,
                        },
                    )
                )
            events = await self._store.list_events(run_id, limit=request.event_limit)
            artifacts = await self._store.list_artifacts(run_id)
            checkpoints = await self._list_run_checkpoints(run_id)

        checks = [
            _application_store_check(self._store, run, events, artifacts),
            _event_log_check(events, request.include_run_evidence),
            _live_postgres_evidence_check(events, self._store),
            _checkpoint_runtime_evidence_check(checkpoints, events),
        ]
        if request.include_static_checks:
            checks.extend(
                [
                    _postgres_schema_check(self._project_root),
                    _pgvector_schema_check(self._project_root),
                    _docker_compose_check(self._project_root),
                    _langgraph_postgres_checkpointer_check(self._project_root),
                    _no_sqlite_boundary_check(self._project_root),
                ]
            )
        else:
            checks.append(
                RuntimeHealthCheck(
                    check_id="static-runtime-surface-skipped",
                    title="Static runtime surface",
                    status=RuntimeHealthStatus.UNKNOWN,
                    component="static_runtime_surface",
                    requirement=(
                        "Static Postgres, pgvector, Docker, LangGraph, and no-SQLite "
                        "checks should be available before release."
                    ),
                    evidence=["Static runtime inspection was skipped by request."],
                    recommended_action=(
                        "Run the ledger with include_static_checks=true before "
                        "marking local runtime readiness."
                    ),
                    severity="operator",
                )
            )
        if request.include_voice_edge_benchmark:
            checks.append(
                await _voice_edge_benchmark_check(
                    self._project_root,
                    self._settings,
                )
            )

        ready_count = _count(checks, RuntimeHealthStatus.READY)
        degraded_count = _count(checks, RuntimeHealthStatus.DEGRADED)
        blocked_count = _count(checks, RuntimeHealthStatus.BLOCKED)
        unknown_count = _count(checks, RuntimeHealthStatus.UNKNOWN)
        status = _overall_status(blocked_count, degraded_count, unknown_count)
        result = RuntimeHealthLedgerResult(
            run_id=run_id,
            status=status,
            check_count=len(checks),
            ready_count=ready_count,
            degraded_count=degraded_count,
            blocked_count=blocked_count,
            unknown_count=unknown_count,
            checks=checks,
            summary=(
                f"Runtime health ledger: {ready_count}/{len(checks)} checks ready, "
                f"{degraded_count} degraded, {blocked_count} blocked, "
                f"{unknown_count} unknown."
            ),
        )

        voice_edge_check = _find_check(checks, "voice-edge-local-benchmark")
        if request.include_voice_edge_benchmark and voice_edge_check is not None:
            await self._store.append_event(
                RunEvent(
                    run_id=run_id,
                    event_type=(
                        "voice_edge_benchmark_passed"
                        if voice_edge_check.status == RuntimeHealthStatus.READY
                        else "voice_edge_benchmark_needs_attention"
                    ),
                    actor="observability-agent",
                    payload={
                        "status": voice_edge_check.status.value,
                        "component": voice_edge_check.component,
                        "severity": voice_edge_check.severity,
                        "evidence": voice_edge_check.evidence,
                    },
                )
            )

        if request.record_artifact:
            artifact = ArtifactRecord(
                run_id=run_id,
                artifact_type=ArtifactType.RUNTIME_HEALTH_LEDGER,
                title="Runtime health ledger",
                uri=f"artifact://runs/{run_id}/runtime-health-ledger",
                content=result.model_dump(
                    mode="json", exclude={"ledger_artifact_id", "event_id"}
                ),
                provenance={
                    "workflow": "runtime_health_ledger_v1",
                    "agent_id": "observability-agent",
                    "event_limit": request.event_limit,
                    "include_static_checks": request.include_static_checks,
                    "include_run_evidence": request.include_run_evidence,
                    "record_live_store_evidence": request.record_live_store_evidence,
                    "include_voice_edge_benchmark": (
                        request.include_voice_edge_benchmark
                    ),
                },
                revision_history=[
                    {
                        "actor": "observability-agent",
                        "note": (
                            "Captured Postgres, pgvector, Docker compose, "
                            "LangGraph checkpointing, event-log, checkpoint, "
                            "no-SQLite runtime boundaries, and local voice-edge "
                            "benchmark evidence."
                        ),
                    }
                ],
            )
            result.ledger_artifact_id = artifact.artifact_id
            artifact.content["ledger_artifact_id"] = str(artifact.artifact_id)
            await self._store.record_artifact(artifact)
            await self._store.append_event(
                RunEvent(
                    run_id=run_id,
                    event_type="artifact_recorded",
                    actor="artifact-librarian",
                    payload=artifact.model_dump(mode="json"),
                )
            )

        event = await self._store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="runtime_health_ledger_built",
                actor="observability-agent",
                payload={
                    "status": result.status.value,
                    "check_count": result.check_count,
                    "ready_count": result.ready_count,
                    "degraded_count": result.degraded_count,
                    "blocked_count": result.blocked_count,
                    "unknown_count": result.unknown_count,
                    "ledger_artifact_id": (
                        str(result.ledger_artifact_id)
                        if result.ledger_artifact_id
                        else None
                    ),
                },
            )
        )
        result.event_id = event.event_id
        return result

    async def _list_run_checkpoints(self, run_id: UUID):
        if not hasattr(self._store, "list_run_checkpoints"):
            return []
        return await self._store.list_run_checkpoints(run_id, limit=50)


def _application_store_check(store, run, events, artifacts) -> RuntimeHealthCheck:
    return RuntimeHealthCheck(
        check_id="application-store-api",
        title="Application store API",
        status=RuntimeHealthStatus.READY,
        component="durable_store",
        requirement=(
            "The app must be able to retrieve run state and list durable run "
            "evidence before any long-running agent pass continues."
        ),
        evidence=[
            f"Run {run.run_id} retrieved with status '{run.status.value}'.",
            f"Store implementation: {store.__class__.__name__}.",
            f"Fetched {len(events)} event(s) and {len(artifacts)} artifact(s) for the ledger request.",
        ],
        recommended_action=(
            "Keep this check in every operator preflight; it confirms app-level "
            "durable state access but does not replace live Docker/Postgres checks."
        ),
        severity="runtime",
    )


def _event_log_check(events, include_run_evidence: bool) -> RuntimeHealthCheck:
    if not include_run_evidence:
        return RuntimeHealthCheck(
            check_id="event-log-runtime-evidence",
            title="Event log runtime evidence",
            status=RuntimeHealthStatus.UNKNOWN,
            component="event_log",
            requirement="Run events should be listable for timeline replay and recovery.",
            evidence=["Run evidence collection was skipped by request."],
            recommended_action="Run again with include_run_evidence=true.",
            severity="operator",
        )
    return RuntimeHealthCheck(
        check_id="event-log-runtime-evidence",
        title="Event log runtime evidence",
        status=RuntimeHealthStatus.READY,
        component="event_log",
        requirement="Run events should be listable for timeline replay and recovery.",
        evidence=[
            f"Fetched {len(events)} event(s) without requiring an in-memory fallback.",
            "The ledger appends its own runtime_health_ledger_built event after artifact recording.",
        ],
        recommended_action="Use the event stream or replay ledger when debugging run recovery.",
        severity="runtime",
    )


def _live_postgres_evidence_check(events, store) -> RuntimeHealthCheck:
    evidence_events = [
        event.event_type
        for event in events
        if event.event_type in LIVE_POSTGRES_EVIDENCE_EVENTS
    ]
    if evidence_events:
        return RuntimeHealthCheck(
            check_id="live-postgres-runtime-evidence",
            title="Live Postgres runtime evidence",
            status=RuntimeHealthStatus.READY,
            component="postgres_runtime",
            requirement=(
                "Live Postgres connectivity should be verified independently from "
                "static schema inspection."
            ),
            evidence=[
                "Found runtime evidence event(s): " + ", ".join(evidence_events),
                f"Store implementation: {store.__class__.__name__}.",
            ],
            recommended_action=(
                "Keep recording explicit live Postgres smoke events after operator "
                "preflight or CI live-database runs."
            ),
            severity="runtime",
        )
    if _is_postgres_store(store):
        return RuntimeHealthCheck(
            check_id="live-postgres-runtime-evidence",
            title="Live Postgres runtime evidence",
            status=RuntimeHealthStatus.READY,
            component="postgres_runtime",
            requirement=(
                "Live Postgres connectivity should be verified independently from "
                "static schema inspection."
            ),
            evidence=[
                "The current runtime health request completed through PostgresStore.",
                "Run-state and evidence reads completed before this check was built.",
                "No Docker or pg_isready command was executed from the API path.",
            ],
            recommended_action=(
                "Keep the explicit runtime_health_live_postgres_connected event "
                "enabled for durable operator evidence when possible."
            ),
            severity="runtime",
        )
    return RuntimeHealthCheck(
        check_id="live-postgres-runtime-evidence",
        title="Live Postgres runtime evidence",
        status=RuntimeHealthStatus.UNKNOWN,
        component="postgres_runtime",
        requirement=(
            "Live Postgres connectivity should be verified independently from "
            "static schema inspection."
        ),
        evidence=[
            "No explicit live Postgres smoke event was present in the run timeline.",
            "The API request path does not execute Docker or pg_isready commands.",
            f"Store implementation: {store.__class__.__name__}.",
        ],
        recommended_action=(
            "Run `docker compose up -d postgres`, then live Postgres tests or a "
            "small operator smoke that records a runtime evidence event."
        ),
        severity="operator",
    )


def _checkpoint_runtime_evidence_check(checkpoints, events) -> RuntimeHealthCheck:
    checkpoint_events = [
        event for event in events if event.event_type == "run_checkpoint_recorded"
    ]
    if checkpoints or checkpoint_events:
        return RuntimeHealthCheck(
            check_id="langgraph-checkpoint-runtime-evidence",
            title="Checkpoint runtime evidence",
            status=RuntimeHealthStatus.READY,
            component="langgraph_checkpointing",
            requirement=(
                "Long-running work should have checkpoint evidence before resume "
                "or time-travel debugging is trusted."
            ),
            evidence=[
                f"Fetched {len(checkpoints)} application checkpoint record(s).",
                f"Found {len(checkpoint_events)} checkpoint event(s).",
            ],
            recommended_action="Continue creating checkpoints before autonomous passes.",
            severity="runtime",
        )
    return RuntimeHealthCheck(
        check_id="langgraph-checkpoint-runtime-evidence",
        title="Checkpoint runtime evidence",
        status=RuntimeHealthStatus.UNKNOWN,
        component="langgraph_checkpointing",
        requirement=(
            "Long-running work should have checkpoint evidence before resume "
            "or time-travel debugging is trusted."
        ),
        evidence=["No checkpoint records or checkpoint events were found for this run."],
        recommended_action=(
            "Create a run checkpoint or autonomous pass checkpoint before relying "
            "on resume/time-travel behavior for this run."
        ),
        severity="operator",
    )


def _postgres_schema_check(project_root: Path) -> RuntimeHealthCheck:
    schema_path = project_root / "infra/postgres/001_foundation.sql"
    text = _read_text(schema_path)
    required = [
        "create table if not exists runs",
        "create table if not exists run_events",
        "create table if not exists run_checkpoints",
        "create table if not exists artifacts",
        "create table if not exists agent_memories",
    ]
    missing = [snippet for snippet in required if snippet not in text.lower()]
    return RuntimeHealthCheck(
        check_id="postgres-application-schema",
        title="Postgres application schema",
        status=RuntimeHealthStatus.BLOCKED if missing else RuntimeHealthStatus.READY,
        component="postgres_schema",
        requirement=(
            "Postgres must own runs, events, checkpoints, artifacts, feedback, "
            "sources, claims, worker profiles, and memory tables from v1."
        ),
        evidence=(
            [f"Schema file present: {schema_path.relative_to(project_root)}."]
            + (
                ["Required runtime tables are declared."]
                if not missing
                else ["Missing schema snippets: " + ", ".join(missing)]
            )
        ),
        recommended_action=(
            "Apply `uv run all-about-llms-admin setup-durable-storage` against "
            "the configured Postgres service."
        ),
        severity="foundation",
    )


def _pgvector_schema_check(project_root: Path) -> RuntimeHealthCheck:
    schema_path = project_root / "infra/postgres/001_foundation.sql"
    text = _read_text(schema_path).lower()
    missing = []
    if "create extension if not exists vector" not in text:
        missing.append("vector extension")
    if "embedding vector" not in text:
        missing.append("agent_memories.embedding vector column")
    return RuntimeHealthCheck(
        check_id="pgvector-memory-schema",
        title="pgvector memory schema",
        status=RuntimeHealthStatus.BLOCKED if missing else RuntimeHealthStatus.READY,
        component="pgvector_memory",
        requirement=(
            "Semantic retrieval memory should live in Postgres with pgvector, "
            "not a sidecar local database."
        ),
        evidence=(
            ["Schema declares pgvector extension and vector memory column."]
            if not missing
            else ["Missing pgvector pieces: " + ", ".join(missing)]
        ),
        recommended_action="Install pgvector in the Postgres image and reapply migrations.",
        severity="foundation",
    )


def _docker_compose_check(project_root: Path) -> RuntimeHealthCheck:
    compose_path = project_root / "docker-compose.yml"
    text = _read_text(compose_path).lower()
    required = [
        "postgres:",
        "pgvector/pgvector:pg16",
        "5432:5432",
        "pg_isready",
        "001_foundation.sql",
    ]
    missing = [snippet for snippet in required if snippet not in text]
    return RuntimeHealthCheck(
        check_id="docker-compose-postgres-service",
        title="Docker Postgres service",
        status=RuntimeHealthStatus.BLOCKED if missing else RuntimeHealthStatus.READY,
        component="docker_postgres",
        requirement=(
            "Local runs should have a reproducible Postgres + pgvector service "
            "definition with a healthcheck."
        ),
        evidence=(
            [
                f"Compose file present: {compose_path.relative_to(project_root)}.",
                "Postgres service uses the pgvector image and pg_isready healthcheck.",
            ]
            if not missing
            else ["Missing docker-compose snippets: " + ", ".join(missing)]
        ),
        recommended_action="Fix docker-compose.yml before starting long-running local runs.",
        severity="operator",
    )


def _langgraph_postgres_checkpointer_check(project_root: Path) -> RuntimeHealthCheck:
    checkpointing_path = project_root / "src/all_about_llms/orchestration/checkpointing.py"
    migrations_path = project_root / "src/all_about_llms/storage/migrations.py"
    checkpointing = _read_text(checkpointing_path)
    migrations = _read_text(migrations_path)
    required = {
        "AsyncPostgresSaver": checkpointing,
        "await saver.setup()": checkpointing,
        "setup_postgres_checkpointer": migrations,
    }
    missing = [snippet for snippet, text in required.items() if snippet not in text]
    return RuntimeHealthCheck(
        check_id="langgraph-postgres-checkpointer",
        title="LangGraph Postgres checkpointer",
        status=RuntimeHealthStatus.BLOCKED if missing else RuntimeHealthStatus.READY,
        component="langgraph_checkpointing",
        requirement=(
            "LangGraph-style orchestration must use Postgres checkpointing for "
            "resumable state machines and time-travel debugging."
        ),
        evidence=(
            [
                "checkpointing.py uses AsyncPostgresSaver.",
                "storage setup calls the LangGraph Postgres checkpointer setup.",
            ]
            if not missing
            else ["Missing checkpointer snippets: " + ", ".join(missing)]
        ),
        recommended_action=(
            "Restore AsyncPostgresSaver setup before running autonomous agents."
        ),
        severity="foundation",
    )


def _no_sqlite_boundary_check(project_root: Path) -> RuntimeHealthCheck:
    roots = [
        project_root / "src/all_about_llms",
        project_root / "infra",
        project_root / "docker-compose.yml",
        project_root / "pyproject.toml",
    ]
    sqlite_token = "sqlite"
    forbidden_tokens = [
        f"{sqlite_token}://",
        f"{sqlite_token}+aio{sqlite_token}",
        f"{sqlite_token}3",
        f"aio{sqlite_token}",
        f"from {sqlite_token}",
        f"import {sqlite_token}",
    ]
    hits = []
    for path in _iter_files(roots):
        text = _read_text(path).lower()
        for token in forbidden_tokens:
            if token in text:
                hits.append(f"{path.relative_to(project_root)} contains {token}")
    return RuntimeHealthCheck(
        check_id="no-sqlite-runtime-boundary",
        title="No SQLite runtime boundary",
        status=RuntimeHealthStatus.BLOCKED if hits else RuntimeHealthStatus.READY,
        component="durable_store",
        requirement=(
            "The local-first foundation must not include SQLite adapters, URLs, "
            "imports, or fallback paths."
        ),
        evidence=hits or ["No SQLite runtime adapter tokens found in app or infra files."],
        recommended_action=(
            "Remove SQLite adapters or fallback URLs; keep Postgres + pgvector as "
            "the only durable local store."
        ),
        severity="foundation",
    )


async def _voice_edge_benchmark_check(
    project_root: Path,
    settings: Settings | None,
) -> RuntimeHealthCheck:
    binary_path = _resolve_voice_edge_binary_path(project_root, settings)
    display_binary_path = _runtime_health_path_text(project_root, binary_path)
    binary_available = binary_path.is_file() and os.access(binary_path, os.X_OK)
    http_url = settings.rust_voice_edge_http_url if settings else None
    requirement = (
        "The realtime voice edge should prove low-latency VAD, speech-start "
        "detection, and barge-in cancellation before operator readiness is trusted."
    )
    if not binary_available and not http_url:
        return RuntimeHealthCheck(
            check_id="voice-edge-local-benchmark",
            title="Voice edge local benchmark",
            status=RuntimeHealthStatus.DEGRADED,
            component="realtime_voice_edge",
            requirement=requirement,
            evidence=[
                f"Rust voice-edge binary is missing or not executable at {display_binary_path}.",
                "No local VAD/barge-in benchmark was executed.",
            ],
            recommended_action=(
                "Build services/voice-edge, then rerun runtime health so the "
                "benchmark can record latency and FP/FN-style quality counts."
            ),
            severity="operator",
        )

    client_kwargs = dict(
        timeout_seconds=(
            settings.rust_voice_edge_timeout_seconds if settings else 1.0
        ),
        sample_rate=settings.gemma4_realtime_sample_rate if settings else 16_000,
        frame_ms=settings.rust_voice_edge_frame_ms if settings else 32,
        vad_backend=(
            settings.rust_voice_edge_vad_backend if settings else "deterministic_energy"
        ),
        target_vad_model=(
            settings.gemma4_realtime_rust_vad_model if settings else "silero-vad-rust"
        ),
        vad_model_path=settings.rust_voice_edge_vad_model_path if settings else None,
        allow_vad_fallback=(
            settings.rust_voice_edge_allow_vad_fallback if settings else True
        ),
        vad_threshold=settings.rust_voice_edge_vad_threshold if settings else 0.018,
        vad_probability_threshold=(
            settings.rust_voice_edge_vad_probability_threshold if settings else 0.5
        ),
        vad_session_pool_size=(
            settings.rust_voice_edge_vad_session_pool_size if settings else 4
        ),
        vad_stream_state_cache_size=(
            settings.rust_voice_edge_vad_stream_state_cache_size if settings else 512
        ),
        min_speech_frames=settings.rust_voice_edge_min_speech_frames if settings else 2,
        max_inbound_buffer_bytes=(
            settings.rust_voice_edge_max_inbound_buffer_bytes
            if settings
            else 16_000 * 2 * 30
        ),
        max_outbound_buffer_bytes=(
            settings.rust_voice_edge_max_outbound_buffer_bytes
            if settings
            else 16_000 * 2 * 2
        ),
    )
    jsonl_client = (
        PersistentRustVoiceEdgeClient(binary_path=binary_path, **client_kwargs)
        if binary_available
        else None
    )
    if http_url and jsonl_client is not None:
        client = FallbackVoiceEdgeClient(
            primary=RustVoiceEdgeHttpClient(base_url=http_url, **client_kwargs),
            fallback=jsonl_client,
        )
    elif http_url:
        client = RustVoiceEdgeHttpClient(base_url=http_url, **client_kwargs)
    else:
        client = jsonl_client
    try:
        speech_pcm_s16le = (
            load_wav_pcm_s16le(
                settings.rust_voice_edge_benchmark_speech_wav_path,
                expected_sample_rate=client.sample_rate,
            )
            if settings and settings.rust_voice_edge_benchmark_speech_wav_path
            else None
        )
        result = await run_voice_edge_benchmark(
            client,
            config=VoiceEdgeBenchmarkConfig(
                runs_per_scenario=1,
                concurrent_streams=max(2, min(client.vad_session_pool_size, 8)),
                concurrent_iterations=1,
                speech_pcm_s16le=speech_pcm_s16le,
                speech_source=(
                    f"wav:{settings.rust_voice_edge_benchmark_speech_wav_path}"
                    if settings and settings.rust_voice_edge_benchmark_speech_wav_path
                    else "synthetic_constant"
                ),
                max_speech_frames=(
                    settings.rust_voice_edge_benchmark_max_speech_frames
                    if settings
                    else 64
                ),
                frame_ms=client.frame_ms,
            ),
        )
    except Exception as exc:  # noqa: BLE001 - runtime health must record failures.
        return RuntimeHealthCheck(
            check_id="voice-edge-local-benchmark",
            title="Voice edge local benchmark",
            status=RuntimeHealthStatus.DEGRADED,
            component="realtime_voice_edge",
            requirement=requirement,
            evidence=[
                f"Benchmark failed for {http_url or display_binary_path}: {exc}",
                "The durable runtime can still operate, but realtime voice readiness is not proven.",
            ],
            recommended_action=(
                "Run `cargo test --offline` in services/voice-edge and "
                "`all-about-llms-admin benchmark-voice-edge` locally, then "
                "rerun this ledger."
            ),
            severity="runtime",
        )
    finally:
        await client.aclose()

    quality = result.get("quality", {})
    latency = result.get("latency", {})
    concurrency = result.get("concurrency", {})
    concurrency_quality = concurrency.get("quality", {})
    concurrency_latency = concurrency.get("latency", {})
    tuning = result.get("tuning", {})
    stimulus = result.get("stimulus", {})
    passed = result.get("status") == "passed"
    tuning_recommendations = [
        str(item)
        for item in tuning.get("recommendations", [])
        if str(item).strip()
    ]
    return RuntimeHealthCheck(
        check_id="voice-edge-local-benchmark",
        title="Voice edge local benchmark",
        status=RuntimeHealthStatus.READY if passed else RuntimeHealthStatus.DEGRADED,
        component="realtime_voice_edge",
        requirement=requirement,
        evidence=[
            f"Binary: {display_binary_path}.",
            f"HTTP sidecar URL: {http_url or 'not configured'}.",
            f"Benchmark status: {result.get('status')}.",
            f"Process mode: {result.get('process_mode')}.",
            (
                "Speech stimulus: "
                f"source={stimulus.get('speech_source')}, "
                f"frames={stimulus.get('speech_frame_count')}, "
                f"samples_per_frame={stimulus.get('samples_per_frame')}, "
                f"frame_ms={stimulus.get('frame_ms')}, "
                f"max_speech_frames={stimulus.get('max_speech_frames')}."
            ),
            (
                "Latency ms: "
                f"p50={latency.get('p50_ms')}, "
                f"p95={latency.get('p95_ms')}, "
                f"max={latency.get('max_ms')}, "
                f"count={latency.get('count')}."
            ),
            (
                "Quality counts: "
                f"false_positive={quality.get('false_positive_count')}, "
                f"missed_speech_start={quality.get('missed_speech_start_count')}, "
                f"missed_cancellation={quality.get('missed_cancellation_count')}."
            ),
            (
                "Concurrency probe: "
                f"enabled={concurrency.get('enabled')}, "
                f"streams={concurrency.get('streams')}, "
                f"iterations={concurrency.get('iterations')}, "
                f"requests={concurrency.get('request_count')}, "
                f"serialized_by_client={concurrency.get('serialized_by_client')}, "
                f"fallback_used={concurrency.get('fallback_used_count')}, "
                f"p95_ms={concurrency_latency.get('p95_ms')}, "
                f"max_ms={concurrency_latency.get('max_ms')}, "
                "missed_speech_start="
                f"{concurrency_quality.get('missed_speech_start_count')}."
            ),
            (
                "Tuning status: "
                f"{tuning.get('status', 'unknown')}; "
                f"recommended_pool={tuning.get('recommended_vad_session_pool_size')}, "
                "recommended_stream_cache="
                f"{tuning.get('recommended_vad_stream_state_cache_size')}, "
                "measured_serialized="
                f"{tuning.get('measured_serialized_by_client')}, "
                "target_single_p95_ms="
                f"{tuning.get('target_single_request_p95_ms')}, "
                "target_concurrency_p95_ms="
                f"{tuning.get('target_concurrency_p95_ms')}, "
                f"warnings={tuning.get('warnings', [])}."
            ),
        ],
        recommended_action=(
            " ".join(tuning_recommendations)
            if tuning_recommendations
            else (
                "Keep this local benchmark in runtime health, then add provider-backed "
                "LiveKit + Gemma/Kokoro smoke before claiming end-to-end voice readiness."
            )
        ),
        severity="runtime",
    )


def _resolve_voice_edge_binary_path(
    project_root: Path,
    settings: Settings | None,
) -> Path:
    binary_path = (
        settings.rust_voice_edge_binary_path
        if settings is not None
        else Path("services/voice-edge/target/debug/voice-edge")
    )
    binary_path = Path(binary_path)
    if binary_path.is_absolute():
        return binary_path
    return project_root / binary_path


def _runtime_health_path_text(project_root: Path, path: Path) -> str:
    try:
        relative_path = path.resolve().relative_to(project_root.resolve())
    except (OSError, RuntimeError, ValueError):
        return "<configured-path>"
    return relative_path.as_posix()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _iter_files(paths: list[Path]):
    for path in paths:
        if path.is_file():
            yield path
            continue
        if path.is_dir():
            for child in path.rglob("*"):
                if child.is_file() and child.suffix in {".py", ".sql", ".toml", ".yml"}:
                    yield child


def _count(checks: list[RuntimeHealthCheck], status: RuntimeHealthStatus) -> int:
    return sum(1 for check in checks if check.status == status)


def _find_check(
    checks: list[RuntimeHealthCheck],
    check_id: str,
) -> RuntimeHealthCheck | None:
    return next((check for check in checks if check.check_id == check_id), None)


def _overall_status(
    blocked_count: int, degraded_count: int, unknown_count: int
) -> RuntimeHealthStatus:
    if blocked_count:
        return RuntimeHealthStatus.BLOCKED
    if degraded_count:
        return RuntimeHealthStatus.DEGRADED
    if unknown_count:
        return RuntimeHealthStatus.DEGRADED
    return RuntimeHealthStatus.READY


def _is_postgres_store(store) -> bool:
    return store.__class__.__name__ == "PostgresStore"
