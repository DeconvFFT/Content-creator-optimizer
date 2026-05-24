from typing import Any

import httpx

from all_about_llms.providers.interfaces import (
    GemmaRequest,
    GemmaResponse,
    ProviderConfigurationError,
)


class HuggingFaceGemmaProvider:
    """Gemma 4 expert provider backed by a Hugging Face HTTP endpoint."""

    def __init__(
        self,
        *,
        token: str | None,
        default_endpoint_url: str | None,
        timeout_seconds: float = 120.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._token = token
        self._default_endpoint_url = default_endpoint_url
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def complete(self, request: GemmaRequest) -> GemmaResponse:
        disable_default_endpoint = bool(request.metadata.get("disable_default_endpoint"))
        endpoint_url = request.metadata.get("endpoint_url") or (
            None if disable_default_endpoint else self._default_endpoint_url
        )
        if not endpoint_url:
            raise ProviderConfigurationError("Gemma 4 endpoint URL is not configured.")
        if not self._token:
            raise ProviderConfigurationError("HF_TOKEN is not configured.")

        payload: dict[str, Any] = {
            "model": request.model_id,
            "messages": [
                {"role": "system", "content": request.system_context},
                {
                    "role": "user",
                    "content": _build_user_content(
                        request.user_input,
                        request.attachments,
                    ),
                },
            ],
        }
        if request.response_format:
            payload["response_format"] = request.response_format
        if request.attachments:
            # Keep the side-channel for custom HF endpoint handlers while also
            # making the chat message compatible with Gemma multimodal templates.
            payload["attachments"] = request.attachments

        client_kwargs: dict[str, Any] = {"timeout": self._timeout_seconds}
        if self._transport is not None:
            client_kwargs["transport"] = self._transport
        try:
            async with httpx.AsyncClient(**client_kwargs) as client:
                response = await client.post(
                    endpoint_url,
                    headers={"Authorization": f"Bearer {self._token}"},
                    json=payload,
                )
                response.raise_for_status()
                raw = response.json()
        except httpx.HTTPStatusError as exc:
            raise ProviderConfigurationError(
                "Gemma 4 request failed with provider HTTP status "
                f"{exc.response.status_code}."
            ) from exc
        except httpx.RequestError as exc:
            raise ProviderConfigurationError("Gemma 4 request failed.") from exc
        except ValueError as exc:
            raise ProviderConfigurationError(
                "Gemma 4 provider returned invalid JSON."
            ) from exc

        if not isinstance(raw, dict):
            raise ProviderConfigurationError(
                "Gemma 4 provider returned non-object JSON."
            )
        content = _extract_content(raw)
        if not content.strip():
            raise ProviderConfigurationError(
                "Gemma 4 provider returned no usable content."
            )

        return GemmaResponse(
            model_id=request.model_id,
            agent_id=request.agent_id,
            content=content,
            raw_response=raw,
            usage=raw.get("usage", {}),
        )


def _extract_content(raw: dict[str, Any]) -> str:
    choices = raw.get("choices")
    if isinstance(choices, list) and choices:
        choice = choices[0]
        if isinstance(choice, dict):
            message = choice.get("message", {})
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    return "\n".join(
                        part.get("text", "")
                        for part in content
                        if isinstance(part, dict) and part.get("text")
                    )
    if isinstance(raw.get("generated_text"), str):
        return raw["generated_text"]
    if isinstance(raw.get("text"), str):
        return raw["text"]
    return ""


def _build_user_content(
    user_input: str,
    attachments: list[dict[str, Any]],
) -> str | list[dict[str, Any]]:
    multimodal_parts = [
        part
        for attachment in attachments
        if (part := _attachment_to_message_part(attachment)) is not None
    ]
    if not multimodal_parts:
        return user_input
    return [*multimodal_parts, {"type": "text", "text": user_input}]


def _attachment_to_message_part(
    attachment: dict[str, Any],
) -> dict[str, Any] | None:
    attachment_type = attachment.get("type") or attachment.get("modality")
    if attachment_type == "audio":
        if attachment.get("content_base64"):
            return {
                "type": "audio",
                "audio_base64": attachment["content_base64"],
                "audio_format": attachment.get("audio_format"),
                "sample_rate": attachment.get("sample_rate"),
            }
        if attachment.get("uri"):
            return {"type": "audio", "audio": attachment["uri"]}
    if attachment_type == "image":
        image_uri = attachment.get("uri") or attachment.get("asset_uri")
        if image_uri:
            return {"type": "image", "url": image_uri}
    if attachment_type == "video":
        video_uri = attachment.get("uri") or attachment.get("asset_uri")
        if video_uri:
            return {"type": "video", "video": video_uri}
    return None
