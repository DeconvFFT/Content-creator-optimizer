#!/usr/bin/env bash
# Audio-format proxy for Agent Studio -> MLX-VLM local E4B.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export GEMMA4_LOCAL_PROXY_HOST="${GEMMA4_LOCAL_PROXY_HOST:-127.0.0.1}"
export GEMMA4_LOCAL_PROXY_PORT="${GEMMA4_LOCAL_PROXY_PORT:-8090}"
export GEMMA4_LOCAL_UPSTREAM_URL="${GEMMA4_LOCAL_UPSTREAM_URL:-http://127.0.0.1:8080/v1/chat/completions}"
export GEMMA4_LOCAL_MLX_MODEL="${GEMMA4_LOCAL_MLX_MODEL:-mlx-community/gemma-4-e4b-it-4bit}"

if command -v uv >/dev/null; then
  uv pip install -q httpx fastapi uvicorn 2>/dev/null || true
  exec uv run python3 scripts/local_gemma_e4b_proxy.py
else
  python3 -m pip install -q httpx fastapi uvicorn
  exec python3 scripts/local_gemma_e4b_proxy.py
fi
