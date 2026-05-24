import importlib.util
from dataclasses import dataclass
from urllib.parse import urlparse

from all_about_llms.config import Settings


@dataclass(frozen=True, slots=True)
class KokoroRuntimeRoute:
    provider: str | None
    transport: str
    endpoint_url: str | None
    endpoint_configured: bool
    endpoint_supplied: bool
    endpoint_error: str | None
    local_package_available: bool

    @property
    def ready(self) -> bool:
        return self.transport in {"hf_endpoint", "local_package"}

    def metadata(self) -> dict[str, object]:
        return {
            "kokoro_provider": self.provider,
            "kokoro_transport": self.transport,
            "kokoro_endpoint_configured": self.endpoint_configured,
            "kokoro_endpoint_supplied": self.endpoint_supplied,
            "kokoro_endpoint_error": self.endpoint_error,
            "kokoro_local_package_available": self.local_package_available,
        }

    def evidence(self) -> str:
        if self.transport == "hf_endpoint":
            return "Hosted Kokoro endpoint is configured."
        if self.transport == "local_package":
            if self.endpoint_error:
                return (
                    "Local Kokoro package is importable; "
                    "malformed hosted endpoint is ignored."
                )
            return "Local Kokoro package is importable."
        if self.endpoint_error:
            return "Kokoro hosted endpoint is malformed and local Kokoro is not available."
        return "Kokoro TTS needs an endpoint or local voice extra installation."

    def configuration_error(self) -> str:
        if self.endpoint_error:
            return (
                f"{self.endpoint_error} Provide a valid KOKORO_TTS_ENDPOINT_URL "
                "or install the voice extra with local Kokoro support."
            )
        return (
            "KOKORO_TTS_ENDPOINT_URL or the local Kokoro package is required "
            "for Kokoro TTS."
        )


def _trimmed_kokoro_endpoint_url(settings: Settings) -> str | None:
    if settings.kokoro_tts_endpoint_url is None:
        return None
    endpoint_url = str(settings.kokoro_tts_endpoint_url).strip()
    return endpoint_url or None


def _validated_kokoro_endpoint_url(
    endpoint_url: str | None,
) -> tuple[str | None, str | None]:
    if endpoint_url is None:
        return None, None
    parsed = urlparse(endpoint_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None, "KOKORO_TTS_ENDPOINT_URL must be an http(s) URL with a host."
    return endpoint_url, None


def kokoro_local_package_available() -> bool:
    return importlib.util.find_spec("kokoro") is not None


def kokoro_runtime_route(settings: Settings) -> KokoroRuntimeRoute:
    supplied_endpoint_url = _trimmed_kokoro_endpoint_url(settings)
    endpoint_url, endpoint_error = _validated_kokoro_endpoint_url(supplied_endpoint_url)
    local_available = kokoro_local_package_available()
    if endpoint_url:
        return KokoroRuntimeRoute(
            provider="huggingface_kokoro",
            transport="hf_endpoint",
            endpoint_url=endpoint_url,
            endpoint_configured=True,
            endpoint_supplied=True,
            endpoint_error=None,
            local_package_available=local_available,
        )
    if local_available:
        return KokoroRuntimeRoute(
            provider="local_kokoro",
            transport="local_package",
            endpoint_url=None,
            endpoint_configured=False,
            endpoint_supplied=supplied_endpoint_url is not None,
            endpoint_error=endpoint_error,
            local_package_available=True,
        )
    return KokoroRuntimeRoute(
        provider=None,
        transport="missing",
        endpoint_url=None,
        endpoint_configured=False,
        endpoint_supplied=supplied_endpoint_url is not None,
        endpoint_error=endpoint_error,
        local_package_available=False,
    )
