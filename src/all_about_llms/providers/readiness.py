from urllib.parse import urlparse

from all_about_llms.config import Settings
from all_about_llms.contracts import (
    ProviderReadinessItem,
    ProviderReadinessResult,
    ProviderReadinessStatus,
    ProviderSecretFileStatus,
    ProviderSmokeTestStep,
)


OPENAI_REALTIME_DOCS = "https://platform.openai.com/docs/guides/realtime"
LIVEKIT_TURNS_DOCS = "https://docs.livekit.io/agents/logic/turns/"
PIPECAT_TRANSPORTS_DOCS = "https://docs.pipecat.ai/pipecat/learn/transports"
ELEVENLABS_SIGNED_URL_DOCS = (
    "https://elevenlabs.io/docs/conversational-ai/api-reference/"
    "conversations/get-signed-url"
)
CARTESIA_WEBSOCKET_DOCS = "https://docs.cartesia.ai/api-reference/tts/websocket"
GEMMA4_DOCS = "https://huggingface.co/docs/transformers/model_doc/gemma4"
TAVILY_SEARCH_DOCS = "https://docs.tavily.com/documentation/api-reference/endpoint/search"
SERPAPI_SEARCH_DOCS = "https://serpapi.com/search-api"


def build_provider_readiness(settings: Settings) -> ProviderReadinessResult:
    """Return a non-secret provider readiness report for the studio harness."""

    providers = [
        _gemma_provider(
            provider_id="gemma4-primary",
            display_name="Gemma 4 primary synthesis",
            model_id=settings.gemma4_primary_model_id,
            hf_token_configured=bool(settings.hf_token),
            hf_token_value=settings.hf_token,
            hf_token_file=settings.hf_token_file,
            endpoint_env="GEMMA4_PRIMARY_ENDPOINT_URL",
            endpoint_configured=bool(settings.gemma4_primary_endpoint_url),
            router_enabled=settings.hf_inference_router_enabled,
            router_url=settings.hf_inference_router_chat_completions_url,
            capabilities=[
                "deep_synthesis",
                "content_writing",
                "review",
                "long_context_planning",
            ],
        ),
        _gemma_provider(
            provider_id="gemma4-fast",
            display_name="Gemma 4 fast specialist",
            model_id=settings.gemma4_fast_model_id,
            hf_token_configured=bool(settings.hf_token),
            hf_token_value=settings.hf_token,
            hf_token_file=settings.hf_token_file,
            endpoint_env="GEMMA4_FAST_ENDPOINT_URL",
            endpoint_configured=bool(settings.gemma4_fast_endpoint_url),
            router_enabled=settings.hf_inference_router_enabled,
            router_url=settings.hf_inference_router_chat_completions_url,
            capabilities=[
                "fast_iteration",
                "specialist_review",
                "task_summarization",
            ],
        ),
        _gemma_provider(
            provider_id="gemma4-multimodal",
            display_name="Gemma 4 multimodal specialist",
            model_id=settings.gemma4_multimodal_model_id,
            hf_token_configured=bool(settings.hf_token),
            hf_token_value=settings.hf_token,
            hf_token_file=settings.hf_token_file,
            endpoint_env="GEMMA4_MULTIMODAL_ENDPOINT_URL",
            endpoint_configured=bool(settings.gemma4_multimodal_endpoint_url),
            router_enabled=settings.hf_inference_router_enabled,
            router_url=settings.hf_inference_router_chat_completions_url,
            allow_router_fallback=False,
            capabilities=[
                "vision_review",
                "multimodal_analysis",
                "audio_image_specialist_tasks",
            ],
        ),
        _provider(
            provider_id="openrouter-livekit",
            provider_type="realtime_audio",
            display_name="OpenRouter DeepSeek V4 Flash + Kokoro realtime dialogue",
            selected=settings.realtime_default_provider
            in {"openrouter_livekit", "openrouter-livekit"},
            required_env=[
                "OPENROUTER_API_KEY",
                "OPENROUTER_LIVEKIT_URL",
                "LIVEKIT_API_KEY",
                "LIVEKIT_API_SECRET",
            ],
            configured_env=_configured(
                {
                    "OPENROUTER_API_KEY": settings.openrouter_api_key,
                    "OPENROUTER_LIVEKIT_URL": (
                        settings.realtime_livekit_url()
                        or settings.gemma4_realtime_ws_url
                    ),
                    "LIVEKIT_API_KEY": settings.livekit_api_key,
                    "LIVEKIT_API_SECRET": settings.livekit_api_secret,
                }
            ),
            model_ids=[
                settings.gemma4_realtime_audio_input_model,
                settings.gemma4_realtime_reasoning_model,
                settings.gemma4_realtime_audio_output_model,
            ],
            endpoint_configured=bool(
                settings.realtime_livekit_url() or settings.gemma4_realtime_ws_url
            ),
            capabilities=[
                "openrouter_live_dialogue",
                "speech_to_speech_pipeline",
                "turn_taking",
                "interruptions",
                "context_pruning",
                "open_weight_tts",
                "livekit_join_token",
                "deepseek_streaming_reasoning",
            ],
            boundary=(
                "LiveKit handles public media transport; Rust handles VAD, "
                "buffers, and barge-in; Python calls OpenRouter DeepSeek V4 "
                "Flash for dialogue reasoning and Kokoro for TTS. Pipecat is "
                "optional for internal pipeline composition."
            ),
            notes=(
                "Default realtime dialogue path. Uses OpenRouter DeepSeek V4 "
                "Flash for live text-turn dialogue reasoning and Kokoro-82M "
                "for TTS. Needs OpenRouter plus LiveKit URL and API key/secret "
                "to mint ephemeral room tokens."
            ),
            documentation_url=LIVEKIT_TURNS_DOCS,
            secret_files=[
                _secret_file_status(
                    env_name="OPENROUTER_API_KEY",
                    file_env_name="OPENROUTER_API_KEY_FILE",
                    path=settings.openrouter_api_key_file,
                    secret_value=settings.openrouter_api_key,
                ),
                _secret_file_status(
                    env_name="LIVEKIT_API_KEY",
                    file_env_name="LIVEKIT_API_KEY_FILE",
                    path=settings.livekit_api_key_file,
                    secret_value=settings.livekit_api_key,
                ),
                _secret_file_status(
                    env_name="LIVEKIT_API_SECRET",
                    file_env_name="LIVEKIT_API_SECRET_FILE",
                    path=settings.livekit_api_secret_file,
                    secret_value=settings.livekit_api_secret,
                ),
            ],
        ),
        _provider(
            provider_id="open-source-realtime",
            provider_type="realtime_audio",
            display_name="Open-source realtime fallback",
            selected=settings.realtime_default_provider == "open_source_realtime",
            required_env=["OPEN_SOURCE_REALTIME_WS_URL"],
            configured_env=_configured(
                {"OPEN_SOURCE_REALTIME_WS_URL": settings.open_source_realtime_ws_url}
            ),
            model_ids=[
                settings.open_source_realtime_stt_model,
                settings.open_source_realtime_llm_model,
                settings.open_source_realtime_tts_model,
            ],
            endpoint_configured=bool(settings.open_source_realtime_ws_url),
            capabilities=[
                "speech_to_text",
                "text_to_speech",
                "local_realtime_adapter",
                "dev_fallback",
            ],
            boundary=(
                "Fallback open-source adapter for local experiments; production "
                "browser voice still routes through LiveKit."
            ),
            notes=(
                "Use only when explicitly selected. The OpenRouter/Kokoro LiveKit "
                "runtime is the product default."
            ),
            documentation_url=PIPECAT_TRANSPORTS_DOCS,
        ),
        _provider(
            provider_id="openai-realtime",
            provider_type="realtime_audio",
            display_name="OpenAI Realtime",
            selected=settings.realtime_default_provider == "openai_realtime",
            required_env=["OPENAI_API_KEY"],
            configured_env=_configured(
                {
                    "OPENAI_API_KEY": settings.openai_api_key,
                }
            ),
            model_ids=[settings.openai_realtime_model],
            endpoint_configured=True,
            capabilities=[
                "speech_to_speech",
                "turn_taking",
                "interruptions",
                "spoken_output",
            ],
            boundary="Realtime provider handles live audio transport; durable turns are stored in Postgres.",
            notes="Used for natural voice dialogue when OPENAI_API_KEY is configured.",
            documentation_url=OPENAI_REALTIME_DOCS,
        ),
        _provider(
            provider_id="elevenlabs",
            provider_type="realtime_audio",
            display_name="ElevenLabs Conversational AI",
            selected=settings.realtime_default_provider == "elevenlabs",
            required_env=["ELEVENLABS_API_KEY", "ELEVENLABS_AGENT_ID"],
            configured_env=_configured(
                {
                    "ELEVENLABS_API_KEY": settings.elevenlabs_api_key,
                    "ELEVENLABS_AGENT_ID": settings.elevenlabs_agent_id,
                }
            ),
            model_ids=[settings.elevenlabs_model_id],
            endpoint_configured=True,
            capabilities=[
                "signed_websocket_session",
                "voice_agent",
                "spoken_output",
            ],
            boundary="ElevenLabs returns a signed realtime URL; secrets are not stored in run events.",
            notes="Requires an ElevenLabs agent id for local cockpit session creation.",
            documentation_url=ELEVENLABS_SIGNED_URL_DOCS,
        ),
        _provider(
            provider_id="cartesia",
            provider_type="realtime_audio",
            display_name="Cartesia realtime TTS",
            selected=settings.realtime_default_provider == "cartesia",
            required_env=["CARTESIA_API_KEY", "CARTESIA_VOICE_ID"],
            configured_env=_configured(
                {
                    "CARTESIA_API_KEY": settings.cartesia_api_key,
                    "CARTESIA_VOICE_ID": settings.cartesia_voice_id,
                }
            ),
            model_ids=[settings.cartesia_model_id],
            endpoint_configured=True,
            capabilities=[
                "low_latency_tts",
                "spoken_output",
                "websocket_tts",
            ],
            boundary="Cartesia is a realtime TTS output layer; dialogue state remains in the studio.",
            notes="Useful for fast spoken output when paired with the durable conversation router.",
            documentation_url=CARTESIA_WEBSOCKET_DOCS,
        ),
        _provider(
            provider_id="tavily-search",
            provider_type="web_search",
            display_name="Tavily web search",
            selected=settings.web_search_provider == "tavily",
            required_env=["TAVILY_API_KEY"],
            configured_env=_configured({"TAVILY_API_KEY": settings.tavily_api_key}),
            secret_files=[
                _secret_file_status(
                    env_name="TAVILY_API_KEY",
                    file_env_name="TAVILY_API_KEY_FILE",
                    path=settings.tavily_api_key_file,
                    secret_value=settings.tavily_api_key,
                )
            ],
            model_ids=[],
            endpoint_configured=True,
            capabilities=[
                "freshness_check",
                "source_discovery",
                "grounding",
            ],
            boundary="Web search returns source candidates; claims still need source ledger review.",
            notes="Selected when WEB_SEARCH_PROVIDER=tavily.",
            documentation_url=TAVILY_SEARCH_DOCS,
        ),
        _provider(
            provider_id="serpapi-search",
            provider_type="web_search",
            display_name="SerpAPI search",
            selected=settings.web_search_provider == "serpapi",
            required_env=["SERPAPI_API_KEY"],
            configured_env=_configured({"SERPAPI_API_KEY": settings.serpapi_api_key}),
            model_ids=[],
            endpoint_configured=True,
            capabilities=[
                "freshness_check",
                "source_discovery",
                "grounding",
            ],
            boundary="Web search returns source candidates; claims still need source ledger review.",
            notes="Selected when WEB_SEARCH_PROVIDER=serpapi.",
            documentation_url=SERPAPI_SEARCH_DOCS,
        ),
        _provider(
            provider_id="deterministic-reranker",
            provider_type="reranker",
            display_name="Deterministic source-quality reranker",
            selected=settings.reranker_provider == "deterministic",
            required_env=[],
            configured_env=[],
            model_ids=[],
            endpoint_configured=True,
            capabilities=[
                "local_reranking",
                "source_quality_scoring",
                "freshness_scoring",
                "repeatable_tests",
            ],
            boundary=(
                "Reranker provider scores fused retrieval candidates before "
                "source-backed synthesis; this default does not call an external model."
            ),
            notes="Default local fallback until a cloud reranker is configured.",
            documentation_url=None,
        ),
        ProviderReadinessItem(
            provider_id="rust-retrieval-ranker",
            provider_type="reranker",
            display_name="Rust retrieval ranker",
            status=(
                ProviderReadinessStatus.READY
                if settings.rust_reranker_binary_path.exists()
                else ProviderReadinessStatus.MISSING_CONFIG
            ),
            selected=settings.reranker_provider == "rust",
            required_env=["RUST_RERANKER_BINARY_PATH"],
            configured_env=(
                ["RUST_RERANKER_BINARY_PATH"]
                if settings.rust_reranker_binary_path.exists()
                else []
            ),
            missing_env=(
                []
                if settings.rust_reranker_binary_path.exists()
                else ["RUST_RERANKER_BINARY_PATH"]
            ),
            model_ids=[],
            endpoint_configured=settings.rust_reranker_binary_path.exists(),
            capabilities=[
                "low_latency_local_reranking",
                "hybrid_signal_scoring",
                "graph_traversal",
                "stable_tie_breaking",
            ],
            boundary=(
                "Rust owns deterministic high-throughput reranking and bounded graph traversal; "
                "Python owns retrieval, persistence, and agent orchestration."
            ),
            notes=(
                "Set RERANKER_PROVIDER=rust after building services/retrieval-ranker "
                "or pointing RUST_RERANKER_BINARY_PATH at the compiled binary."
            ),
            documentation_url=None,
            next_actions=[
                "Run cargo build for services/retrieval-ranker before selecting this provider.",
                "Build a retrieval-quality ledger and verify provider_id=rust_retrieval_ranker_v1.",
            ],
        ),
        ProviderReadinessItem(
            provider_id="imagegen",
            provider_type="raster_visual_generation",
            display_name="Codex imagegen boundary",
            status=ProviderReadinessStatus.TOOL_BOUNDARY,
            selected=True,
            capabilities=[
                "raster_visual_generation",
                "image_editing",
                "social_visual_assets",
            ],
            boundary="Imagegen is a Codex tool boundary, not a FastAPI network provider.",
            notes="The app stores prompt packs and provenance; Codex invokes imagegen for actual raster assets.",
            next_actions=[
                "Create or review imagegen prompt-pack artifacts before invoking Codex imagegen.",
                "Store generated raster asset provenance back on the run artifact.",
            ],
        ),
    ]

    ready_provider_ids = [
        provider.provider_id
        for provider in providers
        if provider.status == ProviderReadinessStatus.READY
    ]
    missing_provider_ids = [
        provider.provider_id
        for provider in providers
        if provider.status == ProviderReadinessStatus.MISSING_CONFIG
    ]
    tool_boundary_provider_ids = [
        provider.provider_id
        for provider in providers
        if provider.status == ProviderReadinessStatus.TOOL_BOUNDARY
    ]
    missing_required_env = sorted(
        {
            env_name
            for provider in providers
            for env_name in provider.missing_env
        }
    )
    provider_by_id = {provider.provider_id: provider for provider in providers}
    selected_realtime_provider_id = {
        "openrouter_livekit": "openrouter-livekit",
        "openrouter-livekit": "openrouter-livekit",
        "gemma4_realtime": "gemma4-realtime",
        "open_source_realtime": "open-source-realtime",
        "openai_realtime": "openai-realtime",
        "elevenlabs": "elevenlabs",
        "cartesia": "cartesia",
    }.get(settings.realtime_default_provider, settings.realtime_default_provider)
    selected_web_search_provider_id = {
        "tavily": "tavily-search",
        "serpapi": "serpapi-search",
    }.get(settings.web_search_provider, settings.web_search_provider)
    selected_reranker_provider_id = {
        "deterministic": "deterministic-reranker",
        "rust": "rust-retrieval-ranker",
    }.get(settings.reranker_provider, settings.reranker_provider)
    smoke_test_plan = _build_smoke_test_plan(
        provider_by_id=provider_by_id,
        selected_realtime_provider_id=selected_realtime_provider_id,
        selected_web_search_provider_id=selected_web_search_provider_id,
        selected_reranker_provider_id=selected_reranker_provider_id,
    )
    required_live_provider_ids = [
        selected_realtime_provider_id,
        selected_web_search_provider_id,
        selected_reranker_provider_id,
    ]
    provider_backed_smoke_ready = all(
        provider_by_id.get(provider_id) is not None
        and provider_by_id[provider_id].status == ProviderReadinessStatus.READY
        for provider_id in required_live_provider_ids
    )
    smoke_status = "ready" if provider_backed_smoke_ready else "blocked"
    return ProviderReadinessResult(
        default_realtime_provider=settings.realtime_default_provider,
        selected_web_search_provider=settings.web_search_provider,
        providers=providers,
        ready_provider_ids=ready_provider_ids,
        missing_provider_ids=missing_provider_ids,
        tool_boundary_provider_ids=tool_boundary_provider_ids,
        missing_required_env=missing_required_env,
        provider_backed_smoke_ready=provider_backed_smoke_ready,
        smoke_test_plan=smoke_test_plan,
        demo_walkthrough=[
            "Start Postgres + pgvector before browser-backed cockpit smoke checks.",
            "Open /cockpit and click Load demo run to prove the cockpit works without external provider keys.",
            "Refresh Provider Readiness and resolve missing env values for the selected realtime provider and selected web-search provider.",
            "Run the provider-backed smoke steps and verify durable run evidence: source records, provider events, model-routing ledger, realtime dialogue ledger, and source ledger.",
        ],
        summary=(
            f"{len(ready_provider_ids)} provider(s) ready, "
            f"{len(missing_provider_ids)} missing configuration, "
            f"{len(tool_boundary_provider_ids)} tool boundary provider(s). "
            f"Provider-backed smoke is {smoke_status}."
        ),
    )


def _gemma_provider(
    *,
    provider_id: str,
    display_name: str,
    model_id: str,
    hf_token_configured: bool,
    hf_token_value: str | None,
    hf_token_file: object | None,
    endpoint_env: str,
    endpoint_configured: bool,
    router_enabled: bool,
    router_url: str | None,
    capabilities: list[str],
    allow_router_fallback: bool = True,
) -> ProviderReadinessItem:
    router_configured = bool(
        allow_router_fallback and router_enabled and _is_http_url(router_url)
    )
    configured_env = _configured(
        {
            "HF_TOKEN": "configured" if hf_token_configured else None,
            endpoint_env: "configured" if endpoint_configured else None,
            "HF_INFERENCE_ROUTER_CHAT_COMPLETIONS_URL": (
                "configured" if not endpoint_configured and router_configured else None
            ),
        }
    )
    required_env = ["HF_TOKEN"]
    if endpoint_configured:
        required_env.append(endpoint_env)
    elif router_enabled and allow_router_fallback:
        required_env.append("HF_INFERENCE_ROUTER_CHAT_COMPLETIONS_URL")
    else:
        required_env.append(endpoint_env)
    return _provider(
        provider_id=provider_id,
        provider_type="gemma4_hf_endpoint",
        display_name=display_name,
        selected=False,
        required_env=required_env,
        configured_env=configured_env,
        model_ids=[model_id],
        endpoint_configured=endpoint_configured or router_configured,
        capabilities=capabilities,
        boundary=(
            "Legacy/non-default Gemma 4 expert lane retained for historical "
            "experiments only; the current default uses OpenRouter/LiveKit for "
            "live dialogue."
        ),
        notes=(
            "Do not use this for the current OpenRouter LiveKit proof path. "
            "HF/Gemma setup is legacy or future native-audio background unless "
            "a new design note deliberately re-promotes it."
        ),
        documentation_url=GEMMA4_DOCS,
        secret_files=[
            _secret_file_status(
                env_name="HF_TOKEN",
                file_env_name="HF_TOKEN_FILE",
                path=hf_token_file,
                secret_value=hf_token_value,
            )
        ],
    )


def _provider(
    *,
    provider_id: str,
    provider_type: str,
    display_name: str,
    selected: bool,
    required_env: list[str],
    configured_env: list[str],
    model_ids: list[str],
    endpoint_configured: bool | None,
    capabilities: list[str],
    boundary: str,
    notes: str,
    documentation_url: str | None = None,
    secret_files: list[ProviderSecretFileStatus] | None = None,
) -> ProviderReadinessItem:
    missing_env = [
        env_name for env_name in required_env if env_name not in configured_env
    ]
    status = (
        ProviderReadinessStatus.READY
        if not missing_env
        else ProviderReadinessStatus.MISSING_CONFIG
    )
    return ProviderReadinessItem(
        provider_id=provider_id,
        provider_type=provider_type,
        display_name=display_name,
        status=status,
        selected=selected,
        required_env=required_env,
        configured_env=configured_env,
        missing_env=missing_env,
        model_ids=model_ids,
        endpoint_configured=endpoint_configured,
        capabilities=capabilities,
        boundary=boundary,
        notes=notes,
        documentation_url=documentation_url,
        next_actions=_provider_next_actions(
            status=status,
            missing_env=missing_env,
            provider_type=provider_type,
            secret_files=secret_files or [],
        ),
        secret_files=secret_files or [],
    )


def _configured(values: dict[str, object | None]) -> list[str]:
    return [env_name for env_name, value in values.items() if value]


def _is_http_url(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _secret_file_status(
    *,
    env_name: str,
    file_env_name: str,
    path: object | None,
    secret_value: str | None = None,
) -> ProviderSecretFileStatus:
    if path is None:
        if secret_value:
            return ProviderSecretFileStatus(
                env_name=env_name,
                file_env_name=file_env_name,
                status="direct_env",
                configured=True,
                path=None,
                detail=f"{env_name} is configured directly.",
            )
        return ProviderSecretFileStatus(
            env_name=env_name,
            file_env_name=file_env_name,
            status="not_configured",
            configured=False,
            path=None,
            detail=f"{file_env_name} is not configured.",
        )
    try:
        text = path.read_text(encoding="utf-8")  # type: ignore[attr-defined]
    except FileNotFoundError:
        if secret_value:
            return ProviderSecretFileStatus(
                env_name=env_name,
                file_env_name=file_env_name,
                status="direct_env",
                configured=True,
                path=None,
                detail=(
                    f"{env_name} is configured directly; {file_env_name} "
                    "points to a missing file."
                ),
            )
        return ProviderSecretFileStatus(
            env_name=env_name,
            file_env_name=file_env_name,
            status="missing",
            configured=False,
            path=None,
            detail=f"{file_env_name} points to a missing file.",
        )
    except OSError:
        if secret_value:
            return ProviderSecretFileStatus(
                env_name=env_name,
                file_env_name=file_env_name,
                status="direct_env",
                configured=True,
                path=None,
                detail=(
                    f"{env_name} is configured directly; {file_env_name} "
                    "points to a file that could not be read."
                ),
            )
        return ProviderSecretFileStatus(
            env_name=env_name,
            file_env_name=file_env_name,
            status="unreadable",
            configured=False,
            path=None,
            detail=f"{file_env_name} points to a file that could not be read.",
        )
    stripped = text.strip()
    if not stripped:
        if secret_value:
            return ProviderSecretFileStatus(
                env_name=env_name,
                file_env_name=file_env_name,
                status="direct_env",
                configured=True,
                path=None,
                detail=(
                    f"{env_name} is configured directly; {file_env_name} "
                    "points to an empty file."
                ),
            )
        return ProviderSecretFileStatus(
            env_name=env_name,
            file_env_name=file_env_name,
            status="empty",
            configured=False,
            path=None,
            detail=f"{file_env_name} points to an empty file.",
        )
    if secret_value and stripped != secret_value:
        return ProviderSecretFileStatus(
            env_name=env_name,
            file_env_name=file_env_name,
            status="direct_env",
            configured=True,
            path=None,
            detail=(
                f"{env_name} is configured directly and overrides "
                f"{file_env_name}."
            ),
        )
    return ProviderSecretFileStatus(
        env_name=env_name,
        file_env_name=file_env_name,
        status="loaded",
        configured=True,
        path=None,
        detail=f"{file_env_name} is configured with a readable non-empty file.",
    )


def _provider_next_actions(
    *,
    status: ProviderReadinessStatus,
    missing_env: list[str],
    provider_type: str,
    secret_files: list[ProviderSecretFileStatus] | None = None,
) -> list[str]:
    if status == ProviderReadinessStatus.MISSING_CONFIG:
        secret_files_by_env = {
            secret_file.env_name: secret_file
            for secret_file in secret_files or []
        }
        return [
            _missing_env_next_action(env_name, secret_files_by_env.get(env_name))
            for env_name in missing_env
        ]
    if provider_type == "gemma4_hf_endpoint":
        return [
            "No action for the current OpenRouter LiveKit proof path.",
            "Keep this legacy lane disabled unless a future design note re-promotes native Gemma audio.",
        ]
    if provider_type == "realtime_audio":
        return [
            "Create a realtime session from the product voice panel.",
            "Route one voice/text turn and verify the realtime dialogue ledger.",
        ]
    if provider_type == "web_search":
        return [
            "Run a source-backed content request and verify web_search_result sources.",
            "Build retrieval quality and source ledger artifacts after search.",
        ]
    if provider_type == "reranker":
        return [
            "Build a retrieval-quality ledger and verify rerank scores are present.",
        ]
    return ["Run the provider-specific smoke step and verify durable events."]


def _missing_env_next_action(
    env_name: str,
    secret_file: ProviderSecretFileStatus | None,
) -> str:
    if secret_file is None:
        return f"Set {env_name} in .env or the process environment."
    display_path = (secret_file.path or "").strip()
    if secret_file.status == "missing" and display_path:
        return (
            f"Create {display_path} with the {secret_file.env_name} value, or "
            f"set {secret_file.env_name} directly for this process."
        )
    if secret_file.status == "empty" and display_path:
        return (
            f"Put the {secret_file.env_name} value in {display_path}, or set "
            f"{secret_file.env_name} directly for this process."
        )
    if secret_file.status == "unreadable" and display_path:
        return (
            f"Fix read permissions for {display_path}, or set "
            f"{secret_file.env_name} directly for this process."
        )
    return (
        f"Set {secret_file.env_name} directly, or configure "
        f"{secret_file.file_env_name} to point to a readable secret file."
    )


def _build_smoke_test_plan(
    *,
    provider_by_id: dict[str, ProviderReadinessItem],
    selected_realtime_provider_id: str,
    selected_web_search_provider_id: str,
    selected_reranker_provider_id: str,
) -> list[ProviderSmokeTestStep]:
    steps = [
        ProviderSmokeTestStep(
            step_id="local-postgres-pgvector",
            provider_id="postgres-pgvector",
            provider_type="durable_store",
            title="Start local Postgres + pgvector",
            status="manual_check",
            required=True,
            live_call=False,
            cockpit_action=None,
            api_path="docker compose up -d postgres",
            expected_evidence=[
                "pg_isready reports the agentstudio database is accepting connections.",
                "Runtime health ledger records live Postgres connectivity when using PostgresStore.",
            ],
            blockers=[
                "Docker Desktop or another Postgres + pgvector service must be running locally.",
            ],
            next_actions=[
                "Start Docker Desktop or another compatible Postgres + pgvector instance.",
                "Run the FastAPI app only after DATABASE_URL points to the live database.",
            ],
        ),
        ProviderSmokeTestStep(
            step_id="provider-free-cockpit-demo",
            provider_id="local-demo",
            provider_type="cockpit_demo",
            title="Load the provider-free cockpit demo run",
            status="ready",
            required=True,
            live_call=False,
            cockpit_action="Click Load demo run in the cockpit.",
            api_path="POST /api/demo/cockpit-run",
            expected_evidence=[
                "Run status becomes waiting_for_human.",
                "Sources, claims, draft artifacts, retrieval quality, source ledger, feedback gate, and project memory render in the cockpit.",
            ],
            next_actions=[
                "Use this before live provider keys exist to verify cockpit wiring.",
            ],
        ),
        _selected_provider_smoke_step(
            step_id="selected-realtime-smoke",
            provider=provider_by_id.get(selected_realtime_provider_id),
            selected_provider_id=selected_realtime_provider_id,
            provider_type="realtime_audio",
            title="Create selected realtime audio session",
            api_path="POST /api/runs/{run_id}/realtime-session",
            cockpit_action="Create realtime session, then route one voice turn.",
            expected_evidence=[
                "Realtime session is recorded with provider, voice, status, and sanitized provider payload.",
                "Routed turn returns a spoken_response plan.",
                "Realtime dialogue ledger includes the session and routed turn.",
            ],
            live_call=True,
        ),
        ProviderSmokeTestStep(
            step_id="provider-free-realtime-rehearsal",
            provider_id="local_realtime_rehearsal",
            provider_type="realtime_rehearsal",
            title="Rehearse realtime dialogue without provider credentials",
            status="ready",
            required=False,
            live_call=False,
            cockpit_action=(
                "Enable provider-free rehearsal, create a realtime session, "
                "then route one voice turn."
            ),
            api_path="POST /api/runs/{run_id}/realtime-session",
            expected_evidence=[
                "Realtime session provider is local_realtime_rehearsal.",
                "Session metadata has dry_run=true and not_provider_backed=true.",
                "Realtime dialogue ledger includes the rehearsal session and turn.",
                "Cockpit walkthrough still blocks provider-backed smoke until a real selected-provider session exists.",
            ],
            next_actions=[
                "Use rehearsal for local dialogue UX testing before secrets are configured.",
                "Do not treat rehearsal evidence as provider-backed readiness.",
            ],
        ),
        _selected_provider_smoke_step(
            step_id="selected-web-search-smoke",
            provider=provider_by_id.get(selected_web_search_provider_id),
            selected_provider_id=selected_web_search_provider_id,
            provider_type="web_search",
            title="Run selected web-search grounding smoke",
            api_path="POST /api/orchestrations/content-studio",
            cockpit_action="Generate content pack on a current topic.",
            expected_evidence=[
                "Source records include source_type=web_search_result.",
                "Retrieval quality ledger accepts at least one source-linked candidate.",
                "Source ledger maps accepted sources to claims and artifacts.",
            ],
            live_call=True,
        ),
        _selected_provider_smoke_step(
            step_id="local-reranker-smoke",
            provider=provider_by_id.get(selected_reranker_provider_id),
            selected_provider_id=selected_reranker_provider_id,
            provider_type="reranker",
            title="Build retrieval-quality reranker smoke",
            api_path="POST /api/runs/{run_id}/retrieval-quality-ledger",
            cockpit_action="Run retrieval quality after sources exist.",
            expected_evidence=[
                "Ledger status is ready or gives explicit recall/rerank repair actions.",
                "Accepted candidates include rank, score, and rerank reason.",
            ],
            live_call=False,
        ),
        ProviderSmokeTestStep(
            step_id="imagegen-boundary-smoke",
            provider_id="imagegen",
            provider_type="raster_visual_generation",
            title="Verify imagegen remains a tool boundary",
            status="tool_boundary",
            required=False,
            live_call=False,
            cockpit_action="Review image prompt-pack artifacts before Codex imagegen use.",
            api_path=None,
            expected_evidence=[
                "Run stores image prompt packs and provenance before raster generation.",
                "Actual raster generation is invoked through the Codex imagegen tool, not as a FastAPI provider.",
            ],
            next_actions=[
                "Use imagegen only when a run needs real raster social assets.",
            ],
        ),
    ]
    return steps


def _provider_smoke_step(
    *,
    step_id: str,
    provider: ProviderReadinessItem,
    title: str,
    api_path: str,
    cockpit_action: str,
    expected_evidence: list[str],
    live_call: bool,
) -> ProviderSmokeTestStep:
    blockers = [
        f"Missing required environment variable: {env_name}"
        for env_name in provider.missing_env
    ]
    return ProviderSmokeTestStep(
        step_id=step_id,
        provider_id=provider.provider_id,
        provider_type=provider.provider_type,
        title=title,
        status=(
            "ready"
            if provider.status == ProviderReadinessStatus.READY
            else "blocked"
        ),
        required=True,
        live_call=live_call,
        cockpit_action=cockpit_action,
        api_path=api_path,
        documentation_url=provider.documentation_url,
        required_env=provider.required_env,
        missing_env=provider.missing_env,
        expected_evidence=expected_evidence,
        blockers=blockers,
        next_actions=provider.next_actions,
    )


def _selected_provider_smoke_step(
    *,
    step_id: str,
    provider: ProviderReadinessItem | None,
    selected_provider_id: str,
    provider_type: str,
    title: str,
    api_path: str,
    cockpit_action: str,
    expected_evidence: list[str],
    live_call: bool,
) -> ProviderSmokeTestStep:
    if provider is not None:
        return _provider_smoke_step(
            step_id=step_id,
            provider=provider,
            title=title,
            api_path=api_path,
            cockpit_action=cockpit_action,
            expected_evidence=expected_evidence,
            live_call=live_call,
        )
    return ProviderSmokeTestStep(
        step_id=step_id,
        provider_id=selected_provider_id,
        provider_type=provider_type,
        title=title,
        status="blocked",
        required=True,
        live_call=live_call,
        cockpit_action=cockpit_action,
        api_path=api_path,
        expected_evidence=expected_evidence,
        blockers=[
            f"Selected provider {selected_provider_id} is not recognized by the provider factory."
        ],
        next_actions=[
            "Set the selected provider to one of the provider ids listed in /api/provider-readiness."
        ],
    )
