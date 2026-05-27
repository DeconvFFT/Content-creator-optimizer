import json
import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
CURRENT_MATRIX = (
    ROOT
    / "social_media_optimiser/output/provider-proof/"
    / "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-blocker-matrix.json"
)


def _open(page, relative_path):
    page.goto((ROOT / relative_path).as_uri())


def _json(page, selector):
    return json.loads(page.locator(selector).input_value())


def _current_matrix_readiness():
    return json.loads(CURRENT_MATRIX.read_text(encoding="utf-8"))


def _resolve_json_pointer(payload, pointer):
    assert pointer.startswith("/")
    value = payload
    for raw_part in pointer.lstrip("/").split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        value = value[part]
    return value


def _normalize_run_id(value):
    if isinstance(value, dict):
        return {key: _normalize_run_id(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_run_id(item) for item in value]
    if isinstance(value, str):
        return re.sub(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "<run-id>",
            value,
        )
    return value


def _assert_readiness_matches_matrix(packet):
    matrix_payload = _current_matrix_readiness()
    matrix = matrix_payload["operator_input_readiness"]
    proof_id = packet["proof_id"]
    matrix_row = _resolve_json_pointer(matrix_payload, packet["matrix_parity_ref"])
    assert matrix_row == matrix["proofs"][proof_id]
    readiness = packet["operator_input_readiness"]

    assert readiness["status"] == matrix_row["status"]
    assert readiness["checked_at"] == matrix["checked_at"]
    assert readiness["evidence_ref"] == matrix["evidence_ref"]
    assert readiness["effective_fail_on_blocked_exit_code"] == matrix[
        "effective_fail_on_blocked_exit_code"
    ]
    assert readiness["exit_policy"] == matrix["exit_policy"]
    assert _normalize_run_id(readiness["strict_readiness_command"]) == (
        _normalize_run_id(matrix["strict_readiness_command"])
    )
    assert readiness["state"] == matrix_row["state"]
    assert readiness["issue_codes"] == matrix_row["issue_codes"]
    assert readiness["next_action"] == matrix_row["next_action"]
    assert readiness["blocked_fields"] == matrix_row["blocked_fields"]
    assert readiness["required_fields"] == matrix_row["required_fields"]
    assert readiness["configured_fields"] == matrix_row["configured_fields"]
    assert readiness["field_contracts"] == matrix_row["field_contracts"]
    assert readiness["field_ownership"] == matrix_row["field_ownership"]
    assert readiness["field_groups"] == matrix_row["field_groups"]
    assert readiness["field_statuses"] == matrix_row["field_statuses"]
    assert _normalize_run_id(readiness["next_action_commands"]) == (
        _normalize_run_id(matrix_row["next_action_commands"])
    )
    assert _normalize_run_id(readiness["guarded_next_action_commands"]) == (
        _normalize_run_id(matrix_row["guarded_next_action_commands"])
    )
    assert (
        readiness["required_evidence_after_unblock"]
        == matrix_row["required_evidence_after_unblock"]
    )


def _assert_readiness_exit_policy(readiness):
    assert readiness["exit_policy"] == {
        "default_exit_code": 0,
        "fail_on_blocked_exit_code": 2,
        "fail_on_blocked_statuses": [
            "blocked_by_operator_inputs",
            "invalid_operator_input_file",
        ],
        "ready_status": "ready_for_credential_snapshot_refresh",
    }


def _assert_common_readiness_diagnostics(readiness):
    assert readiness["state"] == "blocked_by_operator_inputs"
    assert readiness["checked_at"] == "2026-05-26"
    assert readiness["evidence_ref"] == "operator-input-readiness.json"
    assert readiness["issue_codes"] == ["operator_input_placeholder"]
    report_only_commands = readiness["next_action_commands"]
    assert report_only_commands[0].startswith(
        "uv run all-about-llms-admin provider-proof-operator-input-readiness "
    )
    assert "--fail-on-blocked" not in report_only_commands[0]
    assert any(
        "blocker-credential-snapshot" in command for command in report_only_commands
    )
    assert any("provider-proof-plan" in command for command in report_only_commands)
    assert any(
        "provider-proof-current-blocker-matrix" in command
        for command in report_only_commands
    )


def _assert_packet_contract(packet):
    matrix_payload = _current_matrix_readiness()

    assert packet["packet_schema_version"] == "operator-proof-packet.v1"
    assert packet["handoff_contract"] == "value-free-operator-proof-handoff"
    assert packet["state_change_allowed"] is False
    assert (
        packet["state_change_guardrail"]
        == "no_state_change_without_accepted_proof_and_closure_review"
    )
    assert packet["source_artifacts"] == {
        "operator_input_readiness": "operator-input-readiness.json",
        "current_blocker_matrix": "current-blocker-matrix.json",
        "operator_input_template": "operator-inputs.template.env",
        "proof_plan": "proof-plan.json",
    }
    assert packet["completion_evidence_ref"] == matrix_payload["completion"][
        "evidence_ref"
    ]
    assert packet["closure_evidence_refs"] == matrix_payload["closure"][
        "evidence_refs"
    ]
    expected_current_gate = {
        "completion_status": matrix_payload["completion"]["status"],
        "closure_review_template_status": matrix_payload["closure"][
            "closure_review_template_status"
        ],
        "closure_review_status": matrix_payload["closure"]["closure_review_status"],
        "blocker_state_update_status": matrix_payload["closure"][
            "blocker_state_update_status"
        ],
        "completion_next_action": matrix_payload["completion"]["next_action"],
        "completion_next_action_commands": matrix_payload["completion"][
            "next_action_commands"
        ],
        "state_change_allowed": matrix_payload["closure"]["state_change_allowed"],
        "goal_completion_claimed": matrix_payload["closure"][
            "goal_completion_claimed"
        ],
        "completion_issue_codes": matrix_payload["completion"]["issue_codes"],
        "latest_failed_proofs": matrix_payload["completion"][
            "latest_failed_proofs"
        ],
        "missing_accepted_proofs": matrix_payload["completion"][
            "missing_accepted_proofs"
        ],
    }
    assert _normalize_run_id(packet["current_gate"]) == (
        _normalize_run_id(expected_current_gate)
    )
    assert packet["current_state_packets"] == matrix_payload[
        "current_state_packets"
    ]
    assert _normalize_run_id(packet["current_state_packet_commands"]) == (
        _normalize_run_id(matrix_payload["current_state_packet_commands"])
    )
    assert packet["next_status_packet"] == matrix_payload["next_status_packet"]
    assert packet["next_operator_packet"] == matrix_payload["next_operator_packet"]
    matrix_packet = matrix_payload["operator_proof_packets"][packet["proof_id"]]
    assert packet["proof_capture_matrix_ref"] == matrix_packet[
        "proof_capture_matrix_ref"
    ]
    assert _resolve_json_pointer(
        matrix_payload,
        packet["proof_capture_matrix_ref"],
    ) == matrix_payload["proofs"][packet["proof_id"]][
        "proof_capture_commands_after_unblock"
    ]
    assert _normalize_run_id(packet["proof_capture_commands_after_unblock"]) == (
        _normalize_run_id(matrix_packet["proof_capture_commands_after_unblock"])
    )


def _assert_voice_proof_packet(packet):
    assert packet["proof_id"] == "provider-backed-live-voice-proof"
    assert (
        packet["matrix_parity_ref"]
        == "/operator_input_readiness/proofs/provider-backed-live-voice-proof"
    )
    _assert_packet_contract(packet)
    _assert_readiness_matches_matrix(packet)
    assert packet["secret_handling"] == (
        "Do not print tokens, API keys, or secrets; record endpoint and account "
        "identifiers only."
    )
    assert "provider_smoke_ledger with execute_live_calls=true" in packet[
        "must_capture"
    ]
    assert "livekit_voice_timing_capture JSON" in packet["must_capture"]
    assert "realtime_voice_timing_ledger JSON" in packet["must_capture"]
    assert "LiveKit room/session id and participant identity" in packet[
        "must_capture"
    ]
    assert "captured microphone turn with first text/audio timing" in packet[
        "must_capture"
    ]
    assert "interrupt or barge-in acknowledgement evidence" in packet[
        "must_capture"
    ]
    assert "social_media_optimiser/01-work-tracking/Agent Studio Objective Completion Audit.md" in packet[
        "store_in"
    ]
    readiness = packet["operator_input_readiness"]
    assert readiness["status"] == "ready_for_credential_snapshot_refresh"
    assert readiness["state"] == "ready_for_credential_snapshot_refresh"
    assert readiness["next_action"] == "refresh_credential_snapshot"
    assert readiness["effective_fail_on_blocked_exit_code"] == 2
    assert readiness["blocked_fields"] == []
    assert readiness["issue_codes"] == []
    assert "HF_TOKEN_FILE" not in readiness["required_fields"]
    assert "GEMMA4_MULTIMODAL_ENDPOINT_URL" not in readiness["required_fields"]
    assert "same-run OpenRouter DeepSeek live dialogue reasoning evidence" in readiness[
        "required_evidence_after_unblock"
    ]
    assert readiness["field_groups"] == {
        "invalid_fields": [],
        "missing_fields": [],
        "placeholder_fields": [],
        "unavailable_secret_file_fields": [],
    }
    assert readiness["field_ownership"]["OPENROUTER_API_KEY_FILE"] == {
        "proof_id": "provider-backed-live-voice-proof",
        "proof_input_role": "provider_credential",
    }
    assert readiness["field_ownership"]["OPENROUTER_LIVEKIT_URL"] == {
        "proof_id": "provider-backed-live-voice-proof",
        "proof_input_role": "transport_endpoint",
    }
    assert readiness["field_statuses"]["OPENROUTER_API_KEY_FILE"] == {
        "contract": "readable local secret file path; file content is never emitted",
        "issue_code": "none",
        "next_action": "refresh_credential_snapshot",
        "proof_id": "provider-backed-live-voice-proof",
        "proof_input_role": "provider_credential",
        "state": "configured",
        "value_source": "secret_file_path",
    }
    assert readiness["field_statuses"]["OPENROUTER_LIVEKIT_URL"] == {
        "contract": "ws or wss LiveKit URL for OpenRouter-backed realtime dialogue",
        "issue_code": "none",
        "next_action": "refresh_credential_snapshot",
        "proof_id": "provider-backed-live-voice-proof",
        "proof_input_role": "transport_endpoint",
        "state": "configured",
        "value_source": "endpoint_url",
    }
    _assert_readiness_exit_policy(readiness)
    assert "--fail-on-blocked" in readiness["strict_readiness_command"]
    guarded_commands = readiness["guarded_next_action_commands"]
    assert guarded_commands[0] == readiness["strict_readiness_command"]
    assert any("blocker-credential-snapshot" in command for command in guarded_commands)
    assert any("provider-proof-plan" in command for command in guarded_commands)
    assert any(
        "provider-proof-current-blocker-matrix" in command
        for command in guarded_commands
    )


def _assert_publication_proof_packet(packet):
    assert packet["proof_id"] == "external-publication-proof"
    assert (
        packet["matrix_parity_ref"]
        == "/operator_input_readiness/proofs/external-publication-proof"
    )
    _assert_packet_contract(packet)
    _assert_readiness_matches_matrix(packet)
    assert packet["secret_handling"] == (
        "Do not print tokens, API keys, or secrets; record endpoint and account "
        "identifiers only."
    )
    assert "approved artifact snapshot with copy, media, audience, visibility, disclosure, and schedule" in packet[
        "must_capture"
    ]
    assert "platform API response proof or approved manual completion proof" in packet[
        "must_capture"
    ]
    assert "durable platform ID or URL" in packet["must_capture"]
    assert "postcondition monitoring record" in packet["must_capture"]
    assert "rollback, delete, private, or correction proof" in packet[
        "must_capture"
    ]
    assert "system_design_vault/04-agent-studio-implications/agent-studio-objective-completion-audit.md" in packet[
        "store_in"
    ]
    readiness = packet["operator_input_readiness"]
    assert readiness["status"] == "blocked_by_operator_inputs"
    assert readiness["next_action"] == (
        "supply_manual_publication_policy_destination_and_rollback_evidence"
    )
    assert readiness["effective_fail_on_blocked_exit_code"] == 2
    assert "LINKEDIN_ACCESS_TOKEN_FILE" not in readiness["blocked_fields"]
    assert "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL" in readiness["blocked_fields"]
    assert "rollback or postcondition artifact" in readiness[
        "required_evidence_after_unblock"
    ]
    _assert_common_readiness_diagnostics(readiness)
    assert readiness["field_groups"] == {
        "invalid_fields": [],
        "missing_fields": [],
        "placeholder_fields": [
            "LINKEDIN_POLICY_ACKNOWLEDGEMENT_ARTIFACT_ID",
            "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL",
            "PUBLICATION_ROLLBACK_OR_POSTCONDITION_ARTIFACT_ID",
        ],
        "unavailable_secret_file_fields": [],
    }
    assert readiness["field_ownership"]["PUBLICATION_DURABLE_PLATFORM_ID_OR_URL"] == {
        "proof_id": "external-publication-proof",
        "proof_input_role": "publication_destination",
    }
    assert "LINKEDIN_ACCESS_TOKEN_FILE" not in readiness["field_ownership"]
    assert readiness["field_statuses"]["PUBLICATION_DURABLE_PLATFORM_ID_OR_URL"] == {
        "contract": "durable LinkedIn URL or platform id; local substitutes rejected",
        "issue_code": "operator_input_placeholder",
        "next_action": "replace_placeholder_in_operator_input_file",
        "proof_id": "external-publication-proof",
        "proof_input_role": "publication_destination",
        "state": "placeholder",
        "value_source": "external_destination",
    }
    assert "LINKEDIN_ACCESS_TOKEN_FILE" not in readiness["field_statuses"]
    _assert_readiness_exit_policy(readiness)
    assert "--fail-on-blocked" in readiness["strict_readiness_command"]
    guarded_commands = readiness["guarded_next_action_commands"]
    assert guarded_commands[0] == readiness["strict_readiness_command"]
    assert any("blocker-credential-snapshot" in command for command in guarded_commands)
    assert any("provider-proof-plan" in command for command in guarded_commands)
    assert any(
        "provider-proof-current-blocker-matrix" in command
        for command in guarded_commands
    )


def test_live_voice_operator_proof_packet_is_exported_and_propagated():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})

            _open(
                page,
                "social_media_optimiser/01-work-tracking/"
                "agent-studio-proof-readiness.html",
            )
            page.get_by_role("button", name="Live voice").click()
            expect(page.locator("#blocker-detail")).to_contain_text("Proof packet")
            expect(page.locator("#blocker-detail")).to_contain_text("Packet schema")
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Matrix parity ref"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Source artifacts"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Completion evidence ref"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Closure evidence refs"
            )
            expect(page.locator("#blocker-detail")).to_contain_text("Current gate")
            expect(page.locator("#blocker-detail")).to_contain_text(
                "blocked_by_latest_failed_proof_record"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Completion next action"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "capture_validate_record_and_recheck"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "provider-proof-record-template --proof provider-backed-live-voice-proof"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "provider-proof-completion-status --run-id"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "goal completion claimed: false"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Current state packets"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Proof capture commands after unblock"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Proof-plan operator packet"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Proof-plan current gate recovery authority"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "completion_next_action"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "current_matrix_packet_ref"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Proof-plan source artifacts"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Proof-plan field ownership"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "transport_endpoint"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "capture-livekit-voice-timing-proof"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "livekit_voice_timing_capture_artifact_id"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "validate-provider-proof-preflight-artifacts"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "current-proof-status.md"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "State change guardrail"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Do not print tokens"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Readiness evidence"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Report-only retry sequence"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Input required fields"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Configured fields"
            )
            expect(page.locator("#blocker-detail")).to_contain_text("Issue codes")
            expect(page.locator("#blocker-detail")).to_contain_text("Exit policy")
            expect(page.locator("#blocker-detail")).to_contain_text("Field contracts")
            expect(page.locator("#blocker-detail")).to_contain_text("Field ownership")
            expect(page.locator("#blocker-detail")).to_contain_text("Field statuses")
            expect(page.locator("#blocker-detail")).to_contain_text(
                "provider_credential"
            )
            expect(page.locator("#blocker-detail")).to_contain_text("endpoint_url")
            readiness_packet = _json(page, "#readiness-export")["blockers"][0][
                "operator_proof_packet"
            ]
            _assert_voice_proof_packet(readiness_packet)

            _open(
                page,
                "social_media_optimiser/02-research/openrouter-livekit-voice-boundary-map.html",
            )
            page.get_by_role("button", name="Proof gate").click()
            expect(page.locator("#route-detail")).to_contain_text("Proof packet")
            expect(page.locator("#route-detail")).to_contain_text(
                "Proof-plan operator packet"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                "Proof-plan current gate recovery authority"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                "completion_next_action"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                "Proof-plan source artifacts"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                "Proof-plan field ownership"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                "transport_endpoint"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                "capture-livekit-voice-timing-proof"
            )
            expect(page.locator("#route-detail")).to_contain_text("Field ownership")
            expect(page.locator("#route-detail")).to_contain_text("Field statuses")
            expect(page.locator("#route-detail")).to_contain_text(
                "provider_credential"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                "Completion next action"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                "provider-proof-completion-status --run-id"
            )
            expect(page.locator("#route-detail")).to_contain_text("endpoint_url")
            boundary_packet = _json(page, "#boundary-export")["routes"][0][
                "operator_proof_packet"
            ]
            assert boundary_packet == readiness_packet
        finally:
            browser.close()


def test_publication_operator_proof_packet_is_exported_and_propagated():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})

            _open(
                page,
                "social_media_optimiser/01-work-tracking/"
                "agent-studio-proof-readiness.html",
            )
            page.get_by_role("button", name="Publication").click()
            expect(page.locator("#blocker-detail")).to_contain_text("Proof packet")
            expect(page.locator("#blocker-detail")).to_contain_text("Packet schema")
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Matrix parity ref"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Source artifacts"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Completion evidence ref"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Closure evidence refs"
            )
            expect(page.locator("#blocker-detail")).to_contain_text("Current gate")
            expect(page.locator("#blocker-detail")).to_contain_text(
                "blocked_by_latest_failed_proof_record"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Completion next action"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "capture_validate_record_and_recheck"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "provider-proof-record-template --proof external-publication-proof"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "provider-proof-completion-status --run-id"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "goal completion claimed: false"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Current state packets"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Proof capture commands after unblock"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Proof-plan operator packet"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Proof-plan current gate recovery authority"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "completion_next_action"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "current_matrix_packet_ref"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Proof-plan source artifacts"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Proof-plan field ownership"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "publication_evidence"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "validate-provider-proof-preflight-artifacts"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "current-proof-status.md"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "State change guardrail"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Do not print tokens"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Readiness evidence"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Report-only retry sequence"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Input required fields"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Configured fields"
            )
            expect(page.locator("#blocker-detail")).to_contain_text("Issue codes")
            expect(page.locator("#blocker-detail")).to_contain_text("Exit policy")
            expect(page.locator("#blocker-detail")).to_contain_text("Field contracts")
            expect(page.locator("#blocker-detail")).to_contain_text("Field ownership")
            expect(page.locator("#blocker-detail")).to_contain_text("Field statuses")
            expect(page.locator("#blocker-detail")).to_contain_text(
                "publication_destination"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "external_destination"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "secret_file_unavailable"
            )
            readiness_packet = _json(page, "#readiness-export")["blockers"][0][
                "operator_proof_packet"
            ]
            _assert_publication_proof_packet(readiness_packet)

            _open(
                page,
                "social_media_optimiser/03-review-packets/"
                "agent-studio-publication-boundary-map.html",
            )
            page.get_by_role("button", name="External proof").click()
            expect(page.locator("#publication-detail")).to_contain_text(
                "Proof packet"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "Proof-plan operator packet"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "Proof-plan current gate recovery authority"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "completion_next_action"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "Proof-plan source artifacts"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "Proof-plan field ownership"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "publication_evidence"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "Field ownership"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "Field statuses"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "publication_destination"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "Completion next action"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "provider-proof-completion-status --run-id"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "external_destination"
            )
            boundary_packet = _json(page, "#publication-export")["routes"][0][
                "operator_proof_packet"
            ]
            assert boundary_packet == readiness_packet
        finally:
            browser.close()
