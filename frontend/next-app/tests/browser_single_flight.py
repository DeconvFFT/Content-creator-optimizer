import asyncio
import json
import os
import signal
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.async_api import async_playwright, expect


ROOT = Path(__file__).resolve().parents[3]
APP_DIR = ROOT / "frontend" / "next-app"
RUN_ID = "11111111-1111-4111-8111-111111111111"
TURN_ID = "22222222-2222-4222-8222-222222222222"
SOURCE_ID = "33333333-3333-4333-8333-333333333333"
SEED_SOURCE_ID = "33333333-3333-4333-8333-333333333334"
CLAIM_ID = "44444444-4444-4444-8444-444444444444"
SEED_CLAIM_ID = "44444444-4444-4444-8444-444444444445"
ARTIFACT_ID = "55555555-5555-4555-8555-555555555555"
AGENT_MESSAGE_ID = "99999999-9999-4999-8999-999999999999"
RUN_PLAN_MESSAGE_ID = "99999999-9999-4999-8999-999999999998"
RETRY_MESSAGE_ID = "99999999-9999-4999-8999-999999999997"
WORK_PLAN_ITEM_ID = "66666666-6666-4666-8666-666666666666"
PROFILE_ID = "88888888-8888-4888-8888-888888888888"
FEEDBACK_ID = "77777777-7777-4777-8777-777777777770"
NOW = "2026-05-19T18:00:00.000Z"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def wait_for_url(url: str, deadline: float) -> bool:
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=0.75) as response:
                if response.status < 500:
                    return True
        except (OSError, urllib.error.URLError):
            time.sleep(0.25)
    return False


def existing_next_dev_url(log_text: str) -> str | None:
    if "Another next dev server is already running" not in log_text:
        return None
    match = re.search(r"http://localhost:(\d+)", log_text)
    if match:
        return f"http://127.0.0.1:{match.group(1)}"
    return None


def wait_for_server(port: int, log_path: Path) -> str:
    deadline = time.time() + 45
    url = f"http://127.0.0.1:{port}"
    while time.time() < deadline:
        if wait_for_url(url, time.time() + 0.75):
            return url
        log_text = log_path.read_text(errors="replace") if log_path.exists() else ""
        existing_url = existing_next_dev_url(log_text)
        if existing_url and wait_for_url(existing_url, time.time() + 5):
            return existing_url
    log_tail = log_path.read_text(errors="replace")[-4000:] if log_path.exists() else ""
    raise RuntimeError(f"Next dev server did not start on {url}.\n{log_tail}")


def run_state() -> dict:
    return {
        "run_id": RUN_ID,
        "goal": "Browser single-flight validation run",
        "status": "running",
        "conversation_state": {},
        "active_agents": [],
        "source_record_ids": [SOURCE_ID, SEED_SOURCE_ID],
        "artifact_ids": [ARTIFACT_ID],
        "feedback_item_ids": [FEEDBACK_ID],
        "created_at": NOW,
        "updated_at": NOW,
    }


def run_context() -> dict:
    return {
        "run": run_state(),
        "conversation_turns": [
            {
                "turn_id": TURN_ID,
                "run_id": RUN_ID,
                "speaker": "user",
                "modality": "text",
                "transcript": "Create a source-backed browser single-flight proof.",
                "audio_uri": None,
                "metadata": {},
                "created_at": NOW,
            }
        ],
        "agent_messages": [
            {
                "message_id": RETRY_MESSAGE_ID,
                "run_id": RUN_ID,
                "sender_agent_id": "editor-in-chief",
                "recipient_agent_id": "script-doctor-agent",
                "task_type": "revise_script",
                "status": "failed",
                "payload": {
                    "target_artifact_ids": [ARTIFACT_ID],
                    "summary": "Retry fixture task should run once.",
                },
                "result": {
                    "retry_policy": {
                        "reason": "Script Doctor needs a bounded retry."
                    }
                },
                "error": "Retry fixture failed before completion.",
                "depends_on_message_ids": [],
                "requires_human_feedback": False,
                "attempt_count": 1,
                "max_attempts": 3,
                "created_at": NOW,
                "updated_at": NOW,
            }
        ],
        "recent_events": [],
        "sources": [
            {
                "source_id": SOURCE_ID,
                "run_id": RUN_ID,
                "citation_id": "S1",
                "title": "Browser single-flight source",
                "url": "https://example.com/browser-single-flight",
                "publisher": "Example",
                "retrieved_at": NOW,
                "published_at": NOW,
                "metadata": {"source_type": "official_documentation"},
            },
            {
                "source_id": SEED_SOURCE_ID,
                "run_id": RUN_ID,
                "citation_id": "S2",
                "title": "Live web research needed",
                "url": "https://www.google.com/search?q=browser+single+flight",
                "publisher": "Web search task",
                "retrieved_at": NOW,
                "published_at": None,
                "metadata": {
                    "source_type": "search_query_seed",
                    "requires_web_search": True,
                    "search_query": "browser single-flight source refresh",
                },
            }
        ],
        "claims": [
            {
                "claim_id": CLAIM_ID,
                "run_id": RUN_ID,
                "claim_text": "Rapid duplicate UI submits must not create duplicate actions.",
                "support_status": "supported",
                "source_ids": [SOURCE_ID],
                "reviewer_agent_id": "claim-verification-agent",
                "notes": "Supported by test fixture source.",
            },
            {
                "claim_id": SEED_CLAIM_ID,
                "run_id": RUN_ID,
                "claim_text": "Source refresh should replace search-query seeds before publishing.",
                "support_status": "needs_review",
                "source_ids": [SEED_SOURCE_ID],
                "reviewer_agent_id": "claim-verification-agent",
                "notes": "Fixture claim keeps the search seed unresolved for browser refresh proof.",
            }
        ],
        "artifacts": [
            {
                "artifact_id": ARTIFACT_ID,
                "run_id": RUN_ID,
                "artifact_type": "post",
                "title": "Browser Single-Flight Draft",
                "uri": "artifact://browser-single-flight-draft",
                "content": {
                    "body": "A source-backed draft used by browser single-flight validation.",
                    "claim_ids": [CLAIM_ID, SEED_CLAIM_ID],
                    "source_citations": ["S1"],
                },
                "provenance": {
                    "workflow": "browser_single_flight_fixture",
                    "claim_ids": [CLAIM_ID, SEED_CLAIM_ID],
                },
                "source_ids": [SOURCE_ID],
                "reviewer_decisions": [
                    {"reviewer_agent_id": "editor-in-chief", "status": "approved"}
                ],
                "revision_history": [
                    {"actor": "browser-single-flight-test", "note": "Fixture draft."}
                ],
                "created_at": NOW,
            }
        ],
        "feedback_items": [feedback_item()],
        "summary": {"fixture": "browser_single_flight"},
        "context_risks": [],
        "recommended_fetches": [],
        "source_evidence": [
            {
                "source_id": SOURCE_ID,
                "citation_id": "S1",
                "title": "Browser single-flight source",
                "url": "https://example.com/browser-single-flight",
                "publisher": "Example",
                "source_type": "official_documentation",
                "snippet": "Fixture evidence for browser-level duplicate-submit validation.",
                "published_at": NOW,
                "retrieved_at": NOW,
                "quality_status": "strong",
                "freshness_status": "fresh",
                "quality_flags": [],
                "claim_ids": [CLAIM_ID],
                "artifact_ids": [ARTIFACT_ID],
                "accepted_for_context": True,
            },
            {
                "source_id": SEED_SOURCE_ID,
                "citation_id": "S2",
                "title": "Live web research needed",
                "url": "https://www.google.com/search?q=browser+single+flight",
                "publisher": "Web search task",
                "source_type": "search_query_seed",
                "snippet": "Fixture search seed that must be replaced by source refresh.",
                "published_at": None,
                "retrieved_at": NOW,
                "quality_status": "weak",
                "freshness_status": "current",
                "quality_flags": ["requires live provider research"],
                "claim_ids": [SEED_CLAIM_ID],
                "artifact_ids": [],
                "accepted_for_context": False,
            }
        ],
    }


def worker_scheduler_status() -> dict:
    return {
        "enabled": True,
        "status": "stopped",
        "running": False,
        "pid": None,
        "returncode": None,
        "last_error": None,
        "started_at": None,
        "stopped_at": None,
        "run_id": None,
        "execution_mode": "autonomous_pass",
        "max_profiles": 10,
        "poll_interval_seconds": 5,
        "command": [],
        "log_tail": [],
        "next_actions": [],
        "summary": "Browser fixture scheduler is stopped.",
    }


def worker_scheduler_running_status() -> dict:
    payload = worker_scheduler_status()
    payload.update(
        {
            "status": "running",
            "running": True,
            "pid": 4242,
            "run_id": RUN_ID,
            "summary": "Local worker scheduler process is running.",
        }
    )
    return payload


def worker_scheduler_stopped_status() -> dict:
    payload = worker_scheduler_status()
    payload["summary"] = "Background runner is stopped."
    return payload


def active_worker_profile() -> dict:
    return {
        "profile_id": PROFILE_ID,
        "run_id": RUN_ID,
        "name": "Creator app autopilot",
        "execution_mode": "autonomous_pass",
        "agent_ids": ["web-research-agent"],
        "max_tasks_per_agent": 1,
        "max_rounds": 2,
        "poll_interval_seconds": 5,
        "include_global_memories": True,
        "memory_limit": 8,
        "autonomous_auto_refresh_research_sources": True,
        "autonomous_block_on_research_freshness_blocked": True,
        "autonomous_block_on_retrieval_quality_blocked": True,
        "autonomous_export_memory_summary_to_obsidian": True,
        "autonomous_memory_summary_agent_id": None,
        "autonomous_memory_summary_limit": 8,
        "use_gemma": True,
        "fail_on_provider_error": False,
        "status": "active",
        "last_heartbeat_at": "2999-01-01T00:00:00.000Z",
        "heartbeat_claimed_at": None,
        "heartbeat_claimed_by": None,
        "heartbeat_lease_until": None,
        "created_at": NOW,
        "updated_at": NOW,
    }


def stopped_worker_profile() -> dict:
    payload = active_worker_profile()
    payload["status"] = "stopped"
    payload["updated_at"] = NOW
    return payload


def autopilot_launch_result() -> dict:
    return {
        "run_id": RUN_ID,
        "profile": active_worker_profile(),
        "created_profile": True,
        "reused_profile": False,
        "started_profile": True,
        "heartbeat_result": None,
        "launch_ledger_artifact": None,
        "event_id": 1001,
        "summary": "Autopilot launch recorded. Creator app autopilot will run specialist heartbeats.",
    }


def worker_profile_heartbeat_result() -> dict:
    return {
        "profile": active_worker_profile(),
        "skipped": False,
        "skipped_reason": None,
        "summary": "Browser fixture specialist pulse finished.",
        "heartbeat_ledger_artifact": None,
        "context_packet_artifact": None,
        "autonomous_pass_result": {"event_id": 7001},
        "cycle_result": {"total_processed_tasks": 0},
    }


def worker_scheduler_run_result() -> dict:
    return {
        "checked_profiles": 1,
        "heartbeat_results": [worker_profile_heartbeat_result()],
        "total_processed_tasks": 0,
        "idle": True,
        "summary": "Browser fixture background check finished.",
    }


def provider_readiness(configured: bool = False) -> dict:
    if configured:
        return {
            "default_realtime_provider": "gemma4_realtime",
            "selected_web_search_provider": "tavily",
            "providers": [],
            "ready_provider_ids": [],
            "missing_provider_ids": [],
            "tool_boundary_provider_ids": [],
            "missing_required_env": [],
            "provider_backed_smoke_ready": False,
            "smoke_test_plan": [],
            "demo_walkthrough": [],
            "summary": "Browser fixture provider readiness.",
        }
    return {
        "default_realtime_provider": "gemma4_realtime",
        "selected_web_search_provider": "tavily",
        "providers": [
            {
                "provider_id": "gemma4-primary",
                "provider_type": "gemma4_hf_endpoint",
                "display_name": "Gemma 4 primary",
                "status": "missing_config",
                "selected": False,
                "required_env": ["GEMMA4_MULTIMODAL_ENDPOINT_URL"],
                "configured_env": [],
                "missing_env": ["GEMMA4_MULTIMODAL_ENDPOINT_URL"],
                "model_ids": ["google/gemma-4-E4B-it"],
                "endpoint_configured": False,
                "capabilities": ["text", "audio_input"],
                "boundary": "Fixture Gemma provider boundary.",
                "notes": "Fixture Gemma provider notes.",
                "documentation_url": None,
                "next_actions": ["Save the Gemma endpoint."],
                "secret_files": [],
            },
            {
                "provider_id": "gemma4-realtime",
                "provider_type": "realtime_audio",
                "display_name": "Gemma/Kokoro realtime",
                "status": "missing_config",
                "selected": True,
                "required_env": [
                    "GEMMA4_REALTIME_LIVEKIT_URL",
                    "LIVEKIT_API_KEY",
                    "LIVEKIT_API_SECRET",
                    "KOKORO_TTS_ENDPOINT_URL",
                ],
                "configured_env": [],
                "missing_env": [
                    "GEMMA4_REALTIME_LIVEKIT_URL",
                    "LIVEKIT_API_KEY",
                    "LIVEKIT_API_SECRET",
                    "KOKORO_TTS_ENDPOINT_URL",
                ],
                "model_ids": ["google/gemma-4-E4B-it", "hexgrad/Kokoro-82M"],
                "endpoint_configured": False,
                "capabilities": ["realtime_audio"],
                "boundary": "Fixture realtime provider boundary.",
                "notes": "Fixture realtime provider notes.",
                "documentation_url": None,
                "next_actions": ["Use local LiveKit dev defaults."],
                "secret_files": [
                    {
                        "env_name": "LIVEKIT_API_KEY",
                        "file_env_name": "LIVEKIT_API_KEY_FILE",
                        "status": "missing",
                        "configured": False,
                        "path": ".secrets/livekit_api_key",
                        "detail": "LIVEKIT_API_KEY_FILE points to a missing file.",
                    }
                ],
            },
            {
                "provider_id": "tavily-search",
                "provider_type": "web_search",
                "display_name": "Tavily search",
                "status": "ready",
                "selected": True,
                "required_env": [],
                "configured_env": [],
                "missing_env": [],
                "model_ids": [],
                "endpoint_configured": True,
                "capabilities": ["web_search"],
                "boundary": "Fixture search provider boundary.",
                "notes": "Fixture search provider notes.",
                "documentation_url": None,
                "next_actions": [],
                "secret_files": [],
            },
            {
                "provider_id": "deterministic-reranker",
                "provider_type": "reranker",
                "display_name": "Deterministic reranker",
                "status": "ready",
                "selected": True,
                "required_env": [],
                "configured_env": [],
                "missing_env": [],
                "model_ids": [],
                "endpoint_configured": True,
                "capabilities": ["reranker"],
                "boundary": "Fixture reranker boundary.",
                "notes": "Fixture reranker notes.",
                "documentation_url": None,
                "next_actions": [],
                "secret_files": [],
            },
        ],
        "ready_provider_ids": [],
        "missing_provider_ids": [],
        "tool_boundary_provider_ids": [],
        "missing_required_env": [],
        "provider_backed_smoke_ready": False,
        "smoke_test_plan": [],
        "demo_walkthrough": [],
        "summary": "Browser fixture provider readiness.",
    }


def local_livekit_dev_config_result() -> dict:
    return {
        "status": "configured",
        "configured": True,
        "configured_env": [
            "GEMMA4_REALTIME_LIVEKIT_URL",
            "LIVEKIT_API_KEY",
            "LIVEKIT_API_SECRET",
        ],
        "config_file_env_name": "LOCAL_PROVIDER_CONFIG_FILE",
        "secret_file_env_names": ["LIVEKIT_API_KEY_FILE", "LIVEKIT_API_SECRET_FILE"],
        "paths": {},
        "detail": "Browser fixture local LiveKit dev defaults configured.",
    }


def local_provider_config_result(env_name: str) -> dict:
    return {
        "env_name": env_name,
        "status": "configured",
        "configured": True,
        "config_file_env_name": "LOCAL_PROVIDER_CONFIG_FILE",
        "path": "/fixture/local-provider.env",
        "detail": "Browser fixture provider endpoint configured.",
    }


def local_secret_file_result() -> dict:
    return {
        "env_name": "LIVEKIT_API_KEY",
        "file_env_name": "LIVEKIT_API_KEY_FILE",
        "status": "configured",
        "configured": True,
        "path": "/fixture/livekit_api_key",
        "detail": "Browser fixture secret file configured.",
    }


def voice_runtime_readiness() -> dict:
    return {
        "status": "blocked",
        "selected_provider": "gemma4_realtime",
        "transport_framework": "livekit",
        "audio_input_model": "google/gemma-4-E4B-it",
        "reasoning_model": "google/gemma-4-E4B-it",
        "audio_output_model": "hexgrad/Kokoro-82M",
        "preflight_edge": False,
        "preflight_agent": False,
        "preflight_gemma": False,
        "preflight_tts": False,
        "checks": [],
        "blockers": ["fixture_missing_live_provider"],
        "next_actions": ["Use fixture UI only."],
        "summary": "Browser fixture voice readiness is blocked.",
    }


def ready_voice_runtime_readiness() -> dict:
    payload = voice_runtime_readiness()
    payload.update(
        {
            "status": "ready",
            "preflight_edge": True,
            "preflight_agent": True,
            "preflight_livekit": True,
            "preflight_gemma": True,
            "preflight_tts": True,
            "blockers": [],
            "next_actions": [],
            "summary": "Browser fixture runtime preflight complete.",
        }
    )
    return payload


def voice_process_status(running: bool = True) -> dict:
    return {
        "enabled": True,
        "status": "running" if running else "stopped",
        "running": running,
        "pid": None,
        "returncode": None,
        "last_error": None,
        "started_at": None,
        "stopped_at": None if running else "2026-05-19T18:30:00Z",
        "command": [],
        "log_tail": [],
        "next_actions": [],
        "summary": "Browser fixture process running." if running else "Browser fixture process stopped.",
    }


def voice_agent_presence() -> dict:
    return {
        "run_id": RUN_ID,
        "realtime_session_id": None,
        "status": "missing",
        "observed": False,
        "stale": True,
        "stale_after_seconds": 60,
        "event_age_seconds": None,
        "latest_event_id": None,
        "latest_event_type": None,
        "latest_event_created_at": None,
        "provider": None,
        "provider_session_id": None,
        "transport_framework": None,
        "room_name": None,
        "agent_participant_identity": None,
        "livekit_sender_identity": None,
        "probe_id": None,
        "audio_input_model": None,
        "reasoning_model": None,
        "audio_output_model": None,
        "evidence": [],
        "missing_evidence": ["fixture_no_voice_session"],
        "next_actions": ["Create a fixture voice session first."],
        "summary": "Browser fixture has no voice-agent presence.",
    }


def local_livekit_status(running: bool = True) -> dict:
    payload = voice_process_status(running=running)
    payload["mode"] = "native"
    return payload


def conversation_result() -> dict:
    return {
        "run_id": RUN_ID,
        "turn_id": TURN_ID,
        "response_turn_id": None,
        "routed_intent": "create_content",
        "response_text": "",
        "created_run": True,
        "task_message_ids": [],
        "artifact_ids": [ARTIFACT_ID],
        "target_artifact_ids": [],
        "feedback_id": None,
        "feedback_gate_opened": False,
        "summary": "Browser fixture turn routed.",
    }


def feedback_item(status: str = "open") -> dict:
    return {
        "feedback_id": FEEDBACK_ID,
        "run_id": RUN_ID,
        "author": "editor-in-chief",
        "target_agent_id": "content-strategist-agent",
        "feedback_text": "Confirm the browser proof keeps feedback gates explicit.",
        "status": status,
        "metadata": {"fixture": "browser_single_flight"},
        "resolution_notes": "Resolved from the creator app after review." if status == "resolved" else None,
        "resolved_by": "user" if status == "resolved" else None,
        "resolved_at": NOW if status == "resolved" else None,
        "created_at": NOW,
        "updated_at": NOW,
    }


def feedback_resolution_result() -> dict:
    return {
        "feedback": feedback_item("resolved"),
        "run_status": "running",
        "open_feedback_count": 0,
        "resolution_ledger": None,
        "event_id": 7101,
        "summary": "Browser fixture feedback item resolved.",
    }


def work_plan_result() -> dict:
    return {
        "run_id": RUN_ID,
        "plan_items": [
            {
                "item_id": WORK_PLAN_ITEM_ID,
                "item_type": "browser_single_flight",
                "title": "Keep browser duplicate-submit coverage green",
                "owner_agent_id": "frontend-experience-engineer",
                "status": "pending",
                "priority": "medium",
                "blocking": False,
                "source_message_id": None,
                "source_feedback_id": None,
                "recommended_action": "Keep the browser single-flight smoke passing.",
                "reason": "Rapid duplicate submits should not create duplicate actions.",
                "metadata": {},
                "dependency_blocked_tasks": 0,
                "idle": False,
                "summary": "Browser single-flight coverage item.",
            }
        ],
        "recommended_agent_ids": ["frontend-experience-engineer"],
        "open_feedback_count": 0,
        "routed_feedback_count": 0,
        "pending_task_count": 1,
        "blocked_item_count": 0,
        "created_task_message_ids": [],
        "skipped_duplicate_task_count": 0,
        "artifact_id": None,
        "event_id": None,
        "refresh_reason": "creator_app_next_actions",
        "summary": "Built browser fixture next action.",
    }


def materialized_work_plan_result() -> dict:
    payload = work_plan_result()
    payload.update(
        {
            "created_task_message_ids": [RUN_PLAN_MESSAGE_ID],
            "event_id": 3001,
            "refresh_reason": "creator_app_run_plan",
            "summary": "Materialized browser fixture next step.",
        }
    )
    return payload


def post_run_work_plan_result() -> dict:
    payload = work_plan_result()
    payload.update(
        {
            "plan_items": [],
            "recommended_agent_ids": [],
            "pending_task_count": 0,
            "blocked_item_count": 0,
            "created_task_message_ids": [],
            "event_id": 3002,
            "refresh_reason": "creator_app_after_run_plan",
            "summary": "Refreshed browser fixture next actions after running plan.",
        }
    )
    return payload


def agent_message_create_result() -> dict:
    return {
        "message_id": AGENT_MESSAGE_ID,
        "run_id": RUN_ID,
        "accepted": True,
        "recipient_agent_id": "web-research-agent",
        "event_id": 2001,
        "status": "accepted",
    }


def source_refresh_cycle_result() -> dict:
    return {
        "run_id": RUN_ID,
        "agent_ids": ["web-research-agent", "claim-verification-agent"],
        "rounds_completed": 1,
        "worker_results": [
            {
                "run_id": RUN_ID,
                "agent_id": "web-research-agent",
                "processed_tasks": [
                    {
                        "message_id": AGENT_MESSAGE_ID,
                        "task_type": "research_topic",
                        "status": "completed",
                        "generation_mode": "web_search_provider_blocked",
                        "summary": "Provider-backed web research is blocked in the browser fixture.",
                    },
                    {
                        "message_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                        "task_type": "verify_source_refresh_claims",
                        "status": "completed",
                        "generation_mode": "claim_verification_worker",
                        "summary": "Claim verification completed after fixture source refresh.",
                    },
                ],
                "recovered_stale_tasks": 0,
                "blocked_exhausted_tasks": 0,
                "dependency_blocked_tasks": 0,
                "idle": False,
                "summary": "Web Research Agent processed 2 fixture task(s).",
            }
        ],
        "total_processed_tasks": 2,
        "idle": False,
        "summary": "Worker cycle ran fixture source refresh.",
    }


def run_plan_cycle_result() -> dict:
    return {
        "run_id": RUN_ID,
        "agent_ids": ["frontend-experience-engineer"],
        "rounds_completed": 1,
        "worker_results": [
            {
                "run_id": RUN_ID,
                "agent_id": "frontend-experience-engineer",
                "processed_tasks": [
                    {
                        "message_id": RUN_PLAN_MESSAGE_ID,
                        "task_type": "browser_single_flight",
                        "status": "completed",
                        "generation_mode": "local_fixture",
                        "summary": "Frontend Experience Engineer completed the browser fixture next step.",
                    }
                ],
                "recovered_stale_tasks": 0,
                "blocked_exhausted_tasks": 0,
                "dependency_blocked_tasks": 0,
                "idle": False,
                "summary": "Frontend Experience Engineer processed 1 fixture task.",
            }
        ],
        "total_processed_tasks": 1,
        "idle": False,
        "summary": "Worker cycle ran fixture plan execution.",
    }


def voice_followup_cycle_result() -> dict:
    return {
        "run_id": RUN_ID,
        "agent_ids": [],
        "rounds_completed": 1,
        "worker_results": [
            {
                "run_id": RUN_ID,
                "agent_id": "realtime-conversation-host",
                "processed_tasks": [
                    {
                        "message_id": "99999999-9999-4999-8999-999999999999",
                        "task_type": "summarize_realtime_turn_context",
                        "status": "completed",
                        "generation_mode": "local_voice_followup_fixture",
                        "summary": "Realtime Conversation Host continued the rehearsal follow-up.",
                    }
                ],
                "recovered_stale_tasks": 0,
                "blocked_exhausted_tasks": 0,
                "dependency_blocked_tasks": 0,
                "idle": False,
                "summary": "Realtime Conversation Host processed 1 fixture task.",
            }
        ],
        "total_processed_tasks": 1,
        "idle": False,
        "summary": "Worker cycle ran voice follow-up fixture.",
    }


def manual_continue_cycle_result() -> dict:
    return {
        "run_id": RUN_ID,
        "agent_ids": [],
        "rounds_completed": 1,
        "worker_results": [
            {
                "run_id": RUN_ID,
                "agent_id": "content-strategist-agent",
                "processed_tasks": [
                    {
                        "message_id": "99999999-9999-4999-8999-999999999994",
                        "task_type": "continue_specialist_loop",
                        "status": "completed",
                        "generation_mode": "local_manual_continue_fixture",
                        "summary": "Content Strategist continued the manual specialist loop.",
                    }
                ],
                "recovered_stale_tasks": 0,
                "blocked_exhausted_tasks": 0,
                "dependency_blocked_tasks": 0,
                "idle": False,
                "summary": "Content Strategist processed 1 manual continuation task.",
            }
        ],
        "total_processed_tasks": 1,
        "idle": False,
        "summary": "Worker cycle ran manual specialist continuation fixture.",
    }


def retry_authorized_result() -> dict:
    return {
        "message": {
            "message_id": RETRY_MESSAGE_ID,
            "run_id": RUN_ID,
            "sender_agent_id": "editor-in-chief",
            "recipient_agent_id": "script-doctor-agent",
            "task_type": "revise_script",
            "payload": {
                "target_artifact_ids": [ARTIFACT_ID],
                "summary": "Retry fixture task should run once.",
            },
            "depends_on_message_ids": [],
            "requires_human_feedback": False,
            "status": "accepted",
            "claimed_by_agent_id": None,
            "attempt_count": 0,
            "max_attempts": 3,
            "result": {},
            "error": None,
            "created_at": NOW,
            "updated_at": NOW,
        },
        "event_id": 4001,
        "summary": "Browser fixture retry authorized.",
    }


def retry_cycle_result() -> dict:
    return {
        "run_id": RUN_ID,
        "agent_ids": ["script-doctor-agent"],
        "rounds_completed": 1,
        "worker_results": [
            {
                "run_id": RUN_ID,
                "agent_id": "script-doctor-agent",
                "processed_tasks": [
                    {
                        "message_id": RETRY_MESSAGE_ID,
                        "task_type": "revise_script",
                        "status": "completed",
                        "generation_mode": "local_retry_fixture",
                        "summary": "Script Doctor completed the targeted retry fixture.",
                    }
                ],
                "recovered_stale_tasks": 0,
                "blocked_exhausted_tasks": 0,
                "dependency_blocked_tasks": 0,
                "idle": False,
                "summary": "Script Doctor processed 1 targeted retry task.",
            }
        ],
        "total_processed_tasks": 1,
        "idle": False,
        "summary": "Worker cycle ran targeted retry fixture.",
    }


def publish_readiness_result() -> dict:
    return {
        "run_id": RUN_ID,
        "status": "needs_review",
        "ready": False,
        "artifact_ids": [ARTIFACT_ID],
        "source_count": 1,
        "claim_count": 1,
        "audit_count": 1,
        "open_feedback_count": 0,
        "blocking_issues": ["publish_channel_policy_review_required"],
        "recommended_next_actions": [
            "Confirm platform policy, account permissions, and human approval before live publication."
        ],
        "publish_channel_checks": [
            {
                "platform": "linkedin",
                "credential_envs": ["LINKEDIN_ACCESS_TOKEN"],
                "credential_status": "configured",
                "policy_status": "needs_review",
                "blocking_issues": ["publish_channel_policy_review_required"],
                "recommended_next_actions": [
                    "Confirm current linkedin platform policy and account permissions before live publication."
                ],
            }
        ],
        "feedback_gate_opened": False,
        "feedback_id": None,
        "summary": "Browser fixture publish readiness needs policy review.",
    }


def growth_package_result() -> dict:
    return {
        "run_id": RUN_ID,
        "source_artifact_ids": [ARTIFACT_ID],
        "distribution_artifact_id": "55555555-5555-4555-8555-555555555556",
        "platforms": [
            "instagram_post",
            "instagram_reel",
            "linkedin",
            "x_thread",
            "substack",
        ],
        "influencer_strategy_artifact_id": "55555555-5555-4555-8555-555555555557",
        "outreach_strategy_artifact_id": "55555555-5555-4555-8555-555555555558",
        "strategy_artifact_ids": [
            "55555555-5555-4555-8555-555555555557",
            "55555555-5555-4555-8555-555555555558",
        ],
        "agent_message_ids": [
            "99999999-9999-4999-8999-999999999996",
            "99999999-9999-4999-8999-999999999995",
        ],
        "event_id": 6101,
        "summary": "Browser fixture growth package built.",
    }


def media_plan_result() -> dict:
    return {
        "run_id": RUN_ID,
        "source_artifact_ids": [ARTIFACT_ID],
        "media_artifact_ids": [
            "55555555-5555-4555-8555-555555555559",
            "55555555-5555-4555-8555-555555555560",
            "55555555-5555-4555-8555-555555555561",
        ],
        "image_artifact_id": "55555555-5555-4555-8555-555555555559",
        "audio_artifact_id": "55555555-5555-4555-8555-555555555560",
        "video_artifact_id": "55555555-5555-4555-8555-555555555561",
        "event_id": 6201,
        "summary": "Browser fixture media plan built.",
    }


def revision_result() -> dict:
    return {
        "run_id": RUN_ID,
        "feedback_id": "77777777-7777-4777-8777-777777777777",
        "task_message_ids": [],
        "revised_artifact_ids": [],
        "feedback_gate_opened": False,
        "summary": "Browser fixture revision queued.",
    }


def transcript_rehearsal_session_result() -> dict:
    return {
        "run_id": RUN_ID,
        "realtime_session_id": "77777777-7777-4777-8777-777777777778",
        "provider": "local_realtime_rehearsal",
        "session_id": "browser-transcript-rehearsal",
        "client_secret": None,
        "websocket_url": None,
        "transport": {
            "framework": "local_rehearsal",
            "url": None,
            "room_name": None,
            "participant_identity": "browser-fixture-creator",
            "agent_identity": None,
            "token": None,
            "has_token": False,
            "token_persisted": False,
            "expires_at_unix": None,
            "metadata": {"fixture": "browser_single_flight"},
        },
        "expires_at_unix": None,
        "event_id": 7001,
        "metadata": {
            "frontend": "next-app",
            "selected_voice_provider": "local_rehearsal",
        },
    }


def provider_live_session_result() -> dict:
    return {
        "run_id": RUN_ID,
        "realtime_session_id": "77777777-7777-4777-8777-777777777779",
        "provider": "gemma4_realtime",
        "session_id": "browser-provider-livekit",
        "client_secret": None,
        "websocket_url": None,
        "transport": {
            "framework": "livekit",
            "url": "wss://livekit.fixture.invalid",
            "room_name": "browser-fixture-room",
            "participant_identity": "browser-fixture-creator",
            "agent_identity": "gemma-kokoro-fixture-agent",
            "token": None,
            "has_token": False,
            "token_persisted": False,
            "expires_at_unix": None,
            "metadata": {"fixture": "browser_single_flight"},
        },
        "expires_at_unix": None,
        "event_id": 7003,
        "metadata": {
            "frontend": "next-app",
            "selected_voice_provider": "gemma4_realtime",
        },
    }


def transcript_rehearsal_turn_result() -> dict:
    return {
        "realtime_session": {
            "realtime_session_id": "77777777-7777-4777-8777-777777777778",
            "run_id": RUN_ID,
            "provider": "local_realtime_rehearsal",
        },
        "conversation_turn": None,
        "routed_result": None,
        "summary": "Browser fixture transcript rehearsal turn routed.",
        "event_id": 7002,
        "brief_task_message_id": "99999999-9999-4999-8999-999999999999",
        "spoken_response": None,
    }


def voice_provider_smoke_result() -> dict:
    return {
        "run_id": RUN_ID,
        "status": "blocked",
        "execute_live_calls": False,
        "provider_readiness": provider_readiness(),
        "step_count": 1,
        "passed_count": 0,
        "blocked_count": 1,
        "failed_count": 0,
        "not_run_count": 0,
        "tool_boundary_count": 0,
        "source_ids": [],
        "realtime_session_ids": [],
        "provider_configuration_followup_message_ids": [],
        "steps": [
            {
                "step_id": "selected-realtime-smoke",
                "provider_id": "gemma4-realtime",
                "provider_type": "realtime_audio",
                "title": "Selected Gemma/Kokoro realtime smoke",
                "status": "blocked",
                "required": True,
                "live_call": False,
                "smoke_proof_status": "not_provider_backed",
                "evidence": [],
                "blockers": ["fixture_live_provider_missing"],
                "next_actions": ["Configure provider endpoints before live smoke."],
                "source_ids": [],
                "realtime_session_ids": [],
                "event_ids": [],
                "details": {},
            }
        ],
        "ledger_artifact_id": None,
        "event_id": 6001,
        "summary": "Browser fixture provider smoke is blocked.",
    }


def voice_timing_ledger_result() -> dict:
    return {
        "run_id": RUN_ID,
        "status": "needs_more_evidence",
        "session_count": 0,
        "event_count": 0,
        "measured_stage_count": 0,
        "missing_stage_count": 2,
        "stages": [
            {
                "stage_id": "media_bridge_ready",
                "title": "LiveKit media bridge is ready",
                "status": "missing",
                "latency_ms": None,
                "evidence": [],
                "missing_evidence": ["No fixture media bridge event was recorded."],
                "event_ids": [],
            },
            {
                "stage_id": "first_audio_out",
                "title": "First Kokoro audio reaches LiveKit output",
                "status": "missing",
                "latency_ms": None,
                "evidence": [],
                "missing_evidence": ["No fixture assistant audio event was recorded."],
                "event_ids": [],
            },
        ],
        "turns": [],
        "recommended_next_actions": ["Join a live voice session before timing proof."],
        "ledger_artifact_id": None,
        "event_id": 6002,
        "summary": "Browser fixture voice timing ledger needs more evidence.",
    }


async def fulfill_json(route, payload: dict, status: int = 200, delay: float = 0.0) -> None:
    if delay:
        await asyncio.sleep(delay)
    await route.fulfill(
        status=status,
        content_type="application/json",
        body=json.dumps(payload),
    )


def request_json(request) -> dict:
    try:
        return json.loads(request.post_data or "{}")
    except json.JSONDecodeError:
        return {}


async def run_browser_assertions(base_url: str) -> None:
    counts = defaultdict(int)
    seen = {
        "conversation_started": asyncio.Event(),
        "conversation": asyncio.Event(),
        "work_plan_request_started": asyncio.Event(),
        "work_plan": asyncio.Event(),
        "run_plan_materialize": asyncio.Event(),
        "run_plan_cycle_started": asyncio.Event(),
        "run_plan_cycle": asyncio.Event(),
        "run_plan_refresh": asyncio.Event(),
        "manual_continue_cycle_started": asyncio.Event(),
        "manual_continue_cycle": asyncio.Event(),
        "voice_followup_cycle_started": asyncio.Event(),
        "voice_followup_cycle": asyncio.Event(),
        "source_refresh_message": asyncio.Event(),
        "source_refresh_cycle_started": asyncio.Event(),
        "source_refresh_cycle": asyncio.Event(),
        "manual_refresh_context": asyncio.Event(),
        "publish": asyncio.Event(),
        "revision_started": asyncio.Event(),
        "revision": asyncio.Event(),
        "autopilot_launch_started": asyncio.Event(),
        "autopilot_launch": asyncio.Event(),
        "autopilot_heartbeat_started": asyncio.Event(),
        "autopilot_heartbeat": asyncio.Event(),
        "autopilot_scheduler_started": asyncio.Event(),
        "autopilot_scheduler": asyncio.Event(),
        "autopilot_stop_started": asyncio.Event(),
        "autopilot_stop": asyncio.Event(),
        "runner_start": asyncio.Event(),
        "runner_stop_started": asyncio.Event(),
        "runner_stop": asyncio.Event(),
        "retry_authorize": asyncio.Event(),
        "retry_cycle_started": asyncio.Event(),
        "retry_cycle": asyncio.Event(),
        "feedback_resolve_started": asyncio.Event(),
        "feedback_resolve": asyncio.Event(),
        "voice_run_create": asyncio.Event(),
        "voice_run_context_refresh": asyncio.Event(),
        "runtime_preflight_started": asyncio.Event(),
        "runtime_preflight": asyncio.Event(),
        "live_proof_provider_refresh_started": asyncio.Event(),
        "live_proof_provider_refresh": asyncio.Event(),
        "local_livekit_dev_config_started": asyncio.Event(),
        "local_livekit_dev_config": asyncio.Event(),
        "local_secret_file_save_started": asyncio.Event(),
        "local_secret_file_save": asyncio.Event(),
        "local_provider_config_save_started": asyncio.Event(),
        "local_provider_config_save": asyncio.Event(),
        "provider_panel_refresh_started": asyncio.Event(),
        "provider_panel_refresh": asyncio.Event(),
        "provider_resolve_refresh_started": asyncio.Event(),
        "provider_resolve_refresh": asyncio.Event(),
        "provider_resolve_proof": asyncio.Event(),
        "provider_live_join_request_started": asyncio.Event(),
        "provider_live_join_start": asyncio.Event(),
        "provider_join_end_session": asyncio.Event(),
        "transcript_rehearsal_stop_started": asyncio.Event(),
        "transcript_rehearsal_stop": asyncio.Event(),
        "setup_check_request_started": asyncio.Event(),
        "setup_check_proof": asyncio.Event(),
        "voice_provider_smoke_request_started": asyncio.Event(),
        "voice_provider_smoke": asyncio.Event(),
        "voice_timing_ledger_request_started": asyncio.Event(),
        "voice_timing_ledger": asyncio.Event(),
        "local_livekit_start_started": asyncio.Event(),
        "local_livekit_start": asyncio.Event(),
        "local_livekit_stop_started": asyncio.Event(),
        "local_livekit_stop": asyncio.Event(),
        "voice_agent_start_started": asyncio.Event(),
        "voice_agent_start": asyncio.Event(),
        "voice_agent_stop_started": asyncio.Event(),
        "voice_agent_stop": asyncio.Event(),
        "growth_package_request_started": asyncio.Event(),
        "growth_package": asyncio.Event(),
        "media_plan_request_started": asyncio.Event(),
        "media_plan": asyncio.Event(),
        "publish_request_started": asyncio.Event(),
        "transcript_rehearsal_start": asyncio.Event(),
        "transcript_rehearsal_turn_started": asyncio.Event(),
        "transcript_rehearsal_turn": asyncio.Event(),
    }
    unexpected_api_requests: list[str] = []
    page_errors: list[str] = []
    retry_phase_worker_payloads: list[dict] = []
    voice_run_create_payloads: list[dict] = []
    conversation_payloads: list[dict] = []
    runtime_preflight_queries: list[dict[str, list[str]]] = []
    provider_live_join_payloads: list[dict] = []
    provider_join_end_payloads: list[dict] = []
    transcript_rehearsal_stop_payloads: list[dict] = []
    setup_check_proof_payloads: list[dict] = []
    voice_provider_smoke_payloads: list[dict] = []
    voice_timing_ledger_payloads: list[dict] = []
    local_secret_file_payloads: list[dict] = []
    local_provider_config_payloads: list[dict] = []
    growth_package_payloads: list[dict] = []
    media_plan_payloads: list[dict] = []
    transcript_rehearsal_payloads: list[dict] = []
    transcript_rehearsal_turn_payloads: list[dict] = []
    autopilot_scheduler_payloads: list[dict] = []
    feedback_resolve_payloads: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        await page.add_init_script("window.localStorage.clear();")
        fixture_state = {
            "autopilot_started": False,
            "runner_running": False,
            "retry_phase": False,
            "manual_continue_phase": False,
            "manual_refresh_phase": False,
            "voice_run_create_pending": False,
            "setup_check_phase": False,
            "live_proof_provider_refresh_phase": False,
            "provider_panel_refresh_phase": False,
            "provider_resolve_phase": False,
            "local_livekit_running": True,
            "voice_agent_running": True,
            "local_livekit_configured": False,
        }

        async def handle_api(route):
            request = route.request
            path = urlparse(request.url).path
            method = request.method.upper()
            if path == "/api/worker-scheduler-process" and method == "GET":
                await fulfill_json(
                    route,
                    worker_scheduler_running_status()
                    if fixture_state["runner_running"]
                    else worker_scheduler_status(),
                )
            elif path == "/api/worker-scheduler-process/start" and method == "POST":
                fixture_state["runner_running"] = True
                seen["runner_start"].set()
                await fulfill_json(route, worker_scheduler_running_status(), delay=0.5)
            elif path == "/api/worker-scheduler-process/stop" and method == "POST":
                counts["runner_stop"] += 1
                fixture_state["runner_running"] = False
                seen["runner_stop_started"].set()
                await fulfill_json(route, worker_scheduler_stopped_status(), delay=0.5)
                seen["runner_stop"].set()
            elif path == "/api/provider-readiness" and method == "GET":
                if fixture_state["setup_check_phase"]:
                    counts["setup_check_provider_readiness"] += 1
                if fixture_state["provider_resolve_phase"]:
                    counts["provider_resolve_refresh"] += 1
                    seen["provider_resolve_refresh_started"].set()
                    await fulfill_json(
                        route,
                        provider_readiness(fixture_state["local_livekit_configured"]),
                        delay=0.5,
                    )
                    seen["provider_resolve_refresh"].set()
                elif fixture_state["live_proof_provider_refresh_phase"]:
                    counts["live_proof_provider_refresh"] += 1
                    seen["live_proof_provider_refresh_started"].set()
                    await fulfill_json(
                        route,
                        provider_readiness(fixture_state["local_livekit_configured"]),
                        delay=0.5,
                    )
                    seen["live_proof_provider_refresh"].set()
                elif fixture_state["provider_panel_refresh_phase"]:
                    counts["provider_panel_refresh"] += 1
                    seen["provider_panel_refresh_started"].set()
                    await fulfill_json(
                        route,
                        provider_readiness(fixture_state["local_livekit_configured"]),
                        delay=0.5,
                    )
                    seen["provider_panel_refresh"].set()
                else:
                    await fulfill_json(route, provider_readiness(fixture_state["local_livekit_configured"]))
            elif path == "/api/local-livekit-dev-config" and method == "POST":
                counts["local_livekit_dev_config"] += 1
                seen["local_livekit_dev_config_started"].set()
                fixture_state["local_livekit_configured"] = True
                await fulfill_json(route, local_livekit_dev_config_result(), delay=0.5)
                seen["local_livekit_dev_config"].set()
            elif path == "/api/local-secret-files" and method == "POST":
                counts["local_secret_file_save"] += 1
                local_secret_file_payloads.append(request_json(request))
                seen["local_secret_file_save_started"].set()
                await fulfill_json(route, local_secret_file_result(), delay=0.5)
                seen["local_secret_file_save"].set()
            elif path == "/api/local-provider-config" and method == "POST":
                counts["local_provider_config_save"] += 1
                payload = request_json(request)
                local_provider_config_payloads.append(payload)
                seen["local_provider_config_save_started"].set()
                await fulfill_json(
                    route,
                    local_provider_config_result(str(payload.get("env_name", ""))),
                    delay=0.5,
                )
                seen["local_provider_config_save"].set()
            elif path == "/api/voice-runtime-readiness" and method == "GET":
                query = parse_qs(urlparse(request.url).query)
                preflight_keys = {
                    "preflight_edge",
                    "preflight_agent",
                    "preflight_livekit",
                    "preflight_gemma",
                    "preflight_tts",
                }
                is_full_runtime_preflight = all(query.get(key) == ["true"] for key in preflight_keys)
                payload = voice_runtime_readiness()
                if is_full_runtime_preflight:
                    counts["runtime_preflight"] += 1
                    seen["runtime_preflight_started"].set()
                    if fixture_state["setup_check_phase"]:
                        counts["setup_check_runtime_preflight"] += 1
                        seen["setup_check_request_started"].set()
                    runtime_preflight_queries.append(query)
                    payload = ready_voice_runtime_readiness()
                    await fulfill_json(route, payload, delay=0.5)
                    seen["runtime_preflight"].set()
                else:
                    if fixture_state["local_livekit_configured"]:
                        payload = ready_voice_runtime_readiness()
                    await fulfill_json(route, payload)
            elif path == "/api/voice-agent-process" and method == "GET":
                if fixture_state["setup_check_phase"]:
                    counts["setup_check_voice_process"] += 1
                await fulfill_json(route, voice_process_status(running=fixture_state["voice_agent_running"]))
            elif path == "/api/voice-agent-process/start" and method == "POST":
                counts["voice_agent_start"] += 1
                fixture_state["voice_agent_running"] = True
                seen["voice_agent_start_started"].set()
                await fulfill_json(route, voice_process_status(running=True), delay=0.5)
                seen["voice_agent_start"].set()
            elif path == "/api/voice-agent-process/stop" and method == "POST":
                counts["voice_agent_stop"] += 1
                fixture_state["voice_agent_running"] = False
                seen["voice_agent_stop_started"].set()
                await fulfill_json(route, voice_process_status(running=False), delay=0.5)
                seen["voice_agent_stop"].set()
            elif path == "/api/local-livekit-process" and method == "GET":
                if fixture_state["setup_check_phase"]:
                    counts["setup_check_livekit_process"] += 1
                await fulfill_json(route, local_livekit_status(running=fixture_state["local_livekit_running"]))
            elif path == "/api/local-livekit-process/start" and method == "POST":
                counts["local_livekit_start"] += 1
                fixture_state["local_livekit_running"] = True
                seen["local_livekit_start_started"].set()
                await fulfill_json(route, local_livekit_status(running=True), delay=0.5)
                seen["local_livekit_start"].set()
            elif path == "/api/local-livekit-process/stop" and method == "POST":
                counts["local_livekit_stop"] += 1
                fixture_state["local_livekit_running"] = False
                seen["local_livekit_stop_started"].set()
                await fulfill_json(route, local_livekit_status(running=False), delay=0.5)
                seen["local_livekit_stop"].set()
            elif path == f"/api/runs/{RUN_ID}/voice-agent-presence" and method == "GET":
                if fixture_state["setup_check_phase"]:
                    counts["setup_check_presence"] += 1
                await fulfill_json(route, voice_agent_presence())
            elif path == "/api/runs" and method == "POST":
                counts["voice_run_create"] += 1
                voice_run_create_payloads.append(request_json(request))
                fixture_state["voice_run_create_pending"] = True
                await fulfill_json(route, run_state(), delay=0.5)
                seen["voice_run_create"].set()
            elif path == "/api/conversation/turns" and method == "POST":
                counts["conversation"] += 1
                conversation_payloads.append(request_json(request))
                seen["conversation_started"].set()
                await fulfill_json(route, conversation_result(), delay=0.5)
                seen["conversation"].set()
            elif path == f"/api/runs/{RUN_ID}/context-packet" and method == "POST":
                if fixture_state["voice_run_create_pending"]:
                    counts["voice_run_context_refresh"] += 1
                    await fulfill_json(route, run_context())
                    fixture_state["voice_run_create_pending"] = False
                    seen["voice_run_context_refresh"].set()
                elif fixture_state["manual_refresh_phase"]:
                    counts["manual_refresh_context"] += 1
                    await fulfill_json(route, run_context(), delay=0.5)
                    seen["manual_refresh_context"].set()
                else:
                    await fulfill_json(route, run_context())
            elif path == f"/api/runs/{RUN_ID}/worker-profiles" and method == "GET":
                await fulfill_json(
                    route,
                    {
                        "profiles": [active_worker_profile()]
                        if fixture_state["autopilot_started"]
                        else []
                    },
                )
            elif path == f"/api/runs/{RUN_ID}/autopilot-launch" and method == "POST":
                counts["autopilot_launch"] += 1
                fixture_state["autopilot_started"] = True
                seen["autopilot_launch_started"].set()
                await fulfill_json(route, autopilot_launch_result(), delay=0.5)
                seen["autopilot_launch"].set()
            elif path == f"/api/worker-profiles/{PROFILE_ID}/stop" and method == "POST":
                counts["autopilot_stop"] += 1
                fixture_state["autopilot_started"] = False
                seen["autopilot_stop_started"].set()
                await fulfill_json(route, stopped_worker_profile(), delay=0.5)
                seen["autopilot_stop"].set()
            elif path == f"/api/worker-profiles/{PROFILE_ID}/heartbeat" and method == "POST":
                counts["autopilot_heartbeat"] += 1
                seen["autopilot_heartbeat_started"].set()
                await fulfill_json(route, worker_profile_heartbeat_result(), delay=0.5)
                seen["autopilot_heartbeat"].set()
            elif path == "/api/worker-profiles/scheduler/run" and method == "POST":
                counts["autopilot_scheduler"] += 1
                autopilot_scheduler_payloads.append(request_json(request))
                seen["autopilot_scheduler_started"].set()
                await fulfill_json(route, worker_scheduler_run_result(), delay=0.5)
                seen["autopilot_scheduler"].set()
            elif path == f"/api/runs/{RUN_ID}/events/stream" and method == "GET":
                await route.fulfill(
                    status=200,
                    headers={"Content-Type": "text/event-stream"},
                    body="",
                )
            elif path == f"/api/runs/{RUN_ID}/work-plan" and method == "POST":
                payload = request_json(request)
                refresh_reason = payload.get("refresh_reason")
                if refresh_reason == "creator_app_run_plan":
                    counts["run_plan_materialize"] += 1
                    seen["run_plan_materialize"].set()
                    await fulfill_json(route, materialized_work_plan_result(), delay=0.5)
                elif refresh_reason == "creator_app_after_run_plan":
                    counts["run_plan_refresh"] += 1
                    seen["run_plan_refresh"].set()
                    await fulfill_json(route, post_run_work_plan_result(), delay=0.5)
                else:
                    counts["work_plan"] += 1
                    seen["work_plan_request_started"].set()
                    await fulfill_json(route, work_plan_result(), delay=0.5)
                    seen["work_plan"].set()
            elif path == "/api/a2a/messages" and method == "POST":
                counts["source_refresh_message"] += 1
                seen["source_refresh_message"].set()
                await fulfill_json(route, agent_message_create_result(), delay=0.5)
            elif path == f"/api/a2a/messages/{RETRY_MESSAGE_ID}/retry" and method == "POST":
                counts["retry_authorize"] += 1
                seen["retry_authorize"].set()
                await fulfill_json(route, retry_authorized_result(), delay=0.5)
            elif path == f"/api/feedback/{FEEDBACK_ID}/resolve" and method == "POST":
                counts["feedback_resolve"] += 1
                feedback_resolve_payloads.append(request_json(request))
                seen["feedback_resolve_started"].set()
                await fulfill_json(route, feedback_resolution_result(), delay=0.5)
                seen["feedback_resolve"].set()
            elif path == "/api/a2a/workers/run-cycle" and method == "POST":
                payload = request_json(request)
                if fixture_state["retry_phase"]:
                    retry_phase_worker_payloads.append(payload)
                    if payload.get("message_ids") != [RETRY_MESSAGE_ID]:
                        unexpected_api_requests.append(
                            f"Unexpected retry-phase worker cycle payload: {payload}"
                        )
                        await fulfill_json(
                            route,
                            {"detail": "Unexpected retry-phase worker-cycle payload."},
                            status=500,
                        )
                        return
                if payload.get("message_ids") == [RETRY_MESSAGE_ID]:
                    counts["retry_cycle"] += 1
                    seen["retry_cycle_started"].set()
                    await fulfill_json(route, retry_cycle_result(), delay=0.5)
                    seen["retry_cycle"].set()
                elif payload.get("agent_ids") == ["frontend-experience-engineer"]:
                    counts["run_plan_cycle"] += 1
                    seen["run_plan_cycle_started"].set()
                    await fulfill_json(route, run_plan_cycle_result(), delay=0.5)
                    seen["run_plan_cycle"].set()
                elif payload.get("agent_ids") == [] and payload.get("message_ids") == []:
                    if fixture_state["manual_continue_phase"]:
                        counts["manual_continue_cycle"] += 1
                        seen["manual_continue_cycle_started"].set()
                        await fulfill_json(route, manual_continue_cycle_result(), delay=0.5)
                        seen["manual_continue_cycle"].set()
                        return
                    counts["voice_followup_cycle"] += 1
                    seen["voice_followup_cycle_started"].set()
                    await fulfill_json(route, voice_followup_cycle_result(), delay=0.5)
                    seen["voice_followup_cycle"].set()
                else:
                    counts["source_refresh_cycle"] += 1
                    seen["source_refresh_cycle_started"].set()
                    await fulfill_json(route, source_refresh_cycle_result(), delay=0.5)
                    seen["source_refresh_cycle"].set()
            elif path == f"/api/runs/{RUN_ID}/publish-readiness" and method == "POST":
                counts["publish"] += 1
                seen["publish_request_started"].set()
                await fulfill_json(route, publish_readiness_result(), delay=0.5)
                seen["publish"].set()
            elif path == f"/api/runs/{RUN_ID}/growth-package" and method == "POST":
                counts["growth_package"] += 1
                growth_package_payloads.append(request_json(request))
                seen["growth_package_request_started"].set()
                await fulfill_json(route, growth_package_result(), delay=0.5)
                seen["growth_package"].set()
            elif path == f"/api/runs/{RUN_ID}/media-production" and method == "POST":
                counts["media_plan"] += 1
                media_plan_payloads.append(request_json(request))
                seen["media_plan_request_started"].set()
                await fulfill_json(route, media_plan_result(), delay=0.5)
                seen["media_plan"].set()
            elif path == f"/api/runs/{RUN_ID}/voice-setup-proof" and method == "POST":
                counts["setup_check_proof"] += 1
                payload = request_json(request)
                setup_check_proof_payloads.append(payload)
                if payload.get("action") == "refresh_provider_readiness":
                    counts["provider_resolve_proof"] += 1
                await fulfill_json(
                    route,
                    {
                        "run_id": RUN_ID,
                        "status": "blocked",
                        "action": payload.get("action", "check_setup"),
                        "artifact_id": None,
                        "event_id": 5001,
                        "summary": "Browser fixture voice setup check recorded.",
                    },
                    delay=0.5,
                )
                if payload.get("action") == "refresh_provider_readiness":
                    seen["provider_resolve_proof"].set()
                seen["setup_check_proof"].set()
            elif path == f"/api/runs/{RUN_ID}/provider-smoke" and method == "POST":
                counts["voice_provider_smoke"] += 1
                voice_provider_smoke_payloads.append(request_json(request))
                seen["voice_provider_smoke_request_started"].set()
                await fulfill_json(route, voice_provider_smoke_result(), delay=0.5)
                seen["voice_provider_smoke"].set()
            elif path == f"/api/runs/{RUN_ID}/realtime-voice-timing-ledger" and method == "POST":
                counts["voice_timing_ledger"] += 1
                voice_timing_ledger_payloads.append(request_json(request))
                seen["voice_timing_ledger_request_started"].set()
                await fulfill_json(route, voice_timing_ledger_result(), delay=0.5)
                seen["voice_timing_ledger"].set()
            elif path == f"/api/runs/{RUN_ID}/realtime-session" and method == "POST":
                payload = request_json(request)
                if payload.get("dry_run") is False and payload.get("transport_framework") == "livekit":
                    counts["provider_live_join_start"] += 1
                    provider_live_join_payloads.append(payload)
                    seen["provider_live_join_request_started"].set()
                    await fulfill_json(route, provider_live_session_result(), delay=0.5)
                    seen["provider_live_join_start"].set()
                else:
                    counts["transcript_rehearsal_start"] += 1
                    transcript_rehearsal_payloads.append(payload)
                    await fulfill_json(route, transcript_rehearsal_session_result(), delay=0.5)
                    seen["transcript_rehearsal_start"].set()
            elif (
                path == "/api/realtime-sessions/77777777-7777-4777-8777-777777777779/status"
                and method == "POST"
            ):
                counts["provider_join_end_session"] += 1
                provider_join_end_payloads.append(request_json(request))
                await fulfill_json(
                    route,
                    {
                        "run_id": RUN_ID,
                        "realtime_session_id": "77777777-7777-4777-8777-777777777779",
                        "provider": "gemma4_realtime",
                        "status": "ended",
                    },
                    delay=0.5,
                )
                seen["provider_join_end_session"].set()
            elif (
                path == "/api/realtime-sessions/77777777-7777-4777-8777-777777777778/status"
                and method == "POST"
            ):
                counts["transcript_rehearsal_stop"] += 1
                transcript_rehearsal_stop_payloads.append(request_json(request))
                seen["transcript_rehearsal_stop_started"].set()
                await fulfill_json(
                    route,
                    {
                        "run_id": RUN_ID,
                        "realtime_session_id": "77777777-7777-4777-8777-777777777778",
                        "provider": "gemma4_realtime",
                        "status": "ended",
                    },
                    delay=0.5,
                )
                seen["transcript_rehearsal_stop"].set()
            elif (
                path == "/api/realtime-sessions/77777777-7777-4777-8777-777777777778/turns"
                and method == "POST"
            ):
                counts["transcript_rehearsal_turn"] += 1
                transcript_rehearsal_turn_payloads.append(request_json(request))
                seen["transcript_rehearsal_turn_started"].set()
                await fulfill_json(route, transcript_rehearsal_turn_result(), delay=0.5)
                seen["transcript_rehearsal_turn"].set()
            elif path == f"/api/runs/{RUN_ID}/revision-loop" and method == "POST":
                counts["revision"] += 1
                seen["revision_started"].set()
                await fulfill_json(route, revision_result(), delay=0.5)
                seen["revision"].set()
            else:
                unexpected_api_requests.append(f"{method} {path}")
                await fulfill_json(route, {"detail": f"Unexpected API request: {method} {path}"}, status=500)

        await page.route("**/api/**", handle_api)
        await page.goto(base_url, wait_until="domcontentloaded")
        await expect(page.get_by_role("heading", name="Tell the agents what to make")).to_be_visible()
        await page.wait_for_load_state("networkidle")

        create_voice_run = page.get_by_role("button", name="Create voice run")
        await expect(create_voice_run).to_be_enabled(timeout=10000)
        await create_voice_run.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["voice_run_create"].wait(), timeout=5)
        await asyncio.wait_for(seen["voice_run_context_refresh"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        assert counts["voice_run_create"] == 1, (
            f"Expected one voice-run create request after rapid Create voice run clicks, "
            f"got {counts['voice_run_create']}"
        )
        assert counts["voice_run_context_refresh"] == 1, (
            f"Expected one same-run context refresh after voice-run create, "
            f"got {counts['voice_run_context_refresh']}"
        )
        assert voice_run_create_payloads == [
            {
                "goal": "Create source-backed social content from my live voice session.",
                "input_mode": "voice",
                "initial_context": {
                    "input_surface": "live_voice_panel",
                    "voice_provider": "gemma4_realtime",
                    "provider_backed_realtime": True,
                    "voice_first": True,
                    "audio_understanding_model": "google/gemma-4-E4B-it",
                    "tts_model": "hexgrad/Kokoro-82M",
                    "rehearsal_only": False,
                },
            }
        ], f"Unexpected voice-run create payloads: {voice_run_create_payloads}"
        await expect(create_voice_run).not_to_be_visible(timeout=10000)
        await expect(page.locator(".status-strip")).to_contain_text(
            "Created a voice-first run. Join Live Voice when setup is ready.",
            timeout=10000,
        )

        run_web_research = page.get_by_role("button", name="Run web research")
        await expect(run_web_research).to_be_enabled(timeout=10000)

        resolve_runtime_preflight = page.locator(
            ".voice-readiness-header > button",
            has_text="Run preflight",
        )
        await expect(resolve_runtime_preflight).to_be_enabled(timeout=10000)
        source_message_before_resolve_preflight_overlap = counts["source_refresh_message"]
        source_cycle_before_resolve_preflight_overlap = counts["source_refresh_cycle"]
        await resolve_runtime_preflight.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["runtime_preflight_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["source_refresh_message"] == source_message_before_resolve_preflight_overlap, (
            f"Expected no source-refresh A2A message while Resolve next Run preflight is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_resolve_preflight_overlap, (
            f"Expected no source-refresh worker cycle while Resolve next Run preflight is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["runtime_preflight"].wait(), timeout=5)
        await asyncio.wait_for(seen["setup_check_proof"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        assert counts["runtime_preflight"] == 1, (
            f"Expected one resolver runtime preflight request after rapid Resolve next clicks, "
            f"got {counts['runtime_preflight']}"
        )
        assert setup_check_proof_payloads[-1]["action"] == "run_preflight", (
            f"Unexpected resolver preflight proof payloads: {setup_check_proof_payloads}"
        )

        seen["runtime_preflight_started"].clear()
        seen["runtime_preflight"].clear()
        runtime_preflight_count_before_direct = counts["runtime_preflight"]
        runtime_preflight_query_count_before_direct = len(runtime_preflight_queries)

        runtime_preflight = page.get_by_role("button", name="Runtime preflight")
        await expect(runtime_preflight).to_be_enabled(timeout=10000)
        source_message_before_runtime_preflight_overlap = counts["source_refresh_message"]
        source_cycle_before_runtime_preflight_overlap = counts["source_refresh_cycle"]
        await runtime_preflight.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["runtime_preflight_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["source_refresh_message"] == source_message_before_runtime_preflight_overlap, (
            f"Expected no source-refresh A2A message while Runtime preflight is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_runtime_preflight_overlap, (
            f"Expected no source-refresh worker cycle while Runtime preflight is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["runtime_preflight"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        assert counts["runtime_preflight"] == runtime_preflight_count_before_direct + 1, (
            f"Expected one runtime preflight request after rapid Runtime preflight clicks, "
            f"got {counts['runtime_preflight']}"
        )
        assert runtime_preflight_queries[runtime_preflight_query_count_before_direct:] == [
            {
                "preflight_edge": ["true"],
                "preflight_agent": ["true"],
                "preflight_livekit": ["true"],
                "preflight_gemma": ["true"],
                "preflight_tts": ["true"],
            }
        ], f"Runtime preflight did not request the full provider checks: {runtime_preflight_queries}"
        await expect(page.get_by_text("Runtime preflight complete", exact=True).first).to_be_visible(
            timeout=10000
        )

        live_proof_provider_refresh = page.get_by_role("button", name="Refresh provider readiness")
        await expect(live_proof_provider_refresh).to_be_enabled(timeout=10000)
        fixture_state["live_proof_provider_refresh_phase"] = True
        source_message_before_live_proof_provider_overlap = counts["source_refresh_message"]
        source_cycle_before_live_proof_provider_overlap = counts["source_refresh_cycle"]
        await live_proof_provider_refresh.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["live_proof_provider_refresh_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["source_refresh_message"] == source_message_before_live_proof_provider_overlap, (
            f"Expected no source-refresh A2A message while live proof Refresh provider readiness is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_live_proof_provider_overlap, (
            f"Expected no source-refresh worker cycle while live proof Refresh provider readiness is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["live_proof_provider_refresh"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        fixture_state["live_proof_provider_refresh_phase"] = False
        assert counts["live_proof_provider_refresh"] == 1, (
            f"Expected one provider readiness refresh after rapid live proof path clicks, "
            f"got {counts['live_proof_provider_refresh']}"
        )

        provider_panel_refresh = page.get_by_role("button", name="Provider readiness", exact=True)
        await expect(provider_panel_refresh).to_be_enabled(timeout=10000)
        fixture_state["provider_panel_refresh_phase"] = True
        source_message_before_provider_panel_overlap = counts["source_refresh_message"]
        source_cycle_before_provider_panel_overlap = counts["source_refresh_cycle"]
        await provider_panel_refresh.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["provider_panel_refresh_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["source_refresh_message"] == source_message_before_provider_panel_overlap, (
            f"Expected no source-refresh A2A message while provider panel refresh is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_provider_panel_overlap, (
            f"Expected no source-refresh worker cycle while provider panel refresh is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["provider_panel_refresh"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        fixture_state["provider_panel_refresh_phase"] = False
        assert counts["provider_panel_refresh"] == 1, (
            f"Expected one provider readiness refresh after rapid provider panel clicks, "
            f"got {counts['provider_panel_refresh']}"
        )

        secret_file_setup = page.get_by_label("Secret file diagnostics")
        secret_input = secret_file_setup.locator("input").first
        save_locally = secret_file_setup.get_by_role("button", name="Save locally").first
        await secret_input.fill("fixture-livekit-api-key")
        await expect(save_locally).to_be_enabled(timeout=10000)
        source_message_before_secret_save_overlap = counts["source_refresh_message"]
        source_cycle_before_secret_save_overlap = counts["source_refresh_cycle"]
        await save_locally.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["local_secret_file_save_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["source_refresh_message"] == source_message_before_secret_save_overlap, (
            f"Expected no source-refresh A2A message while secret file save is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_secret_save_overlap, (
            f"Expected no source-refresh worker cycle while secret file save is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["local_secret_file_save"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        assert counts["local_secret_file_save"] == 1, (
            f"Expected one secret file save request, got {counts['local_secret_file_save']}"
        )
        assert local_secret_file_payloads == [
            {
                "env_name": "LIVEKIT_API_KEY",
                "secret_value": "fixture-livekit-api-key",
            }
        ], f"Unexpected secret file save payloads: {local_secret_file_payloads}"

        provider_endpoint_setup = page.get_by_label("Provider endpoint setup")
        endpoint_input = provider_endpoint_setup.locator("input").first
        save_endpoint = provider_endpoint_setup.get_by_role("button", name="Save endpoint").first
        await endpoint_input.fill("http://127.0.0.1:7880")
        await expect(save_endpoint).to_be_enabled(timeout=10000)
        source_message_before_provider_config_overlap = counts["source_refresh_message"]
        source_cycle_before_provider_config_overlap = counts["source_refresh_cycle"]
        await save_endpoint.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["local_provider_config_save_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["source_refresh_message"] == source_message_before_provider_config_overlap, (
            f"Expected no source-refresh A2A message while provider endpoint save is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_provider_config_overlap, (
            f"Expected no source-refresh worker cycle while provider endpoint save is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["local_provider_config_save"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        assert counts["local_provider_config_save"] == 1, (
            f"Expected one provider endpoint save request, got {counts['local_provider_config_save']}"
        )
        assert local_provider_config_payloads == [
            {
                "env_name": "GEMMA4_MULTIMODAL_ENDPOINT_URL",
                "config_value": "http://127.0.0.1:7880",
            }
        ], f"Unexpected provider endpoint save payloads: {local_provider_config_payloads}"

        local_livekit_dev = page.get_by_role("button", name="Use local LiveKit dev defaults")
        await expect(local_livekit_dev).to_be_enabled(timeout=10000)
        source_message_before_local_livekit_config_overlap = counts["source_refresh_message"]
        source_cycle_before_local_livekit_config_overlap = counts["source_refresh_cycle"]
        await local_livekit_dev.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["local_livekit_dev_config_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["source_refresh_message"] == source_message_before_local_livekit_config_overlap, (
            f"Expected no source-refresh A2A message while local LiveKit dev config is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_local_livekit_config_overlap, (
            f"Expected no source-refresh worker cycle while local LiveKit dev config is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["local_livekit_dev_config"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        assert counts["local_livekit_dev_config"] == 1, (
            f"Expected one local LiveKit dev config request, got {counts['local_livekit_dev_config']}"
        )

        join_voice_room = page.get_by_role("button", name="Join voice room")
        await expect(join_voice_room).to_be_enabled(timeout=10000)
        source_message_before_join_overlap = counts["source_refresh_message"]
        source_cycle_before_join_overlap = counts["source_refresh_cycle"]
        await join_voice_room.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["provider_live_join_request_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["source_refresh_message"] == source_message_before_join_overlap, (
            f"Expected no source-refresh A2A message while Join voice room is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_join_overlap, (
            f"Expected no source-refresh worker cycle while Join voice room is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["provider_live_join_start"].wait(), timeout=5)
        await asyncio.wait_for(seen["provider_join_end_session"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        assert counts["provider_live_join_start"] == 1, (
            f"Expected one provider-backed realtime session request after rapid Join voice room clicks, "
            f"got {counts['provider_live_join_start']}"
        )
        assert provider_live_join_payloads == [
            {
                "provider": "gemma4_realtime",
                "voice": "af_heart",
                "transport_framework": "livekit",
                "room_name": None,
                "participant_identity": None,
                "agent_participant_identity": None,
                "context_window_turns": 4,
                "summarize_after_turns": 3,
                "dry_run": False,
                "metadata": {
                    "frontend": "next-app",
                    "selected_voice_provider": "gemma4_realtime",
                },
            }
        ], f"Unexpected provider-backed join payloads: {provider_live_join_payloads}"
        assert counts["provider_join_end_session"] == 1, (
            f"Expected one cleanup status update after blocked provider-backed Join voice room, "
            f"got {counts['provider_join_end_session']}"
        )
        assert provider_join_end_payloads == [
            {
                "status": "ended",
                "reason": "Discarded Gemma/Kokoro voice session after LiveKit join did not complete.",
            }
        ], f"Unexpected provider join cleanup payloads: {provider_join_end_payloads}"

        check_setup = page.get_by_role("button", name="Check setup")
        await expect(check_setup).to_be_enabled(timeout=10000)
        fixture_state["setup_check_phase"] = True
        seen["setup_check_proof"].clear()
        setup_check_proof_before_check = counts["setup_check_proof"]
        source_message_before_setup_overlap = counts["source_refresh_message"]
        source_cycle_before_setup_overlap = counts["source_refresh_cycle"]
        await check_setup.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["setup_check_request_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["source_refresh_message"] == source_message_before_setup_overlap, (
            f"Expected no source-refresh A2A message while Check setup is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_setup_overlap, (
            f"Expected no source-refresh worker cycle while Check setup is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["setup_check_proof"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        fixture_state["setup_check_phase"] = False
        assert counts["setup_check_livekit_process"] == 1, (
            f"Expected one LiveKit process refresh after rapid Check setup clicks, "
            f"got {counts['setup_check_livekit_process']}"
        )
        assert counts["setup_check_voice_process"] == 1, (
            f"Expected one voice-agent process refresh after rapid Check setup clicks, "
            f"got {counts['setup_check_voice_process']}"
        )
        assert counts["setup_check_provider_readiness"] == 1, (
            f"Expected one provider-readiness refresh after rapid Check setup clicks, "
            f"got {counts['setup_check_provider_readiness']}"
        )
        assert counts["setup_check_runtime_preflight"] == 1, (
            f"Expected one setup runtime preflight after rapid Check setup clicks, "
            f"got {counts['setup_check_runtime_preflight']}"
        )
        assert counts["setup_check_presence"] == 1, (
            f"Expected one voice-agent presence check after rapid Check setup clicks, "
            f"got {counts['setup_check_presence']}"
        )
        assert counts["setup_check_proof"] == setup_check_proof_before_check + 1, (
            f"Expected one durable voice setup proof after rapid Check setup clicks, "
            f"got {counts['setup_check_proof']}"
        )
        assert setup_check_proof_payloads[-1]["action"] == "check_setup", (
            f"Unexpected setup proof action: {setup_check_proof_payloads}"
        )
        assert setup_check_proof_payloads[-1]["metadata"]["action_source"] == "check_setup", (
            f"Unexpected setup proof metadata: {setup_check_proof_payloads}"
        )

        resolve_provider_refresh = page.get_by_role("button", name="Refresh providers")
        await expect(resolve_provider_refresh).to_be_enabled(timeout=10000)
        fixture_state["provider_resolve_phase"] = True
        source_message_before_resolve_provider_overlap = counts["source_refresh_message"]
        source_cycle_before_resolve_provider_overlap = counts["source_refresh_cycle"]
        await resolve_provider_refresh.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["provider_resolve_refresh_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["source_refresh_message"] == source_message_before_resolve_provider_overlap, (
            f"Expected no source-refresh A2A message while Resolve next Refresh providers is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_resolve_provider_overlap, (
            f"Expected no source-refresh worker cycle while Resolve next Refresh providers is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["provider_resolve_refresh"].wait(), timeout=5)
        await asyncio.wait_for(seen["provider_resolve_proof"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        fixture_state["provider_resolve_phase"] = False
        assert counts["provider_resolve_refresh"] == 1, (
            f"Expected one provider readiness refresh after rapid Resolve next clicks, "
            f"got {counts['provider_resolve_refresh']}"
        )
        assert counts["provider_resolve_proof"] == 1, (
            f"Expected one provider readiness setup proof after rapid Resolve next clicks, "
            f"got {counts['provider_resolve_proof']}"
        )

        runtime_smoke = page.get_by_role("button", name="Runtime smoke")
        await expect(runtime_smoke).to_be_enabled(timeout=10000)
        source_message_before_runtime_smoke_overlap = counts["source_refresh_message"]
        source_cycle_before_runtime_smoke_overlap = counts["source_refresh_cycle"]
        await runtime_smoke.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["voice_provider_smoke_request_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["source_refresh_message"] == source_message_before_runtime_smoke_overlap, (
            f"Expected no source-refresh A2A message while Runtime smoke is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_runtime_smoke_overlap, (
            f"Expected no source-refresh worker cycle while Runtime smoke is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["voice_provider_smoke"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        assert counts["voice_provider_smoke"] == 1, (
            f"Expected one provider smoke request after rapid Runtime smoke clicks, "
            f"got {counts['voice_provider_smoke']}"
        )
        assert voice_provider_smoke_payloads == [
            {
                "record_artifact": True,
                "execute_live_calls": False,
                "realtime_provider": "openrouter_livekit",
                "realtime_session_id": None,
                "require_voice_agent_presence": False,
                "voice_agent_presence_stale_after_seconds": 60,
                "max_voice_audio_artifact_age_seconds": 120,
                "voice": "af_heart",
                "include_gemma": False,
                "include_realtime": True,
                "include_web_search": False,
                "include_reranker": False,
                "include_imagegen_boundary": False,
                "topic": "OpenRouter DeepSeek Kokoro LiveKit voice runtime smoke",
            }
        ], f"Unexpected provider smoke payloads: {voice_provider_smoke_payloads}"

        timing_ledger = page.get_by_role("button", name="Timing ledger")
        await expect(timing_ledger).to_be_enabled(timeout=10000)
        source_message_before_timing_ledger_overlap = counts["source_refresh_message"]
        source_cycle_before_timing_ledger_overlap = counts["source_refresh_cycle"]
        await timing_ledger.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["voice_timing_ledger_request_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["source_refresh_message"] == source_message_before_timing_ledger_overlap, (
            f"Expected no source-refresh A2A message while Timing ledger is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_timing_ledger_overlap, (
            f"Expected no source-refresh worker cycle while Timing ledger is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["voice_timing_ledger"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        assert counts["voice_timing_ledger"] == 1, (
            f"Expected one timing ledger request after rapid Timing ledger clicks, "
            f"got {counts['voice_timing_ledger']}"
        )
        assert voice_timing_ledger_payloads == [
            {
                "record_artifact": True,
                "event_limit": 500,
            }
        ], f"Unexpected timing ledger payloads: {voice_timing_ledger_payloads}"

        seen["voice_provider_smoke"].clear()
        seen["voice_timing_ledger"].clear()
        await page.evaluate(
            """() => {
                const buttons = Array.from(document.querySelectorAll("button"));
                const runtimeSmoke = buttons.find((button) =>
                    button.textContent && button.textContent.includes("Runtime smoke")
                );
                const timingLedger = buttons.find((button) =>
                    button.textContent && button.textContent.includes("Timing ledger")
                );
                if (!runtimeSmoke || !timingLedger) {
                    throw new Error("Voice proof buttons not found");
                }
                runtimeSmoke.click();
                timingLedger.click();
            }"""
        )
        await asyncio.wait_for(seen["voice_provider_smoke"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        assert counts["voice_provider_smoke"] == 2, (
            f"Expected one extra provider smoke request after Runtime smoke then Timing ledger, "
            f"got {counts['voice_provider_smoke']}"
        )
        assert counts["voice_timing_ledger"] == 1, (
            f"Expected no extra timing ledger request while Runtime smoke is in flight, "
            f"got {counts['voice_timing_ledger']}"
        )

        seen["voice_provider_smoke"].clear()
        seen["voice_timing_ledger"].clear()
        await page.evaluate(
            """() => {
                const buttons = Array.from(document.querySelectorAll("button"));
                const runtimeSmoke = buttons.find((button) =>
                    button.textContent && button.textContent.includes("Runtime smoke")
                );
                const timingLedger = buttons.find((button) =>
                    button.textContent && button.textContent.includes("Timing ledger")
                );
                if (!runtimeSmoke || !timingLedger) {
                    throw new Error("Voice proof buttons not found");
                }
                timingLedger.click();
                runtimeSmoke.click();
            }"""
        )
        await asyncio.wait_for(seen["voice_timing_ledger"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        assert counts["voice_timing_ledger"] == 2, (
            f"Expected one extra timing ledger request after Timing ledger then Runtime smoke, "
            f"got {counts['voice_timing_ledger']}"
        )
        assert counts["voice_provider_smoke"] == 2, (
            f"Expected no extra provider smoke request while Timing ledger is in flight, "
            f"got {counts['voice_provider_smoke']}"
        )

        await page.get_by_role("button", name="Current explainer").click()
        await expect(page.get_by_label("Composer input")).to_have_value(
            re.compile("Create a source-backed explanation")
        )
        generate = page.get_by_role("button", name="Generate")
        await expect(generate).to_be_enabled(timeout=10000)
        await expect(run_web_research).to_be_enabled(timeout=10000)
        source_message_before_generate_overlap = counts["source_refresh_message"]
        source_cycle_before_generate_overlap = counts["source_refresh_cycle"]
        await generate.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["conversation_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["source_refresh_message"] == source_message_before_generate_overlap, (
            f"Expected no source-refresh A2A message while Generate is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_generate_overlap, (
            f"Expected no source-refresh worker cycle while Generate is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["conversation"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        assert counts["conversation"] == 1, (
            f"Expected one conversation route request after rapid Generate clicks, "
            f"got {counts['conversation']}"
        )
        assert conversation_payloads[0]["run_id"] == RUN_ID, (
            f"Expected Generate after voice-run create to continue run {RUN_ID}, "
            f"got {conversation_payloads[0].get('run_id')}"
        )
        assert conversation_payloads[0]["intent"] == "auto", (
            f"Expected Generate after voice-run create to use auto intent, "
            f"got {conversation_payloads[0].get('intent')}"
        )
        await run_web_research.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["source_refresh_message"].wait(), timeout=5)
        await asyncio.wait_for(seen["source_refresh_cycle"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        assert counts["source_refresh_message"] == 1, (
            f"Expected one source-refresh message after rapid Run web research clicks, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == 1, (
            f"Expected one source-refresh worker cycle after rapid Run web research clicks, "
            f"got {counts['source_refresh_cycle']}"
        )

        seen["source_refresh_message"].clear()
        seen["source_refresh_cycle_started"].clear()
        seen["source_refresh_cycle"].clear()
        source_cycle_before_overlap = counts["source_refresh_cycle"]
        manual_refresh_before_source_overlap = counts["manual_refresh_context"]
        growth_before_source_overlap = counts["growth_package"]
        topbar_refresh = page.get_by_role("button", name="Refresh", exact=True)
        topbar_new = page.get_by_role("button", name="New", exact=True)
        await run_web_research.click()
        await asyncio.wait_for(seen["source_refresh_cycle_started"].wait(), timeout=5)
        fixture_state["manual_refresh_phase"] = True
        await topbar_refresh.evaluate("(button) => button.click()")
        await page.wait_for_timeout(100)
        assert counts["manual_refresh_context"] == manual_refresh_before_source_overlap, (
            f"Expected no topbar Refresh context request while Run web research is in flight, "
            f"got {counts['manual_refresh_context']}"
        )
        fixture_state["manual_refresh_phase"] = False
        await topbar_new.evaluate("(button) => button.click()")
        await page.wait_for_timeout(100)
        await expect(create_voice_run).not_to_be_visible(timeout=1000)
        await expect(page.locator(".run-chip")).to_contain_text("11111111", timeout=1000)
        await page.get_by_role("button", name="Growth package").evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["source_refresh_cycle"] == source_cycle_before_overlap + 1, (
            f"Expected one extra source-refresh worker cycle before overlap assertion, "
            f"got {counts['source_refresh_cycle']}"
        )
        expected_source_refresh_cycle_count = source_cycle_before_overlap + 1
        assert counts["growth_package"] == growth_before_source_overlap, (
            f"Expected no growth package request while Run web research is in flight, "
            f"got {counts['growth_package']}"
        )
        await asyncio.wait_for(seen["source_refresh_cycle"].wait(), timeout=5)

        continue_specialists = page.get_by_role("button", name="Continue specialists")
        await expect(continue_specialists).to_be_enabled(timeout=10000)
        fixture_state["manual_continue_phase"] = True
        source_message_before_manual_continue_overlap = counts["source_refresh_message"]
        source_cycle_before_manual_continue_overlap = counts["source_refresh_cycle"]
        await continue_specialists.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["manual_continue_cycle_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["source_refresh_message"] == source_message_before_manual_continue_overlap, (
            f"Expected no source-refresh A2A message while Continue specialists is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_manual_continue_overlap, (
            f"Expected no source-refresh worker cycle while Continue specialists is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["manual_continue_cycle"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        fixture_state["manual_continue_phase"] = False
        assert counts["manual_continue_cycle"] == 1, (
            f"Expected one manual specialist continuation after rapid Continue specialists clicks, "
            f"got {counts['manual_continue_cycle']}"
        )

        start_always_on = page.get_by_role("button", name="Start always-on")
        await expect(start_always_on).to_be_enabled(timeout=10000)
        source_message_before_launch_overlap = counts["source_refresh_message"]
        source_cycle_before_launch_overlap = counts["source_refresh_cycle"]
        await start_always_on.click()
        await asyncio.wait_for(seen["autopilot_launch_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["autopilot_launch"] == 1, (
            f"Expected one always-on launch request before overlap assertion, "
            f"got {counts['autopilot_launch']}"
        )
        assert counts["source_refresh_message"] == source_message_before_launch_overlap, (
            f"Expected no source-refresh A2A message while Start always-on is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_launch_overlap, (
            f"Expected no source-refresh worker cycle while Start always-on is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["autopilot_launch"].wait(), timeout=5)
        status_strip = page.locator(".status-strip")
        await expect(status_strip).to_contain_text("Always-on studio started.", timeout=10000)
        await expect(status_strip).to_contain_text(re.compile("Always-on studio launch recorded"))
        await expect(status_strip).to_contain_text(re.compile("Creator always-on studio"))
        await expect(page.get_by_text(re.compile("Autopilot launch recorded"))).not_to_be_visible()
        await expect(page.get_by_text(re.compile("Creator app autopilot"))).not_to_be_visible()

        run_pulse = page.get_by_role("button", name="Run pulse")
        await expect(run_pulse).to_be_enabled(timeout=10000)
        await run_pulse.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["autopilot_heartbeat"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        assert counts["autopilot_heartbeat"] == 1, (
            f"Expected one specialist pulse request after rapid Run pulse clicks, "
            f"got {counts['autopilot_heartbeat']}"
        )
        await expect(status_strip).to_contain_text("Specialist pulse finished.", timeout=10000)

        seen["autopilot_heartbeat_started"].clear()
        seen["autopilot_heartbeat"].clear()
        heartbeat_count_before_overlap = counts["autopilot_heartbeat"]
        source_message_before_heartbeat_overlap = counts["source_refresh_message"]
        source_cycle_before_heartbeat_overlap = counts["source_refresh_cycle"]
        await run_pulse.click()
        await asyncio.wait_for(seen["autopilot_heartbeat_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["autopilot_heartbeat"] == heartbeat_count_before_overlap + 1, (
            f"Expected one extra specialist pulse request before overlap assertion, "
            f"got {counts['autopilot_heartbeat']}"
        )
        assert counts["source_refresh_message"] == source_message_before_heartbeat_overlap, (
            f"Expected no source-refresh A2A message while Run pulse is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_heartbeat_overlap, (
            f"Expected no source-refresh worker cycle while Run pulse is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["autopilot_heartbeat"].wait(), timeout=5)

        check_due_work = page.get_by_role("button", name="Check due work")
        await expect(check_due_work).to_be_enabled(timeout=10000)
        await check_due_work.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["autopilot_scheduler"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        assert counts["autopilot_scheduler"] == 1, (
            f"Expected one always-on scheduler request after rapid Check due work clicks, "
            f"got {counts['autopilot_scheduler']}"
        )
        assert autopilot_scheduler_payloads == [
            {
                "max_profiles": 10,
                "run_id": RUN_ID,
                "execution_mode": "autonomous_pass",
            }
        ], f"Unexpected always-on scheduler payloads: {autopilot_scheduler_payloads}"
        await expect(status_strip).to_contain_text(
            "Always-on studio checked due work.",
            timeout=10000,
        )

        seen["autopilot_scheduler_started"].clear()
        seen["autopilot_scheduler"].clear()
        scheduler_count_before_overlap = counts["autopilot_scheduler"]
        source_message_before_scheduler_overlap = counts["source_refresh_message"]
        source_cycle_before_scheduler_overlap = counts["source_refresh_cycle"]
        await check_due_work.click()
        await asyncio.wait_for(seen["autopilot_scheduler_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["autopilot_scheduler"] == scheduler_count_before_overlap + 1, (
            f"Expected one extra always-on scheduler request before overlap assertion, "
            f"got {counts['autopilot_scheduler']}"
        )
        assert counts["source_refresh_message"] == source_message_before_scheduler_overlap, (
            f"Expected no source-refresh A2A message while Check due work is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_scheduler_overlap, (
            f"Expected no source-refresh worker cycle while Check due work is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["autopilot_scheduler"].wait(), timeout=5)

        start_runner = page.get_by_role("button", name="Start runner")
        await expect(start_runner).to_be_enabled(timeout=10000)
        source_message_before_runner_overlap = counts["source_refresh_message"]
        source_cycle_before_runner_overlap = counts["source_refresh_cycle"]
        await start_runner.click()
        await asyncio.wait_for(seen["runner_start"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["source_refresh_message"] == source_message_before_runner_overlap, (
            f"Expected no source-refresh A2A message while Start runner is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_runner_overlap, (
            f"Expected no source-refresh worker cycle while Start runner is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await expect(status_strip).to_contain_text("Background runner is running.", timeout=10000)
        await expect(page.get_by_text(re.compile("Local worker scheduler process"))).not_to_be_visible()
        await expect(page.get_by_text(re.compile("local scheduler"))).not_to_be_visible()

        stop_runner = page.get_by_role("button", name="Stop runner")
        await expect(stop_runner).to_be_enabled(timeout=10000)
        runner_stop_before_overlap = counts["runner_stop"]
        source_message_before_runner_stop_overlap = counts["source_refresh_message"]
        source_cycle_before_runner_stop_overlap = counts["source_refresh_cycle"]
        await stop_runner.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["runner_stop_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["runner_stop"] == runner_stop_before_overlap + 1, (
            f"Expected one background-runner stop request before overlap assertion, "
            f"got {counts['runner_stop']}"
        )
        assert counts["source_refresh_message"] == source_message_before_runner_stop_overlap, (
            f"Expected no source-refresh A2A message while Stop runner is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_runner_stop_overlap, (
            f"Expected no source-refresh worker cycle while Stop runner is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["runner_stop"].wait(), timeout=5)
        await expect(status_strip).to_contain_text("Background runner is stopped.", timeout=10000)
        await expect(page.get_by_text(re.compile("local scheduler"))).not_to_be_visible()

        stop_always_on = page.locator(".autopilot-controls").get_by_role(
            "button", name="Stop", exact=True
        )
        await expect(stop_always_on).to_be_enabled(timeout=10000)
        autopilot_stop_before_overlap = counts["autopilot_stop"]
        source_message_before_autopilot_stop_overlap = counts["source_refresh_message"]
        source_cycle_before_autopilot_stop_overlap = counts["source_refresh_cycle"]
        await stop_always_on.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["autopilot_stop_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["autopilot_stop"] == autopilot_stop_before_overlap + 1, (
            f"Expected one always-on stop request before overlap assertion, "
            f"got {counts['autopilot_stop']}"
        )
        assert counts["source_refresh_message"] == source_message_before_autopilot_stop_overlap, (
            f"Expected no source-refresh A2A message while always-on Stop is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_autopilot_stop_overlap, (
            f"Expected no source-refresh worker cycle while always-on Stop is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["autopilot_stop"].wait(), timeout=5)
        await expect(status_strip).to_contain_text("Always-on studio stopped", timeout=10000)

        await expect(page.get_by_text("Needs attention", exact=True)).to_be_visible(timeout=10000)
        queue_and_run = page.get_by_role("button", name="Queue and run")
        await expect(queue_and_run).to_be_enabled(timeout=10000)
        worker_cycle_counts_before_retry = {
            key: counts[key]
            for key in ["source_refresh_cycle", "run_plan_cycle", "retry_cycle"]
        }
        source_message_before_retry_overlap = counts["source_refresh_message"]
        fixture_state["retry_phase"] = True
        await queue_and_run.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["retry_authorize"].wait(), timeout=5)
        await asyncio.wait_for(seen["retry_cycle_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["source_refresh_message"] == source_message_before_retry_overlap, (
            f"Expected no source-refresh A2A message while Queue and run is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == worker_cycle_counts_before_retry[
            "source_refresh_cycle"
        ], (
            f"Expected no source-refresh worker cycle while Queue and run is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["retry_cycle"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        assert counts["source_refresh_message"] == source_message_before_retry_overlap, (
            f"Expected no delayed source-refresh A2A message after Queue and run completed, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == worker_cycle_counts_before_retry[
            "source_refresh_cycle"
        ], (
            f"Expected no delayed source-refresh worker cycle after Queue and run completed, "
            f"got {counts['source_refresh_cycle']}"
        )
        fixture_state["retry_phase"] = False
        assert counts["retry_authorize"] == 1, (
            f"Expected one retry authorization after rapid Queue and run clicks, "
            f"got {counts['retry_authorize']}"
        )
        assert counts["retry_cycle"] == 1, (
            f"Expected one targeted retry worker cycle after rapid Queue and run clicks, "
            f"got {counts['retry_cycle']}"
        )
        assert counts["source_refresh_cycle"] == worker_cycle_counts_before_retry[
            "source_refresh_cycle"
        ], (
            "Queue and run must not create an extra broad source-refresh/default "
            f"cycle; got {counts['source_refresh_cycle']}"
        )
        assert counts["run_plan_cycle"] == worker_cycle_counts_before_retry[
            "run_plan_cycle"
        ], (
            "Queue and run must not create an extra planned-worker/default cycle; "
            f"got {counts['run_plan_cycle']}"
        )
        assert [payload.get("message_ids") for payload in retry_phase_worker_payloads] == [
            [RETRY_MESSAGE_ID]
        ], f"Retry worker-cycle payloads were not strictly targeted: {retry_phase_worker_payloads}"

        suggest_next = page.get_by_role("button", name="Suggest next step")
        await expect(suggest_next).to_be_enabled(timeout=10000)
        source_message_before_planning_overlap = counts["source_refresh_message"]
        source_before_planning_overlap = counts["source_refresh_cycle"]
        await suggest_next.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["work_plan_request_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["source_refresh_message"] == source_message_before_planning_overlap, (
            f"Expected no source-refresh A2A message while Suggest next step is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_before_planning_overlap, (
            f"Expected no source-refresh worker cycle while Suggest next step is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["work_plan"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        assert counts["work_plan"] == 1, (
            f"Expected one work-plan request after rapid Suggest next step clicks, "
            f"got {counts['work_plan']}"
        )

        run_next_steps = page.get_by_role("button", name="Run next steps")
        await expect(run_next_steps).to_be_enabled(timeout=10000)
        source_message_before_run_plan_overlap = counts["source_refresh_message"]
        source_cycle_before_run_plan_overlap = counts["source_refresh_cycle"]
        await run_next_steps.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["run_plan_materialize"].wait(), timeout=5)
        await asyncio.wait_for(seen["run_plan_cycle_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["source_refresh_message"] == source_message_before_run_plan_overlap, (
            f"Expected no source-refresh A2A message while Run next steps is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_run_plan_overlap, (
            f"Expected no source-refresh worker cycle while Run next steps is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["run_plan_cycle"].wait(), timeout=5)
        await asyncio.wait_for(seen["run_plan_refresh"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        assert counts["run_plan_materialize"] == 1, (
            f"Expected one work-plan materialization after rapid Run next steps clicks, "
            f"got {counts['run_plan_materialize']}"
        )
        assert counts["run_plan_cycle"] == 1, (
            f"Expected one planned worker cycle after rapid Run next steps clicks, "
            f"got {counts['run_plan_cycle']}"
        )
        assert counts["run_plan_refresh"] == 1, (
            f"Expected one post-run work-plan refresh after rapid Run next steps clicks, "
            f"got {counts['run_plan_refresh']}"
        )

        growth_package = page.get_by_role("button", name="Growth package")
        await expect(growth_package).to_be_enabled(timeout=10000)
        await growth_package.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["growth_package"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        assert counts["growth_package"] == 1, (
            f"Expected one growth package request after rapid Growth package clicks, "
            f"got {counts['growth_package']}"
        )
        assert growth_package_payloads == [
            {
                "target_artifact_ids": [],
                "platforms": [
                    "instagram_post",
                    "instagram_reel",
                    "linkedin",
                    "x_thread",
                    "substack",
                ],
                "audience": "AI-curious builders, creators, and operators",
                "campaign_goal": "educate with source-backed, ELI5 content",
                "include_outreach": True,
                "created_by_agent_id": "platform-optimization-agent",
                "initiated_by_agent_id": "product-manager",
            }
        ], f"Unexpected growth package payloads: {growth_package_payloads}"

        seen["growth_package_request_started"].clear()
        seen["growth_package"].clear()
        growth_before_source_overlap = counts["growth_package"]
        source_message_before_growth_overlap = counts["source_refresh_message"]
        source_cycle_before_growth_overlap = counts["source_refresh_cycle"]
        await growth_package.click()
        await asyncio.wait_for(seen["growth_package_request_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["growth_package"] == growth_before_source_overlap + 1, (
            f"Expected one extra growth package request before overlap assertion, "
            f"got {counts['growth_package']}"
        )
        assert counts["source_refresh_message"] == source_message_before_growth_overlap, (
            f"Expected no source-refresh A2A message while Growth package is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_growth_overlap, (
            f"Expected no source-refresh worker cycle while Growth package is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["growth_package"].wait(), timeout=5)

        media_plan = page.get_by_role("button", name="Media plan")
        await expect(media_plan).to_be_enabled(timeout=10000)
        await media_plan.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["media_plan"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        assert counts["media_plan"] == 1, (
            f"Expected one media plan request after rapid Media plan clicks, "
            f"got {counts['media_plan']}"
        )
        assert media_plan_payloads == [
            {
                "target_artifact_ids": [],
                "include_image_prompt": True,
                "include_audio_brief": True,
                "include_video_storyboard": True,
                "image_style": "clean educational social visual",
                "voice_style": "natural, warm, interruptible, ELI5",
                "platform": "instagram_reel",
            }
        ], f"Unexpected media plan payloads: {media_plan_payloads}"

        seen["media_plan_request_started"].clear()
        seen["media_plan"].clear()
        media_before_source_overlap = counts["media_plan"]
        source_message_before_media_overlap = counts["source_refresh_message"]
        source_cycle_before_media_overlap = counts["source_refresh_cycle"]
        await media_plan.click()
        await asyncio.wait_for(seen["media_plan_request_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["media_plan"] == media_before_source_overlap + 1, (
            f"Expected one extra media plan request before overlap assertion, "
            f"got {counts['media_plan']}"
        )
        assert counts["source_refresh_message"] == source_message_before_media_overlap, (
            f"Expected no source-refresh A2A message while Media plan is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_media_overlap, (
            f"Expected no source-refresh worker cycle while Media plan is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["media_plan"].wait(), timeout=5)

        publish_check = page.get_by_role("button", name="Publish check")
        seen["growth_package_request_started"].clear()
        seen["growth_package"].clear()
        growth_before_overlap = counts["growth_package"]
        media_before_overlap = counts["media_plan"]
        await growth_package.click()
        await asyncio.wait_for(seen["growth_package_request_started"].wait(), timeout=5)
        await media_plan.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["growth_package"] == growth_before_overlap + 1, (
            f"Expected one extra growth package request before cross-action gate assertion, "
            f"got {counts['growth_package']}"
        )
        assert counts["media_plan"] == media_before_overlap, (
            f"Expected no media plan request while Growth package is in flight, "
            f"got {counts['media_plan']}"
        )
        await asyncio.wait_for(seen["growth_package"].wait(), timeout=5)

        seen["media_plan_request_started"].clear()
        seen["media_plan"].clear()
        seen["publish_request_started"].clear()
        media_before_overlap = counts["media_plan"]
        publish_before_overlap = counts["publish"]
        await media_plan.click()
        await asyncio.wait_for(seen["media_plan_request_started"].wait(), timeout=5)
        await publish_check.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["media_plan"] == media_before_overlap + 1, (
            f"Expected one extra media plan request before cross-action gate assertion, "
            f"got {counts['media_plan']}"
        )
        assert counts["publish"] == publish_before_overlap, (
            f"Expected no publish-readiness request while Media plan is in flight, "
            f"got {counts['publish']}"
        )
        await asyncio.wait_for(seen["media_plan"].wait(), timeout=5)

        await expect(publish_check).to_be_enabled(timeout=10000)
        await publish_check.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["publish"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        assert counts["publish"] == 1, (
            f"Expected one publish-readiness request after rapid Publish check clicks, "
            f"got {counts['publish']}"
        )

        seen["publish_request_started"].clear()
        seen["publish"].clear()
        publish_before_source_overlap = counts["publish"]
        source_message_before_publish_overlap = counts["source_refresh_message"]
        source_cycle_before_publish_overlap = counts["source_refresh_cycle"]
        await publish_check.click()
        await asyncio.wait_for(seen["publish_request_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["publish"] == publish_before_source_overlap + 1, (
            f"Expected one extra publish-readiness request before overlap assertion, "
            f"got {counts['publish']}"
        )
        assert counts["source_refresh_message"] == source_message_before_publish_overlap, (
            f"Expected no source-refresh A2A message while Publish check is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_publish_overlap, (
            f"Expected no source-refresh worker cycle while Publish check is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["publish"].wait(), timeout=5)

        await expect(
            page.get_by_label("Production controls").get_by_text(
                "Browser fixture publish readiness needs policy review."
            )
        ).to_be_visible(timeout=10000)

        revise = page.get_by_role("button", name="Revise")
        await expect(revise).to_be_enabled(timeout=10000)
        await revise.click()
        await page.get_by_label("Revision feedback").fill(
            "Tighten the browser single-flight explanation."
        )
        send_revision = page.get_by_role("button", name="Send revision")
        await expect(send_revision).to_be_enabled(timeout=10000)
        source_message_before_revision_overlap = counts["source_refresh_message"]
        source_cycle_before_revision_overlap = counts["source_refresh_cycle"]
        await send_revision.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["revision_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["source_refresh_message"] == source_message_before_revision_overlap, (
            f"Expected no source-refresh A2A message while Send revision is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_revision_overlap, (
            f"Expected no source-refresh worker cycle while Send revision is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["revision"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        assert counts["revision"] == 1, (
            f"Expected one revision request after rapid Send revision clicks, "
            f"got {counts['revision']}"
        )

        resolve_feedback = page.get_by_role("button", name="Resolve", exact=True).first
        await expect(resolve_feedback).to_be_enabled(timeout=10000)
        source_message_before_feedback_resolve_overlap = counts["source_refresh_message"]
        source_cycle_before_feedback_resolve_overlap = counts["source_refresh_cycle"]
        await resolve_feedback.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["feedback_resolve_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["source_refresh_message"] == source_message_before_feedback_resolve_overlap, (
            f"Expected no source-refresh A2A message while Resolve feedback is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_feedback_resolve_overlap, (
            f"Expected no source-refresh worker cycle while Resolve feedback is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["feedback_resolve"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        assert counts["feedback_resolve"] == 1, (
            f"Expected one feedback resolve request after rapid Resolve clicks, "
            f"got {counts['feedback_resolve']}"
        )
        assert feedback_resolve_payloads == [
            {
                "resolution_notes": "Resolved from the creator app after review.",
                "resolver": "user",
            }
        ], f"Unexpected feedback resolve payloads: {feedback_resolve_payloads}"
        assert counts["retry_authorize"] == 1, (
            f"Expected retry authorization count to remain one at smoke end, "
            f"got {counts['retry_authorize']}"
        )
        assert counts["retry_cycle"] == 1, (
            f"Expected targeted retry worker cycle count to remain one at smoke end, "
            f"got {counts['retry_cycle']}"
        )
        assert counts["source_refresh_cycle"] == expected_source_refresh_cycle_count, (
            f"Expected no late broad/default worker cycle after retry, "
            f"source_refresh_cycle count is {counts['source_refresh_cycle']}"
        )
        assert counts["run_plan_cycle"] == 1, (
            f"Expected no late planned/default worker cycle after retry, "
            f"run_plan_cycle count is {counts['run_plan_cycle']}"
        )

        stop_livekit = page.get_by_role("button", name="Stop LiveKit")
        await expect(stop_livekit).to_be_enabled(timeout=10000)
        local_livekit_stop_before_overlap = counts["local_livekit_stop"]
        source_message_before_livekit_stop_overlap = counts["source_refresh_message"]
        source_cycle_before_livekit_stop_overlap = counts["source_refresh_cycle"]
        await stop_livekit.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["local_livekit_stop_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["local_livekit_stop"] == local_livekit_stop_before_overlap + 1, (
            f"Expected one local LiveKit stop request before overlap assertion, "
            f"got {counts['local_livekit_stop']}"
        )
        assert counts["source_refresh_message"] == source_message_before_livekit_stop_overlap, (
            f"Expected no source-refresh A2A message while Stop LiveKit is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_livekit_stop_overlap, (
            f"Expected no source-refresh worker cycle while Stop LiveKit is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["local_livekit_stop"].wait(), timeout=5)

        resolve_start_livekit = page.locator(
            ".voice-readiness-header > button",
            has_text="Start LiveKit",
        )
        await expect(resolve_start_livekit).to_be_enabled(timeout=10000)
        seen["setup_check_proof"].clear()
        local_livekit_start_before_overlap = counts["local_livekit_start"]
        source_message_before_resolve_livekit_start_overlap = counts["source_refresh_message"]
        source_cycle_before_resolve_livekit_start_overlap = counts["source_refresh_cycle"]
        await resolve_start_livekit.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["local_livekit_start_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["local_livekit_start"] == local_livekit_start_before_overlap + 1, (
            f"Expected one resolver LiveKit start request before overlap assertion, "
            f"got {counts['local_livekit_start']}"
        )
        assert counts["source_refresh_message"] == source_message_before_resolve_livekit_start_overlap, (
            f"Expected no source-refresh A2A message while Resolve next Start LiveKit is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_resolve_livekit_start_overlap, (
            f"Expected no source-refresh worker cycle while Resolve next Start LiveKit is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["local_livekit_start"].wait(), timeout=5)
        await asyncio.wait_for(seen["setup_check_proof"].wait(), timeout=5)
        seen["runtime_preflight"].clear()
        await runtime_preflight.click()
        await asyncio.wait_for(seen["runtime_preflight"].wait(), timeout=5)

        stop_agent = page.get_by_role("button", name="Stop agent")
        await expect(stop_agent).to_be_enabled(timeout=10000)
        voice_agent_stop_before_overlap = counts["voice_agent_stop"]
        source_message_before_agent_stop_overlap = counts["source_refresh_message"]
        source_cycle_before_agent_stop_overlap = counts["source_refresh_cycle"]
        await stop_agent.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["voice_agent_stop_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["voice_agent_stop"] == voice_agent_stop_before_overlap + 1, (
            f"Expected one voice-agent stop request before overlap assertion, "
            f"got {counts['voice_agent_stop']}"
        )
        assert counts["source_refresh_message"] == source_message_before_agent_stop_overlap, (
            f"Expected no source-refresh A2A message while Stop agent is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_agent_stop_overlap, (
            f"Expected no source-refresh worker cycle while Stop agent is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["voice_agent_stop"].wait(), timeout=5)

        resolve_start_agent = page.locator(
            ".voice-readiness-header > button",
            has_text="Start agent",
        )
        await expect(resolve_start_agent).to_be_enabled(timeout=10000)
        seen["setup_check_proof"].clear()
        voice_agent_start_before_overlap = counts["voice_agent_start"]
        source_message_before_resolve_agent_start_overlap = counts["source_refresh_message"]
        source_cycle_before_resolve_agent_start_overlap = counts["source_refresh_cycle"]
        await resolve_start_agent.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["voice_agent_start_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["voice_agent_start"] == voice_agent_start_before_overlap + 1, (
            f"Expected one resolver voice-agent start request before overlap assertion, "
            f"got {counts['voice_agent_start']}"
        )
        assert counts["source_refresh_message"] == source_message_before_resolve_agent_start_overlap, (
            f"Expected no source-refresh A2A message while Resolve next Start agent is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_resolve_agent_start_overlap, (
            f"Expected no source-refresh worker cycle while Resolve next Start agent is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["voice_agent_start"].wait(), timeout=5)
        await asyncio.wait_for(seen["setup_check_proof"].wait(), timeout=5)

        await page.locator(".realtime-voice-grid select").select_option("local_rehearsal")
        start_rehearsal = page.get_by_role("button", name="Start transcript rehearsal")
        await expect(start_rehearsal).to_be_enabled(timeout=10000)
        await start_rehearsal.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["transcript_rehearsal_start"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        assert counts["transcript_rehearsal_start"] == 1, (
            f"Expected one realtime session request after rapid Start transcript rehearsal clicks, "
            f"got {counts['transcript_rehearsal_start']}"
        )
        assert transcript_rehearsal_payloads == [
            {
                "provider": "gemma4_realtime",
                "voice": "af_heart",
                "transport_framework": "local_rehearsal",
                "room_name": None,
                "participant_identity": None,
                "agent_participant_identity": None,
                "context_window_turns": 4,
                "summarize_after_turns": 3,
                "dry_run": True,
                "metadata": {
                    "frontend": "next-app",
                    "selected_voice_provider": "gemma4_realtime",
                },
            }
        ], f"Unexpected transcript rehearsal payloads: {transcript_rehearsal_payloads}"
        route_rehearsal = page.get_by_role("button", name="Route rehearsal turn")
        await expect(route_rehearsal).to_be_enabled(timeout=10000)
        source_message_before_rehearsal_turn_overlap = counts["source_refresh_message"]
        source_cycle_before_rehearsal_turn_overlap = counts["source_refresh_cycle"]
        await route_rehearsal.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["transcript_rehearsal_turn_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["source_refresh_message"] == source_message_before_rehearsal_turn_overlap, (
            f"Expected no source-refresh A2A message while Route rehearsal turn is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_rehearsal_turn_overlap, (
            f"Expected no source-refresh worker cycle while Route rehearsal turn is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["transcript_rehearsal_turn"].wait(), timeout=5)
        source_message_before_voice_followup_overlap = counts["source_refresh_message"]
        source_cycle_before_voice_followup_overlap = counts["source_refresh_cycle"]
        await asyncio.wait_for(seen["voice_followup_cycle_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["source_refresh_message"] == source_message_before_voice_followup_overlap, (
            f"Expected no source-refresh A2A message while voice follow-up continuation is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_voice_followup_overlap, (
            f"Expected no source-refresh worker cycle while voice follow-up continuation is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["voice_followup_cycle"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        assert counts["voice_followup_cycle"] == 1, (
            f"Expected one voice follow-up worker cycle after routing rehearsal turn, "
            f"got {counts['voice_followup_cycle']}"
        )
        assert counts["transcript_rehearsal_turn"] == 1, (
            f"Expected one realtime turn request after rapid Route rehearsal turn clicks, "
            f"got {counts['transcript_rehearsal_turn']}"
        )
        assert transcript_rehearsal_turn_payloads == [
            {
                "speaker": "user",
                "transcript": "Create a source-backed ELI5 reel and Substack angle from this spoken idea.",
                "modality": "voice",
                "topic": "voice rehearsal to source-backed content",
                "target_formats": ["post", "reel", "substack"],
                "route_turn": True,
                "create_realtime_brief_task": True,
                "require_human_feedback": True,
                "interrupted": False,
                "metadata": {
                    "frontend": "next-app",
                    "input_surface": "voice_runtime_transcript_rehearsal",
                    "provider_backed_realtime": False,
                    "rehearsal_only": True,
                },
            }
        ], f"Unexpected transcript rehearsal turn payloads: {transcript_rehearsal_turn_payloads}"

        stop_voice_session = page.locator(".realtime-actions").get_by_role("button", name="Stop")
        await expect(stop_voice_session).to_be_enabled(timeout=10000)
        source_message_before_voice_stop_overlap = counts["source_refresh_message"]
        source_cycle_before_voice_stop_overlap = counts["source_refresh_cycle"]
        await stop_voice_session.evaluate("(button) => { button.click(); button.click(); }")
        await asyncio.wait_for(seen["transcript_rehearsal_stop_started"].wait(), timeout=5)
        await run_web_research.evaluate("(button) => button.click()")
        await page.wait_for_timeout(250)
        assert counts["source_refresh_message"] == source_message_before_voice_stop_overlap, (
            f"Expected no source-refresh A2A message while Stop voice session is in flight, "
            f"got {counts['source_refresh_message']}"
        )
        assert counts["source_refresh_cycle"] == source_cycle_before_voice_stop_overlap, (
            f"Expected no source-refresh worker cycle while Stop voice session is in flight, "
            f"got {counts['source_refresh_cycle']}"
        )
        await asyncio.wait_for(seen["transcript_rehearsal_stop"].wait(), timeout=5)
        await page.wait_for_timeout(250)
        assert counts["transcript_rehearsal_stop"] == 1, (
            f"Expected one transcript rehearsal stop status request, "
            f"got {counts['transcript_rehearsal_stop']}"
        )
        assert transcript_rehearsal_stop_payloads == [
            {
                "status": "ended",
                "reason": "Creator stopped the Gemma/Kokoro live voice session.",
            }
        ], f"Unexpected transcript rehearsal stop payloads: {transcript_rehearsal_stop_payloads}"

        assert not unexpected_api_requests, f"Unexpected API requests: {unexpected_api_requests}"
        assert not page_errors, f"Browser page errors: {page_errors}"
        await browser.close()


async def main() -> None:
    port = free_port()
    env = os.environ.copy()
    env["NEXT_TELEMETRY_DISABLED"] = "1"
    env.pop("NEXT_PUBLIC_API_BASE_URL", None)
    log_file = tempfile.NamedTemporaryFile("w+", delete=False, suffix="-next-dev.log")
    log_path = Path(log_file.name)
    log_file.close()
    with log_path.open("w") as log:
        process = subprocess.Popen(
            ["npm", "run", "dev", "--", "-H", "127.0.0.1", "-p", str(port)],
            cwd=APP_DIR,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    try:
        base_url = wait_for_server(port, log_path)
        await run_browser_assertions(base_url)
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
        try:
            log_path.unlink()
        except OSError:
            pass


if __name__ == "__main__":
    asyncio.run(main())
