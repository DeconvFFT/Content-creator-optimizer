# Agent Operating Contract

This repo is the product/code workspace for Agent Studio. The Obsidian vaults are planning and memory artifacts, not product UI. Keep the app boundary clear.

## Token Efficiency Principles (agents.md best practices)

These rules follow the agents.md format used by 60k+ projects (codex, hermes-agent, aider, etc.). Every agent and subagent MUST apply these.

### 1. Setup commands — use these exact commands (do not guess)
- Install deps: `uv sync` (Python) or `npm install` (frontend)
- Dev server: `uv run uvicorn src.all_about_llms.app:app --reload` or `cd frontend/next-app && npm run dev`
- Run tests: `uv run pytest tests/<scope>/ -v --tb=short -n auto` (narrow) or `uv run pytest tests/ -v --tb=short -n auto` (full)
- Lint: `uv run ruff check src/` and `uv run ruff format --check src/`
- Type check: `uv run mypy src/`
- Run single test: `uv run pytest tests/path/test_file.py::TestClass::test_name -v --tb=short`

### 2. Code style & conventions
- Python: ruff (line-length 100), mypy strict on new code, type annotations required for public APIs
- TypeScript: strict mode, single quotes, no semicolons, functional patterns where possible
- No bool literal positional args — prefer enums or named kwargs (`train(use_fp16=True)` not `train(True)`)
- Favor small focused modules under 500 LoC (excl. tests); split large files rather than extending them
- New public APIs need docstrings explaining role, contract, and expected usage
- Exhaustive match/enum handling — no bare wildcard arms unless semantically necessary
- Avoid `# type: ignore` without a documented justification comment

### 3. Testing patterns
- Always run the NARROWEST test first — only expand scope if the narrow test passes or reveals cross-cutting failures
- Before pushing: run tests for the specific module changed, then lint + type-check
- Do not run full test suite unless the change affects shared foundational code
- Test setup: fixtures live in `tests/conftest.py`, shared mocks in `tests/mocks/`
- CI runs via GitHub Actions — do not replicate CI workflows locally unless debugging a CI failure

### 4. Environment constraints awareness
- Local Mac (arm64), no GPU for inference — use OpenRouter for all model calls
- Do NOT kill/restart shared processes (Docker, LiveKit, backend server, Cursor) without explicit operator approval
- Cron jobs run in isolated sessions with NO conversation history — their prompts must be fully self-contained
- Subagents (delegate_task) get a fresh terminal session and NO memory — pass ALL context in the goal/context fields
- The model is deepseek/deepseek-v4-flash via OpenRouter — reasoning_effort=xhigh, temperature<=0.2
- Token budget: ~120 max iterations per agent loop, ~600 max per multi-agent run

### 5. Token efficiency rules (mandatory)
- Do NOT ls/find the filesystem to explore the project — use the file tree documented below
- For code lookup: use search_files() over reading entire files — context windows are expensive
- When debugging: state your hypothesis before running the first test; skip the "let me check" shotgun approach
- Subagent summaries should be compact (500-1000 chars) — no dumping full tool output
- Prefer reducing/filtering large outputs in execute_code before they enter your context
- Batch parallel work: delegate_task(tasks=[...]) for 3 concurrent subagents — sequential costs 3x tokens
- Use web_search over browser_navigate for simple info retrieval — browser is 10x more expensive
- When blocked: state the blocker clearly rather than retrying 3 times with the same approach

### 6. Subagent contracts (for spawned agents)
When you spawn a subagent, ensure it follows the same AGENTS.md contract:
- Pass the relevant AGENTS.md path in the context field: `"Load AGENTS.md rules from /path/to/AGENTS.md"`
- For task-specific agents (e.g. a Rust backend agent), the subagent should first read the task's local AGENTS.md or create one if none exists
- Subagent scope: focused on ONE task, returns a structured summary (what was done, files created, blockers)
- If a subagent needs to set up its own AGENTS.md for a specific tech stack, write it to the workdir before delegating

## Project Structure (canonical — do not explore via ls)

```
all-about-llms/
├── src/all_about_llms/       # Python application code
│   ├── app.py                # FastAPI app entry
│   ├── main.py               # CLI entrypoint
│   ├── agents/               # Agent card definitions, roster
│   ├── orchestration/        # Workflows, state machines
│   ├── providers/            # Provider interfaces & implementations
│   ├── voice_agent/          # Realtime voice engine
│   ├── storage/              # Postgres persistence
│   └── cli.py                # Admin CLI commands
├── frontend/next-app/        # Next.js product app
├── services/                 # Rust sidecars (voice-edge, retrieval-ranker)
├── infra/postgres/           # Schema DDL
├── social_media_optimiser/   # Project planning vault (Obsidian)
├── system_design_vault/      # Architecture knowledge vault (Obsidian)
└── tests/                    # Pytest suite
```

## Branch And PR Flow

- Use branch prefixes: `feature/` for new features, `fix_` plus timestamp/UUID for fixes, `tests/` for test-only
- Prefer small PR-style commits with focused verification notes
- Do not merge until CI is green and proof gates are checked
- CI gates: workflows in `.github/workflows/` — auto-pr creates draft PRs from matching branches
- If PR creation blocked, try `provider-proof-pr-create` helper; if still blocked, leave branch pushed and record blocker

## Files That May Be Versioned

- Code, tests, `.github/workflows/ci.yml`, `.github/workflows/auto-pr.yml`, `uv.lock`, lightweight Markdown coordination files, `AGENTS.md`, `agents.md`, `CLOUD.md`, and `cloud.md`.
- `uv.lock` is the committed Python dependency lockfile; include when deps change.
- Local command-log artifacts are transient output — never track.

## Files That Must Stay Out

- Do NOT commit secrets, `.env` values, provider tokens, raw private provider responses, private audio, screenshots, PDFs, generated media, proof workspaces, local caches, or large artifacts.
- Use `.secrets/...` only in local operator inputs; never print or commit secret contents.

## Current Realtime Stack

- Active realtime dialogue: OpenRouter `deepseek/deepseek-v4-flash` + LiveKit + Kokoro.
- Do NOT use Hugging Face, Gemma4, Gamma4, or MLX as realtime defaults.
- Do NOT restart Cursor, backend, LiveKit, Docker, or shared local processes without explicit approval.

## Vault Coordination

- Check `agent_progress_vault` for background-agent status before runtime-sensitive work.
- Durable implementation memory: `social_media_optimiser`. Architecture implications: `system_design_vault`.
- Preserve source attribution; avoid duplicate long-form notes across vaults.

## Proof Gates

- `provider-backed-live-voice-proof`: OpenRouter/LiveKit/Kokoro proof gate — accepted state must not be reopened without new evidence.
- `external-publication-proof`: Remaining publication gate — must not be faked locally.
- Requires operator inputs: `LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID`, `PUBLICATION_DURABLE_PLATFORM_ID_OR_URL`, `PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID`.
- After inputs supplied: refresh readiness → credential snapshot → proof plan → blocker matrix → status → unblocker checklist → completion → closure review → blocker-state update.

## Verification Baseline

- Run the narrowest test for your change first.
- Before pushing: run tests for the touched module, then lint + type-check.
- Proof-gate changes: include fresh no-secret provider-readiness evidence in vault handoff.
