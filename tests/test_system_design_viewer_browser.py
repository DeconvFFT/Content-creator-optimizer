import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def _objective_audit_component():
    viewer_path = (
        ROOT / "social_media_optimiser/output/viewers/agent-studio-system-design.json"
    )
    projection = json.loads(viewer_path.read_text())
    return next(
        component
        for component in projection["runtime_components"]
        if component["id"] == "objective-completion-audit"
    )


def test_system_design_viewer_operator_input_handoff_matches_current_matrix():
    matrix_path = (
        ROOT
        / "social_media_optimiser/output/provider-proof/"
        / "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-blocker-matrix.json"
    )
    proof_plan_path = (
        ROOT
        / "social_media_optimiser/output/provider-proof/"
        / "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/proof-plan.json"
    )
    matrix = json.loads(matrix_path.read_text())
    proof_plan = json.loads(proof_plan_path.read_text())
    audit = _objective_audit_component()

    readiness = matrix["operator_input_readiness"]
    assert audit["current_gate"]["completion_next_action"] == matrix["completion"][
        "next_action"
    ]
    assert audit["current_gate"]["completion_next_action_commands"] == matrix[
        "completion"
    ]["next_action_commands"]
    assert audit["operator_input_readiness_command"] == readiness[
        "strict_readiness_command"
    ]
    assert audit["operator_input_retry_sequence"] == readiness[
        "next_action_commands"
    ]
    assert audit["guarded_operator_retry_sequence"] == readiness[
        "guarded_next_action_commands"
    ]
    assert audit["operator_input_readiness_exit_policy"] == readiness["exit_policy"]
    assert audit["operator_input_readiness_diagnostics"] == {
        "checked_at": readiness["checked_at"],
        "effective_fail_on_blocked_exit_code": readiness[
            "effective_fail_on_blocked_exit_code"
        ],
        "evidence_ref": readiness["evidence_ref"],
        "status": readiness["status"],
        "issue_codes": readiness["issue_codes"],
        "required_fields": readiness["required_fields"],
        "blocked_fields": readiness["blocked_fields"],
        "configured_fields": readiness["configured_fields"],
        "field_contracts": readiness["field_contracts"],
        "field_groups": readiness["field_groups"],
        "field_ownership": readiness["field_ownership"],
        "field_statuses": readiness["field_statuses"],
    }
    assert audit["operator_input_source_artifacts"] == next(
        iter(matrix["operator_proof_packets"].values())
    )["source_artifacts"]
    assert audit["proof_plan_operator_sequence"] == proof_plan["proofs"][
        "provider-backed-live-voice-proof"
    ]["operator_sequence"]
    assert audit["proof_plan_operator_sequence"] == proof_plan["proofs"][
        "external-publication-proof"
    ]["operator_sequence"]
    assert audit["proof_plan_closeout_commands_by_proof"] == {
        proof_id: proof["closeout_commands"]
        for proof_id, proof in proof_plan["proofs"].items()
    }

    expected_routes = {
        proof_id: {
            "proof_id": proof_id,
            "state": proof["state"],
            "next_action": proof["next_action"],
            "matrix_parity_ref": f"/operator_input_readiness/proofs/{proof_id}",
            "proof_capture_matrix_ref": matrix["operator_proof_packets"][proof_id][
                "proof_capture_matrix_ref"
            ],
            "blocked_fields": proof["blocked_fields"],
            "required_fields": proof["required_fields"],
            "configured_fields": proof["configured_fields"],
            "issue_codes": proof["issue_codes"],
            "field_contracts": proof["field_contracts"],
            "field_ownership": proof["field_ownership"],
            "field_groups": proof["field_groups"],
            "field_statuses": proof["field_statuses"],
            "required_evidence_after_unblock": proof[
                "required_evidence_after_unblock"
            ],
            "next_action_commands": proof["next_action_commands"],
            "guarded_next_action_commands": proof["guarded_next_action_commands"],
            "proof_capture_commands_after_unblock": matrix[
                "operator_proof_packets"
            ][proof_id]["proof_capture_commands_after_unblock"],
            "proof_record_schema": matrix["operator_proof_packets"][proof_id][
                "proof_record_schema"
            ],
            "proof_record_required_fields": matrix["operator_proof_packets"][
                proof_id
            ]["proof_record_required_fields"],
            "operator_proof_packet": matrix["operator_proof_packets"][proof_id],
            "proof_plan_operator_packet": proof_plan["proofs"][proof_id][
                "operator_proof_packet"
            ],
        }
        for proof_id, proof in readiness["proofs"].items()
    }
    actual_routes = {
        route["proof_id"]: route for route in audit["operator_input_readiness_routing"]
    }
    assert actual_routes == expected_routes


def test_system_design_viewer_filter_promotes_visible_objective_audit_detail():
    viewer_path = (
        ROOT
        / "social_media_optimiser/output/viewers/agent-studio-system-design-viewer.html"
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(viewer_path.as_uri())

            expect(page.locator("#component-count")).to_have_text("10 shown")
            expect(page.locator("#component-grid .node")).to_have_count(10)

            page.locator("#search").fill("external publication proof")

            expect(page.locator("#component-count")).to_have_text("1 shown")
            expect(page.locator("#component-grid .node")).to_have_count(1)
            expect(page.locator("#component-grid .node")).to_contain_text(
                "Objective Completion Audit"
            )
            expect(page.locator("#selected-id")).to_have_text(
                "objective-completion-audit"
            )
            expect(page.locator("#detail")).to_contain_text(
                "Do not call the goal complete"
            )
            expect(page.locator("#detail")).to_contain_text("proof_plan")
            expect(page.locator("#detail")).to_contain_text(
                "provider-proof-plan"
            )
            expect(page.locator("#detail")).to_contain_text(
                "Provider-backed live voice proof packet"
            )
            expect(page.locator("#detail")).to_contain_text(
                "Proof-plan operator packet"
            )
            expect(page.locator("#detail")).to_contain_text(
                "current_matrix_packet_ref="
            )
            expect(page.locator("#detail")).to_contain_text(
                "Proof-plan current gate recovery authority"
            )
            expect(page.locator("#detail")).to_contain_text(
                "completion_next_action"
            )
            expect(page.locator("#detail")).to_contain_text(
                "Proof-plan source artifacts"
            )
            expect(page.locator("#detail")).to_contain_text(
                "Proof-plan field ownership"
            )
            expect(page.locator("#detail")).to_contain_text("must_capture")
            expect(page.locator("#detail")).to_contain_text(
                "current-proof-status.md"
            )
            expect(page.locator("#detail")).to_contain_text(
                "current-blocker-matrix.json"
            )
            expect(page.locator("#detail")).to_contain_text(
                "operator-unblocker-checklist.md"
            )
            expect(page.locator("#detail")).to_contain_text("Current proof gate")
            expect(page.locator("#detail")).to_contain_text(
                "completion_next_action"
            )
            expect(page.locator("#detail")).to_contain_text(
                "capture_validate_record_and_recheck"
            )
            expect(page.locator("#detail")).to_contain_text(
                "completion_next_action_commands"
            )
            expect(page.locator("#detail")).to_contain_text(
                "blocked_by_latest_failed_proof_record"
            )
            expect(page.locator("#detail")).to_contain_text(
                "provider-backed-live-voice-proof"
            )
            expect(page.locator("#detail")).to_contain_text(
                "provider_backed_live_voice_proof_record"
            )
            expect(page.locator("#detail")).to_contain_text(
                "external_publication_proof_record"
            )
            expect(page.locator("#detail")).to_contain_text(
                "external-publication-proof"
            )
            expect(page.locator("#detail")).to_contain_text(
                "state_change_allowed=false"
            )
            expect(page.locator("#detail")).to_contain_text(
                "completion-status.json"
            )
            expect(page.locator("#detail")).to_contain_text(
                "closure-review-status.json"
            )
            expect(page.locator("#detail")).to_contain_text(
                "blocker-state-update.json"
            )
            expect(page.locator("#detail")).to_contain_text(
                "Current state packet commands"
            )
            expect(page.locator("#detail")).to_contain_text(
                "provider-proof-current-blocker-matrix"
            )
            expect(page.locator("#detail")).to_contain_text(
                "provider-proof-current-status"
            )
            expect(page.locator("#detail")).to_contain_text(
                "provider-proof-operator-unblocker-checklist"
            )
            expect(page.locator("#detail")).to_contain_text(
                "Operator input readiness command"
            )
            expect(page.locator("#detail")).to_contain_text(
                "provider-proof-operator-input-readiness"
            )
            expect(page.locator("#detail")).to_contain_text("--fail-on-blocked")
            expect(page.locator("#detail")).to_contain_text(
                "operator-input-readiness.json"
            )
            expect(page.locator("#detail")).to_contain_text(
                "Proof-plan operator sequence"
            )
            expect(page.locator("#detail")).to_contain_text(
                "create or select durable product run UUID"
            )
            expect(page.locator("#detail")).to_contain_text(
                "Proof-plan closeout commands"
            )
            expect(page.locator("#detail")).to_contain_text(
                "provider-proof-completion-status"
            )
            expect(page.locator("#detail")).to_contain_text(
                "record-provider-proof-blocker-state-update"
            )
            expect(page.locator("#detail")).to_contain_text(
                "Guarded operator retry sequence"
            )
            expect(page.locator("#detail")).to_contain_text(
                "blocker-credential-snapshot"
            )
            expect(page.locator("#detail")).to_contain_text(
                "credential-snapshot.json"
            )
            expect(page.locator("#detail")).to_contain_text("proof-plan.json")
            expect(page.locator("#detail")).to_contain_text(
                "current-proof-status.md"
            )
            expect(page.locator("#detail")).to_contain_text(
                "Operator input readiness exit policy"
            )
            expect(page.locator("#detail")).to_contain_text("default_exit_code=0")
            expect(page.locator("#detail")).to_contain_text(
                "fail_on_blocked_exit_code=2"
            )
            expect(page.locator("#detail")).to_contain_text(
                "blocked_by_operator_inputs"
            )
            expect(page.locator("#detail")).to_contain_text(
                "invalid_operator_input_file"
            )
            expect(page.locator("#detail")).to_contain_text(
                "ready_for_credential_snapshot_refresh"
            )
            expect(page.locator("#detail")).to_contain_text(
                "Report-only operator retry sequence"
            )
            expect(page.locator("#detail")).to_contain_text(
                "Operator input readiness diagnostics"
            )
            expect(page.locator("#detail")).to_contain_text(
                "status=blocked_by_operator_inputs"
            )
            expect(page.locator("#detail")).to_contain_text("checked_at=2026-05-23")
            expect(page.locator("#detail")).to_contain_text(
                "effective_fail_on_blocked_exit_code=2"
            )
            expect(page.locator("#detail")).to_contain_text(
                "operator_input_secret_file_unavailable"
            )
            expect(page.locator("#detail")).to_contain_text(
                "operator_input_placeholder"
            )
            expect(page.locator("#detail")).to_contain_text("configured_fields")
            expect(page.locator("#detail")).to_contain_text("required_fields")
            expect(page.locator("#detail")).to_contain_text("field_contracts")
            expect(page.locator("#detail")).to_contain_text("field_statuses")
            expect(page.locator("#detail")).to_contain_text("field_groups")
            expect(page.locator("#detail")).to_contain_text(
                "Operator input readiness routing"
            )
            expect(page.locator("#detail")).to_contain_text(
                "refresh_credential_snapshot"
            )
            expect(page.locator("#detail")).to_contain_text(
                "supply_linkedin_token_policy_destination_and_rollback_evidence"
            )
            expect(page.locator("#detail")).to_contain_text("placeholder_fields")
            expect(page.locator("#detail")).to_contain_text(
                "unavailable_secret_file_fields"
            )
            expect(page.locator("#detail")).to_contain_text("Field contracts")
            expect(page.locator("#detail")).to_contain_text("Field ownership")
            expect(page.locator("#detail")).to_contain_text("Field statuses")
            expect(page.locator("#detail")).to_contain_text("provider_credential")
            expect(page.locator("#detail")).to_contain_text(
                "publication_destination"
            )
            expect(page.locator("#detail")).to_contain_text("endpoint_url")
            expect(page.locator("#detail")).to_contain_text("external_destination")
            expect(page.locator("#detail")).to_contain_text(
                "secret_file_unavailable"
            )
            expect(page.locator("#detail")).to_contain_text("next_action_commands")
            expect(page.locator("#detail")).to_contain_text(
                "guarded_next_action_commands"
            )
            expect(page.locator("#detail")).to_contain_text(
                "proof_capture_commands_after_unblock"
            )
            expect(page.locator("#detail")).to_contain_text(
                "Proof capture commands after unblock"
            )
            expect(page.locator("#detail")).to_contain_text(
                "Route required evidence after unblock"
            )
            expect(page.locator("#detail")).to_contain_text(
                "valid provider-backed live voice preflight validation"
            )
            expect(page.locator("#detail")).to_contain_text(
                "valid external publication preflight validation"
            )
            expect(page.locator("#detail")).to_contain_text(
                "Proof record required fields"
            )
            expect(page.locator("#detail")).to_contain_text(
                "voice_agent_process_start_artifact_id"
            )
            expect(page.locator("#detail")).to_contain_text(
                "validate-provider-proof-record --proof provider-backed-live-voice-proof"
            )
            expect(page.locator("#detail")).to_contain_text(
                "validate-provider-proof-record --proof external-publication-proof"
            )
            expect(page.locator("#detail")).to_contain_text(
                "validate-provider-proof-preflight-artifacts"
            )
            expect(page.locator("#detail")).to_contain_text(
                "/proofs/provider-backed-live-voice-proof/proof_capture_commands_after_unblock"
            )
            expect(page.locator("#detail")).to_contain_text(
                "/operator_input_readiness/proofs/provider-backed-live-voice-proof"
            )
            expect(page.locator("#detail")).to_contain_text(
                "/operator_input_readiness/proofs/external-publication-proof"
            )
            expect(page.locator("#detail")).to_contain_text(
                "Operator input source artifacts"
            )
            expect(page.locator("#detail")).to_contain_text(
                "operator_input_template"
            )
            expect(page.locator("#detail")).to_contain_text(
                "operator-inputs.template.env"
            )
            expect(page.locator("#detail")).to_contain_text(
                "Operator proof packet contract"
            )
            expect(page.locator("#detail")).to_contain_text(
                "operator-proof-packet.v1"
            )
            expect(page.locator("#detail")).to_contain_text(
                "value-free-operator-proof-handoff"
            )
            expect(page.locator("#detail")).to_contain_text(
                "no_state_change_without_accepted_proof_and_closure_review"
            )
            expect(page.locator("#detail")).to_contain_text(
                "Operator input blockers"
            )
            expect(page.locator("#detail")).not_to_contain_text("HF_TOKEN_FILE")
            expect(page.locator("#detail")).not_to_contain_text(
                "GEMMA4_MULTIMODAL_ENDPOINT_URL"
            )
            expect(page.locator("#detail")).to_contain_text("OPENROUTER_API_KEY_FILE")
            expect(page.locator("#detail")).to_contain_text("OPENROUTER_LIVEKIT_URL")
            expect(page.locator("#detail")).to_contain_text(
                "LINKEDIN_ACCESS_TOKEN_FILE"
            )
            expect(page.locator("#detail")).to_contain_text(
                "PUBLICATION_DURABLE_PLATFORM_ID_OR_URL"
            )
            expect(page.locator("#detail")).to_contain_text(
                "Required evidence after unblock"
            )
            expect(page.locator("#detail")).to_contain_text(
                "same-run OpenRouter DeepSeek live dialogue reasoning evidence"
            )
            expect(page.locator("#detail")).to_contain_text(
                "durable external destination proof"
            )
            expect(page.locator("#detail")).to_contain_text(
                "passed secret-redaction check"
            )
        finally:
            browser.close()
