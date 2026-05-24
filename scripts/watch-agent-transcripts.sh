#!/usr/bin/env bash
# Live-monitor Cursor subagent transcript JSONL files.
# Thinking/reasoning blocks are [REDACTED] in transcripts — only tool calls and visible text appear.

set -euo pipefail

DEFAULT_DIR="${HOME}/.cursor/projects/Users-saumyamehta-Gen-AI-all-about-llms/agent-transcripts/dc541605-3c57-402f-bbbd-538d6748fe61/subagents"

# Usage: watch-agent-transcripts.sh [list|tail|tail-all] ...
#    or: watch-agent-transcripts.sh [transcript_dir] [list|tail|tail-all] ...
if [[ "${1:-}" == "list" || "${1:-}" == "tail" || "${1:-}" == "tail-all" ]]; then
  TRANSCRIPT_DIR="$DEFAULT_DIR"
  CMD="$1"
  shift
else
  TRANSCRIPT_DIR="${1:-$DEFAULT_DIR}"
  CMD="${2:-list}"
  shift 2 2>/dev/null || true
fi

print_header() {
  echo "============================================================"
  echo " Agent transcript monitor"
  echo " Directory: $TRANSCRIPT_DIR"
  echo " NOTE: Full reasoning/thinking traces are NOT stored."
  echo "       [REDACTED] blocks appear instead of chain-of-thought."
  echo "============================================================"
}

list_agents() {
  print_header
  echo
  if [[ ! -d "$TRANSCRIPT_DIR" ]]; then
    echo "Directory not found: $TRANSCRIPT_DIR" >&2
    exit 1
  fi
  shopt -s nullglob
  local files=("$TRANSCRIPT_DIR"/*.jsonl)
  if [[ ${#files[@]} -eq 0 ]]; then
    echo "No .jsonl transcript files found."
    exit 0
  fi
  printf "%-10s  %-8s  %s\n" "AGENT_ID" "LINES" "FILE"
  printf "%-10s  %-8s  %s\n" "--------" "-----" "----"
  for f in "${files[@]}"; do
    local id
    id="$(basename "$f" .jsonl)"
    local lines
    lines="$(wc -l < "$f" | tr -d ' ')"
    printf "%-10s  %-8s  %s\n" "${id:0:8}" "$lines" "$(basename "$f")"
  done
}

format_line() {
  local line="$1"
  if command -v jq >/dev/null 2>&1; then
    local role
    role="$(echo "$line" | jq -r '.role // "?"')"
    if [[ "$role" == "assistant" ]]; then
      echo "$line" | jq -r '
        .message.content[]? |
        if .type == "text" then
          if (.text | test("\\[REDACTED\\]")) then "[thinking redacted by Cursor]"
          else (.text | split("\n")[0][0:120]) end
        elif .type == "tool_use" then
          if .name == "UpdateCurrentStep" then "STEP: " + (.input.current_step // "?")
          elif .name == "Shell" then "SHELL: " + ((.input.command // "")[0:80])
          elif .name == "Read" then "READ: " + ((.input.path // "") | split("/") | last)
          else .name end
        else empty end
      ' 2>/dev/null | sed '/^$/d' | while read -r part; do
        echo "  $part"
      done
      echo "[$role] activity"
    else
      echo "[$role] message"
    fi
  else
    echo "$line"
  fi
}

tail_file() {
  local file="$1"
  local id
  id="$(basename "$file" .jsonl)"
  echo "--- tail -f ${id:0:8} ($(basename "$file")) ---"
  tail -n 0 -f "$file" | while read -r line; do
    echo "[$(date +%H:%M:%S)]"
    format_line "$line"
    echo
  done
}

resolve_file() {
  local prefix="$1"
  shopt -s nullglob
  local matches=("$TRANSCRIPT_DIR"/${prefix}*.jsonl)
  if [[ ${#matches[@]} -eq 0 ]]; then
    echo "No transcript matching prefix: $prefix" >&2
    exit 1
  fi
  if [[ ${#matches[@]} -gt 1 ]]; then
    echo "Multiple matches for prefix $prefix:" >&2
    printf '  %s\n' "${matches[@]}" >&2
    exit 1
  fi
  echo "${matches[0]}"
}

case "$CMD" in
  list)
    list_agents
    ;;
  tail)
    prefix="${1:-}"
    if [[ -z "$prefix" ]]; then
      echo "Usage: $0 tail <agent-id-prefix>" >&2
      echo "Example: $0 tail fd7b525b" >&2
      exit 1
    fi
    print_header
    tail_file "$(resolve_file "$prefix")"
    ;;
  tail-all)
    print_header
    echo "Tailing all transcripts (Ctrl+C to stop)..."
    shopt -s nullglob
    pids=()
    for f in "$TRANSCRIPT_DIR"/*.jsonl; do
      tail_file "$f" &
      pids+=($!)
    done
    trap 'kill "${pids[@]}" 2>/dev/null; exit' INT TERM
    wait
    ;;
  *)
    echo "Usage:" >&2
    echo "  $0 list" >&2
    echo "  $0 tail <agent-id-prefix>" >&2
    echo "  $0 tail-all" >&2
    echo "  $0 <transcript_dir> list|tail|tail-all ..." >&2
    exit 1
    ;;
esac
