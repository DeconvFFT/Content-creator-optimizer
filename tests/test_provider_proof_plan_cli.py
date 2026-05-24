import json
import os
import shlex
import stat
import subprocess
import sys
from argparse import Namespace
from pathlib import Path
from uuid import uuid4

import pytest

from all_about_llms.cli import (
    _provider_proof_plan_payload,
    _provider_proof_record_template_payload,
    _provider_proof_record_validation_payload,
    _provider_proof_workspace_payload,
    _record_provider_proof_record_payload,
)
import all_about_llms.cli as provider_cli

ROOT = Path(__file__).resolve().parents[1]
PROVIDER_PROOF_TEST_RUN_UUID = "123e4567-e89b-12d3-a456-426614174000"


def _no_local_secret_file_env_values() -> dict[str, str | None]:
    return {
        "OPENROUTER_API_KEY_FILE": "__missing_openrouter_api_key_file__",
        "LIVEKIT_API_KEY_FILE": "__missing_livekit_api_key_file__",
        "LIVEKIT_API_SECRET_FILE": "__missing_livekit_api_secret_file__",
        "INSTAGRAM_ACCESS_TOKEN_FILE": "__missing_instagram_access_token_file__",
        "LINKEDIN_ACCESS_TOKEN_FILE": "__missing_linkedin_access_token_file__",
        "X_ACCESS_TOKEN_FILE": "__missing_x_access_token_file__",
        "X_API_KEY_FILE": "__missing_x_api_key_file__",
        "SUBSTACK_API_TOKEN_FILE": "__missing_substack_api_token_file__",
        "LOCAL_PROVIDER_CONFIG_FILE": "__missing_local_provider_config_file__",
    }


def _ready_provider_readiness_preflight_payload():
    return {
        "default_realtime_provider": "openrouter_livekit",
        "selected_web_search_provider": "tavily",
        "providers": [
            {
                "provider_id": "openrouter-livekit",
                "provider_type": "realtime_audio",
                "display_name": "OpenRouter DeepSeek V4 Flash + Kokoro realtime dialogue",
                "status": "ready",
                "selected": True,
                "required_env": [
                    "OPENROUTER_API_KEY",
                    "OPENROUTER_LIVEKIT_URL",
                    "LIVEKIT_API_KEY",
                    "LIVEKIT_API_SECRET",
                ],
                "configured_env": [
                    "OPENROUTER_API_KEY",
                    "OPENROUTER_LIVEKIT_URL",
                    "LIVEKIT_API_KEY",
                    "LIVEKIT_API_SECRET",
                ],
                "missing_env": [],
                "model_ids": [
                    "deepseek/deepseek-v4-flash",
                    "deepseek/deepseek-v4-flash",
                    "hexgrad/Kokoro-82M",
                ],
                "endpoint_configured": True,
                "capabilities": ["openrouter_live_dialogue"],
                "boundary": "LiveKit public transport with OpenRouter DeepSeek reasoning and Kokoro TTS.",
                "notes": "Configured for provider-backed proof.",
                "next_actions": [],
                "secret_files": [],
            }
        ],
        "ready_provider_ids": ["openrouter-livekit"],
        "missing_provider_ids": [],
        "tool_boundary_provider_ids": [],
        "missing_required_env": [],
        "provider_backed_smoke_ready": True,
        "smoke_test_plan": [],
        "demo_walkthrough": [],
        "summary": "Provider-backed smoke is ready.",
    }


def _ready_voice_runtime_preflight_payload():
    checks = [
        "livekit-transport",
        "livekit-agent-participant",
        "voice-agent-backend-event-sink",
        "openrouter-live-dialogue-reasoning",
        "kokoro-tts",
        "rust-voice-edge",
    ]
    return {
        "status": "ready",
        "selected_provider": "openrouter_livekit",
        "transport_framework": "livekit",
        "audio_input_model": "deepseek/deepseek-v4-flash",
        "reasoning_model": "deepseek/deepseek-v4-flash",
        "audio_output_model": "hexgrad/Kokoro-82M",
        "preflight_livekit": True,
        "preflight_edge": True,
        "preflight_agent": True,
        "preflight_gemma": True,
        "preflight_tts": True,
        "checks": [
            {
                "check_id": check_id,
                "label": check_id,
                "status": "ready",
                "required": True,
                "evidence": ["ready"],
                "missing_env": [],
                "next_actions": [],
                "metadata": {},
            }
            for check_id in checks
        ],
        "blockers": [],
        "next_actions": [],
        "summary": "Voice runtime readiness checks are ready.",
    }


def _ready_openrouter_text_turn_voice_runtime_preflight_payload():
    checks = [
        "livekit-transport",
        "livekit-agent-participant",
        "voice-agent-backend-event-sink",
        "openrouter-live-dialogue-reasoning",
        "kokoro-tts",
        "rust-voice-edge",
    ]
    return {
        "status": "ready",
        "selected_provider": "openrouter_livekit",
        "transport_framework": "livekit",
        "audio_input_model": "deepseek/deepseek-v4-flash",
        "reasoning_model": "deepseek/deepseek-v4-flash",
        "audio_output_model": "hexgrad/Kokoro-82M",
        "preflight_livekit": True,
        "preflight_edge": True,
        "preflight_agent": True,
        "preflight_gemma": True,
        "preflight_tts": True,
        "checks": [
            {
                "check_id": check_id,
                "label": check_id,
                "status": "ready",
                "required": True,
                "evidence": ["ready"],
                "missing_env": [],
                "next_actions": [],
                "metadata": (
                    {"voice_reasoning_provider": "openrouter"}
                    if check_id == "openrouter-live-dialogue-reasoning"
                    else {}
                ),
            }
            for check_id in checks
        ],
        "blockers": [],
        "next_actions": [],
        "summary": "OpenRouter text-turn live dialogue checks are ready.",
    }


def _publish_readiness_preflight_payload(
    *,
    status: str = "needs_review",
    ready: bool = False,
    blocking_issues: list[str] | None = None,
    credential_status: str = "configured",
    policy_status: str = "needs_review",
):
    return {
        "run_id": str(uuid4()),
        "status": status,
        "ready": ready,
        "artifact_ids": [str(uuid4())],
        "source_count": 1,
        "claim_count": 1,
        "audit_count": 1,
        "open_feedback_count": 0,
        "blocking_issues": (
            blocking_issues
            if blocking_issues is not None
            else ["publish_channel_policy_review_required"]
        ),
        "recommended_next_actions": [],
        "publish_channel_checks": [
            {
                "platform": "linkedin",
                "credential_envs": ["LINKEDIN_ACCESS_TOKEN"],
                "credential_status": credential_status,
                "policy_status": policy_status,
                "blocking_issues": (
                    []
                    if credential_status == "configured"
                    else ["missing_publish_channel_credentials"]
                ),
                "recommended_next_actions": [],
            }
        ],
        "feedback_gate_opened": False,
        "feedback_id": None,
        "summary": "Publishing readiness awaits explicit policy acknowledgement.",
    }


def _product_run_preflight_payload(run_id: str = PROVIDER_PROOF_TEST_RUN_UUID):
    return {
        "run_id": run_id,
        "goal": "Provider proof run",
        "status": "running",
        "conversation_state": {"input_mode": "voice"},
        "active_agents": ["realtime-conversation-host", "intent-router"],
        "source_record_ids": [],
        "artifact_ids": [],
        "feedback_item_ids": [],
        "created_at": "2026-05-20T12:00:00Z",
        "updated_at": "2026-05-20T12:01:00Z",
    }


def _write_product_run_preflight(preflight_dir: Path, run_id: str = PROVIDER_PROOF_TEST_RUN_UUID):
    (preflight_dir / "product-run.preflight.json").write_text(
        json.dumps(_product_run_preflight_payload(run_id)),
        encoding="utf-8",
    )


def _accepted_provider_proof_record(
    env_example,
    proof: str,
    *,
    checked_at: str = "2026-05-20",
    run_id: str = PROVIDER_PROOF_TEST_RUN_UUID,
):
    template_payload = _provider_proof_record_template_payload(
        Namespace(
            env_example_path=env_example,
            checked_at=checked_at,
            run_id=run_id,
            proof=proof,
        )
    )
    record = dict(template_payload["record"])
    record["validation_timestamp"] = "2026-05-20T12:00:00Z"
    record["proof_outcome"] = "accepted"
    record["secret_redaction_check"] = "passed"
    record["voice_edge_benchmark_status"] = "ready"
    record["realtime_provider"] = "openrouter_livekit"
    record["execute_live_calls"] = True
    if proof == "external-publication-proof":
        record["destination_channel"] = "linkedin"
        record["durable_platform_id_or_url"] = "https://linkedin.com/posts/RUN-ID"
    record["post_capture_validation_results"] = {
        check: "passed" for check in template_payload["post_capture_validation_checks"]
    }
    for field, value in list(record.items()):
        if field in {
            "run_id",
            "checked_at",
            "validation_timestamp",
            "proof_outcome",
            "post_capture_validation_results",
            "secret_redaction_check",
        }:
            continue
        if value == "<true-after-live-call>":
            record[field] = True
        elif proof == "external-publication-proof" and field in {
            "policy_acknowledgement_artifact_id",
            "rollback_or_postcondition_artifact_id",
        }:
            record[field] = f"linkedin-{field.replace('_', '-')}-{run_id}"
        elif isinstance(value, str) and value.startswith("<") and value.endswith(">"):
            record[field] = f"{field}-evidence"
    if "preflight_validation_report_artifact_id" in record:
        preflight_report_path = (
            env_example.parent / f"{proof}-{run_id}-preflight-validation.json"
        )
        preflight_artifact_ids = {
            field: record[field]
            for field in provider_cli._proof_preflight_artifact_id_fields(proof)
        }
        preflight_report_path.write_text(
            json.dumps(
                {
                    "artifact": (
                        "agent-studio-provider-proof-preflight-artifacts-validation"
                    ),
                    "boundary": "no_secret_values_printed_no_state_change",
                    "checked_at": checked_at,
                    "proof": proof,
                    "command_run_id": run_id,
                    "run_id_state": "concrete_run_id",
                    "product_run_id_state": "product_run_uuid",
                    "status": "valid_preflight_artifacts",
                    "state_change_allowed": False,
                    "issue_codes": [],
                    "issues": [],
                    "preflight_artifact_ids": preflight_artifact_ids,
                    "validated_product_run_id": run_id,
                    **(
                        {
                            "validated_runtime_checks": list(
                                provider_cli.VOICE_PROOF_REQUIRED_RUNTIME_CHECKS
                            )
                        }
                        if proof == "provider-backed-live-voice-proof"
                        else {}
                    ),
                    **(
                        {"validated_publish_channels": ["linkedin"]}
                        if proof == "external-publication-proof"
                        else {}
                    ),
                }
            ),
            encoding="utf-8",
        )
        record["preflight_validation_report_artifact_id"] = str(
            preflight_report_path
        )
    if "workspace_validation_report_artifact_id" in record:
        record["workspace_validation_report_artifact_id"] = str(
            _write_valid_workspace_validation_report(
                env_example,
                checked_at=checked_at,
                run_id=run_id,
            )
        )
    return record


def _write_valid_workspace_validation_report(
    env_example,
    *,
    checked_at: str = "2026-05-20",
    run_id: str = PROVIDER_PROOF_TEST_RUN_UUID,
):
    output_dir = env_example.parent / f"{run_id}-proof-workspace"
    report_path = output_dir / "workspace-validation.json"
    workspace_payload = provider_cli._provider_proof_workspace_payload(
        Namespace(
            env_example_path=env_example,
            checked_at=checked_at,
            run_id=run_id,
            output_dir=output_dir,
        )
    )
    assert workspace_payload["status"] in {"workspace_ready", "workspace_exists"}
    validation_payload = provider_cli._provider_proof_workspace_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at=checked_at,
            run_id=run_id,
            output_dir=output_dir,
        )
    )
    assert validation_payload["status"] == "valid_workspace"
    report_path.write_text(json.dumps(validation_payload), encoding="utf-8")
    return report_path


def _failed_provider_proof_record(
    env_example,
    proof: str,
    *,
    checked_at: str = "2026-05-20",
    run_id: str = PROVIDER_PROOF_TEST_RUN_UUID,
):
    record = _accepted_provider_proof_record(
        env_example,
        proof,
        checked_at=checked_at,
        run_id=run_id,
    )
    record["proof_outcome"] = "failed"
    first_check = next(iter(record["post_capture_validation_results"]))
    record["post_capture_validation_results"] = {first_check: "failed"}
    return record


def _closure_review_record(
    env_example,
    proof_audit,
    *,
    decision: str = "approved",
    review_timestamp: str = "2026-05-20T13:00:00Z",
    run_id: str = PROVIDER_PROOF_TEST_RUN_UUID,
):
    template_payload = provider_cli._provider_proof_closure_review_template_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id=run_id,
            audit_target=[proof_audit],
        )
    )
    record = dict(template_payload["template"])
    record["review_timestamp"] = review_timestamp
    record["reviewer"] = "Leibniz"
    record["review_decision"] = decision
    record["review_requirements"] = {
        requirement: "confirmed"
        for requirement in record["review_requirements"]
    }
    if decision == "rejected":
        first_requirement = next(iter(record["review_requirements"]))
        record["review_requirements"][first_requirement] = "rejected"
    record["secret_redaction_check"] = "passed"
    record["review_notes"] = "reviewed without secret material"
    return record


def _operator_packet_markdown_block(markdown: str, proof_id: str) -> str:
    proof_id_line = f"\n- proof_id: `{proof_id}`"
    proof_id_pos = markdown.index(proof_id_line)
    block_start = markdown.rfind("operator_proof_packet:", 0, proof_id_pos)
    assert block_start >= 0
    block_end_candidates = [
        pos
        for pos in [
            markdown.find("\n\nproof_record_schema:", proof_id_pos),
            markdown.find("\n\n- proof_record_schema:", proof_id_pos),
            markdown.find("\n\nproof_record_required_fields:", proof_id_pos),
            markdown.find("\n\n- proof_record_required_fields:", proof_id_pos),
        ]
        if pos >= 0
    ]
    block_end = min(block_end_candidates) if block_end_candidates else len(markdown)
    return markdown[block_start:block_end]


def _operator_packet_blocks(markdown: str) -> dict[str, str]:
    return {
        proof_id: _operator_packet_markdown_block(markdown, proof_id)
        for proof_id in [
            "provider-backed-live-voice-proof",
            "external-publication-proof",
        ]
        if f"\n- proof_id: `{proof_id}`" in markdown
    }


def _assert_operator_packet_capture_commands(markdown: str) -> None:
    blocks = _operator_packet_blocks(markdown)
    voice_block = blocks.get("provider-backed-live-voice-proof")
    if voice_block is not None:
        assert "- proof_capture_commands_after_unblock:" in voice_block
        assert "build-provider-smoke-ledger" in voice_block
        assert (
            "record-provider-proof-record --proof provider-backed-live-voice-proof"
            in voice_block
        )
    publication_block = blocks.get("external-publication-proof")
    if publication_block is not None:
        assert "- proof_capture_commands_after_unblock:" in publication_block
        assert "build-distribution-package" in publication_block
        assert (
            "record-provider-proof-record --proof external-publication-proof"
            in publication_block
        )


def _assert_operator_packet_closeout_refs(markdown: str) -> None:
    for block in _operator_packet_blocks(markdown).values():
        assert "- completion_evidence_ref: `completion-status.json`" in block
        assert "- closure_evidence_refs:" in block
        assert "  - `closure-review-template.json`" in block
        assert "  - `closure-review-status.json`" in block
        assert "  - `blocker-state-update.json`" in block


def _assert_operator_packet_current_gate(markdown: str) -> None:
    for block in _operator_packet_blocks(markdown).values():
        assert "- current_gate:" in block
        current_gate_block = block.split("- current_gate:", 1)[1].split(
            "\n- proof_capture_commands_after_unblock:",
            1,
        )[0]
        assert (
            "  - completion_status: "
            "`blocked_by_latest_failed_proof_record`"
        ) in current_gate_block
        assert (
            "  - closure_review_template_status: "
            "`blocked_by_completion_status`"
        ) in current_gate_block
        assert (
            "  - blocker_state_update_status: "
            "`blocked_by_closure_review_status`"
        ) in current_gate_block
        assert "  - state_change_allowed: `False`" in current_gate_block
        assert (
            "  - completion_next_action: "
            "`capture_validate_record_and_recheck`"
        ) in current_gate_block
        assert "  - completion_next_action_commands:" in current_gate_block
        assert (
            "provider-proof-record-template --proof "
            "provider-backed-live-voice-proof"
        ) not in current_gate_block
        assert (
            "provider-proof-record-template --proof external-publication-proof"
        ) in current_gate_block
        assert (
            current_gate_block.count("provider-proof-completion-status --run-id")
            == 1
        )
        assert "  - goal_completion_claimed: `False`" in current_gate_block
        assert (
            "  - completion_issue_codes: `['latest_proof_record_failed']`"
            in current_gate_block
        )


def _assert_operator_packet_current_state_packets(markdown: str) -> None:
    for block in _operator_packet_blocks(markdown).values():
        assert "- current_state_packets:" in block
        assert "  - current_blocker_matrix: `current-blocker-matrix.json`" in block
        assert "  - current_proof_status: `current-proof-status.md`" in block
        assert (
            "  - operator_unblocker_checklist: "
            "`operator-unblocker-checklist.md`"
        ) in block
        assert "- current_state_packet_commands:" in block
        assert "provider-proof-current-blocker-matrix" in block
        assert "provider-proof-current-status" in block
        assert "provider-proof-operator-unblocker-checklist" in block


def _assert_operator_packet_record_schema(markdown: str) -> None:
    blocks = _operator_packet_blocks(markdown)
    voice_block = blocks.get("provider-backed-live-voice-proof")
    if voice_block is not None:
        assert "- proof_record_schema:" in voice_block
        assert (
            "  - artifact_type: `provider_backed_live_voice_proof_record`"
            in voice_block
        )
        assert "  - state_field: `provider-backed-live-voice-proof`" in voice_block
        assert "- proof_record_required_fields:" in voice_block
        assert "  - `voice_agent_process_start_artifact_id`" in voice_block
    publication_block = blocks.get("external-publication-proof")
    if publication_block is not None:
        assert "- proof_record_schema:" in publication_block
        assert (
            "  - artifact_type: `external_publication_proof_record`"
            in publication_block
        )
        assert "  - state_field: `external-publication-proof`" in publication_block
        assert "- proof_record_required_fields:" in publication_block
        assert "  - `durable_platform_id_or_url`" in publication_block


def _assert_operator_packet_input_readiness(markdown: str) -> None:
    blocks = _operator_packet_blocks(markdown)
    voice_block = blocks.get("provider-backed-live-voice-proof")
    if voice_block is not None:
        assert "\n- operator_input_readiness:" in voice_block
        assert "  - state: `ready_for_credential_snapshot_refresh`" in voice_block
        assert "  - next_action: `refresh_credential_snapshot`" in voice_block
        assert "  - blocked_fields:\n    - `none`" in voice_block
        assert "OPENROUTER_API_KEY_FILE" in voice_block
        assert "OPENROUTER_LIVEKIT_URL" in voice_block
        assert "GEMMA4_MULTIMODAL_ENDPOINT_URL" not in voice_block
        assert "HF_TOKEN_FILE" not in voice_block
    publication_block = blocks.get("external-publication-proof")
    if publication_block is not None:
        assert "\n- operator_input_readiness:" in publication_block
        assert "  - state: `blocked_by_operator_inputs`" in publication_block
        assert (
            "  - next_action: "
            "`supply_linkedin_token_policy_destination_and_rollback_evidence`"
        ) in publication_block
        assert "LINKEDIN_ACCESS_TOKEN_FILE" in publication_block
        assert "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL" in publication_block


def _assert_operator_packet_field_statuses(markdown: str) -> None:
    blocks = _operator_packet_blocks(markdown)
    voice_block = blocks.get("provider-backed-live-voice-proof")
    if voice_block is not None:
        assert "  - field_statuses:" in voice_block
        assert "    - OPENROUTER_API_KEY_FILE:" in voice_block
        assert (
            (
                "      - state: `secret_file_unavailable`" in voice_block
                and (
                    "      - next_action: "
                    "`write_readable_secret_file_and_reference_path`"
                )
                in voice_block
            )
            or (
                "      - state: `configured`" in voice_block
                and "      - issue_code: `none`" in voice_block
                and "      - next_action: `refresh_credential_snapshot`" in voice_block
            )
        )
        assert "      - value_source: `secret_file_path`" in voice_block
        assert "    - OPENROUTER_LIVEKIT_URL:" in voice_block
        assert (
            "      - state: `placeholder`" in voice_block
            or "      - state: `configured`" in voice_block
        )
        assert "      - value_source: `endpoint_url`" in voice_block
    publication_block = blocks.get("external-publication-proof")
    if publication_block is not None:
        assert "  - field_statuses:" in publication_block
        assert "    - PUBLICATION_DURABLE_PLATFORM_ID_OR_URL:" in publication_block
        assert "      - value_source: `external_destination`" in publication_block
        assert (
            "      - contract: "
            "`durable LinkedIn URL or platform id; local substitutes rejected`"
        ) in publication_block


def _assert_operator_packet_field_ownership(markdown: str) -> None:
    blocks = _operator_packet_blocks(markdown)
    voice_block = blocks.get("provider-backed-live-voice-proof")
    if voice_block is not None:
        assert "{'proof_id':" not in voice_block
        assert "  - field_ownership:" in voice_block
        assert "    - OPENROUTER_API_KEY_FILE:" in voice_block
        assert "      - proof_id: `provider-backed-live-voice-proof`" in voice_block
        assert "      - proof_input_role: `provider_credential`" in voice_block
        assert "    - OPENROUTER_LIVEKIT_URL:" in voice_block
        assert "      - proof_input_role: `transport_endpoint`" in voice_block
    publication_block = blocks.get("external-publication-proof")
    if publication_block is not None:
        assert "{'proof_id':" not in publication_block
        assert "  - field_ownership:" in publication_block
        assert "    - PUBLICATION_DURABLE_PLATFORM_ID_OR_URL:" in publication_block
        assert "      - proof_id: `external-publication-proof`" in publication_block
        assert "      - proof_input_role: `publication_destination`" in publication_block


def _assert_operator_packet_readiness_command_lists(markdown: str) -> None:
    for block in _operator_packet_blocks(markdown).values():
        assert "  - next_action_commands:\n" in block
        assert "  - guarded_next_action_commands:\n" in block
        assert "  - next_action_commands: `[" not in block
        assert "  - guarded_next_action_commands: `[" not in block
        assert (
            "    - `uv run all-about-llms-admin "
            "provider-proof-operator-input-readiness "
        ) in block
        assert "    - `uv run all-about-llms-admin blocker-credential-snapshot " in block
        assert "    - `uv run all-about-llms-admin provider-proof-plan " in block
        assert "    - `uv run all-about-llms-admin provider-proof-current-status " in block
        assert "--fail-on-blocked" in block


def _assert_operator_packet_input_contracts(markdown: str) -> None:
    blocks = _operator_packet_blocks(markdown)
    voice_block = blocks.get("provider-backed-live-voice-proof")
    if voice_block is not None:
        assert "\n- operator_input_field_contracts:" in voice_block
        assert (
            "  - OPENROUTER_API_KEY_FILE: "
            "`readable local secret file path; file content is never emitted`"
        ) in voice_block
        assert (
            "  - OPENROUTER_LIVEKIT_URL: "
            "`ws or wss LiveKit URL for OpenRouter-backed realtime dialogue`"
        ) in voice_block
    publication_block = blocks.get("external-publication-proof")
    if publication_block is not None:
        assert "\n- operator_input_field_contracts:" in publication_block
        assert (
            "  - LINKEDIN_ACCESS_TOKEN_FILE: "
            "`readable local secret file path; file content is never emitted`"
        ) in publication_block
        assert (
            "  - PUBLICATION_DURABLE_PLATFORM_ID_OR_URL: "
            "`durable LinkedIn URL or platform id; local substitutes rejected`"
        ) in publication_block
    assert (
        "  - LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID: "
        "`durable non-local policy acknowledgement artifact id or URL`"
    ) in publication_block
    assert (
        "  - PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID: "
        "`durable non-local rollback or postcondition artifact id or URL`"
    ) in publication_block


def test_provider_proof_plan_blocks_runtime_until_credentials_are_configured(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text(
        "\n".join(
                [
                    "OPENROUTER_API_KEY=",
                "OPENROUTER_LIVEKIT_URL=",
                    "OPENROUTER_API_KEY=",
                    "OPENROUTER_LIVEKIT_URL=",
                    "LIVEKIT_API_KEY=",
                    "LIVEKIT_API_SECRET=",
                "INSTAGRAM_ACCESS_TOKEN=",
                "LINKEDIN_ACCESS_TOKEN=",
                "X_ACCESS_TOKEN=",
                "X_API_KEY=",
                "SUBSTACK_API_TOKEN=",
            ]
        )
    )

    payload = _provider_proof_plan_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
        ),
        env_values={},
    )
    serialized = json.dumps(payload)

    assert payload["artifact"] == "agent-studio-provider-proof-plan"
    assert payload["boundary"] == "planning_only_no_live_calls_no_secret_values"
    assert payload["checked_at"] == "2026-05-20"
    expected_record_targets = [
        "social_media_optimiser/01-work-tracking/"
        "Agent Studio Objective Completion Audit.md",
        "social_media_optimiser/wiki/ops/active-codex-context.md",
        "system_design_vault/04-agent-studio-implications/"
        "agent-studio-objective-completion-audit.md",
    ]
    expected_voice_credential_setup = [
        "configure OPENROUTER_API_KEY_FILE or OPENROUTER_API_KEY",
        "configure OPENROUTER_LIVEKIT_URL",
        "configure LIVEKIT_API_KEY_FILE or LIVEKIT_API_KEY",
        "configure LIVEKIT_API_SECRET_FILE or LIVEKIT_API_SECRET",
    ]
    expected_publication_credential_setup = [
        "configure LINKEDIN_ACCESS_TOKEN_FILE or LINKEDIN_ACCESS_TOKEN",
    ]
    expected_operator_sequence = [
        "configure credential_setup_requirements without printing secret values",
        "create or select durable product run UUID with product_run_bootstrap",
        "initialize proof workspace with workspace_commands",
        "validate proof workspace with workspace_validation_commands",
        "run preflight_checks and stop if any readiness gate fails",
        "execute proof commands and capture must_capture evidence",
        "generate, validate, and record the provider proof record",
        "rerun provider-proof-completion-status after both proofs are recorded",
        (
            "complete closure review, then record blocker-state update only "
            "after approved review"
        ),
    ]
    expected_closeout_commands = [
        (
            "uv run all-about-llms-admin provider-proof-completion-status "
            "--run-id 123e4567-e89b-12d3-a456-426614174000"
        ),
        (
            "uv run all-about-llms-admin "
            "provider-proof-closure-review-template --run-id 123e4567-e89b-12d3-a456-426614174000"
        ),
        (
            "uv run all-about-llms-admin "
            "validate-provider-proof-closure-review --run-id 123e4567-e89b-12d3-a456-426614174000 "
            "--record-path <provider-proof-closure-review.json>"
        ),
        (
            "uv run all-about-llms-admin "
            "record-provider-proof-closure-review --run-id 123e4567-e89b-12d3-a456-426614174000 "
            "--record-path <provider-proof-closure-review.json>"
        ),
        (
            "uv run all-about-llms-admin "
            "provider-proof-closure-review-status --run-id 123e4567-e89b-12d3-a456-426614174000"
        ),
        (
            "uv run all-about-llms-admin "
            "record-provider-proof-blocker-state-update --run-id 123e4567-e89b-12d3-a456-426614174000"
        ),
    ]
    expected_workspace_commands = [
        (
            "uv run all-about-llms-admin init-provider-proof-workspace "
            "--run-id 123e4567-e89b-12d3-a456-426614174000 --output-dir "
            "social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000"
        )
    ]
    expected_workspace_validation_commands = [
        (
            "uv run all-about-llms-admin validate-provider-proof-workspace "
            "--run-id 123e4567-e89b-12d3-a456-426614174000 --output-dir "
            "social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000"
        )
    ]
    expected_workspace_validation_report = (
        "social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000/"
        "workspace-validation.json"
    )
    expected_workspace_validation_capture_commands = [
        (
            "uv run all-about-llms-admin validate-provider-proof-workspace "
            "--run-id 123e4567-e89b-12d3-a456-426614174000 --output-dir "
            "social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000 "
            f"> {expected_workspace_validation_report}"
        )
    ]
    expected_workspace_files = [
        (
            "social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000/"
            "provider-backed-live-voice-proof.template.json"
        ),
        (
            "social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000/"
            "external-publication-proof.template.json"
        ),
        (
            "social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000/"
            "operator-inputs.template.env"
        ),
        "social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000/README.md",
    ]
    expected_voice_preflight_validation_requirements = [
        "product-run.preflight.json must match /api/runs/<run-id> response shape and run_id must match command_run_id",
        "provider-readiness.preflight.json must select ready openrouter-livekit",
        "voice-runtime-readiness.preflight.json must be ready for openrouter_livekit",
        (
            "voice runtime preflight flags must include livekit, edge, "
            "agent, OpenRouter reasoning, and tts"
        ),
        (
            "required runtime checks must be present once and ready: livekit-transport, "
            "livekit-agent-participant, voice-agent-backend-event-sink, "
            "openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge"
        ),
    ]
    expected_publication_preflight_validation_requirements = [
        "product-run.preflight.json must match /api/runs/<run-id> response shape and run_id must match command_run_id",
        (
            "publish-readiness.preflight.json status must be ready with "
            "ready=true and no top-level or channel blocking issues, or "
            "needs_review with ready=false and only "
            "publish_channel_policy_review_required"
        ),
        (
            "publish-readiness.preflight.json must include one normalized, "
            "non-empty supported publish_channel_checks entry per channel"
        ),
        "publish channel credentials must be configured",
        (
            "publish channel policy status must be acknowledged when status is "
            "ready; policy-review handoff must include at least one "
            "needs_review channel policy, channel blockers must be empty or "
            "policy-review-only, and acknowledged channels must not carry "
            "policy-review blockers"
        ),
        "publish readiness must not open a feedback gate",
    ]
    expected_voice_credential_setup_commands = [
        "mkdir -p .secrets && chmod 700 .secrets",
        (
            ': "${OPENROUTER_API_KEY:?set OPENROUTER_API_KEY first}" && '
            "umask 077 && printf '%s\\n' \"$OPENROUTER_API_KEY\" > "
            ".secrets/openrouter_api_key && chmod 600 .secrets/openrouter_api_key"
        ),
        (
            ': "${LIVEKIT_API_KEY:?set LIVEKIT_API_KEY first}" && '
            "umask 077 && printf '%s\\n' \"$LIVEKIT_API_KEY\" > "
            ".secrets/livekit_api_key && "
            "chmod 600 .secrets/livekit_api_key"
        ),
        (
            ': "${LIVEKIT_API_SECRET:?set LIVEKIT_API_SECRET first}" && '
            "umask 077 && printf '%s\\n' \"$LIVEKIT_API_SECRET\" > "
            ".secrets/livekit_api_secret && chmod 600 .secrets/livekit_api_secret"
        ),
        (
            ': "${OPENROUTER_LIVEKIT_URL:?set OPENROUTER_LIVEKIT_URL first}" && '
            ': "${LOCAL_PROVIDER_CONFIG_FILE:=.secrets/local_provider_config.json}" '
            "&& export OPENROUTER_LIVEKIT_URL LOCAL_PROVIDER_CONFIG_FILE && "
            "umask 077 && python3 -c 'import json, os, pathlib, sys; "
            "from urllib.parse import urlparse; "
            'names = ("OPENROUTER_LIVEKIT_URL",); '
            "values = {name: os.environ[name].strip() for name in names}; "
            "valid = lambda name, value: (lambda parsed, schemes: "
            "parsed.scheme in schemes and parsed.netloc and not "
            "(parsed.username or parsed.password or parsed.query or "
            'parsed.fragment))(urlparse(value), ({"ws", "wss", "http", '
            '"https"} if name == "OPENROUTER_LIVEKIT_URL" else '
            '{"http", "https"})); '
            "bad = [name for name, value in values.items() if not "
            "valid(name, value)]; "
            "bad and sys.exit(\"Invalid local provider config values: \" + "
            "\",\".join(bad)); "
            'path = pathlib.Path(os.environ["LOCAL_PROVIDER_CONFIG_FILE"]); '
            'ns = {"json": json, "path": path, "sys": sys}; '
            'exec("try:\\n existing = path.read_text(encoding=\\"utf-8\\") '
            'if path.exists() else \\"{}\\"\\n raw = json.loads(existing)\\n'
            'except Exception:\\n '
            'sys.exit(\\"Invalid existing LOCAL_PROVIDER_CONFIG_FILE\\")", ns); '
            'raw = ns["raw"]; '
            'isinstance(raw, dict) or sys.exit("Invalid existing '
            'LOCAL_PROVIDER_CONFIG_FILE"); '
            "managed = set(names); "
            "merged = {k: v for k, v in raw.items() if k not in managed}; "
            "merged.update(values); "
            "path.parent.mkdir(parents=True, exist_ok=True); "
            "path.write_text(json.dumps(merged, indent=2, "
            'sort_keys=True) + "\\n", encoding="utf-8")' "'" " && "
            'chmod 600 "$LOCAL_PROVIDER_CONFIG_FILE"'
        ),
    ]
    expected_publication_credential_setup_commands = [
        "mkdir -p .secrets && chmod 700 .secrets",
        (
            ': "${LINKEDIN_ACCESS_TOKEN:?set LINKEDIN_ACCESS_TOKEN first}" && '
            "umask 077 && printf '%s\\n' \"$LINKEDIN_ACCESS_TOKEN\" > "
            ".secrets/linkedin_access_token && "
            "chmod 600 .secrets/linkedin_access_token"
        ),
    ]
    recheck_command = (
        "uv run all-about-llms-admin provider-proof-plan --run-id 123e4567-e89b-12d3-a456-426614174000"
    )
    expected_voice_blocked_attempt_gate = {
        "state": "blocked_by_credentials",
        "can_run_preflight_capture": False,
        "can_run_proof_commands": False,
        "blocked_by": ["blocked_by_placeholder_only_configuration"],
        "next_action": "configure_credentials",
        "next_action_commands": [
            *expected_voice_credential_setup_commands,
            recheck_command,
        ],
        "proof_commands_allowed_after": [
            "proof workspace initialized",
            "proof workspace validation status is valid_workspace",
            "preflight output files captured",
            "preflight validation report status is valid_preflight_artifacts",
            "proof-specific human confirmations are complete",
        ],
        "state_change_allowed": False,
    }
    expected_publication_blocked_attempt_gate = {
        **expected_voice_blocked_attempt_gate,
        "next_action_commands": [
            *expected_publication_credential_setup_commands,
            recheck_command,
        ],
    }
    expected_voice_preflight_validation_report = (
        "social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000/"
        "provider-backed-live-voice-proof.preflight-validation.json"
    )
    voice = payload["proofs"]["provider-backed-live-voice-proof"]
    assert voice["status"] == "blocked_by_credentials"
    assert voice["credential_state"] == "blocked_by_placeholder_only_configuration"
    assert voice["credential_setup_requirements"] == expected_voice_credential_setup
    assert voice["credential_setup_commands"] == (
        expected_voice_credential_setup_commands
    )
    assert voice["operator_sequence"] == expected_operator_sequence
    assert voice["workspace_commands"] == expected_workspace_commands
    assert voice["workspace_validation_commands"] == (
        expected_workspace_validation_commands
    )
    assert voice["workspace_validation_report_files"] == [
        expected_workspace_validation_report
    ]
    assert voice["workspace_validation_capture_commands"] == (
        expected_workspace_validation_capture_commands
    )
    assert voice["workspace_expected_files"] == expected_workspace_files
    assert voice["attempt_gate"] == expected_voice_blocked_attempt_gate
    assert voice["runtime_proof_required"] is True
    assert voice["command_run_id"] == "123e4567-e89b-12d3-a456-426614174000"
    assert voice["record_proof_in"] == expected_record_targets
    assert voice["template_commands"] == [
        (
            "uv run all-about-llms-admin provider-proof-record-template "
            "--proof provider-backed-live-voice-proof --run-id 123e4567-e89b-12d3-a456-426614174000"
        )
    ]
    assert voice["record_commands"] == [
        (
            "uv run all-about-llms-admin record-provider-proof-record "
            "--proof provider-backed-live-voice-proof --run-id 123e4567-e89b-12d3-a456-426614174000 "
            "--record-path <provider-proof-record.json> "
            "--preflight-validation-path "
            f"{expected_voice_preflight_validation_report} "
            "--workspace-validation-path "
            f"{expected_workspace_validation_report}"
        )
    ]
    assert voice["completion_status_commands"] == [
        (
            "uv run all-about-llms-admin provider-proof-completion-status "
            "--run-id 123e4567-e89b-12d3-a456-426614174000"
        )
    ]
    assert voice["closeout_commands"] == expected_closeout_commands
    assert voice["preflight_checks"] == [
        "GET /api/runs/123e4567-e89b-12d3-a456-426614174000",
        "GET /api/provider-readiness",
        (
            "GET /api/voice-runtime-readiness?"
            "preflight_gemma=true&preflight_tts=true&"
            "preflight_livekit=true&preflight_edge=true&preflight_agent=true"
        ),
        "confirm selected realtime provider is openrouter_livekit before live smoke",
    ]
    assert voice["preflight_commands"] == [
        "curl -sS http://127.0.0.1:8000/api/runs/123e4567-e89b-12d3-a456-426614174000",
        "curl -sS http://127.0.0.1:8000/api/provider-readiness",
        (
            "curl -sS 'http://127.0.0.1:8000/api/voice-runtime-readiness?"
            "preflight_gemma=true&preflight_tts=true&"
            "preflight_livekit=true&preflight_edge=true&preflight_agent=true'"
        ),
    ]
    assert voice["preflight_output_files"] == [
        (
            "social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000/"
            "product-run.preflight.json"
        ),
        (
            "social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000/"
            "provider-readiness.preflight.json"
        ),
        (
            "social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000/"
            "voice-runtime-readiness.preflight.json"
        ),
    ]
    assert voice["preflight_capture_commands"] == [
        (
            "curl -sS -o social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000/"
            "product-run.preflight.json "
            "http://127.0.0.1:8000/api/runs/123e4567-e89b-12d3-a456-426614174000"
        ),
        (
            "curl -sS -o social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000/"
            "provider-readiness.preflight.json "
            "http://127.0.0.1:8000/api/provider-readiness"
        ),
        (
            "curl -sS -o social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000/"
            "voice-runtime-readiness.preflight.json "
            "'http://127.0.0.1:8000/api/voice-runtime-readiness?"
            "preflight_gemma=true&preflight_tts=true&"
            "preflight_livekit=true&preflight_edge=true&preflight_agent=true'"
        ),
    ]
    assert voice["preflight_artifact_id_fields"] == [
        "product_run_preflight_artifact_id",
        "provider_readiness_preflight_artifact_id",
        "voice_runtime_readiness_preflight_artifact_id",
    ]
    assert voice["preflight_validation_commands"] == [
        (
            "uv run all-about-llms-admin "
            "validate-provider-proof-preflight-artifacts "
            "--proof provider-backed-live-voice-proof --run-id 123e4567-e89b-12d3-a456-426614174000 "
            "--preflight-dir social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000"
        )
    ]
    assert voice["preflight_validation_report_files"] == [
        expected_voice_preflight_validation_report
    ]
    assert (
        voice["preflight_validation_requirements"]
        == expected_voice_preflight_validation_requirements
    )
    assert voice["preflight_validation_capture_commands"] == [
        (
            "uv run all-about-llms-admin "
            "validate-provider-proof-preflight-artifacts "
            "--proof provider-backed-live-voice-proof --run-id 123e4567-e89b-12d3-a456-426614174000 "
            "--preflight-dir social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000 "
            f"> {expected_voice_preflight_validation_report}"
        )
    ]
    assert voice["proof_capture_commands_after_unblock"] == (
        provider_cli._provider_proof_capture_commands_after_unblock(
            "provider-backed-live-voice-proof",
            "123e4567-e89b-12d3-a456-426614174000",
            Path(
                "social_media_optimiser/output/provider-proof/"
                "123e4567-e89b-12d3-a456-426614174000"
            ),
        )
    )
    voice_after_unblock_commands = voice["proof_capture_commands_after_unblock"]
    assert any(
        "build-runtime-health-ledger --run-id 123e4567-e89b-12d3-a456-426614174000"
        in command
        for command in voice_after_unblock_commands
    )
    assert any(
        "build-provider-smoke-ledger --run-id 123e4567-e89b-12d3-a456-426614174000 --live --realtime-provider openrouter_livekit --skip-gemma --skip-web-search"
        in command
        for command in voice_after_unblock_commands
    )
    livekit_capture_command = (
        "uv run all-about-llms-admin capture-livekit-voice-timing-proof "
        "--run-id 123e4567-e89b-12d3-a456-426614174000 "
        "> social_media_optimiser/output/provider-proof/"
        "123e4567-e89b-12d3-a456-426614174000/"
        "livekit-voice-timing-capture.json"
    )
    assert livekit_capture_command in voice_after_unblock_commands
    assert all(
        "--realtime-provider gemma4_realtime" not in command
        for command in voice_after_unblock_commands
    )
    assert any(
        "build-realtime-voice-timing-ledger --run-id 123e4567-e89b-12d3-a456-426614174000"
        in command
        for command in voice_after_unblock_commands
    )
    managed_voice_agent_start_command = (
        "curl -sS -X POST -o "
        "social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000/"
        "voice-agent-process.start.json "
        "http://127.0.0.1:8000/api/voice-agent-process/start "
        "-H 'Content-Type: application/json' "
        "--data '{\"dev\":true,\"unregistered\":false,\"force_restart\":false}'"
    )
    generic_voice_agent_start_command = (
        "curl -sS -X POST http://127.0.0.1:8000/api/voice-agent-process/start "
        "-H 'Content-Type: application/json' "
        "--data '{\"dev\":true,\"unregistered\":false,\"force_restart\":false}'"
    )
    assert managed_voice_agent_start_command in voice_after_unblock_commands
    assert generic_voice_agent_start_command not in voice_after_unblock_commands
    assert all(
        command != "uv run all-about-llms-admin run-voice-agent --dev"
        for command in voice_after_unblock_commands
    )
    assert voice_after_unblock_commands.index(
        managed_voice_agent_start_command
    ) < next(
        index
        for index, command in enumerate(voice_after_unblock_commands)
        if "build-provider-smoke-ledger" in command
    )
    assert next(
        index
        for index, command in enumerate(voice_after_unblock_commands)
        if "build-provider-smoke-ledger" in command
    ) < voice_after_unblock_commands.index(livekit_capture_command) < next(
        index
        for index, command in enumerate(voice_after_unblock_commands)
        if "build-realtime-voice-timing-ledger" in command
    )
    assert voice_after_unblock_commands.index(
        "uv run all-about-llms-admin "
        "provider-proof-record-template --proof provider-backed-live-voice-proof "
        "--run-id 123e4567-e89b-12d3-a456-426614174000"
    ) > next(
        index
        for index, command in enumerate(voice_after_unblock_commands)
        if "build-provider-smoke-ledger" in command
    )
    assert voice["rejected_substitutes"] == [
        ".env.example placeholders",
        "OpenRouter credential existence without a live dialogue turn",
        "transcript rehearsal or local-only dry run",
        "credential existence without live calls",
    ]
    assert voice["proof_linkage_requirements"] == [
        (
            "same run_id across runtime_health_ledger, provider_smoke_ledger, "
            "livekit_voice_timing_capture, and realtime_voice_timing_ledger"
        ),
        "voice_agent_process_start artifact captured before live smoke",
        (
            "same realtime_session_id or LiveKit room/session id across "
            "smoke, headless capture, timing, and participant evidence"
        ),
        (
            "required runtime checks appear in the preflight validation "
            "report's validated_runtime_checks"
        ),
        "runtime configuration snapshot recorded with the same checked_at",
    ]
    assert voice["post_capture_validation_checks"] == [
        (
            "runtime_health_ledger voice-edge benchmark is ready and records "
            "p50/p95/max latency plus false-positive, missed-speech-start, "
            "and missed-cancellation counts"
        ),
        "provider_smoke_ledger execute_live_calls is true",
        "provider_smoke_ledger realtime_provider is openrouter_livekit",
        (
            "provider_smoke_ledger run_id equals realtime_voice_timing_ledger "
            "run_id and command_run_id"
        ),
        (
            "realtime_session_id or LiveKit room/session id matches across "
            "smoke, timing, and participant evidence"
        ),
        "first text or audio timing plus interruption evidence are present",
        "captured proof artifacts contain no token, API key, or secret values",
    ]
    assert voice["failure_recording_requirements"] == [
        "record failing run_id and checked_at without secret values",
        (
            "record the failed preflight, runtime health, provider smoke, "
            "headless LiveKit capture, timing, managed voice-agent start, LiveKit, or "
            "participant-evidence step"
        ),
        (
            "record provider endpoint/account identifiers only after redacting "
            "tokens, API keys, and secrets"
        ),
        (
            "keep provider-backed-live-voice-proof blocked until a later "
            "same-session proof passes validation"
        ),
        "open or update the follow-up task with the failed validation check",
    ]
    assert voice["success_recording_requirements"] == [
        "record passing run_id, checked_at, and validation timestamp",
        (
            "record voice_agent_process_start, runtime_health_ledger, "
            "provider_smoke_ledger, livekit_voice_timing_capture, "
            "realtime_voice_timing_ledger, LiveKit room/session id, and "
            "participant evidence artifact ids"
        ),
        (
            "record every post_capture_validation_check as passed before "
            "changing blocker state"
        ),
        (
            "update provider-backed-live-voice-proof status only after "
            "same-session validation passes"
        ),
        "close or link the follow-up task to the accepted proof record",
    ]
    assert voice["proof_artifact_schema"] == {
        "artifact_type": "provider_backed_live_voice_proof_record",
        "allowed_outcomes": ["accepted", "failed"],
        "state_field": "provider-backed-live-voice-proof",
        "required_fields": [
            "run_id",
            "checked_at",
            "validation_timestamp",
            "proof_outcome",
            "workspace_validation_report_artifact_id",
            "preflight_validation_report_artifact_id",
            "product_run_preflight_artifact_id",
            "provider_readiness_preflight_artifact_id",
            "voice_runtime_readiness_preflight_artifact_id",
            "voice_agent_process_start_artifact_id",
            "runtime_health_ledger_artifact_id",
            "voice_edge_benchmark_status",
            "provider_smoke_ledger_artifact_id",
            "livekit_voice_timing_capture_artifact_id",
            "realtime_voice_timing_ledger_artifact_id",
            "realtime_provider",
            "execute_live_calls",
            "realtime_session_id_or_livekit_room",
            "participant_identity",
            "runtime_configuration_snapshot_id",
            "post_capture_validation_results",
            "secret_redaction_check",
        ],
    }
    managed_voice_agent_command = (
        "curl -sS -X POST http://127.0.0.1:8000/api/voice-agent-process/start "
        "-H 'Content-Type: application/json' "
        "--data '{\"dev\":true,\"unregistered\":false,\"force_restart\":false}'"
    )
    assert managed_voice_agent_command in voice["commands"]
    assert "uv run all-about-llms-admin run-voice-agent --dev" not in voice[
        "commands"
    ]
    assert (
        "uv run all-about-llms-admin build-runtime-health-ledger "
        "--run-id 123e4567-e89b-12d3-a456-426614174000"
    ) in voice["commands"]
    assert (
        "uv run all-about-llms-admin build-provider-smoke-ledger "
        "--run-id 123e4567-e89b-12d3-a456-426614174000 --live --realtime-provider openrouter_livekit --skip-gemma --skip-web-search"
    ) in voice["commands"]
    assert (
        "runtime_health_ledger with voice-edge-local-benchmark status ready"
        in voice["must_capture"]
    )
    assert "runtime_configuration_present_unverified" in voice["unblock_when"]
    assert (
        "same-run runtime_health_ledger voice-edge benchmark is ready"
        in voice["unblock_when"]
    )
    publication = payload["proofs"]["external-publication-proof"]
    expected_publication_preflight_validation_report = (
        "social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000/"
        "external-publication-proof.preflight-validation.json"
    )
    assert publication["status"] == "blocked_by_credentials"
    assert publication["command_run_id"] == "123e4567-e89b-12d3-a456-426614174000"
    assert (
        publication["credential_setup_requirements"]
        == expected_publication_credential_setup
    )
    assert publication["credential_setup_commands"] == (
        expected_publication_credential_setup_commands
    )
    assert publication["operator_sequence"] == expected_operator_sequence
    assert publication["workspace_commands"] == expected_workspace_commands
    assert publication["workspace_validation_commands"] == (
        expected_workspace_validation_commands
    )
    assert publication["workspace_validation_report_files"] == [
        expected_workspace_validation_report
    ]
    assert publication["workspace_validation_capture_commands"] == (
        expected_workspace_validation_capture_commands
    )
    assert publication["workspace_expected_files"] == expected_workspace_files
    assert publication["attempt_gate"] == expected_publication_blocked_attempt_gate
    assert publication["record_proof_in"] == expected_record_targets
    assert publication["template_commands"] == [
        (
            "uv run all-about-llms-admin provider-proof-record-template "
            "--proof external-publication-proof --run-id 123e4567-e89b-12d3-a456-426614174000"
        )
    ]
    assert publication["record_commands"] == [
        (
            "uv run all-about-llms-admin record-provider-proof-record "
            "--proof external-publication-proof --run-id 123e4567-e89b-12d3-a456-426614174000 "
            "--record-path <provider-proof-record.json> "
            "--preflight-validation-path "
            f"{expected_publication_preflight_validation_report} "
            "--workspace-validation-path "
            f"{expected_workspace_validation_report}"
        )
    ]
    assert publication["completion_status_commands"] == [
        (
            "uv run all-about-llms-admin provider-proof-completion-status "
            "--run-id 123e4567-e89b-12d3-a456-426614174000"
        )
    ]
    assert publication["closeout_commands"] == expected_closeout_commands
    assert publication["preflight_checks"] == [
        "GET /api/runs/123e4567-e89b-12d3-a456-426614174000",
        "POST /api/runs/123e4567-e89b-12d3-a456-426614174000/publish-readiness",
        "confirm human approval and channel policy acknowledgement",
        "confirm disclosure-bearing artifact snapshot before destination proof",
    ]
    assert publication["preflight_commands"] == [
        "curl -sS http://127.0.0.1:8000/api/runs/123e4567-e89b-12d3-a456-426614174000",
        (
            "curl -sS -X POST "
            "http://127.0.0.1:8000/api/runs/123e4567-e89b-12d3-a456-426614174000/publish-readiness "
            "-H 'Content-Type: application/json' "
            "--data "
            "'{\"open_feedback_gate\":false,"
            "\"mark_run_completed_if_ready\":false,"
            "\"check_publish_channel_readiness\":true,"
            "\"acknowledge_publish_channel_policy\":false}'"
        )
    ]
    assert publication["preflight_output_files"] == [
        (
            "social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000/"
            "product-run.preflight.json"
        ),
        (
            "social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000/"
            "publish-readiness.preflight.json"
        )
    ]
    assert publication["preflight_capture_commands"] == [
        (
            "curl -sS -o "
            "social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000/"
            "product-run.preflight.json "
            "http://127.0.0.1:8000/api/runs/123e4567-e89b-12d3-a456-426614174000"
        ),
        (
            "curl -sS -X POST -o "
            "social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000/"
            "publish-readiness.preflight.json "
            "http://127.0.0.1:8000/api/runs/123e4567-e89b-12d3-a456-426614174000/publish-readiness "
            "-H 'Content-Type: application/json' "
            "--data "
            "'{\"open_feedback_gate\":false,"
            "\"mark_run_completed_if_ready\":false,"
            "\"check_publish_channel_readiness\":true,"
            "\"acknowledge_publish_channel_policy\":false}'"
        )
    ]
    assert publication["preflight_artifact_id_fields"] == [
        "product_run_preflight_artifact_id",
        "publish_readiness_preflight_artifact_id",
    ]
    assert publication["preflight_validation_commands"] == [
        (
            "uv run all-about-llms-admin "
            "validate-provider-proof-preflight-artifacts "
            "--proof external-publication-proof --run-id 123e4567-e89b-12d3-a456-426614174000 "
            "--preflight-dir social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000"
        )
    ]
    assert publication["preflight_validation_report_files"] == [
        expected_publication_preflight_validation_report
    ]
    assert (
        publication["preflight_validation_requirements"]
        == expected_publication_preflight_validation_requirements
    )
    assert publication["preflight_validation_capture_commands"] == [
        (
            "uv run all-about-llms-admin "
            "validate-provider-proof-preflight-artifacts "
            "--proof external-publication-proof --run-id 123e4567-e89b-12d3-a456-426614174000 "
            "--preflight-dir social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000 "
            f"> {expected_publication_preflight_validation_report}"
        )
    ]
    assert publication["proof_capture_commands_after_unblock"] == (
        provider_cli._provider_proof_capture_commands_after_unblock(
            "external-publication-proof",
            "123e4567-e89b-12d3-a456-426614174000",
            Path(
                "social_media_optimiser/output/provider-proof/"
                "123e4567-e89b-12d3-a456-426614174000"
            ),
        )
    )
    publication_capture_after_unblock = publication[
        "proof_capture_commands_after_unblock"
    ][1]
    assert '"acknowledge_publish_channel_policy":true' in (
        publication_capture_after_unblock
    )
    assert '"acknowledge_publish_channel_policy":false' not in (
        publication_capture_after_unblock
    )
    distribution_package_capture = (
        "uv run all-about-llms-admin build-distribution-package "
        "--run-id 123e4567-e89b-12d3-a456-426614174000 "
        "> social_media_optimiser/output/provider-proof/"
        "123e4567-e89b-12d3-a456-426614174000/distribution-package.json"
    )
    assert distribution_package_capture in publication[
        "proof_capture_commands_after_unblock"
    ]
    assert publication["proof_capture_commands_after_unblock"].index(
        "uv run all-about-llms-admin "
        "provider-proof-record-template --proof external-publication-proof "
        "--run-id 123e4567-e89b-12d3-a456-426614174000"
    ) > publication["proof_capture_commands_after_unblock"].index(
        distribution_package_capture
    )
    assert publication["rejected_substitutes"] == [
        "non-live channel smoke",
        "generic policy acknowledgement",
        "credential existence without destination proof",
        "local draft preview or generated artifact only",
    ]
    assert publication["proof_linkage_requirements"] == [
        (
            "same run_id across publish-readiness, distribution package, "
            "approved artifact, and destination proof"
        ),
        (
            "destination_channel is linkedin and the preflight validation "
            "report's validated_publish_channels is exactly linkedin"
        ),
        "durable platform ID or URL matches the approved destination/channel",
        (
            "rollback or postcondition monitoring record references the same "
            "platform ID or URL"
        ),
    ]
    assert publication["post_capture_validation_checks"] == [
        (
            "publish-readiness, distribution package, approved artifact, and "
            "destination proof all reference command_run_id"
        ),
        (
            "destination_channel is linkedin and the preflight validation "
            "report's validated_publish_channels is exactly linkedin; durable "
            "URL is a LinkedIn destination"
        ),
        (
            "approved artifact snapshot has disclosure, visibility, audience, "
            "and schedule"
        ),
        (
            "platform API response or approved manual proof contains durable "
            "platform ID or URL"
        ),
        (
            "durable platform ID or URL matches rollback or postcondition "
            "monitoring record"
        ),
        "captured proof artifacts contain no token, API key, or secret values",
    ]
    assert publication["failure_recording_requirements"] == [
        "record failing run_id and checked_at without secret values",
        (
            "record the failed publish-readiness, policy, approval, destination, "
            "or rollback/postcondition step"
        ),
        (
            "record platform response class, destination channel, and account "
            "identifier only after redacting tokens, API keys, and secrets"
        ),
        (
            "keep external-publication-proof blocked until a later exact-"
            "destination proof passes validation"
        ),
        "open or update the follow-up task with the failed validation check",
    ]
    assert publication["success_recording_requirements"] == [
        "record passing run_id, checked_at, and validation timestamp",
        (
            "record publish-readiness, distribution package, approved artifact, "
            "destination proof, and rollback/postcondition artifact ids"
        ),
        (
            "record every post_capture_validation_check as passed before "
            "changing blocker state"
        ),
        (
            "update external-publication-proof status only after exact-"
            "destination validation passes"
        ),
        "close or link the follow-up task to the accepted proof record",
    ]
    assert publication["proof_artifact_schema"] == {
        "artifact_type": "external_publication_proof_record",
        "allowed_outcomes": ["accepted", "failed"],
        "state_field": "external-publication-proof",
        "required_fields": [
            "run_id",
            "checked_at",
            "validation_timestamp",
            "proof_outcome",
            "workspace_validation_report_artifact_id",
            "preflight_validation_report_artifact_id",
            "product_run_preflight_artifact_id",
            "publish_readiness_preflight_artifact_id",
            "publish_readiness_artifact_id",
            "distribution_package_artifact_id",
            "approved_artifact_snapshot_id",
            "destination_channel",
            "durable_platform_id_or_url",
            "policy_acknowledgement_artifact_id",
            "rollback_or_postcondition_artifact_id",
            "post_capture_validation_results",
            "secret_redaction_check",
        ],
    }
    assert "platform API response proof" in publication["must_capture"]
    assert "channel policy acknowledgement" in publication["must_capture"]
    assert "disclosure-bearing approved artifact snapshot" in publication[
        "must_capture"
    ]
    assert "run-autonomous-pass --provider-smoke-live" not in " ".join(
        publication["commands"]
    )
    assert any(
        "publish the approved artifact through the exact platform API" in step
        for step in publication["manual_capture_steps"]
    )
    assert "hf_secret" not in serialized
    assert "livekit_secret" not in serialized


def test_provider_proof_plan_exposes_no_secret_credential_setup_commands_when_blocked(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=",
                "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key",
                "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret",
                "INSTAGRAM_ACCESS_TOKEN_FILE=.secrets/instagram_access_token",
                "LINKEDIN_ACCESS_TOKEN_FILE=.secrets/linkedin_access_token",
                "X_ACCESS_TOKEN_FILE=.secrets/x_access_token",
                "X_API_KEY_FILE=.secrets/x_api_key",
                "SUBSTACK_API_TOKEN_FILE=.secrets/substack_api_token",
            ]
        )
    )

    payload = _provider_proof_plan_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
        ),
        env_values={},
    )
    serialized = json.dumps(payload)

    expected_voice_setup_commands = (
        provider_cli.PROVIDER_PROOF_CREDENTIAL_SETUP_COMMANDS[
            "provider-backed-live-voice-proof"
        ]
    )
    expected_publication_setup_commands = (
        provider_cli.PROVIDER_PROOF_CREDENTIAL_SETUP_COMMANDS[
            "external-publication-proof"
        ]
    )
    recheck_command = (
        "uv run all-about-llms-admin provider-proof-plan --run-id 123e4567-e89b-12d3-a456-426614174000"
    )

    voice = payload["proofs"]["provider-backed-live-voice-proof"]
    assert voice["credential_setup_commands"] == expected_voice_setup_commands
    assert voice["credential_setup_commands"][0] == (
        "mkdir -p .secrets && chmod 700 .secrets"
    )
    assert voice["attempt_gate"]["next_action_commands"] == [
        *expected_voice_setup_commands,
        recheck_command,
    ]

    publication = payload["proofs"]["external-publication-proof"]
    assert (
        publication["credential_setup_commands"]
        == expected_publication_setup_commands
    )
    assert publication["credential_setup_commands"][0] == (
        "mkdir -p .secrets && chmod 700 .secrets"
    )
    secret_file_commands = [
        command
        for command in (
            voice["credential_setup_commands"]
            + publication["credential_setup_commands"]
        )
        if ".secrets/" in command
    ]
    assert secret_file_commands
    assert all("chmod 600" in command for command in secret_file_commands)
    assert all("umask 077 &&" in command for command in secret_file_commands)
    assert publication["attempt_gate"]["next_action_commands"] == [
        *expected_publication_setup_commands,
        recheck_command,
    ]
    assert all(
        legacy_key not in " ".join(publication["credential_setup_commands"])
        for legacy_key in (
            "INSTAGRAM_ACCESS_TOKEN",
            "X_ACCESS_TOKEN",
            "X_API_KEY",
            "SUBSTACK_API_TOKEN",
        )
    )
    assert "hf_secret" not in serialized
    assert "livekit_secret" not in serialized
    assert "sk-ABCDEFGHIJKLMNOPQRST" not in serialized


def test_provider_proof_plan_setup_commands_write_local_provider_config_without_echoing_values(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=",
                "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key",
                "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret",
                "LOCAL_PROVIDER_CONFIG_FILE=.secrets/local_provider_config.json",
            ]
        )
    )
    payload = _provider_proof_plan_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="RUN-ID",
        ),
        env_values={},
    )
    voice_commands = payload["proofs"]["provider-backed-live-voice-proof"][
        "credential_setup_commands"
    ]
    setup_values = {
        "OPENROUTER_API_KEY": "openrouter_setup_command_secret_must_not_echo",
        "LIVEKIT_API_KEY": "livekit_setup_key_must_not_echo",
        "LIVEKIT_API_SECRET": "livekit_setup_secret_must_not_echo",
        "OPENROUTER_LIVEKIT_URL": "wss://livekit.setup.example",
        "LOCAL_PROVIDER_CONFIG_FILE": ".secrets/local_provider_config.json",
    }

    result = subprocess.run(
        ["/bin/sh", "-c", "\n".join(voice_commands)],
        cwd=tmp_path,
        env={"PATH": os.environ.get("PATH", ""), **setup_values},
        check=True,
        capture_output=True,
        text=True,
    )

    config_path = tmp_path / ".secrets/local_provider_config.json"
    assert json.loads(config_path.read_text(encoding="utf-8")) == {
        "OPENROUTER_LIVEKIT_URL": setup_values["OPENROUTER_LIVEKIT_URL"],
    }
    assert stat.S_IMODE(config_path.stat().st_mode) == 0o600
    output = result.stdout + result.stderr
    for value in setup_values.values():
        assert value not in output


def test_provider_proof_plan_setup_commands_reject_invalid_local_provider_config_without_overwrite(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=",
                "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key",
                "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret",
                "LOCAL_PROVIDER_CONFIG_FILE=.secrets/local_provider_config.json",
            ]
        )
    )
    config_path = tmp_path / ".secrets/local_provider_config.json"
    config_path.parent.mkdir()
    existing_config = '{"existing": "keep"}\n'
    config_path.write_text(existing_config, encoding="utf-8")
    payload = _provider_proof_plan_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="RUN-ID",
        ),
        env_values={},
    )
    voice_commands = payload["proofs"]["provider-backed-live-voice-proof"][
        "credential_setup_commands"
    ]
    setup_values = {
        "OPENROUTER_API_KEY": "openrouter_invalid_setup_secret_must_not_echo",
        "LIVEKIT_API_KEY": "livekit_invalid_key_must_not_echo",
        "LIVEKIT_API_SECRET": "livekit_invalid_secret_must_not_echo",
        "OPENROUTER_LIVEKIT_URL": "wss://user:pass@livekit.invalid.example",
        "LOCAL_PROVIDER_CONFIG_FILE": ".secrets/local_provider_config.json",
    }

    result = subprocess.run(
        ["/bin/sh", "-c", "\n".join(voice_commands)],
        cwd=tmp_path,
        env={"PATH": os.environ.get("PATH", ""), **setup_values},
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert config_path.read_text(encoding="utf-8") == existing_config
    output = result.stdout + result.stderr
    assert "Invalid local provider config values" in output
    for value in setup_values.values():
        assert value not in output


def test_provider_proof_plan_setup_commands_preserve_unmanaged_local_provider_config(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=",
                "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key",
                "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret",
                "LOCAL_PROVIDER_CONFIG_FILE=.secrets/local_provider_config.json",
            ]
        )
    )
    config_path = tmp_path / ".secrets/local_provider_config.json"
    config_path.parent.mkdir()
    config_path.write_text(
        json.dumps(
            {
                "CUSTOM_LOCAL_PROVIDER_NOTE": "keep-me",
                "OPENROUTER_LIVEKIT_URL": "wss://old.example",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    payload = _provider_proof_plan_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="RUN-ID",
        ),
        env_values={},
    )
    voice_commands = payload["proofs"]["provider-backed-live-voice-proof"][
        "credential_setup_commands"
    ]

    subprocess.run(
        ["/bin/sh", "-c", "\n".join(voice_commands)],
        cwd=tmp_path,
        env={
            "PATH": os.environ.get("PATH", ""),
            "OPENROUTER_API_KEY": "openrouter_preserve_config_secret_must_not_echo",
            "LIVEKIT_API_KEY": "livekit_preserve_key_must_not_echo",
            "LIVEKIT_API_SECRET": "livekit_preserve_secret_must_not_echo",
            "OPENROUTER_LIVEKIT_URL": "wss://livekit.new.example",
            "LOCAL_PROVIDER_CONFIG_FILE": ".secrets/local_provider_config.json",
        },
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(config_path.read_text(encoding="utf-8")) == {
        "CUSTOM_LOCAL_PROVIDER_NOTE": "keep-me",
        "OPENROUTER_LIVEKIT_URL": "wss://livekit.new.example",
    }


@pytest.mark.parametrize("existing_config_case", ["invalid_json", "non_utf8", "directory"])
def test_provider_proof_plan_setup_commands_reject_bad_existing_local_provider_config_without_traceback(
    tmp_path,
    existing_config_case,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=",
                "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key",
                "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret",
                "LOCAL_PROVIDER_CONFIG_FILE=.secrets/local_provider_config.json",
            ]
        )
    )
    config_path = tmp_path / ".secrets/local_provider_config.json"
    config_path.parent.mkdir()
    existing_marker = "hf_existing_config_secret_must_not_echo"
    if existing_config_case == "invalid_json":
        malformed_config = "{" + existing_marker
        config_path.write_text(malformed_config, encoding="utf-8")
    elif existing_config_case == "non_utf8":
        malformed_bytes = b"\xff\xfe" + existing_marker.encode("utf-8")
        config_path.write_bytes(malformed_bytes)
    else:
        config_path.mkdir()
    payload = _provider_proof_plan_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="RUN-ID",
        ),
        env_values={},
    )
    voice_commands = payload["proofs"]["provider-backed-live-voice-proof"][
        "credential_setup_commands"
    ]

    result = subprocess.run(
        ["/bin/sh", "-c", "\n".join(voice_commands)],
        cwd=tmp_path,
        env={
            "PATH": os.environ.get("PATH", ""),
            "OPENROUTER_API_KEY": "openrouter_malformed_existing_secret_must_not_echo",
            "LIVEKIT_API_KEY": "livekit_malformed_existing_key_must_not_echo",
            "LIVEKIT_API_SECRET": "livekit_malformed_existing_secret_must_not_echo",
            "OPENROUTER_LIVEKIT_URL": "wss://livekit.malformed.example",
            "LOCAL_PROVIDER_CONFIG_FILE": ".secrets/local_provider_config.json",
        },
        check=False,
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    if existing_config_case == "invalid_json":
        assert config_path.read_text(encoding="utf-8") == malformed_config
    elif existing_config_case == "non_utf8":
        assert config_path.read_bytes() == malformed_bytes
    else:
        assert config_path.is_dir()
    assert "Invalid existing LOCAL_PROVIDER_CONFIG_FILE" in output
    assert "Traceback" not in output
    assert "UnicodeDecodeError" not in output
    assert "IsADirectoryError" not in output
    assert existing_marker not in output
    assert "openrouter_malformed_existing_secret_must_not_echo" not in output
    assert "wss://livekit.malformed.example" not in output


def test_provider_proof_plan_setup_commands_recheck_as_ready_without_echoing_values(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=",
                "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key",
                "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret",
                "LOCAL_PROVIDER_CONFIG_FILE=.secrets/local_provider_config.json",
                "INSTAGRAM_ACCESS_TOKEN_FILE=.secrets/instagram_access_token",
                "LINKEDIN_ACCESS_TOKEN_FILE=.secrets/linkedin_access_token",
                "X_API_KEY_FILE=.secrets/x_api_key",
                "SUBSTACK_API_TOKEN_FILE=.secrets/substack_api_token",
            ]
        )
    )
    initial_payload = _provider_proof_plan_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
        ),
        env_values={},
    )
    setup_values = {
        "OPENROUTER_API_KEY": "openrouter_recheck_secret_must_not_echo",
        "LIVEKIT_API_KEY": "livekit_recheck_key_must_not_echo",
        "LIVEKIT_API_SECRET": "livekit_recheck_secret_must_not_echo",
        "OPENROUTER_LIVEKIT_URL": "wss://livekit.recheck.example",
        "INSTAGRAM_ACCESS_TOKEN": "instagram_recheck_secret_must_not_echo",
        "LINKEDIN_ACCESS_TOKEN": "linkedin_recheck_secret_must_not_echo",
        "X_API_KEY": "x_api_key_recheck_secret_must_not_echo",
        "SUBSTACK_API_TOKEN": "substack_recheck_secret_must_not_echo",
        "LOCAL_PROVIDER_CONFIG_FILE": ".secrets/local_provider_config.json",
    }
    commands = (
        initial_payload["proofs"]["provider-backed-live-voice-proof"][
            "credential_setup_commands"
        ]
        + initial_payload["proofs"]["external-publication-proof"][
            "credential_setup_commands"
        ]
    )

    result = subprocess.run(
        ["/bin/sh", "-c", "\n".join(commands)],
        cwd=tmp_path,
        env={"PATH": os.environ.get("PATH", ""), **setup_values},
        check=True,
        capture_output=True,
        text=True,
    )
    rechecked_payload = _provider_proof_plan_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
        ),
        env_values={},
    )
    serialized = json.dumps(rechecked_payload)

    assert (
        rechecked_payload["proofs"]["provider-backed-live-voice-proof"]["status"]
        == "ready_for_runtime_attempt"
    )
    assert (
        rechecked_payload["proofs"]["external-publication-proof"]["status"]
        == "ready_for_runtime_attempt"
    )
    assert rechecked_payload["proofs"]["provider-backed-live-voice-proof"][
        "configured_inputs"
    ] == []
    assert rechecked_payload["proofs"]["provider-backed-live-voice-proof"][
        "configured_local_provider_inputs"
    ] == ["OPENROUTER_LIVEKIT_URL"]
    assert rechecked_payload["proofs"]["external-publication-proof"][
        "configured_file_inputs"
    ] == [
        "LINKEDIN_ACCESS_TOKEN_FILE",
    ]
    output = result.stdout + result.stderr + serialized
    for key, value in setup_values.items():
        if key == "LOCAL_PROVIDER_CONFIG_FILE":
            continue
        assert value not in output


def test_provider_proof_plan_rejects_literal_placeholder_credential_values(
    tmp_path,
):
    secrets_dir = tmp_path / ".secrets"
    secrets_dir.mkdir()
    placeholder_files = {
        "openrouter_api_key": "<OPENROUTER_API_KEY>",
        "livekit_api_key": "<LIVEKIT_API_KEY>",
        "livekit_api_secret": "<LIVEKIT_API_SECRET>",
        "instagram_access_token": "<INSTAGRAM_ACCESS_TOKEN>",
        "linkedin_access_token": "<LINKEDIN_ACCESS_TOKEN>",
        "x_access_token": "<X_ACCESS_TOKEN>",
        "substack_api_token": "<SUBSTACK_API_TOKEN>",
    }
    for file_name, placeholder in placeholder_files.items():
        (secrets_dir / file_name).write_text(f"{placeholder}\n", encoding="utf-8")

    env_example = tmp_path / ".env.example"
    env_example.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=",
                "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key",
                "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret",
                "INSTAGRAM_ACCESS_TOKEN=",
                "INSTAGRAM_ACCESS_TOKEN_FILE=.secrets/instagram_access_token",
                "LINKEDIN_ACCESS_TOKEN=",
                "LINKEDIN_ACCESS_TOKEN_FILE=.secrets/linkedin_access_token",
                "X_ACCESS_TOKEN=",
                "X_ACCESS_TOKEN_FILE=.secrets/x_access_token",
                "SUBSTACK_API_TOKEN=",
                "SUBSTACK_API_TOKEN_FILE=.secrets/substack_api_token",
            ]
        )
    )

    payload = _provider_proof_plan_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
        ),
        env_values={
            "OPENROUTER_LIVEKIT_URL": "<OPENROUTER_LIVEKIT_URL>",
        },
    )

    voice = payload["proofs"]["provider-backed-live-voice-proof"]
    assert voice["status"] == "blocked_by_credentials"
    assert voice["credential_state"] == "blocked_by_placeholder_only_configuration"
    assert voice["configured_inputs"] == []
    assert voice["configured_file_inputs"] == []

    publication = payload["proofs"]["external-publication-proof"]
    assert publication["status"] == "blocked_by_credentials"
    assert (
        publication["credential_state"]
        == "blocked_by_placeholder_only_configuration"
    )
    assert publication["configured_inputs"] == []
    assert publication["configured_file_inputs"] == []


def test_provider_proof_plan_requires_voice_edge_benchmark_runtime_health_for_live_voice(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")

    payload = _provider_proof_plan_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
        ),
        env_values={},
    )
    voice = payload["proofs"]["provider-backed-live-voice-proof"]

    assert (
        "uv run all-about-llms-admin build-runtime-health-ledger --run-id 123e4567-e89b-12d3-a456-426614174000"
        in voice["commands"]
    )
    assert (
        "runtime_health_ledger with voice-edge-local-benchmark status ready"
        in voice["must_capture"]
    )
    assert (
        "runtime_health_ledger_artifact_id"
        in voice["proof_artifact_schema"]["required_fields"]
    )
    assert (
        "voice_edge_benchmark_status"
        in voice["proof_artifact_schema"]["required_fields"]
    )
    assert any(
        "voice-edge benchmark" in check
        for check in voice["post_capture_validation_checks"]
    )
    assert any(
        "runtime_health_ledger" in requirement
        for requirement in voice["proof_linkage_requirements"]
    )
    assert any(
        "voice-edge benchmark is ready" in requirement
        for requirement in voice["unblock_when"]
    )


def test_provider_proof_plan_marks_configured_inputs_ready_for_runtime_attempt(
    tmp_path,
):
    secrets_dir = tmp_path / ".secrets"
    secrets_dir.mkdir()
    (secrets_dir / "openrouter_api_key").write_text(
        "openrouter_secret_proof_plan_test_must_not_echo\n",
        encoding="utf-8",
    )
    (secrets_dir / "livekit_api_key").write_text(
        "livekit_key_proof_plan_test_must_not_echo\n",
        encoding="utf-8",
    )
    (secrets_dir / "livekit_api_secret").write_text(
        "livekit_secret_proof_plan_test_must_not_echo\n",
        encoding="utf-8",
    )
    env_example = tmp_path / ".env.example"
    env_example.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=",
                "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key",
                "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret",
                "INSTAGRAM_ACCESS_TOKEN=",
                "LINKEDIN_ACCESS_TOKEN=",
                "X_ACCESS_TOKEN=",
                "SUBSTACK_API_TOKEN=",
            ]
        )
    )

    payload = _provider_proof_plan_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
        ),
        env_values={
            "OPENROUTER_LIVEKIT_URL": "wss://livekit.example",
            "INSTAGRAM_ACCESS_TOKEN": "instagram-configured",
            "LINKEDIN_ACCESS_TOKEN": "linkedin-configured",
            "X_ACCESS_TOKEN": "x-configured",
            "SUBSTACK_API_TOKEN": "substack-configured",
        },
    )
    serialized = json.dumps(payload)

    voice = payload["proofs"]["provider-backed-live-voice-proof"]
    assert voice["status"] == "ready_for_runtime_attempt"
    assert voice["credential_state"] == "runtime_configuration_present_unverified"
    assert voice["blocking_reasons"] == []
    assert voice["attempt_gate"] == {
        "state": "ready_for_preflight_capture",
        "can_run_preflight_capture": True,
        "can_run_proof_commands": False,
        "blocked_by": [],
        "next_action": "initialize_workspace_and_capture_preflight",
        "next_action_commands": [
            (
                "uv run all-about-llms-admin init-provider-proof-workspace "
                f"--run-id {PROVIDER_PROOF_TEST_RUN_UUID} --output-dir "
                "social_media_optimiser/output/provider-proof/"
                f"{PROVIDER_PROOF_TEST_RUN_UUID}"
            ),
            (
                "uv run all-about-llms-admin validate-provider-proof-workspace "
                f"--run-id {PROVIDER_PROOF_TEST_RUN_UUID} --output-dir "
                "social_media_optimiser/output/provider-proof/"
                f"{PROVIDER_PROOF_TEST_RUN_UUID}"
            ),
            (
                "curl -sS -o social_media_optimiser/output/provider-proof/"
                f"{PROVIDER_PROOF_TEST_RUN_UUID}/product-run.preflight.json "
                f"http://127.0.0.1:8000/api/runs/{PROVIDER_PROOF_TEST_RUN_UUID}"
            ),
            (
                "curl -sS -o social_media_optimiser/output/provider-proof/"
                f"{PROVIDER_PROOF_TEST_RUN_UUID}/provider-readiness.preflight.json "
                "http://127.0.0.1:8000/api/provider-readiness"
            ),
            (
                "curl -sS -o social_media_optimiser/output/provider-proof/"
                f"{PROVIDER_PROOF_TEST_RUN_UUID}/"
                "voice-runtime-readiness.preflight.json "
                "'http://127.0.0.1:8000/api/voice-runtime-readiness?"
                "preflight_gemma=true&preflight_tts=true&"
                "preflight_livekit=true&preflight_edge=true&"
                "preflight_agent=true'"
            ),
            (
                "uv run all-about-llms-admin "
                "validate-provider-proof-preflight-artifacts "
                "--proof provider-backed-live-voice-proof "
                f"--run-id {PROVIDER_PROOF_TEST_RUN_UUID} "
                "--preflight-dir social_media_optimiser/output/provider-proof/"
                f"{PROVIDER_PROOF_TEST_RUN_UUID} > "
                "social_media_optimiser/output/provider-proof/"
                f"{PROVIDER_PROOF_TEST_RUN_UUID}/"
                "provider-backed-live-voice-proof.preflight-validation.json"
            ),
        ],
        "proof_commands_allowed_after": [
            "proof workspace initialized",
            "proof workspace validation status is valid_workspace",
            "preflight output files captured",
            "preflight validation report status is valid_preflight_artifacts",
            "proof-specific human confirmations are complete",
        ],
        "state_change_allowed": False,
    }
    assert voice["configured_file_inputs"] == [
        "OPENROUTER_API_KEY_FILE",
        "LIVEKIT_API_KEY_FILE",
        "LIVEKIT_API_SECRET_FILE",
    ]
    assert voice["secret_files_loaded"] is True
    assert "openrouter_secret_proof_plan_test_must_not_echo" not in serialized
    assert "livekit_key_proof_plan_test_must_not_echo" not in serialized
    assert "livekit_secret_proof_plan_test_must_not_echo" not in serialized


def test_provider_proof_plan_blocks_configured_inputs_until_run_id_is_product_uuid(
    tmp_path,
):
    secrets_dir = tmp_path / ".secrets"
    secrets_dir.mkdir()
    (secrets_dir / "openrouter_api_key").write_text(
        "openrouter_secret_test\n",
        encoding="utf-8",
    )
    (secrets_dir / "livekit_api_key").write_text(
        "livekit_key_test\n",
        encoding="utf-8",
    )
    (secrets_dir / "livekit_api_secret").write_text(
        "livekit_secret_test\n",
        encoding="utf-8",
    )
    env_example = tmp_path / ".env.example"
    env_example.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=",
                "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key",
                "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret",
                "INSTAGRAM_ACCESS_TOKEN=",
                "LINKEDIN_ACCESS_TOKEN=",
                "X_ACCESS_TOKEN=",
                "SUBSTACK_API_TOKEN=",
            ]
        )
    )

    payload = _provider_proof_plan_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="RUN-ID",
        ),
        env_values={
            "OPENROUTER_LIVEKIT_URL": "wss://livekit.example",
            "INSTAGRAM_ACCESS_TOKEN": "instagram-configured",
            "LINKEDIN_ACCESS_TOKEN": "linkedin-configured",
            "X_ACCESS_TOKEN": "x-configured",
            "SUBSTACK_API_TOKEN": "substack-configured",
        },
    )

    voice = payload["proofs"]["provider-backed-live-voice-proof"]
    publication = payload["proofs"]["external-publication-proof"]
    assert voice["credential_state"] == "runtime_configuration_present_unverified"
    assert voice["status"] == "blocked_by_run_id"
    assert voice["blocking_reasons"] == ["run_id_not_product_uuid"]
    assert voice["attempt_gate"]["state"] == "blocked_by_run_id"
    assert voice["attempt_gate"]["can_run_preflight_capture"] is False
    assert voice["attempt_gate"]["next_action"] == "replace_run_id"
    assert publication["status"] == "blocked_by_run_id"
    assert publication["blocking_reasons"] == ["run_id_not_product_uuid"]
    assert "durable product run UUID replaces run id" in voice["unblock_when"]


def test_provider_proof_plan_includes_product_run_preflight_capture(tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")

    payload = _provider_proof_plan_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
        )
    )

    voice = payload["proofs"]["provider-backed-live-voice-proof"]
    publication = payload["proofs"]["external-publication-proof"]
    expected_product_run_file = (
        f"social_media_optimiser/output/provider-proof/{PROVIDER_PROOF_TEST_RUN_UUID}/"
        "product-run.preflight.json"
    )
    expected_product_run_command = (
        "curl -sS -o "
        f"{expected_product_run_file} "
        f"http://127.0.0.1:8000/api/runs/{PROVIDER_PROOF_TEST_RUN_UUID}"
    )

    for proof in (voice, publication):
        assert f"GET /api/runs/{PROVIDER_PROOF_TEST_RUN_UUID}" in proof[
            "preflight_checks"
        ]
        assert (
            f"curl -sS http://127.0.0.1:8000/api/runs/{PROVIDER_PROOF_TEST_RUN_UUID}"
            in proof["preflight_commands"]
        )
        assert proof["preflight_output_files"][0] == expected_product_run_file
        assert proof["preflight_capture_commands"][0] == expected_product_run_command
        assert proof["preflight_artifact_id_fields"][0] == (
            "product_run_preflight_artifact_id"
        )
        assert "product-run.preflight.json must match /api/runs/<run-id> response shape and run_id must match command_run_id" in proof[
            "preflight_validation_requirements"
        ]
        assert "product_run_preflight_artifact_id" in proof[
            "proof_artifact_schema"
        ]["required_fields"]


def test_provider_proof_plan_exposes_product_run_bootstrap_handoff(tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")

    payload = _provider_proof_plan_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="<run-id>",
        ),
    )

    bootstrap = payload["product_run_bootstrap"]
    assert bootstrap["api_path"] == "POST /api/runs"
    assert bootstrap["output_file"] == (
        "social_media_optimiser/output/provider-proof/bootstrap/"
        "product-run.create.json"
    )
    assert bootstrap["created_run_id_field"] == "run_id"
    assert bootstrap["next_step"] == (
        "rerun provider-proof-plan with the printed run_id and initialize "
        "social_media_optimiser/output/provider-proof/<run-id>"
    )
    assert bootstrap["commands"][0] == (
        "mkdir -p social_media_optimiser/output/provider-proof/bootstrap"
    )
    assert (
        "curl -sS -X POST -o "
        "social_media_optimiser/output/provider-proof/bootstrap/"
        "product-run.create.json http://127.0.0.1:8000/api/runs "
        "-H 'Content-Type: application/json'"
    ) in bootstrap["commands"][1]
    assert '"input_mode":"text"' in bootstrap["commands"][1]
    assert "provider_proof_closeout" in bootstrap["commands"][1]
    assert "init-provider-proof-workspace-from-bootstrap" in bootstrap["commands"][2]
    assert "product-run.create.json" in bootstrap["commands"][2]
    assert "social_media_optimiser/output/provider-proof" in bootstrap["commands"][2]

    for proof in payload["proofs"].values():
        assert proof["product_run_bootstrap"] == bootstrap
        assert (
            "create or select durable product run UUID with "
            "product_run_bootstrap"
        ) in proof["operator_sequence"]


def test_provider_proof_product_run_bootstrap_validation_accepts_run_state_response(
    tmp_path,
):
    create_response_path = tmp_path / "product-run.create.json"
    create_response_path.write_text(
        json.dumps(_product_run_preflight_payload()),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_product_run_bootstrap_validation_payload(
        Namespace(
            checked_at="2026-05-20",
            create_response_path=create_response_path,
        )
    )

    assert payload == {
        "artifact": "agent-studio-provider-proof-product-run-bootstrap-validation",
        "boundary": "no_secret_values_printed_no_state_change",
        "checked_at": "2026-05-20",
        "status": "valid_product_run_bootstrap",
        "create_response_path": str(create_response_path),
        "run_id": PROVIDER_PROOF_TEST_RUN_UUID,
        "product_run_id_state": "product_run_uuid",
        "issue_codes": [],
        "issues": [],
        "state_change_allowed": False,
        "next_commands": [
            (
                "uv run all-about-llms-admin "
                "init-provider-proof-workspace-from-bootstrap "
                f"--create-response-path {create_response_path} "
                "--output-root social_media_optimiser/output/provider-proof"
            ),
            (
                "uv run all-about-llms-admin provider-proof-plan "
                f"--run-id {PROVIDER_PROOF_TEST_RUN_UUID}"
            ),
            (
                "uv run all-about-llms-admin init-provider-proof-workspace "
                f"--run-id {PROVIDER_PROOF_TEST_RUN_UUID} --output-dir "
                "social_media_optimiser/output/provider-proof/"
                f"{PROVIDER_PROOF_TEST_RUN_UUID}"
            ),
            (
                "uv run all-about-llms-admin validate-provider-proof-workspace "
                f"--run-id {PROVIDER_PROOF_TEST_RUN_UUID} --output-dir "
                "social_media_optimiser/output/provider-proof/"
                f"{PROVIDER_PROOF_TEST_RUN_UUID}"
            ),
        ],
    }


def test_provider_proof_workspace_from_bootstrap_initializes_uuid_workspace(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    create_response_path = tmp_path / "product-run.create.json"
    create_response_path.write_text(
        json.dumps(_product_run_preflight_payload()),
        encoding="utf-8",
    )
    output_root = tmp_path / "provider-proof"

    payload = provider_cli._provider_proof_workspace_from_bootstrap_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            create_response_path=create_response_path,
            output_root=output_root,
        )
    )

    output_dir = output_root / PROVIDER_PROOF_TEST_RUN_UUID
    assert payload["artifact"] == (
        "agent-studio-provider-proof-workspace-from-bootstrap"
    )
    assert payload["boundary"] == "no_secret_values_printed_no_state_change"
    assert payload["checked_at"] == "2026-05-20"
    assert payload["status"] == "workspace_ready"
    assert payload["create_response_validation_status"] == (
        "valid_product_run_bootstrap"
    )
    assert payload["run_id"] == PROVIDER_PROOF_TEST_RUN_UUID
    assert payload["output_dir"] == str(output_dir)
    assert payload["state_change_allowed"] is False
    assert payload["issue_codes"] == []
    assert payload["workspace_validation_commands"] == [
        (
            "uv run all-about-llms-admin validate-provider-proof-workspace "
            f"--run-id {PROVIDER_PROOF_TEST_RUN_UUID} --output-dir "
            f"{shlex.quote(str(output_dir))}"
        )
    ]
    assert (output_dir / "provider-backed-live-voice-proof.template.json").exists()
    assert (output_dir / "external-publication-proof.template.json").exists()
    assert (output_dir / "README.md").exists()


def test_provider_proof_workspace_from_bootstrap_rejects_invalid_bootstrap_without_writing(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    create_response_path = tmp_path / "product-run.create.json"
    create_response_path.write_text(
        json.dumps({"run_id": PROVIDER_PROOF_TEST_RUN_UUID}),
        encoding="utf-8",
    )
    output_root = tmp_path / "provider-proof"

    payload = provider_cli._provider_proof_workspace_from_bootstrap_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            create_response_path=create_response_path,
            output_root=output_root,
        )
    )

    assert payload["status"] == "invalid_product_run_bootstrap"
    assert payload["create_response_validation_status"] == (
        "invalid_product_run_bootstrap"
    )
    assert payload["run_id"] is None
    assert payload["state_change_allowed"] is False
    assert payload["written_files"] == []
    assert payload["issue_codes"] == ["product_run_payload_schema_invalid"]
    assert not output_root.exists()


def test_provider_proof_workspace_from_bootstrap_rejects_non_directory_output_root(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    create_response_path = tmp_path / "product-run.create.json"
    create_response_path.write_text(
        json.dumps(_product_run_preflight_payload()),
        encoding="utf-8",
    )
    output_root = tmp_path / "provider-proof"
    output_root.write_text("not a directory", encoding="utf-8")

    payload = provider_cli._provider_proof_workspace_from_bootstrap_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            create_response_path=create_response_path,
            output_root=output_root,
        )
    )

    assert payload["status"] == "invalid_workspace"
    assert payload["create_response_validation_status"] == (
        "valid_product_run_bootstrap"
    )
    assert payload["run_id"] == PROVIDER_PROOF_TEST_RUN_UUID
    assert payload["written_files"] == []
    assert payload["issue_codes"] == ["workspace_path_unwritable"]


def test_provider_proof_product_run_bootstrap_validation_rejects_run_id_only_json(
    tmp_path,
):
    create_response_path = tmp_path / "product-run.create.json"
    create_response_path.write_text(
        json.dumps({"run_id": PROVIDER_PROOF_TEST_RUN_UUID}),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_product_run_bootstrap_validation_payload(
        Namespace(
            checked_at="2026-05-20",
            create_response_path=create_response_path,
        )
    )

    assert payload["status"] == "invalid_product_run_bootstrap"
    assert payload["run_id"] is None
    assert payload["state_change_allowed"] is False
    assert payload["next_commands"] == []
    assert payload["issue_codes"] == ["product_run_payload_schema_invalid"]
    assert payload["issues"] == [
        {
            "code": "product_run_payload_schema_invalid",
            "field": str(create_response_path),
            "detail": (
                "product-run.create.json must match /api/runs response shape"
            ),
        }
    ]


def test_provider_proof_preflight_validation_requires_product_run_capture(tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    (preflight_dir / "provider-readiness.preflight.json").write_text(
        json.dumps(_ready_provider_readiness_preflight_payload()),
        encoding="utf-8",
    )
    (preflight_dir / "voice-runtime-readiness.preflight.json").write_text(
        json.dumps(_ready_voice_runtime_preflight_payload()),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            proof="provider-backed-live-voice-proof",
            preflight_dir=preflight_dir,
        )
    )

    assert payload["status"] == "invalid_preflight_artifacts"
    assert payload["state_change_allowed"] is False
    assert "preflight_file_missing" in payload["issue_codes"]
    assert "product-run.preflight.json" in payload["expected_files"][0]
    assert payload["preflight_artifact_ids"] == {}


def test_provider_proof_preflight_validation_rejects_run_id_only_product_run_capture(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    (preflight_dir / "product-run.preflight.json").write_text(
        json.dumps({"run_id": PROVIDER_PROOF_TEST_RUN_UUID}),
        encoding="utf-8",
    )
    (preflight_dir / "provider-readiness.preflight.json").write_text(
        json.dumps(_ready_provider_readiness_preflight_payload()),
        encoding="utf-8",
    )
    (preflight_dir / "voice-runtime-readiness.preflight.json").write_text(
        json.dumps(_ready_voice_runtime_preflight_payload()),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            proof="provider-backed-live-voice-proof",
            preflight_dir=preflight_dir,
        )
    )

    assert payload["status"] == "invalid_preflight_artifacts"
    assert payload["state_change_allowed"] is False
    assert "product_run_payload_schema_invalid" in payload["issue_codes"]
    assert "validated_product_run_id" not in payload
    assert payload["preflight_artifact_ids"] == {}


def test_provider_proof_plan_reads_local_provider_config_without_echoing_values(
    tmp_path,
):
    secrets_dir = tmp_path / ".secrets"
    secrets_dir.mkdir()
    (secrets_dir / "openrouter_api_key").write_text(
        "openrouter_secret_local_provider_config_test_must_not_echo\n",
        encoding="utf-8",
    )
    (secrets_dir / "livekit_api_key").write_text(
        "livekit_key_local_provider_config_test_must_not_echo\n",
        encoding="utf-8",
    )
    (secrets_dir / "livekit_api_secret").write_text(
        "livekit_secret_local_provider_config_test_must_not_echo\n",
        encoding="utf-8",
    )
    (secrets_dir / "local_provider_config.json").write_text(
        json.dumps(
            {
                "OPENROUTER_LIVEKIT_URL": "wss://livekit.example",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    env_example = tmp_path / ".env.example"
    env_example.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=",
                "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key",
                "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret",
                "LOCAL_PROVIDER_CONFIG_FILE=.secrets/local_provider_config.json",
            ]
        )
    )

    payload = _provider_proof_plan_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
        ),
        env_values={},
    )
    serialized = json.dumps(payload)
    voice = payload["proofs"]["provider-backed-live-voice-proof"]

    assert voice["status"] == "ready_for_runtime_attempt"
    assert voice["credential_state"] == "runtime_configuration_present_unverified"
    assert voice["configured_inputs"] == []
    assert voice["configured_local_provider_inputs"] == ["OPENROUTER_LIVEKIT_URL"]
    assert voice["local_provider_config_loaded"] is True
    assert "wss://livekit.example" not in serialized
    assert "openrouter_secret_local_provider_config_test_must_not_echo" not in serialized
    assert "livekit_key_local_provider_config_test_must_not_echo" not in serialized
    assert "livekit_secret_local_provider_config_test_must_not_echo" not in serialized


def test_provider_proof_plan_blocks_runtime_attempt_until_run_id_is_concrete(
    tmp_path,
):
    secrets_dir = tmp_path / ".secrets"
    secrets_dir.mkdir()
    (secrets_dir / "openrouter_api_key").write_text(
        "openrouter_secret_test\n",
        encoding="utf-8",
    )
    (secrets_dir / "livekit_api_key").write_text(
        "livekit_key_test\n",
        encoding="utf-8",
    )
    (secrets_dir / "livekit_api_secret").write_text(
        "livekit_secret_test\n",
        encoding="utf-8",
    )
    env_example = tmp_path / ".env.example"
    env_example.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=",
                "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key",
                "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret",
                "INSTAGRAM_ACCESS_TOKEN=",
                "LINKEDIN_ACCESS_TOKEN=",
                "X_ACCESS_TOKEN=",
                "SUBSTACK_API_TOKEN=",
            ]
        )
    )

    payload = _provider_proof_plan_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="<run-id>",
        ),
        env_values={
            "OPENROUTER_LIVEKIT_URL": "wss://livekit.example",
            "INSTAGRAM_ACCESS_TOKEN": "instagram-configured",
            "LINKEDIN_ACCESS_TOKEN": "linkedin-configured",
            "X_ACCESS_TOKEN": "x-configured",
            "SUBSTACK_API_TOKEN": "substack-configured",
        },
    )

    voice = payload["proofs"]["provider-backed-live-voice-proof"]
    assert voice["credential_state"] == "runtime_configuration_present_unverified"
    assert voice["status"] == "blocked_by_run_id"
    assert voice["blocking_reasons"] == ["run_id_not_concrete"]
    assert voice["attempt_gate"]["state"] == "blocked_by_run_id"
    assert voice["attempt_gate"]["can_run_preflight_capture"] is False
    assert voice["attempt_gate"]["next_action"] == "replace_run_id"
    assert voice["run_id_state"] == "placeholder_run_id"
    assert voice["run_id_required_before_execution"] is True
    assert "durable product run UUID replaces <run-id>" in voice["unblock_when"]


def test_provider_proof_plan_exposes_all_active_attempt_blockers(tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY=",
                "OPENROUTER_LIVEKIT_URL=",
                "LIVEKIT_API_KEY=",
                "LIVEKIT_API_SECRET=",
                "INSTAGRAM_ACCESS_TOKEN=",
                "LINKEDIN_ACCESS_TOKEN=",
                "X_ACCESS_TOKEN=",
                "SUBSTACK_API_TOKEN=",
            ]
        )
    )

    payload = _provider_proof_plan_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="<run-id>",
        ),
        env_values={},
    )

    voice = payload["proofs"]["provider-backed-live-voice-proof"]
    publication = payload["proofs"]["external-publication-proof"]
    assert voice["status"] == "blocked_by_run_id"
    assert voice["blocking_reasons"] == [
        "run_id_not_concrete",
        "blocked_by_placeholder_only_configuration",
    ]
    assert publication["blocking_reasons"] == [
        "run_id_not_concrete",
        "blocked_by_placeholder_only_configuration",
    ]


def test_provider_proof_plan_does_not_emit_unsafe_run_id_in_commands(tmp_path):
    secrets_dir = tmp_path / ".secrets"
    secrets_dir.mkdir()
    (secrets_dir / "openrouter_api_key").write_text(
        "openrouter_secret_test\n",
        encoding="utf-8",
    )
    (secrets_dir / "livekit_api_key").write_text(
        "livekit_key_test\n",
        encoding="utf-8",
    )
    (secrets_dir / "livekit_api_secret").write_text(
        "livekit_secret_test\n",
        encoding="utf-8",
    )
    env_example = tmp_path / ".env.example"
    env_example.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=",
                "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key",
                "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret",
                "INSTAGRAM_ACCESS_TOKEN=",
                "LINKEDIN_ACCESS_TOKEN=",
                "X_ACCESS_TOKEN=",
                "SUBSTACK_API_TOKEN=",
            ]
        )
    )

    payload = _provider_proof_plan_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="RUN-ID; echo injected",
        ),
        env_values={
            "OPENROUTER_LIVEKIT_URL": "wss://livekit.example",
            "INSTAGRAM_ACCESS_TOKEN": "instagram-configured",
            "LINKEDIN_ACCESS_TOKEN": "linkedin-configured",
            "X_ACCESS_TOKEN": "x-configured",
            "SUBSTACK_API_TOKEN": "substack-configured",
        },
    )
    serialized = json.dumps(payload)

    voice = payload["proofs"]["provider-backed-live-voice-proof"]
    publication = payload["proofs"]["external-publication-proof"]
    assert voice["credential_state"] == "runtime_configuration_present_unverified"
    assert voice["status"] == "blocked_by_run_id"
    assert voice["run_id_state"] == "unsafe_run_id"
    assert voice["blocking_reasons"] == ["run_id_unsafe"]
    assert voice["command_run_id"] == "<run-id>"
    assert publication["status"] == "blocked_by_run_id"
    assert publication["blocking_reasons"] == ["run_id_unsafe"]
    assert publication["command_run_id"] == "<run-id>"
    assert "<run-id>" in " ".join(voice["commands"])
    assert "<run-id>" in " ".join(publication["preflight_commands"])
    assert "<run-id>" in " ".join(publication["preflight_capture_commands"])
    assert "echo injected" not in " ".join(publication["preflight_capture_commands"])
    assert "POST /api/runs/<run-id>/publish-readiness" in publication[
        "preflight_checks"
    ]
    assert "RUN-ID; echo injected" not in serialized
    assert "echo injected" not in serialized
    assert "run id contains unsupported characters" in voice["unblock_when"]


def test_provider_proof_plan_exposes_missing_configuration_blocker_reason(tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text(
        "\n".join(
            [
                "X_ACCESS_TOKEN=",
                "SUBSTACK_API_TOKEN=",
            ]
        )
    )

    payload = _provider_proof_plan_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="RUN-ID",
        ),
        env_values={},
    )

    voice = payload["proofs"]["provider-backed-live-voice-proof"]
    publication = payload["proofs"]["external-publication-proof"]
    assert voice["status"] == "blocked_by_credentials"
    assert voice["credential_state"] == "blocked_by_missing_configuration"
    assert voice["blocking_reasons"] == ["blocked_by_missing_configuration"]
    assert "OPENROUTER_API_KEY" in payload["credential_snapshot"][
        "snapshots"
    ]["provider-backed-live-voice-proof"]["absent_inputs"]
    assert publication["status"] == "blocked_by_credentials"
    assert publication["credential_state"] == "blocked_by_missing_configuration"
    assert publication["blocking_reasons"] == ["blocked_by_missing_configuration"]
    assert payload["credential_snapshot"]["snapshots"][
        "external-publication-proof"
    ]["absent_inputs"] == ["LINKEDIN_ACCESS_TOKEN"]


def test_provider_proof_plan_does_not_emit_secret_shaped_run_id(tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    secret_shaped_run_id = "sk-" + "ABCDEFGHIJKLMNOPQRST"

    payload = _provider_proof_plan_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id=secret_shaped_run_id,
        )
    )
    serialized = json.dumps(payload)

    voice = payload["proofs"]["provider-backed-live-voice-proof"]
    publication = payload["proofs"]["external-publication-proof"]
    assert voice["status"] == "blocked_by_run_id"
    assert voice["run_id_state"] == "unsafe_run_id"
    assert voice["command_run_id"] == "<run-id>"
    assert publication["command_run_id"] == "<run-id>"
    assert secret_shaped_run_id not in serialized
    assert secret_shaped_run_id not in " ".join(voice["commands"])


def test_provider_proof_record_validation_accepts_matching_voice_record(tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    record = {
        "run_id": "123e4567-e89b-12d3-a456-426614174000",
        "checked_at": "2026-05-20",
        "validation_timestamp": "2026-05-20T12:00:00Z",
        "proof_outcome": "accepted",
        "product_run_preflight_artifact_id": "artifact-product-run",
        "provider_readiness_preflight_artifact_id": "artifact-provider-preflight",
        "voice_runtime_readiness_preflight_artifact_id": "artifact-voice-preflight",
        "voice_agent_process_start_artifact_id": "artifact-voice-agent-start",
        "runtime_health_ledger_artifact_id": "artifact-runtime-health",
        "voice_edge_benchmark_status": "ready",
        "provider_smoke_ledger_artifact_id": "artifact-smoke",
        "livekit_voice_timing_capture_artifact_id": "artifact-livekit-capture",
        "realtime_voice_timing_ledger_artifact_id": "artifact-timing",
        "realtime_provider": "openrouter_livekit",
        "execute_live_calls": True,
        "realtime_session_id_or_livekit_room": "room-123",
        "participant_identity": "agent-voice",
        "runtime_configuration_snapshot_id": "runtime-snapshot",
        "post_capture_validation_results": {
            (
                "runtime_health_ledger voice-edge benchmark is ready and records "
                "p50/p95/max latency plus false-positive, missed-speech-start, "
                "and missed-cancellation counts"
            ): "passed",
            "provider_smoke_ledger execute_live_calls is true": "passed",
            "provider_smoke_ledger realtime_provider is openrouter_livekit": "passed",
            (
                "provider_smoke_ledger run_id equals "
                "realtime_voice_timing_ledger run_id and command_run_id"
            ): "passed",
            (
                "realtime_session_id or LiveKit room/session id matches across "
                "smoke, timing, and participant evidence"
            ): "passed",
            "first text or audio timing plus interruption evidence are present": "passed",
            (
                "captured proof artifacts contain no token, API key, or secret values"
            ): "passed",
        },
        "secret_redaction_check": "passed",
    }
    preflight_report_path = tmp_path / "voice-preflight-validation.json"
    preflight_report_path.write_text(
        json.dumps(
            {
                "artifact": (
                    "agent-studio-provider-proof-preflight-artifacts-validation"
                ),
                "proof": "provider-backed-live-voice-proof",
                "command_run_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "valid_preflight_artifacts",
                "issue_codes": [],
                "preflight_artifact_ids": {
                    "product_run_preflight_artifact_id": "artifact-product-run",
                    "provider_readiness_preflight_artifact_id": (
                        "artifact-provider-preflight"
                    ),
                    "voice_runtime_readiness_preflight_artifact_id": (
                        "artifact-voice-preflight"
                    ),
                },
                "validated_runtime_checks": list(
                    provider_cli.VOICE_PROOF_REQUIRED_RUNTIME_CHECKS
                ),
                "validated_product_run_id": PROVIDER_PROOF_TEST_RUN_UUID,
            }
        ),
        encoding="utf-8",
    )
    record["preflight_validation_report_artifact_id"] = str(preflight_report_path)
    record["workspace_validation_report_artifact_id"] = str(
        _write_valid_workspace_validation_report(env_example)
    )

    payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            proof="provider-backed-live-voice-proof",
        ),
        record,
    )

    assert payload["artifact"] == "agent-studio-provider-proof-record-validation"
    assert payload["boundary"] == "no_secret_values_printed_no_state_change"
    assert payload["proof"] == "provider-backed-live-voice-proof"
    assert payload["status"] == "valid_accepted_record"
    assert payload["state_change_allowed"] is True
    assert payload["issues"] == []


def test_provider_proof_record_validation_rejects_accepted_voice_record_without_voice_agent_process_start_artifact(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    record = _accepted_provider_proof_record(
        env_example,
        "provider-backed-live-voice-proof",
    )
    record.pop("voice_agent_process_start_artifact_id", None)

    payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            proof="provider-backed-live-voice-proof",
        ),
        record,
    )

    assert payload["status"] == "invalid_record"
    assert payload["state_change_allowed"] is False
    assert "missing_required_field" in payload["issue_codes"]
    assert {
        "code": "missing_required_field",
        "field": "voice_agent_process_start_artifact_id",
    } in payload["issues"]


def test_provider_proof_record_validation_rejects_unparseable_validation_timestamp(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    record = _accepted_provider_proof_record(
        env_example,
        "provider-backed-live-voice-proof",
    )
    record["validation_timestamp"] = "not-a-date"

    payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            proof="provider-backed-live-voice-proof",
        ),
        record,
    )

    assert payload["status"] == "invalid_record"
    assert "invalid_validation_timestamp" in payload["issue_codes"]
    assert any(
        issue["field"] == "validation_timestamp" for issue in payload["issues"]
    )


def test_provider_proof_record_validation_rejects_accepted_voice_record_with_contradictory_live_voice_fields(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    base_record = _accepted_provider_proof_record(
        env_example,
        "provider-backed-live-voice-proof",
    )
    cases = [
        ("voice_edge_benchmark_status", "failed", "voice_edge_benchmark_not_ready"),
        ("execute_live_calls", False, "execute_live_calls_not_true"),
        ("realtime_provider", "hf_router_text", "realtime_provider_not_openrouter_livekit"),
    ]

    for field, value, expected_issue in cases:
        record = dict(base_record)
        record[field] = value

        payload = _provider_proof_record_validation_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof="provider-backed-live-voice-proof",
            ),
            record,
        )

        assert payload["status"] == "invalid_record"
        assert payload["state_change_allowed"] is False
        assert expected_issue in payload["issue_codes"]


def test_provider_proof_record_template_builds_non_accepted_voice_draft(tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")

    payload = _provider_proof_record_template_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
        ),
    )
    record = payload["record"]
    validation_payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
        ),
        record,
    )

    assert payload["artifact"] == "agent-studio-provider-proof-record-template"
    assert payload["status"] == "template_ready"
    assert payload["run_id_state"] == "concrete_run_id"
    assert payload["command_run_id"] == "123e4567-e89b-12d3-a456-426614174000"
    expected_preflight_report = (
        "social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000/"
        "provider-backed-live-voice-proof.preflight-validation.json"
    )
    expected_workspace_report = (
        "social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000/"
        "workspace-validation.json"
    )
    assert payload["next_commands"] == [
        (
            "uv run all-about-llms-admin validate-provider-proof-record "
            "--proof provider-backed-live-voice-proof --run-id 123e4567-e89b-12d3-a456-426614174000 "
            "--record-path <provider-proof-record.json> "
            f"--preflight-validation-path {expected_preflight_report} "
            f"--workspace-validation-path {expected_workspace_report}"
        ),
        (
            "uv run all-about-llms-admin record-provider-proof-record "
            "--proof provider-backed-live-voice-proof --run-id 123e4567-e89b-12d3-a456-426614174000 "
            "--record-path <provider-proof-record.json> "
            f"--preflight-validation-path {expected_preflight_report} "
            f"--workspace-validation-path {expected_workspace_report}"
        ),
    ]
    assert "<preflight-validation.json>" not in " ".join(payload["next_commands"])
    assert "<workspace-validation.json>" not in " ".join(payload["next_commands"])
    assert record["run_id"] == "123e4567-e89b-12d3-a456-426614174000"
    assert record["checked_at"] == "2026-05-20"
    assert record["validation_timestamp"] == "<validation-timestamp>"
    assert record["proof_outcome"] == "<accepted-or-failed>"
    assert record["workspace_validation_report_artifact_id"] == "<artifact-id>"
    assert record["voice_agent_process_start_artifact_id"] == "<artifact-id>"
    assert record["provider_smoke_ledger_artifact_id"] == "<artifact-id>"
    assert record["livekit_voice_timing_capture_artifact_id"] == "<artifact-id>"
    assert record["secret_redaction_check"] == "<passed-after-no-secret-scan>"
    assert set(record["post_capture_validation_results"]) == set(
        payload["post_capture_validation_checks"]
    )
    assert all(
        value == "<passed-or-failed>"
        for value in record["post_capture_validation_results"].values()
    )
    assert validation_payload["status"] == "invalid_record"
    assert validation_payload["state_change_allowed"] is False


def test_provider_proof_record_next_commands_redact_token_shaped_report_paths(
    tmp_path,
):
    secret_segment = "sk-ABCDEFGHIJKLMNOPQRST"
    report_dir = tmp_path / secret_segment
    preflight_report = report_dir / "preflight-validation.json"
    workspace_report = report_dir / "workspace-validation.json"

    commands = provider_cli._proof_record_next_commands(
        "provider-backed-live-voice-proof",
        "123e4567-e89b-12d3-a456-426614174000",
        preflight_validation_path=preflight_report,
        workspace_validation_path=workspace_report,
    )
    serialized = json.dumps(commands)

    assert secret_segment not in serialized
    assert "<redacted>" in serialized
    assert "--preflight-validation-path" in commands[0]
    assert "--workspace-validation-path" in commands[0]


def test_provider_proof_record_next_commands_redact_angle_wrapped_token_shaped_report_paths():
    secret_value = "<sk-ABCDEFGHIJKLMNOPQRST>"

    commands = provider_cli._proof_record_next_commands(
        "provider-backed-live-voice-proof",
        "123e4567-e89b-12d3-a456-426614174000",
        preflight_validation_path=secret_value,
        workspace_validation_path=secret_value,
    )
    serialized = json.dumps(commands)

    assert secret_value not in serialized
    assert "sk-ABCDEFGHIJKLMNOPQRST" not in serialized
    assert "<preflight-validation.json>" not in serialized
    assert "<redacted>" in serialized


def test_provider_proof_record_template_blocks_placeholder_run_id(tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")

    payload = _provider_proof_record_template_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="<run-id>",
            proof="provider-backed-live-voice-proof",
        ),
    )

    assert payload["status"] == "blocked_by_run_id"
    assert payload["run_id_state"] == "placeholder_run_id"
    assert payload["record"] is None
    assert payload["next_commands"] == []
    assert payload["issue_codes"] == ["run_id_not_concrete"]


def test_provider_proof_record_template_blocks_non_uuid_product_run_id(tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")

    payload = _provider_proof_record_template_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="RUN-ID",
            proof="provider-backed-live-voice-proof",
        ),
    )

    assert payload["status"] == "blocked_by_run_id"
    assert payload["run_id_state"] == "concrete_run_id"
    assert payload["product_run_id_state"] == "non_uuid_run_id"
    assert payload["record"] is None
    assert payload["next_commands"] == []
    assert payload["issue_codes"] == ["run_id_not_product_uuid"]


def test_provider_proof_record_validation_rejects_non_uuid_product_run_id(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    record = _accepted_provider_proof_record(
        env_example,
        "provider-backed-live-voice-proof",
        run_id=PROVIDER_PROOF_TEST_RUN_UUID,
    )
    record["run_id"] = "RUN-ID"

    payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="RUN-ID",
            proof="provider-backed-live-voice-proof",
        ),
        record,
    )

    assert payload["status"] == "invalid_record"
    assert payload["state_change_allowed"] is False
    assert payload["product_run_id_state"] == "non_uuid_run_id"
    assert "run_id_not_product_uuid" in payload["issue_codes"]


def test_provider_proof_record_validation_rejects_partially_filled_template_acceptance(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    args = Namespace(
        env_example_path=env_example,
        checked_at="2026-05-20",
        run_id="123e4567-e89b-12d3-a456-426614174000",
        proof="provider-backed-live-voice-proof",
    )
    template_payload = _provider_proof_record_template_payload(args)
    record = template_payload["record"]
    record["proof_outcome"] = "accepted"
    record["execute_live_calls"] = True
    record["secret_redaction_check"] = "passed"
    record["post_capture_validation_results"] = {
        check: "passed" for check in template_payload["post_capture_validation_checks"]
    }

    payload = _provider_proof_record_validation_payload(args, record)

    assert payload["status"] == "invalid_record"
    assert payload["state_change_allowed"] is False
    assert "template_placeholder_not_replaced" in payload["issue_codes"]


def test_provider_proof_record_validation_rejects_partially_filled_template_failure(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    args = Namespace(
        env_example_path=env_example,
        checked_at="2026-05-20",
        run_id="123e4567-e89b-12d3-a456-426614174000",
        proof="provider-backed-live-voice-proof",
    )
    template_payload = _provider_proof_record_template_payload(args)
    record = template_payload["record"]
    record["proof_outcome"] = "failed"
    record["secret_redaction_check"] = "passed"
    record["post_capture_validation_results"] = {
        "provider_smoke_ledger execute_live_calls is true": "failed"
    }

    payload = _provider_proof_record_validation_payload(args, record)

    assert payload["status"] == "invalid_record"
    assert payload["state_change_allowed"] is False
    assert "template_placeholder_not_replaced" in payload["issue_codes"]


def test_provider_proof_workspace_writes_templates_and_readme(tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    output_dir = tmp_path / "proof workspace"

    payload = _provider_proof_workspace_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            output_dir=output_dir,
        ),
    )
    voice_path = output_dir / "provider-backed-live-voice-proof.template.json"
    publication_path = output_dir / "external-publication-proof.template.json"
    operator_inputs_path = output_dir / "operator-inputs.template.env"
    readme_path = output_dir / "README.md"
    voice_record = json.loads(voice_path.read_text(encoding="utf-8"))
    publication_record = json.loads(publication_path.read_text(encoding="utf-8"))
    operator_inputs = operator_inputs_path.read_text(encoding="utf-8")
    readme = readme_path.read_text(encoding="utf-8")
    generated_handoff_text = "\n".join(
        [
            json.dumps(publication_record, sort_keys=True),
            readme,
        ]
    )
    stale_publication_linkage_phrases = [
        (
            "destination_channel appears in validated_publish_channels "
            "from the accepted preflight validation report"
        ),
        (
            "destination_channel appears in the preflight validation "
            "report's validated_publish_channels"
        ),
    ]
    linkedin_only_publication_linkage = (
        "destination_channel is linkedin and the preflight validation "
        "report's validated_publish_channels is exactly linkedin"
    )

    assert payload["artifact"] == "agent-studio-provider-proof-workspace"
    assert payload["status"] == "workspace_ready"
    assert payload["run_id_state"] == "concrete_run_id"
    assert payload["output_dir"] == str(output_dir)
    assert payload["written_files"] == [
        str(voice_path),
        str(publication_path),
        str(operator_inputs_path),
        str(readme_path),
    ]
    assert payload["validation_commands"] == [
        (
            "uv run all-about-llms-admin validate-provider-proof-workspace "
            f"--run-id 123e4567-e89b-12d3-a456-426614174000 --output-dir {shlex.quote(str(output_dir))}"
        )
    ]
    assert voice_record["run_id"] == "123e4567-e89b-12d3-a456-426614174000"
    assert publication_record["run_id"] == "123e4567-e89b-12d3-a456-426614174000"
    assert voice_record["proof_outcome"] == "<accepted-or-failed>"
    assert publication_record["proof_outcome"] == "<accepted-or-failed>"
    assert linkedin_only_publication_linkage in generated_handoff_text
    for stale_phrase in stale_publication_linkage_phrases:
        assert stale_phrase not in generated_handoff_text
    assert "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key" in operator_inputs
    assert "OPENROUTER_LIVEKIT_URL=ws://127.0.0.1:7880" in operator_inputs
    assert "LINKEDIN_ACCESS_TOKEN_FILE=.secrets/linkedin_access_token" in operator_inputs
    assert "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL=<external-url-or-id>" in operator_inputs
    assert operator_inputs.count("# contract: ") == 8
    assert operator_inputs.count("# value_source: ") == 8
    assert operator_inputs.count("# template_state: ") == 8
    assert operator_inputs.count("# issue_code: ") == 8
    assert operator_inputs.count("# next_action: ") == 8
    assert operator_inputs.count("# proof_id: ") == 8
    assert operator_inputs.count("# proof_input_role: ") == 8
    assert (
        "# proof_id: provider-backed-live-voice-proof\n"
        "# proof_input_role: provider_credential"
    ) in operator_inputs
    assert (
        "# proof_id: provider-backed-live-voice-proof\n"
        "# proof_input_role: transport_endpoint"
    ) in operator_inputs
    assert (
        "# proof_id: external-publication-proof\n"
        "# proof_input_role: publisher_credential"
    ) in operator_inputs
    assert (
        "# proof_id: external-publication-proof\n"
        "# proof_input_role: publication_evidence"
    ) in operator_inputs
    assert "readable local secret file path; file content is never emitted" in (
        operator_inputs
    )
    assert "ws or wss LiveKit URL for OpenRouter-backed realtime dialogue" in (
        operator_inputs
    )
    assert "# value_source: secret_file_path" in operator_inputs
    assert "# value_source: endpoint_url" in operator_inputs
    assert "# value_source: external_destination" in operator_inputs
    assert "# value_source: artifact_id" in operator_inputs
    assert "# template_state: secret_file_unavailable" in operator_inputs
    assert "# template_state: placeholder" in operator_inputs
    assert "# issue_code: operator_input_secret_file_unavailable" in operator_inputs
    assert "# issue_code: operator_input_placeholder" in operator_inputs
    assert "# next_action: write_readable_secret_file_and_reference_path" in (
        operator_inputs
    )
    assert "# next_action: replace_placeholder_in_operator_input_file" in (
        operator_inputs
    )
    assert "provider-backed-live-voice-proof.template.json" in readme
    assert "external-publication-proof.template.json" in readme
    assert "operator-inputs.template.env" in readme
    assert "provider-proof-operator-input-readiness" in readme
    assert "--fail-on-blocked" in readme
    assert "guarded retry sequence:" in readme
    assert "aggregate operator input readiness:" in readme
    aggregate_block = readme.split(
        "- aggregate operator input readiness:",
        1,
    )[1].split("- per-proof operator input route commands:", 1)[0]
    assert "- blocked_fields:" in aggregate_block
    assert "- required_fields:" in aggregate_block
    assert "- configured_fields:" in aggregate_block
    assert "- field_contracts:" in aggregate_block
    assert "- field_ownership:" in aggregate_block
    assert "  `none`" in aggregate_block
    assert "- field_groups:" in aggregate_block
    assert "- field_statuses:" in aggregate_block
    assert "    - OPENROUTER_API_KEY_FILE:" in aggregate_block
    assert "      - proof_id: `provider-backed-live-voice-proof`" in aggregate_block
    assert "      - proof_input_role: `provider_credential`" in aggregate_block
    assert "    - OPENROUTER_LIVEKIT_URL:" in aggregate_block
    assert "      - proof_input_role: `transport_endpoint`" in aggregate_block
    assert "    - PUBLICATION_DURABLE_PLATFORM_ID_OR_URL:" in aggregate_block
    assert "      - proof_id: `external-publication-proof`" in aggregate_block
    assert "      - proof_input_role: `publication_destination`" in aggregate_block
    assert "readable local secret file path; file content is never emitted" in (
        aggregate_block
    )
    assert "secret_file_unavailable" in aggregate_block
    assert "endpoint_url" in aggregate_block
    assert "  - placeholder_fields:" in aggregate_block
    assert "  - unavailable_secret_file_fields:" in aggregate_block
    assert "  - invalid_fields:" in aggregate_block
    assert "  - missing_fields:" in aggregate_block
    assert "per-proof operator input route commands:" in readme
    operator_route_block = readme.split(
        "- per-proof operator input route commands:",
        1,
    )[1].split("- required evidence after input unblock:", 1)[0]
    assert operator_route_block.count("    - next_action_commands:") == 2
    assert operator_route_block.count("    - guarded_next_action_commands:") == 2
    assert operator_route_block.count("    - status: `blocked_by_operator_inputs`") == 2
    assert operator_route_block.count("    - checked_at: `2026-05-20`") == 2
    assert operator_route_block.count("    - evidence_ref: `operator-input-readiness.json`") == 2
    assert (
        "    - next_action: `supply_openrouter_and_livekit_inputs`"
        in operator_route_block
    )
    assert (
        "    - next_action: `supply_linkedin_token_policy_destination_and_rollback_evidence`"
        in operator_route_block
    )
    assert operator_route_block.count(
        "    - effective_fail_on_blocked_exit_code: `2`"
    ) == 2
    assert operator_route_block.count("    - blocked_fields:") == 2
    assert operator_route_block.count("    - required_fields:") == 2
    assert operator_route_block.count("    - configured_fields:") == 2
    assert operator_route_block.count("    - field_contracts:") == 2
    assert operator_route_block.count("    - field_ownership:") == 2
    assert operator_route_block.count("    - field_statuses:") == 2
    assert "      - OPENROUTER_API_KEY_FILE:" in operator_route_block
    assert "        - proof_input_role: `provider_credential`" in operator_route_block
    assert "      - OPENROUTER_LIVEKIT_URL:" in operator_route_block
    assert "        - proof_input_role: `transport_endpoint`" in operator_route_block
    assert "      - PUBLICATION_DURABLE_PLATFORM_ID_OR_URL:" in operator_route_block
    assert "        - proof_input_role: `publication_destination`" in operator_route_block
    assert operator_route_block.count("    - issue_codes:") == 2
    assert operator_route_block.count("    - field_groups:") == 2
    assert "readable local secret file path; file content is never emitted" in (
        operator_route_block
    )
    assert "secret_file_unavailable" in operator_route_block
    assert "endpoint_url" in operator_route_block
    assert "      - placeholder_fields:" in operator_route_block
    assert "      - unavailable_secret_file_fields:" in operator_route_block
    assert "      - invalid_fields:" in operator_route_block
    assert "      - missing_fields:" in operator_route_block
    assert "`operator_input_secret_file_unavailable`" in operator_route_block
    assert "`operator_input_placeholder`" in operator_route_block
    assert (
        "provider-proof-operator-input-readiness "
        "--run-id 123e4567-e89b-12d3-a456-426614174000 "
        f"--input-path {shlex.quote(str(output_dir / 'operator-inputs.template.env'))} > "
        f"{shlex.quote(str(output_dir / 'operator-input-readiness.json'))}"
    ) in operator_route_block
    assert (
        "provider-proof-operator-input-readiness "
        "--run-id 123e4567-e89b-12d3-a456-426614174000 "
        f"--input-path {shlex.quote(str(output_dir / 'operator-inputs.template.env'))} "
        f"--fail-on-blocked > {shlex.quote(str(output_dir / 'operator-input-readiness.json'))}"
    ) in operator_route_block
    assert "required evidence after input unblock:" in readme
    assert "provider-backed-live-voice-proof:" in readme
    assert "same-run OpenRouter DeepSeek live dialogue reasoning evidence" in readme
    assert "external-publication-proof:" in readme
    assert "rollback or postcondition artifact" in readme
    assert readme.count("- proof_record_schema:") == 4
    assert "  - artifact_type: `provider_backed_live_voice_proof_record`" in readme
    assert "  - state_field: `provider-backed-live-voice-proof`" in readme
    assert "  - artifact_type: `external_publication_proof_record`" in readme
    assert "  - state_field: `external-publication-proof`" in readme
    assert readme.count("  - allowed_outcomes:") == 4
    assert readme.count("- proof_record_required_fields:") == 4
    assert "  `voice_agent_process_start_artifact_id`" in readme
    assert "  `durable_platform_id_or_url`" in readme
    assert readme.count("- proof_capture_commands_after_unblock:") == 4
    assert readme.count("operator_proof_packet:") == 2
    _assert_operator_packet_capture_commands(readme)
    _assert_operator_packet_closeout_refs(readme)
    _assert_operator_packet_record_schema(readme)
    _assert_operator_packet_input_contracts(readme)
    _assert_operator_packet_field_ownership(readme)
    _assert_operator_packet_field_statuses(readme)
    assert "- proof_id: `provider-backed-live-voice-proof`" in readme
    assert "- proof_id: `external-publication-proof`" in readme
    assert readme.count("- matrix_parity_ref:") == 2
    assert (
        "- matrix_parity_ref: "
        "`/operator_input_readiness/proofs/provider-backed-live-voice-proof`"
    ) in readme
    assert (
        "- matrix_parity_ref: "
        "`/operator_input_readiness/proofs/external-publication-proof`"
    ) in readme
    assert readme.count("- proof_capture_matrix_ref:") == 2
    assert (
        "- proof_capture_matrix_ref: "
        "`/proofs/provider-backed-live-voice-proof/proof_capture_commands_after_unblock`"
    ) in readme
    assert (
        "- proof_capture_matrix_ref: "
        "`/proofs/external-publication-proof/proof_capture_commands_after_unblock`"
    ) in readme
    assert "- label: `Provider-backed live voice proof packet`" in readme
    assert "- label: `External publication proof packet`" in readme
    assert "- packet_schema_version: `operator-proof-packet.v1`" in readme
    assert "- handoff_contract: `value-free-operator-proof-handoff`" in readme
    assert "- state_change_allowed: `False`" in readme
    assert "- secret_handling: `Do not print tokens, API keys, or secrets; record endpoint and account identifiers only.`" in readme
    assert readme.count("- source_artifacts:") == 2
    assert "  - operator_input_readiness: `operator-input-readiness.json`" in readme
    assert "  - current_blocker_matrix: `current-blocker-matrix.json`" in readme
    assert "  - operator_input_template: `operator-inputs.template.env`" in readme
    assert "  - proof_plan: `proof-plan.json`" in readme
    assert readme.count("- proof_plan_packet: `proof-plan.json`") == 2
    assert (
        f"- proof_plan_packet_ref: `{output_dir / 'proof-plan.json'}`"
    ) in readme
    assert (
        "- proof_plan_packet_command: `uv run all-about-llms-admin "
        "provider-proof-plan --run-id 123e4567-e89b-12d3-a456-426614174000 "
        f"--operator-input-path {shlex.quote(str(output_dir / 'operator-inputs.template.env'))} "
        f"> {shlex.quote(str(output_dir / 'proof-plan.json'))}`"
    ) in readme
    assert (
        "- proof_plan_operator_packet_ref: "
        "`/proofs/provider-backed-live-voice-proof/operator_proof_packet`"
    ) in readme
    assert (
        "- proof_plan_operator_packet_ref: "
        "`/proofs/external-publication-proof/operator_proof_packet`"
    ) in readme
    assert readme.count("- current_matrix_packet: `current-blocker-matrix.json`") == 2
    assert (
        f"- current_matrix_packet_ref: `{output_dir / 'current-blocker-matrix.json'}`"
    ) in readme
    assert (
        "- current_matrix_packet_command: `uv run all-about-llms-admin "
        "provider-proof-current-blocker-matrix "
        "--run-id 123e4567-e89b-12d3-a456-426614174000 "
        f"--output-dir {shlex.quote(str(output_dir))} > "
        f"{shlex.quote(str(output_dir / 'current-blocker-matrix.json'))}`"
    ) in readme
    assert (
        "- current_matrix_operator_packet_ref: "
        "`/operator_proof_packets/provider-backed-live-voice-proof`"
    ) in readme
    assert (
        "- current_matrix_operator_packet_ref: "
        "`/operator_proof_packets/external-publication-proof`"
    ) in readme
    assert readme.count("- current_gate_recovery_authority:") == 2
    assert (
        "open current_matrix_packet_ref at current_matrix_operator_packet_ref "
        "for current_gate, completion_next_action, and completion recovery commands"
    ) in readme
    assert "- next_status_packet: `current-proof-status.md`" in readme
    assert "- next_operator_packet: `operator-unblocker-checklist.md`" in readme
    assert "- must_capture:" in readme
    assert "`LiveKit room/session id and participant identity`" in readme
    assert "`durable platform ID or URL`" in readme
    assert "- store_in:" in readme
    assert "`social_media_optimiser/wiki/ops/active-codex-context.md`" in readme
    assert "blocker-credential-snapshot --operator-input-path" in readme
    assert "provider-proof-plan --run-id" in readme
    assert "--operator-input-path" in readme
    assert "Run these commands from the repository root." in readme
    assert "attempt gate:" in readme
    assert "state: blocked_by_credentials" in readme
    assert "can_run_preflight_capture: false" in readme
    assert "credential setup requirements:" in readme
    assert "configure OPENROUTER_API_KEY_FILE or OPENROUTER_API_KEY" in readme
    assert "configure OPENROUTER_LIVEKIT_URL" in readme
    assert "configure GEMMA4_MULTIMODAL_ENDPOINT_URL" not in readme
    assert "configure HF_TOKEN_FILE or HF_TOKEN" not in readme
    assert "configure LIVEKIT_API_KEY_FILE or LIVEKIT_API_KEY" in readme
    assert (
        "configure LINKEDIN_ACCESS_TOKEN_FILE or LINKEDIN_ACCESS_TOKEN" in readme
    )
    assert (
        "configure INSTAGRAM_ACCESS_TOKEN_FILE or INSTAGRAM_ACCESS_TOKEN"
        not in readme
    )
    assert "configure SUBSTACK_API_TOKEN_FILE or SUBSTACK_API_TOKEN" not in readme
    assert "credential setup commands:" in readme
    assert ': "${OPENROUTER_API_KEY:?set OPENROUTER_API_KEY first}"' in readme
    assert ': "${LIVEKIT_API_SECRET:?set LIVEKIT_API_SECRET first}"' in readme
    assert ': "${LINKEDIN_ACCESS_TOKEN:?set LINKEDIN_ACCESS_TOKEN first}"' in readme
    assert ': "${INSTAGRAM_ACCESS_TOKEN:?set INSTAGRAM_ACCESS_TOKEN first}"' not in readme
    assert "X_API_KEY" not in readme
    assert ".secrets/x_api_key" not in readme
    assert "proof commands allowed after:" in readme
    assert "validate-provider-proof-record" in readme
    assert "record-provider-proof-record" in readme
    assert "provider-proof-completion-status" in readme
    assert "provider-proof-closure-review-template" in readme
    assert "validate-provider-proof-closure-review" in readme
    assert "record-provider-proof-closure-review" in readme
    assert "provider-proof-closure-review-status" in readme
    assert "record-provider-proof-blocker-state-update" in readme
    assert "provider-proof-current-blocker-matrix" in readme
    assert "provider-proof-current-status" in readme
    assert "provider-proof-operator-unblocker-checklist" in readme
    assert "current-blocker-matrix.json" in readme
    assert "current-proof-status.md" in readme
    assert "operator-unblocker-checklist.md" in readme
    assert "validate-provider-proof-workspace" in readme
    assert "validate-provider-proof-preflight-artifacts" in readme
    assert "curl -sS http://127.0.0.1:8000/api/provider-readiness" in readme
    assert (
        "curl -sS -X POST "
        "http://127.0.0.1:8000/api/runs/123e4567-e89b-12d3-a456-426614174000/publish-readiness"
    ) in readme
    assert "provider-readiness.preflight.json" in readme
    assert "voice-runtime-readiness.preflight.json" in readme
    assert "publish-readiness.preflight.json" in readme
    assert (
        shlex.quote(str(output_dir / "provider-readiness.preflight.json"))
        in readme
    )
    assert (
        shlex.quote(str(output_dir / "voice-runtime-readiness.preflight.json"))
        in readme
    )
    assert (
        shlex.quote(str(output_dir / "publish-readiness.preflight.json"))
        in readme
    )
    voice_report_path = (
        output_dir / "provider-backed-live-voice-proof.preflight-validation.json"
    )
    publication_report_path = (
        output_dir / "external-publication-proof.preflight-validation.json"
    )
    assert "preflight validation report files:" in readme
    assert "preflight validation requirements:" in readme
    assert (
        "provider-readiness.preflight.json must select ready openrouter-livekit"
        in readme
    )
    assert (
        "voice-runtime-readiness.preflight.json must be ready for "
        "openrouter_livekit"
    ) in readme
    assert (
        "publish-readiness.preflight.json status must be ready with "
        "ready=true and no top-level or channel blocking issues, or "
        "needs_review with ready=false and only "
        "publish_channel_policy_review_required"
    ) in readme
    assert (
        "publish-readiness.preflight.json must include one normalized, "
        "non-empty supported publish_channel_checks entry per channel"
    ) in readme
    assert (
        "publish channel policy status must be acknowledged when status is "
        "ready; policy-review handoff must include at least one "
        "needs_review channel policy, channel blockers must be empty or "
        "policy-review-only, and acknowledged channels must not carry "
        "policy-review blockers"
        in readme
    )
    assert "publish readiness must not open a feedback gate" in readme
    publication_readme_section = readme.split("## external-publication-proof", 1)[
        1
    ].split("## Completion status", 1)[0]
    publication_capture_block = publication_readme_section.split(
        "- proof_capture_commands_after_unblock:",
        1,
    )[1].split("- validate preflight artifacts:", 1)[0]
    assert '"acknowledge_publish_channel_policy":true' in publication_capture_block
    assert '"acknowledge_publish_channel_policy":false' not in publication_capture_block
    assert shlex.quote(str(voice_report_path)) in readme
    assert shlex.quote(str(publication_report_path)) in readme
    assert f"> {shlex.quote(str(voice_report_path))}" in readme
    assert f"> {shlex.quote(str(publication_report_path))}" in readme
    assert (
        "--preflight-validation-path "
        f"{shlex.quote(str(voice_report_path))}"
    ) in readme
    assert (
        "--preflight-validation-path "
        f"{shlex.quote(str(publication_report_path))}"
    ) in readme
    assert "<preflight-validation.json>" not in readme
    assert (
        "validate-provider-proof-preflight-artifacts --proof "
        "provider-backed-live-voice-proof --run-id 123e4567-e89b-12d3-a456-426614174000 --preflight-dir "
        f"{shlex.quote(str(output_dir))}"
    ) in readme
    assert (
        "validate-provider-proof-preflight-artifacts --proof "
        "external-publication-proof --run-id 123e4567-e89b-12d3-a456-426614174000 --preflight-dir "
        f"{shlex.quote(str(output_dir))}"
    ) in readme
    assert (
        "social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000/"
        "provider-readiness.preflight.json"
        not in readme
    )
    assert "goal_completion_claimed=false" in readme
    assert "does not mark the active objective complete" in readme


def test_concrete_provider_proof_workspace_matches_current_plan():
    output_dir = (
        ROOT
        / "social_media_optimiser/output/provider-proof/RUN-2026-05-20-NEXT"
    )

    payload = provider_cli._provider_proof_workspace_validation_payload(
        Namespace(
            env_example_path=ROOT / ".env.example",
            checked_at="2026-05-20",
            run_id="RUN-2026-05-20-NEXT",
            output_dir=output_dir,
        ),
        env_values={},
    )

    assert payload["status"] == "blocked_by_run_id"
    assert payload["issue_codes"] == ["run_id_not_product_uuid"]


def test_concrete_provider_proof_workspace_readme_uses_portable_paths():
    output_dir = (
        ROOT
        / "social_media_optimiser/output/provider-proof/RUN-2026-05-20-NEXT"
    )
    readme = (output_dir / "README.md").read_text(encoding="utf-8")

    assert str(ROOT) not in readme
    assert "status: blocked_by_run_id" in readme
    assert "product_run_id_state: non_uuid_run_id" in readme
    assert "Do not run provider preflight" in readme
    assert "Create or select a durable product run UUID first:" in readme
    assert "POST /api/runs" in readme
    assert "product-run.create.json" in readme
    assert "init-provider-proof-workspace-from-bootstrap" in readme
    assert readme.count("- proof_record_schema:") == 4
    assert "  - artifact_type: `provider_backed_live_voice_proof_record`" in readme
    assert "  - state_field: `provider-backed-live-voice-proof`" in readme
    assert "  - artifact_type: `external_publication_proof_record`" in readme
    assert "  - state_field: `external-publication-proof`" in readme
    assert "RUN-2026-05-20-NEXT/publish-readiness" not in readme


def test_concrete_uuid_provider_proof_workspace_readme_is_current():
    run_id = "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e"
    relative_output_dir = Path("social_media_optimiser/output/provider-proof") / run_id
    readme_path = ROOT / relative_output_dir / "README.md"

    readme = readme_path.read_text(encoding="utf-8")
    proof_plan = provider_cli._provider_proof_plan_payload(
        Namespace(
            env_example_path=ROOT / ".env.example",
            checked_at="2026-05-24",
            run_id=run_id,
            output_dir=ROOT / relative_output_dir,
            operator_input_path=ROOT / relative_output_dir / "operator-inputs.template.env",
        ),
        env_values={},
    )
    fresh_readme = provider_cli._provider_proof_workspace_readme(
        proof_plan=proof_plan,
        template_payloads=[
            (
                proof_name,
                relative_output_dir / f"{proof_name}.template.json",
                {},
            )
            for proof_name in proof_plan["proofs"]
        ],
    )

    assert readme == fresh_readme
    assert str(ROOT) not in readme
    assert "- aggregate operator input readiness:" in readme
    aggregate_block = readme.split(
        "- aggregate operator input readiness:",
        1,
    )[1].split("- per-proof operator input route commands:", 1)[0]
    assert "- blocked_fields:" in aggregate_block
    assert "- required_fields:" in aggregate_block
    assert "- configured_fields:" in aggregate_block
    assert "- field_contracts:" in aggregate_block
    assert "- field_ownership:" in aggregate_block
    assert "- field_groups:" in aggregate_block
    assert "- field_statuses:" in aggregate_block
    assert "    - OPENROUTER_API_KEY_FILE:" in aggregate_block
    assert "    - OPENROUTER_LIVEKIT_URL:" in aggregate_block
    assert "      - proof_id: `provider-backed-live-voice-proof`" in aggregate_block
    assert "      - proof_input_role: `provider_credential`" in aggregate_block
    assert "    - PUBLICATION_DURABLE_PLATFORM_ID_OR_URL:" in aggregate_block
    assert "      - proof_id: `external-publication-proof`" in aggregate_block
    assert "      - proof_input_role: `publication_destination`" in aggregate_block
    assert "readable local secret file path; file content is never emitted" in (
        aggregate_block
    )
    assert "secret_file_unavailable" in aggregate_block
    assert "OpenRouter-backed realtime dialogue" in aggregate_block
    assert "  - placeholder_fields:" in aggregate_block
    assert "  - unavailable_secret_file_fields:" in aggregate_block
    assert "  - invalid_fields:" in aggregate_block
    assert "  - missing_fields:" in aggregate_block
    operator_route_block = readme.split(
        "- per-proof operator input route commands:",
        1,
    )[1].split("- required evidence after input unblock:", 1)[0]
    assert operator_route_block.count("    - required_fields:") == 2
    assert operator_route_block.count("    - configured_fields:") == 2
    assert operator_route_block.count("    - status: `blocked_by_operator_inputs`") == 2
    assert operator_route_block.count("    - checked_at: `2026-05-23`") == 2
    assert operator_route_block.count("    - evidence_ref: `operator-input-readiness.json`") == 2
    assert (
        "    - next_action: `supply_openrouter_and_livekit_inputs`"
        in operator_route_block
    )
    assert (
        "    - next_action: `supply_linkedin_token_policy_destination_and_rollback_evidence`"
        in operator_route_block
    )
    assert operator_route_block.count(
        "    - effective_fail_on_blocked_exit_code: `2`"
    ) == 2
    assert operator_route_block.count("    - blocked_fields:") == 2
    assert operator_route_block.count("    - field_contracts:") == 2
    assert operator_route_block.count("    - field_ownership:") == 2
    assert operator_route_block.count("    - field_statuses:") == 2
    assert "      - OPENROUTER_API_KEY_FILE:" in operator_route_block
    assert "      - OPENROUTER_LIVEKIT_URL:" in operator_route_block
    assert "        - proof_input_role: `provider_credential`" in operator_route_block
    assert "      - PUBLICATION_DURABLE_PLATFORM_ID_OR_URL:" in operator_route_block
    assert "        - proof_input_role: `publication_destination`" in operator_route_block
    assert "secret_file_unavailable" in operator_route_block
    assert "- per-proof operator input route commands:" in readme
    assert "    - issue_codes:" in readme
    assert "    - field_groups:" in readme
    assert "    - next_action_commands:" in readme
    assert "    - guarded_next_action_commands:" in readme
    assert readme.count("- proof_record_schema:") == 4
    assert "  - artifact_type: `provider_backed_live_voice_proof_record`" in readme
    assert "  - state_field: `provider-backed-live-voice-proof`" in readme
    assert "  - artifact_type: `external_publication_proof_record`" in readme
    assert "  - state_field: `external-publication-proof`" in readme
    assert readme.count("  - allowed_outcomes:") == 4
    assert readme.count("- proof_record_required_fields:") == 4
    assert "  `voice_agent_process_start_artifact_id`" in readme
    assert "  `durable_platform_id_or_url`" in readme
    assert readme.count("- proof_capture_commands_after_unblock:") == 4
    assert readme.count("operator_proof_packet:") == 2
    _assert_operator_packet_capture_commands(readme)
    _assert_operator_packet_closeout_refs(readme)
    _assert_operator_packet_record_schema(readme)
    _assert_operator_packet_input_contracts(readme)
    _assert_operator_packet_field_ownership(readme)
    _assert_operator_packet_field_statuses(readme)
    assert "- proof_id: `provider-backed-live-voice-proof`" in readme
    assert "- proof_id: `external-publication-proof`" in readme
    assert readme.count("- matrix_parity_ref:") == 2
    assert (
        "- matrix_parity_ref: "
        "`/operator_input_readiness/proofs/provider-backed-live-voice-proof`"
    ) in readme
    assert (
        "- matrix_parity_ref: "
        "`/operator_input_readiness/proofs/external-publication-proof`"
    ) in readme
    assert readme.count("- proof_capture_matrix_ref:") == 2
    assert (
        "- proof_capture_matrix_ref: "
        "`/proofs/provider-backed-live-voice-proof/proof_capture_commands_after_unblock`"
    ) in readme
    assert (
        "- proof_capture_matrix_ref: "
        "`/proofs/external-publication-proof/proof_capture_commands_after_unblock`"
    ) in readme
    assert "- label: `Provider-backed live voice proof packet`" in readme
    assert "- label: `External publication proof packet`" in readme
    assert "- packet_schema_version: `operator-proof-packet.v1`" in readme
    assert "- handoff_contract: `value-free-operator-proof-handoff`" in readme
    assert "- state_change_allowed: `False`" in readme
    assert "- secret_handling: `Do not print tokens, API keys, or secrets; record endpoint and account identifiers only.`" in readme
    assert readme.count("- proof_plan_packet: `proof-plan.json`") == 2
    assert (
        "- proof_plan_packet_ref: `social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/proof-plan.json`"
    ) in readme
    assert (
        "- proof_plan_packet_command: `uv run all-about-llms-admin "
        "provider-proof-plan --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e "
        "--operator-input-path social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env "
        "> social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/proof-plan.json`"
    ) in readme
    assert (
        "- proof_plan_operator_packet_ref: "
        "`/proofs/provider-backed-live-voice-proof/operator_proof_packet`"
    ) in readme
    assert (
        "- proof_plan_operator_packet_ref: "
        "`/proofs/external-publication-proof/operator_proof_packet`"
    ) in readme
    assert readme.count("- current_matrix_packet: `current-blocker-matrix.json`") == 2
    assert (
        "- current_matrix_packet_ref: `social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-blocker-matrix.json`"
    ) in readme
    assert (
        "- current_matrix_packet_command: `uv run all-about-llms-admin "
        "provider-proof-current-blocker-matrix --run-id "
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e --output-dir "
        "social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e > "
        "social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-blocker-matrix.json`"
    ) in readme
    assert (
        "- current_matrix_operator_packet_ref: "
        "`/operator_proof_packets/provider-backed-live-voice-proof`"
    ) in readme
    assert (
        "- current_matrix_operator_packet_ref: "
        "`/operator_proof_packets/external-publication-proof`"
    ) in readme
    assert readme.count("- current_gate_recovery_authority:") == 2
    assert (
        "open current_matrix_packet_ref at current_matrix_operator_packet_ref "
        "for current_gate, completion_next_action, and completion recovery commands"
    ) in readme
    assert "- next_status_packet: `current-proof-status.md`" in readme
    assert "- next_operator_packet: `operator-unblocker-checklist.md`" in readme
    assert "- must_capture:" in readme
    assert "`LiveKit room/session id and participant identity`" in readme
    assert "`durable platform ID or URL`" in readme
    assert "- store_in:" in readme
    assert "`system_design_vault/04-agent-studio-implications/agent-studio-objective-completion-audit.md`" in readme
    publication_readme_section = readme.split("## external-publication-proof", 1)[
        1
    ].split("## Completion status", 1)[0]
    publication_capture_block = publication_readme_section.split(
        "- proof_capture_commands_after_unblock:",
        1,
    )[1].split("- validate preflight artifacts:", 1)[0]
    assert '"acknowledge_publish_channel_policy":true' in publication_capture_block
    assert '"acknowledge_publish_channel_policy":false' not in publication_capture_block


def test_concrete_uuid_provider_proof_workspace_validation_is_current():
    run_id = "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e"
    output_dir = ROOT / "social_media_optimiser/output/provider-proof" / run_id

    payload = provider_cli._provider_proof_workspace_validation_payload(
        Namespace(
            env_example_path=ROOT / ".env.example",
            checked_at="2026-05-24",
            run_id=run_id,
            output_dir=output_dir,
        ),
        env_values={},
    )

    assert payload["status"] == "valid_workspace"
    assert payload["issue_codes"] == []
    assert "workspace_file_mismatch" not in json.dumps(payload)
    assert (
        "<workspace-root>/social_media_optimiser/output/provider-proof/"
        f"{run_id}/provider-backed-live-voice-proof.template.json"
    ) in payload["validated_files"]


def test_concrete_provider_proof_workspace_validation_report_is_current():
    output_dir = (
        ROOT
        / "social_media_optimiser/output/provider-proof/RUN-2026-05-20-NEXT"
    )
    report_path = output_dir / "workspace-validation.json"

    report = json.loads(report_path.read_text(encoding="utf-8"))
    fresh_payload = provider_cli._provider_proof_workspace_validation_payload(
        Namespace(
            env_example_path=ROOT / ".env.example",
            checked_at="2026-05-20",
            run_id="RUN-2026-05-20-NEXT",
            output_dir=output_dir,
        ),
        env_values={},
    )

    assert report == fresh_payload
    assert report["artifact"] == "agent-studio-provider-proof-workspace-validation"
    assert report["run_id"] == "<run-id>"
    assert report["status"] == "blocked_by_run_id"
    assert report["issue_codes"] == ["run_id_not_product_uuid"]
    assert report["state_change_allowed"] is False
    serialized_report = json.dumps(report)
    assert str(ROOT) not in serialized_report
    assert report["output_dir"] == (
        "<workspace-root>/social_media_optimiser/output/provider-proof/"
        "RUN-2026-05-20-NEXT"
    )
    assert report["validated_files"] == []


def test_concrete_provider_proof_plan_uses_portable_credential_source():
    payload = _provider_proof_plan_payload(
        Namespace(
            env_example_path=ROOT / ".env.example",
            checked_at="2026-05-20",
            run_id="RUN-2026-05-20-NEXT",
        ),
        env_values=_no_local_secret_file_env_values(),
    )
    credential_snapshot = payload["credential_snapshot"]

    assert credential_snapshot["source"] == "<workspace-root>/.env.example"
    assert str(ROOT) not in json.dumps(credential_snapshot)


def test_concrete_blocker_credential_snapshot_report_is_current():
    output_dir = (
        ROOT
        / "social_media_optimiser/output/provider-proof/RUN-2026-05-20-NEXT"
    )
    report_path = output_dir / "credential-snapshot.json"

    report = json.loads(report_path.read_text(encoding="utf-8"))
    fresh_payload = provider_cli._blocker_credential_snapshot_payload(
        Namespace(
            env_example_path=ROOT / ".env.example",
            checked_at="2026-05-20",
        ),
        env_values=_no_local_secret_file_env_values(),
    )

    assert report == fresh_payload
    assert report["artifact"] == "agent-studio-blocker-credential-snapshots"
    assert report["source"] == "<workspace-root>/.env.example"
    assert report["boundary"] == "no_secret_values_printed"
    assert report["snapshots"]["provider-backed-live-voice-proof"]["state"] == (
        "blocked_by_placeholder_only_configuration"
    )
    assert report["snapshots"]["external-publication-proof"]["state"] == (
        "blocked_by_placeholder_only_configuration"
    )
    assert report["snapshots"]["provider-backed-live-voice-proof"][
        "configured_inputs"
    ] == []
    assert report["snapshots"]["external-publication-proof"][
        "configured_file_inputs"
    ] == []
    assert str(ROOT) not in json.dumps(report)


def test_concrete_current_uuid_blocker_credential_snapshot_report_is_current():
    output_dir = (
        ROOT
        / (
            "social_media_optimiser/output/provider-proof/"
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e"
        )
    )
    report_path = output_dir / "credential-snapshot.json"

    report = json.loads(report_path.read_text(encoding="utf-8"))
    fresh_payload = provider_cli._blocker_credential_snapshot_payload(
        Namespace(
            env_example_path=ROOT / ".env.example",
            checked_at="2026-05-24",
            operator_input_path=output_dir / "operator-inputs.template.env",
        ),
        env_values={},
    )

    assert report == fresh_payload
    assert report["artifact"] == "agent-studio-blocker-credential-snapshots"
    assert report["source"] == "<workspace-root>/.env.example"
    assert report["boundary"] == "no_secret_values_printed"
    assert report["snapshots"]["provider-backed-live-voice-proof"]["state"] == (
        "runtime_configuration_present_unverified"
    )
    assert report["snapshots"]["external-publication-proof"]["state"] == (
        "blocked_by_placeholder_only_configuration"
    )
    assert report["snapshots"]["provider-backed-live-voice-proof"][
        "configured_inputs"
    ] == ["OPENROUTER_LIVEKIT_URL"]
    assert str(ROOT) not in json.dumps(report)


def test_concrete_current_uuid_operator_input_template_is_present():
    output_dir = (
        ROOT
        / (
            "social_media_optimiser/output/provider-proof/"
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e"
        )
    )
    template = (output_dir / "operator-inputs.template.env").read_text(
        encoding="utf-8"
    )

    assert "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key" in template
    assert "OPENROUTER_LIVEKIT_URL=ws://127.0.0.1:7880" in template
    assert "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key" in template
    assert "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret" in template
    assert "LINKEDIN_ACCESS_TOKEN_FILE=.secrets/linkedin_access_token" in template
    assert "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID=<artifact-id>" in template
    assert "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL=<external-url-or-id>" in template
    assert "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID=<artifact-id>" in template
    assert "# Provider-backed live voice proof blockers." not in template
    assert "# Provider-backed live voice proof default inputs." in template
    assert "# External publication proof blockers." in template
    assert template.count("# contract: ") == 8
    assert template.count("# value_source: ") == 8
    assert template.count("# template_state: ") == 8
    assert template.count("# issue_code: ") == 8
    assert template.count("# next_action: ") == 8
    assert template.count("# proof_id: ") == 8
    assert template.count("# proof_input_role: ") == 8
    assert (
        "# proof_id: provider-backed-live-voice-proof\n"
        "# proof_input_role: provider_credential"
    ) in template
    assert (
        "# proof_id: provider-backed-live-voice-proof\n"
        "# proof_input_role: transport_endpoint"
    ) in template
    assert (
        "# proof_id: provider-backed-live-voice-proof\n"
        "# proof_input_role: transport_credential"
    ) in template
    assert (
        "# proof_id: external-publication-proof\n"
        "# proof_input_role: publisher_credential"
    ) in template
    assert (
        "# proof_id: external-publication-proof\n"
        "# proof_input_role: publication_evidence"
    ) in template
    assert "readable local secret file path; file content is never emitted" in template
    assert "ws or wss LiveKit URL for OpenRouter-backed realtime dialogue" in template
    assert "# value_source: secret_file_path" in template
    assert "# value_source: endpoint_url" in template
    assert "# value_source: external_destination" in template
    assert "# value_source: artifact_id" in template
    assert "# template_state: secret_file_unavailable" in template
    assert "# template_state: placeholder" in template
    assert "# issue_code: operator_input_secret_file_unavailable" in template
    assert "# issue_code: operator_input_placeholder" in template
    assert "# next_action: write_readable_secret_file_and_reference_path" in template
    assert "# next_action: replace_placeholder_in_operator_input_file" in template
    assert "sk-" not in template
    assert "hf_secret" not in template
    assert "openrouter_secret" not in template
    assert "linkedin-configured" not in template
    assert str(ROOT) not in template


def test_concrete_current_uuid_operator_input_readiness_is_current():
    output_dir = (
        ROOT
        / (
            "social_media_optimiser/output/provider-proof/"
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e"
        )
    )
    report_path = output_dir / "operator-input-readiness.json"

    report = json.loads(report_path.read_text(encoding="utf-8"))
    fresh_payload = provider_cli._provider_proof_operator_input_readiness_payload(
        Namespace(
            env_example_path=ROOT / ".env.example",
            checked_at="2026-05-24",
            run_id="190ae2f9-a74b-4a23-b39c-aaf2d636bd8e",
            input_path=output_dir / "operator-inputs.template.env",
        )
    )
    serialized = json.dumps(report)

    assert report == fresh_payload
    assert report["status"] == "blocked_by_operator_inputs"
    assert report["state_change_allowed"] is False
    assert report["exit_policy"] == {
        "default_exit_code": 0,
        "fail_on_blocked_exit_code": 2,
        "fail_on_blocked_statuses": [
            "blocked_by_operator_inputs",
            "invalid_operator_input_file",
        ],
        "ready_status": "ready_for_credential_snapshot_refresh",
    }
    assert report["effective_fail_on_blocked_exit_code"] == 2
    assert "operator_input_placeholder" in report["issue_codes"]
    assert "operator_input_secret_file_unavailable" in report["issue_codes"]
    assert report["blocked_fields"] == [
        "LINKEDIN_ACCESS_TOKEN_FILE",
        "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID",
        "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL",
        "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID",
    ]
    assert report["configured_fields"] == [
        "OPENROUTER_API_KEY_FILE",
        "OPENROUTER_LIVEKIT_URL",
        "LIVEKIT_API_KEY_FILE",
        "LIVEKIT_API_SECRET_FILE",
    ]
    assert report["field_groups"] == {
        "missing_fields": [],
        "placeholder_fields": [
            "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID",
            "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL",
            "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID",
        ],
        "invalid_fields": [],
        "unavailable_secret_file_fields": [
            "LINKEDIN_ACCESS_TOKEN_FILE",
        ],
    }
    assert report["required_fields"] == [
        "OPENROUTER_API_KEY_FILE",
        "OPENROUTER_LIVEKIT_URL",
        "LIVEKIT_API_KEY_FILE",
        "LIVEKIT_API_SECRET_FILE",
        "LINKEDIN_ACCESS_TOKEN_FILE",
        "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID",
        "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL",
        "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID",
    ]
    assert report["field_contracts"]["OPENROUTER_API_KEY_FILE"] == (
        "readable local secret file path; file content is never emitted"
    )
    assert report["field_contracts"]["PUBLICATION_DURABLE_PLATFORM_ID_OR_URL"] == (
        "durable LinkedIn URL or platform id; local substitutes rejected"
    )
    assert report["field_ownership"]["OPENROUTER_API_KEY_FILE"] == {
        "proof_id": "provider-backed-live-voice-proof",
        "proof_input_role": "provider_credential",
    }
    assert report["field_ownership"]["PUBLICATION_DURABLE_PLATFORM_ID_OR_URL"] == {
        "proof_id": "external-publication-proof",
        "proof_input_role": "publication_destination",
    }
    assert report["field_statuses"]["OPENROUTER_API_KEY_FILE"]["state"] == "configured"
    assert report["field_statuses"]["OPENROUTER_API_KEY_FILE"]["proof_id"] == (
        "provider-backed-live-voice-proof"
    )
    assert report["field_statuses"]["OPENROUTER_API_KEY_FILE"]["proof_input_role"] == (
        "provider_credential"
    )
    assert report["field_statuses"]["PUBLICATION_DURABLE_PLATFORM_ID_OR_URL"][
        "value_source"
    ] == "external_destination"
    assert report["field_statuses"]["PUBLICATION_DURABLE_PLATFORM_ID_OR_URL"][
        "proof_id"
    ] == "external-publication-proof"
    assert report["field_statuses"]["PUBLICATION_DURABLE_PLATFORM_ID_OR_URL"][
        "proof_input_role"
    ] == "publication_destination"
    assert report["proofs"]["provider-backed-live-voice-proof"]["blocked_fields"] == []
    assert report["proofs"]["external-publication-proof"]["blocked_fields"] == [
        "LINKEDIN_ACCESS_TOKEN_FILE",
        "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID",
        "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL",
        "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID",
    ]
    assert report["proofs"]["provider-backed-live-voice-proof"]["field_contracts"] == {
        "OPENROUTER_API_KEY_FILE": (
            "readable local secret file path; file content is never emitted"
        ),
        "OPENROUTER_LIVEKIT_URL": (
            "ws or wss LiveKit URL for OpenRouter-backed realtime dialogue"
        ),
        "LIVEKIT_API_KEY_FILE": (
            "readable local secret file path; file content is never emitted"
        ),
        "LIVEKIT_API_SECRET_FILE": (
            "readable local secret file path; file content is never emitted"
        ),
    }
    assert report["proofs"]["provider-backed-live-voice-proof"]["field_ownership"] == {
        "OPENROUTER_API_KEY_FILE": {
            "proof_id": "provider-backed-live-voice-proof",
            "proof_input_role": "provider_credential",
        },
        "OPENROUTER_LIVEKIT_URL": {
            "proof_id": "provider-backed-live-voice-proof",
            "proof_input_role": "transport_endpoint",
        },
        "LIVEKIT_API_KEY_FILE": {
            "proof_id": "provider-backed-live-voice-proof",
            "proof_input_role": "transport_credential",
        },
        "LIVEKIT_API_SECRET_FILE": {
            "proof_id": "provider-backed-live-voice-proof",
            "proof_input_role": "transport_credential",
        },
    }
    voice_field_statuses = report["proofs"]["provider-backed-live-voice-proof"][
        "field_statuses"
    ]
    assert voice_field_statuses["OPENROUTER_API_KEY_FILE"] == {
        "state": "configured",
        "issue_code": "none",
        "proof_id": "provider-backed-live-voice-proof",
        "proof_input_role": "provider_credential",
        "value_source": "secret_file_path",
        "next_action": "refresh_credential_snapshot",
        "contract": "readable local secret file path; file content is never emitted",
    }
    assert voice_field_statuses["OPENROUTER_LIVEKIT_URL"] == {
        "state": "configured",
        "issue_code": "none",
        "proof_id": "provider-backed-live-voice-proof",
        "proof_input_role": "transport_endpoint",
        "value_source": "endpoint_url",
        "next_action": "refresh_credential_snapshot",
        "contract": "ws or wss LiveKit URL for OpenRouter-backed realtime dialogue",
    }
    assert report["proofs"]["external-publication-proof"]["field_contracts"] == {
        "LINKEDIN_ACCESS_TOKEN_FILE": (
            "readable local secret file path; file content is never emitted"
        ),
        "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID": (
            "durable non-local policy acknowledgement artifact id or URL"
        ),
        "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL": (
            "durable LinkedIn URL or platform id; local substitutes rejected"
        ),
        "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID": (
            "durable non-local rollback or postcondition artifact id or URL"
        ),
    }
    assert report["proofs"]["external-publication-proof"]["field_ownership"][
        "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL"
    ] == {
        "proof_id": "external-publication-proof",
        "proof_input_role": "publication_destination",
    }
    publication_field_statuses = report["proofs"]["external-publication-proof"][
        "field_statuses"
    ]
    assert publication_field_statuses["PUBLICATION_DURABLE_PLATFORM_ID_OR_URL"] == {
        "state": "placeholder",
        "issue_code": "operator_input_placeholder",
        "proof_id": "external-publication-proof",
        "proof_input_role": "publication_destination",
        "value_source": "external_destination",
        "next_action": "replace_placeholder_in_operator_input_file",
        "contract": "durable LinkedIn URL or platform id; local substitutes rejected",
    }
    assert "OPENROUTER_LIVEKIT_URL" in serialized
    assert "<ws-or-wss-url>" not in serialized
    assert ".secrets/openrouter_api_key" not in serialized
    assert ".secrets/livekit_api_key" not in serialized
    assert ".secrets/livekit_api_secret" not in serialized
    assert str(ROOT) not in serialized


def test_provider_proof_operator_input_readiness_blocks_placeholder_template(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("", encoding="utf-8")
    input_path = tmp_path / "operator-inputs.template.env"
    input_path.write_text(
        provider_cli._provider_proof_operator_inputs_template(),
        encoding="utf-8",
    )
    template = input_path.read_text(encoding="utf-8")

    payload = provider_cli._provider_proof_operator_input_readiness_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-21",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            input_path=input_path,
        )
    )
    serialized = json.dumps(payload)

    assert payload["artifact"] == "agent-studio-provider-proof-operator-input-readiness"
    assert payload["boundary"] == "no_secret_values_printed_no_state_change"
    assert payload["status"] == "blocked_by_operator_inputs"
    assert payload["state_change_allowed"] is False
    assert payload["exit_policy"]["fail_on_blocked_exit_code"] == 2
    assert "operator_input_placeholder" in payload["issue_codes"]
    assert "operator_input_secret_file_unavailable" in payload["issue_codes"]
    assert payload["proofs"]["provider-backed-live-voice-proof"]["state"] == (
        "blocked_by_operator_inputs"
    )
    assert payload["proofs"]["external-publication-proof"]["state"] == (
        "blocked_by_operator_inputs"
    )
    assert payload["proofs"]["provider-backed-live-voice-proof"]["blocked_fields"] == [
        "OPENROUTER_API_KEY_FILE",
        "LIVEKIT_API_KEY_FILE",
        "LIVEKIT_API_SECRET_FILE",
    ]
    assert payload["proofs"]["external-publication-proof"]["blocked_fields"] == [
        "LINKEDIN_ACCESS_TOKEN_FILE",
        "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID",
        "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL",
        "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID",
    ]
    assert payload["proofs"]["provider-backed-live-voice-proof"]["field_contracts"] == {
        "OPENROUTER_API_KEY_FILE": (
            "readable local secret file path; file content is never emitted"
        ),
        "OPENROUTER_LIVEKIT_URL": (
            "ws or wss LiveKit URL for OpenRouter-backed realtime dialogue"
        ),
        "LIVEKIT_API_KEY_FILE": (
            "readable local secret file path; file content is never emitted"
        ),
        "LIVEKIT_API_SECRET_FILE": (
            "readable local secret file path; file content is never emitted"
        ),
    }
    assert payload["proofs"]["external-publication-proof"]["field_contracts"][
        "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL"
    ] == "durable LinkedIn URL or platform id; local substitutes rejected"
    assert payload["proofs"]["provider-backed-live-voice-proof"]["field_statuses"][
        "OPENROUTER_API_KEY_FILE"
    ]["state"] == "secret_file_unavailable"
    assert payload["proofs"]["provider-backed-live-voice-proof"]["field_statuses"][
        "OPENROUTER_LIVEKIT_URL"
    ]["value_source"] == "endpoint_url"
    assert payload["proofs"]["external-publication-proof"]["field_statuses"][
        "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID"
    ]["value_source"] == "artifact_id"
    assert "OPENROUTER_API_KEY_FILE" in serialized
    assert "# Provider-backed live voice proof blockers." not in template
    assert "# Provider-backed live voice proof default inputs." in template
    assert "# External publication proof blockers." in template
    assert "<https-url>" not in serialized
    assert ".secrets/hf_token" not in serialized
    assert str(ROOT) not in serialized


def test_provider_proof_operator_input_readiness_cli_can_fail_on_blocked(
    tmp_path,
    capsys,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("", encoding="utf-8")
    input_path = tmp_path / "operator-inputs.template.env"
    input_path.write_text(
        provider_cli._provider_proof_operator_inputs_template(),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as exc:
        provider_cli._print_provider_proof_operator_input_readiness(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-21",
                run_id=PROVIDER_PROOF_TEST_RUN_UUID,
                input_path=input_path,
                fail_on_blocked=True,
            )
        )
    payload = json.loads(capsys.readouterr().out)

    assert exc.value.code == 2
    assert payload["status"] == "blocked_by_operator_inputs"
    assert payload["state_change_allowed"] is False
    assert "operator_input_placeholder" in payload["issue_codes"]


def test_provider_proof_operator_input_readiness_cli_fail_on_blocked_marks_invalid_file_next_action(
    tmp_path,
    capsys,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("", encoding="utf-8")
    input_path = tmp_path / "missing.env"

    with pytest.raises(SystemExit) as exc:
        provider_cli._print_provider_proof_operator_input_readiness(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-21",
                run_id=PROVIDER_PROOF_TEST_RUN_UUID,
                input_path=input_path,
                fail_on_blocked=True,
            )
        )
    payload = json.loads(capsys.readouterr().out)

    assert exc.value.code == 2
    assert payload["status"] == "invalid_operator_input_file"
    assert payload["issue_codes"] == ["operator_input_file_missing"]
    assert payload["next_action"] == "fix_operator_input_file"
    assert payload["effective_fail_on_blocked_exit_code"] == 2


def test_provider_proof_operator_input_readiness_accepts_filled_no_secret_file(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("", encoding="utf-8")
    secret_dir = tmp_path / ".secrets"
    secret_dir.mkdir()
    (secret_dir / "openrouter_api_key").write_text(
        "openrouter_secret_token\n",
        encoding="utf-8",
    )
    (secret_dir / "livekit_api_key").write_text(
        "livekit_key_secret\n",
        encoding="utf-8",
    )
    (secret_dir / "livekit_api_secret").write_text(
        "livekit_secret_token\n",
        encoding="utf-8",
    )
    (secret_dir / "linkedin_access_token").write_text(
        "linkedin_secret_token\n",
        encoding="utf-8",
    )
    input_path = tmp_path / "operator-inputs.local.env"
    input_path.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=ws://127.0.0.1:7880",
                "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key",
                "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret",
                "LINKEDIN_ACCESS_TOKEN_FILE=.secrets/linkedin_access_token",
                "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID="
                "linkedin-policy-acknowledgement-artifact-"
                f"{PROVIDER_PROOF_TEST_RUN_UUID}",
                (
                    "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL="
                    "https://www.linkedin.com/feed/update/urn:li:activity:123"
                ),
                "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID="
                "linkedin-rollback-postcondition-artifact-"
                f"{PROVIDER_PROOF_TEST_RUN_UUID}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_operator_input_readiness_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-21",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            input_path=input_path,
        )
    )
    serialized = json.dumps(payload)

    assert payload["status"] == "ready_for_credential_snapshot_refresh"
    assert payload["effective_fail_on_blocked_exit_code"] == 0
    assert payload["issue_codes"] == []
    assert payload["blocked_fields"] == []
    assert payload["configured_fields"] == [
        "OPENROUTER_API_KEY_FILE",
        "OPENROUTER_LIVEKIT_URL",
        "LIVEKIT_API_KEY_FILE",
        "LIVEKIT_API_SECRET_FILE",
        "LINKEDIN_ACCESS_TOKEN_FILE",
        "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID",
        "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL",
        "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID",
    ]
    assert payload["field_groups"] == {
        "missing_fields": [],
        "placeholder_fields": [],
        "invalid_fields": [],
        "unavailable_secret_file_fields": [],
    }
    assert payload["required_fields"] == [
        "OPENROUTER_API_KEY_FILE",
        "OPENROUTER_LIVEKIT_URL",
        "LIVEKIT_API_KEY_FILE",
        "LIVEKIT_API_SECRET_FILE",
        "LINKEDIN_ACCESS_TOKEN_FILE",
        "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID",
        "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL",
        "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID",
    ]
    assert payload["field_ownership"]["OPENROUTER_API_KEY_FILE"] == {
        "proof_id": "provider-backed-live-voice-proof",
        "proof_input_role": "provider_credential",
    }
    assert payload["field_ownership"]["PUBLICATION_DURABLE_PLATFORM_ID_OR_URL"] == {
        "proof_id": "external-publication-proof",
        "proof_input_role": "publication_destination",
    }
    assert payload["field_statuses"]["OPENROUTER_API_KEY_FILE"]["state"] == "configured"
    assert payload["field_statuses"]["OPENROUTER_API_KEY_FILE"]["proof_id"] == (
        "provider-backed-live-voice-proof"
    )
    assert payload["field_statuses"]["OPENROUTER_API_KEY_FILE"]["proof_input_role"] == (
        "provider_credential"
    )
    assert payload["field_statuses"]["PUBLICATION_DURABLE_PLATFORM_ID_OR_URL"][
        "state"
    ] == "configured"
    assert payload["field_statuses"]["PUBLICATION_DURABLE_PLATFORM_ID_OR_URL"][
        "proof_id"
    ] == "external-publication-proof"
    assert payload["field_statuses"]["PUBLICATION_DURABLE_PLATFORM_ID_OR_URL"][
        "proof_input_role"
    ] == "publication_destination"
    assert payload["proofs"]["provider-backed-live-voice-proof"]["state"] == (
        "ready_for_credential_snapshot_refresh"
    )
    assert payload["proofs"]["external-publication-proof"]["state"] == (
        "ready_for_credential_snapshot_refresh"
    )
    assert payload["proofs"]["provider-backed-live-voice-proof"]["field_contracts"][
        "OPENROUTER_API_KEY_FILE"
    ] == "readable local secret file path; file content is never emitted"
    assert payload["proofs"]["external-publication-proof"]["field_contracts"][
        "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID"
    ] == "durable non-local policy acknowledgement artifact id or URL"
    assert payload["proofs"]["provider-backed-live-voice-proof"]["field_statuses"][
        "OPENROUTER_API_KEY_FILE"
    ] == {
        "state": "configured",
        "issue_code": "none",
        "proof_id": "provider-backed-live-voice-proof",
        "proof_input_role": "provider_credential",
        "value_source": "secret_file_path",
        "next_action": "refresh_credential_snapshot",
        "contract": "readable local secret file path; file content is never emitted",
    }
    assert payload["proofs"]["external-publication-proof"]["field_statuses"][
        "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL"
    ]["state"] == "configured"
    assert payload["proofs"]["provider-backed-live-voice-proof"]["configured_fields"] == [
        "OPENROUTER_API_KEY_FILE",
        "OPENROUTER_LIVEKIT_URL",
        "LIVEKIT_API_KEY_FILE",
        "LIVEKIT_API_SECRET_FILE",
    ]
    assert payload["proofs"]["external-publication-proof"]["configured_fields"] == [
        "LINKEDIN_ACCESS_TOKEN_FILE",
        "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID",
        "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL",
        "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID",
    ]
    assert payload["proofs"]["provider-backed-live-voice-proof"]["blocked_fields"] == []
    assert payload["proofs"]["external-publication-proof"]["blocked_fields"] == []
    next_action_commands = payload["next_action_commands"]
    guarded_next_action_commands = payload["guarded_next_action_commands"]
    expected_input_arg = shlex.quote(str(input_path))
    serialized_commands = "\n".join(
        [*next_action_commands, *guarded_next_action_commands]
    )

    assert len(next_action_commands) == 6
    assert len(guarded_next_action_commands) == 6
    assert (
        "provider-proof-operator-input-readiness "
        f"--run-id {PROVIDER_PROOF_TEST_RUN_UUID} --input-path {expected_input_arg}"
    ) in next_action_commands[0]
    assert "--fail-on-blocked" not in next_action_commands[0]
    assert "--fail-on-blocked" in guarded_next_action_commands[0]
    assert (
        "blocker-credential-snapshot "
        f"--operator-input-path {expected_input_arg}"
    ) in next_action_commands[1]
    assert (
        "provider-proof-plan "
        f"--run-id {PROVIDER_PROOF_TEST_RUN_UUID} "
        f"--operator-input-path {expected_input_arg}"
    ) in next_action_commands[2]
    assert "operator-inputs.template.env" not in serialized_commands
    assert "openrouter_secret_token" not in serialized
    assert "livekit_key_secret" not in serialized
    assert "livekit_secret_token" not in serialized
    assert "linkedin_secret_token" not in serialized
    assert "127.0.0.1" not in serialized
    assert "linkedin.com" not in serialized
    assert str(ROOT) not in serialized


def test_provider_proof_operator_input_readiness_rejects_generic_bare_publication_artifact_ids(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("", encoding="utf-8")
    secret_dir = tmp_path / ".secrets"
    secret_dir.mkdir()
    (secret_dir / "openrouter_api_key").write_text(
        "openrouter_secret_token\n",
        encoding="utf-8",
    )
    (secret_dir / "livekit_api_key").write_text(
        "livekit_key_secret\n",
        encoding="utf-8",
    )
    (secret_dir / "livekit_api_secret").write_text(
        "livekit_secret_token\n",
        encoding="utf-8",
    )
    (secret_dir / "linkedin_access_token").write_text(
        "linkedin_secret_token\n",
        encoding="utf-8",
    )
    input_path = tmp_path / "operator-inputs.local.env"
    input_path.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=wss://livekit.example.com",
                "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key",
                "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret",
                "LINKEDIN_ACCESS_TOKEN_FILE=.secrets/linkedin_access_token",
                "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID=policy-artifact-1",
                (
                    "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL="
                    "https://www.linkedin.com/feed/update/urn:li:activity:123"
                ),
                "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID=rollback-artifact-1",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_operator_input_readiness_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-21",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            input_path=input_path,
        )
    )
    serialized = json.dumps(payload)

    assert payload["status"] == "blocked_by_operator_inputs"
    assert "operator_input_local_artifact_substitute" in payload["issue_codes"]
    invalid_fields = payload["proofs"]["external-publication-proof"][
        "invalid_fields"
    ]
    assert "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID" in invalid_fields
    assert "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID" in invalid_fields
    assert payload["field_statuses"]["LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID"][
        "issue_code"
    ] == "operator_input_local_artifact_substitute"
    assert payload["field_statuses"]["PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID"][
        "issue_code"
    ] == "operator_input_local_artifact_substitute"
    assert "policy-artifact-1" not in serialized
    assert "rollback-artifact-1" not in serialized


def test_provider_proof_operator_input_readiness_rejects_prefix_only_linkedin_artifact_urns(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("", encoding="utf-8")
    secret_dir = tmp_path / ".secrets"
    secret_dir.mkdir()
    (secret_dir / "openrouter_api_key").write_text(
        "openrouter_secret_token\n",
        encoding="utf-8",
    )
    (secret_dir / "livekit_api_key").write_text(
        "livekit_key_secret\n",
        encoding="utf-8",
    )
    (secret_dir / "livekit_api_secret").write_text(
        "livekit_secret_token\n",
        encoding="utf-8",
    )
    (secret_dir / "linkedin_access_token").write_text(
        "linkedin_secret_token\n",
        encoding="utf-8",
    )
    input_path = tmp_path / "operator-inputs.local.env"
    input_path.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=wss://livekit.example.com",
                "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key",
                "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret",
                "LINKEDIN_ACCESS_TOKEN_FILE=.secrets/linkedin_access_token",
                "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID=urn:li:activity:",
                (
                    "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL="
                    "https://www.linkedin.com/feed/update/urn:li:activity:123"
                ),
                "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID=urn:li:share:",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_operator_input_readiness_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-21",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            input_path=input_path,
        )
    )
    serialized = json.dumps(payload)

    assert payload["status"] == "blocked_by_operator_inputs"
    assert "operator_input_local_artifact_substitute" in payload["issue_codes"]
    invalid_fields = payload["proofs"]["external-publication-proof"][
        "invalid_fields"
    ]
    assert "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID" in invalid_fields
    assert "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID" in invalid_fields
    assert "urn:li:activity:" not in serialized
    assert "urn:li:share:" not in serialized


def test_provider_proof_record_validation_rejects_generic_bare_publication_artifact_ids(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("", encoding="utf-8")
    record = _accepted_provider_proof_record(
        env_example,
        "external-publication-proof",
    )
    record["policy_acknowledgement_artifact_id"] = "policy-artifact-1"
    record["rollback_or_postcondition_artifact_id"] = "rollback-artifact-1"

    payload = provider_cli._provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-21",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            proof="external-publication-proof",
            record_path=None,
            workspace_validation_path=Path(
                record["workspace_validation_report_artifact_id"]
            ),
            preflight_validation_path=Path(
                record["preflight_validation_report_artifact_id"]
            ),
        ),
        record,
    )
    serialized = json.dumps(payload)

    assert payload["status"] == "invalid_record"
    assert "publication_artifact_local_substitute" in payload["issue_codes"]
    assert "policy-artifact-1" not in serialized
    assert "rollback-artifact-1" not in serialized


def test_provider_proof_record_validation_rejects_prefix_only_linkedin_artifact_urns(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("", encoding="utf-8")
    record = _accepted_provider_proof_record(
        env_example,
        "external-publication-proof",
    )
    record["policy_acknowledgement_artifact_id"] = "urn:li:activity:"
    record["rollback_or_postcondition_artifact_id"] = "urn:li:share:"

    payload = provider_cli._provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-21",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            proof="external-publication-proof",
            record_path=None,
            workspace_validation_path=Path(
                record["workspace_validation_report_artifact_id"]
            ),
            preflight_validation_path=Path(
                record["preflight_validation_report_artifact_id"]
            ),
        ),
        record,
    )
    serialized = json.dumps(payload)

    assert payload["status"] == "invalid_record"
    assert "publication_artifact_local_substitute" in payload["issue_codes"]
    assert "urn:li:activity:" not in serialized
    assert "urn:li:share:" not in serialized


def test_provider_proof_operator_input_readiness_cli_fail_on_blocked_allows_ready(
    tmp_path,
    capsys,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("", encoding="utf-8")
    secret_dir = tmp_path / ".secrets"
    secret_dir.mkdir()
    (secret_dir / "openrouter_api_key").write_text(
        "openrouter_secret_token\n",
        encoding="utf-8",
    )
    (secret_dir / "livekit_api_key").write_text(
        "livekit_key_secret\n",
        encoding="utf-8",
    )
    (secret_dir / "livekit_api_secret").write_text(
        "livekit_secret_token\n",
        encoding="utf-8",
    )
    (secret_dir / "linkedin_access_token").write_text(
        "linkedin_secret_token\n",
        encoding="utf-8",
    )
    input_path = tmp_path / "operator-inputs.local.env"
    input_path.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=wss://livekit.example.com",
                "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key",
                "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret",
                "LINKEDIN_ACCESS_TOKEN_FILE=.secrets/linkedin_access_token",
                "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID="
                "linkedin-policy-acknowledgement-artifact-"
                f"{PROVIDER_PROOF_TEST_RUN_UUID}",
                (
                    "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL="
                    "https://www.linkedin.com/feed/update/urn:li:activity:123"
                ),
                "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID="
                "linkedin-rollback-postcondition-artifact-"
                f"{PROVIDER_PROOF_TEST_RUN_UUID}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    provider_cli._print_provider_proof_operator_input_readiness(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-21",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            input_path=input_path,
            fail_on_blocked=True,
        )
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["status"] == "ready_for_credential_snapshot_refresh"
    assert payload["issue_codes"] == []


def test_provider_proof_current_blocker_matrix_preserves_filled_operator_input_path(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("", encoding="utf-8")
    output_dir = tmp_path / "proof-workspace"
    output_dir.mkdir()
    secret_dir = tmp_path / ".secrets"
    secret_dir.mkdir()
    (secret_dir / "openrouter_api_key").write_text(
        "openrouter_secret_token\n",
        encoding="utf-8",
    )
    (secret_dir / "livekit_api_key").write_text(
        "livekit_key_secret\n",
        encoding="utf-8",
    )
    (secret_dir / "livekit_api_secret").write_text(
        "livekit_secret_token\n",
        encoding="utf-8",
    )
    (secret_dir / "linkedin_access_token").write_text(
        "linkedin_secret_token\n",
        encoding="utf-8",
    )
    input_path = output_dir / "operator-inputs.local.env"
    input_path.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=wss://livekit.example.com",
                "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key",
                "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret",
                "LINKEDIN_ACCESS_TOKEN_FILE=.secrets/linkedin_access_token",
                "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID="
                "linkedin-policy-acknowledgement-artifact-"
                f"{PROVIDER_PROOF_TEST_RUN_UUID}",
                (
                    "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL="
                    "https://www.linkedin.com/feed/update/urn:li:activity:123"
                ),
                "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID="
                "linkedin-rollback-postcondition-artifact-"
                f"{PROVIDER_PROOF_TEST_RUN_UUID}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    readiness = provider_cli._provider_proof_operator_input_readiness_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-21",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            input_path=input_path,
        )
    )
    (output_dir / "operator-input-readiness.json").write_text(
        json.dumps(readiness),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_current_blocker_matrix_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-21",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            output_dir=output_dir,
            audit_target=None,
            proof_audit_target=None,
            closure_review_audit_target=None,
            blocker_update_audit_target=None,
        )
    )
    expected_input_arg = shlex.quote(str(input_path))
    next_action_commands = payload["operator_input_readiness"][
        "next_action_commands"
    ]
    guarded_next_action_commands = payload["operator_input_readiness"][
        "guarded_next_action_commands"
    ]
    voice_commands = payload["operator_input_readiness"]["proofs"][
        "provider-backed-live-voice-proof"
    ]["next_action_commands"]
    serialized_commands = "\n".join(
        [*next_action_commands, *guarded_next_action_commands, *voice_commands]
    )

    assert payload["operator_input_readiness"]["status"] == (
        "ready_for_credential_snapshot_refresh"
    )
    assert (
        "provider-proof-operator-input-readiness "
        f"--run-id {PROVIDER_PROOF_TEST_RUN_UUID} --input-path {expected_input_arg}"
    ) in next_action_commands[0]
    assert "--fail-on-blocked" in guarded_next_action_commands[0]
    assert (
        "blocker-credential-snapshot "
        f"--operator-input-path {expected_input_arg}"
    ) in next_action_commands[1]
    assert (
        "provider-proof-plan "
        f"--run-id {PROVIDER_PROOF_TEST_RUN_UUID} "
        f"--operator-input-path {expected_input_arg}"
    ) in next_action_commands[2]
    assert voice_commands == next_action_commands
    assert "operator-inputs.template.env" not in serialized_commands


def test_provider_proof_operator_input_readiness_rejects_substitute_urls(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("", encoding="utf-8")
    secret_dir = tmp_path / ".secrets"
    secret_dir.mkdir()
    (secret_dir / "openrouter_api_key").write_text(
        "openrouter_secret_token\n",
        encoding="utf-8",
    )
    (secret_dir / "livekit_api_key").write_text(
        "livekit_key_secret\n",
        encoding="utf-8",
    )
    (secret_dir / "livekit_api_secret").write_text(
        "livekit_secret_token\n",
        encoding="utf-8",
    )
    (secret_dir / "linkedin_access_token").write_text(
        "linkedin_secret_token\n",
        encoding="utf-8",
    )
    input_path = tmp_path / "operator-inputs.local.env"
    input_path.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=wss://livekit.example.invalid",
                "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key",
                "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret",
                "LINKEDIN_ACCESS_TOKEN_FILE=.secrets/linkedin_access_token",
                "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID="
                "linkedin-policy-acknowledgement-artifact-"
                f"{PROVIDER_PROOF_TEST_RUN_UUID}",
                "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL=https://preview.local/draft",
                "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID="
                "linkedin-rollback-postcondition-artifact-"
                f"{PROVIDER_PROOF_TEST_RUN_UUID}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_operator_input_readiness_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-21",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            input_path=input_path,
        )
    )
    serialized = json.dumps(payload)

    assert payload["status"] == "blocked_by_operator_inputs"
    assert "operator_input_local_substitute" in payload["issue_codes"]
    assert "OPENROUTER_LIVEKIT_URL" in payload["proofs"][
        "provider-backed-live-voice-proof"
    ]["invalid_fields"]
    assert "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL" in payload["proofs"][
        "external-publication-proof"
    ]["invalid_fields"]
    assert "openrouter_secret_token" not in serialized
    assert "livekit_key_secret" not in serialized
    assert "livekit_secret_token" not in serialized
    assert "preview.local" not in serialized
    assert "hf_secret_token" not in serialized
    assert "linkedin_secret_token" not in serialized
    assert str(ROOT) not in serialized


def test_provider_proof_operator_input_readiness_rejects_wrong_publication_channel(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("", encoding="utf-8")
    secret_dir = tmp_path / ".secrets"
    secret_dir.mkdir()
    (secret_dir / "openrouter_api_key").write_text(
        "openrouter_secret_token\n",
        encoding="utf-8",
    )
    (secret_dir / "livekit_api_key").write_text(
        "livekit_key_secret\n",
        encoding="utf-8",
    )
    (secret_dir / "livekit_api_secret").write_text(
        "livekit_secret_token\n",
        encoding="utf-8",
    )
    (secret_dir / "linkedin_access_token").write_text(
        "linkedin_secret_token\n",
        encoding="utf-8",
    )
    input_path = tmp_path / "operator-inputs.local.env"
    input_path.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=wss://livekit.example.com",
                "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key",
                "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret",
                "LINKEDIN_ACCESS_TOKEN_FILE=.secrets/linkedin_access_token",
                "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID="
                "linkedin-policy-acknowledgement-artifact-"
                f"{PROVIDER_PROOF_TEST_RUN_UUID}",
                (
                    "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL="
                    "https://www.instagram.com/p/provider-proof"
                ),
                "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID="
                "linkedin-rollback-postcondition-artifact-"
                f"{PROVIDER_PROOF_TEST_RUN_UUID}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_operator_input_readiness_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-21",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            input_path=input_path,
        )
    )
    serialized = json.dumps(payload)

    assert payload["status"] == "blocked_by_operator_inputs"
    assert "operator_input_destination_channel_mismatch" in payload["issue_codes"]
    assert "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL" in payload["proofs"][
        "external-publication-proof"
    ]["invalid_fields"]
    assert "instagram.com" not in serialized
    assert "api-inference.huggingface.co" not in serialized
    assert "hf_secret_token" not in serialized
    assert "linkedin_secret_token" not in serialized
    assert str(ROOT) not in serialized


def test_provider_proof_operator_input_readiness_rejects_local_artifact_ids(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("", encoding="utf-8")
    secret_dir = tmp_path / ".secrets"
    secret_dir.mkdir()
    (secret_dir / "openrouter_api_key").write_text(
        "openrouter_secret_token\n",
        encoding="utf-8",
    )
    (secret_dir / "livekit_api_key").write_text(
        "livekit_key_secret\n",
        encoding="utf-8",
    )
    (secret_dir / "livekit_api_secret").write_text(
        "livekit_secret_token\n",
        encoding="utf-8",
    )
    (secret_dir / "linkedin_access_token").write_text(
        "linkedin_secret_token\n",
        encoding="utf-8",
    )
    input_path = tmp_path / "operator-inputs.local.env"
    input_path.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=wss://livekit.example.com",
                "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key",
                "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret",
                "LINKEDIN_ACCESS_TOKEN_FILE=.secrets/linkedin_access_token",
                "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID=draft-policy-note",
                (
                    "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL="
                    "https://www.linkedin.com/feed/update/urn:li:activity:123"
                ),
                "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID=./local-rollback.md",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_operator_input_readiness_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-21",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            input_path=input_path,
        )
    )
    serialized = json.dumps(payload)

    assert payload["status"] == "blocked_by_operator_inputs"
    assert "operator_input_local_artifact_substitute" in payload["issue_codes"]
    invalid_fields = payload["proofs"]["external-publication-proof"][
        "invalid_fields"
    ]
    assert "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID" in invalid_fields
    assert "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID" in invalid_fields
    assert "draft-policy-note" not in serialized
    assert "local-rollback" not in serialized
    assert "hf_secret_token" not in serialized
    assert "linkedin_secret_token" not in serialized
    assert str(ROOT) not in serialized


def test_provider_proof_operator_input_readiness_rejects_secret_shaped_file_paths(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("", encoding="utf-8")
    secret_dir = tmp_path / ".secrets"
    secret_dir.mkdir()
    (secret_dir / "openrouter_api_key").write_text(
        "openrouter_secret_token\n",
        encoding="utf-8",
    )
    (secret_dir / "livekit_api_key").write_text(
        "livekit_key_secret\n",
        encoding="utf-8",
    )
    (secret_dir / "livekit_api_secret").write_text(
        "livekit_secret_token\n",
        encoding="utf-8",
    )
    (secret_dir / "linkedin_secret_path").write_text(
        "linkedin_secret_token\n",
        encoding="utf-8",
    )
    input_path = tmp_path / "operator-inputs.local.env"
    input_path.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=wss://livekit.example.com",
                "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key",
                "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret",
                "LINKEDIN_ACCESS_TOKEN_FILE=.secrets/linkedin_secret_path",
                "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID="
                "linkedin-policy-acknowledgement-artifact-"
                f"{PROVIDER_PROOF_TEST_RUN_UUID}",
                (
                    "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL="
                    "https://www.linkedin.com/feed/update/urn:li:activity:123"
                ),
                "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID="
                "linkedin-rollback-postcondition-artifact-"
                f"{PROVIDER_PROOF_TEST_RUN_UUID}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_operator_input_readiness_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-21",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            input_path=input_path,
        )
    )
    serialized = json.dumps(payload)

    assert payload["status"] == "blocked_by_operator_inputs"
    assert "operator_input_secret_path_detected" in payload["issue_codes"]
    assert "LINKEDIN_ACCESS_TOKEN_FILE" in payload["proofs"][
        "external-publication-proof"
    ]["invalid_fields"]
    assert "linkedin_secret_path" not in serialized
    assert "linkedin_secret_token" not in serialized
    assert "api-inference.huggingface.co" not in serialized
    assert str(ROOT) not in serialized


def test_blocker_credential_snapshot_consumes_operator_input_path_without_values(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("", encoding="utf-8")
    secret_dir = tmp_path / ".secrets"
    secret_dir.mkdir()
    (secret_dir / "openrouter_api_key").write_text(
        "openrouter_secret_token\n",
        encoding="utf-8",
    )
    (secret_dir / "livekit_api_key").write_text(
        "livekit_key_secret\n",
        encoding="utf-8",
    )
    (secret_dir / "livekit_api_secret").write_text(
        "livekit_secret_token\n",
        encoding="utf-8",
    )
    (secret_dir / "linkedin_access_token").write_text(
        "linkedin_secret_token\n",
        encoding="utf-8",
    )
    input_path = tmp_path / "operator-inputs.local.env"
    input_path.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=wss://livekit.example.com",
                "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key",
                "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret",
                "LINKEDIN_ACCESS_TOKEN_FILE=.secrets/linkedin_access_token",
                "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID="
                "linkedin-policy-acknowledgement-artifact-"
                f"{PROVIDER_PROOF_TEST_RUN_UUID}",
                (
                    "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL="
                    "https://www.linkedin.com/feed/update/urn:li:activity:123"
                ),
                "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID="
                "linkedin-rollback-postcondition-artifact-"
                f"{PROVIDER_PROOF_TEST_RUN_UUID}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._blocker_credential_snapshot_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-21",
            operator_input_path=input_path,
        ),
        env_values={
            "LIVEKIT_API_KEY": "livekit_key_should_not_print",
            "LIVEKIT_API_SECRET": "livekit_secret_should_not_print",
            "INSTAGRAM_ACCESS_TOKEN": "instagram_secret_should_not_print",
            "X_ACCESS_TOKEN": "x_secret_should_not_print",
            "SUBSTACK_API_TOKEN": "substack_secret_should_not_print",
        },
    )
    serialized = json.dumps(payload)

    assert payload["snapshots"]["provider-backed-live-voice-proof"]["state"] == (
        "runtime_configuration_present_unverified"
    )
    assert payload["snapshots"]["external-publication-proof"]["state"] == (
        "runtime_configuration_present_unverified"
    )
    assert "OPENROUTER_API_KEY_FILE" in payload["snapshots"][
        "provider-backed-live-voice-proof"
    ]["configured_file_inputs"]
    assert "LINKEDIN_ACCESS_TOKEN_FILE" in payload["snapshots"][
        "external-publication-proof"
    ]["configured_file_inputs"]
    assert "openrouter_secret_token" not in serialized
    assert "livekit_key_secret" not in serialized
    assert "livekit_secret_token" not in serialized
    assert "linkedin_secret_token" not in serialized
    assert "livekit.example.com" not in serialized
    assert "linkedin.com" not in serialized
    assert "livekit_secret_should_not_print" not in serialized
    assert str(ROOT) not in serialized


def test_blocker_credential_snapshot_ignores_substitute_operator_input_urls(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("", encoding="utf-8")
    secret_dir = tmp_path / ".secrets"
    secret_dir.mkdir()
    (secret_dir / "openrouter_api_key").write_text(
        "openrouter_secret_token\n",
        encoding="utf-8",
    )
    input_path = tmp_path / "operator-inputs.local.env"
    input_path.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=wss://livekit.example.invalid",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._blocker_credential_snapshot_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-21",
            operator_input_path=input_path,
        ),
        env_values={
            "LIVEKIT_API_KEY": "livekit_key_should_not_print",
            "LIVEKIT_API_SECRET": "livekit_secret_should_not_print",
        },
    )
    voice_snapshot = payload["snapshots"]["provider-backed-live-voice-proof"]
    serialized = json.dumps(payload)

    assert voice_snapshot["state"] == "blocked_by_missing_configuration"
    assert "OPENROUTER_LIVEKIT_URL" in voice_snapshot["absent_inputs"]
    assert "OPENROUTER_LIVEKIT_URL" not in voice_snapshot[
        "configured_inputs"
    ]
    assert "livekit.example.invalid" not in serialized
    assert "openrouter_secret_token" not in serialized
    assert "livekit_secret_should_not_print" not in serialized
    assert str(ROOT) not in serialized


def test_provider_proof_plan_consumes_operator_input_path_for_attempt_gate(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("", encoding="utf-8")
    secret_dir = tmp_path / ".secrets"
    secret_dir.mkdir()
    (secret_dir / "openrouter_api_key").write_text(
        "openrouter_secret_token\n",
        encoding="utf-8",
    )
    (secret_dir / "livekit_api_key").write_text(
        "livekit_key_secret\n",
        encoding="utf-8",
    )
    (secret_dir / "livekit_api_secret").write_text(
        "livekit_secret_token\n",
        encoding="utf-8",
    )
    (secret_dir / "linkedin_access_token").write_text(
        "linkedin_secret_token\n",
        encoding="utf-8",
    )
    input_path = tmp_path / "operator-inputs.local.env"
    input_path.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=wss://livekit.example.com",
                "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key",
                "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret",
                "LINKEDIN_ACCESS_TOKEN_FILE=.secrets/linkedin_access_token",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_plan_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-21",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            operator_input_path=input_path,
        ),
        env_values={
            "LIVEKIT_API_KEY": "livekit_key_should_not_print",
            "LIVEKIT_API_SECRET": "livekit_secret_should_not_print",
            "INSTAGRAM_ACCESS_TOKEN": "instagram_secret_should_not_print",
            "X_ACCESS_TOKEN": "x_secret_should_not_print",
            "SUBSTACK_API_TOKEN": "substack_secret_should_not_print",
        },
    )
    serialized = json.dumps(payload)

    assert payload["proofs"]["provider-backed-live-voice-proof"]["attempt_gate"][
        "state"
    ] == "ready_for_preflight_capture"
    assert payload["proofs"]["external-publication-proof"]["attempt_gate"][
        "state"
    ] == "ready_for_preflight_capture"
    assert "openrouter_secret_token" not in serialized
    assert "livekit_key_secret" not in serialized
    assert "livekit_secret_token" not in serialized
    assert "linkedin_secret_token" not in serialized
    assert "livekit.example.com" not in serialized
    assert "linkedin.com" not in serialized
    assert "livekit_secret_should_not_print" not in serialized
    assert str(ROOT) not in serialized


def test_concrete_provider_proof_plan_report_is_current():
    output_dir = (
        ROOT
        / "social_media_optimiser/output/provider-proof/RUN-2026-05-20-NEXT"
    )
    report_path = output_dir / "proof-plan.json"

    report = json.loads(report_path.read_text(encoding="utf-8"))
    fresh_payload = _provider_proof_plan_payload(
        Namespace(
            env_example_path=ROOT / ".env.example",
            checked_at="2026-05-20",
            run_id="RUN-2026-05-20-NEXT",
        ),
        env_values=_no_local_secret_file_env_values(),
    )

    assert report == fresh_payload
    assert report["artifact"] == "agent-studio-provider-proof-plan"
    assert report["boundary"] == "planning_only_no_live_calls_no_secret_values"
    assert report["credential_snapshot"]["source"] == "<workspace-root>/.env.example"
    assert report["proofs"]["provider-backed-live-voice-proof"]["attempt_gate"][
        "state"
    ] == "blocked_by_credentials"
    assert report["proofs"]["external-publication-proof"]["attempt_gate"][
        "state"
    ] == "blocked_by_credentials"
    for proof_name, proof in report["proofs"].items():
        assert proof["proof_capture_commands_after_unblock"] == (
            provider_cli._provider_proof_capture_commands_after_unblock(
                proof_name,
                str(proof["command_run_id"]),
                Path("social_media_optimiser/output/provider-proof/<run-id>"),
            )
        )
        packet = proof["operator_proof_packet"]
        assert packet["proof_id"] == proof_name
        assert packet["label"] in {
            "Provider-backed live voice proof packet",
            "External publication proof packet",
        }
        assert packet["packet_schema_version"] == "operator-proof-packet.v1"
        assert packet["handoff_contract"] == "value-free-operator-proof-handoff"
        assert packet["state_change_allowed"] is False
        assert packet["secret_handling"] == (
            "Do not print tokens, API keys, or secrets; record endpoint "
            "and account identifiers only."
        )
        assert packet["current_matrix_packet"] == "current-blocker-matrix.json"
        assert packet["current_matrix_packet_ref"] == (
            "social_media_optimiser/output/provider-proof/<run-id>/"
            "current-blocker-matrix.json"
        )
        assert packet["current_matrix_packet_command"] == (
            "uv run all-about-llms-admin provider-proof-current-blocker-matrix "
            "--run-id <run-id> --output-dir "
            "'social_media_optimiser/output/provider-proof/<run-id>' > "
            "'social_media_optimiser/output/provider-proof/<run-id>/"
            "current-blocker-matrix.json'"
        )
        assert packet["current_matrix_operator_packet_ref"] == (
            f"/operator_proof_packets/{proof_name}"
        )
        assert packet["source_artifacts"] == {
            "proof_plan": "proof-plan.json",
            "current_blocker_matrix": "current-blocker-matrix.json",
        }
        assert packet["operator_input_readiness"]["field_contracts"] == (
            provider_cli._provider_proof_operator_input_field_contracts(proof_name)
        )
        assert packet["operator_input_readiness"]["field_ownership"] == (
            provider_cli._provider_proof_operator_input_field_ownership(proof_name)
        )
        assert packet["operator_input_readiness"]["blocked_fields"] == (
            provider_cli.PROVIDER_PROOF_OPERATOR_INPUT_FIELDS[proof_name]
        )
        assert packet["operator_input_readiness"]["field_statuses"]
        assert packet["proof_capture_commands_after_unblock"] == proof[
            "proof_capture_commands_after_unblock"
        ]
        assert packet["proof_record_schema"] == proof["proof_artifact_schema"]
        assert packet["proof_record_required_fields"] == proof[
            "proof_artifact_schema"
        ]["required_fields"]
        assert packet["store_in"] == provider_cli.PROVIDER_PROOF_RECORD_TARGETS
    assert str(ROOT) not in json.dumps(report)


def test_concrete_uuid_provider_proof_plan_report_is_current():
    run_id = "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e"
    output_dir = ROOT / "social_media_optimiser/output/provider-proof" / run_id
    report_path = output_dir / "proof-plan.json"

    report = json.loads(report_path.read_text(encoding="utf-8"))
    fresh_payload = provider_cli._provider_proof_plan_payload(
        Namespace(
            env_example_path=ROOT / ".env.example",
            checked_at="2026-05-24",
            run_id=run_id,
            output_dir=output_dir,
            operator_input_path=output_dir / "operator-inputs.template.env",
        ),
        env_values={},
    )

    assert report == fresh_payload
    for proof_name, proof in report["proofs"].items():
        packet = proof["operator_proof_packet"]
        assert packet["proof_id"] == proof_name
        assert packet["packet_schema_version"] == "operator-proof-packet.v1"
        assert packet["current_matrix_packet"] == "current-blocker-matrix.json"
        assert packet["current_matrix_packet_ref"] == (
            "social_media_optimiser/output/provider-proof/"
            f"{run_id}/current-blocker-matrix.json"
        )
        assert packet["current_matrix_packet_command"] == (
            "uv run all-about-llms-admin provider-proof-current-blocker-matrix "
            f"--run-id {run_id} --output-dir "
            "social_media_optimiser/output/provider-proof/"
            f"{run_id} > social_media_optimiser/output/provider-proof/"
            f"{run_id}/current-blocker-matrix.json"
        )
        assert packet["current_matrix_operator_packet_ref"] == (
            f"/operator_proof_packets/{proof_name}"
        )
        assert packet["source_artifacts"] == {
            "proof_plan": "proof-plan.json",
            "current_blocker_matrix": "current-blocker-matrix.json",
        }
        assert packet["operator_input_readiness"]["field_contracts"] == (
            provider_cli._provider_proof_operator_input_field_contracts(proof_name)
        )
        assert packet["operator_input_readiness"]["field_ownership"] == (
            provider_cli._provider_proof_operator_input_field_ownership(proof_name)
        )
        expected_blocked_fields = (
            []
            if proof_name == "provider-backed-live-voice-proof"
            else provider_cli.PROVIDER_PROOF_OPERATOR_INPUT_FIELDS[proof_name]
        )
        assert packet["operator_input_readiness"]["blocked_fields"] == (
            expected_blocked_fields
        )
        assert packet["operator_input_readiness"]["field_statuses"]
        assert packet["proof_capture_commands_after_unblock"] == proof[
            "proof_capture_commands_after_unblock"
        ]
        assert packet["proof_record_schema"] == proof["proof_artifact_schema"]
        assert packet["store_in"] == provider_cli.PROVIDER_PROOF_RECORD_TARGETS
    voice_readiness = report["proofs"]["provider-backed-live-voice-proof"][
        "operator_proof_packet"
    ]["operator_input_readiness"]
    assert voice_readiness["configured_fields"] == [
        "OPENROUTER_API_KEY_FILE",
        "OPENROUTER_LIVEKIT_URL",
        "LIVEKIT_API_KEY_FILE",
        "LIVEKIT_API_SECRET_FILE",
    ]
    assert voice_readiness["field_groups"] == {
        "invalid_fields": [],
        "missing_fields": [],
        "placeholder_fields": [],
        "unavailable_secret_file_fields": [],
    }
    assert voice_readiness["field_statuses"]["OPENROUTER_API_KEY_FILE"]["state"] == (
        "configured"
    )
    assert voice_readiness["field_statuses"]["OPENROUTER_LIVEKIT_URL"]["state"] == (
        "configured"
    )
    assert voice_readiness["field_statuses"]["LIVEKIT_API_KEY_FILE"]["state"] == (
        "configured"
    )
    assert voice_readiness["field_statuses"]["LIVEKIT_API_SECRET_FILE"]["state"] == (
        "configured"
    )
    assert voice_readiness["issue_codes"] == []
    assert voice_readiness["next_action"] == "refresh_credential_snapshot"
    assert "HF_TOKEN or HF_TOKEN_FILE" not in json.dumps(report)
    assert "GEMMA4_MULTIMODAL_ENDPOINT_URL" not in json.dumps(report)


def test_concrete_completion_status_uses_portable_default_audit_targets():
    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=ROOT / ".env.example",
            checked_at="2026-05-20",
            run_id="RUN-2026-05-20-NEXT",
            audit_target=None,
        ),
        env_values={},
    )
    serialized = json.dumps(payload)

    assert str(ROOT) not in serialized
    assert payload["audit_targets"] == [
        (
            "<workspace-root>/social_media_optimiser/01-work-tracking/"
            "Agent Studio Objective Completion Audit.md"
        ),
        "<workspace-root>/social_media_optimiser/wiki/ops/active-codex-context.md",
        (
            "<workspace-root>/system_design_vault/04-agent-studio-implications/"
            "agent-studio-objective-completion-audit.md"
        ),
    ]
    assert payload["status"] == "blocked_by_run_id"
    assert payload["issue_codes"] == ["run_id_not_product_uuid"]
    assert payload["proofs"]["provider-backed-live-voice-proof"][
        "next_action"
    ] == "replace_run_id_and_recheck"


def test_concrete_closure_review_status_uses_portable_default_audit_targets():
    payload = provider_cli._provider_proof_closure_review_status_payload(
        Namespace(
            env_example_path=ROOT / ".env.example",
            checked_at="2026-05-20",
            run_id="RUN-2026-05-20-NEXT",
            audit_target=None,
            proof_audit_target=None,
            blocker_update_audit_target=None,
        ),
        env_values={},
    )
    expected_targets = [
        (
            "<workspace-root>/social_media_optimiser/01-work-tracking/"
            "Agent Studio Objective Completion Audit.md"
        ),
        "<workspace-root>/social_media_optimiser/wiki/ops/active-codex-context.md",
        (
            "<workspace-root>/system_design_vault/04-agent-studio-implications/"
            "agent-studio-objective-completion-audit.md"
        ),
    ]

    assert str(ROOT) not in json.dumps(payload)
    assert payload["status"] == "blocked_by_completion_status"
    assert payload["audit_targets"] == expected_targets
    assert payload["proof_audit_targets"] == expected_targets


def test_concrete_provider_proof_completion_status_report_is_current():
    output_dir = (
        ROOT
        / "social_media_optimiser/output/provider-proof/RUN-2026-05-20-NEXT"
    )
    report_path = output_dir / "completion-status.json"

    report = json.loads(report_path.read_text(encoding="utf-8"))
    fresh_payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=ROOT / ".env.example",
            checked_at="2026-05-20",
            run_id="RUN-2026-05-20-NEXT",
            audit_target=None,
        ),
        env_values={},
    )

    assert report == fresh_payload
    assert report["artifact"] == "agent-studio-provider-proof-completion-status"
    assert report["run_id"] == "<run-id>"
    assert report["status"] == "blocked_by_run_id"
    assert report["issue_codes"] == ["run_id_not_product_uuid"]
    assert report["blocker_state_change_allowed_by_this_command"] is False
    assert report["accepted_proofs"] == []
    assert report["missing_accepted_proofs"] == [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]
    assert str(ROOT) not in json.dumps(report)


def test_concrete_provider_proof_closure_review_status_report_is_current():
    output_dir = (
        ROOT
        / "social_media_optimiser/output/provider-proof/RUN-2026-05-20-NEXT"
    )
    report_path = output_dir / "closure-review-status.json"

    report = json.loads(report_path.read_text(encoding="utf-8"))
    fresh_payload = provider_cli._provider_proof_closure_review_status_payload(
        Namespace(
            env_example_path=ROOT / ".env.example",
            checked_at="2026-05-20",
            run_id="RUN-2026-05-20-NEXT",
            audit_target=None,
            proof_audit_target=None,
            blocker_update_audit_target=None,
        ),
        env_values={},
    )

    assert report == fresh_payload
    assert report["artifact"] == (
        "agent-studio-provider-proof-closure-review-status"
    )
    assert report["run_id"] == "<run-id>"
    assert report["status"] == "blocked_by_completion_status"
    assert report["completion_status"] == "blocked_by_run_id"
    assert report["state_change_allowed"] is False
    assert report["blocker_state_update_allowed_after_review"] is False
    assert str(ROOT) not in json.dumps(report)


def test_concrete_provider_proof_closure_review_template_report_is_current():
    output_dir = (
        ROOT
        / "social_media_optimiser/output/provider-proof/RUN-2026-05-20-NEXT"
    )
    report_path = output_dir / "closure-review-template.json"

    report = json.loads(report_path.read_text(encoding="utf-8"))
    fresh_payload = provider_cli._provider_proof_closure_review_template_payload(
        Namespace(
            env_example_path=ROOT / ".env.example",
            checked_at="2026-05-20",
            run_id="RUN-2026-05-20-NEXT",
            audit_target=None,
        ),
        env_values={},
    )

    assert report == fresh_payload
    assert report["artifact"] == (
        "agent-studio-provider-proof-closure-review-template"
    )
    assert report["run_id"] == "<run-id>"
    assert report["status"] == "blocked_by_completion_status"
    assert report["completion_status"] == "blocked_by_run_id"
    assert report["completion_issue_codes"] == ["run_id_not_product_uuid"]
    assert report["template"] is None
    assert report["next_commands"] == []
    assert report["state_change_allowed"] is False
    assert str(ROOT) not in json.dumps(report)


def test_concrete_provider_proof_blocker_state_update_report_is_current():
    output_dir = (
        ROOT
        / "social_media_optimiser/output/provider-proof/RUN-2026-05-20-NEXT"
    )
    report_path = output_dir / "blocker-state-update.json"

    report = json.loads(report_path.read_text(encoding="utf-8"))
    fresh_payload = provider_cli._record_provider_proof_blocker_state_update_payload(
        Namespace(
            env_example_path=ROOT / ".env.example",
            checked_at="2026-05-20",
            run_id="RUN-2026-05-20-NEXT",
            proof_audit_target=None,
            closure_review_audit_target=None,
            audit_target=None,
        ),
        env_values={},
    )

    assert report == fresh_payload
    assert report["artifact"] == (
        "agent-studio-provider-proof-blocker-state-update-audit"
    )
    assert report["boundary"] == "no_secret_values_printed_no_state_change"
    assert report["run_id"] == "<run-id>"
    assert report["status"] == "blocked_by_closure_review_status"
    assert report["closure_review_status"] == "blocked_by_completion_status"
    assert report["issue_codes"] == ["closure_review_not_approved"]
    assert report["state_change_allowed"] is False
    assert report["blocker_state_update_note_recorded"] is False
    assert report["goal_completion_claimed"] is False
    assert report["written_targets"] == []
    assert report["existing_targets"] == []
    assert str(ROOT) not in json.dumps(report)


def test_concrete_current_blocker_matrix_report_is_current():
    output_dir = (
        ROOT
        / (
            "social_media_optimiser/output/provider-proof/"
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e"
        )
    )
    report_path = output_dir / "current-blocker-matrix.json"

    report = json.loads(report_path.read_text(encoding="utf-8"))
    fresh_payload = provider_cli._provider_proof_current_blocker_matrix_payload(
        Namespace(
            env_example_path=ROOT / ".env.example",
            checked_at="2026-05-24",
            run_id="190ae2f9-a74b-4a23-b39c-aaf2d636bd8e",
            output_dir=output_dir,
            audit_target=None,
            proof_audit_target=None,
            closure_review_audit_target=None,
            blocker_update_audit_target=None,
        ),
        env_values={},
    )

    assert report == fresh_payload
    assert report["artifact"] == "agent-studio-current-blocker-matrix"
    assert report["completion"]["status"] == "blocked_by_latest_failed_proof_record"
    assert report["completion"]["next_action"] == "capture_validate_record_and_recheck"
    completion_recovery_commands = report["completion"]["next_action_commands"]
    assert not any(
        "provider-proof-record-template --proof provider-backed-live-voice-proof"
        in command
        for command in completion_recovery_commands
    )
    assert any(
        "provider-proof-record-template --proof external-publication-proof" in command
        for command in completion_recovery_commands
    )
    assert completion_recovery_commands[-1] == (
        "uv run all-about-llms-admin provider-proof-completion-status "
        "--run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e"
    )
    assert report["closure"]["state_change_allowed"] is False
    assert report["closure"]["goal_completion_claimed"] is False
    voice = report["proofs"]["provider-backed-live-voice-proof"]
    publication = report["proofs"]["external-publication-proof"]
    assert report["completion"]["latest_failed_proofs"] == [
        "external-publication-proof"
    ]
    assert voice["current_state"] == "accepted_proof_record_available"
    assert voice["latest_record_outcome"] == "accepted"
    assert voice["accepted_record_available"] is True
    assert publication["accepted_record_available"] is False
    command_output_dir = Path(
        "social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e"
    )
    voice_capture_commands = [
        *provider_cli._proof_preflight_capture_commands_for_output(
            "provider-backed-live-voice-proof",
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e",
            command_output_dir,
        ),
        *provider_cli._proof_preflight_validation_capture_commands_for_output(
            "provider-backed-live-voice-proof",
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e",
            command_output_dir,
        ),
        *provider_cli._proof_execution_capture_commands_for_output(
            "provider-backed-live-voice-proof",
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e",
            command_output_dir,
        ),
        *provider_cli._proof_record_template_commands(
            "provider-backed-live-voice-proof",
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e",
        ),
        *provider_cli._proof_record_next_commands(
            "provider-backed-live-voice-proof",
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e",
            preflight_validation_path=(
                command_output_dir
                / "provider-backed-live-voice-proof.preflight-validation.json"
            ),
            workspace_validation_path=command_output_dir / "workspace-validation.json",
        ),
    ]
    publication_capture_commands = [
        *provider_cli._proof_preflight_capture_commands_for_output(
            "external-publication-proof",
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e",
            command_output_dir,
            acknowledge_publish_channel_policy=True,
        ),
        *provider_cli._proof_preflight_validation_capture_commands_for_output(
            "external-publication-proof",
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e",
            command_output_dir,
        ),
        *provider_cli._proof_execution_capture_commands_for_output(
            "external-publication-proof",
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e",
            command_output_dir,
        ),
        *provider_cli._proof_record_template_commands(
            "external-publication-proof",
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e",
        ),
        *provider_cli._proof_record_next_commands(
            "external-publication-proof",
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e",
            preflight_validation_path=(
                command_output_dir
                / "external-publication-proof.preflight-validation.json"
            ),
            workspace_validation_path=command_output_dir / "workspace-validation.json",
        ),
    ]
    assert voice["proof_capture_commands_after_unblock"] == voice_capture_commands
    assert publication["proof_capture_commands_after_unblock"] == (
        publication_capture_commands
    )
    publication_policy_capture_command = publication[
        "proof_capture_commands_after_unblock"
    ][1]
    assert '"acknowledge_publish_channel_policy":true' in (
        publication_policy_capture_command
    )
    assert '"acknowledge_publish_channel_policy":false' not in (
        publication_policy_capture_command
    )
    assert report["operator_input_readiness"]["status"] == (
        "blocked_by_operator_inputs"
    )
    readiness_report = json.loads(
        (output_dir / "operator-input-readiness.json").read_text(encoding="utf-8")
    )
    assert report["operator_input_readiness"]["blocked_fields"] == (
        readiness_report["blocked_fields"]
    )
    assert report["operator_input_readiness"]["configured_fields"] == (
        readiness_report["configured_fields"]
    )
    assert report["operator_input_readiness"]["field_groups"] == (
        readiness_report["field_groups"]
    )
    assert report["operator_input_readiness"]["required_fields"] == (
        readiness_report["required_fields"]
    )
    assert report["operator_input_readiness"]["field_contracts"] == (
        readiness_report["field_contracts"]
    )
    assert report["operator_input_readiness"]["field_statuses"] == (
        readiness_report["field_statuses"]
    )
    assert "operator_input_placeholder" in report["operator_input_readiness"][
        "issue_codes"
    ]
    strict_readiness_command = (
        "uv run all-about-llms-admin provider-proof-operator-input-readiness "
        "--run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e "
        "--input-path social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env "
        "--fail-on-blocked > social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-input-readiness.json"
    )
    assert report["operator_input_readiness"]["strict_readiness_command"] == (
        strict_readiness_command
    )
    assert report["operator_input_readiness"]["exit_policy"] == {
        "default_exit_code": 0,
        "fail_on_blocked_exit_code": 2,
        "fail_on_blocked_statuses": [
            "blocked_by_operator_inputs",
            "invalid_operator_input_file",
        ],
        "ready_status": "ready_for_credential_snapshot_refresh",
    }
    assert (
        report["operator_input_readiness"]["effective_fail_on_blocked_exit_code"]
        == 2
    )
    assert "GEMMA4_MULTIMODAL_ENDPOINT_URL" not in report["operator_input_readiness"][
        "blocked_fields"
    ]
    assert "HF_TOKEN_FILE" not in report["operator_input_readiness"][
        "blocked_fields"
    ]
    assert report["operator_input_readiness"]["proofs"][
        "provider-backed-live-voice-proof"
    ]["state"] == "ready_for_credential_snapshot_refresh"
    assert report["operator_input_readiness"]["proofs"][
        "provider-backed-live-voice-proof"
    ]["blocked_fields"] == readiness_report["proofs"][
        "provider-backed-live-voice-proof"
    ]["blocked_fields"]
    assert report["operator_input_readiness"]["proofs"][
        "provider-backed-live-voice-proof"
    ]["required_fields"] == readiness_report["proofs"][
        "provider-backed-live-voice-proof"
    ]["required_fields"]
    assert report["operator_input_readiness"]["proofs"][
        "provider-backed-live-voice-proof"
    ]["configured_fields"] == readiness_report["proofs"][
        "provider-backed-live-voice-proof"
    ]["configured_fields"]
    assert report["operator_input_readiness"]["proofs"][
        "provider-backed-live-voice-proof"
    ]["field_groups"] == {
        "missing_fields": [],
        "placeholder_fields": [],
        "invalid_fields": [],
        "unavailable_secret_file_fields": [],
    }
    assert report["operator_input_readiness"]["proofs"][
        "provider-backed-live-voice-proof"
    ]["field_contracts"] == {
        "OPENROUTER_API_KEY_FILE": (
            "readable local secret file path; file content is never emitted"
        ),
        "OPENROUTER_LIVEKIT_URL": (
            "ws or wss LiveKit URL for OpenRouter-backed realtime dialogue"
        ),
        "LIVEKIT_API_KEY_FILE": (
            "readable local secret file path; file content is never emitted"
        ),
        "LIVEKIT_API_SECRET_FILE": (
            "readable local secret file path; file content is never emitted"
        ),
    }
    assert report["operator_input_readiness"]["proofs"][
        "provider-backed-live-voice-proof"
    ]["field_statuses"]["OPENROUTER_API_KEY_FILE"]["state"] == "configured"
    assert report["operator_input_readiness"]["proofs"][
        "provider-backed-live-voice-proof"
    ]["field_statuses"]["OPENROUTER_LIVEKIT_URL"]["value_source"] == (
        "endpoint_url"
    )
    assert report["operator_input_readiness"]["proofs"][
        "provider-backed-live-voice-proof"
    ]["field_statuses"]["LIVEKIT_API_SECRET_FILE"]["state"] == "configured"
    assert report["operator_input_readiness"]["proofs"][
        "provider-backed-live-voice-proof"
    ]["issue_codes"] == []
    assert report["operator_input_readiness"]["proofs"][
        "provider-backed-live-voice-proof"
    ]["next_action"] == "refresh_credential_snapshot"
    assert report["operator_input_readiness"]["proofs"][
        "provider-backed-live-voice-proof"
    ]["required_evidence_after_unblock"] == [
        "operator-input-readiness status ready_for_credential_snapshot_refresh",
        "credential-snapshot status runtime_configuration_present_unverified",
        "proof-plan attempt gate ready_for_preflight_capture",
        "valid provider-backed live voice preflight validation",
        "same-run OpenRouter DeepSeek live dialogue reasoning evidence",
        "same-run realtime session or LiveKit room evidence",
        "provider smoke ledger evidence",
        "realtime voice timing ledger evidence",
        "zero failed post-capture validation checks",
        "passed secret-redaction check",
    ]
    retry_commands = [
        (
            "uv run all-about-llms-admin provider-proof-operator-input-readiness "
            "--run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e "
            "--input-path social_media_optimiser/output/provider-proof/"
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env "
            "> social_media_optimiser/output/provider-proof/"
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-input-readiness.json"
        ),
        (
            "uv run all-about-llms-admin blocker-credential-snapshot "
            "--operator-input-path social_media_optimiser/output/provider-proof/"
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env "
            "> social_media_optimiser/output/provider-proof/"
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/credential-snapshot.json"
        ),
        (
            "uv run all-about-llms-admin provider-proof-plan "
            "--run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e "
            "--operator-input-path social_media_optimiser/output/provider-proof/"
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env "
            "> social_media_optimiser/output/provider-proof/"
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/proof-plan.json"
        ),
        (
            "uv run all-about-llms-admin provider-proof-current-blocker-matrix "
            "--run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e "
            "--output-dir social_media_optimiser/output/provider-proof/"
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e > "
            "social_media_optimiser/output/provider-proof/"
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-blocker-matrix.json"
        ),
        (
            "uv run all-about-llms-admin provider-proof-current-status "
            "--run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e "
            "--output-dir social_media_optimiser/output/provider-proof/"
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e > "
            "social_media_optimiser/output/provider-proof/"
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-proof-status.md"
        ),
        (
            "uv run all-about-llms-admin provider-proof-operator-unblocker-checklist "
            "--run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e "
            "--output-dir social_media_optimiser/output/provider-proof/"
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e > "
            "social_media_optimiser/output/provider-proof/"
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-unblocker-checklist.md"
        ),
    ]
    assert report["operator_input_readiness"]["proofs"][
        "provider-backed-live-voice-proof"
    ]["next_action_commands"] == retry_commands
    guarded_retry_commands = [strict_readiness_command, *retry_commands[1:]]
    assert report["operator_input_readiness"]["guarded_next_action_commands"] == (
        guarded_retry_commands
    )
    assert report["operator_input_readiness"]["proofs"][
        "provider-backed-live-voice-proof"
    ]["guarded_next_action_commands"] == guarded_retry_commands
    assert report["operator_input_readiness"]["proofs"][
        "external-publication-proof"
    ]["state"] == "blocked_by_operator_inputs"
    assert report["operator_input_readiness"]["proofs"][
        "external-publication-proof"
    ]["blocked_fields"] == readiness_report["proofs"][
        "external-publication-proof"
    ]["blocked_fields"]
    assert report["operator_input_readiness"]["proofs"][
        "external-publication-proof"
    ]["required_fields"] == readiness_report["proofs"][
        "external-publication-proof"
    ]["required_fields"]
    assert report["operator_input_readiness"]["proofs"][
        "external-publication-proof"
    ]["configured_fields"] == readiness_report["proofs"][
        "external-publication-proof"
    ]["configured_fields"]
    assert report["operator_input_readiness"]["proofs"][
        "external-publication-proof"
    ]["field_groups"] == {
        "missing_fields": [],
        "placeholder_fields": [
            "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID",
            "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL",
            "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID",
        ],
        "invalid_fields": [],
        "unavailable_secret_file_fields": ["LINKEDIN_ACCESS_TOKEN_FILE"],
    }
    assert report["operator_input_readiness"]["proofs"][
        "external-publication-proof"
    ]["issue_codes"] == [
        "operator_input_secret_file_unavailable",
        "operator_input_placeholder",
    ]
    assert report["operator_input_readiness"]["proofs"][
        "external-publication-proof"
    ]["next_action"] == (
        "supply_linkedin_token_policy_destination_and_rollback_evidence"
    )
    assert report["operator_input_readiness"]["proofs"][
        "external-publication-proof"
    ]["required_evidence_after_unblock"] == [
        "operator-input-readiness status ready_for_credential_snapshot_refresh",
        "credential-snapshot status runtime_configuration_present_unverified",
        "proof-plan attempt gate ready_for_preflight_capture",
        "valid external publication preflight validation",
        "destination channel and durable URL linked to validated linkedin readiness",
        "durable external destination proof",
        "policy acknowledgement artifact",
        "rollback or postcondition artifact",
        "zero failed post-capture validation checks",
        "passed secret-redaction check",
    ]
    assert report["operator_input_readiness"]["proofs"][
        "external-publication-proof"
    ]["next_action_commands"] == retry_commands
    assert report["operator_input_readiness"]["proofs"][
        "external-publication-proof"
    ]["guarded_next_action_commands"] == guarded_retry_commands
    voice_packet = report["operator_proof_packets"]["provider-backed-live-voice-proof"]
    assert voice_packet["proof_id"] == "provider-backed-live-voice-proof"
    assert voice_packet["matrix_parity_ref"] == (
        "/operator_input_readiness/proofs/provider-backed-live-voice-proof"
    )
    assert voice_packet["packet_schema_version"] == "operator-proof-packet.v1"
    assert voice_packet["handoff_contract"] == "value-free-operator-proof-handoff"
    assert voice_packet["state_change_allowed"] is False
    assert voice_packet["state_change_guardrail"] == (
        "no_state_change_without_accepted_proof_and_closure_review"
    )
    assert voice_packet["proof_capture_matrix_ref"] == (
        "/proofs/provider-backed-live-voice-proof/"
        "proof_capture_commands_after_unblock"
    )
    assert voice_packet["proof_plan_packet"] == "proof-plan.json"
    assert voice_packet["proof_plan_packet_ref"] == (
        "social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/proof-plan.json"
    )
    assert voice_packet["proof_plan_packet_command"] == retry_commands[2]
    assert voice_packet["proof_plan_operator_packet_ref"] == (
        "/proofs/provider-backed-live-voice-proof/operator_proof_packet"
    )
    assert voice_packet["proof_capture_commands_after_unblock"] == voice[
        "proof_capture_commands_after_unblock"
    ]
    assert voice_packet["proof_record_schema"] == (
        provider_cli._voice_proof_artifact_schema()
    )
    assert voice_packet["proof_record_required_fields"] == (
        provider_cli._voice_proof_artifact_schema()["required_fields"]
    )
    assert (
        "voice_agent_process_start_artifact_id"
        in voice_packet["proof_record_required_fields"]
    )
    assert voice_packet["current_gate"]["completion_next_action"] == (
        report["completion"]["next_action"]
    )
    assert voice_packet["current_gate"]["completion_next_action_commands"] == (
        completion_recovery_commands
    )
    assert (
        voice_packet["current_gate"]["completion_next_action_commands"][-1]
        == completion_recovery_commands[-1]
    )
    assert voice_packet["source_artifacts"] == {
        "operator_input_readiness": "operator-input-readiness.json",
        "current_blocker_matrix": "current-blocker-matrix.json",
        "operator_input_template": "operator-inputs.template.env",
        "proof_plan": "proof-plan.json",
    }
    assert voice_packet["operator_input_readiness"] == {
        **report["operator_input_readiness"]["proofs"][
            "provider-backed-live-voice-proof"
        ],
        "status": "ready_for_credential_snapshot_refresh",
        "checked_at": report["operator_input_readiness"]["checked_at"],
        "evidence_ref": report["operator_input_readiness"]["evidence_ref"],
        "effective_fail_on_blocked_exit_code": report[
            "operator_input_readiness"
        ]["effective_fail_on_blocked_exit_code"],
        "exit_policy": report["operator_input_readiness"]["exit_policy"],
        "strict_readiness_command": strict_readiness_command,
    }
    publication_packet = report["operator_proof_packets"][
        "external-publication-proof"
    ]
    assert publication_packet["proof_id"] == "external-publication-proof"
    assert publication_packet["matrix_parity_ref"] == (
        "/operator_input_readiness/proofs/external-publication-proof"
    )
    assert publication_packet["proof_capture_matrix_ref"] == (
        "/proofs/external-publication-proof/"
        "proof_capture_commands_after_unblock"
    )
    assert publication_packet["proof_plan_packet"] == "proof-plan.json"
    assert publication_packet["proof_plan_packet_ref"] == (
        "social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/proof-plan.json"
    )
    assert publication_packet["proof_plan_packet_command"] == retry_commands[2]
    assert publication_packet["proof_plan_operator_packet_ref"] == (
        "/proofs/external-publication-proof/operator_proof_packet"
    )
    assert publication_packet["proof_capture_commands_after_unblock"] == publication[
        "proof_capture_commands_after_unblock"
    ]
    assert publication_packet["proof_record_schema"] == (
        provider_cli._publication_proof_artifact_schema()
    )
    assert publication_packet["proof_record_required_fields"] == (
        provider_cli._publication_proof_artifact_schema()["required_fields"]
    )
    assert (
        "durable_platform_id_or_url"
        in publication_packet["proof_record_required_fields"]
    )
    assert publication_packet["current_gate"]["completion_next_action"] == (
        report["completion"]["next_action"]
    )
    assert publication_packet["current_gate"]["completion_next_action_commands"] == (
        completion_recovery_commands
    )
    assert (
        publication_packet["current_gate"]["completion_next_action_commands"][-1]
        == completion_recovery_commands[-1]
    )
    assert publication_packet["source_artifacts"] == {
        "operator_input_readiness": "operator-input-readiness.json",
        "current_blocker_matrix": "current-blocker-matrix.json",
        "operator_input_template": "operator-inputs.template.env",
        "proof_plan": "proof-plan.json",
    }
    assert publication_packet["operator_input_readiness"] == {
        **report["operator_input_readiness"]["proofs"]["external-publication-proof"],
        "status": report["operator_input_readiness"]["status"],
        "checked_at": report["operator_input_readiness"]["checked_at"],
        "evidence_ref": report["operator_input_readiness"]["evidence_ref"],
        "effective_fail_on_blocked_exit_code": report[
            "operator_input_readiness"
        ]["effective_fail_on_blocked_exit_code"],
        "exit_policy": report["operator_input_readiness"]["exit_policy"],
        "strict_readiness_command": strict_readiness_command,
    }
    assert report["operator_input_readiness"]["evidence_ref"] == (
        "operator-input-readiness.json"
    )
    assert report["current_state_packets"] == {
        "current_blocker_matrix": "current-blocker-matrix.json",
        "current_proof_status": "current-proof-status.md",
        "operator_unblocker_checklist": "operator-unblocker-checklist.md",
    }
    assert report["current_state_packet_commands"] == {
        "current_blocker_matrix": retry_commands[3],
        "current_proof_status": retry_commands[4],
        "operator_unblocker_checklist": (
            "uv run all-about-llms-admin provider-proof-operator-unblocker-checklist "
            "--run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e "
            "--output-dir social_media_optimiser/output/provider-proof/"
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e > "
            "social_media_optimiser/output/provider-proof/"
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-unblocker-checklist.md"
        ),
    }
    assert report["next_status_packet"] == "current-proof-status.md"
    assert voice["remaining_blockers"] == []
    assert voice_packet["operator_input_readiness"]["blocked_fields"] == []
    assert voice_packet["operator_input_readiness"]["configured_fields"] == [
        "OPENROUTER_API_KEY_FILE",
        "OPENROUTER_LIVEKIT_URL",
        "LIVEKIT_API_KEY_FILE",
        "LIVEKIT_API_SECRET_FILE",
    ]
    assert "GEMMA4_MULTIMODAL_ENDPOINT_URL" not in json.dumps(voice)
    assert "HF_TOKEN_FILE" not in json.dumps(voice)
    assert publication["remaining_blockers"][0]["blocker_id"] == (
        "linkedin-publication-readiness"
    )
    assert str(ROOT) not in json.dumps(report)


def test_concrete_current_proof_status_report_is_current():
    output_dir = (
        ROOT
        / (
            "social_media_optimiser/output/provider-proof/"
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e"
        )
    )
    report_path = output_dir / "current-proof-status.md"

    report = report_path.read_text(encoding="utf-8")
    fresh_report = provider_cli._provider_proof_current_status_markdown(
        Namespace(
            env_example_path=ROOT / ".env.example",
            checked_at="2026-05-24",
            run_id="190ae2f9-a74b-4a23-b39c-aaf2d636bd8e",
            output_dir=output_dir,
            audit_target=None,
            proof_audit_target=None,
            closure_review_audit_target=None,
            blocker_update_audit_target=None,
        ),
        env_values={},
    )

    assert report == fresh_report
    assert "provider-proof-current-status" in report
    assert "## Current State Packet Contract" in report
    assert "- current_state_packets:" in report
    assert "current_blocker_matrix: `current-blocker-matrix.json`" in report
    assert "current_proof_status: `current-proof-status.md`" in report
    assert "operator_unblocker_checklist: `operator-unblocker-checklist.md`" in report
    assert "- next_status_packet: `current-proof-status.md`" in report
    assert "- next_operator_packet: `operator-unblocker-checklist.md`" in report
    assert "- current_state_packet_commands:" in report
    assert "provider-proof-current-status --run-id" in report
    assert "current-blocker-matrix.json" in report
    assert "operator-unblocker-checklist.md" in report
    regeneration_block = report.split("## Regeneration Commands", 1)[1].split(
        "## Next Packets",
        1,
    )[0]
    matrix_pos = regeneration_block.index("provider-proof-current-blocker-matrix")
    status_pos = regeneration_block.index("provider-proof-current-status")
    checklist_pos = regeneration_block.index(
        "provider-proof-operator-unblocker-checklist"
    )
    assert matrix_pos < status_pos < checklist_pos
    next_packets_block = report.split("## Next Packets", 1)[1].split(
        "Do not run closure review",
        1,
    )[0]
    next_matrix_pos = next_packets_block.index("current-blocker-matrix.json")
    next_status_pos = next_packets_block.index("current-proof-status.md")
    next_checklist_pos = next_packets_block.index("operator-unblocker-checklist.md")
    assert next_matrix_pos < next_status_pos < next_checklist_pos
    assert (
        "`provider-backed-live-voice-proof`: "
        "`accepted_proof_record_available`"
    ) in report
    assert "- remaining blockers: `none`" in report
    assert "realtime-voice-timing-ledger-evidence" not in report
    assert "`realtime-voice-timing-ledger.json`" in report
    assert "`external-publication-proof`: `local_publication_fixture_ready_external_destination_blocked`" in report
    assert "HF_TOKEN or HF_TOKEN_FILE" not in report
    assert "blocked_by_latest_failed_proof_record" in report
    assert "completion issue codes:" in report
    assert "`latest_proof_record_failed`" in report
    assert "completion evidence ref: `completion-status.json`" in report
    assert "closure evidence refs:" in report
    assert "`closure-review-template.json`" in report
    assert "`closure-review-status.json`" in report
    assert "`blocker-state-update.json`" in report
    assert "latest failed proofs:" in report
    assert "missing accepted proofs:" in report
    current_gate_block = report.split("## Current Gate", 1)[1].split(
        "## Current State Packet Contract",
        1,
    )[0]
    assert "- completion next_action: `capture_validate_record_and_recheck`" in (
        current_gate_block
    )
    assert "- completion next_action_commands:" in current_gate_block
    assert (
        "provider-proof-record-template --proof provider-backed-live-voice-proof"
        not in current_gate_block
    )
    assert (
        "provider-proof-record-template --proof external-publication-proof"
        in current_gate_block
    )
    assert (
        current_gate_block.count("provider-proof-completion-status --run-id")
        == 1
    )
    assert "blocked_by_operator_inputs" in report
    operator_input_block = report.split("## Operator Input Readiness", 1)[1].split(
        "Per-proof readiness:",
        1,
    )[0]
    assert "Required fields:" in operator_input_block
    assert "Configured fields:" in operator_input_block
    assert "Field contracts:" in operator_input_block
    assert "Field ownership:" in operator_input_block
    assert "Field groups:" in operator_input_block
    assert "Field statuses:" in operator_input_block
    assert "- OPENROUTER_API_KEY_FILE:" in operator_input_block
    assert "  - proof_id: `provider-backed-live-voice-proof`" in operator_input_block
    assert "  - proof_input_role: `provider_credential`" in operator_input_block
    assert "- OPENROUTER_LIVEKIT_URL:" in operator_input_block
    assert "  - proof_input_role: `transport_endpoint`" in operator_input_block
    assert "- LIVEKIT_API_KEY_FILE:" in operator_input_block
    assert "- LIVEKIT_API_SECRET_FILE:" in operator_input_block
    assert "  - proof_input_role: `transport_credential`" in operator_input_block
    assert "- PUBLICATION_DURABLE_PLATFORM_ID_OR_URL:" in operator_input_block
    assert "  - proof_id: `external-publication-proof`" in operator_input_block
    assert "  - proof_input_role: `publication_destination`" in operator_input_block
    assert "`OPENROUTER_API_KEY_FILE`" in operator_input_block
    assert "`OPENROUTER_LIVEKIT_URL`" in operator_input_block
    assert "`LIVEKIT_API_KEY_FILE`" in operator_input_block
    assert "`LIVEKIT_API_SECRET_FILE`" in operator_input_block
    assert "`LINKEDIN_ACCESS_TOKEN_FILE`" in operator_input_block
    assert "`HF_TOKEN_FILE`" not in operator_input_block
    assert "`GEMMA4_MULTIMODAL_ENDPOINT_URL`" not in operator_input_block
    assert "readable local secret file path; file content is never emitted" in (
        operator_input_block
    )
    assert "secret_file_unavailable" in operator_input_block
    assert "endpoint_url" in operator_input_block
    assert "- placeholder_fields:" in operator_input_block
    assert "- unavailable_secret_file_fields:" in operator_input_block
    assert "- invalid_fields:" in operator_input_block
    assert "- missing_fields:" in operator_input_block
    per_proof_readiness_block = report.split("Per-proof readiness:", 1)[1].split(
        "## Regeneration Commands",
        1,
    )[0]
    assert per_proof_readiness_block.count("  - next_action_commands:") == 2
    assert per_proof_readiness_block.count("  - guarded_next_action_commands:") == 2
    assert per_proof_readiness_block.count("  - required fields:") == 2
    assert per_proof_readiness_block.count("  - configured fields:") == 2
    assert per_proof_readiness_block.count("  - field_contracts:") == 2
    assert per_proof_readiness_block.count("  - field_ownership:") == 2
    assert per_proof_readiness_block.count("  - field_statuses:") == 2
    assert per_proof_readiness_block.count("  - issue_codes:") == 2
    assert per_proof_readiness_block.count("  - field_groups:") == 2
    assert "`OPENROUTER_API_KEY_FILE`" in per_proof_readiness_block
    assert "`OPENROUTER_LIVEKIT_URL`" in per_proof_readiness_block
    assert "`LIVEKIT_API_KEY_FILE`" in per_proof_readiness_block
    assert "`LIVEKIT_API_SECRET_FILE`" in per_proof_readiness_block
    assert "`LINKEDIN_ACCESS_TOKEN_FILE`" in per_proof_readiness_block
    assert "`HF_TOKEN_FILE`" not in per_proof_readiness_block
    assert "`GEMMA4_MULTIMODAL_ENDPOINT_URL`" not in per_proof_readiness_block
    assert "secret_file_unavailable" in per_proof_readiness_block
    assert "endpoint_url" in per_proof_readiness_block
    assert "    - OPENROUTER_API_KEY_FILE:" in per_proof_readiness_block
    assert "      - proof_input_role: `provider_credential`" in per_proof_readiness_block
    assert "    - OPENROUTER_LIVEKIT_URL:" in per_proof_readiness_block
    assert "      - proof_input_role: `transport_endpoint`" in per_proof_readiness_block
    assert "    - LIVEKIT_API_KEY_FILE:" in per_proof_readiness_block
    assert "    - LIVEKIT_API_SECRET_FILE:" in per_proof_readiness_block
    assert "      - proof_input_role: `transport_credential`" in per_proof_readiness_block
    assert "    - PUBLICATION_DURABLE_PLATFORM_ID_OR_URL:" in per_proof_readiness_block
    assert "      - proof_input_role: `publication_destination`" in per_proof_readiness_block
    assert "    - placeholder_fields:" in per_proof_readiness_block
    assert "    - unavailable_secret_file_fields:" in per_proof_readiness_block
    assert "    - invalid_fields:" in per_proof_readiness_block
    assert "    - missing_fields:" in per_proof_readiness_block
    assert "`operator_input_secret_file_unavailable`" in per_proof_readiness_block
    assert "`operator_input_placeholder`" in per_proof_readiness_block
    assert (
        "provider-proof-operator-input-readiness "
        "--run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e "
        "--input-path social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env "
        "> social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-input-readiness.json"
    ) in per_proof_readiness_block
    assert (
        "provider-proof-operator-input-readiness "
        "--run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e "
        "--input-path social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env "
        "--fail-on-blocked > social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-input-readiness.json"
    ) in per_proof_readiness_block
    assert report.count("proof_capture_commands_after_unblock:") == 4
    assert report.count("operator_proof_packet:") == 2
    _assert_operator_packet_capture_commands(report)
    _assert_operator_packet_closeout_refs(report)
    _assert_operator_packet_record_schema(report)
    _assert_operator_packet_input_readiness(report)
    _assert_operator_packet_field_ownership(report)
    _assert_operator_packet_field_statuses(report)
    _assert_operator_packet_readiness_command_lists(report)
    _assert_operator_packet_input_contracts(report)
    _assert_operator_packet_current_gate(report)
    _assert_operator_packet_current_state_packets(report)
    assert "- proof_id: `provider-backed-live-voice-proof`" in report
    assert "- proof_id: `external-publication-proof`" in report
    assert report.count("- matrix_parity_ref:") == 2
    assert (
        "- matrix_parity_ref: "
        "`/operator_input_readiness/proofs/provider-backed-live-voice-proof`"
    ) in report
    assert (
        "- matrix_parity_ref: "
        "`/operator_input_readiness/proofs/external-publication-proof`"
    ) in report
    assert report.count("- proof_capture_matrix_ref:") == 2
    assert (
        "- proof_capture_matrix_ref: "
        "`/proofs/provider-backed-live-voice-proof/proof_capture_commands_after_unblock`"
    ) in report
    assert (
        "- proof_capture_matrix_ref: "
        "`/proofs/external-publication-proof/proof_capture_commands_after_unblock`"
    ) in report
    assert "- label: `Provider-backed live voice proof packet`" in report
    assert "- label: `External publication proof packet`" in report
    assert "- packet_schema_version: `operator-proof-packet.v1`" in report
    assert "- handoff_contract: `value-free-operator-proof-handoff`" in report
    assert "- state_change_allowed: `False`" in report
    assert "- secret_handling: `Do not print tokens, API keys, or secrets; record endpoint and account identifiers only.`" in report
    assert report.count("- source_artifacts:") == 2
    assert "  - operator_input_readiness: `operator-input-readiness.json`" in report
    assert "  - current_blocker_matrix: `current-blocker-matrix.json`" in report
    assert "  - operator_input_template: `operator-inputs.template.env`" in report
    assert "  - proof_plan: `proof-plan.json`" in report
    assert "- must_capture:" in report
    assert "`LiveKit room/session id and participant identity`" in report
    assert "`durable platform ID or URL`" in report
    assert "- store_in:" in report
    assert "`social_media_optimiser/wiki/ops/active-codex-context.md`" in report
    assert "- next_status_packet: `current-proof-status.md`" in report
    assert "- next_operator_packet: `operator-unblocker-checklist.md`" in report
    assert "- proof_plan_packet: `proof-plan.json`" in report
    assert (
        "- proof_plan_packet_ref: `social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/proof-plan.json`"
    ) in report
    assert (
        "- proof_plan_packet_command: `uv run all-about-llms-admin "
        "provider-proof-plan --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e "
        "--operator-input-path social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env "
        "> social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/proof-plan.json`"
    ) in report
    assert (
        "- proof_plan_operator_packet_ref: "
        "`/proofs/provider-backed-live-voice-proof/operator_proof_packet`"
    ) in report
    assert (
        "- proof_plan_operator_packet_ref: "
        "`/proofs/external-publication-proof/operator_proof_packet`"
    ) in report
    assert report.count("proof_record_schema:") == 4
    assert "- artifact_type: `provider_backed_live_voice_proof_record`" in report
    assert "- state_field: `provider-backed-live-voice-proof`" in report
    assert "- artifact_type: `external_publication_proof_record`" in report
    assert "- state_field: `external-publication-proof`" in report
    assert report.count("- allowed_outcomes:") == 4
    assert report.count("proof_record_required_fields:") == 4
    assert "`voice_agent_process_start_artifact_id`" in report
    assert "`durable_platform_id_or_url`" in report
    assert "validate-provider-proof-preflight-artifacts --proof provider-backed-live-voice-proof" in report
    assert "record-provider-proof-record --proof provider-backed-live-voice-proof" in report
    assert "validate-provider-proof-preflight-artifacts --proof external-publication-proof" in report
    assert "record-provider-proof-record --proof external-publication-proof" in report
    publication_capture_block = report.split("## External Publication", 1)[1].split(
        "## Operator Input Readiness",
        1,
    )[0]
    assert '"acknowledge_publish_channel_policy":true' in publication_capture_block
    assert '"acknowledge_publish_channel_policy":false' not in publication_capture_block
    assert "OPENROUTER_API_KEY_FILE" in report
    assert "OPENROUTER_LIVEKIT_URL" in report
    assert "LIVEKIT_API_KEY_FILE" in report
    assert "LIVEKIT_API_SECRET_FILE" in report
    assert "HF_TOKEN_FILE" not in report
    assert "GEMMA4_MULTIMODAL_ENDPOINT_URL" not in report
    assert "- blocker: `realtime-voice-timing-ledger-evidence`" not in report
    assert "- blocker: `gemma-audio-reasoning`" not in report
    assert "LINKEDIN_ACCESS_TOKEN_FILE" in report
    assert "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL" in report
    assert "- blocker: `linkedin-publication-readiness` (`blocked`)" in report
    assert "- blocker: `linkedin-publication-readiness` (`unknown`)" not in report
    assert "no secret values, no raw provider responses, no private audio" in report
    assert str(ROOT) not in report


def test_provider_proof_current_status_preserves_filled_operator_input_path(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("", encoding="utf-8")
    output_dir = tmp_path / "provider-proof" / PROVIDER_PROOF_TEST_RUN_UUID
    output_dir.mkdir(parents=True)
    secret_dir = tmp_path / ".secrets"
    secret_dir.mkdir()
    (secret_dir / "openrouter_api_key").write_text(
        "openrouter_secret_token\n",
        encoding="utf-8",
    )
    (secret_dir / "livekit_api_key").write_text("livekit_key\n", encoding="utf-8")
    (secret_dir / "livekit_api_secret").write_text(
        "livekit_secret\n",
        encoding="utf-8",
    )
    (secret_dir / "linkedin_access_token").write_text(
        "linkedin_secret_token\n",
        encoding="utf-8",
    )
    input_path = output_dir / "operator-inputs.local.env"
    input_path.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=wss://livekit.openrouter.example",
                "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key",
                "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret",
                "LINKEDIN_ACCESS_TOKEN_FILE=.secrets/linkedin_access_token",
                "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID="
                "linkedin-policy-acknowledgement-artifact-"
                f"{PROVIDER_PROOF_TEST_RUN_UUID}",
                (
                    "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL="
                    "https://www.linkedin.com/feed/update/urn:li:activity:123"
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    readiness = provider_cli._provider_proof_operator_input_readiness_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-21",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            input_path=input_path,
        )
    )
    (output_dir / "operator-input-readiness.json").write_text(
        json.dumps(readiness),
        encoding="utf-8",
    )

    report = provider_cli._provider_proof_current_status_markdown(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-21",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            output_dir=output_dir,
            audit_target=None,
            proof_audit_target=None,
            closure_review_audit_target=None,
            blocker_update_audit_target=None,
        ),
        env_values={},
    )
    operator_block = report.split("## Operator Input Readiness", 1)[1].split(
        "Per-proof readiness:",
        1,
    )[0]
    expected_input_arg = shlex.quote(str(input_path))
    template_input_arg = shlex.quote(str(output_dir / "operator-inputs.template.env"))

    assert "- next_action_commands:" in operator_block
    assert "- guarded_next_action_commands:" in operator_block
    assert f"--input-path {expected_input_arg}" in operator_block
    assert f"--operator-input-path {expected_input_arg}" in operator_block
    assert "--fail-on-blocked" in operator_block
    assert f"--input-path {template_input_arg}" not in operator_block
    assert f"--operator-input-path {template_input_arg}" not in operator_block


def test_provider_proof_current_blocker_matrix_clears_accepted_proof_blockers(
    tmp_path,
):
    output_dir = tmp_path / "provider-proof" / "123e4567-e89b-12d3-a456-426614174000"
    output_dir.mkdir(parents=True)
    (output_dir / "completion-status.json").write_text(
        json.dumps(
            {
                "status": "required_proofs_accepted",
                "checked_at": "2026-05-21",
                "accepted_proofs": [
                    "provider-backed-live-voice-proof",
                    "external-publication-proof",
                ],
                "accepted_record_sources": {
                    "provider-backed-live-voice-proof": [
                        "social_media_optimiser/01-work-tracking/audit.md",
                    ],
                    "external-publication-proof": [
                        "social_media_optimiser/wiki/ops/active-codex-context.md",
                    ],
                },
                "missing_accepted_proofs": [],
                "latest_failed_proofs": [],
                "issue_codes": [],
            }
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_current_blocker_matrix_payload(
        Namespace(
            env_example_path=tmp_path / ".env.example",
            checked_at=None,
            run_id="123e4567-e89b-12d3-a456-426614174000",
            output_dir=output_dir,
            audit_target=None,
            proof_audit_target=None,
            closure_review_audit_target=None,
            blocker_update_audit_target=None,
        ),
        env_values={},
    )

    assert payload["completion"]["status"] == "required_proofs_accepted"
    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        proof_status = payload["proofs"][proof]
        assert proof_status["current_state"] == "accepted_proof_record_available"
        assert proof_status["latest_record_outcome"] == "accepted"
        assert proof_status["accepted_record_available"] is True
        assert proof_status["remaining_blockers"] == []
        assert not any("failed-record" in ref for ref in proof_status["evidence_refs"])
        assert proof_status["evidence_refs"][0] == "completion-status.json"

    assert payload["proofs"]["provider-backed-live-voice-proof"]["evidence_refs"] == [
        "completion-status.json",
        "social_media_optimiser/01-work-tracking/audit.md",
    ]
    assert payload["proofs"]["external-publication-proof"]["evidence_refs"] == [
        "completion-status.json",
        "social_media_optimiser/wiki/ops/active-codex-context.md",
    ]


def test_provider_proof_current_blocker_matrix_keeps_partial_coverage_blocked(
    tmp_path,
):
    output_dir = tmp_path / "provider-proof" / "123e4567-e89b-12d3-a456-426614174000"
    output_dir.mkdir(parents=True)
    (output_dir / "completion-status.json").write_text(
        json.dumps(
            {
                "status": "blocked_by_incomplete_audit_target_coverage",
                "checked_at": "2026-05-21",
                "accepted_proofs": [
                    "provider-backed-live-voice-proof",
                    "external-publication-proof",
                ],
                "accepted_record_sources": {
                    "provider-backed-live-voice-proof": [
                        "social_media_optimiser/01-work-tracking/audit.md",
                    ],
                    "external-publication-proof": [
                        "social_media_optimiser/01-work-tracking/audit.md",
                    ],
                },
                "missing_accepted_proofs": [],
                "latest_failed_proofs": [],
                "incomplete_audit_target_proofs": [
                    "provider-backed-live-voice-proof",
                    "external-publication-proof",
                ],
                "issue_codes": ["audit_target_coverage_incomplete"],
                "proofs": {
                    proof: {
                        "status": "accepted_record_missing_from_some_targets",
                        "missing_source_targets": [
                            "system_design_vault/04-agent-studio-implications/audit.md",
                        ],
                    }
                    for proof in [
                        "provider-backed-live-voice-proof",
                        "external-publication-proof",
                    ]
                },
            }
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_current_blocker_matrix_payload(
        Namespace(
            env_example_path=tmp_path / ".env.example",
            checked_at=None,
            run_id="123e4567-e89b-12d3-a456-426614174000",
            output_dir=output_dir,
            audit_target=None,
            proof_audit_target=None,
            closure_review_audit_target=None,
            blocker_update_audit_target=None,
        ),
        env_values={},
    )

    assert payload["completion"]["incomplete_audit_target_proofs"] == [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]
    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        proof_status = payload["proofs"][proof]
        assert proof_status["current_state"] == (
            "accepted_record_missing_from_some_targets"
        )
        assert proof_status["latest_record_outcome"] == "incomplete"
        assert proof_status["accepted_record_available"] is False
        assert proof_status["remaining_blockers"][0]["blocker_id"] == (
            "accepted-record-audit-target-coverage"
        )
        assert "completion-status.json" in proof_status["evidence_refs"]


def test_provider_proof_current_blocker_matrix_preserves_audit_note_blocker_lists(
    tmp_path,
):
    output_dir = tmp_path / "provider-proof" / "123e4567-e89b-12d3-a456-426614174000"
    output_dir.mkdir(parents=True)
    (output_dir / "completion-status.json").write_text(
        json.dumps(
            {
                "status": "blocked_by_secret_shaped_audit_note",
                "checked_at": "2026-05-21",
                "accepted_proofs": [
                    "provider-backed-live-voice-proof",
                    "external-publication-proof",
                ],
                "missing_accepted_proofs": [],
                "latest_failed_proofs": [],
                "secret_shaped_audit_note_proofs": [
                    "provider-backed-live-voice-proof",
                ],
                "invalid_accepted_audit_note_proofs": [
                    "external-publication-proof",
                ],
                "issue_codes": [
                    "audit_note_secret_shape_detected",
                    "invalid_accepted_audit_note",
                ],
                "proofs": {
                    "provider-backed-live-voice-proof": {
                        "status": "latest_record_contains_secret_shape",
                        "secret_source_targets": [
                            "social_media_optimiser/01-work-tracking/audit.md",
                        ],
                    },
                    "external-publication-proof": {
                        "status": "latest_record_has_invalid_fields",
                        "invalid_source_targets": [
                            "system_design_vault/04-agent-studio-implications/audit.md",
                        ],
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_current_blocker_matrix_payload(
        Namespace(
            env_example_path=tmp_path / ".env.example",
            checked_at=None,
            run_id="123e4567-e89b-12d3-a456-426614174000",
            output_dir=output_dir,
            audit_target=None,
            proof_audit_target=None,
            closure_review_audit_target=None,
            blocker_update_audit_target=None,
        ),
        env_values={},
    )

    assert payload["completion"]["secret_shaped_audit_note_proofs"] == [
        "provider-backed-live-voice-proof",
    ]
    assert payload["completion"]["invalid_accepted_audit_note_proofs"] == [
        "external-publication-proof",
    ]
    assert payload["proofs"]["provider-backed-live-voice-proof"]["current_state"] == (
        "latest_record_contains_secret_shape"
    )
    assert payload["proofs"]["external-publication-proof"]["current_state"] == (
        "latest_record_has_invalid_fields"
    )


def test_provider_proof_current_blocker_matrix_derives_audit_note_summary_lists(
    tmp_path,
):
    output_dir = tmp_path / "provider-proof" / "123e4567-e89b-12d3-a456-426614174000"
    output_dir.mkdir(parents=True)
    (output_dir / "completion-status.json").write_text(
        json.dumps(
            {
                "status": "blocked_by_secret_shaped_audit_note",
                "checked_at": "2026-05-21",
                "accepted_proofs": [
                    "provider-backed-live-voice-proof",
                    "external-publication-proof",
                ],
                "missing_accepted_proofs": [],
                "latest_failed_proofs": [],
                "issue_codes": [
                    "audit_note_secret_shape_detected",
                    "invalid_accepted_audit_note",
                ],
                "proofs": {
                    "provider-backed-live-voice-proof": {
                        "status": "latest_record_contains_secret_shape",
                    },
                    "external-publication-proof": {
                        "status": "latest_record_has_invalid_fields",
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_current_blocker_matrix_payload(
        Namespace(
            env_example_path=tmp_path / ".env.example",
            checked_at=None,
            run_id="123e4567-e89b-12d3-a456-426614174000",
            output_dir=output_dir,
            audit_target=None,
            proof_audit_target=None,
            closure_review_audit_target=None,
            blocker_update_audit_target=None,
        ),
        env_values={},
    )

    assert payload["completion"]["secret_shaped_audit_note_proofs"] == [
        "provider-backed-live-voice-proof",
    ]
    assert payload["completion"]["invalid_accepted_audit_note_proofs"] == [
        "external-publication-proof",
    ]


def test_provider_proof_operator_unblocker_checklist_clears_accepted_proof_inputs(
    tmp_path,
):
    output_dir = tmp_path / "provider-proof" / "123e4567-e89b-12d3-a456-426614174000"
    output_dir.mkdir(parents=True)
    (output_dir / "completion-status.json").write_text(
        json.dumps(
            {
                "status": "required_proofs_accepted",
                "checked_at": "2026-05-21",
                "accepted_proofs": [
                    "provider-backed-live-voice-proof",
                    "external-publication-proof",
                ],
                "missing_accepted_proofs": [],
                "latest_failed_proofs": [],
                "issue_codes": [],
            }
        ),
        encoding="utf-8",
    )

    report = provider_cli._provider_proof_operator_unblocker_checklist_markdown(
        Namespace(
            env_example_path=tmp_path / ".env.example",
            checked_at=None,
            run_id="123e4567-e89b-12d3-a456-426614174000",
            output_dir=output_dir,
        ),
        env_values={},
    )

    assert "No proof-level operator blockers remain." in report
    assert (
        "Required accepted proof state: all required accepted records are available."
    ) in report
    assert "validate-provider-proof-closure-review" in report
    assert "record-provider-proof-closure-review" in report
    assert report.index("provider-proof-closure-review-template") < report.index(
        "validate-provider-proof-closure-review"
    )
    assert report.index("validate-provider-proof-closure-review") < report.index(
        "record-provider-proof-closure-review"
    )
    assert report.index("record-provider-proof-closure-review") < report.index(
        "provider-proof-closure-review-status"
    )
    assert "HF_TOKEN" not in report
    assert "LINKEDIN_ACCESS_TOKEN" not in report


def test_provider_proof_operator_unblocker_checklist_names_incomplete_coverage(
    tmp_path,
):
    output_dir = tmp_path / "provider-proof" / "123e4567-e89b-12d3-a456-426614174000"
    output_dir.mkdir(parents=True)
    (output_dir / "completion-status.json").write_text(
        json.dumps(
            {
                "status": "blocked_by_incomplete_audit_target_coverage",
                "checked_at": "2026-05-21",
                "accepted_proofs": [
                    "provider-backed-live-voice-proof",
                    "external-publication-proof",
                ],
                "accepted_record_sources": {
                    "provider-backed-live-voice-proof": [
                        "social_media_optimiser/01-work-tracking/audit.md",
                    ],
                    "external-publication-proof": [
                        "social_media_optimiser/01-work-tracking/audit.md",
                    ],
                },
                "missing_accepted_proofs": [],
                "latest_failed_proofs": [],
                "incomplete_audit_target_proofs": [
                    "provider-backed-live-voice-proof",
                    "external-publication-proof",
                ],
                "issue_codes": ["audit_target_coverage_incomplete"],
                "proofs": {
                    proof: {
                        "status": "accepted_record_missing_from_some_targets",
                        "missing_source_targets": [
                            "system_design_vault/04-agent-studio-implications/audit.md",
                        ],
                    }
                    for proof in [
                        "provider-backed-live-voice-proof",
                        "external-publication-proof",
                    ]
                },
            }
        ),
        encoding="utf-8",
    )

    report = provider_cli._provider_proof_operator_unblocker_checklist_markdown(
        Namespace(
            env_example_path=tmp_path / ".env.example",
            checked_at=None,
            run_id="123e4567-e89b-12d3-a456-426614174000",
            output_dir=output_dir,
        ),
        env_values={},
    )

    assert (
        "Required accepted proof state: blocked by incomplete accepted-record "
        "audit coverage for provider-backed live voice and external publication."
    ) in report
    assert "Accepted proof audit coverage is incomplete." in report
    assert "system_design_vault/04-agent-studio-implications/audit.md" in report
    assert "HF_TOKEN" not in report
    assert "LINKEDIN_ACCESS_TOKEN" not in report
    assert "provider-readiness.preflight.json" not in report
    assert "publish-readiness.preflight.json" not in report


def test_provider_proof_operator_unblocker_checklist_names_invalid_accepted_notes(
    tmp_path,
):
    output_dir = tmp_path / "provider-proof" / "123e4567-e89b-12d3-a456-426614174000"
    output_dir.mkdir(parents=True)
    (output_dir / "completion-status.json").write_text(
        json.dumps(
            {
                "status": "blocked_by_invalid_accepted_audit_note",
                "checked_at": "2026-05-21",
                "accepted_proofs": [
                    "provider-backed-live-voice-proof",
                    "external-publication-proof",
                ],
                "accepted_record_sources": {
                    "provider-backed-live-voice-proof": [
                        "social_media_optimiser/01-work-tracking/audit.md",
                    ],
                    "external-publication-proof": [
                        "social_media_optimiser/01-work-tracking/audit.md",
                    ],
                },
                "missing_accepted_proofs": [],
                "latest_failed_proofs": [],
                "invalid_accepted_audit_note_proofs": [
                    "provider-backed-live-voice-proof",
                    "external-publication-proof",
                ],
                "issue_codes": ["accepted_audit_note_invalid_fields"],
                "proofs": {
                    proof: {
                        "status": "latest_record_has_invalid_fields",
                        "invalid_source_targets": [
                            "social_media_optimiser/01-work-tracking/audit.md",
                        ],
                    }
                    for proof in [
                        "provider-backed-live-voice-proof",
                        "external-publication-proof",
                    ]
                },
            }
        ),
        encoding="utf-8",
    )

    report = provider_cli._provider_proof_operator_unblocker_checklist_markdown(
        Namespace(
            env_example_path=tmp_path / ".env.example",
            checked_at=None,
            run_id="123e4567-e89b-12d3-a456-426614174000",
            output_dir=output_dir,
        ),
        env_values={},
    )

    assert (
        "Required accepted proof state: blocked by invalid accepted audit notes "
        "for provider-backed live voice and external publication."
    ) in report
    assert "Accepted proof audit note needs repair." in report
    assert "valid accepted proof audit note fields" in report
    assert "provider-readiness.preflight.json" not in report
    assert "publish-readiness.preflight.json" not in report


def test_provider_proof_operator_unblocker_checklist_names_latest_failed_records(
    tmp_path,
):
    output_dir = tmp_path / "provider-proof" / "123e4567-e89b-12d3-a456-426614174000"
    output_dir.mkdir(parents=True)
    (output_dir / "completion-status.json").write_text(
        json.dumps(
            {
                "status": "blocked_by_latest_failed_proof_record",
                "checked_at": "2026-05-21",
                "accepted_proofs": [],
                "missing_accepted_proofs": [],
                "latest_failed_proofs": [
                    "provider-backed-live-voice-proof",
                    "external-publication-proof",
                ],
                "issue_codes": ["latest_proof_record_failed"],
            }
        ),
        encoding="utf-8",
    )

    report = provider_cli._provider_proof_operator_unblocker_checklist_markdown(
        Namespace(
            env_example_path=tmp_path / ".env.example",
            checked_at=None,
            run_id="123e4567-e89b-12d3-a456-426614174000",
            output_dir=output_dir,
        ),
        env_values={},
    )

    assert (
        "Required accepted proof state: blocked by latest failed records for "
        "provider-backed live voice and external publication."
    ) in report
    assert "blocker-credential-snapshot --operator-input-path" in report
    assert "provider-proof-plan --run-id" in report
    assert "--operator-input-path" in report
    assert "credential-snapshot.json" in report
    assert "runtime_configuration_present_unverified" in report
    assert "provider-backed-live-voice-proof" in report
    assert "external-publication-proof" in report
    assert "validate-provider-proof-record --proof provider-backed-live-voice-proof" in report
    assert "record-provider-proof-record --proof provider-backed-live-voice-proof" in report
    assert "validate-provider-proof-record --proof external-publication-proof" in report
    assert "record-provider-proof-record --proof external-publication-proof" in report
    assert "Required accepted records still missing:" not in report


def test_provider_proof_operator_unblocker_checklist_preserves_filled_operator_input_path(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("", encoding="utf-8")
    output_dir = tmp_path / "provider-proof" / PROVIDER_PROOF_TEST_RUN_UUID
    output_dir.mkdir(parents=True)
    secret_dir = tmp_path / ".secrets"
    secret_dir.mkdir()
    (secret_dir / "openrouter_api_key").write_text(
        "openrouter_secret_token\n",
        encoding="utf-8",
    )
    (secret_dir / "livekit_api_key").write_text("livekit_key\n", encoding="utf-8")
    (secret_dir / "livekit_api_secret").write_text(
        "livekit_secret\n",
        encoding="utf-8",
    )
    (secret_dir / "linkedin_access_token").write_text(
        "linkedin_secret_token\n",
        encoding="utf-8",
    )
    (output_dir / "operator-inputs.template.env").write_text(
        provider_cli._provider_proof_operator_inputs_template(),
        encoding="utf-8",
    )
    input_path = output_dir / "operator-inputs.local.env"
    input_path.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=wss://livekit.openrouter.example",
                "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key",
                "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret",
                "LINKEDIN_ACCESS_TOKEN_FILE=.secrets/linkedin_access_token",
                "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID="
                "linkedin-policy-acknowledgement-artifact-"
                f"{PROVIDER_PROOF_TEST_RUN_UUID}",
                (
                    "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL="
                    "https://www.linkedin.com/feed/update/urn:li:activity:123"
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    readiness = provider_cli._provider_proof_operator_input_readiness_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-21",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            input_path=input_path,
        )
    )
    (output_dir / "operator-input-readiness.json").write_text(
        json.dumps(readiness),
        encoding="utf-8",
    )
    (output_dir / "completion-status.json").write_text(
        json.dumps(
            {
                "status": "blocked_by_latest_failed_proof_record",
                "checked_at": "2026-05-21",
                "accepted_proofs": [],
                "missing_accepted_proofs": [],
                "latest_failed_proofs": [
                    "provider-backed-live-voice-proof",
                    "external-publication-proof",
                ],
                "issue_codes": ["latest_proof_record_failed"],
            }
        ),
        encoding="utf-8",
    )

    report = provider_cli._provider_proof_operator_unblocker_checklist_markdown(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-21",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            output_dir=output_dir,
        ),
        env_values={},
    )
    expected_input_arg = shlex.quote(str(input_path))
    template_input_arg = shlex.quote(str(output_dir / "operator-inputs.template.env"))

    assert f"--input-path {expected_input_arg}" in report
    assert f"--operator-input-path {expected_input_arg}" in report
    assert "--fail-on-blocked" in report
    assert f"--input-path {template_input_arg}" not in report
    assert f"--operator-input-path {template_input_arg}" not in report


def test_provider_proof_operator_unblocker_checklist_uses_recorded_checkpoint_kind(
    tmp_path,
):
    output_dir = tmp_path / "provider-proof" / "123e4567-e89b-12d3-a456-426614174000"
    output_dir.mkdir(parents=True)
    (output_dir / "completion-status.json").write_text(
        json.dumps(
            {
                "status": "blocked_by_latest_failed_proof_record",
                "checked_at": "2026-05-21",
                "accepted_proofs": [],
                "missing_accepted_proofs": [],
                "latest_failed_proofs": [
                    "provider-backed-live-voice-proof",
                ],
                "issue_codes": ["latest_proof_record_failed"],
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "operator-checkpoint.json").write_text(
        json.dumps(
            {
                "checkpoint": {
                    "checkpoint_id": "6fddc144-9872-4452-8b74-54e4f25cdbf3",
                    "checkpoint_kind": "provider_configuration_recovery",
                    "event_cursor": 42,
                },
            }
        ),
        encoding="utf-8",
    )

    report = provider_cli._provider_proof_operator_unblocker_checklist_markdown(
        Namespace(
            env_example_path=tmp_path / ".env.example",
            checked_at=None,
            run_id="123e4567-e89b-12d3-a456-426614174000",
            output_dir=output_dir,
        ),
        env_values={},
    )

    assert "operator-checkpoint.json" in report
    assert "provider_configuration_recovery" in report
    assert "6fddc144-9872-4452-8b74-54e4f25cdbf3" in report
    assert "event cursor: `42`" in report
    assert "checkpoint kind: `operator_preflight`" not in report


def test_concrete_operator_unblocker_checklist_is_current():
    output_dir = (
        ROOT
        / (
            "social_media_optimiser/output/provider-proof/"
            "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e"
        )
    )
    report_path = output_dir / "operator-unblocker-checklist.md"

    report = report_path.read_text(encoding="utf-8")
    fresh_report = provider_cli._provider_proof_operator_unblocker_checklist_markdown(
        Namespace(
            env_example_path=ROOT / ".env.example",
            checked_at="2026-05-24",
            run_id="190ae2f9-a74b-4a23-b39c-aaf2d636bd8e",
            output_dir=output_dir,
        ),
        env_values={},
    )

    assert report == fresh_report
    assert "provider-proof-operator-unblocker-checklist" in report
    assert "- input readiness field ownership:" in report
    assert "  - OPENROUTER_API_KEY_FILE:" in report
    assert "    - proof_id: `provider-backed-live-voice-proof`" in report
    assert "    - proof_input_role: `provider_credential`" in report
    assert "  - PUBLICATION_DURABLE_PLATFORM_ID_OR_URL:" in report
    assert "    - proof_id: `external-publication-proof`" in report
    assert "    - proof_input_role: `publication_destination`" in report
    assert "    - provider-backed-live-voice-proof field ownership:" in report
    assert "    - external-publication-proof field ownership:" in report
    assert "`closure-review-status.json`: `blocked_by_completion_status`" in report
    assert "state_change_allowed: `False`" in report
    assert "goal_completion_claimed: `False`" in report
    assert "completion issue codes:" in report
    assert "`latest_proof_record_failed`" in report
    assert "completion evidence ref: `completion-status.json`" in report
    assert "closure evidence refs:" in report
    assert "`closure-review-template.json`" in report
    assert "`closure-review-status.json`" in report
    assert "`blocker-state-update.json`" in report
    assert "latest failed proofs:" in report
    assert "missing accepted proofs:" in report
    current_gate_block = report.split("## Current Gate", 1)[1].split(
        "## Operator Input Template",
        1,
    )[0]
    assert "- completion next_action: `capture_validate_record_and_recheck`" in (
        current_gate_block
    )
    assert "- completion next_action_commands:" in current_gate_block
    assert (
        "provider-proof-record-template --proof provider-backed-live-voice-proof"
        not in current_gate_block
    )
    assert (
        "provider-proof-record-template --proof external-publication-proof"
        in current_gate_block
    )
    assert (
        current_gate_block.count("provider-proof-completion-status --run-id")
        == 1
    )
    assert "`provider-backed-live-voice-proof`" in report
    assert "`external-publication-proof`" in report
    assert "Accepted proof record is available." in report
    assert "No proof-level operator inputs remain for this proof." in report
    assert "validate-provider-proof-record --proof provider-backed-live-voice-proof" not in report
    assert "record-provider-proof-record --proof provider-backed-live-voice-proof" not in report
    assert "validate-provider-proof-record --proof external-publication-proof" in report
    assert "record-provider-proof-record --proof external-publication-proof" in report
    assert report.count("proof_capture_commands_after_unblock:") == 2
    assert report.count("operator_proof_packet:") == 1
    _assert_operator_packet_capture_commands(report)
    _assert_operator_packet_closeout_refs(report)
    _assert_operator_packet_record_schema(report)
    _assert_operator_packet_input_readiness(report)
    _assert_operator_packet_field_ownership(report)
    _assert_operator_packet_field_statuses(report)
    _assert_operator_packet_readiness_command_lists(report)
    _assert_operator_packet_input_contracts(report)
    _assert_operator_packet_current_gate(report)
    _assert_operator_packet_current_state_packets(report)
    assert "- proof_id: `external-publication-proof`" in report
    assert report.count("- matrix_parity_ref:") == 1
    assert (
        "- matrix_parity_ref: "
        "`/operator_input_readiness/proofs/external-publication-proof`"
    ) in report
    assert report.count("- proof_capture_matrix_ref:") == 1
    assert (
        "- proof_capture_matrix_ref: "
        "`/proofs/external-publication-proof/proof_capture_commands_after_unblock`"
    ) in report
    assert "- label: `External publication proof packet`" in report
    assert "- packet_schema_version: `operator-proof-packet.v1`" in report
    assert "- handoff_contract: `value-free-operator-proof-handoff`" in report
    assert "- state_change_allowed: `False`" in report
    assert "- secret_handling: `Do not print tokens, API keys, or secrets; record endpoint and account identifiers only.`" in report
    assert report.count("- source_artifacts:") == 1
    assert "  - operator_input_readiness: `operator-input-readiness.json`" in report
    assert "  - current_blocker_matrix: `current-blocker-matrix.json`" in report
    assert "  - operator_input_template: `operator-inputs.template.env`" in report
    assert "  - proof_plan: `proof-plan.json`" in report
    assert "- must_capture:" in report
    assert "`durable platform ID or URL`" in report
    assert "- store_in:" in report
    assert "`system_design_vault/04-agent-studio-implications/agent-studio-objective-completion-audit.md`" in report
    assert "- next_status_packet: `current-proof-status.md`" in report
    assert "- next_operator_packet: `operator-unblocker-checklist.md`" in report
    assert "- proof_plan_packet: `proof-plan.json`" in report
    assert (
        "- proof_plan_packet_ref: `social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/proof-plan.json`"
    ) in report
    assert (
        "- proof_plan_packet_command: `uv run all-about-llms-admin "
        "provider-proof-plan --run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e "
        "--operator-input-path social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env "
        "> social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/proof-plan.json`"
    ) in report
    assert (
        "- proof_plan_operator_packet_ref: "
        "`/proofs/external-publication-proof/operator_proof_packet`"
    ) in report
    assert report.count("proof_record_schema:") == 2
    assert "- artifact_type: `external_publication_proof_record`" in report
    assert "- state_field: `external-publication-proof`" in report
    assert report.count("- allowed_outcomes:") == 2
    assert report.count("proof_record_required_fields:") == 2
    assert "`voice_agent_process_start_artifact_id`" not in report
    assert "`durable_platform_id_or_url`" in report
    assert "validate-provider-proof-preflight-artifacts --proof provider-backed-live-voice-proof" not in report
    assert "record-provider-proof-record --proof provider-backed-live-voice-proof" not in report
    assert "validate-provider-proof-preflight-artifacts --proof external-publication-proof" in report
    assert "record-provider-proof-record --proof external-publication-proof" in report
    publication_section = report.split("## External Publication", 1)[1].split(
        "## Completion Sequence",
        1,
    )[0]
    publication_capture_block = publication_section.split(
        "proof_capture_commands_after_unblock:",
        1,
    )[1].split("After those inputs are available", 1)[0]
    assert '"acknowledge_publish_channel_policy":true' in publication_capture_block
    assert '"acknowledge_publish_channel_policy":false' not in publication_capture_block
    assert "Current publication blocker status: `blocked`" in report
    assert "Current live voice blocker status:" not in report
    assert "Current publication blocker status: `unknown`" not in report
    live_voice_section = report.split("## Provider-Backed Live Voice", 1)[1].split(
        "## External Publication",
        1,
    )[0]
    assert "Accepted proof status:" in live_voice_section
    assert "Operator must still supply:" not in live_voice_section
    assert "No voice_agent_media_bridge_ready event was found" not in live_voice_section
    assert "OPENROUTER_API_KEY or OPENROUTER_API_KEY_FILE" not in live_voice_section
    assert "LIVEKIT_API_SECRET or LIVEKIT_API_SECRET_FILE" not in live_voice_section
    assert "validate-provider-proof-closure-review" in report
    assert "record-provider-proof-closure-review" in report
    assert "blocker-credential-snapshot --operator-input-path" in report
    assert "provider-proof-plan --run-id" in report
    assert "--operator-input-path" in report
    assert "credential-snapshot.json" in report
    assert "runtime_configuration_present_unverified" in report
    assert "Current snapshot state:" in report
    assert "snapshot checked_at: `2026-05-23`" in report
    assert "blocked_by_placeholder_only_configuration" in report
    assert "operator-inputs.template.env" in report
    assert "provider-proof-operator-input-readiness" in report
    assert "operator-input-readiness.json" in report
    assert "--fail-on-blocked" in report
    assert (
        "provider-proof-operator-input-readiness "
        "--run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e "
        "--input-path social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env "
        "--fail-on-blocked > social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-input-readiness.json"
    ) in report
    assert "Guarded retry sequence:" in report
    guarded_sequence = (
        "provider-proof-operator-input-readiness "
        "--run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e "
        "--input-path social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env "
        "--fail-on-blocked > social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-input-readiness.json\n"
        "uv run all-about-llms-admin blocker-credential-snapshot "
        "--operator-input-path social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env "
        "> social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/credential-snapshot.json\n"
        "uv run all-about-llms-admin provider-proof-plan "
        "--run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e "
        "--operator-input-path social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env "
        "> social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/proof-plan.json\n"
        "uv run all-about-llms-admin provider-proof-current-blocker-matrix "
        "--run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e "
        "--output-dir social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e > "
        "social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-blocker-matrix.json\n"
        "uv run all-about-llms-admin provider-proof-current-status "
        "--run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e "
        "--output-dir social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e > "
        "social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-proof-status.md\n"
        "uv run all-about-llms-admin provider-proof-operator-unblocker-checklist "
        "--run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e "
        "--output-dir social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e > "
        "social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-unblocker-checklist.md"
    )
    assert guarded_sequence in report
    assert "Current operator input readiness:" in report
    assert "HF_TOKEN or HF_TOKEN_FILE" not in report
    assert "input readiness checked_at: `2026-05-23`" in report
    assert "input readiness status: `blocked_by_operator_inputs`" in report
    assert "input readiness `--fail-on-blocked` exit code: `2`" in report
    assert "operator_input_secret_file_unavailable" in report
    assert "operator_input_placeholder" in report
    assert "input readiness blocked fields:" in report
    current_input_block = report.split("Current operator input readiness:", 1)[
        1
    ].split("- per-proof input readiness:", 1)[0]
    assert "input readiness required fields:" in current_input_block
    assert "input readiness configured fields:" in current_input_block
    assert "input readiness field contracts:" in current_input_block
    assert "input readiness field groups:" in current_input_block
    assert "input readiness field statuses:" in current_input_block
    assert "`HF_TOKEN_FILE`" not in current_input_block
    assert "`GEMMA4_MULTIMODAL_ENDPOINT_URL`" not in current_input_block
    assert "`LINKEDIN_ACCESS_TOKEN_FILE`" in current_input_block
    assert "readable local secret file path; file content is never emitted" in (
        current_input_block
    )
    assert "secret_file_unavailable" in current_input_block
    assert "endpoint_url" in current_input_block
    assert "  - placeholder_fields:" in current_input_block
    assert "  - unavailable_secret_file_fields:" in current_input_block
    assert "  - invalid_fields:" in current_input_block
    assert "  - missing_fields:" in current_input_block
    assert "per-proof input readiness:" in report
    per_proof_input_block = report.split("- per-proof input readiness:", 1)[1].split(
        "Validate the filled file",
        1,
    )[0]
    assert per_proof_input_block.count(" next_action_commands:") == 2
    assert per_proof_input_block.count(" guarded_next_action_commands:") == 2
    assert per_proof_input_block.count(" required fields:") == 2
    assert per_proof_input_block.count(" configured fields:") == 2
    assert per_proof_input_block.count(" field contracts:") == 2
    assert per_proof_input_block.count(" field statuses:") == 2
    assert (
        "provider-proof-operator-input-readiness "
        "--run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e "
        "--input-path social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env "
        "> social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-input-readiness.json"
    ) in per_proof_input_block
    assert (
        "provider-proof-operator-input-readiness "
        "--run-id 190ae2f9-a74b-4a23-b39c-aaf2d636bd8e "
        "--input-path social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-inputs.template.env "
        "--fail-on-blocked > social_media_optimiser/output/provider-proof/"
        "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-input-readiness.json"
    ) in per_proof_input_block
    assert (
        "`provider-backed-live-voice-proof`: "
        "`ready_for_credential_snapshot_refresh`"
    ) in report
    assert "`external-publication-proof`: `blocked_by_operator_inputs`" in report
    assert (
        "provider-backed-live-voice-proof next action: "
        "`refresh_credential_snapshot`"
    ) in report
    assert (
        "external-publication-proof next action: "
        "`supply_linkedin_token_policy_destination_and_rollback_evidence`"
    ) in report
    assert "provider-backed-live-voice-proof required evidence after unblock:" in report
    assert "same-run OpenRouter DeepSeek live dialogue reasoning evidence" in report
    assert "realtime voice timing ledger evidence" in report
    assert "external-publication-proof required evidence after unblock:" in report
    assert (
        "destination channel and durable URL linked to validated linkedin readiness"
        in report
    )
    assert "rollback or postcondition artifact" in report
    assert "provider-backed-live-voice-proof issue codes:" not in report
    assert "provider-backed-live-voice-proof placeholder fields:" not in report
    assert "provider-backed-live-voice-proof unavailable secret-file fields:" not in report
    assert "external-publication-proof issue codes:" in report
    assert "external-publication-proof placeholder fields:" in report
    assert "external-publication-proof unavailable secret-file fields:" in report
    assert "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID" in report
    assert "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL" in report
    assert "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID" in report
    assert "operator-checkpoint.json" in report
    assert "checkpoints.list.json" in report
    assert "operator_preflight" in report
    assert "cc9c7ff8-99d8-4656-9ef1-7412694602bb" in report
    assert "event cursor: `105458`" in report
    assert "HF_TOKEN" not in report
    assert "GEMMA4_MULTIMODAL_ENDPOINT_URL" not in report
    assert "LINKEDIN_ACCESS_TOKEN" in report
    assert str(ROOT) not in report


def test_concrete_provider_proof_closure_review_validation_report_is_current():
    output_dir = (
        ROOT
        / "social_media_optimiser/output/provider-proof/RUN-2026-05-20-NEXT"
    )
    template_path = output_dir / "closure-review-template.json"
    report_path = output_dir / "closure-review-validation.json"

    report = json.loads(report_path.read_text(encoding="utf-8"))
    record = json.loads(template_path.read_text(encoding="utf-8"))
    fresh_payload = provider_cli._provider_proof_closure_review_validation_payload(
        Namespace(
            env_example_path=ROOT / ".env.example",
            checked_at="2026-05-20",
            run_id="RUN-2026-05-20-NEXT",
            audit_target=None,
        ),
        record,
        env_values={},
    )

    assert report == fresh_payload
    assert report["artifact"] == (
        "agent-studio-provider-proof-closure-review-validation"
    )
    assert report["boundary"] == "no_secret_values_printed_no_state_change"
    assert report["run_id"] == "<run-id>"
    assert report["status"] == "invalid_closure_review"
    assert report["completion_status"] == "blocked_by_run_id"
    assert report["state_change_allowed"] is False
    assert report["blocker_state_update_allowed_after_review"] is False
    assert "completion_status_not_accepted" in report["issue_codes"]
    assert "missing_required_field" in report["issue_codes"]
    assert str(ROOT) not in json.dumps(report)


def test_concrete_provider_proof_closure_review_audit_report_is_current():
    output_dir = (
        ROOT
        / "social_media_optimiser/output/provider-proof/RUN-2026-05-20-NEXT"
    )
    template_path = output_dir / "closure-review-template.json"
    report_path = output_dir / "closure-review-audit.json"

    report = json.loads(report_path.read_text(encoding="utf-8"))
    record = json.loads(template_path.read_text(encoding="utf-8"))
    fresh_payload = provider_cli._record_provider_proof_closure_review_payload(
        Namespace(
            env_example_path=ROOT / ".env.example",
            checked_at="2026-05-20",
            run_id="RUN-2026-05-20-NEXT",
            proof_audit_target=None,
            audit_target=None,
        ),
        record,
        env_values={},
    )

    assert report == fresh_payload
    assert report["artifact"] == "agent-studio-provider-proof-closure-review-audit"
    assert report["boundary"] == "no_secret_values_printed_no_state_change"
    assert report["run_id"] == "<run-id>"
    assert report["status"] == "invalid_closure_review"
    assert report["validation_status"] == "invalid_closure_review"
    assert report["audit_recorded"] is False
    assert report["state_change_allowed"] is False
    assert report["blocker_state_update_allowed_after_review"] is False
    assert report["written_targets"] == []
    assert "completion_status_not_accepted" in report["validation_issue_codes"]
    assert str(ROOT) not in json.dumps(report)


@pytest.mark.parametrize(
    ("proof", "template_name", "report_name"),
    [
        (
            "provider-backed-live-voice-proof",
            "provider-backed-live-voice-proof.template.json",
            "provider-backed-live-voice-proof.record-validation.json",
        ),
        (
            "external-publication-proof",
            "external-publication-proof.template.json",
            "external-publication-proof.record-validation.json",
        ),
    ],
)
def test_concrete_provider_proof_record_validation_report_is_current(
    proof,
    template_name,
    report_name,
):
    output_dir = (
        ROOT
        / "social_media_optimiser/output/provider-proof/RUN-2026-05-20-NEXT"
    )
    template_path = output_dir / template_name
    report_path = output_dir / report_name

    report = json.loads(report_path.read_text(encoding="utf-8"))
    record = json.loads(template_path.read_text(encoding="utf-8"))
    fresh_payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=ROOT / ".env.example",
            checked_at="2026-05-20",
            run_id="RUN-2026-05-20-NEXT",
            proof=proof,
            preflight_validation_path=(
                output_dir / f"{proof}.preflight-validation.json"
            ),
            workspace_validation_path=output_dir / "workspace-validation.json",
        ),
        record,
        env_values={},
    )

    assert report == fresh_payload
    assert report["artifact"] == "agent-studio-provider-proof-record-validation"
    assert report["boundary"] == "no_secret_values_printed_no_state_change"
    assert report["proof"] == proof
    assert report["command_run_id"] == "<run-id>"
    assert report["status"] == "invalid_record"
    assert report["state_change_allowed"] is False
    assert report["proof_outcome"] is None
    assert report["issue_codes"] == [
        "missing_required_field",
        "invalid_outcome",
        "run_id_not_product_uuid",
        "missing_validation_results",
        "secret_redaction_check_not_passed",
    ]
    assert str(ROOT) not in json.dumps(report)


@pytest.mark.parametrize(
    ("proof", "template_name", "report_name"),
    [
        (
            "provider-backed-live-voice-proof",
            "provider-backed-live-voice-proof.template.json",
            "provider-backed-live-voice-proof.record-audit.json",
        ),
        (
            "external-publication-proof",
            "external-publication-proof.template.json",
            "external-publication-proof.record-audit.json",
        ),
    ],
)
def test_concrete_provider_proof_record_audit_report_is_current(
    proof,
    template_name,
    report_name,
):
    output_dir = (
        ROOT
        / "social_media_optimiser/output/provider-proof/RUN-2026-05-20-NEXT"
    )
    template_path = output_dir / template_name
    report_path = output_dir / report_name

    report = json.loads(report_path.read_text(encoding="utf-8"))
    record = json.loads(template_path.read_text(encoding="utf-8"))
    fresh_payload = _record_provider_proof_record_payload(
        Namespace(
            env_example_path=ROOT / ".env.example",
            checked_at="2026-05-20",
            run_id="RUN-2026-05-20-NEXT",
            proof=proof,
            audit_target=None,
            preflight_validation_path=(
                output_dir / f"{proof}.preflight-validation.json"
            ),
            workspace_validation_path=output_dir / "workspace-validation.json",
        ),
        record,
        env_values={},
    )

    assert report == fresh_payload
    assert report["artifact"] == "agent-studio-provider-proof-record-audit"
    assert report["boundary"] == "no_secret_values_printed_no_state_change"
    assert report["proof"] == proof
    assert report["command_run_id"] == "<run-id>"
    assert report["proof_outcome"] is None
    assert report["status"] == "invalid_record"
    assert report["validation_status"] == "invalid_record"
    assert report["validation_issue_codes"] == [
        "missing_required_field",
        "invalid_outcome",
        "run_id_not_product_uuid",
        "missing_validation_results",
        "secret_redaction_check_not_passed",
    ]
    assert report["audit_recorded"] is False
    assert report["state_change_allowed"] is False
    assert report["written_targets"] == []
    assert str(ROOT) not in json.dumps(report)


def test_concrete_preflight_validation_uses_portable_report_paths():
    preflight_dir = (
        ROOT
        / "social_media_optimiser/output/provider-proof/RUN-2026-05-20-NEXT"
    )
    payload = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=ROOT / ".env.example",
            checked_at="2026-05-20",
            run_id="RUN-2026-05-20-NEXT",
            proof="provider-backed-live-voice-proof",
            preflight_dir=preflight_dir,
        ),
        env_values={},
    )

    assert str(ROOT) not in json.dumps(payload)
    assert payload["preflight_dir"] == (
        "<workspace-root>/social_media_optimiser/output/provider-proof/"
        "RUN-2026-05-20-NEXT"
    )
    assert payload["expected_files"] == [
        (
            "<workspace-root>/social_media_optimiser/output/provider-proof/"
            "RUN-2026-05-20-NEXT/product-run.preflight.json"
        ),
        (
            "<workspace-root>/social_media_optimiser/output/provider-proof/"
            "RUN-2026-05-20-NEXT/provider-readiness.preflight.json"
        ),
        (
            "<workspace-root>/social_media_optimiser/output/provider-proof/"
            "RUN-2026-05-20-NEXT/voice-runtime-readiness.preflight.json"
        ),
    ]
    assert payload["status"] == "invalid_preflight_artifacts"
    assert payload["issue_codes"] == [
        "run_id_not_product_uuid",
        "preflight_file_missing",
    ]
    assert [issue["field"] for issue in payload["issues"][1:]] == payload[
        "expected_files"
    ]


@pytest.mark.parametrize(
    ("proof", "report_name", "expected_issue_count"),
    [
            (
                "provider-backed-live-voice-proof",
                "provider-backed-live-voice-proof.preflight-validation.json",
                3,
            ),
            (
                "external-publication-proof",
                "external-publication-proof.preflight-validation.json",
                2,
            ),
    ],
)
def test_concrete_provider_proof_preflight_validation_report_is_current(
    proof,
    report_name,
    expected_issue_count,
):
    preflight_dir = (
        ROOT
        / "social_media_optimiser/output/provider-proof/RUN-2026-05-20-NEXT"
    )
    report_path = preflight_dir / report_name

    report = json.loads(report_path.read_text(encoding="utf-8"))
    fresh_payload = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=ROOT / ".env.example",
            checked_at="2026-05-20",
            run_id="RUN-2026-05-20-NEXT",
            proof=proof,
            preflight_dir=preflight_dir,
        ),
        env_values={},
    )

    assert report == fresh_payload
    assert report["artifact"] == (
        "agent-studio-provider-proof-preflight-artifacts-validation"
    )
    assert report["proof"] == proof
    assert report["command_run_id"] == "<run-id>"
    assert report["status"] == "invalid_preflight_artifacts"
    assert report["state_change_allowed"] is False
    assert report["issue_codes"] == [
        "run_id_not_product_uuid",
        "preflight_file_missing",
    ]
    assert len(report["issues"]) == expected_issue_count + 1
    assert report["preflight_artifact_ids"] == {}
    assert str(ROOT) not in json.dumps(report)


def test_provider_proof_workspace_and_preflight_commands_redact_token_shaped_output_dir(
    tmp_path,
):
    secret_segment = "sk-ABCDEFGHIJKLMNOPQRST"
    output_dir = tmp_path / secret_segment / "proof-workspace"

    commands = [
        *provider_cli._proof_workspace_commands_for_output("123e4567-e89b-12d3-a456-426614174000", output_dir),
        *provider_cli._proof_workspace_validation_commands_for_output(
            "123e4567-e89b-12d3-a456-426614174000",
            output_dir,
        ),
        *provider_cli._proof_workspace_validation_capture_commands_for_output(
            "123e4567-e89b-12d3-a456-426614174000",
            output_dir,
        ),
        *provider_cli._proof_preflight_capture_commands_for_output(
            "provider-backed-live-voice-proof",
            "123e4567-e89b-12d3-a456-426614174000",
            output_dir,
        ),
        *provider_cli._proof_preflight_validation_commands_for_output(
            "provider-backed-live-voice-proof",
            "123e4567-e89b-12d3-a456-426614174000",
            output_dir,
        ),
        *provider_cli._proof_preflight_validation_capture_commands_for_output(
            "provider-backed-live-voice-proof",
            "123e4567-e89b-12d3-a456-426614174000",
            output_dir,
        ),
    ]
    serialized = json.dumps(commands)

    assert secret_segment not in serialized
    assert "<redacted>" in serialized


def test_provider_proof_workspace_validation_accepts_current_workspace(tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    output_dir = tmp_path / "proof workspace"
    args = Namespace(
        env_example_path=env_example,
        checked_at="2026-05-20",
        run_id="123e4567-e89b-12d3-a456-426614174000",
        output_dir=output_dir,
    )
    _provider_proof_workspace_payload(args)

    payload = provider_cli._provider_proof_workspace_validation_payload(args)

    assert payload["artifact"] == "agent-studio-provider-proof-workspace-validation"
    assert payload["boundary"] == "no_secret_values_printed_no_state_change"
    assert payload["status"] == "valid_workspace"
    assert payload["state_change_allowed"] is False
    assert payload["issue_codes"] == []
    assert payload["validated_files"] == [
        str(output_dir / "provider-backed-live-voice-proof.template.json"),
        str(output_dir / "external-publication-proof.template.json"),
        str(output_dir / "operator-inputs.template.env"),
        str(output_dir / "README.md"),
    ]


def test_provider_proof_workspace_validation_rejects_stale_readme(tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    output_dir = tmp_path / "proof workspace"
    args = Namespace(
        env_example_path=env_example,
        checked_at="2026-05-20",
        run_id="123e4567-e89b-12d3-a456-426614174000",
        output_dir=output_dir,
    )
    _provider_proof_workspace_payload(args)
    (output_dir / "README.md").write_text(
        "# Provider Proof Workspace\n\nstale handoff\n",
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_workspace_validation_payload(args)

    assert payload["status"] == "invalid_workspace"
    assert payload["state_change_allowed"] is False
    assert "workspace_file_mismatch" in payload["issue_codes"]
    assert payload["issues"] == [
        {
            "code": "workspace_file_mismatch",
            "field": str(output_dir / "README.md"),
            "detail": "workspace file does not match the current proof plan",
        }
    ]


def test_provider_proof_workspace_validation_redacts_secret_shaped_paths(tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    secret_segment = "sk-ABCDEFGHIJKLMNOPQRST"
    output_dir = tmp_path / secret_segment
    output_dir.mkdir()

    payload = provider_cli._provider_proof_workspace_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            output_dir=output_dir,
        )
    )
    serialized = json.dumps(payload)

    assert payload["status"] == "invalid_workspace"
    assert payload["state_change_allowed"] is False
    assert "workspace_path_secret_shape_detected" in payload["issue_codes"]
    assert payload["expected_files"] == []
    assert payload["validated_files"] == []
    assert secret_segment not in serialized
    assert "<redacted>" in serialized


def test_provider_proof_workspace_init_redacts_secret_shaped_output_dir(tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    secret_segment = "sk-ABCDEFGHIJKLMNOPQRST"
    output_dir = tmp_path / secret_segment

    payload = _provider_proof_workspace_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            output_dir=output_dir,
        )
    )
    serialized = json.dumps(payload)

    assert payload["status"] == "invalid_workspace"
    assert payload["written_files"] == []
    assert "workspace_path_secret_shape_detected" in payload["issue_codes"]
    assert not output_dir.exists()
    assert secret_segment not in serialized
    assert "<redacted>" in serialized


def test_provider_proof_workspace_init_rejects_non_directory_output_ancestor(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    output_root = tmp_path / "provider-proof"
    output_root.write_text("not a directory", encoding="utf-8")
    output_dir = output_root / PROVIDER_PROOF_TEST_RUN_UUID

    payload = _provider_proof_workspace_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            output_dir=output_dir,
        )
    )

    assert payload["status"] == "invalid_workspace"
    assert payload["written_files"] == []
    assert payload["issue_codes"] == ["workspace_path_unwritable"]
    assert payload["issues"] == [
        {
            "code": "workspace_path_unwritable",
            "field": str(output_dir),
            "detail": (
                "output_dir or an existing ancestor is not a directory"
            ),
        }
    ]


def test_provider_proof_workspace_init_rejects_broken_symlink_output_ancestor(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    output_root = tmp_path / "provider-proof"
    output_root.symlink_to(tmp_path / "missing-provider-proof-root")
    output_dir = output_root / PROVIDER_PROOF_TEST_RUN_UUID

    payload = _provider_proof_workspace_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            output_dir=output_dir,
        )
    )

    assert payload["status"] == "invalid_workspace"
    assert payload["written_files"] == []
    assert payload["issue_codes"] == ["workspace_path_unwritable"]


def test_provider_proof_preflight_artifacts_validation_accepts_voice_outputs(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    _write_product_run_preflight(preflight_dir)
    (preflight_dir / "provider-readiness.preflight.json").write_text(
        json.dumps(_ready_provider_readiness_preflight_payload()),
        encoding="utf-8",
    )
    (preflight_dir / "voice-runtime-readiness.preflight.json").write_text(
        json.dumps(_ready_voice_runtime_preflight_payload()),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            preflight_dir=preflight_dir,
        )
    )

    assert (
        payload["artifact"]
        == "agent-studio-provider-proof-preflight-artifacts-validation"
    )
    assert payload["boundary"] == "no_secret_values_printed_no_state_change"
    assert payload["status"] == "valid_preflight_artifacts"
    assert payload["state_change_allowed"] is False
    assert payload["issue_codes"] == []
    assert payload["expected_files"] == [
        str(preflight_dir / "product-run.preflight.json"),
        str(preflight_dir / "provider-readiness.preflight.json"),
        str(preflight_dir / "voice-runtime-readiness.preflight.json"),
    ]
    assert payload["validated_files"] == payload["expected_files"]
    assert payload["preflight_artifact_ids"] == {
        "product_run_preflight_artifact_id": str(
            preflight_dir / "product-run.preflight.json"
        ),
        "provider_readiness_preflight_artifact_id": str(
            preflight_dir / "provider-readiness.preflight.json"
        ),
        "voice_runtime_readiness_preflight_artifact_id": str(
            preflight_dir / "voice-runtime-readiness.preflight.json"
        ),
    }
    assert payload["validated_product_run_id"] == PROVIDER_PROOF_TEST_RUN_UUID


def test_provider_proof_preflight_artifacts_validation_accepts_deepseek_openrouter_livekit_dialogue_proof(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    _write_product_run_preflight(preflight_dir)
    (preflight_dir / "provider-readiness.preflight.json").write_text(
        json.dumps(_ready_provider_readiness_preflight_payload()),
        encoding="utf-8",
    )
    (preflight_dir / "voice-runtime-readiness.preflight.json").write_text(
        json.dumps(_ready_openrouter_text_turn_voice_runtime_preflight_payload()),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            preflight_dir=preflight_dir,
        )
    )

    assert payload["status"] == "valid_preflight_artifacts"
    assert payload["issue_codes"] == []
    assert payload["validated_runtime_checks"] == list(
        provider_cli.VOICE_PROOF_REQUIRED_RUNTIME_CHECKS
    )
    assert "openrouter-live-dialogue-reasoning" in payload[
        "validated_runtime_checks"
    ]
    assert "voice-agent-backend-event-sink" in payload[
        "validated_runtime_checks"
    ]
    assert "gemma-audio-reasoning" not in payload["validated_runtime_checks"]


def test_provider_proof_preflight_artifacts_validation_accepts_openrouter_dialogue_with_optional_native_audio_check(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    _write_product_run_preflight(preflight_dir)
    voice_payload = _ready_voice_runtime_preflight_payload()
    voice_payload["checks"].append(
        {
            "check_id": "gemma-audio-reasoning",
            "label": "Legacy Gemma native-audio reasoning",
            "status": "ready",
            "required": False,
            "evidence": ["Legacy native-audio route is configured but optional."],
            "missing_env": [],
            "next_actions": [],
            "metadata": {"voice_reasoning_provider": "gemma_native_audio"},
        }
    )
    (preflight_dir / "provider-readiness.preflight.json").write_text(
        json.dumps(_ready_provider_readiness_preflight_payload()),
        encoding="utf-8",
    )
    (preflight_dir / "voice-runtime-readiness.preflight.json").write_text(
        json.dumps(voice_payload),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            preflight_dir=preflight_dir,
        )
    )

    assert payload["status"] == "valid_preflight_artifacts"
    assert payload["issue_codes"] == []
    assert payload["validated_runtime_checks"] == list(
        provider_cli.VOICE_PROOF_REQUIRED_RUNTIME_CHECKS
    )
    assert "openrouter-live-dialogue-reasoning" in payload[
        "validated_runtime_checks"
    ]


def test_provider_proof_preflight_artifacts_validation_rejects_non_ready_voice_payloads(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    provider_payload = _ready_provider_readiness_preflight_payload()
    provider_payload["providers"][0]["status"] = "missing_config"
    provider_payload["ready_provider_ids"] = []
    voice_payload = _ready_voice_runtime_preflight_payload()
    voice_payload["status"] = "blocked"
    voice_payload["checks"][0]["status"] = "blocked"
    (preflight_dir / "provider-readiness.preflight.json").write_text(
        json.dumps(provider_payload),
        encoding="utf-8",
    )
    (preflight_dir / "voice-runtime-readiness.preflight.json").write_text(
        json.dumps(voice_payload),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            preflight_dir=preflight_dir,
        )
    )

    assert payload["status"] == "invalid_preflight_artifacts"
    assert payload["preflight_artifact_ids"] == {}
    assert "provider_readiness_openrouter_livekit_not_ready" in payload["issue_codes"]
    assert "voice_runtime_readiness_not_ready" in payload["issue_codes"]
    assert "voice_runtime_required_check_not_ready" in payload["issue_codes"]


def test_provider_proof_preflight_artifacts_validation_rejects_duplicate_voice_runtime_check_ids(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    voice_payload = _ready_voice_runtime_preflight_payload()
    voice_payload["checks"][0]["status"] = "blocked"
    voice_payload["checks"].append(
        {
            **voice_payload["checks"][0],
            "status": "ready",
            "evidence": ["duplicate ready check"],
        }
    )
    (preflight_dir / "provider-readiness.preflight.json").write_text(
        json.dumps(_ready_provider_readiness_preflight_payload()),
        encoding="utf-8",
    )
    (preflight_dir / "voice-runtime-readiness.preflight.json").write_text(
        json.dumps(voice_payload),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            preflight_dir=preflight_dir,
        )
    )

    assert payload["status"] == "invalid_preflight_artifacts"
    assert payload["preflight_artifact_ids"] == {}
    assert "voice_runtime_duplicate_check_id" in payload["issue_codes"]


def test_provider_proof_preflight_artifacts_validation_redacts_duplicate_voice_check_ids(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    provider_payload = _ready_provider_readiness_preflight_payload()
    voice_payload = _ready_voice_runtime_preflight_payload()
    secret_shaped_check_id = "sk-ABCDEFGHIJKLMNOPQRST"
    duplicate_check = dict(voice_payload["checks"][0])
    duplicate_check["check_id"] = secret_shaped_check_id
    voice_payload["checks"].append(duplicate_check)
    duplicate_check = dict(duplicate_check)
    duplicate_check["status"] = "blocked"
    voice_payload["checks"].append(duplicate_check)
    (preflight_dir / "provider-readiness.preflight.json").write_text(
        json.dumps(provider_payload),
        encoding="utf-8",
    )
    (preflight_dir / "voice-runtime-readiness.preflight.json").write_text(
        json.dumps(voice_payload),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            preflight_dir=preflight_dir,
        )
    )

    serialized = json.dumps(payload)
    assert payload["status"] == "invalid_preflight_artifacts"
    assert payload["preflight_artifact_ids"] == {}
    assert "voice_runtime_duplicate_check_id" in payload["issue_codes"]
    assert "token_shaped_value_detected" in payload["issue_codes"]
    assert secret_shaped_check_id not in serialized


def test_provider_proof_preflight_artifacts_validation_accepts_publication_policy_review_payload(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    _write_product_run_preflight(preflight_dir)
    (preflight_dir / "publish-readiness.preflight.json").write_text(
        json.dumps(_publish_readiness_preflight_payload()),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
            preflight_dir=preflight_dir,
        )
    )

    assert payload["status"] == "valid_preflight_artifacts"
    assert payload["issue_codes"] == []
    assert payload["preflight_artifact_ids"] == {
        "product_run_preflight_artifact_id": str(
            preflight_dir / "product-run.preflight.json"
        ),
        "publish_readiness_preflight_artifact_id": str(
            preflight_dir / "publish-readiness.preflight.json"
        )
    }
    assert payload["validated_product_run_id"] == PROVIDER_PROOF_TEST_RUN_UUID


def test_provider_proof_preflight_artifacts_validation_rejects_duplicate_publish_channel_checks(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    payload = _publish_readiness_preflight_payload(
        status="ready",
        ready=True,
        blocking_issues=[],
        policy_status="acknowledged",
    )
    payload["publish_channel_checks"].append(dict(payload["publish_channel_checks"][0]))
    (preflight_dir / "publish-readiness.preflight.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    validation = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
            preflight_dir=preflight_dir,
        )
    )

    assert validation["status"] == "invalid_preflight_artifacts"
    assert validation["preflight_artifact_ids"] == {}
    assert "publish_channel_duplicate_platform" in validation["issue_codes"]


def test_provider_proof_preflight_artifacts_validation_rejects_duplicate_publish_channel_aliases(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    payload = _publish_readiness_preflight_payload(
        status="ready",
        ready=True,
        blocking_issues=[],
        policy_status="acknowledged",
    )
    first_check = payload["publish_channel_checks"][0]
    first_check["platform"] = "x"
    first_check["credential_envs"] = ["X_ACCESS_TOKEN"]
    payload["publish_channel_checks"].append(
        {
            "platform": "twitter",
            "credential_envs": ["X_ACCESS_TOKEN"],
            "credential_status": "configured",
            "policy_status": "acknowledged",
            "blocking_issues": [],
            "recommended_next_actions": [],
        }
    )
    (preflight_dir / "publish-readiness.preflight.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    validation = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
            preflight_dir=preflight_dir,
        )
    )

    assert validation["status"] == "invalid_preflight_artifacts"
    assert validation["preflight_artifact_ids"] == {}
    assert "publish_channel_duplicate_platform" in validation["issue_codes"]


def test_provider_proof_preflight_artifacts_validation_rejects_blank_publish_channel_platform(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    payload = _publish_readiness_preflight_payload(
        status="ready",
        ready=True,
        blocking_issues=[],
        policy_status="acknowledged",
    )
    payload["publish_channel_checks"][0]["platform"] = "   "
    (preflight_dir / "publish-readiness.preflight.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    validation = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
            preflight_dir=preflight_dir,
        )
    )

    assert validation["status"] == "invalid_preflight_artifacts"
    assert validation["preflight_artifact_ids"] == {}
    assert "publish_channel_platform_missing" in validation["issue_codes"]


def test_provider_proof_preflight_artifacts_validation_rejects_unknown_publish_channel_platform(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    payload = _publish_readiness_preflight_payload(
        status="ready",
        ready=True,
        blocking_issues=[],
        policy_status="acknowledged",
    )
    check = payload["publish_channel_checks"][0]
    check["platform"] = "mastodon"
    check["credential_envs"] = ["MASTODON_ACCESS_TOKEN"]
    (preflight_dir / "publish-readiness.preflight.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    validation = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
            preflight_dir=preflight_dir,
        )
    )

    assert validation["status"] == "invalid_preflight_artifacts"
    assert validation["preflight_artifact_ids"] == {}
    assert "publish_channel_platform_unsupported" in validation["issue_codes"]


def test_provider_proof_preflight_artifacts_validation_rejects_ready_publication_with_unacknowledged_policy(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    (preflight_dir / "publish-readiness.preflight.json").write_text(
        json.dumps(
            _publish_readiness_preflight_payload(
                status="ready",
                ready=True,
                blocking_issues=[],
                policy_status="needs_review",
            )
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
            preflight_dir=preflight_dir,
        )
    )

    assert payload["status"] == "invalid_preflight_artifacts"
    assert payload["preflight_artifact_ids"] == {}
    assert "publish_channel_policy_not_reviewed" in payload["issue_codes"]


def test_provider_proof_preflight_artifacts_validation_rejects_ready_publication_with_channel_blockers(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    payload = _publish_readiness_preflight_payload(
        status="ready",
        ready=True,
        blocking_issues=[],
        policy_status="acknowledged",
    )
    payload["publish_channel_checks"][0]["blocking_issues"] = [
        "publish_channel_policy_review_required"
    ]
    (preflight_dir / "publish-readiness.preflight.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    validation = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
            preflight_dir=preflight_dir,
        )
    )

    assert validation["status"] == "invalid_preflight_artifacts"
    assert validation["preflight_artifact_ids"] == {}
    assert "publish_channel_blocking_issues_present" in validation["issue_codes"]


def test_provider_proof_preflight_artifacts_validation_rejects_policy_review_handoff_without_pending_channel_policy(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    (preflight_dir / "publish-readiness.preflight.json").write_text(
        json.dumps(
            _publish_readiness_preflight_payload(
                status="needs_review",
                ready=False,
                blocking_issues=["publish_channel_policy_review_required"],
                policy_status="acknowledged",
            )
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
            preflight_dir=preflight_dir,
        )
    )

    assert payload["status"] == "invalid_preflight_artifacts"
    assert payload["preflight_artifact_ids"] == {}
    assert "publish_channel_policy_review_not_pending" in payload["issue_codes"]


def test_provider_proof_preflight_artifacts_validation_rejects_duplicate_policy_review_blockers(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    (preflight_dir / "publish-readiness.preflight.json").write_text(
        json.dumps(
            _publish_readiness_preflight_payload(
                status="needs_review",
                ready=False,
                blocking_issues=[
                    "publish_channel_policy_review_required",
                    "publish_channel_policy_review_required",
                ],
                policy_status="needs_review",
            )
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
            preflight_dir=preflight_dir,
        )
    )

    assert payload["status"] == "invalid_preflight_artifacts"
    assert payload["preflight_artifact_ids"] == {}
    assert "publish_readiness_not_ready" in payload["issue_codes"]


def test_provider_proof_preflight_artifacts_validation_rejects_non_policy_channel_blockers_in_review_handoff(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    payload = _publish_readiness_preflight_payload(
        status="needs_review",
        ready=False,
        blocking_issues=["publish_channel_policy_review_required"],
        policy_status="needs_review",
    )
    payload["publish_channel_checks"][0]["blocking_issues"] = [
        "unsupported_publish_channel"
    ]
    (preflight_dir / "publish-readiness.preflight.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    validation = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
            preflight_dir=preflight_dir,
        )
    )

    assert validation["status"] == "invalid_preflight_artifacts"
    assert validation["preflight_artifact_ids"] == {}
    assert "publish_channel_blocking_issues_not_policy_review" in validation[
        "issue_codes"
    ]


def test_provider_proof_preflight_artifacts_validation_rejects_acknowledged_channel_policy_blocker_in_review_handoff(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    payload = _publish_readiness_preflight_payload(
        status="needs_review",
        ready=False,
        blocking_issues=["publish_channel_policy_review_required"],
        policy_status="needs_review",
    )
    payload["publish_channel_checks"][0]["blocking_issues"] = [
        "publish_channel_policy_review_required"
    ]
    payload["publish_channel_checks"].append(
        {
            "platform": "instagram",
            "credential_envs": ["INSTAGRAM_ACCESS_TOKEN"],
            "credential_status": "configured",
            "policy_status": "acknowledged",
            "blocking_issues": ["publish_channel_policy_review_required"],
            "recommended_next_actions": [],
        }
    )
    (preflight_dir / "publish-readiness.preflight.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    validation = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
            preflight_dir=preflight_dir,
        )
    )

    assert validation["status"] == "invalid_preflight_artifacts"
    assert validation["preflight_artifact_ids"] == {}
    assert "publish_channel_policy_blocker_already_acknowledged" in validation[
        "issue_codes"
    ]


def test_provider_proof_preflight_artifacts_validation_rejects_blocked_publication_payload(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    (preflight_dir / "publish-readiness.preflight.json").write_text(
        json.dumps(
            _publish_readiness_preflight_payload(
                status="blocked",
                blocking_issues=["missing_publish_channel_credentials"],
                credential_status="missing",
            )
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
            preflight_dir=preflight_dir,
        )
    )

    assert payload["status"] == "invalid_preflight_artifacts"
    assert payload["preflight_artifact_ids"] == {}
    assert "publish_readiness_not_ready" in payload["issue_codes"]
    assert "publish_channel_credentials_not_configured" in payload["issue_codes"]


def test_provider_proof_preflight_artifacts_validation_rejects_non_policy_publication_review(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    (preflight_dir / "publish-readiness.preflight.json").write_text(
        json.dumps(
            _publish_readiness_preflight_payload(
                status="needs_review",
                blocking_issues=["claims_need_review"],
            )
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
            preflight_dir=preflight_dir,
        )
    )

    assert payload["status"] == "invalid_preflight_artifacts"
    assert payload["preflight_artifact_ids"] == {}
    assert "publish_readiness_not_ready" in payload["issue_codes"]


def test_provider_proof_preflight_artifacts_validation_rejects_empty_publication_review(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    (preflight_dir / "publish-readiness.preflight.json").write_text(
        json.dumps(
            _publish_readiness_preflight_payload(
                status="needs_review",
                blocking_issues=[],
            )
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
            preflight_dir=preflight_dir,
        )
    )

    assert payload["status"] == "invalid_preflight_artifacts"
    assert payload["preflight_artifact_ids"] == {}
    assert "publish_readiness_not_ready" in payload["issue_codes"]


def test_provider_proof_preflight_artifacts_validation_rejects_secret_values(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    secret_value = "hf_secret_preflight_test_must_not_echo"
    (preflight_dir / "publish-readiness.preflight.json").write_text(
        json.dumps({"status": "blocked", "debug": secret_value}),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
            preflight_dir=preflight_dir,
        )
    )
    serialized = json.dumps(payload)

    assert payload["status"] == "invalid_preflight_artifacts"
    assert payload["state_change_allowed"] is False
    assert "token_shaped_value_detected" in payload["issue_codes"]
    assert payload["validated_files"] == []
    assert payload["preflight_artifact_ids"] == {}
    assert secret_value not in serialized


def test_provider_proof_preflight_artifacts_validation_rejects_missing_or_invalid_json(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    (preflight_dir / "provider-readiness.preflight.json").write_text(
        "{not-valid-json",
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            preflight_dir=preflight_dir,
        )
    )

    assert payload["status"] == "invalid_preflight_artifacts"
    assert payload["state_change_allowed"] is False
    assert payload["validated_files"] == []
    assert payload["preflight_artifact_ids"] == {}
    assert "preflight_file_invalid_json" in payload["issue_codes"]
    assert "preflight_file_missing" in payload["issue_codes"]


def test_provider_proof_preflight_artifacts_validation_handles_unreadable_file(
    tmp_path,
    monkeypatch,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    _write_product_run_preflight(preflight_dir)
    unreadable_file = preflight_dir / "provider-readiness.preflight.json"
    unreadable_file.write_text("{}", encoding="utf-8")
    (preflight_dir / "voice-runtime-readiness.preflight.json").write_text(
        json.dumps(_ready_voice_runtime_preflight_payload()),
        encoding="utf-8",
    )
    original_read_text = Path.read_text

    def fail_expected_file_read(path, *args, **kwargs):
        if path == unreadable_file:
            raise OSError("permission denied")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_expected_file_read)

    payload = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            preflight_dir=preflight_dir,
        )
    )

    assert payload["status"] == "invalid_preflight_artifacts"
    assert payload["state_change_allowed"] is False
    assert payload["validated_files"] == [
        str(preflight_dir / "product-run.preflight.json"),
        str(preflight_dir / "voice-runtime-readiness.preflight.json"),
    ]
    assert payload["preflight_artifact_ids"] == {}
    assert "preflight_file_unreadable" in payload["issue_codes"]
    assert payload["issues"][0] == {
        "code": "preflight_file_unreadable",
        "field": str(unreadable_file),
    }


def test_provider_proof_preflight_artifacts_validation_redacts_secret_shaped_paths(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    secret_segment = "sk-ABCDEFGHIJKLMNOPQRST"
    preflight_dir = tmp_path / secret_segment
    preflight_dir.mkdir()
    (preflight_dir / "publish-readiness.preflight.json").write_text(
        json.dumps({"status": "blocked"}),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_preflight_artifacts_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
            preflight_dir=preflight_dir,
        )
    )
    serialized = json.dumps(payload)

    assert payload["status"] == "invalid_preflight_artifacts"
    assert payload["state_change_allowed"] is False
    assert "token_shaped_value_detected" in payload["issue_codes"]
    assert payload["preflight_artifact_ids"] == {}
    assert secret_segment not in serialized
    assert "<redacted>" in serialized


def test_provider_proof_workspace_blocks_placeholder_run_id_without_writes(tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    output_dir = tmp_path / "proof-workspace"

    payload = _provider_proof_workspace_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="<run-id>",
            output_dir=output_dir,
        ),
    )

    assert payload["status"] == "blocked_by_run_id"
    assert payload["run_id_state"] == "placeholder_run_id"
    assert payload["next_action"] == "replace_run_id_and_initialize_workspace"
    assert payload["next_action_commands"] == [
        (
            "uv run all-about-llms-admin init-provider-proof-workspace "
            f"--run-id <run-id> --output-dir {output_dir}"
        )
    ]
    assert payload["written_files"] == []
    assert payload["issue_codes"] == ["run_id_not_concrete"]
    assert not output_dir.exists()


def test_provider_proof_workspace_blocks_non_uuid_product_run_id_without_writes(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    output_dir = tmp_path / "proof-workspace"

    payload = _provider_proof_workspace_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="RUN-2026-05-20-NEXT",
            output_dir=output_dir,
        ),
    )
    serialized = json.dumps(payload)

    assert payload["status"] == "blocked_by_run_id"
    assert payload["run_id"] == "<run-id>"
    assert payload["run_id_state"] == "concrete_run_id"
    assert payload["product_run_id_state"] == "non_uuid_run_id"
    assert payload["next_action"] == "replace_run_id_and_initialize_workspace"
    assert payload["written_files"] == []
    assert payload["issue_codes"] == ["run_id_not_product_uuid"]
    assert "RUN-2026-05-20-NEXT" not in serialized
    assert not output_dir.exists()


def test_provider_proof_workspace_does_not_emit_secret_shaped_run_id(tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    output_dir = tmp_path / "proof-workspace"
    secret_shaped_run_id = "sk-" + "ABCDEFGHIJKLMNOPQRST"

    payload = _provider_proof_workspace_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id=secret_shaped_run_id,
            output_dir=output_dir,
        ),
    )
    serialized = json.dumps(payload)

    assert payload["status"] == "blocked_by_run_id"
    assert payload["run_id"] == "<run-id>"
    assert payload["run_id_state"] == "unsafe_run_id"
    assert payload["next_action"] == "replace_run_id_and_initialize_workspace"
    assert payload["next_action_commands"] == [
        (
            "uv run all-about-llms-admin init-provider-proof-workspace "
            f"--run-id <run-id> --output-dir {output_dir}"
        )
    ]
    assert payload["written_files"] == []
    assert "<run-id>" in " ".join(payload["next_action_commands"])
    assert secret_shaped_run_id not in serialized
    assert not output_dir.exists()


def test_provider_proof_workspace_refuses_to_overwrite_existing_files(tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    output_dir = tmp_path / "proof-workspace"
    output_dir.mkdir()
    existing = output_dir / "provider-backed-live-voice-proof.template.json"
    existing.write_text("operator edits stay intact\n", encoding="utf-8")

    payload = _provider_proof_workspace_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            output_dir=output_dir,
        ),
    )

    assert payload["status"] == "workspace_exists"
    assert payload["written_files"] == []
    assert payload["existing_files"] == [str(existing)]
    assert existing.read_text(encoding="utf-8") == "operator edits stay intact\n"
    assert not (output_dir / "external-publication-proof.template.json").exists()
    assert not (output_dir / "README.md").exists()


def test_provider_proof_record_validation_rejects_missing_fields_and_secrets(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    record = {
        "run_id": "123e4567-e89b-12d3-a456-426614174000",
        "checked_at": "2026-05-20",
        "validation_timestamp": "2026-05-20T12:00:00Z",
        "proof_outcome": "accepted",
        "publish_readiness_preflight_artifact_id": "publish-preflight",
        "publish_readiness_artifact_id": "publish-ready",
        "distribution_package_artifact_id": "distribution",
        "approved_artifact_snapshot_id": "approved",
        "destination_channel": "linkedin",
        "durable_platform_id_or_url": "https://platform.example/post/123",
        "policy_acknowledgement_artifact_id": (
            "linkedin-policy-acknowledgement-artifact-123e4567-e89b-12d3-a456-426614174000"
        ),
        "rollback_or_postcondition_artifact_id": (
            "linkedin-rollback-postcondition-artifact-123e4567-e89b-12d3-a456-426614174000"
        ),
        "post_capture_validation_results": {},
        "secret_redaction_check": "passed",
        "debug": "hf_secret_proof_plan_test_must_not_echo",
    }

    payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
        ),
        record,
    )
    serialized = json.dumps(payload)

    assert payload["status"] == "invalid_record"
    assert payload["state_change_allowed"] is False
    assert "missing_validation_results" in payload["issue_codes"]
    assert "token_shaped_value_detected" in payload["issue_codes"]
    assert "hf_secret_proof_plan_test_must_not_echo" not in serialized


def test_provider_proof_record_validation_accepts_matching_preflight_validation_report(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    _write_product_run_preflight(preflight_dir)
    (preflight_dir / "provider-readiness.preflight.json").write_text(
        json.dumps(_ready_provider_readiness_preflight_payload()),
        encoding="utf-8",
    )
    (preflight_dir / "voice-runtime-readiness.preflight.json").write_text(
        json.dumps(_ready_voice_runtime_preflight_payload()),
        encoding="utf-8",
    )
    preflight_report = (
        provider_cli._provider_proof_preflight_artifacts_validation_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof="provider-backed-live-voice-proof",
                preflight_dir=preflight_dir,
            )
        )
    )
    preflight_report_path = tmp_path / "preflight-validation.json"
    preflight_report_path.write_text(
        json.dumps(preflight_report),
        encoding="utf-8",
    )
    record = _accepted_provider_proof_record(
        env_example,
        "provider-backed-live-voice-proof",
    )
    record.update(preflight_report["preflight_artifact_ids"])
    record["preflight_validation_report_artifact_id"] = str(
        preflight_report_path
    )

    payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            preflight_validation_path=preflight_report_path,
        ),
        record,
    )

    assert payload["status"] == "valid_accepted_record"
    assert payload["state_change_allowed"] is True
    assert payload["preflight_validation_report"] == {
        "status": "valid_preflight_artifacts",
        "path": str(preflight_report_path),
        "matched_fields": [
            "product_run_preflight_artifact_id",
            "provider_readiness_preflight_artifact_id",
            "voice_runtime_readiness_preflight_artifact_id",
        ],
        "validated_runtime_checks": list(
            provider_cli.VOICE_PROOF_REQUIRED_RUNTIME_CHECKS
        ),
        "validated_product_run_id": PROVIDER_PROOF_TEST_RUN_UUID,
    }


def test_provider_proof_record_validation_rejects_live_voice_runtime_check_missing_from_preflight_report(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    _write_product_run_preflight(preflight_dir)
    (preflight_dir / "provider-readiness.preflight.json").write_text(
        json.dumps(_ready_provider_readiness_preflight_payload()),
        encoding="utf-8",
    )
    (preflight_dir / "voice-runtime-readiness.preflight.json").write_text(
        json.dumps(_ready_voice_runtime_preflight_payload()),
        encoding="utf-8",
    )
    preflight_report = (
        provider_cli._provider_proof_preflight_artifacts_validation_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof="provider-backed-live-voice-proof",
                preflight_dir=preflight_dir,
            )
        )
    )
    preflight_report["validated_runtime_checks"] = [
        check
        for check in provider_cli.VOICE_PROOF_REQUIRED_RUNTIME_CHECKS
        if check != "rust-voice-edge"
    ]
    preflight_report_path = tmp_path / "preflight-validation.json"
    preflight_report_path.write_text(
        json.dumps(preflight_report),
        encoding="utf-8",
    )
    record = _accepted_provider_proof_record(
        env_example,
        "provider-backed-live-voice-proof",
    )
    record.update(preflight_report["preflight_artifact_ids"])
    record["preflight_validation_report_artifact_id"] = str(
        preflight_report_path
    )

    payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            preflight_validation_path=preflight_report_path,
        ),
        record,
    )

    assert payload["status"] == "invalid_record"
    assert payload["state_change_allowed"] is False
    assert "runtime_check_missing_from_preflight" in payload["issue_codes"]


def test_provider_proof_record_validation_rejects_live_voice_noncanonical_runtime_checks_from_preflight_report(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    _write_product_run_preflight(preflight_dir)
    (preflight_dir / "provider-readiness.preflight.json").write_text(
        json.dumps(_ready_provider_readiness_preflight_payload()),
        encoding="utf-8",
    )
    (preflight_dir / "voice-runtime-readiness.preflight.json").write_text(
        json.dumps(_ready_voice_runtime_preflight_payload()),
        encoding="utf-8",
    )
    preflight_report = (
        provider_cli._provider_proof_preflight_artifacts_validation_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof="provider-backed-live-voice-proof",
                preflight_dir=preflight_dir,
            )
        )
    )
    preflight_report["validated_runtime_checks"] = [
        *provider_cli.VOICE_PROOF_REQUIRED_RUNTIME_CHECKS,
        "local-rehearsal-only",
    ]
    preflight_report_path = tmp_path / "preflight-validation.json"
    preflight_report_path.write_text(
        json.dumps(preflight_report),
        encoding="utf-8",
    )
    record = _accepted_provider_proof_record(
        env_example,
        "provider-backed-live-voice-proof",
    )
    record.update(preflight_report["preflight_artifact_ids"])
    record["preflight_validation_report_artifact_id"] = str(
        preflight_report_path
    )

    payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            preflight_validation_path=preflight_report_path,
        ),
        record,
    )

    assert payload["status"] == "invalid_record"
    assert payload["state_change_allowed"] is False
    assert "preflight_validation_report_runtime_checks_not_canonical" in payload[
        "issue_codes"
    ]


def test_provider_proof_record_validation_accepts_matching_workspace_validation_report(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    workspace_report_path = _write_valid_workspace_validation_report(env_example)
    record = _accepted_provider_proof_record(
        env_example,
        "provider-backed-live-voice-proof",
    )
    record["workspace_validation_report_artifact_id"] = str(
        workspace_report_path
    )

    payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            workspace_validation_path=workspace_report_path,
        ),
        record,
    )

    assert payload["status"] == "valid_accepted_record"
    assert payload["state_change_allowed"] is True
    assert payload["workspace_validation_report"] == {
        "status": "valid_workspace",
        "path": str(workspace_report_path),
        "matched_fields": [
            "provider-backed-live-voice-proof.template.json",
            "README.md",
        ],
    }


def test_provider_proof_record_validation_requires_report_for_accepted_record(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    record = _accepted_provider_proof_record(
        env_example,
        "external-publication-proof",
    )
    record["preflight_validation_report_artifact_id"] = "<artifact-id>"

    payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
        ),
        record,
    )

    assert payload["status"] == "invalid_record"
    assert payload["state_change_allowed"] is False
    assert "preflight_validation_report_required" in payload["issue_codes"]


def test_provider_proof_record_validation_rejects_unreadable_preflight_report_path(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    report_path = tmp_path / "preflight-validation.json"
    report_path.mkdir()
    record = _accepted_provider_proof_record(
        env_example,
        "provider-backed-live-voice-proof",
    )
    record["preflight_validation_report_artifact_id"] = str(report_path)

    payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            preflight_validation_path=report_path,
        ),
        record,
    )

    assert payload["status"] == "invalid_record"
    assert payload["state_change_allowed"] is False
    assert "preflight_validation_report_unreadable" in payload["issue_codes"]
    assert payload["preflight_validation_report"]["status"] == (
        "invalid_preflight_report_linkage"
    )


def test_provider_proof_record_validation_requires_workspace_report_for_accepted_record(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    record = _accepted_provider_proof_record(
        env_example,
        "external-publication-proof",
    )
    record["workspace_validation_report_artifact_id"] = "<artifact-id>"

    payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
        ),
        record,
    )

    assert payload["status"] == "invalid_record"
    assert payload["state_change_allowed"] is False
    assert "workspace_validation_report_required" in payload["issue_codes"]


def test_provider_proof_record_validation_rejects_unreadable_workspace_report_path(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    report_path = tmp_path / "workspace-validation.json"
    report_path.mkdir()
    record = _accepted_provider_proof_record(
        env_example,
        "provider-backed-live-voice-proof",
    )
    record["workspace_validation_report_artifact_id"] = str(report_path)

    payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            workspace_validation_path=report_path,
        ),
        record,
    )

    assert payload["status"] == "invalid_record"
    assert payload["state_change_allowed"] is False
    assert "workspace_validation_report_unreadable" in payload["issue_codes"]
    assert payload["workspace_validation_report"]["status"] == (
        "invalid_workspace_validation_report_linkage"
    )


def test_provider_proof_record_validation_rejects_mismatched_preflight_report_ids(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    preflight_dir = tmp_path / "proof workspace"
    preflight_dir.mkdir()
    (preflight_dir / "publish-readiness.preflight.json").write_text(
        json.dumps({"status": "ready"}),
        encoding="utf-8",
    )
    preflight_report = (
        provider_cli._provider_proof_preflight_artifacts_validation_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof="external-publication-proof",
                preflight_dir=preflight_dir,
            )
        )
    )
    preflight_report_path = tmp_path / "preflight-validation.json"
    preflight_report_path.write_text(
        json.dumps(preflight_report),
        encoding="utf-8",
    )
    record = _accepted_provider_proof_record(
        env_example,
        "external-publication-proof",
    )
    record["publish_readiness_preflight_artifact_id"] = "wrong-preflight-id"
    record["preflight_validation_report_artifact_id"] = str(
        preflight_report_path
    )

    payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
            preflight_validation_path=preflight_report_path,
        ),
        record,
    )

    assert payload["status"] == "invalid_record"
    assert payload["state_change_allowed"] is False
    assert "preflight_artifact_id_mismatch" in payload["issue_codes"]
    assert payload["preflight_validation_report"] == {
        "status": "invalid_preflight_report_linkage",
        "path": str(preflight_report_path),
        "matched_fields": [],
    }


def test_provider_proof_record_validation_rejects_publication_destination_channel_missing_from_preflight(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    record = _accepted_provider_proof_record(
        env_example,
        "external-publication-proof",
    )
    record["destination_channel"] = "x_thread"
    record["durable_platform_id_or_url"] = "https://x.com/example/status/123"
    preflight_report_path = Path(record["preflight_validation_report_artifact_id"])
    preflight_report = json.loads(preflight_report_path.read_text(encoding="utf-8"))
    preflight_report["validated_publish_channels"] = ["linkedin"]
    preflight_report_path.write_text(
        json.dumps(preflight_report),
        encoding="utf-8",
    )

    payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
            preflight_validation_path=preflight_report_path,
        ),
        record,
    )

    assert payload["status"] == "invalid_record"
    assert payload["state_change_allowed"] is False
    assert "destination_channel_missing_from_preflight" in payload["issue_codes"]


@pytest.mark.parametrize(
    "validated_publish_channels",
    [
        ["linkedin", "mastodon"],
        ["linkedin", "linkedin"],
    ],
)
def test_provider_proof_record_validation_rejects_publication_noncanonical_publish_channels(
    tmp_path,
    validated_publish_channels,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    record = _accepted_provider_proof_record(
        env_example,
        "external-publication-proof",
    )
    preflight_report_path = Path(record["preflight_validation_report_artifact_id"])
    preflight_report = json.loads(preflight_report_path.read_text(encoding="utf-8"))
    preflight_report["validated_publish_channels"] = validated_publish_channels
    preflight_report_path.write_text(
        json.dumps(preflight_report),
        encoding="utf-8",
    )

    payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
            preflight_validation_path=preflight_report_path,
        ),
        record,
    )

    assert payload["status"] == "invalid_record"
    assert payload["state_change_allowed"] is False
    assert (
        "preflight_validation_report_publish_channels_not_canonical"
        in payload["issue_codes"]
    )


def test_provider_proof_record_validation_rejects_publication_alias_publish_channel_summary(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    record = _accepted_provider_proof_record(
        env_example,
        "external-publication-proof",
    )
    record["destination_channel"] = "x_thread"
    record["durable_platform_id_or_url"] = "https://x.com/example/status/123"
    preflight_report_path = Path(record["preflight_validation_report_artifact_id"])
    preflight_report = json.loads(preflight_report_path.read_text(encoding="utf-8"))
    preflight_report["validated_publish_channels"] = ["twitter"]
    preflight_report_path.write_text(
        json.dumps(preflight_report),
        encoding="utf-8",
    )

    payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
            preflight_validation_path=preflight_report_path,
        ),
        record,
    )

    assert payload["status"] == "invalid_record"
    assert payload["state_change_allowed"] is False
    assert (
        "preflight_validation_report_publish_channels_not_canonical"
        in payload["issue_codes"]
    )


def test_provider_proof_record_validation_rejects_accepted_publication_local_or_draft_destination(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    base_record = _accepted_provider_proof_record(
        env_example,
        "external-publication-proof",
    )
    local_destinations = [
        "file:///tmp/local-draft.html",
        "http://localhost:3000/preview/post",
        "http://192.168.1.10/post",
        "http://10.0.0.5/post",
        "http://0.0.0.0/post",
        "http://169.254.1.1/post",
        "http://intranet/post",
        "https://corp.internal/post",
        "https://service.lan/post",
        "https://staging.company.test/post",
        "https://reserved.example/post",
        "ftp://localhost/post",
        "ftp://192.168.1.10/post",
        "ssh://localhost/post",
        "javascript:alert(1)",
        "chrome://version",
        "mailto:user@example.com",
        "draft-artifact-123",
        "draft-post-123",
        "preview-post-123",
        "local-artifact-123",
        "internal-post-123",
        "https://linkedin.com/preview/post",
        "https://linkedin.com/draft/post",
        "urn:li:activity:",
        "urn:li:share:",
        "urn:li:ugcpost:",
        "~/post.html",
        "tmp/post.html",
        "C:/Users/me/post.html",
        "local-draft-preview-artifact",
    ]

    for destination in local_destinations:
        record = dict(base_record)
        record["durable_platform_id_or_url"] = destination

        payload = _provider_proof_record_validation_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof="external-publication-proof",
            ),
            record,
        )

        assert payload["status"] == "invalid_record"
        assert payload["state_change_allowed"] is False
        assert "durable_destination_not_external" in payload["issue_codes"]

    accepted_record = dict(base_record)
    accepted_record["durable_platform_id_or_url"] = "urn:li:share:123"
    accepted_payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
        ),
        accepted_record,
    )
    assert accepted_payload["status"] == "valid_accepted_record"

    accepted_activity_record = dict(base_record)
    accepted_activity_record["durable_platform_id_or_url"] = "urn:li:activity:123"
    accepted_activity_payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
        ),
        accepted_activity_record,
    )
    assert accepted_activity_payload["status"] == "valid_accepted_record"

    external_slug_record = dict(base_record)
    external_slug_record["durable_platform_id_or_url"] = (
        "https://linkedin.com/company/local-ai-lab/posts/internal-comms-launch-123"
    )
    external_slug_payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
        ),
        external_slug_record,
    )
    assert external_slug_payload["status"] == "valid_accepted_record"


def test_provider_proof_record_validation_rejects_accepted_publication_local_evidence_artifacts(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    base_record = _accepted_provider_proof_record(
        env_example,
        "external-publication-proof",
    )
    local_artifact_records = [
        {
            **base_record,
            "policy_acknowledgement_artifact_id": "policy",
        },
        {
            **base_record,
            "rollback_or_postcondition_artifact_id": "rollback",
        },
        {
            **base_record,
            "policy_acknowledgement_artifact_id": "draft-policy-note",
        },
        {
            **base_record,
            "rollback_or_postcondition_artifact_id": "./local-rollback.md",
        },
    ]

    for record in local_artifact_records:
        payload = _provider_proof_record_validation_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof="external-publication-proof",
            ),
            record,
        )

        assert payload["status"] == "invalid_record"
        assert payload["state_change_allowed"] is False
        assert "publication_artifact_local_substitute" in payload["issue_codes"]

    accepted_artifact_record = dict(base_record)
    accepted_artifact_record["policy_acknowledgement_artifact_id"] = (
        "compliance:linkedin-policy-acknowledgement-2026-05-24"
    )
    accepted_artifact_record["rollback_or_postcondition_artifact_id"] = (
        "urn:li:activity:123"
    )
    accepted_artifact_payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
        ),
        accepted_artifact_record,
    )
    assert accepted_artifact_payload["status"] == "valid_accepted_record"


def test_provider_proof_record_validation_rejects_accepted_publication_cross_channel_destination(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    base_record = _accepted_provider_proof_record(
        env_example,
        "external-publication-proof",
    )
    preflight_report_path = Path(base_record["preflight_validation_report_artifact_id"])
    preflight_report = json.loads(preflight_report_path.read_text(encoding="utf-8"))
    preflight_report["validated_publish_channels"] = [
        "linkedin",
        "instagram_post",
        "instagram_reel",
        "x_thread",
    ]
    preflight_report_path.write_text(
        json.dumps(preflight_report),
        encoding="utf-8",
    )

    mismatches = [
        ("linkedin", "https://instagram.com/p/abc123"),
        ("linkedin", "https://x.com/example/status/123"),
        ("linkedin", "https://newsletter.substack.com/p/post"),
        ("instagram", "https://linkedin.com/posts/123e4567-e89b-12d3-a456-426614174000"),
        ("x", "https://linkedin.com/posts/123e4567-e89b-12d3-a456-426614174000"),
    ]
    for channel, destination in mismatches:
        record = dict(base_record)
        record["destination_channel"] = channel
        record["durable_platform_id_or_url"] = destination

        payload = _provider_proof_record_validation_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof="external-publication-proof",
            ),
            record,
        )

        assert payload["status"] == "invalid_record"
        assert payload["state_change_allowed"] is False
        assert "destination_channel_mismatch" in payload["issue_codes"]

    linkedin_record_with_extra_preflight_channels = dict(base_record)
    linkedin_record_with_extra_preflight_channels["destination_channel"] = "linkedin"
    linkedin_record_with_extra_preflight_channels["durable_platform_id_or_url"] = (
        "https://linkedin.com/posts/123e4567-e89b-12d3-a456-426614174000"
    )
    linkedin_extra_preflight_payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
        ),
        linkedin_record_with_extra_preflight_channels,
    )
    assert linkedin_extra_preflight_payload["status"] == "invalid_record"
    assert linkedin_extra_preflight_payload["state_change_allowed"] is False
    assert (
        "preflight_validation_report_publish_channels_not_linkedin_only"
        in linkedin_extra_preflight_payload["issue_codes"]
    )

    non_linkedin_records = [
        ("instagram", "https://instagram.com/p/abc123"),
        ("instagram_post", "https://instagram.com/p/abc123"),
        ("instagram_reel", "https://instagram.com/reel/abc123"),
        ("x_thread", "https://x.com/example/status/123"),
    ]
    for channel, destination in non_linkedin_records:
        record = dict(base_record)
        record["destination_channel"] = channel
        record["durable_platform_id_or_url"] = destination
        payload = _provider_proof_record_validation_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof="external-publication-proof",
            ),
            record,
        )
        assert payload["status"] == "invalid_record"
        assert payload["state_change_allowed"] is False
        assert "destination_channel_not_linkedin" in payload["issue_codes"]


def test_provider_proof_record_validation_accepts_failed_record_without_all_passes(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    record = {
        "run_id": "123e4567-e89b-12d3-a456-426614174000",
        "checked_at": "2026-05-20",
        "validation_timestamp": "2026-05-20T12:00:00Z",
        "proof_outcome": "failed",
        "workspace_validation_report_artifact_id": "artifact-workspace-validation",
        "preflight_validation_report_artifact_id": "artifact-preflight-validation",
        "product_run_preflight_artifact_id": "artifact-product-run",
        "provider_readiness_preflight_artifact_id": "artifact-provider-preflight",
        "voice_runtime_readiness_preflight_artifact_id": "artifact-voice-preflight",
        "voice_agent_process_start_artifact_id": "artifact-voice-agent-start",
        "runtime_health_ledger_artifact_id": "artifact-runtime-health",
        "voice_edge_benchmark_status": "failed",
        "provider_smoke_ledger_artifact_id": "artifact-smoke",
        "livekit_voice_timing_capture_artifact_id": "artifact-livekit-capture",
        "realtime_voice_timing_ledger_artifact_id": "artifact-timing",
        "realtime_provider": "openrouter_livekit",
        "execute_live_calls": True,
        "realtime_session_id_or_livekit_room": "room-123",
        "participant_identity": "agent-voice",
        "runtime_configuration_snapshot_id": "runtime-snapshot",
        "post_capture_validation_results": {
            "provider_smoke_ledger execute_live_calls is true": "failed"
        },
        "secret_redaction_check": "passed",
    }

    payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
        ),
        record,
    )

    assert payload["status"] == "valid_failed_record"
    assert payload["state_change_allowed"] is False
    assert payload["issues"] == []


def test_provider_proof_record_validation_keeps_failed_record_with_missing_report_path(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    missing_report = tmp_path / "missing-preflight-validation.json"
    record = _failed_provider_proof_record(
        env_example,
        "provider-backed-live-voice-proof",
    )
    record["preflight_validation_report_artifact_id"] = str(missing_report)

    payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            preflight_validation_path=missing_report,
        ),
        record,
    )

    assert payload["status"] == "valid_failed_record"
    assert payload["state_change_allowed"] is False
    assert payload["issues"] == []
    assert "preflight_validation_report" not in payload


def test_provider_proof_record_validation_redacts_secret_shaped_keys(tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    record = {
        "run_id": "123e4567-e89b-12d3-a456-426614174000",
        "checked_at": "2026-05-20",
        "validation_timestamp": "2026-05-20T12:00:00Z",
        "proof_outcome": "failed",
        "workspace_validation_report_artifact_id": "artifact-workspace-validation",
        "preflight_validation_report_artifact_id": "artifact-preflight-validation",
        "product_run_preflight_artifact_id": "artifact-product-run",
        "provider_readiness_preflight_artifact_id": "artifact-provider-preflight",
        "voice_runtime_readiness_preflight_artifact_id": "artifact-voice-preflight",
        "voice_agent_process_start_artifact_id": "artifact-voice-agent-start",
        "runtime_health_ledger_artifact_id": "artifact-runtime-health",
        "voice_edge_benchmark_status": "failed",
        "provider_smoke_ledger_artifact_id": "artifact-smoke",
        "livekit_voice_timing_capture_artifact_id": "artifact-livekit-capture",
        "realtime_voice_timing_ledger_artifact_id": "artifact-timing",
        "realtime_provider": "openrouter_livekit",
        "execute_live_calls": True,
        "realtime_session_id_or_livekit_room": "room-123",
        "participant_identity": "agent-voice",
        "runtime_configuration_snapshot_id": "runtime-snapshot",
        "post_capture_validation_results": {
            "provider_smoke_ledger execute_live_calls is true": "failed"
        },
        "secret_redaction_check": "passed",
        "hf_secret_key_should_not_echo": "benign",
    }

    payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
        ),
        record,
    )
    serialized = json.dumps(payload)

    assert payload["status"] == "invalid_record"
    assert "token_shaped_value_detected" in payload["issue_codes"]
    assert "hf_secret_key_should_not_echo" not in serialized


def test_provider_proof_record_validation_rejects_non_object_json_without_leaks(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    record = ["hf_secret_non_object_test_must_not_echo"]

    payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
        ),
        record,
    )
    serialized = json.dumps(payload)

    assert payload["status"] == "invalid_record"
    assert payload["state_change_allowed"] is False
    assert "record_must_be_object" in payload["issue_codes"]
    assert "token_shaped_value_detected" in payload["issue_codes"]
    assert "hf_secret_non_object_test_must_not_echo" not in serialized


def test_provider_proof_record_validation_cli_rejects_unreadable_record_path(
    tmp_path,
    capsys,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    record_path = tmp_path / "provider-proof-record.json"
    record_path.mkdir()

    provider_cli._print_provider_proof_record_validation(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            record_path=record_path,
        )
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["artifact"] == "agent-studio-provider-proof-record-validation"
    assert payload["status"] == "invalid_record"
    assert payload["state_change_allowed"] is False
    assert payload["issue_codes"] == ["record_path_unreadable"]


def test_record_provider_proof_record_cli_rejects_unreadable_record_path_without_write(
    tmp_path,
    capsys,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    record_path = tmp_path / "provider-proof-record.json"
    record_path.mkdir()
    audit_target = tmp_path / "audit.md"

    provider_cli._print_record_provider_proof_record(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            record_path=record_path,
            audit_target=[audit_target],
        )
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["artifact"] == "agent-studio-provider-proof-record-audit"
    assert payload["status"] == "invalid_record"
    assert payload["validation_issue_codes"] == ["record_path_unreadable"]
    assert payload["audit_recorded"] is False
    assert payload["state_change_allowed"] is False
    assert payload["written_targets"] == []
    assert not audit_target.exists()


@pytest.mark.parametrize(
    ("case", "issue_code"),
    [
        ("missing", "record_path_missing"),
        ("not_utf8", "record_path_not_utf8"),
        ("invalid_json", "record_path_invalid_json"),
    ],
)
def test_provider_proof_record_cli_rejects_bad_record_path_inputs_without_leaks(
    tmp_path,
    capsys,
    case,
    issue_code,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    record_path = tmp_path / f"{case}-provider-proof-record.json"
    secret_value = "hf_secret_bad_record_path_must_not_echo"
    if case == "not_utf8":
        record_path.write_bytes(b"\xff\xfe\x00")
    elif case == "invalid_json":
        record_path.write_text(
            "{not-json: " + secret_value,
            encoding="utf-8",
        )
    audit_target = tmp_path / f"{case}-audit.md"

    provider_cli._print_provider_proof_record_validation(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            record_path=record_path,
        )
    )
    validation_payload = json.loads(capsys.readouterr().out)
    validation_serialized = json.dumps(validation_payload)

    assert validation_payload["status"] == "invalid_record"
    assert validation_payload["state_change_allowed"] is False
    assert validation_payload["issue_codes"] == [issue_code]
    assert secret_value not in validation_serialized

    provider_cli._print_record_provider_proof_record(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            record_path=record_path,
            audit_target=[audit_target],
        )
    )
    audit_payload = json.loads(capsys.readouterr().out)
    audit_serialized = json.dumps(audit_payload)

    assert audit_payload["status"] == "invalid_record"
    assert audit_payload["validation_issue_codes"] == [issue_code]
    assert audit_payload["audit_recorded"] is False
    assert audit_payload["state_change_allowed"] is False
    assert audit_payload["written_targets"] == []
    assert not audit_target.exists()
    assert secret_value not in audit_serialized


def test_provider_proof_record_validation_rejects_placeholder_run_id_record(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    record = {
        "run_id": "<run-id>",
        "checked_at": "2026-05-20",
        "validation_timestamp": "2026-05-20T12:00:00Z",
        "proof_outcome": "accepted",
        "provider_smoke_ledger_artifact_id": "artifact-smoke",
        "livekit_voice_timing_capture_artifact_id": "artifact-livekit-capture",
        "realtime_voice_timing_ledger_artifact_id": "artifact-timing",
        "realtime_provider": "openrouter_livekit",
        "execute_live_calls": True,
        "realtime_session_id_or_livekit_room": "room-123",
        "participant_identity": "agent-voice",
        "runtime_configuration_snapshot_id": "runtime-snapshot",
        "post_capture_validation_results": {
            "provider_smoke_ledger execute_live_calls is true": "passed",
            "provider_smoke_ledger realtime_provider is openrouter_livekit": "passed",
            (
                "provider_smoke_ledger run_id equals "
                "realtime_voice_timing_ledger run_id and command_run_id"
            ): "passed",
            (
                "realtime_session_id or LiveKit room/session id matches across "
                "smoke, timing, and participant evidence"
            ): "passed",
            "first text or audio timing plus interruption evidence are present": "passed",
            (
                "captured proof artifacts contain no token, API key, or secret values"
            ): "passed",
        },
        "secret_redaction_check": "passed",
    }

    payload = _provider_proof_record_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="<run-id>",
            proof="provider-backed-live-voice-proof",
        ),
        record,
    )

    assert payload["status"] == "invalid_record"
    assert payload["state_change_allowed"] is False
    assert "run_id_not_concrete" in payload["issue_codes"]


def test_record_provider_proof_record_appends_redacted_valid_failed_record_to_targets(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    target_one = tmp_path / "project-audit.md"
    target_two = tmp_path / "nested" / "system-audit.md"
    record = {
        "run_id": "123e4567-e89b-12d3-a456-426614174000",
        "checked_at": "2026-05-20",
        "validation_timestamp": "2026-05-20T12:00:00Z",
        "proof_outcome": "failed",
        "workspace_validation_report_artifact_id": "artifact-workspace-validation",
        "preflight_validation_report_artifact_id": "artifact-preflight-validation",
        "product_run_preflight_artifact_id": "artifact-product-run",
        "provider_readiness_preflight_artifact_id": "artifact-provider-preflight",
        "voice_runtime_readiness_preflight_artifact_id": "artifact-voice-preflight",
        "voice_agent_process_start_artifact_id": "artifact-voice-agent-start",
        "runtime_health_ledger_artifact_id": "artifact-runtime-health",
        "voice_edge_benchmark_status": "failed",
        "provider_smoke_ledger_artifact_id": "artifact-smoke",
        "livekit_voice_timing_capture_artifact_id": "artifact-livekit-capture",
        "realtime_voice_timing_ledger_artifact_id": "artifact-timing",
        "realtime_provider": "openrouter_livekit",
        "execute_live_calls": True,
        "realtime_session_id_or_livekit_room": "room-123",
        "participant_identity": "agent-voice",
        "runtime_configuration_snapshot_id": "runtime-snapshot",
        "post_capture_validation_results": {
            "provider_smoke_ledger execute_live_calls is true": "failed"
        },
        "secret_redaction_check": "passed",
    }

    payload = _record_provider_proof_record_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            audit_target=[target_one, target_two],
        ),
        record,
    )
    serialized = json.dumps(payload)
    target_one_body = target_one.read_text(encoding="utf-8")
    target_two_body = target_two.read_text(encoding="utf-8")

    assert payload["artifact"] == "agent-studio-provider-proof-record-audit"
    assert payload["validation_status"] == "valid_failed_record"
    assert payload["audit_recorded"] is True
    assert payload["state_change_allowed"] is False
    assert payload["written_targets"] == [str(target_one), str(target_two)]
    assert target_one_body == target_two_body
    assert "## Provider Proof Record - provider-backed-live-voice-proof - 123e4567-e89b-12d3-a456-426614174000" in (
        target_one_body
    )
    assert "- proof_outcome: failed" in target_one_body
    assert "- state_change_allowed: false" in target_one_body
    assert "- provider_smoke_ledger_artifact_id: artifact-smoke" in target_one_body
    assert "- post_capture_validation_results: 1 recorded / 0 passed / 1 failed" in (
        target_one_body
    )
    assert "hf_secret" not in serialized
    assert "hf_secret" not in target_one_body


def test_record_provider_proof_record_redacts_token_shaped_written_target_paths(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    secret_segment = "sk-ABCDEFGHIJKLMNOPQRST"
    audit_dir = tmp_path / secret_segment
    audit_target = audit_dir / "project-audit.md"
    record = _failed_provider_proof_record(
        env_example,
        "provider-backed-live-voice-proof",
    )

    payload = _record_provider_proof_record_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            audit_target=[audit_target],
        ),
        record,
    )
    serialized = json.dumps(payload)

    assert payload["status"] == "audit_recorded"
    assert payload["written_targets"] == [
        provider_cli._provider_proof_output_path_text(audit_target)
    ]
    assert audit_target.exists()
    assert secret_segment not in serialized


def test_record_provider_proof_record_rejects_unwritable_audit_target_without_partial_write(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    target_one = tmp_path / "project-audit.md"
    target_two = tmp_path / "audit-directory"
    target_two.mkdir()
    record = _failed_provider_proof_record(
        env_example,
        "provider-backed-live-voice-proof",
    )

    payload = _record_provider_proof_record_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            audit_target=[target_one, target_two],
        ),
        record,
    )

    assert payload["artifact"] == "agent-studio-provider-proof-record-audit"
    assert payload["status"] == "audit_target_unwritable"
    assert payload["validation_status"] == "valid_failed_record"
    assert payload["audit_recorded"] is False
    assert payload["state_change_allowed"] is False
    assert payload["written_targets"] == []
    assert payload["audit_issue_codes"] == ["audit_target_unwritable"]
    assert not target_one.exists()


def test_record_provider_proof_record_rejects_nested_bad_audit_parent_without_partial_write(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    target_one = tmp_path / "project-audit.md"
    bad_parent = tmp_path / "not-a-directory"
    bad_parent.write_text("regular file")
    target_two = bad_parent / "nested" / "project-audit.md"
    record = _failed_provider_proof_record(
        env_example,
        "provider-backed-live-voice-proof",
    )

    payload = _record_provider_proof_record_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            audit_target=[target_one, target_two],
        ),
        record,
    )

    assert payload["artifact"] == "agent-studio-provider-proof-record-audit"
    assert payload["status"] == "audit_target_unwritable"
    assert payload["validation_status"] == "valid_failed_record"
    assert payload["audit_recorded"] is False
    assert payload["state_change_allowed"] is False
    assert payload["written_targets"] == []
    assert payload["audit_issue_codes"] == ["audit_target_unwritable"]
    assert not target_one.exists()


def test_record_provider_proof_record_rejects_non_utf8_audit_target_without_partial_write(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    target_one = tmp_path / "project-audit.md"
    target_two = tmp_path / "malformed-audit.md"
    target_two.write_bytes(b"\xff\xfe")
    record = _failed_provider_proof_record(
        env_example,
        "provider-backed-live-voice-proof",
    )

    payload = _record_provider_proof_record_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            audit_target=[target_one, target_two],
        ),
        record,
    )

    assert payload["artifact"] == "agent-studio-provider-proof-record-audit"
    assert payload["status"] == "audit_target_unwritable"
    assert payload["validation_status"] == "valid_failed_record"
    assert payload["audit_recorded"] is False
    assert payload["state_change_allowed"] is False
    assert payload["written_targets"] == []
    assert payload["audit_issue_codes"] == ["audit_target_unwritable"]
    assert not target_one.exists()


def test_record_provider_proof_record_refuses_unsafe_run_id_substitution(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    target = tmp_path / "project-audit.md"
    record = {
        "run_id": "<run-id>",
        "checked_at": "2026-05-20",
        "validation_timestamp": "2026-05-20T12:00:00Z",
        "proof_outcome": "failed",
        "provider_smoke_ledger_artifact_id": "artifact-smoke",
        "livekit_voice_timing_capture_artifact_id": "artifact-livekit-capture",
        "realtime_voice_timing_ledger_artifact_id": "artifact-timing",
        "realtime_provider": "openrouter_livekit",
        "execute_live_calls": True,
        "realtime_session_id_or_livekit_room": "room-123",
        "participant_identity": "agent-voice",
        "runtime_configuration_snapshot_id": "runtime-snapshot",
        "post_capture_validation_results": {
            "provider_smoke_ledger execute_live_calls is true": "failed"
        },
        "secret_redaction_check": "passed",
    }

    payload = _record_provider_proof_record_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000; echo injected",
            proof="provider-backed-live-voice-proof",
            audit_target=[target],
        ),
        record,
    )

    assert payload["status"] == "invalid_record"
    assert payload["audit_recorded"] is False
    assert payload["written_targets"] == []
    assert not target.exists()
    assert "run_id_not_concrete" in payload["validation_issue_codes"]


def test_record_provider_proof_record_refuses_invalid_record_and_does_not_write(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    target = tmp_path / "project-audit.md"
    record = ["hf_secret_record_audit_test_must_not_echo"]

    payload = _record_provider_proof_record_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            audit_target=[target],
        ),
        record,
    )
    serialized = json.dumps(payload)

    assert payload["status"] == "invalid_record"
    assert payload["audit_recorded"] is False
    assert payload["written_targets"] == []
    assert not target.exists()
    assert "record_must_be_object" in payload["validation_issue_codes"]
    assert "hf_secret_record_audit_test_must_not_echo" not in serialized


def test_provider_proof_completion_status_blocks_until_all_accepted_records_exist(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"
    missing_target = tmp_path / "missing-audit.md"
    accepted_voice = _accepted_provider_proof_record(
        env_example,
        "provider-backed-live-voice-proof",
    )
    failed_publication = dict(
        _accepted_provider_proof_record(env_example, "external-publication-proof")
    )
    failed_publication["proof_outcome"] = "failed"
    failed_publication["post_capture_validation_results"] = {
        next(iter(failed_publication["post_capture_validation_results"])): "failed"
    }

    _record_provider_proof_record_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            audit_target=[audit_target],
        ),
        accepted_voice,
    )
    _record_provider_proof_record_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
            audit_target=[audit_target],
        ),
        failed_publication,
    )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target, missing_target],
        )
    )
    serialized = json.dumps(payload)

    assert payload["artifact"] == "agent-studio-provider-proof-completion-status"
    assert payload["status"] == "blocked_by_latest_failed_proof_record"
    assert payload["all_required_proofs_accepted"] is False
    assert payload["accepted_proofs"] == ["provider-backed-live-voice-proof"]
    assert payload["missing_accepted_proofs"] == []
    assert payload["latest_failed_proofs"] == ["external-publication-proof"]
    assert payload["missing_audit_targets"] == [str(missing_target)]
    assert payload["proofs"]["provider-backed-live-voice-proof"]["status"] == (
        "accepted_record_found"
    )
    assert payload["proofs"]["external-publication-proof"]["status"] == (
        "latest_record_failed"
    )
    publication_commands = payload["proofs"]["external-publication-proof"][
        "next_action_commands"
    ]
    assert all(
        "--proof provider-backed-live-voice-proof" not in command
        for command in publication_commands
    )
    assert any(
        "/publish-readiness" in command and "publish-readiness.preflight.json" in command
        for command in publication_commands
    )
    per_proof_distribution_command_index = next(
        index
        for index, command in enumerate(publication_commands)
        if "build-distribution-package" in command
        and "distribution-package.json" in command
    )
    per_proof_template_index = next(
        index
        for index, command in enumerate(publication_commands)
        if "provider-proof-record-template --proof external-publication-proof"
        in command
    )
    assert per_proof_distribution_command_index < per_proof_template_index
    top_level_commands = payload["next_action_commands"]
    assert all(
        "--proof provider-backed-live-voice-proof" not in command
        for command in top_level_commands
    )
    assert any(
        "provider-proof-record-template --proof external-publication-proof" in command
        for command in top_level_commands
    )
    assert any(
        "/publish-readiness" in command and "publish-readiness.preflight.json" in command
        for command in top_level_commands
    )
    distribution_command_index = next(
        index
        for index, command in enumerate(top_level_commands)
        if "build-distribution-package" in command
        and "distribution-package.json" in command
    )
    publication_template_index = next(
        index
        for index, command in enumerate(top_level_commands)
        if "provider-proof-record-template --proof external-publication-proof"
        in command
    )
    assert distribution_command_index < publication_template_index
    assert top_level_commands[-1] == (
        "uv run all-about-llms-admin provider-proof-completion-status "
        "--run-id 123e4567-e89b-12d3-a456-426614174000"
    )
    assert "hf_secret" not in serialized


def test_provider_proof_completion_status_gates_failed_publication_on_operator_inputs(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    output_dir = tmp_path / "provider-proof" / PROVIDER_PROOF_TEST_RUN_UUID
    output_dir.mkdir(parents=True)
    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    for filename in [
        "openrouter_api_key",
        "livekit_api_key",
        "livekit_api_secret",
    ]:
        (secrets_dir / filename).write_text("test-secret-value", encoding="utf-8")
    input_path = output_dir / "operator-inputs.template.env"
    input_path.write_text(
        "\n".join(
            [
                f"OPENROUTER_API_KEY_FILE={secrets_dir / 'openrouter_api_key'}",
                "OPENROUTER_LIVEKIT_URL=wss://livekit.example.test",
                f"LIVEKIT_API_KEY_FILE={secrets_dir / 'livekit_api_key'}",
                f"LIVEKIT_API_SECRET_FILE={secrets_dir / 'livekit_api_secret'}",
                f"LINKEDIN_ACCESS_TOKEN_FILE={secrets_dir / 'missing_linkedin'}",
                "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID=<artifact-id>",
                "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL=<external-url-or-id>",
                "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID=<artifact-id>",
                "",
            ]
        ),
        encoding="utf-8",
    )
    readiness = provider_cli._provider_proof_operator_input_readiness_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            input_path=input_path,
        )
    )
    assert readiness["proofs"]["external-publication-proof"]["state"] == (
        "blocked_by_operator_inputs"
    )
    (output_dir / "operator-input-readiness.json").write_text(
        json.dumps(readiness),
        encoding="utf-8",
    )
    audit_target = tmp_path / "objective-audit.md"
    accepted_voice = _accepted_provider_proof_record(
        env_example,
        "provider-backed-live-voice-proof",
    )
    failed_publication = dict(
        _accepted_provider_proof_record(env_example, "external-publication-proof")
    )
    failed_publication["proof_outcome"] = "failed"
    failed_publication["post_capture_validation_results"] = {
        next(iter(failed_publication["post_capture_validation_results"])): "failed"
    }

    _record_provider_proof_record_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            proof="provider-backed-live-voice-proof",
            audit_target=[audit_target],
        ),
        accepted_voice,
    )
    _record_provider_proof_record_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            proof="external-publication-proof",
            audit_target=[audit_target],
        ),
        failed_publication,
    )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            audit_target=[audit_target],
            output_dir=output_dir,
        )
    )

    publication_commands = payload["proofs"]["external-publication-proof"][
        "next_action_commands"
    ]
    assert "provider-proof-operator-input-readiness" in publication_commands[0]
    assert "--fail-on-blocked" in publication_commands[0]
    assert any("blocker-credential-snapshot" in command for command in publication_commands)
    assert all("/publish-readiness" not in command for command in publication_commands)
    top_level_commands = payload["next_action_commands"]
    assert "provider-proof-operator-input-readiness" in top_level_commands[0]
    assert "--fail-on-blocked" in top_level_commands[0]
    assert all("/publish-readiness" not in command for command in top_level_commands)


def test_provider_proof_completion_status_cli_accepts_custom_output_dir(
    tmp_path,
    monkeypatch,
    capsys,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    output_dir = tmp_path / "custom-provider-proof" / PROVIDER_PROOF_TEST_RUN_UUID
    output_dir.mkdir(parents=True)
    input_path = output_dir / "operator-inputs.template.env"
    input_path.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY_FILE=.secrets/openrouter_api_key",
                "OPENROUTER_LIVEKIT_URL=wss://livekit.example.test",
                "LIVEKIT_API_KEY_FILE=.secrets/livekit_api_key",
                "LIVEKIT_API_SECRET_FILE=.secrets/livekit_api_secret",
                "LINKEDIN_ACCESS_TOKEN_FILE=.secrets/missing_linkedin",
                "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID=<artifact-id>",
                "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL=<external-url-or-id>",
                "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID=<artifact-id>",
                "",
            ]
        ),
        encoding="utf-8",
    )
    readiness = provider_cli._provider_proof_operator_input_readiness_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            input_path=input_path,
        )
    )
    (output_dir / "operator-input-readiness.json").write_text(
        json.dumps(readiness),
        encoding="utf-8",
    )
    audit_target = tmp_path / "objective-audit.md"
    accepted_voice = _accepted_provider_proof_record(
        env_example,
        "provider-backed-live-voice-proof",
    )
    failed_publication = dict(
        _accepted_provider_proof_record(env_example, "external-publication-proof")
    )
    failed_publication["proof_outcome"] = "failed"
    failed_publication["post_capture_validation_results"] = {
        next(iter(failed_publication["post_capture_validation_results"])): "failed"
    }
    _record_provider_proof_record_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            proof="provider-backed-live-voice-proof",
            audit_target=[audit_target],
        ),
        accepted_voice,
    )
    _record_provider_proof_record_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id=PROVIDER_PROOF_TEST_RUN_UUID,
            proof="external-publication-proof",
            audit_target=[audit_target],
        ),
        failed_publication,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "all-about-llms-admin",
            "provider-proof-completion-status",
            "--env-example-path",
            str(env_example),
            "--checked-at",
            "2026-05-20",
            "--run-id",
            PROVIDER_PROOF_TEST_RUN_UUID,
            "--output-dir",
            str(output_dir),
            "--audit-target",
            str(audit_target),
        ],
    )

    provider_cli.main()
    payload = json.loads(capsys.readouterr().out)

    assert payload["next_action_commands"][0].startswith(
        "uv run all-about-llms-admin provider-proof-operator-input-readiness "
    )
    assert "--fail-on-blocked" in payload["next_action_commands"][0]
    assert str(input_path) in payload["next_action_commands"][0]
    assert "--output-dir" in payload["next_action_commands"][-1]
    assert str(output_dir) in payload["next_action_commands"][-1]
    assert all(
        "/publish-readiness" not in command
        for command in payload["next_action_commands"]
    )

    publication_commands = payload["proofs"]["external-publication-proof"][
        "next_action_commands"
    ]
    assert "--output-dir" in publication_commands[-1]
    assert str(output_dir) in publication_commands[-1]


def test_current_packets_do_not_reopen_accepted_live_voice_completion_commands(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    output_dir = tmp_path / "provider-proof" / "123e4567-e89b-12d3-a456-426614174000"
    output_dir.mkdir(parents=True)
    audit_target = tmp_path / "objective-audit.md"
    accepted_voice = _accepted_provider_proof_record(
        env_example,
        "provider-backed-live-voice-proof",
    )
    failed_publication = dict(
        _accepted_provider_proof_record(env_example, "external-publication-proof")
    )
    failed_publication["proof_outcome"] = "failed"
    failed_publication["post_capture_validation_results"] = {
        next(iter(failed_publication["post_capture_validation_results"])): "failed"
    }

    _record_provider_proof_record_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            audit_target=[audit_target],
        ),
        accepted_voice,
    )
    _record_provider_proof_record_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
            audit_target=[audit_target],
        ),
        failed_publication,
    )
    completion_payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )
    (output_dir / "completion-status.json").write_text(
        json.dumps(completion_payload),
        encoding="utf-8",
    )

    current_args = Namespace(
        env_example_path=env_example,
        checked_at="2026-05-20",
        run_id="123e4567-e89b-12d3-a456-426614174000",
        output_dir=output_dir,
        audit_target=None,
        proof_audit_target=None,
        closure_review_audit_target=None,
        blocker_update_audit_target=None,
    )
    matrix = provider_cli._provider_proof_current_blocker_matrix_payload(
        current_args,
        env_values={},
    )
    current_status = provider_cli._provider_proof_current_status_markdown(
        current_args,
        env_values={},
    )
    operator_checklist = (
        provider_cli._provider_proof_operator_unblocker_checklist_markdown(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                output_dir=output_dir,
            ),
            env_values={},
        )
    )

    assert matrix["completion"]["latest_failed_proofs"] == [
        "external-publication-proof"
    ]
    completion_commands = matrix["completion"]["next_action_commands"]
    assert all(
        "--proof provider-backed-live-voice-proof" not in command
        for command in completion_commands
    )
    assert any(
        "--proof external-publication-proof" in command
        for command in completion_commands
    )
    distribution_command_index = next(
        index
        for index, command in enumerate(completion_commands)
        if "build-distribution-package" in command
        and "distribution-package.json" in command
    )
    publication_template_index = next(
        index
        for index, command in enumerate(completion_commands)
        if "provider-proof-record-template --proof external-publication-proof"
        in command
    )
    assert distribution_command_index < publication_template_index
    assert completion_commands[-1] == (
        "uv run all-about-llms-admin provider-proof-completion-status "
        "--run-id 123e4567-e89b-12d3-a456-426614174000 "
        f"--output-dir {output_dir}"
    )
    voice = matrix["proofs"]["provider-backed-live-voice-proof"]
    publication = matrix["proofs"]["external-publication-proof"]
    assert voice["current_state"] == "accepted_proof_record_available"
    assert voice["latest_record_outcome"] == "accepted"
    assert voice["remaining_blockers"] == []
    assert publication["latest_record_outcome"] == "failed"

    for report in [current_status, operator_checklist]:
        current_gate_block = report.split("## Current Gate", 1)[1].split(
            "## Current State Packet Contract"
            if "## Current State Packet Contract" in report
            else "## Operator Input Template",
            1,
        )[0]
        completion_command_block = current_gate_block.split(
            "- completion next_action_commands:",
            1,
        )[1].split("- Required accepted proof state:", 1)[0]
        assert "--proof external-publication-proof" in completion_command_block
        assert "build-distribution-package" in completion_command_block
        assert "distribution-package.json" in completion_command_block
        assert completion_command_block.index(
            "build-distribution-package"
        ) < completion_command_block.index(
            "provider-proof-record-template --proof external-publication-proof"
        )
        assert (
            "--proof provider-backed-live-voice-proof"
            not in completion_command_block
        )


def test_provider_proof_completion_status_exposes_next_commands_for_missing_proofs(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"
    audit_target.write_text("# Empty audit target\n", encoding="utf-8")

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )

    assert payload["status"] == "blocked_by_missing_accepted_proof"
    voice = payload["proofs"]["provider-backed-live-voice-proof"]
    publication = payload["proofs"]["external-publication-proof"]
    assert voice["next_action"] == "capture_validate_record_and_recheck"
    assert publication["next_action"] == "capture_validate_record_and_recheck"
    expected_voice_preflight_report = (
        "social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000/"
        "provider-backed-live-voice-proof.preflight-validation.json"
    )
    expected_publication_preflight_report = (
        "social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000/"
        "external-publication-proof.preflight-validation.json"
    )
    expected_workspace_report = (
        "social_media_optimiser/output/provider-proof/123e4567-e89b-12d3-a456-426614174000/"
        "workspace-validation.json"
    )
    assert voice["next_action_commands"] == [
        (
            "uv run all-about-llms-admin provider-proof-record-template "
            "--proof provider-backed-live-voice-proof --run-id 123e4567-e89b-12d3-a456-426614174000"
        ),
        (
            "uv run all-about-llms-admin validate-provider-proof-record "
            "--proof provider-backed-live-voice-proof --run-id 123e4567-e89b-12d3-a456-426614174000 "
            "--record-path <provider-proof-record.json> "
            f"--preflight-validation-path {expected_voice_preflight_report} "
            f"--workspace-validation-path {expected_workspace_report}"
        ),
        (
            "uv run all-about-llms-admin record-provider-proof-record "
            "--proof provider-backed-live-voice-proof --run-id 123e4567-e89b-12d3-a456-426614174000 "
            "--record-path <provider-proof-record.json> "
            f"--preflight-validation-path {expected_voice_preflight_report} "
            f"--workspace-validation-path {expected_workspace_report}"
        ),
        (
            "uv run all-about-llms-admin provider-proof-completion-status "
            "--run-id 123e4567-e89b-12d3-a456-426614174000"
        ),
    ]
    assert publication["next_action_commands"][0] == (
        "uv run all-about-llms-admin provider-proof-record-template "
        "--proof external-publication-proof --run-id 123e4567-e89b-12d3-a456-426614174000"
    )
    assert publication["next_action_commands"][1:3] == [
        (
            "uv run all-about-llms-admin validate-provider-proof-record "
            "--proof external-publication-proof --run-id 123e4567-e89b-12d3-a456-426614174000 "
            "--record-path <provider-proof-record.json> "
            f"--preflight-validation-path {expected_publication_preflight_report} "
            f"--workspace-validation-path {expected_workspace_report}"
        ),
        (
            "uv run all-about-llms-admin record-provider-proof-record "
            "--proof external-publication-proof --run-id 123e4567-e89b-12d3-a456-426614174000 "
            "--record-path <provider-proof-record.json> "
            f"--preflight-validation-path {expected_publication_preflight_report} "
            f"--workspace-validation-path {expected_workspace_report}"
        ),
    ]
    top_level_commands = payload["next_action_commands"]
    assert top_level_commands == [
        *voice["next_action_commands"][:-1],
        *publication["next_action_commands"][:-1],
        (
            "uv run all-about-llms-admin provider-proof-completion-status "
            "--run-id 123e4567-e89b-12d3-a456-426614174000"
        ),
    ]
    assert top_level_commands.count(
        "uv run all-about-llms-admin provider-proof-completion-status "
        "--run-id 123e4567-e89b-12d3-a456-426614174000"
    ) == 1
    assert "<preflight-validation.json>" not in " ".join(
        voice["next_action_commands"] + publication["next_action_commands"]
    )
    assert "<workspace-validation.json>" not in " ".join(
        voice["next_action_commands"] + publication["next_action_commands"]
    )
    assert publication["record_proof_in"] == [
        (
            "social_media_optimiser/01-work-tracking/"
            "Agent Studio Objective Completion Audit.md"
        ),
        "social_media_optimiser/wiki/ops/active-codex-context.md",
        (
            "system_design_vault/04-agent-studio-implications/"
            "agent-studio-objective-completion-audit.md"
        ),
    ]


def test_provider_proof_completion_status_exposes_run_id_next_actions_without_unsafe_commands(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    secret_shaped_run_id = "sk-" + "ABCDEFGHIJKLMNOPQRST"

    placeholder_payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="<run-id>",
            audit_target=[],
        )
    )
    unsafe_payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000; echo injected",
            audit_target=[],
        )
    )
    secret_payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id=secret_shaped_run_id,
            audit_target=[],
        )
    )

    for payload in [placeholder_payload, unsafe_payload, secret_payload]:
        assert payload["status"] == "blocked_by_run_id"
        voice = payload["proofs"]["provider-backed-live-voice-proof"]
        publication = payload["proofs"]["external-publication-proof"]
        serialized_commands = json.dumps(
            voice["next_action_commands"] + publication["next_action_commands"]
        )
        assert voice["next_action"] == "replace_run_id_and_recheck"
        assert publication["next_action"] == "replace_run_id_and_recheck"
        assert voice["next_action_commands"][0] == (
            "uv run all-about-llms-admin provider-proof-record-template "
            "--proof provider-backed-live-voice-proof --run-id <run-id>"
        )
        assert publication["next_action_commands"][-1] == (
            "uv run all-about-llms-admin provider-proof-completion-status "
            "--run-id <run-id>"
        )
        assert voice["record_proof_in"]
        assert "123e4567-e89b-12d3-a456-426614174000; echo injected" not in serialized_commands
        assert "echo injected" not in serialized_commands

    serialized_secret_payload = json.dumps(secret_payload)
    assert secret_shaped_run_id not in serialized_secret_payload
    assert secret_payload["run_id"] == "<run-id>"


def test_provider_proof_completion_status_blocks_non_uuid_product_run_id_even_with_accepted_notes(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"
    audit_target.write_text(
        "\n".join(
            [
                "## Provider Proof Record - provider-backed-live-voice-proof - RUN-ID",
                "",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "",
                "## Provider Proof Record - external-publication-proof - RUN-ID",
                "",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="RUN-ID",
            audit_target=[audit_target],
        )
    )

    assert payload["status"] == "blocked_by_run_id"
    assert payload["product_run_id_state"] == "non_uuid_run_id"
    assert payload["issue_codes"] == ["run_id_not_product_uuid"]
    assert payload["all_required_proofs_accepted"] is False


def test_provider_proof_completion_status_accepts_all_required_records(tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"
    expected_review_command = (
        "uv run all-about-llms-admin "
        "provider-proof-closure-review-template --run-id 123e4567-e89b-12d3-a456-426614174000 "
        f"--audit-target {audit_target}"
    )

    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        _record_provider_proof_record_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof=proof,
                audit_target=[audit_target],
            ),
            _accepted_provider_proof_record(env_example, proof),
        )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )

    assert payload["status"] == "required_proofs_accepted"
    assert payload["required_proofs"] == [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]
    assert payload["state_change_boundary"] == {
        "command_changes_blocker_state": False,
        "status_only": True,
        "state_change_requires_external_update_after_review": True,
    }
    assert payload["blocker_state_change_allowed_by_this_command"] is False
    assert payload["completion_requirements"] == [
        "run_id is a durable product UUID",
        "each required proof has a latest accepted record",
        "accepted records are present in every configured readable audit target",
        "no configured audit target is missing or invalid",
        "completion status command changes no blocker state",
    ]
    assert payload["all_required_proofs_accepted"] is True
    assert payload["accepted_proofs"] == [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]
    assert payload["missing_accepted_proofs"] == []
    assert payload["next_action"] == "prepare_blocker_closure_review"
    assert payload["next_action_commands"] == [expected_review_command]
    assert payload["closure_review_packet"] == {
        "ready_for_review": True,
        "run_id": "123e4567-e89b-12d3-a456-426614174000",
        "review_required_before_state_change": True,
        "state_change_allowed_by_this_command": False,
        "required_proofs": [
            "provider-backed-live-voice-proof",
            "external-publication-proof",
        ],
        "accepted_record_sources": {
            "provider-backed-live-voice-proof": [str(audit_target)],
            "external-publication-proof": [str(audit_target)],
        },
        "template_commands": [expected_review_command],
        "state_update_candidates_after_review": [
            {
                "blocker": "provider-backed-live-voice-proof",
                "required_completion_status": "accepted_record_found",
                "candidate_state": "provider_proof_recorded_after_review",
            },
            {
                "blocker": "external-publication-proof",
                "required_completion_status": "accepted_record_found",
                "candidate_state": "provider_proof_recorded_after_review",
            },
        ],
        "review_requirements": [
            "confirm every required proof has accepted_record_found status",
            "confirm accepted proof records are present in every configured readable audit target",
            "confirm accepted proof records preserve required schema, validation summary, and redaction proof",
            "confirm no token-shaped values or secret material are present in audit notes",
            "confirm blocker-state notes are updated only after reviewer approval",
        ],
    }


def test_provider_proof_record_audit_note_normalizes_workspace_root_paths():
    run_id = "123e4567-e89b-12d3-a456-426614174000"
    workspace_report = (
        ROOT
        / "social_media_optimiser/output/provider-proof"
        / run_id
        / "workspace-validation.json"
    )
    preflight_report = (
        ROOT
        / "social_media_optimiser/output/provider-proof"
        / run_id
        / "provider-backed-live-voice-proof.preflight-validation.json"
    )
    validation = {
        "run_id": run_id,
        "checked_at": "2026-05-20",
        "proof": "provider-backed-live-voice-proof",
        "status": "valid_accepted_record",
        "state_change_allowed": True,
        "proof_artifact_schema": {
            "artifact_type": "provider_backed_live_voice_proof_record",
            "required_fields": [
                "workspace_validation_report_artifact_id",
                "preflight_validation_report_artifact_id",
            ],
        },
        "issues": [],
        "preflight_validation_report": {"status": "valid_preflight_artifacts"},
        "workspace_validation_report": {"status": "valid_workspace"},
    }
    record = {
        "run_id": run_id,
        "checked_at": "2026-05-20",
        "validation_timestamp": "2026-05-20T12:00:00Z",
        "proof_outcome": "accepted",
        "workspace_validation_report_artifact_id": str(workspace_report),
        "preflight_validation_report_artifact_id": str(preflight_report),
        "post_capture_validation_results": {},
        "secret_redaction_check": "passed",
    }

    audit_note = provider_cli._provider_proof_record_audit_note(validation, record)

    assert str(ROOT) not in audit_note
    assert (
        "- workspace_validation_report_artifact_id: "
        "<workspace-root>/social_media_optimiser/output/provider-proof/"
        f"{run_id}/workspace-validation.json"
    ) in audit_note
    assert (
        "- preflight_validation_report_artifact_id: "
        "<workspace-root>/social_media_optimiser/output/provider-proof/"
        f"{run_id}/provider-backed-live-voice-proof.preflight-validation.json"
    ) in audit_note


def test_provider_proof_completion_status_preserves_audit_target_overrides_in_closure_review_command(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective audit.md"

    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        _record_provider_proof_record_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof=proof,
                audit_target=[audit_target],
            ),
            _accepted_provider_proof_record(env_example, proof),
        )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )
    emitted_command = payload["next_action_commands"][0]
    template_payload = provider_cli._provider_proof_closure_review_template_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )

    assert payload["status"] == "required_proofs_accepted"
    assert emitted_command == (
        "uv run all-about-llms-admin "
        "provider-proof-closure-review-template --run-id 123e4567-e89b-12d3-a456-426614174000 "
        f"--audit-target {shlex.quote(str(audit_target))}"
    )
    assert payload["closure_review_packet"]["template_commands"] == [
        emitted_command
    ]
    assert template_payload["status"] == "template_ready"


def test_provider_proof_closure_review_template_requires_accepted_completion_status(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"
    audit_target.write_text("# Empty audit target\n", encoding="utf-8")

    payload = provider_cli._provider_proof_closure_review_template_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )

    assert payload["artifact"] == "agent-studio-provider-proof-closure-review-template"
    assert payload["boundary"] == "no_secret_values_printed_no_state_change"
    assert payload["status"] == "blocked_by_completion_status"
    assert payload["completion_status"] == "blocked_by_missing_accepted_proof"
    assert payload["template"] is None
    assert payload["state_change_allowed"] is False


def test_provider_proof_closure_review_template_builds_no_secret_review_record(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"

    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        _record_provider_proof_record_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof=proof,
                audit_target=[audit_target],
            ),
            _accepted_provider_proof_record(env_example, proof),
        )

    payload = provider_cli._provider_proof_closure_review_template_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )
    template = payload["template"]
    serialized = json.dumps(payload)

    assert payload["status"] == "template_ready"
    assert payload["completion_status"] == "required_proofs_accepted"
    assert payload["state_change_allowed"] is False
    assert payload["next_commands"] == [
        (
            "uv run all-about-llms-admin "
            "validate-provider-proof-closure-review --run-id 123e4567-e89b-12d3-a456-426614174000 "
            "--record-path <provider-proof-closure-review.json> "
            f"--audit-target {audit_target}"
        ),
        (
            "uv run all-about-llms-admin "
            "record-provider-proof-closure-review --run-id 123e4567-e89b-12d3-a456-426614174000 "
            "--record-path <provider-proof-closure-review.json> "
            f"--proof-audit-target {audit_target}"
        ),
    ]
    assert template == {
        "run_id": "123e4567-e89b-12d3-a456-426614174000",
        "review_timestamp": "<review-timestamp>",
        "reviewer": "<reviewer-or-agent-id>",
        "review_decision": "<approved-or-rejected>",
        "completion_status": "required_proofs_accepted",
        "accepted_proofs": [
            "provider-backed-live-voice-proof",
            "external-publication-proof",
        ],
        "accepted_record_sources": {
            "provider-backed-live-voice-proof": [str(audit_target)],
            "external-publication-proof": [str(audit_target)],
        },
        "review_requirements": {
            "confirm every required proof has accepted_record_found status": (
                "<confirmed-or-rejected>"
            ),
            (
                "confirm accepted proof records are present in every configured "
                "readable audit target"
            ): "<confirmed-or-rejected>",
            (
                "confirm accepted proof records preserve required schema, "
                "validation summary, and redaction proof"
            ): "<confirmed-or-rejected>",
            (
                "confirm no token-shaped values or secret material are present "
                "in audit notes"
            ): "<confirmed-or-rejected>",
            (
                "confirm blocker-state notes are updated only after reviewer "
                "approval"
            ): "<confirmed-or-rejected>",
        },
        "state_update_candidates_after_review": [
            {
                "blocker": "provider-backed-live-voice-proof",
                "required_completion_status": "accepted_record_found",
                "candidate_state": "provider_proof_recorded_after_review",
            },
            {
                "blocker": "external-publication-proof",
                "required_completion_status": "accepted_record_found",
                "candidate_state": "provider_proof_recorded_after_review",
            },
        ],
        "secret_redaction_check": "<passed-after-review>",
        "review_notes": "<no-secret-review-notes>",
    }
    assert "hf_secret" not in serialized


def test_provider_proof_closure_review_validation_accepts_approved_record(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"

    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        _record_provider_proof_record_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof=proof,
                audit_target=[audit_target],
            ),
            _accepted_provider_proof_record(env_example, proof),
        )

    template_payload = provider_cli._provider_proof_closure_review_template_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )
    record = dict(template_payload["template"])
    record["review_timestamp"] = "2026-05-20T13:00:00Z"
    record["reviewer"] = "Leibniz"
    record["review_decision"] = "approved"
    record["review_requirements"] = {
        requirement: "confirmed"
        for requirement in record["review_requirements"]
    }
    record["secret_redaction_check"] = "passed"
    record["review_notes"] = "reviewed without secret material"

    payload = provider_cli._provider_proof_closure_review_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        ),
        record,
    )

    assert payload["artifact"] == (
        "agent-studio-provider-proof-closure-review-validation"
    )
    assert payload["boundary"] == "no_secret_values_printed_no_state_change"
    assert payload["status"] == "valid_approved_closure_review"
    assert payload["completion_status"] == "required_proofs_accepted"
    assert payload["state_change_allowed"] is False
    assert payload["blocker_state_update_allowed_after_review"] is True
    assert payload["issue_codes"] == []
    assert payload["issues"] == []


@pytest.mark.parametrize(
    ("case", "issue_code"),
    [
        ("missing", "record_path_missing"),
        ("unreadable", "record_path_unreadable"),
        ("not_utf8", "record_path_not_utf8"),
        ("invalid_json", "record_path_invalid_json"),
    ],
)
def test_provider_proof_closure_review_cli_rejects_bad_record_path_inputs_without_leaks(
    tmp_path,
    capsys,
    case,
    issue_code,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    record_path = tmp_path / f"{case}-closure-review.json"
    secret_value = "hf_secret_bad_closure_review_path_must_not_echo"
    if case == "unreadable":
        record_path.mkdir()
    elif case == "not_utf8":
        record_path.write_bytes(b"\xff\xfe\x00")
    elif case == "invalid_json":
        record_path.write_text(
            "{not-json: " + secret_value,
            encoding="utf-8",
        )
    audit_target = tmp_path / f"{case}-closure-audit.md"

    provider_cli._print_provider_proof_closure_review_validation(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            record_path=record_path,
            audit_target=[audit_target],
        )
    )
    validation_payload = json.loads(capsys.readouterr().out)
    validation_serialized = json.dumps(validation_payload)

    assert validation_payload["artifact"] == (
        "agent-studio-provider-proof-closure-review-validation"
    )
    assert validation_payload["status"] == "invalid_closure_review"
    assert validation_payload["state_change_allowed"] is False
    assert validation_payload["blocker_state_update_allowed_after_review"] is False
    assert validation_payload["issue_codes"] == [issue_code]
    assert secret_value not in validation_serialized

    provider_cli._print_record_provider_proof_closure_review(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            record_path=record_path,
            proof_audit_target=[audit_target],
            audit_target=[audit_target],
        )
    )
    audit_payload = json.loads(capsys.readouterr().out)
    audit_serialized = json.dumps(audit_payload)

    assert audit_payload["artifact"] == (
        "agent-studio-provider-proof-closure-review-audit"
    )
    assert audit_payload["status"] == "invalid_closure_review"
    assert audit_payload["validation_issue_codes"] == [issue_code]
    assert audit_payload["audit_recorded"] is False
    assert audit_payload["state_change_allowed"] is False
    assert audit_payload["blocker_state_update_allowed_after_review"] is False
    assert audit_payload["written_targets"] == []
    assert not audit_target.exists()
    assert secret_value not in audit_serialized


def test_provider_proof_closure_review_validation_rejects_unconfirmed_requirement(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"

    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        _record_provider_proof_record_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof=proof,
                audit_target=[audit_target],
            ),
            _accepted_provider_proof_record(env_example, proof),
        )

    template_payload = provider_cli._provider_proof_closure_review_template_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )
    record = dict(template_payload["template"])
    first_requirement = next(iter(record["review_requirements"]))
    record["review_timestamp"] = "2026-05-20T13:00:00Z"
    record["reviewer"] = "Leibniz"
    record["review_decision"] = "approved"
    record["review_requirements"] = {
        requirement: "confirmed"
        for requirement in record["review_requirements"]
    }
    record["review_requirements"][first_requirement] = "rejected"
    record["secret_redaction_check"] = "passed"
    record["review_notes"] = "reviewed without secret material"

    payload = provider_cli._provider_proof_closure_review_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        ),
        record,
    )

    assert payload["status"] == "invalid_closure_review"
    assert payload["state_change_allowed"] is False
    assert payload["blocker_state_update_allowed_after_review"] is False
    assert "review_requirement_not_confirmed" in payload["issue_codes"]


def test_provider_proof_closure_review_validation_accepts_rejected_review_with_failed_requirement(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"

    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        _record_provider_proof_record_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof=proof,
                audit_target=[audit_target],
            ),
            _accepted_provider_proof_record(env_example, proof),
        )

    template_payload = provider_cli._provider_proof_closure_review_template_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )
    record = dict(template_payload["template"])
    first_requirement = next(iter(record["review_requirements"]))
    record["review_timestamp"] = "2026-05-20T13:00:00Z"
    record["reviewer"] = "Leibniz"
    record["review_decision"] = "rejected"
    record["review_requirements"] = {
        requirement: "confirmed"
        for requirement in record["review_requirements"]
    }
    record["review_requirements"][first_requirement] = "rejected"
    record["secret_redaction_check"] = "passed"
    record["review_notes"] = "closure rejected until review issue is resolved"

    payload = provider_cli._provider_proof_closure_review_validation_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        ),
        record,
    )

    assert payload["status"] == "valid_rejected_closure_review"
    assert payload["state_change_allowed"] is False
    assert payload["blocker_state_update_allowed_after_review"] is False
    assert payload["issue_codes"] == []


def test_record_provider_proof_closure_review_records_valid_review_without_state_change(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    proof_audit = tmp_path / "proof-audit.md"
    review_audit_one = tmp_path / "review-audit-one.md"
    review_audit_two = tmp_path / "review-audit-two.md"

    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        _record_provider_proof_record_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof=proof,
                audit_target=[proof_audit],
            ),
            _accepted_provider_proof_record(env_example, proof),
        )

    template_payload = provider_cli._provider_proof_closure_review_template_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[proof_audit],
        )
    )
    record = dict(template_payload["template"])
    record["review_timestamp"] = "2026-05-20T13:00:00Z"
    record["reviewer"] = "Leibniz"
    record["review_decision"] = "approved"
    record["review_requirements"] = {
        requirement: "confirmed"
        for requirement in record["review_requirements"]
    }
    record["secret_redaction_check"] = "passed"
    record["review_notes"] = "reviewed without secret material"

    payload = provider_cli._record_provider_proof_closure_review_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            record_path=None,
            proof_audit_target=[proof_audit],
            audit_target=[review_audit_one, review_audit_two],
        ),
        record,
    )
    target_one_body = review_audit_one.read_text(encoding="utf-8")
    target_two_body = review_audit_two.read_text(encoding="utf-8")

    assert payload["artifact"] == "agent-studio-provider-proof-closure-review-audit"
    assert payload["status"] == "audit_recorded"
    assert payload["validation_status"] == "valid_approved_closure_review"
    assert payload["audit_recorded"] is True
    assert payload["state_change_allowed"] is False
    assert payload["blocker_state_update_allowed_after_review"] is True
    assert payload["written_targets"] == [str(review_audit_one), str(review_audit_two)]
    assert target_one_body == target_two_body
    assert "## Provider Proof Closure Review - 123e4567-e89b-12d3-a456-426614174000" in target_one_body
    assert "- review_decision: approved" in target_one_body
    assert "- state_change_allowed: false" in target_one_body
    assert "- blocker_state_update_allowed_after_review: true" in target_one_body
    assert "- review_requirements: 5 recorded / 5 confirmed / 0 rejected" in (
        target_one_body
    )


def test_record_provider_proof_closure_review_redacts_token_shaped_written_target_paths(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    proof_audit = tmp_path / "proof-audit.md"
    secret_segment = "sk-ABCDEFGHIJKLMNOPQRST"
    review_audit_dir = tmp_path / secret_segment
    review_audit = review_audit_dir / "review-audit.md"

    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        _record_provider_proof_record_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof=proof,
                audit_target=[proof_audit],
            ),
            _accepted_provider_proof_record(env_example, proof),
        )

    template_payload = provider_cli._provider_proof_closure_review_template_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[proof_audit],
        )
    )
    record = dict(template_payload["template"])
    record["review_timestamp"] = "2026-05-20T13:00:00Z"
    record["reviewer"] = "Leibniz"
    record["review_decision"] = "approved"
    record["review_requirements"] = {
        requirement: "confirmed"
        for requirement in record["review_requirements"]
    }
    record["secret_redaction_check"] = "passed"
    record["review_notes"] = "reviewed without secret material"

    payload = provider_cli._record_provider_proof_closure_review_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            record_path=None,
            proof_audit_target=[proof_audit],
            audit_target=[review_audit],
        ),
        record,
    )
    serialized = json.dumps(payload)

    assert payload["status"] == "audit_recorded"
    assert payload["written_targets"] == [
        provider_cli._provider_proof_output_path_text(review_audit)
    ]
    assert review_audit.exists()
    assert secret_segment not in serialized


def test_record_provider_proof_closure_review_rejects_unwritable_audit_target_without_partial_write(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    proof_audit = tmp_path / "proof-audit.md"
    review_audit_one = tmp_path / "review-audit-one.md"
    review_audit_two = tmp_path / "review-audit-directory"
    review_audit_two.mkdir()

    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        _record_provider_proof_record_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof=proof,
                audit_target=[proof_audit],
            ),
            _accepted_provider_proof_record(env_example, proof),
        )

    template_payload = provider_cli._provider_proof_closure_review_template_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[proof_audit],
        )
    )
    record = dict(template_payload["template"])
    record["review_timestamp"] = "2026-05-20T13:00:00Z"
    record["reviewer"] = "Leibniz"
    record["review_decision"] = "approved"
    record["review_requirements"] = {
        requirement: "confirmed"
        for requirement in record["review_requirements"]
    }
    record["secret_redaction_check"] = "passed"
    record["review_notes"] = "reviewed without secret material"

    payload = provider_cli._record_provider_proof_closure_review_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            record_path=None,
            proof_audit_target=[proof_audit],
            audit_target=[review_audit_one, review_audit_two],
        ),
        record,
    )

    assert payload["artifact"] == "agent-studio-provider-proof-closure-review-audit"
    assert payload["status"] == "audit_target_unwritable"
    assert payload["validation_status"] == "valid_approved_closure_review"
    assert payload["audit_recorded"] is False
    assert payload["state_change_allowed"] is False
    assert payload["blocker_state_update_allowed_after_review"] is False
    assert payload["written_targets"] == []
    assert payload["audit_issue_codes"] == ["audit_target_unwritable"]
    assert not review_audit_one.exists()


def test_record_provider_proof_closure_review_rejects_nested_bad_audit_parent_without_partial_write(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    proof_audit = tmp_path / "proof-audit.md"
    review_audit_one = tmp_path / "review-audit-one.md"
    bad_parent = tmp_path / "not-a-directory"
    bad_parent.write_text("regular file")
    review_audit_two = bad_parent / "nested" / "review-audit.md"

    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        _record_provider_proof_record_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof=proof,
                audit_target=[proof_audit],
            ),
            _accepted_provider_proof_record(env_example, proof),
        )

    template_payload = provider_cli._provider_proof_closure_review_template_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[proof_audit],
        )
    )
    record = dict(template_payload["template"])
    record["review_timestamp"] = "2026-05-20T13:00:00Z"
    record["reviewer"] = "Leibniz"
    record["review_decision"] = "approved"
    record["review_requirements"] = {
        requirement: "confirmed"
        for requirement in record["review_requirements"]
    }
    record["secret_redaction_check"] = "passed"
    record["review_notes"] = "reviewed without secret material"

    payload = provider_cli._record_provider_proof_closure_review_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            record_path=None,
            proof_audit_target=[proof_audit],
            audit_target=[review_audit_one, review_audit_two],
        ),
        record,
    )

    assert payload["artifact"] == "agent-studio-provider-proof-closure-review-audit"
    assert payload["status"] == "audit_target_unwritable"
    assert payload["validation_status"] == "valid_approved_closure_review"
    assert payload["audit_recorded"] is False
    assert payload["state_change_allowed"] is False
    assert payload["blocker_state_update_allowed_after_review"] is False
    assert payload["written_targets"] == []
    assert payload["audit_issue_codes"] == ["audit_target_unwritable"]
    assert not review_audit_one.exists()


def test_record_provider_proof_closure_review_rejects_non_utf8_audit_target_without_partial_write(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    proof_audit = tmp_path / "proof-audit.md"
    review_audit_one = tmp_path / "review-audit-one.md"
    review_audit_two = tmp_path / "malformed-review-audit.md"
    review_audit_two.write_bytes(b"\xff\xfe")

    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        _record_provider_proof_record_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof=proof,
                audit_target=[proof_audit],
            ),
            _accepted_provider_proof_record(env_example, proof),
        )

    template_payload = provider_cli._provider_proof_closure_review_template_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[proof_audit],
        )
    )
    record = dict(template_payload["template"])
    record["review_timestamp"] = "2026-05-20T13:00:00Z"
    record["reviewer"] = "Leibniz"
    record["review_decision"] = "approved"
    record["review_requirements"] = {
        requirement: "confirmed"
        for requirement in record["review_requirements"]
    }
    record["secret_redaction_check"] = "passed"
    record["review_notes"] = "reviewed without secret material"

    payload = provider_cli._record_provider_proof_closure_review_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            record_path=None,
            proof_audit_target=[proof_audit],
            audit_target=[review_audit_one, review_audit_two],
        ),
        record,
    )

    assert payload["artifact"] == "agent-studio-provider-proof-closure-review-audit"
    assert payload["status"] == "audit_target_unwritable"
    assert payload["validation_status"] == "valid_approved_closure_review"
    assert payload["audit_recorded"] is False
    assert payload["state_change_allowed"] is False
    assert payload["blocker_state_update_allowed_after_review"] is False
    assert payload["written_targets"] == []
    assert payload["audit_issue_codes"] == ["audit_target_unwritable"]
    assert not review_audit_one.exists()


def test_record_provider_proof_closure_review_keeps_review_targets_separate_from_default_proof_audits(
    tmp_path,
    monkeypatch,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    proof_audit = tmp_path / "default-proof-audit.md"
    review_audit = tmp_path / "review-audit.md"
    monkeypatch.setattr(
        provider_cli,
        "PROVIDER_PROOF_RECORD_TARGETS",
        [str(proof_audit)],
    )

    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        _record_provider_proof_record_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof=proof,
                audit_target=[proof_audit],
            ),
            _accepted_provider_proof_record(env_example, proof),
        )

    template_payload = provider_cli._provider_proof_closure_review_template_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[proof_audit],
        )
    )
    record = dict(template_payload["template"])
    record["review_timestamp"] = "2026-05-20T13:00:00Z"
    record["reviewer"] = "Leibniz"
    record["review_decision"] = "approved"
    record["review_requirements"] = {
        requirement: "confirmed"
        for requirement in record["review_requirements"]
    }
    record["secret_redaction_check"] = "passed"
    record["review_notes"] = "reviewed without secret material"

    payload = provider_cli._record_provider_proof_closure_review_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            record_path=None,
            proof_audit_target=None,
            audit_target=[review_audit],
        ),
        record,
    )

    assert payload["status"] == "audit_recorded"
    assert payload["written_targets"] == [str(review_audit)]
    assert review_audit.exists()


def test_record_provider_proof_closure_review_refuses_invalid_review_without_writing(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    proof_audit = tmp_path / "proof-audit.md"
    review_audit = tmp_path / "review-audit.md"
    record = ["hf_secret_closure_review_must_not_echo"]

    payload = provider_cli._record_provider_proof_closure_review_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            record_path=None,
            proof_audit_target=[proof_audit],
            audit_target=[review_audit],
        ),
        record,
    )
    serialized = json.dumps(payload)

    assert payload["status"] == "invalid_closure_review"
    assert payload["audit_recorded"] is False
    assert payload["written_targets"] == []
    assert not review_audit.exists()
    assert "record_must_be_object" in payload["validation_issue_codes"]
    assert "hf_secret_closure_review_must_not_echo" not in serialized


def test_provider_proof_closure_review_status_reports_latest_approved_review_without_state_change(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    proof_audit = tmp_path / "proof-audit.md"
    review_audit = tmp_path / "review-audit.md"
    update_audit = tmp_path / "blocker update audit.md"

    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        _record_provider_proof_record_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof=proof,
                audit_target=[proof_audit],
            ),
            _accepted_provider_proof_record(env_example, proof),
        )

    provider_cli._record_provider_proof_closure_review_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            record_path=None,
            proof_audit_target=[proof_audit],
            audit_target=[review_audit],
        ),
        _closure_review_record(env_example, proof_audit),
    )

    payload = provider_cli._provider_proof_closure_review_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof_audit_target=[proof_audit],
            audit_target=[review_audit],
            blocker_update_audit_target=[update_audit],
        )
    )

    assert payload["artifact"] == "agent-studio-provider-proof-closure-review-status"
    assert payload["boundary"] == "no_secret_values_printed_no_state_change"
    assert payload["status"] == "closure_review_approved"
    assert payload["completion_status"] == "required_proofs_accepted"
    assert payload["audit_targets"] == [str(review_audit)]
    assert payload["proof_audit_targets"] == [str(proof_audit)]
    assert payload["state_change_allowed"] is False
    assert payload["blocker_state_update_allowed_after_review"] is True
    assert payload["issue_codes"] == []
    assert payload["next_action"] == "record_blocker_state_update"
    assert payload["next_action_commands"] == [
        (
            "uv run all-about-llms-admin "
            "record-provider-proof-blocker-state-update --run-id 123e4567-e89b-12d3-a456-426614174000 "
            f"--proof-audit-target {proof_audit} "
            f"--closure-review-audit-target {review_audit} "
            f"--audit-target {shlex.quote(str(update_audit))}"
        )
    ]
    assert payload["latest_closure_review"] == {
        "review_timestamp": "2026-05-20T13:00:00Z",
        "reviewer": "Leibniz",
        "review_decision": "approved",
        "validation_status": "valid_approved_closure_review",
        "source_targets": [str(review_audit)],
    }


def test_provider_proof_closure_review_status_blocks_rejected_review(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    proof_audit = tmp_path / "proof-audit.md"
    review_audit = tmp_path / "review-audit.md"

    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        _record_provider_proof_record_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof=proof,
                audit_target=[proof_audit],
            ),
            _accepted_provider_proof_record(env_example, proof),
        )

    provider_cli._record_provider_proof_closure_review_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            record_path=None,
            proof_audit_target=[proof_audit],
            audit_target=[review_audit],
        ),
        _closure_review_record(env_example, proof_audit, decision="rejected"),
    )

    payload = provider_cli._provider_proof_closure_review_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof_audit_target=[proof_audit],
            audit_target=[review_audit],
        )
    )

    assert payload["status"] == "blocked_by_rejected_closure_review"
    assert payload["state_change_allowed"] is False
    assert payload["blocker_state_update_allowed_after_review"] is False
    assert payload["issue_codes"] == ["latest_closure_review_rejected"]
    assert payload["latest_closure_review"]["review_decision"] == "rejected"
    assert payload["latest_closure_review"]["validation_status"] == (
        "valid_rejected_closure_review"
    )


def test_provider_proof_closure_review_status_reports_non_utf8_audit_target(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    proof_audit = tmp_path / "proof-audit.md"
    review_audit = tmp_path / "review-audit.md"
    secret_segment = "sk-ABCDEFGHIJKLMNOPQRST"
    malformed_review_dir = tmp_path / secret_segment
    malformed_review_dir.mkdir()
    malformed_review_audit = malformed_review_dir / "malformed-review-audit.md"
    malformed_review_audit.write_bytes(b"\xff\xfe")

    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        _record_provider_proof_record_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof=proof,
                audit_target=[proof_audit],
            ),
            _accepted_provider_proof_record(env_example, proof),
        )

    provider_cli._record_provider_proof_closure_review_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            record_path=None,
            proof_audit_target=[proof_audit],
            audit_target=[review_audit],
        ),
        _closure_review_record(env_example, proof_audit),
    )

    payload = provider_cli._provider_proof_closure_review_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof_audit_target=[proof_audit],
            audit_target=[review_audit, malformed_review_audit],
        )
    )

    assert payload["status"] == "blocked_by_invalid_closure_review_audit_target"
    assert payload["state_change_allowed"] is False
    assert payload["blocker_state_update_allowed_after_review"] is False
    assert payload["issue_codes"] == ["closure_review_audit_targets_invalid"]
    assert payload["approved_closure_review_targets"] == [str(review_audit)]
    assert payload["invalid_audit_targets"] == [
        provider_cli._provider_proof_output_path_text(malformed_review_audit)
    ]
    assert secret_segment not in json.dumps(payload)


def test_provider_proof_closure_review_status_rejects_review_with_wrong_proof_set(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    proof_audit = tmp_path / "proof-audit.md"
    review_audit = tmp_path / "review-audit.md"

    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        _record_provider_proof_record_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof=proof,
                audit_target=[proof_audit],
            ),
            _accepted_provider_proof_record(env_example, proof),
        )
    provider_cli._record_provider_proof_closure_review_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            record_path=None,
            proof_audit_target=[proof_audit],
            audit_target=[review_audit],
        ),
        _closure_review_record(env_example, proof_audit),
    )
    review_audit.write_text(
        review_audit.read_text(encoding="utf-8").replace(
            (
                '- accepted_proofs: ["provider-backed-live-voice-proof", '
                '"external-publication-proof"]'
            ),
            "- accepted_proofs: []",
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_closure_review_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof_audit_target=[proof_audit],
            audit_target=[review_audit],
        )
    )

    assert payload["status"] == "blocked_by_invalid_closure_review_audit_note"
    assert payload["blocker_state_update_allowed_after_review"] is False
    assert payload["issue_codes"] == ["closure_review_audit_note_invalid_fields"]
    assert payload["invalid_closure_review_targets"] == [str(review_audit)]


def test_provider_proof_closure_review_status_rejects_partial_requirement_summary(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    proof_audit = tmp_path / "proof-audit.md"
    review_audit = tmp_path / "review-audit.md"

    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        _record_provider_proof_record_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof=proof,
                audit_target=[proof_audit],
            ),
            _accepted_provider_proof_record(env_example, proof),
        )
    provider_cli._record_provider_proof_closure_review_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            record_path=None,
            proof_audit_target=[proof_audit],
            audit_target=[review_audit],
        ),
        _closure_review_record(env_example, proof_audit),
    )
    review_audit.write_text(
        review_audit.read_text(encoding="utf-8").replace(
            "- review_requirements: 5 recorded / 5 confirmed / 0 rejected",
            "- review_requirements: 1 recorded / 1 confirmed / 0 rejected",
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_closure_review_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof_audit_target=[proof_audit],
            audit_target=[review_audit],
        )
    )

    assert payload["status"] == "blocked_by_invalid_closure_review_audit_note"
    assert payload["blocker_state_update_allowed_after_review"] is False
    assert payload["issue_codes"] == ["closure_review_audit_note_invalid_fields"]
    assert payload["invalid_closure_review_targets"] == [str(review_audit)]


def test_provider_proof_closure_review_status_blocks_missing_review(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    proof_audit = tmp_path / "proof-audit.md"
    review_audit = tmp_path / "review-audit.md"

    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        _record_provider_proof_record_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof=proof,
                audit_target=[proof_audit],
            ),
            _accepted_provider_proof_record(env_example, proof),
        )
    review_audit.write_text("# no closure review yet\n", encoding="utf-8")

    payload = provider_cli._provider_proof_closure_review_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof_audit_target=[proof_audit],
            audit_target=[review_audit],
        )
    )

    assert payload["status"] == "blocked_by_missing_closure_review"
    assert payload["state_change_allowed"] is False
    assert payload["blocker_state_update_allowed_after_review"] is False
    assert payload["issue_codes"] == ["closure_review_missing"]
    assert payload["latest_closure_review"] is None


def test_record_provider_proof_blocker_state_update_records_only_after_approved_closure_review(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    proof_audit = tmp_path / "proof-audit.md"
    review_audit = tmp_path / "review-audit.md"
    update_audit = tmp_path / "blocker-update-audit.md"

    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        _record_provider_proof_record_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof=proof,
                audit_target=[proof_audit],
            ),
            _accepted_provider_proof_record(env_example, proof),
        )
    provider_cli._record_provider_proof_closure_review_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            record_path=None,
            proof_audit_target=[proof_audit],
            audit_target=[review_audit],
        ),
        _closure_review_record(env_example, proof_audit),
    )

    payload = provider_cli._record_provider_proof_blocker_state_update_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof_audit_target=[proof_audit],
            closure_review_audit_target=[review_audit],
            audit_target=[update_audit],
        )
    )
    body = update_audit.read_text(encoding="utf-8")

    assert payload["artifact"] == (
        "agent-studio-provider-proof-blocker-state-update-audit"
    )
    assert payload["status"] == "audit_recorded"
    assert payload["closure_review_status"] == "closure_review_approved"
    assert payload["state_change_allowed"] is False
    assert payload["blocker_state_update_note_recorded"] is True
    assert payload["goal_completion_claimed"] is False
    assert payload["written_targets"] == [str(update_audit)]
    assert "## Provider Proof Blocker State Update - 123e4567-e89b-12d3-a456-426614174000" in body
    assert "- closure_review_status: closure_review_approved" in body
    assert "- state_change_allowed: false" in body
    assert "- blocker_state_update_allowed_by_review: true" in body
    assert "- blocker_state_update_note_recorded: true" in body
    assert "- goal_completion_claimed: false" in body
    assert (
        "- updated_blockers: 2 recorded / 2 provider_proof_recorded_after_review"
    ) in body
    assert "provider-backed-live-voice-proof -> provider_proof_recorded_after_review" in body
    assert "external-publication-proof -> provider_proof_recorded_after_review" in body


def test_record_provider_proof_blocker_state_update_is_idempotent_for_same_review(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    proof_audit = tmp_path / "proof-audit.md"
    review_audit = tmp_path / "review-audit.md"
    update_audit = tmp_path / "blocker-update-audit.md"

    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        _record_provider_proof_record_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof=proof,
                audit_target=[proof_audit],
            ),
            _accepted_provider_proof_record(env_example, proof),
        )
    provider_cli._record_provider_proof_closure_review_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            record_path=None,
            proof_audit_target=[proof_audit],
            audit_target=[review_audit],
        ),
        _closure_review_record(env_example, proof_audit),
    )
    args = Namespace(
        env_example_path=env_example,
        checked_at="2026-05-20",
        run_id="123e4567-e89b-12d3-a456-426614174000",
        proof_audit_target=[proof_audit],
        closure_review_audit_target=[review_audit],
        audit_target=[update_audit],
    )

    first_payload = provider_cli._record_provider_proof_blocker_state_update_payload(
        args
    )
    second_payload = provider_cli._record_provider_proof_blocker_state_update_payload(
        args
    )
    body = update_audit.read_text(encoding="utf-8")

    assert first_payload["status"] == "audit_recorded"
    assert second_payload["status"] == "already_recorded"
    assert second_payload["state_change_allowed"] is False
    assert second_payload["blocker_state_update_note_recorded"] is True
    assert second_payload["written_targets"] == []
    assert second_payload["existing_targets"] == [str(update_audit)]
    assert body.count("## Provider Proof Blocker State Update - 123e4567-e89b-12d3-a456-426614174000") == 1


def test_record_provider_proof_blocker_state_update_redacts_token_shaped_written_and_existing_target_paths(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    proof_audit = tmp_path / "proof-audit.md"
    review_audit = tmp_path / "review-audit.md"
    secret_segment = "sk-ABCDEFGHIJKLMNOPQRST"
    update_audit_dir = tmp_path / secret_segment
    update_audit = update_audit_dir / "blocker-update-audit.md"

    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        _record_provider_proof_record_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof=proof,
                audit_target=[proof_audit],
            ),
            _accepted_provider_proof_record(env_example, proof),
        )
    provider_cli._record_provider_proof_closure_review_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            record_path=None,
            proof_audit_target=[proof_audit],
            audit_target=[review_audit],
        ),
        _closure_review_record(env_example, proof_audit),
    )
    args = Namespace(
        env_example_path=env_example,
        checked_at="2026-05-20",
        run_id="123e4567-e89b-12d3-a456-426614174000",
        proof_audit_target=[proof_audit],
        closure_review_audit_target=[review_audit],
        audit_target=[update_audit],
    )

    first_payload = provider_cli._record_provider_proof_blocker_state_update_payload(
        args
    )
    second_payload = provider_cli._record_provider_proof_blocker_state_update_payload(
        args
    )
    serialized = json.dumps([first_payload, second_payload])
    redacted_target = provider_cli._provider_proof_output_path_text(update_audit)

    assert first_payload["status"] == "audit_recorded"
    assert first_payload["written_targets"] == [redacted_target]
    assert second_payload["status"] == "already_recorded"
    assert second_payload["existing_targets"] == [redacted_target]
    assert update_audit.exists()
    assert secret_segment not in serialized


def test_record_provider_proof_blocker_state_update_rejects_unwritable_audit_target_without_partial_write(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    proof_audit = tmp_path / "proof-audit.md"
    review_audit = tmp_path / "review-audit.md"
    update_audit_one = tmp_path / "blocker-update-audit.md"
    update_audit_two = tmp_path / "blocker-update-directory"
    update_audit_two.mkdir()

    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        _record_provider_proof_record_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof=proof,
                audit_target=[proof_audit],
            ),
            _accepted_provider_proof_record(env_example, proof),
        )
    provider_cli._record_provider_proof_closure_review_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            record_path=None,
            proof_audit_target=[proof_audit],
            audit_target=[review_audit],
        ),
        _closure_review_record(env_example, proof_audit),
    )

    payload = provider_cli._record_provider_proof_blocker_state_update_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof_audit_target=[proof_audit],
            closure_review_audit_target=[review_audit],
            audit_target=[update_audit_one, update_audit_two],
        )
    )

    assert payload["artifact"] == (
        "agent-studio-provider-proof-blocker-state-update-audit"
    )
    assert payload["status"] == "audit_target_unwritable"
    assert payload["closure_review_status"] == "closure_review_approved"
    assert payload["state_change_allowed"] is False
    assert payload["blocker_state_update_note_recorded"] is False
    assert payload["goal_completion_claimed"] is False
    assert payload["written_targets"] == []
    assert payload["audit_issue_codes"] == ["audit_target_unwritable"]
    assert not update_audit_one.exists()


def test_record_provider_proof_blocker_state_update_rejects_nested_bad_audit_parent_without_partial_write(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    proof_audit = tmp_path / "proof-audit.md"
    review_audit = tmp_path / "review-audit.md"
    update_audit_one = tmp_path / "blocker-update-audit.md"
    bad_parent = tmp_path / "not-a-directory"
    bad_parent.write_text("regular file")
    update_audit_two = bad_parent / "nested" / "blocker-update-audit.md"

    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        _record_provider_proof_record_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof=proof,
                audit_target=[proof_audit],
            ),
            _accepted_provider_proof_record(env_example, proof),
        )
    provider_cli._record_provider_proof_closure_review_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            record_path=None,
            proof_audit_target=[proof_audit],
            audit_target=[review_audit],
        ),
        _closure_review_record(env_example, proof_audit),
    )

    payload = provider_cli._record_provider_proof_blocker_state_update_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof_audit_target=[proof_audit],
            closure_review_audit_target=[review_audit],
            audit_target=[update_audit_one, update_audit_two],
        )
    )

    assert payload["artifact"] == (
        "agent-studio-provider-proof-blocker-state-update-audit"
    )
    assert payload["status"] == "audit_target_unwritable"
    assert payload["closure_review_status"] == "closure_review_approved"
    assert payload["state_change_allowed"] is False
    assert payload["blocker_state_update_note_recorded"] is False
    assert payload["goal_completion_claimed"] is False
    assert payload["written_targets"] == []
    assert payload["audit_issue_codes"] == ["audit_target_unwritable"]
    assert not update_audit_one.exists()


def test_record_provider_proof_blocker_state_update_rejects_non_utf8_audit_target_without_partial_write(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    proof_audit = tmp_path / "proof-audit.md"
    review_audit = tmp_path / "review-audit.md"
    update_audit_one = tmp_path / "blocker-update-audit.md"
    update_audit_two = tmp_path / "malformed-blocker-update-audit.md"
    update_audit_two.write_bytes(b"\xff\xfe")

    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        _record_provider_proof_record_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof=proof,
                audit_target=[proof_audit],
            ),
            _accepted_provider_proof_record(env_example, proof),
        )
    provider_cli._record_provider_proof_closure_review_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            record_path=None,
            proof_audit_target=[proof_audit],
            audit_target=[review_audit],
        ),
        _closure_review_record(env_example, proof_audit),
    )

    payload = provider_cli._record_provider_proof_blocker_state_update_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof_audit_target=[proof_audit],
            closure_review_audit_target=[review_audit],
            audit_target=[update_audit_one, update_audit_two],
        )
    )

    assert payload["artifact"] == (
        "agent-studio-provider-proof-blocker-state-update-audit"
    )
    assert payload["status"] == "audit_target_unwritable"
    assert payload["closure_review_status"] == "closure_review_approved"
    assert payload["state_change_allowed"] is False
    assert payload["blocker_state_update_note_recorded"] is False
    assert payload["goal_completion_claimed"] is False
    assert payload["written_targets"] == []
    assert payload["audit_issue_codes"] == ["audit_target_unwritable"]
    assert not update_audit_one.exists()


def test_record_provider_proof_blocker_state_update_blocks_without_approved_closure_review(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    proof_audit = tmp_path / "proof-audit.md"
    review_audit = tmp_path / "review-audit.md"
    update_audit = tmp_path / "blocker-update-audit.md"

    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        _record_provider_proof_record_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof=proof,
                audit_target=[proof_audit],
            ),
            _accepted_provider_proof_record(env_example, proof),
        )
    review_audit.write_text("# no closure review yet\n", encoding="utf-8")

    payload = provider_cli._record_provider_proof_blocker_state_update_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof_audit_target=[proof_audit],
            closure_review_audit_target=[review_audit],
            audit_target=[update_audit],
        )
    )

    assert payload["status"] == "blocked_by_closure_review_status"
    assert payload["closure_review_status"] == "blocked_by_missing_closure_review"
    assert payload["state_change_allowed"] is False
    assert payload["blocker_state_update_note_recorded"] is False
    assert payload["goal_completion_claimed"] is False
    assert payload["written_targets"] == []
    assert not update_audit.exists()


def test_provider_proof_completion_status_blocks_partial_audit_target_coverage(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    target_with_records = tmp_path / "project-audit.md"
    target_without_records = tmp_path / "system-audit.md"
    target_without_records.write_text("# Empty audit target\n", encoding="utf-8")

    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        _record_provider_proof_record_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof=proof,
                audit_target=[target_with_records],
            ),
            _accepted_provider_proof_record(env_example, proof),
        )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[target_with_records, target_without_records],
        )
    )

    assert payload["status"] == "blocked_by_incomplete_audit_target_coverage"
    assert payload["all_required_proofs_accepted"] is False
    assert payload["accepted_proofs"] == [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]
    assert payload["missing_accepted_proofs"] == []
    assert payload["incomplete_audit_target_proofs"] == [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]
    assert payload["proofs"]["provider-backed-live-voice-proof"]["status"] == (
        "accepted_record_missing_from_some_targets"
    )
    assert payload["proofs"]["provider-backed-live-voice-proof"][
        "missing_source_targets"
    ] == [str(target_without_records)]


def test_provider_proof_completion_status_uses_latest_valid_record_per_target(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"

    _record_provider_proof_record_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            audit_target=[audit_target],
        ),
        _accepted_provider_proof_record(env_example, "provider-backed-live-voice-proof"),
    )
    _record_provider_proof_record_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            audit_target=[audit_target],
        ),
        _failed_provider_proof_record(env_example, "provider-backed-live-voice-proof"),
    )
    _record_provider_proof_record_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
            audit_target=[audit_target],
        ),
        _accepted_provider_proof_record(env_example, "external-publication-proof"),
    )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )

    assert payload["status"] == "blocked_by_latest_failed_proof_record"
    assert payload["all_required_proofs_accepted"] is False
    assert payload["accepted_proofs"] == ["external-publication-proof"]
    assert payload["missing_accepted_proofs"] == []
    assert payload["latest_failed_proofs"] == ["provider-backed-live-voice-proof"]
    assert "latest_proof_record_failed" in payload["issue_codes"]
    assert payload["proofs"]["provider-backed-live-voice-proof"]["status"] == (
        "latest_record_failed"
    )
    assert payload["proofs"]["provider-backed-live-voice-proof"][
        "failed_source_targets"
    ] == [str(audit_target)]


def test_provider_proof_completion_status_stops_record_at_next_markdown_section(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"

    _record_provider_proof_record_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            audit_target=[audit_target],
        ),
        _accepted_provider_proof_record(env_example, "provider-backed-live-voice-proof"),
    )
    audit_target.write_text(
        audit_target.read_text(encoding="utf-8")
        + "\n".join(
            [
                "## Frontend OpenRouter Copy Handoff",
                "",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- source: live voice proof accepted in prior section",
                "- source: repeated ordinary note field outside proof record",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )

    assert payload["status"] == "blocked_by_missing_accepted_proof"
    assert payload["all_required_proofs_accepted"] is False
    assert payload["accepted_proofs"] == ["provider-backed-live-voice-proof"]
    assert payload["missing_accepted_proofs"] == ["external-publication-proof"]
    assert payload["invalid_accepted_audit_note_proofs"] == []
    assert payload["proofs"]["provider-backed-live-voice-proof"]["status"] == (
        "accepted_record_found"
    )


def test_provider_proof_completion_status_prefers_validation_timestamp_over_file_order(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"
    audit_target.write_text(
        "\n".join(
            [
                "## Provider Proof Record - provider-backed-live-voice-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T13:00:00Z",
                "- proof_outcome: failed",
                "- validation_status: valid_failed_record",
                "- state_change_allowed: false",
                "- proof_artifact_type: provider_backed_live_voice_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "",
                "## Provider Proof Record - provider-backed-live-voice-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:00:00Z",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: provider_backed_live_voice_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "",
                "## Provider Proof Record - external-publication-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:30:00Z",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: external_publication_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- product_run_preflight_artifact_id: product-run-preflight",
                "- publish_readiness_preflight_artifact_id: publish-preflight",
                "- publish_readiness_artifact_id: publish-ready",
                "- distribution_package_artifact_id: distribution",
                "- approved_artifact_snapshot_id: approved",
                "- destination_channel: linkedin",
                "- durable_platform_id_or_url: https://linkedin.com/posts/123e4567-e89b-12d3-a456-426614174000",
                "- policy_acknowledgement_artifact_id: linkedin-policy-acknowledgement-artifact-123e4567-e89b-12d3-a456-426614174000",
                "- rollback_or_postcondition_artifact_id: linkedin-rollback-postcondition-artifact-123e4567-e89b-12d3-a456-426614174000",
                "- post_capture_validation_results: 6 recorded / 6 passed / 0 failed",
                "- secret_redaction_check: passed",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )

    assert payload["status"] == "blocked_by_latest_failed_proof_record"
    assert payload["latest_failed_proofs"] == ["provider-backed-live-voice-proof"]
    assert payload["proofs"]["provider-backed-live-voice-proof"]["status"] == (
        "latest_record_failed"
    )
    assert payload["proofs"]["provider-backed-live-voice-proof"][
        "failed_source_targets"
    ] == [str(audit_target)]


def test_provider_proof_completion_status_requires_matching_artifact_type(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"
    audit_target.write_text(
        "\n".join(
            [
                "## Provider Proof Record - provider-backed-live-voice-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:00:00Z",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: external_publication_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "",
                "## Provider Proof Record - external-publication-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:30:00Z",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: provider_backed_live_voice_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )

    assert payload["status"] == "blocked_by_missing_accepted_proof"
    assert payload["accepted_proofs"] == []
    assert payload["missing_accepted_proofs"] == [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]


def test_provider_proof_completion_status_rejects_secret_shaped_audit_note_values(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"
    audit_target.write_text(
        "\n".join(
            [
                "## Provider Proof Record - provider-backed-live-voice-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:00:00Z",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: provider_backed_live_voice_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- provider_smoke_ledger_artifact_id: hf_secret_completion_status_must_not_echo",
                "",
                "## Provider Proof Record - external-publication-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:30:00Z",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: external_publication_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- product_run_preflight_artifact_id: product-run-preflight",
                "- publish_readiness_preflight_artifact_id: publish-preflight",
                "- publish_readiness_artifact_id: publish-ready",
                "- distribution_package_artifact_id: distribution",
                "- approved_artifact_snapshot_id: approved",
                "- destination_channel: linkedin",
                "- durable_platform_id_or_url: https://linkedin.com/posts/123e4567-e89b-12d3-a456-426614174000",
                "- policy_acknowledgement_artifact_id: linkedin-policy-acknowledgement-artifact-123e4567-e89b-12d3-a456-426614174000",
                "- rollback_or_postcondition_artifact_id: linkedin-rollback-postcondition-artifact-123e4567-e89b-12d3-a456-426614174000",
                "- post_capture_validation_results: 6 recorded / 6 passed / 0 failed",
                "- secret_redaction_check: passed",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )
    serialized = json.dumps(payload)

    assert payload["status"] == "blocked_by_secret_shaped_audit_note"
    assert payload["all_required_proofs_accepted"] is False
    assert payload["accepted_proofs"] == ["external-publication-proof"]
    assert payload["secret_shaped_audit_note_proofs"] == [
        "provider-backed-live-voice-proof"
    ]
    assert "audit_note_secret_shape_detected" in payload["issue_codes"]
    assert payload["proofs"]["provider-backed-live-voice-proof"]["status"] == (
        "latest_record_contains_secret_shape"
    )
    assert payload["proofs"]["provider-backed-live-voice-proof"][
        "secret_source_targets"
    ] == [str(audit_target)]
    assert "hf_secret_completion_status_must_not_echo" not in serialized


def test_provider_proof_completion_status_rejects_invalid_publication_audit_note_fields(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"
    audit_target.write_text(
        "\n".join(
            [
                "## Provider Proof Record - provider-backed-live-voice-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:00:00Z",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: provider_backed_live_voice_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- product_run_preflight_artifact_id: product-run-preflight",
                "- provider_readiness_preflight_artifact_id: provider-preflight",
                "- voice_runtime_readiness_preflight_artifact_id: voice-preflight",
                    "- voice_agent_process_start_artifact_id: voice-agent-start",
                "- runtime_health_ledger_artifact_id: artifact-runtime-health",
                "- voice_edge_benchmark_status: ready",
                "- provider_smoke_ledger_artifact_id: artifact-smoke",
                    "- livekit_voice_timing_capture_artifact_id: artifact-livekit-capture",
                "- realtime_voice_timing_ledger_artifact_id: artifact-timing",
                "- realtime_provider: openrouter_livekit",
                "- execute_live_calls: true",
                "- realtime_session_id_or_livekit_room: room-123",
                "- participant_identity: agent-voice",
                "- runtime_configuration_snapshot_id: runtime-snapshot",
                "- post_capture_validation_results: 7 recorded / 7 passed / 0 failed",
                "- secret_redaction_check: passed",
                "",
                "## Provider Proof Record - external-publication-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:30:00Z",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: external_publication_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- product_run_preflight_artifact_id: product-run-preflight",
                "- publish_readiness_preflight_artifact_id: publish-preflight",
                "- publish_readiness_artifact_id: publish-ready",
                "- distribution_package_artifact_id: distribution",
                "- approved_artifact_snapshot_id: approved",
                "- destination_channel: linkedin",
                "- durable_platform_id_or_url: https://instagram.com/p/abc123",
                "- policy_acknowledgement_artifact_id: linkedin-policy-acknowledgement-artifact-123e4567-e89b-12d3-a456-426614174000",
                "- rollback_or_postcondition_artifact_id: linkedin-rollback-postcondition-artifact-123e4567-e89b-12d3-a456-426614174000",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )

    assert payload["status"] == "blocked_by_invalid_accepted_audit_note"
    assert payload["all_required_proofs_accepted"] is False
    assert payload["accepted_proofs"] == ["provider-backed-live-voice-proof"]
    assert payload["invalid_accepted_audit_note_proofs"] == [
        "external-publication-proof"
    ]
    assert "accepted_audit_note_invalid_fields" in payload["issue_codes"]
    assert payload["proofs"]["external-publication-proof"]["status"] == (
        "latest_record_has_invalid_fields"
    )
    assert payload["proofs"]["external-publication-proof"][
        "invalid_source_targets"
    ] == [str(audit_target)]


def test_provider_proof_completion_status_rejects_publication_audit_note_destination_missing_from_preflight(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"
    audit_target.write_text(
        "\n".join(
            [
                "## Provider Proof Record - provider-backed-live-voice-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:00:00Z",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: provider_backed_live_voice_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- product_run_preflight_artifact_id: product-run-preflight",
                "- provider_readiness_preflight_artifact_id: provider-preflight",
                "- voice_runtime_readiness_preflight_artifact_id: voice-preflight",
                    "- voice_agent_process_start_artifact_id: voice-agent-start",
                "- runtime_health_ledger_artifact_id: artifact-runtime-health",
                "- voice_edge_benchmark_status: ready",
                "- provider_smoke_ledger_artifact_id: artifact-smoke",
                    "- livekit_voice_timing_capture_artifact_id: artifact-livekit-capture",
                "- realtime_voice_timing_ledger_artifact_id: artifact-timing",
                "- realtime_provider: openrouter_livekit",
                "- execute_live_calls: true",
                "- realtime_session_id_or_livekit_room: room-123",
                "- participant_identity: agent-voice",
                "- runtime_configuration_snapshot_id: runtime-snapshot",
                "- post_capture_validation_results: 7 recorded / 7 passed / 0 failed",
                "- secret_redaction_check: passed",
                "",
                "## Provider Proof Record - external-publication-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:30:00Z",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: external_publication_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- product_run_preflight_artifact_id: product-run-preflight",
                "- publish_readiness_preflight_artifact_id: publish-preflight",
                "- publish_readiness_artifact_id: publish-ready",
                "- distribution_package_artifact_id: distribution",
                "- approved_artifact_snapshot_id: approved",
                "- destination_channel: x_thread",
                "- durable_platform_id_or_url: https://x.com/example/status/123",
                "- policy_acknowledgement_artifact_id: linkedin-policy-acknowledgement-artifact-123e4567-e89b-12d3-a456-426614174000",
                "- rollback_or_postcondition_artifact_id: linkedin-rollback-postcondition-artifact-123e4567-e89b-12d3-a456-426614174000",
                "- post_capture_validation_results: 6 recorded / 6 passed / 0 failed",
                "- secret_redaction_check: passed",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )

    assert payload["status"] == "blocked_by_invalid_accepted_audit_note"
    assert payload["all_required_proofs_accepted"] is False
    assert payload["accepted_proofs"] == ["provider-backed-live-voice-proof"]
    assert payload["invalid_accepted_audit_note_proofs"] == [
        "external-publication-proof"
    ]
    assert payload["proofs"]["external-publication-proof"]["status"] == (
        "latest_record_has_invalid_fields"
    )
    assert payload["proofs"]["external-publication-proof"][
        "invalid_source_targets"
    ] == [str(audit_target)]


def test_provider_proof_completion_status_rejects_publication_audit_note_local_evidence_artifacts(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"
    _record_provider_proof_record_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            audit_target=[audit_target],
        ),
        _accepted_provider_proof_record(env_example, "provider-backed-live-voice-proof"),
    )
    with audit_target.open("a", encoding="utf-8") as audit_file:
        audit_file.write(
            "\n".join(
                [
                    "",
                    "## Provider Proof Record - external-publication-proof - 123e4567-e89b-12d3-a456-426614174000",
                    "",
                    "- checked_at: 2026-05-20",
                    "- validation_timestamp: 2026-05-20T12:30:00Z",
                    "- proof_outcome: accepted",
                    "- validation_status: valid_accepted_record",
                    "- state_change_allowed: true",
                    "- proof_artifact_type: external_publication_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                    "- product_run_preflight_artifact_id: product-run-preflight",
                    "- publish_readiness_preflight_artifact_id: publish-preflight",
                    "- publish_readiness_artifact_id: publish-ready",
                    "- distribution_package_artifact_id: distribution",
                    "- approved_artifact_snapshot_id: approved",
                    "- destination_channel: linkedin",
                    "- durable_platform_id_or_url: https://linkedin.com/posts/123e4567-e89b-12d3-a456-426614174000",
                    "- policy_acknowledgement_artifact_id: policy",
                    "- rollback_or_postcondition_artifact_id: rollback",
                    "- post_capture_validation_results: 6 recorded / 6 passed / 0 failed",
                    "- secret_redaction_check: passed",
                    "",
                ]
            )
        )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )

    assert payload["status"] == "blocked_by_invalid_accepted_audit_note"
    assert payload["all_required_proofs_accepted"] is False
    assert payload["accepted_proofs"] == ["provider-backed-live-voice-proof"]
    assert payload["invalid_accepted_audit_note_proofs"] == [
        "external-publication-proof"
    ]
    assert payload["proofs"]["external-publication-proof"]["status"] == (
        "latest_record_has_invalid_fields"
    )
    assert payload["proofs"]["external-publication-proof"][
        "invalid_source_targets"
    ] == [str(audit_target)]


@pytest.mark.parametrize(
    "validated_publish_channels",
    [
        "linkedin, mastodon",
        "linkedin, linkedin",
        "linkedin, ",
        ", linkedin",
    ],
)
def test_provider_proof_completion_status_rejects_publication_audit_note_noncanonical_publish_channels(
    tmp_path,
    validated_publish_channels,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"
    _record_provider_proof_record_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            audit_target=[audit_target],
        ),
        _accepted_provider_proof_record(env_example, "provider-backed-live-voice-proof"),
    )
    with audit_target.open("a", encoding="utf-8") as audit_file:
        audit_file.write(
            "\n".join(
                [
                    "",
                    "## Provider Proof Record - external-publication-proof - 123e4567-e89b-12d3-a456-426614174000",
                    "",
                    "- checked_at: 2026-05-20",
                    "- validation_timestamp: 2026-05-20T12:30:00Z",
                    "- proof_outcome: accepted",
                    "- validation_status: valid_accepted_record",
                    "- state_change_allowed: true",
                    "- proof_artifact_type: external_publication_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: "
                    f"{validated_publish_channels}",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- product_run_preflight_artifact_id: product-run-preflight",
                "- publish_readiness_preflight_artifact_id: publish-preflight",
                    "- publish_readiness_artifact_id: publish-ready",
                    "- distribution_package_artifact_id: distribution",
                    "- approved_artifact_snapshot_id: approved",
                    "- destination_channel: linkedin",
                    "- durable_platform_id_or_url: https://linkedin.com/posts/123e4567-e89b-12d3-a456-426614174000",
                    "- policy_acknowledgement_artifact_id: linkedin-policy-acknowledgement-artifact-123e4567-e89b-12d3-a456-426614174000",
                    "- rollback_or_postcondition_artifact_id: linkedin-rollback-postcondition-artifact-123e4567-e89b-12d3-a456-426614174000",
                    "- post_capture_validation_results: 6 recorded / 6 passed / 0 failed",
                    "- secret_redaction_check: passed",
                    "",
                ]
            )
        )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )

    assert payload["status"] == "blocked_by_invalid_accepted_audit_note"
    assert payload["all_required_proofs_accepted"] is False
    assert payload["accepted_proofs"] == ["provider-backed-live-voice-proof"]
    assert payload["invalid_accepted_audit_note_proofs"] == [
        "external-publication-proof"
    ]
    assert payload["proofs"]["external-publication-proof"]["status"] == (
        "latest_record_has_invalid_fields"
    )
    assert payload["proofs"]["external-publication-proof"][
        "invalid_source_targets"
    ] == [str(audit_target)]


def test_provider_proof_completion_status_rejects_publication_audit_note_alias_publish_channel_summary(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"
    _record_provider_proof_record_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            audit_target=[audit_target],
        ),
        _accepted_provider_proof_record(env_example, "provider-backed-live-voice-proof"),
    )
    with audit_target.open("a", encoding="utf-8") as audit_file:
        audit_file.write(
            "\n".join(
                [
                    "",
                    "## Provider Proof Record - external-publication-proof - 123e4567-e89b-12d3-a456-426614174000",
                    "",
                    "- checked_at: 2026-05-20",
                    "- validation_timestamp: 2026-05-20T12:30:00Z",
                    "- proof_outcome: accepted",
                    "- validation_status: valid_accepted_record",
                    "- state_change_allowed: true",
                    "- proof_artifact_type: external_publication_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: twitter",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- product_run_preflight_artifact_id: product-run-preflight",
                "- publish_readiness_preflight_artifact_id: publish-preflight",
                    "- publish_readiness_artifact_id: publish-ready",
                    "- distribution_package_artifact_id: distribution",
                    "- approved_artifact_snapshot_id: approved",
                    "- destination_channel: x_thread",
                    "- durable_platform_id_or_url: https://x.com/example/status/123",
                    "- policy_acknowledgement_artifact_id: linkedin-policy-acknowledgement-artifact-123e4567-e89b-12d3-a456-426614174000",
                    "- rollback_or_postcondition_artifact_id: linkedin-rollback-postcondition-artifact-123e4567-e89b-12d3-a456-426614174000",
                    "- post_capture_validation_results: 6 recorded / 6 passed / 0 failed",
                    "- secret_redaction_check: passed",
                    "",
                ]
            )
        )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )

    assert payload["status"] == "blocked_by_invalid_accepted_audit_note"
    assert payload["all_required_proofs_accepted"] is False
    assert payload["accepted_proofs"] == ["provider-backed-live-voice-proof"]
    assert payload["invalid_accepted_audit_note_proofs"] == [
        "external-publication-proof"
    ]
    assert payload["proofs"]["external-publication-proof"]["status"] == (
        "latest_record_has_invalid_fields"
    )


def test_provider_proof_completion_status_rejects_non_linkedin_publication_audit_note(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"
    _record_provider_proof_record_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            audit_target=[audit_target],
        ),
        _accepted_provider_proof_record(env_example, "provider-backed-live-voice-proof"),
    )
    with audit_target.open("a", encoding="utf-8") as audit_file:
        audit_file.write(
            "\n".join(
                [
                    "",
                    "## Provider Proof Record - external-publication-proof - 123e4567-e89b-12d3-a456-426614174000",
                    "",
                    "- checked_at: 2026-05-20",
                    "- validation_timestamp: 2026-05-20T12:30:00Z",
                    "- proof_outcome: accepted",
                    "- validation_status: valid_accepted_record",
                    "- state_change_allowed: true",
                    "- proof_artifact_type: external_publication_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: instagram",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                    "- product_run_preflight_artifact_id: product-run-preflight",
                    "- publish_readiness_preflight_artifact_id: publish-preflight",
                    "- publish_readiness_artifact_id: publish-ready",
                    "- distribution_package_artifact_id: distribution",
                    "- approved_artifact_snapshot_id: approved",
                    "- destination_channel: instagram",
                    "- durable_platform_id_or_url: https://instagram.com/p/abc123",
                    "- policy_acknowledgement_artifact_id: linkedin-policy-acknowledgement-artifact-123e4567-e89b-12d3-a456-426614174000",
                    "- rollback_or_postcondition_artifact_id: linkedin-rollback-postcondition-artifact-123e4567-e89b-12d3-a456-426614174000",
                    "- post_capture_validation_results: 6 recorded / 6 passed / 0 failed",
                    "- secret_redaction_check: passed",
                    "",
                ]
            )
        )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )

    assert payload["status"] == "blocked_by_invalid_accepted_audit_note"
    assert payload["all_required_proofs_accepted"] is False
    assert payload["accepted_proofs"] == ["provider-backed-live-voice-proof"]
    assert payload["invalid_accepted_audit_note_proofs"] == [
        "external-publication-proof"
    ]
    assert payload["proofs"]["external-publication-proof"]["status"] == (
        "latest_record_has_invalid_fields"
    )


def test_provider_proof_completion_status_rejects_live_voice_audit_note_missing_runtime_check_from_preflight(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"
    audit_target.write_text(
        "\n".join(
            [
                "## Provider Proof Record - provider-backed-live-voice-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:00:00Z",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: provider_backed_live_voice_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- product_run_preflight_artifact_id: product-run-preflight",
                "- provider_readiness_preflight_artifact_id: provider-preflight",
                "- voice_runtime_readiness_preflight_artifact_id: voice-preflight",
                    "- voice_agent_process_start_artifact_id: voice-agent-start",
                "- runtime_health_ledger_artifact_id: artifact-runtime-health",
                "- voice_edge_benchmark_status: ready",
                "- provider_smoke_ledger_artifact_id: artifact-smoke",
                    "- livekit_voice_timing_capture_artifact_id: artifact-livekit-capture",
                "- realtime_voice_timing_ledger_artifact_id: artifact-timing",
                "- realtime_provider: openrouter_livekit",
                "- execute_live_calls: true",
                "- realtime_session_id_or_livekit_room: room-123",
                "- participant_identity: agent-voice",
                "- runtime_configuration_snapshot_id: runtime-snapshot",
                "- post_capture_validation_results: 7 recorded / 7 passed / 0 failed",
                "- secret_redaction_check: passed",
                "",
                "## Provider Proof Record - external-publication-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:30:00Z",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: external_publication_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- product_run_preflight_artifact_id: product-run-preflight",
                "- publish_readiness_preflight_artifact_id: publish-preflight",
                "- publish_readiness_artifact_id: publish-ready",
                "- distribution_package_artifact_id: distribution",
                "- approved_artifact_snapshot_id: approved",
                "- destination_channel: linkedin",
                "- durable_platform_id_or_url: https://linkedin.com/posts/123e4567-e89b-12d3-a456-426614174000",
                "- policy_acknowledgement_artifact_id: linkedin-policy-acknowledgement-artifact-123e4567-e89b-12d3-a456-426614174000",
                "- rollback_or_postcondition_artifact_id: linkedin-rollback-postcondition-artifact-123e4567-e89b-12d3-a456-426614174000",
                "- post_capture_validation_results: 6 recorded / 6 passed / 0 failed",
                "- secret_redaction_check: passed",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )

    assert payload["status"] == "blocked_by_invalid_accepted_audit_note"
    assert payload["all_required_proofs_accepted"] is False
    assert payload["accepted_proofs"] == ["external-publication-proof"]
    assert payload["invalid_accepted_audit_note_proofs"] == [
        "provider-backed-live-voice-proof"
    ]
    assert payload["proofs"]["provider-backed-live-voice-proof"]["status"] == (
        "latest_record_has_invalid_fields"
    )
    assert payload["proofs"]["provider-backed-live-voice-proof"][
        "invalid_source_targets"
    ] == [str(audit_target)]


def test_provider_proof_completion_status_rejects_live_voice_audit_note_noncanonical_runtime_checks(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"
    audit_target.write_text(
        "\n".join(
            [
                "## Provider Proof Record - provider-backed-live-voice-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:00:00Z",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: provider_backed_live_voice_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge, local-rehearsal-only",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- product_run_preflight_artifact_id: product-run-preflight",
                "- provider_readiness_preflight_artifact_id: provider-preflight",
                "- voice_runtime_readiness_preflight_artifact_id: voice-preflight",
                    "- voice_agent_process_start_artifact_id: voice-agent-start",
                "- runtime_health_ledger_artifact_id: artifact-runtime-health",
                "- voice_edge_benchmark_status: ready",
                "- provider_smoke_ledger_artifact_id: artifact-smoke",
                    "- livekit_voice_timing_capture_artifact_id: artifact-livekit-capture",
                "- realtime_voice_timing_ledger_artifact_id: artifact-timing",
                "- realtime_provider: openrouter_livekit",
                "- execute_live_calls: true",
                "- realtime_session_id_or_livekit_room: room-123",
                "- participant_identity: agent-voice",
                "- runtime_configuration_snapshot_id: runtime-snapshot",
                "- post_capture_validation_results: 7 recorded / 7 passed / 0 failed",
                "- secret_redaction_check: passed",
                "",
                "## Provider Proof Record - external-publication-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:30:00Z",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: external_publication_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- product_run_preflight_artifact_id: product-run-preflight",
                "- publish_readiness_preflight_artifact_id: publish-preflight",
                "- publish_readiness_artifact_id: publish-ready",
                "- distribution_package_artifact_id: distribution",
                "- approved_artifact_snapshot_id: approved",
                "- destination_channel: linkedin",
                "- durable_platform_id_or_url: https://linkedin.com/posts/123e4567-e89b-12d3-a456-426614174000",
                "- policy_acknowledgement_artifact_id: linkedin-policy-acknowledgement-artifact-123e4567-e89b-12d3-a456-426614174000",
                "- rollback_or_postcondition_artifact_id: linkedin-rollback-postcondition-artifact-123e4567-e89b-12d3-a456-426614174000",
                "- post_capture_validation_results: 6 recorded / 6 passed / 0 failed",
                "- secret_redaction_check: passed",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )

    assert payload["status"] == "blocked_by_invalid_accepted_audit_note"
    assert payload["all_required_proofs_accepted"] is False
    assert payload["accepted_proofs"] == ["external-publication-proof"]
    assert payload["invalid_accepted_audit_note_proofs"] == [
        "provider-backed-live-voice-proof"
    ]
    assert payload["proofs"]["provider-backed-live-voice-proof"]["status"] == (
        "latest_record_has_invalid_fields"
    )


def test_provider_proof_completion_status_rejects_duplicate_contradictory_audit_fields(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"
    audit_target.write_text(
        "\n".join(
            [
                "## Provider Proof Record - provider-backed-live-voice-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:00:00Z",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: provider_backed_live_voice_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- product_run_preflight_artifact_id: product-run-preflight",
                "- provider_readiness_preflight_artifact_id: provider-preflight",
                "- voice_runtime_readiness_preflight_artifact_id: voice-preflight",
                    "- voice_agent_process_start_artifact_id: voice-agent-start",
                "- runtime_health_ledger_artifact_id: artifact-runtime-health",
                "- voice_edge_benchmark_status: ready",
                "- provider_smoke_ledger_artifact_id: artifact-smoke",
                    "- livekit_voice_timing_capture_artifact_id: artifact-livekit-capture",
                "- realtime_voice_timing_ledger_artifact_id: artifact-timing",
                "- realtime_provider: openrouter_livekit",
                "- execute_live_calls: true",
                "- execute_live_calls: false",
                "- realtime_session_id_or_livekit_room: room-123",
                "- participant_identity: agent-voice",
                "- runtime_configuration_snapshot_id: runtime-snapshot",
                "",
                "## Provider Proof Record - external-publication-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:30:00Z",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: external_publication_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- product_run_preflight_artifact_id: product-run-preflight",
                "- publish_readiness_preflight_artifact_id: publish-preflight",
                "- publish_readiness_artifact_id: publish-ready",
                "- distribution_package_artifact_id: distribution",
                "- approved_artifact_snapshot_id: approved",
                "- destination_channel: linkedin",
                "- durable_platform_id_or_url: https://linkedin.com/posts/123e4567-e89b-12d3-a456-426614174000",
                "- policy_acknowledgement_artifact_id: linkedin-policy-acknowledgement-artifact-123e4567-e89b-12d3-a456-426614174000",
                "- rollback_or_postcondition_artifact_id: linkedin-rollback-postcondition-artifact-123e4567-e89b-12d3-a456-426614174000",
                "- post_capture_validation_results: 6 recorded / 6 passed / 0 failed",
                "- secret_redaction_check: passed",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )

    assert payload["status"] == "blocked_by_invalid_accepted_audit_note"
    assert payload["accepted_proofs"] == ["external-publication-proof"]
    assert payload["invalid_accepted_audit_note_proofs"] == [
        "provider-backed-live-voice-proof"
    ]
    assert payload["proofs"]["provider-backed-live-voice-proof"]["status"] == (
        "latest_record_has_invalid_fields"
    )


def test_provider_proof_completion_status_scans_duplicate_audit_fields_for_secrets(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"
    duplicate_secret_value = "hf_secret_duplicate_audit_note_must_not_echo"
    audit_target.write_text(
        "\n".join(
            [
                "## Provider Proof Record - provider-backed-live-voice-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:00:00Z",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: provider_backed_live_voice_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- product_run_preflight_artifact_id: product-run-preflight",
                "- provider_readiness_preflight_artifact_id: provider-preflight",
                "- voice_runtime_readiness_preflight_artifact_id: voice-preflight",
                    "- voice_agent_process_start_artifact_id: voice-agent-start",
                "- runtime_health_ledger_artifact_id: artifact-runtime-health",
                "- voice_edge_benchmark_status: ready",
                "- provider_smoke_ledger_artifact_id: artifact-smoke",
                    "- livekit_voice_timing_capture_artifact_id: artifact-livekit-capture",
                "- realtime_voice_timing_ledger_artifact_id: artifact-timing",
                "- realtime_provider: openrouter_livekit",
                "- execute_live_calls: true",
                "- realtime_session_id_or_livekit_room: room-123",
                "- participant_identity: agent-voice",
                "- runtime_configuration_snapshot_id: runtime-snapshot",
                "- post_capture_validation_results: 7 recorded / 7 passed / 0 failed",
                "- secret_redaction_check: passed",
                "",
                "## Provider Proof Record - external-publication-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:30:00Z",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: external_publication_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- product_run_preflight_artifact_id: product-run-preflight",
                "- publish_readiness_preflight_artifact_id: publish-preflight",
                "- publish_readiness_artifact_id: publish-ready",
                "- distribution_package_artifact_id: distribution",
                "- approved_artifact_snapshot_id: approved",
                "- destination_channel: linkedin",
                "- durable_platform_id_or_url: https://linkedin.com/posts/123e4567-e89b-12d3-a456-426614174000",
                f"- durable_platform_id_or_url: {duplicate_secret_value}",
                "- policy_acknowledgement_artifact_id: linkedin-policy-acknowledgement-artifact-123e4567-e89b-12d3-a456-426614174000",
                "- rollback_or_postcondition_artifact_id: linkedin-rollback-postcondition-artifact-123e4567-e89b-12d3-a456-426614174000",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )
    serialized = json.dumps(payload)

    assert payload["status"] == "blocked_by_secret_shaped_audit_note"
    assert payload["accepted_proofs"] == ["provider-backed-live-voice-proof"]
    assert payload["secret_shaped_audit_note_proofs"] == [
        "external-publication-proof"
    ]
    assert duplicate_secret_value not in serialized


def test_provider_proof_completion_status_rejects_missing_required_accepted_audit_fields(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"
    audit_target.write_text(
        "\n".join(
            [
                "## Provider Proof Record - provider-backed-live-voice-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:00:00Z",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: provider_backed_live_voice_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- product_run_preflight_artifact_id: product-run-preflight",
                "- provider_readiness_preflight_artifact_id: provider-preflight",
                "- voice_runtime_readiness_preflight_artifact_id: voice-preflight",
                    "- voice_agent_process_start_artifact_id: voice-agent-start",
                "- runtime_health_ledger_artifact_id: artifact-runtime-health",
                "- voice_edge_benchmark_status: ready",
                "- provider_smoke_ledger_artifact_id: artifact-smoke",
                    "- livekit_voice_timing_capture_artifact_id: artifact-livekit-capture",
                "- realtime_voice_timing_ledger_artifact_id: artifact-timing",
                "- realtime_provider: openrouter_livekit",
                "- execute_live_calls: true",
                "",
                "## Provider Proof Record - external-publication-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:30:00Z",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: external_publication_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- product_run_preflight_artifact_id: product-run-preflight",
                "- publish_readiness_preflight_artifact_id: publish-preflight",
                "- publish_readiness_artifact_id: publish-ready",
                "- distribution_package_artifact_id: distribution",
                "- approved_artifact_snapshot_id: approved",
                "- destination_channel: linkedin",
                "- durable_platform_id_or_url: https://linkedin.com/posts/123e4567-e89b-12d3-a456-426614174000",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )

    assert payload["status"] == "blocked_by_invalid_accepted_audit_note"
    assert payload["accepted_proofs"] == []
    assert payload["invalid_accepted_audit_note_proofs"] == [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]
    assert payload["proofs"]["provider-backed-live-voice-proof"]["status"] == (
        "latest_record_has_invalid_fields"
    )
    assert payload["proofs"]["external-publication-proof"]["status"] == (
        "latest_record_has_invalid_fields"
    )


def test_provider_proof_completion_status_requires_validation_summary_and_redaction_check(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"
    audit_target.write_text(
        "\n".join(
            [
                "## Provider Proof Record - provider-backed-live-voice-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:00:00Z",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: provider_backed_live_voice_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- product_run_preflight_artifact_id: product-run-preflight",
                "- provider_readiness_preflight_artifact_id: provider-preflight",
                "- voice_runtime_readiness_preflight_artifact_id: voice-preflight",
                    "- voice_agent_process_start_artifact_id: voice-agent-start",
                "- runtime_health_ledger_artifact_id: artifact-runtime-health",
                "- voice_edge_benchmark_status: ready",
                "- provider_smoke_ledger_artifact_id: artifact-smoke",
                    "- livekit_voice_timing_capture_artifact_id: artifact-livekit-capture",
                "- realtime_voice_timing_ledger_artifact_id: artifact-timing",
                "- realtime_provider: openrouter_livekit",
                "- execute_live_calls: true",
                "- realtime_session_id_or_livekit_room: room-123",
                "- participant_identity: agent-voice",
                "- runtime_configuration_snapshot_id: runtime-snapshot",
                "",
                "## Provider Proof Record - external-publication-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:30:00Z",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: external_publication_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- product_run_preflight_artifact_id: product-run-preflight",
                "- publish_readiness_preflight_artifact_id: publish-preflight",
                "- publish_readiness_artifact_id: publish-ready",
                "- distribution_package_artifact_id: distribution",
                "- approved_artifact_snapshot_id: approved",
                "- destination_channel: linkedin",
                "- durable_platform_id_or_url: https://linkedin.com/posts/123e4567-e89b-12d3-a456-426614174000",
                "- policy_acknowledgement_artifact_id: linkedin-policy-acknowledgement-artifact-123e4567-e89b-12d3-a456-426614174000",
                "- rollback_or_postcondition_artifact_id: linkedin-rollback-postcondition-artifact-123e4567-e89b-12d3-a456-426614174000",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )

    assert payload["status"] == "blocked_by_invalid_accepted_audit_note"
    assert payload["accepted_proofs"] == []
    assert payload["invalid_accepted_audit_note_proofs"] == [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]


def test_provider_proof_completion_status_requires_preflight_report_summary(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"
    audit_target.write_text(
        "\n".join(
            [
                "## Provider Proof Record - provider-backed-live-voice-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:00:00Z",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: provider_backed_live_voice_proof_record",
                "- preflight_validation_report_artifact_id: preflight-validation",
                "- product_run_preflight_artifact_id: product-run-preflight",
                "- provider_readiness_preflight_artifact_id: provider-preflight",
                "- voice_runtime_readiness_preflight_artifact_id: voice-preflight",
                    "- voice_agent_process_start_artifact_id: voice-agent-start",
                "- runtime_health_ledger_artifact_id: artifact-runtime-health",
                "- voice_edge_benchmark_status: ready",
                "- provider_smoke_ledger_artifact_id: artifact-smoke",
                    "- livekit_voice_timing_capture_artifact_id: artifact-livekit-capture",
                "- realtime_voice_timing_ledger_artifact_id: artifact-timing",
                "- realtime_provider: openrouter_livekit",
                "- execute_live_calls: true",
                "- realtime_session_id_or_livekit_room: room-123",
                "- participant_identity: agent-voice",
                "- runtime_configuration_snapshot_id: runtime-snapshot",
                "- post_capture_validation_results: 7 recorded / 7 passed / 0 failed",
                "- secret_redaction_check: passed",
                "",
                "## Provider Proof Record - external-publication-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:30:00Z",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: external_publication_proof_record",
                "- preflight_validation_report_artifact_id: preflight-validation",
                "- preflight_validation_report_status: valid_preflight_artifacts",
                "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                "- workspace_validation_report_artifact_id: workspace-validation",
                "- workspace_validation_report_status: valid_workspace",
                "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- product_run_preflight_artifact_id: product-run-preflight",
                "- publish_readiness_preflight_artifact_id: publish-preflight",
                "- publish_readiness_artifact_id: publish-ready",
                "- distribution_package_artifact_id: distribution",
                "- approved_artifact_snapshot_id: approved",
                "- destination_channel: linkedin",
                "- durable_platform_id_or_url: https://linkedin.com/posts/123e4567-e89b-12d3-a456-426614174000",
                "- policy_acknowledgement_artifact_id: linkedin-policy-acknowledgement-artifact-123e4567-e89b-12d3-a456-426614174000",
                "- rollback_or_postcondition_artifact_id: linkedin-rollback-postcondition-artifact-123e4567-e89b-12d3-a456-426614174000",
                "- post_capture_validation_results: 6 recorded / 6 passed / 0 failed",
                "- secret_redaction_check: passed",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )

    assert payload["status"] == "blocked_by_invalid_accepted_audit_note"
    assert payload["accepted_proofs"] == ["external-publication-proof"]
    assert payload["proofs"]["provider-backed-live-voice-proof"]["status"] == (
        "latest_record_has_invalid_fields"
    )


def test_provider_proof_completion_status_rejects_unparseable_accepted_audit_timestamp(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"
    audit_target.write_text(
        "\n".join(
            [
                "## Provider Proof Record - provider-backed-live-voice-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: not-a-date",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: provider_backed_live_voice_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- product_run_preflight_artifact_id: product-run-preflight",
                "- provider_readiness_preflight_artifact_id: provider-preflight",
                "- voice_runtime_readiness_preflight_artifact_id: voice-preflight",
                    "- voice_agent_process_start_artifact_id: voice-agent-start",
                "- runtime_health_ledger_artifact_id: artifact-runtime-health",
                "- voice_edge_benchmark_status: ready",
                "- provider_smoke_ledger_artifact_id: artifact-smoke",
                    "- livekit_voice_timing_capture_artifact_id: artifact-livekit-capture",
                "- realtime_voice_timing_ledger_artifact_id: artifact-timing",
                "- realtime_provider: openrouter_livekit",
                "- execute_live_calls: true",
                "- realtime_session_id_or_livekit_room: room-123",
                "- participant_identity: agent-voice",
                "- runtime_configuration_snapshot_id: runtime-snapshot",
                "- post_capture_validation_results: 7 recorded / 7 passed / 0 failed",
                "- secret_redaction_check: passed",
                "",
                "## Provider Proof Record - external-publication-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:30:00Z",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: external_publication_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- product_run_preflight_artifact_id: product-run-preflight",
                "- publish_readiness_preflight_artifact_id: publish-preflight",
                "- publish_readiness_artifact_id: publish-ready",
                "- distribution_package_artifact_id: distribution",
                "- approved_artifact_snapshot_id: approved",
                "- destination_channel: linkedin",
                "- durable_platform_id_or_url: https://linkedin.com/posts/123e4567-e89b-12d3-a456-426614174000",
                "- policy_acknowledgement_artifact_id: linkedin-policy-acknowledgement-artifact-123e4567-e89b-12d3-a456-426614174000",
                "- rollback_or_postcondition_artifact_id: linkedin-rollback-postcondition-artifact-123e4567-e89b-12d3-a456-426614174000",
                "- post_capture_validation_results: 6 recorded / 6 passed / 0 failed",
                "- secret_redaction_check: passed",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )

    assert payload["status"] == "blocked_by_invalid_accepted_audit_note"
    assert payload["accepted_proofs"] == ["external-publication-proof"]
    assert payload["invalid_accepted_audit_note_proofs"] == [
        "provider-backed-live-voice-proof"
    ]


def test_provider_proof_completion_status_unparseable_invalid_note_not_masked_by_older_accepted(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"
    _record_provider_proof_record_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            audit_target=[audit_target],
        ),
        _accepted_provider_proof_record(env_example, "provider-backed-live-voice-proof"),
    )
    _record_provider_proof_record_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
            audit_target=[audit_target],
        ),
        _accepted_provider_proof_record(env_example, "external-publication-proof"),
    )
    audit_target.write_text(
        audit_target.read_text(encoding="utf-8")
        + "\n".join(
            [
                "## Provider Proof Record - provider-backed-live-voice-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: not-a-date",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: provider_backed_live_voice_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- product_run_preflight_artifact_id: product-run-preflight",
                "- provider_readiness_preflight_artifact_id: provider-preflight",
                "- voice_runtime_readiness_preflight_artifact_id: voice-preflight",
                    "- voice_agent_process_start_artifact_id: voice-agent-start",
                "- runtime_health_ledger_artifact_id: artifact-runtime-health",
                "- voice_edge_benchmark_status: ready",
                "- provider_smoke_ledger_artifact_id: artifact-smoke",
                    "- livekit_voice_timing_capture_artifact_id: artifact-livekit-capture",
                "- realtime_voice_timing_ledger_artifact_id: artifact-timing",
                "- realtime_provider: openrouter_livekit",
                "- execute_live_calls: false",
                "- realtime_session_id_or_livekit_room: room-123",
                "- participant_identity: agent-voice",
                "- runtime_configuration_snapshot_id: runtime-snapshot",
                "- post_capture_validation_results: 7 recorded / 7 passed / 0 failed",
                "- secret_redaction_check: passed",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )

    assert payload["status"] == "blocked_by_invalid_accepted_audit_note"
    assert payload["accepted_proofs"] == ["external-publication-proof"]
    assert payload["invalid_accepted_audit_note_proofs"] == [
        "provider-backed-live-voice-proof"
    ]


def test_provider_proof_completion_status_unparseable_secret_note_not_masked_by_older_accepted(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"
    secret_value = "hf_secret_unparseable_timestamp_must_not_echo"
    _record_provider_proof_record_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="provider-backed-live-voice-proof",
            audit_target=[audit_target],
        ),
        _accepted_provider_proof_record(env_example, "provider-backed-live-voice-proof"),
    )
    _record_provider_proof_record_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            proof="external-publication-proof",
            audit_target=[audit_target],
        ),
        _accepted_provider_proof_record(env_example, "external-publication-proof"),
    )
    audit_target.write_text(
        audit_target.read_text(encoding="utf-8")
        + "\n".join(
            [
                "## Provider Proof Record - provider-backed-live-voice-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: not-a-date",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: provider_backed_live_voice_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- product_run_preflight_artifact_id: product-run-preflight",
                "- provider_readiness_preflight_artifact_id: provider-preflight",
                "- voice_runtime_readiness_preflight_artifact_id: voice-preflight",
                    "- voice_agent_process_start_artifact_id: voice-agent-start",
                "- runtime_health_ledger_artifact_id: artifact-runtime-health",
                "- voice_edge_benchmark_status: ready",
                f"- provider_smoke_ledger_artifact_id: {secret_value}",
                "- realtime_voice_timing_ledger_artifact_id: artifact-timing",
                "- realtime_provider: openrouter_livekit",
                "- execute_live_calls: true",
                "- realtime_session_id_or_livekit_room: room-123",
                "- participant_identity: agent-voice",
                "- runtime_configuration_snapshot_id: runtime-snapshot",
                "- post_capture_validation_results: 7 recorded / 7 passed / 0 failed",
                "- secret_redaction_check: passed",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )
    serialized = json.dumps(payload)

    assert payload["status"] == "blocked_by_secret_shaped_audit_note"
    assert payload["accepted_proofs"] == ["external-publication-proof"]
    assert payload["secret_shaped_audit_note_proofs"] == [
        "provider-backed-live-voice-proof"
    ]
    assert secret_value not in serialized


def test_provider_proof_completion_status_secret_shape_takes_precedence_over_failed_proofs(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"
    audit_target.write_text(
        "\n".join(
            [
                "## Provider Proof Record - provider-backed-live-voice-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:00:00Z",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: provider_backed_live_voice_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- provider_smoke_ledger_artifact_id: hf_secret_failed_status_must_not_echo",
                "",
                "## Provider Proof Record - external-publication-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:30:00Z",
                "- proof_outcome: failed",
                "- validation_status: valid_failed_record",
                "- state_change_allowed: false",
                "- proof_artifact_type: external_publication_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )
    serialized = json.dumps(payload)

    assert payload["status"] == "blocked_by_secret_shaped_audit_note"
    assert "audit_note_secret_shape_detected" in payload["issue_codes"]
    assert "latest_proof_record_failed" in payload["issue_codes"]
    assert payload["latest_failed_proofs"] == ["external-publication-proof"]
    assert "hf_secret_failed_status_must_not_echo" not in serialized


def test_provider_proof_completion_status_secret_shape_takes_precedence_over_missing_proofs(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"
    audit_target.write_text(
        "\n".join(
            [
                "## Provider Proof Record - provider-backed-live-voice-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- checked_at: 2026-05-20",
                "- validation_timestamp: 2026-05-20T12:00:00Z",
                "- proof_outcome: accepted",
                "- validation_status: valid_accepted_record",
                "- state_change_allowed: true",
                "- proof_artifact_type: provider_backed_live_voice_proof_record",
                    "- preflight_validation_report_artifact_id: preflight-validation",
                    "- preflight_validation_report_status: valid_preflight_artifacts",
                    "- preflight_validation_report_matched_fields: all_required_fields_matched",
                    "- preflight_validation_report_validated_product_run_id: 123e4567-e89b-12d3-a456-426614174000",
                    "- preflight_validation_report_validated_publish_channels: linkedin",
                    "- preflight_validation_report_validated_runtime_checks: livekit-transport, livekit-agent-participant, voice-agent-backend-event-sink, openrouter-live-dialogue-reasoning, kokoro-tts, rust-voice-edge",
                    "- workspace_validation_report_artifact_id: workspace-validation",
                    "- workspace_validation_report_status: valid_workspace",
                    "- workspace_validation_report_matched_fields: all_required_fields_matched",
                "- provider_smoke_ledger_artifact_id: hf_secret_missing_status_must_not_echo",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )
    serialized = json.dumps(payload)

    assert payload["status"] == "blocked_by_secret_shaped_audit_note"
    assert "audit_note_secret_shape_detected" in payload["issue_codes"]
    assert "accepted_proof_record_missing" in payload["issue_codes"]
    assert payload["missing_accepted_proofs"] == ["external-publication-proof"]
    assert "hf_secret_missing_status_must_not_echo" not in serialized


def test_provider_proof_completion_status_rejects_malformed_accepted_markers(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "objective-audit.md"
    audit_target.write_text(
        "\n".join(
            [
                "## Provider Proof Record - provider-backed-live-voice-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- proof_outcome: accepted-pending",
                "- validation_status: valid_accepted_record_pending",
                "- state_change_allowed: true-ish",
                "",
                "## Provider Proof Record - external-publication-proof - 123e4567-e89b-12d3-a456-426614174000",
                "",
                "- proof_outcome: accepted-pending",
                "- validation_status: valid_accepted_record_pending",
                "- state_change_allowed: true-ish",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )

    assert payload["status"] == "blocked_by_missing_accepted_proof"
    assert payload["accepted_proofs"] == []
    assert payload["missing_accepted_proofs"] == [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]


def test_provider_proof_completion_status_reports_directory_audit_target(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    audit_target = tmp_path / "audit-directory"
    audit_target.mkdir()

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[audit_target],
        )
    )

    assert payload["status"] == "blocked_by_missing_accepted_proof"
    assert "audit_targets_invalid" in payload["issue_codes"]
    assert payload["invalid_audit_targets"] == [str(audit_target)]
    assert payload["missing_accepted_proofs"] == [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]


def test_provider_proof_completion_status_reports_non_utf8_audit_target(
    tmp_path,
):
    env_example = tmp_path / ".env.example"
    env_example.write_text("")
    readable_target = tmp_path / "objective-audit.md"
    secret_segment = "sk-ABCDEFGHIJKLMNOPQRST"
    malformed_target_dir = tmp_path / secret_segment
    malformed_target_dir.mkdir()
    malformed_target = malformed_target_dir / "malformed-audit.md"
    malformed_target.write_bytes(b"\xff\xfe")

    for proof in [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]:
        _record_provider_proof_record_payload(
            Namespace(
                env_example_path=env_example,
                checked_at="2026-05-20",
                run_id="123e4567-e89b-12d3-a456-426614174000",
                proof=proof,
                audit_target=[readable_target],
            ),
            _accepted_provider_proof_record(env_example, proof),
        )

    payload = provider_cli._provider_proof_completion_status_payload(
        Namespace(
            env_example_path=env_example,
            checked_at="2026-05-20",
            run_id="123e4567-e89b-12d3-a456-426614174000",
            audit_target=[readable_target, malformed_target],
        )
    )

    assert payload["status"] == "blocked_by_invalid_audit_target"
    assert payload["blocker_state_change_allowed_by_this_command"] is False
    assert payload["accepted_proofs"] == [
        "provider-backed-live-voice-proof",
        "external-publication-proof",
    ]
    assert payload["issue_codes"] == ["audit_targets_invalid"]
    assert payload["invalid_audit_targets"] == [
        provider_cli._provider_proof_output_path_text(malformed_target)
    ]
    assert secret_segment not in json.dumps(payload)
