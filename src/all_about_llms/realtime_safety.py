import re
from typing import Any


def redact_realtime_string(value: str) -> str:
    redacted = re.sub(
        r"Bearer\s+[A-Za-z0-9._~+/=-]+",
        "Bearer [redacted]",
        value,
        flags=re.IGNORECASE,
    )
    redacted = re.sub(r"hf_[A-Za-z0-9]{20,}", "hf_[redacted]", redacted)
    redacted = re.sub(r"tvly-[A-Za-z0-9-]{20,}", "tvly-[redacted]", redacted)
    return redacted


def safe_realtime_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    safe_metadata: dict[str, Any] = {}
    for key, value in metadata.items():
        if realtime_metadata_key_is_sensitive(key):
            if normalize_realtime_metadata_key(key) == "token" and value is None:
                safe_metadata[key] = None
            continue
        safe_metadata[key] = safe_realtime_metadata_value(value)
    return safe_metadata


def safe_realtime_metadata_value(value: Any) -> Any:
    if isinstance(value, dict):
        return safe_realtime_metadata(value)
    if isinstance(value, list):
        return [safe_realtime_metadata_value(item) for item in value]
    if isinstance(value, str):
        return redact_realtime_string(value)
    return value


def realtime_metadata_key_is_sensitive(key: object) -> bool:
    if not isinstance(key, str) or not key.strip():
        return False
    normalized = normalize_realtime_metadata_key(key)
    safe_exact = {
        "control_binding_required",
        "control_binding_token_issued",
        "has_token",
        "has_transport_token",
        "livekit_token_expires_at_unix",
        "token_persisted",
    }
    if normalized in safe_exact:
        return False
    compact = normalized.replace("_", "")
    sensitive_exact = {
        "access_token",
        "api_key",
        "api_secret",
        "authorization",
        "binding_signature",
        "binding_token",
        "client_secret",
        "control_binding_signature",
        "control_binding_token",
        "livekit_token",
        "private_key",
        "raw_request",
        "raw_response",
        "refresh_token",
        "session_token",
        "signed_url",
        "token",
        "websocket_url",
    }
    sensitive_compact = {item.replace("_", "") for item in sensitive_exact}
    if normalized in sensitive_exact or compact in sensitive_compact:
        return True
    if (
        "authorization" in compact
        or "bearer" in compact
        or "credential" in compact
    ):
        return True
    return normalized.endswith(("_key", "_secret", "_token", "_password"))


def normalize_realtime_metadata_key(key: str) -> str:
    camel_split = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key.strip())
    return re.sub(r"[^a-z0-9]+", "_", camel_split.lower()).strip("_")
