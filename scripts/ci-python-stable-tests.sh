#!/usr/bin/env bash
set -euo pipefail

uv run pytest \
  tests/test_provider_proof_plan_cli.py \
  tests/test_repo_workflow_ci.py \
  tests/test_livekit_voice_timing_capture.py \
  tests/test_cli_scheduler.py \
  tests/test_proof_readiness_browser.py \
  tests/test_blocker_acceptance_gates_browser.py \
  tests/test_gemma_voice_boundary_browser.py \
  tests/test_worker_scheduler_supervisor.py \
  tests/test_voice_agent.py::test_local_voice_agent_supervisor_redacts_secret_log_tail \
  tests/test_api_contracts.py::test_huggingface_gemma_provider_uses_router_default \
  tests/test_api_contracts.py::test_huggingface_gemma_provider_can_disable_default_endpoint \
  tests/test_api_contracts.py::test_voice_runtime_readiness_allows_openrouter_text_turn_dialogue_without_multimodal_endpoint \
  tests/test_api_contracts.py::test_voice_runtime_readiness_keeps_native_gemma_audio_check_when_openrouter_also_configured \
  -q
