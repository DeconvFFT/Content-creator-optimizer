#!/usr/bin/env bash
# Start local Gemma 4 E4B via MLX-VLM (Apple Silicon).
# First run downloads ~3–16 GB model weights from Hugging Face.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MODEL="${GEMMA4_LOCAL_MLX_MODEL:-mlx-community/gemma-4-e4b-it-4bit}"
PORT="${GEMMA4_LOCAL_MLX_PORT:-8080}"

echo "==> Gemma 4 E4B local MLX server"
echo "    Model: $MODEL"
echo "    OpenAI base: http://127.0.0.1:${PORT}/v1"
echo ""

if ! command -v python3 >/dev/null; then
  echo "python3 required" >&2
  exit 1
fi

# Prefer project .venv so mlx_vlm is visible to the server process
VENV_PY="$ROOT/.venv/bin/python"
if [[ -x "$VENV_PY" ]]; then
  echo "==> Installing mlx-vlm into project .venv (network required)..."
  if command -v uv >/dev/null; then
    UV_HTTP_TIMEOUT="${UV_HTTP_TIMEOUT:-300}" uv pip install --python "$VENV_PY" -U "mlx-vlm" "mlx-lm" "mlx"
  else
    "$VENV_PY" -m pip install -U "mlx-vlm" "mlx-lm" "mlx"
  fi
  RUN=("$VENV_PY" -m)
elif command -v uv >/dev/null; then
  echo "==> Installing mlx-vlm into uv env (network required)..."
  UV_HTTP_TIMEOUT="${UV_HTTP_TIMEOUT:-300}" uv pip install -U "mlx-vlm" "mlx-lm" "mlx"
  RUN=(uv run python3 -m)
else
  echo "==> Installing mlx-vlm into user pip (network required)..."
  python3 -m pip install -U "mlx-vlm" "mlx-lm" "mlx"
  RUN=(python3 -m)
fi

echo ""
echo "==> Starting mlx_vlm.server on port $PORT"
echo "    Set in .env:"
echo "      GEMMA4_MULTIMODAL_ENDPOINT_URL=http://127.0.0.1:${PORT}/v1/chat/completions"
echo "    Or use the audio proxy (recommended for this app):"
echo "      GEMMA4_MULTIMODAL_ENDPOINT_URL=http://127.0.0.1:8090/gemma-audio-stream"
echo "      (run scripts/start-local-gemma-e4b-proxy.sh in another terminal)"
echo ""

exec "${RUN[@]}" mlx_vlm.server --host 127.0.0.1 --port "$PORT" --model "$MODEL"
