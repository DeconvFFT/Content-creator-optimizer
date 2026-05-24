from enum import StrEnum
from pathlib import Path
from urllib.parse import urlparse


class LocalProviderConfigValidationError(ValueError):
    pass


class LocalProviderConfigEnvName(StrEnum):
    GEMMA4_MULTIMODAL_ENDPOINT_URL = "GEMMA4_MULTIMODAL_ENDPOINT_URL"
    OPENROUTER_LIVEKIT_URL = "OPENROUTER_LIVEKIT_URL"
    GEMMA4_REALTIME_LIVEKIT_URL = "GEMMA4_REALTIME_LIVEKIT_URL"
    KOKORO_TTS_ENDPOINT_URL = "KOKORO_TTS_ENDPOINT_URL"


LOCAL_PROVIDER_CONFIG_ENV_TO_FIELD: dict[str, str] = {
    LocalProviderConfigEnvName.GEMMA4_MULTIMODAL_ENDPOINT_URL: "gemma4_multimodal_endpoint_url",
    LocalProviderConfigEnvName.OPENROUTER_LIVEKIT_URL: "openrouter_livekit_url",
    LocalProviderConfigEnvName.GEMMA4_REALTIME_LIVEKIT_URL: "gemma4_realtime_livekit_url",
    LocalProviderConfigEnvName.KOKORO_TTS_ENDPOINT_URL: "kokoro_tts_endpoint_url",
}


def local_provider_config_field_name(
    env_name: LocalProviderConfigEnvName,
) -> str:
    return LOCAL_PROVIDER_CONFIG_ENV_TO_FIELD[str(env_name)]


def validate_local_provider_config_value(
    env_name: LocalProviderConfigEnvName | str,
    config_value: str,
) -> str:
    try:
        parsed_env = LocalProviderConfigEnvName(str(env_name))
    except ValueError as exc:
        raise LocalProviderConfigValidationError(
            "Unsupported local provider config."
        ) from exc
    value = config_value.strip()
    if not value:
        raise LocalProviderConfigValidationError(
            "Provider configuration value cannot be blank."
        )
    parsed = urlparse(value)
    livekit_env_names = {
        LocalProviderConfigEnvName.OPENROUTER_LIVEKIT_URL,
        LocalProviderConfigEnvName.GEMMA4_REALTIME_LIVEKIT_URL,
    }
    allowed_schemes = (
        {"ws", "wss", "http", "https"}
        if parsed_env in livekit_env_names
        else {"http", "https"}
    )
    if parsed.scheme not in allowed_schemes or not parsed.netloc:
        if parsed_env in livekit_env_names:
            raise LocalProviderConfigValidationError(
                f"{parsed_env} must be a ws(s) or http(s) URL with a host."
            )
        raise LocalProviderConfigValidationError(
            f"{parsed_env} must be an http(s) URL with a host."
        )
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise LocalProviderConfigValidationError(
            f"{parsed_env} must not include credentials, query strings, or fragments."
        )
    return value


def validated_managed_provider_config(config: dict[str, str]) -> dict[str, str]:
    validated: dict[str, str] = {}
    for env_name in LocalProviderConfigEnvName:
        raw_value = config.get(str(env_name))
        if not isinstance(raw_value, str):
            continue
        try:
            validated[str(env_name)] = validate_local_provider_config_value(
                env_name,
                raw_value,
            )
        except LocalProviderConfigValidationError:
            continue
    return validated


def sanitized_local_provider_config_for_write(config: dict[str, str]) -> dict[str, str]:
    sanitized: dict[str, str] = {}
    managed_names = {str(env_name) for env_name in LocalProviderConfigEnvName}
    for key, value in config.items():
        if key not in managed_names:
            sanitized[key] = value
    sanitized.update(validated_managed_provider_config(config))
    return sanitized


def is_default_local_provider_config_parent(project_root: Path, parent_path: Path) -> bool:
    return parent_path == project_root / ".secrets"
