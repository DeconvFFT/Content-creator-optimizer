#!/usr/bin/env python3
"""Local adapter: Agent Studio Gemma audio streaming format -> MLX-VLM / OpenAI SSE.

The voice agent POSTs a custom JSON payload with audio_base64 message parts and
expects Server-Sent Events (OpenAI chat.completion.chunk shape).

Point GEMMA4_MULTIMODAL_ENDPOINT_URL at:
  http://127.0.0.1:8090/gemma-audio-stream

Upstream (optional): MLX server at GEMMA4_LOCAL_UPSTREAM_URL
  default http://127.0.0.1:8080/v1/chat/completions
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import sys
import tempfile
import wave
from typing import Any

import httpx
from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn

UPSTREAM = os.environ.get(
    "GEMMA4_LOCAL_UPSTREAM_URL",
    "http://127.0.0.1:8080/v1/chat/completions",
)
HOST = os.environ.get("GEMMA4_LOCAL_PROXY_HOST", "127.0.0.1")
PORT = int(os.environ.get("GEMMA4_LOCAL_PROXY_PORT", "8090"))
HF_TOKEN = os.environ.get("HF_TOKEN", "local-dev")

app = FastAPI(title="local-gemma-e4b-proxy")


def _extract_text_and_audio(payload: dict[str, Any]) -> tuple[str, bytes | None, int, str]:
    model = str(payload.get("model") or "google/gemma-4-e4b-it")
    messages = payload.get("messages") or []
    system = ""
    user_text = ""
    audio_pcm: bytes | None = None
    sample_rate = 16000
    audio_format = "pcm_s16le"
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        content = msg.get("content")
        if role == "system" and isinstance(content, str):
            system = content
        if role == "user":
            if isinstance(content, str):
                user_text = content
            elif isinstance(content, list):
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    if part.get("type") == "text" and part.get("text"):
                        user_text = str(part["text"])
                    if part.get("type") == "audio" and part.get("audio_base64"):
                        audio_pcm = base64.b64decode(str(part["audio_base64"]))
                        sample_rate = int(part.get("sample_rate") or sample_rate)
                        audio_format = str(part.get("audio_format") or audio_format)
    attachments = payload.get("attachments") or []
    if audio_pcm is None and isinstance(attachments, list):
        for att in attachments:
            if isinstance(att, dict) and att.get("content_base64"):
                audio_pcm = base64.b64decode(str(att["content_base64"]))
                sample_rate = int(att.get("sample_rate") or sample_rate)
                audio_format = str(att.get("audio_format") or audio_format)
                break
    return model, audio_pcm, sample_rate, user_text or system or "Respond briefly."


def _pcm_to_wav_path(pcm: bytes, sample_rate: int) -> str:
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.sampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return path


def _openai_sse_chunk(text: str, model: str) -> str:
    body = {
        "id": "local-gemma-chunk",
        "object": "chat.completion.chunk",
        "model": model,
        "choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}],
    }
    return f"data: {json.dumps(body)}\n\n"


async def _stream_upstream_openai(
    *,
    token: str,
    model: str,
    system: str,
    user_text: str,
) -> Any:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system or "You are a helpful voice assistant."},
            {"role": "user", "content": user_text},
        ],
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            UPSTREAM,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "text/event-stream",
            },
            json=payload,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip():
                    yield line + "\n"


async def _stream_mlx_vlm_generate(
    *,
    model: str,
    prompt: str,
    image_path: str | None = None,
    audio_path: str | None = None,
) -> Any:
    """Call mlx_vlm in-process when server path lacks audio message parts."""

    def _run() -> str:
        from mlx_vlm import generate, load
        from mlx_vlm.prompt_utils import apply_chat_template

        mlx_model, processor = load(model)
        config = getattr(mlx_model, "config", None)
        formatted = apply_chat_template(processor, config, prompt)
        kwargs: dict[str, Any] = {
            "model": mlx_model,
            "processor": processor,
            "prompt": formatted,
            "max_tokens": 256,
            "temperature": 0.7,
            "verbose": False,
        }
        if image_path:
            kwargs["image"] = image_path
        if audio_path:
            kwargs["audio"] = audio_path
        result = generate(**kwargs)
        if hasattr(result, "text"):
            return str(result.text)
        return str(result)

    text = await asyncio.to_thread(_run)
    # Emit as single SSE chunk (Agent Studio accepts OpenAI delta shape)
    yield _openai_sse_chunk(text, model)
    yield "data: [DONE]\n\n"


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "upstream": UPSTREAM}


@app.post("/gemma-audio-stream")
async def gemma_audio_stream(
    request: Request,
    authorization: str | None = Header(default=None),
) -> StreamingResponse:
    if not authorization or not authorization.lower().startswith("bearer "):
        return JSONResponse(status_code=401, content={"detail": "Bearer token required"})

    token = authorization.split(" ", 1)[1].strip() or HF_TOKEN
    payload = await request.json()
    model, audio_pcm, sample_rate, user_text = _extract_text_and_audio(payload)

    async def event_stream() -> Any:
        wav_path: str | None = None
        try:
            if audio_pcm:
                wav_path = _pcm_to_wav_path(audio_pcm, sample_rate)
                prompt = f"{user_text}\n\n(The user spoke via audio; respond to their intent.)"
                async for chunk in _stream_mlx_vlm_generate(
                    model=os.environ.get("GEMMA4_LOCAL_MLX_MODEL", "mlx-community/gemma-4-e4b-it-4bit"),
                    prompt=prompt,
                    audio_path=wav_path,
                ):
                    yield chunk
                return

            # Text-only fallback via upstream OpenAI-compatible server
            async for line in _stream_upstream_openai(
                token=token,
                model=model,
                system="You are a helpful realtime voice assistant.",
                user_text=user_text,
            ):
                yield line + ("\n" if not line.endswith("\n") else "")
            yield "data: [DONE]\n\n"
        except httpx.HTTPError as exc:
            err = json.dumps({"error": f"upstream failed: {type(exc).__name__}"})
            yield f"data: {err}\n\n"
        except Exception as exc:
            err = json.dumps({"error": f"local proxy: {type(exc).__name__}: {exc}"})
            yield f"data: {err}\n\n"
        finally:
            if wav_path and os.path.exists(wav_path):
                os.unlink(wav_path)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def main() -> None:
    print(f"Local Gemma E4B proxy http://{HOST}:{PORT}/gemma-audio-stream", file=sys.stderr)
    print(f"Upstream OpenAI (text): {UPSTREAM}", file=sys.stderr)
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
