import json
import math
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from all_about_llms.local_provider_config import (
    LOCAL_PROVIDER_CONFIG_ENV_TO_FIELD,
    LocalProviderConfigValidationError,
    validate_local_provider_config_value,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAX_RUST_VOICE_EDGE_BENCHMARK_SPEECH_FRAMES = 4096


class Settings(BaseSettings):
    """Runtime settings for the local-first agent studio."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "all-about-llms-agent-studio"
    environment: str = "local"
    database_url: str = (
        "postgresql://agentstudio:agentstudio@localhost:5432/agentstudio"
    )
    postgres_pool_min_size: int = 1
    postgres_pool_max_size: int = 8

    hf_token: str | None = None
    hf_token_file: Path | None = Field(default=PROJECT_ROOT / ".secrets/hf_token")
    hf_inference_router_enabled: bool = True
    hf_inference_router_chat_completions_url: str | None = (
        "https://router.huggingface.co/v1/chat/completions"
    )
    gemma4_primary_model_id: str = "google/gemma-4-31b-it"
    gemma4_primary_endpoint_url: str | None = None
    gemma4_fast_model_id: str = "google/gemma-4-26b-a4b-it"
    gemma4_fast_endpoint_url: str | None = None
    gemma4_multimodal_model_id: str = "google/gemma-4-e4b-it"
    gemma4_multimodal_endpoint_url: str | None = None
    local_provider_config_file: Path | None = Field(
        default=PROJECT_ROOT / ".secrets/local_provider_config.json"
    )

    realtime_default_provider: str = "openrouter_livekit"
    openrouter_livekit_url: str | None = None
    gemma4_realtime_transport_framework: str = "livekit"
    gemma4_realtime_livekit_url: str | None = None
    livekit_api_key: str | None = None
    livekit_api_key_file: Path | None = Field(
        default=PROJECT_ROOT / ".secrets/livekit_api_key"
    )
    livekit_api_secret: str | None = None
    livekit_api_secret_file: Path | None = Field(
        default=PROJECT_ROOT / ".secrets/livekit_api_secret"
    )
    livekit_connectivity_preflight_timeout_seconds: float = 3.0
    gemma4_realtime_livekit_token_ttl_seconds: int = 3600
    gemma4_realtime_ws_url: str | None = None
    gemma4_realtime_audio_input_model: str = "deepseek/deepseek-v4-flash"
    gemma4_realtime_reasoning_model: str = "deepseek/deepseek-v4-flash"
    gemma4_realtime_audio_output_model: str = "hexgrad/Kokoro-82M"
    gemma4_realtime_audio_format: str = "pcm_s16le"
    gemma4_realtime_sample_rate: int = 16000
    gemma4_realtime_context_window_turns: int = 4
    gemma4_realtime_context_prune_after_turns: int = 3
    gemma4_realtime_max_audio_seconds_per_turn: int = 30
    gemma4_realtime_tts_flush_chars: int = 180
    gemma4_realtime_stream_gemma: bool = True
    gemma4_realtime_gemma_stream_timeout_seconds: float = 120.0
    gemma4_realtime_default_voice: str = "af_heart"
    gemma4_realtime_rust_vad_model: str = "silero-vad-rust"
    rust_voice_edge_http_url: str | None = None
    rust_voice_edge_binary_path: Path = Field(
        default=PROJECT_ROOT / "services/voice-edge/target/debug/voice-edge"
    )
    rust_voice_edge_timeout_seconds: float = 1.0
    rust_voice_edge_vad_backend: str = "deterministic_energy"
    rust_voice_edge_vad_threshold: float = 0.018
    rust_voice_edge_vad_probability_threshold: float = 0.5
    rust_voice_edge_vad_session_pool_size: int = 4
    rust_voice_edge_vad_stream_state_cache_size: int = 512
    rust_voice_edge_vad_model_path: Path | None = None
    rust_voice_edge_benchmark_speech_wav_path: Path | None = None
    rust_voice_edge_benchmark_max_speech_frames: int = 64
    rust_voice_edge_allow_vad_fallback: bool = True
    rust_voice_edge_min_speech_frames: int = 2
    rust_voice_edge_min_silence_frames: int = 16
    rust_voice_edge_turn_pre_roll_frames: int = 3
    rust_voice_edge_frame_ms: int = 32
    rust_voice_edge_max_inbound_buffer_bytes: int = 16_000 * 2 * 30
    rust_voice_edge_max_outbound_buffer_bytes: int = 16_000 * 2 * 2
    livekit_agent_name: str = "openrouter-kokoro-agent"
    livekit_agent_log_level: str = "INFO"
    voice_agent_supervisor_enabled: bool = True
    voice_agent_supervisor_log_lines: int = 80
    voice_agent_backend_event_sink_enabled: bool = True
    voice_agent_backend_event_sink_url: str | None = "http://127.0.0.1:8000"
    voice_agent_backend_event_sink_timeout_seconds: float = 2.0
    local_livekit_supervisor_enabled: bool = True
    local_livekit_supervisor_log_lines: int = 80
    worker_scheduler_supervisor_enabled: bool = True
    worker_scheduler_supervisor_log_lines: int = 80
    kokoro_tts_endpoint_url: str | None = None
    kokoro_tts_chunk_bytes: int = 6400
    kokoro_tts_timeout_seconds: float = 60.0
    open_source_realtime_ws_url: str | None = None
    open_source_realtime_stt_model: str = "nvidia/parakeet-tdt-0.6b-v2"
    open_source_realtime_llm_model: str = "google/gemma-4-31b-it"
    open_source_realtime_tts_model: str = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
    open_source_realtime_audio_format: str = "pcm_s16le"
    open_source_realtime_sample_rate: int = 16000
    openrouter_api_key: str | None = None
    openrouter_api_key_file: Path | None = Field(
        default=PROJECT_ROOT / ".secrets/openrouter_api_key"
    )
    openrouter_chat_completions_url: str = (
        "https://openrouter.ai/api/v1/chat/completions"
    )
    openai_api_key: str | None = None
    openai_realtime_model: str = "gpt-4o-realtime-preview"
    elevenlabs_api_key: str | None = None
    elevenlabs_agent_id: str | None = None
    elevenlabs_voice_id: str | None = None
    elevenlabs_model_id: str = "eleven_v3"
    cartesia_api_key: str | None = None
    cartesia_voice_id: str | None = None
    cartesia_model_id: str = "sonic-3.5"

    web_search_provider: str = "tavily"
    tavily_api_key: str | None = None
    tavily_api_key_file: Path | None = Field(
        default=PROJECT_ROOT / ".secrets/tavily_api_key"
    )
    serpapi_api_key: str | None = None
    instagram_access_token: str | None = None
    instagram_access_token_file: Path | None = Field(
        default=PROJECT_ROOT / ".secrets/instagram_access_token"
    )
    linkedin_access_token: str | None = None
    linkedin_access_token_file: Path | None = Field(
        default=PROJECT_ROOT / ".secrets/linkedin_access_token"
    )
    x_access_token: str | None = None
    x_access_token_file: Path | None = Field(
        default=PROJECT_ROOT / ".secrets/x_access_token"
    )
    x_api_key: str | None = None
    x_api_key_file: Path | None = Field(default=PROJECT_ROOT / ".secrets/x_api_key")
    substack_api_token: str | None = None
    substack_api_token_file: Path | None = Field(
        default=PROJECT_ROOT / ".secrets/substack_api_token"
    )
    reranker_provider: str = "deterministic"
    rust_reranker_binary_path: Path = Field(
        default=PROJECT_ROOT
        / "services/retrieval-ranker/target/debug/retrieval-ranker"
    )
    rust_reranker_timeout_seconds: float = 2.0

    artifacts_root: Path = Field(default=Path("artifacts"))
    voice_agent_persist_audio_artifacts: bool = True
    voice_agent_audio_artifact_max_bytes: int = 16_000 * 2 * 30
    voice_agent_audio_artifact_retention_days: int = 7
    voice_agent_audio_artifact_cleanup_interval_seconds: int = 3600
    obsidian_vault_path: Path = Field(default=Path("social_media_optimiser"))
    cockpit_artifact_path: Path = Field(default=Path("frontend/cockpit/index.html"))
    planning_artifact_path: Path = Field(
        default=Path("planning/foundation-system-design.html")
    )

    @field_validator(
        "rust_voice_edge_binary_path",
        "rust_reranker_binary_path",
        mode="before",
    )
    @classmethod
    def resolve_project_relative_binary_path(cls, value: str | Path) -> Path:
        path = Path(value).expanduser()
        if path.is_absolute():
            return path
        return PROJECT_ROOT / path

    @field_validator(
        "hf_token_file",
        "tavily_api_key_file",
        "instagram_access_token_file",
        "linkedin_access_token_file",
        "x_access_token_file",
        "x_api_key_file",
        "substack_api_token_file",
        "livekit_api_key_file",
        "livekit_api_secret_file",
        "openrouter_api_key_file",
        "local_provider_config_file",
        "rust_voice_edge_vad_model_path",
        "rust_voice_edge_benchmark_speech_wav_path",
        mode="before",
    )
    @classmethod
    def resolve_optional_project_relative_path(
        cls, value: str | Path | None
    ) -> Path | None:
        if value is None or value == "":
            return None
        path = Path(value).expanduser()
        if path.is_absolute():
            return path
        return PROJECT_ROOT / path

    @field_validator(
        "hf_token",
        "tavily_api_key",
        "livekit_api_key",
        "livekit_api_secret",
        "openrouter_api_key",
        "instagram_access_token",
        "linkedin_access_token",
        "x_access_token",
        "x_api_key",
        "substack_api_token",
        mode="before",
    )
    @classmethod
    def normalize_optional_secret(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = str(value).strip()
        return stripped or None

    @field_validator(
        "hf_inference_router_chat_completions_url",
        "gemma4_primary_endpoint_url",
        "gemma4_fast_endpoint_url",
        "gemma4_multimodal_endpoint_url",
        "openrouter_livekit_url",
        "gemma4_realtime_livekit_url",
        "gemma4_realtime_ws_url",
        "kokoro_tts_endpoint_url",
        "open_source_realtime_ws_url",
        mode="before",
    )
    @classmethod
    def normalize_optional_url_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = str(value).strip()
        return stripped or None

    @model_validator(mode="after")
    def load_secret_files(self) -> "Settings":
        self._load_secret_file_if_missing("hf_token", self.hf_token_file)
        self._load_secret_file_if_missing("tavily_api_key", self.tavily_api_key_file)
        self._load_secret_file_if_missing(
            "livekit_api_key", self.livekit_api_key_file
        )
        self._load_secret_file_if_missing(
            "livekit_api_secret", self.livekit_api_secret_file
        )
        self._load_secret_file_if_missing(
            "openrouter_api_key", self.openrouter_api_key_file
        )
        self._load_secret_file_if_missing(
            "instagram_access_token", self.instagram_access_token_file
        )
        self._load_secret_file_if_missing(
            "linkedin_access_token", self.linkedin_access_token_file
        )
        self._load_secret_file_if_missing("x_access_token", self.x_access_token_file)
        self._load_secret_file_if_missing("x_api_key", self.x_api_key_file)
        self._load_secret_file_if_missing(
            "substack_api_token", self.substack_api_token_file
        )
        self._load_local_provider_config_file()
        return self

    def publication_credential_env_values(self) -> dict[str, str | None]:
        return {
            "INSTAGRAM_ACCESS_TOKEN": self.instagram_access_token,
            "INSTAGRAM_ACCESS_TOKEN_FILE": _path_value(
                self.instagram_access_token_file
            ),
            "LINKEDIN_ACCESS_TOKEN": self.linkedin_access_token,
            "LINKEDIN_ACCESS_TOKEN_FILE": _path_value(self.linkedin_access_token_file),
            "X_ACCESS_TOKEN": self.x_access_token,
            "X_ACCESS_TOKEN_FILE": _path_value(self.x_access_token_file),
            "X_API_KEY": self.x_api_key,
            "X_API_KEY_FILE": _path_value(self.x_api_key_file),
            "SUBSTACK_API_TOKEN": self.substack_api_token,
            "SUBSTACK_API_TOKEN_FILE": _path_value(self.substack_api_token_file),
        }

    def _load_secret_file_if_missing(
        self,
        field_name: str,
        secret_file: Path | None,
    ) -> None:
        if getattr(self, field_name) or secret_file is None:
            return
        try:
            value = secret_file.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            return
        if value:
            object.__setattr__(self, field_name, value)

    def _load_local_provider_config_file(self) -> None:
        if self.local_provider_config_file is None:
            return
        try:
            raw_config = json.loads(
                self.local_provider_config_file.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(raw_config, dict):
            return
        for env_name, field_name in LOCAL_PROVIDER_CONFIG_ENV_TO_FIELD.items():
            if getattr(self, field_name):
                continue
            raw_value = raw_config.get(env_name)
            if not isinstance(raw_value, str):
                continue
            try:
                value = validate_local_provider_config_value(env_name, raw_value)
            except LocalProviderConfigValidationError:
                continue
            object.__setattr__(self, field_name, value)

    @field_validator("rust_voice_edge_vad_backend", mode="before")
    @classmethod
    def validate_rust_voice_edge_vad_backend(cls, value: str) -> str:
        backend = str(value).strip().lower()
        allowed = {"deterministic_energy", "silero_onnx"}
        if backend not in allowed:
            raise ValueError(
                "rust_voice_edge_vad_backend must be deterministic_energy or silero_onnx"
            )
        return backend

    @field_validator("rust_voice_edge_benchmark_max_speech_frames", mode="before")
    @classmethod
    def validate_positive_benchmark_frame_limit(cls, value: int | str) -> int:
        parsed = int(value)
        if parsed <= 0:
            raise ValueError("rust_voice_edge_benchmark_max_speech_frames must be positive")
        if parsed > MAX_RUST_VOICE_EDGE_BENCHMARK_SPEECH_FRAMES:
            raise ValueError(
                "rust_voice_edge_benchmark_max_speech_frames must be "
                f"<= {MAX_RUST_VOICE_EDGE_BENCHMARK_SPEECH_FRAMES}"
            )
        return parsed

    @field_validator("livekit_connectivity_preflight_timeout_seconds", mode="before")
    @classmethod
    def validate_livekit_connectivity_preflight_timeout(
        cls, value: float | int | str
    ) -> float:
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError(
                "livekit_connectivity_preflight_timeout_seconds must be finite"
            )
        if parsed <= 0:
            raise ValueError(
                "livekit_connectivity_preflight_timeout_seconds must be positive"
            )
        if parsed > 30:
            raise ValueError(
                "livekit_connectivity_preflight_timeout_seconds must be <= 30"
            )
        return parsed

    @field_validator("voice_agent_backend_event_sink_timeout_seconds", mode="before")
    @classmethod
    def validate_voice_agent_backend_event_sink_timeout(
        cls, value: float | int | str
    ) -> float:
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError(
                "voice_agent_backend_event_sink_timeout_seconds must be finite"
            )
        if parsed <= 0:
            raise ValueError(
                "voice_agent_backend_event_sink_timeout_seconds must be positive"
            )
        if parsed > 30:
            raise ValueError(
                "voice_agent_backend_event_sink_timeout_seconds must be <= 30"
            )
        return parsed

    @field_validator("voice_agent_audio_artifact_max_bytes", mode="before")
    @classmethod
    def validate_voice_agent_audio_artifact_max_bytes(cls, value: int | str) -> int:
        parsed = int(value)
        if parsed <= 0:
            raise ValueError("voice_agent_audio_artifact_max_bytes must be positive")
        return parsed

    @field_validator(
        "voice_agent_audio_artifact_retention_days",
        "voice_agent_audio_artifact_cleanup_interval_seconds",
        "voice_agent_supervisor_log_lines",
        "local_livekit_supervisor_log_lines",
        "worker_scheduler_supervisor_log_lines",
        mode="before",
    )
    @classmethod
    def validate_positive_integer_runtime_limits(
        cls, value: int | str
    ) -> int:
        parsed = int(value)
        if parsed <= 0:
            raise ValueError("runtime limit values must be positive")
        return parsed

    def configured_realtime_providers(self) -> list[str]:
        providers: list[str] = []
        if self.realtime_livekit_url() or self.gemma4_realtime_ws_url:
            providers.append("openrouter_livekit")
        if self.open_source_realtime_ws_url:
            providers.append("open_source_realtime")
        if self.openai_api_key:
            providers.append("openai_realtime")
        if self.elevenlabs_api_key:
            providers.append("elevenlabs")
        if self.cartesia_api_key:
            providers.append("cartesia")
        return providers

    def realtime_livekit_url(self) -> str | None:
        return self.openrouter_livekit_url or self.gemma4_realtime_livekit_url

    def gemma_chat_endpoint_url(self, dedicated_endpoint_url: str | None) -> str | None:
        if dedicated_endpoint_url:
            return dedicated_endpoint_url
        if (
            self.hf_inference_router_enabled
            and _is_http_url(self.hf_inference_router_chat_completions_url)
        ):
            return self.hf_inference_router_chat_completions_url
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()


def _is_http_url(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _path_value(path: Path | None) -> str | None:
    return str(path) if path is not None else None
