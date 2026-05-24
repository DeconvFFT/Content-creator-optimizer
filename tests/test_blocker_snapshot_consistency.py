import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
CURRENT_RUN_ID = "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e"
CURRENT_BLOCKER_MATRIX = (
    ROOT
    / "social_media_optimiser/output/provider-proof/"
    / f"{CURRENT_RUN_ID}/current-blocker-matrix.json"
)


def _open(page, relative_path):
    page.goto((ROOT / relative_path).as_uri())


def _export_json(page, selector):
    return json.loads(page.locator(selector).input_value())


def _current_blocker_matrix_checked_at():
    return json.loads(CURRENT_BLOCKER_MATRIX.read_text())["checked_at"]


def _current_operator_packets():
    return json.loads(CURRENT_BLOCKER_MATRIX.read_text())["operator_proof_packets"]


def _current_credential_snapshots():
    snapshot_path = CURRENT_BLOCKER_MATRIX.parent / "credential-snapshot.json"
    return json.loads(snapshot_path.read_text())["snapshots"]


def _current_proof_plans():
    proof_plan_path = CURRENT_BLOCKER_MATRIX.parent / "proof-plan.json"
    return json.loads(proof_plan_path.read_text())["proofs"]


def _extract_static_const_array(relative_path, const_name):
    html = (ROOT / relative_path).read_text(encoding="utf-8")
    marker = f"const {const_name} = "
    start = html.index(marker) + len(marker)
    assert html[start] == "["
    depth = 0
    in_string = None
    escaped = False
    for index, char in enumerate(html[start:], start=start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == in_string:
                in_string = None
            continue
        if char in {'"', "'"}:
            in_string = char
        elif char in "[{":
            depth += 1
        elif char in "]}":
            depth -= 1
            if depth == 0:
                return html[start : index + 1]
    raise AssertionError(f"Could not extract const {const_name} from {relative_path}")


def _static_js_array_payload(relative_path, const_name):
    js_literal = _extract_static_const_array(relative_path, const_name)
    json_literal = re.sub(
        r"(?m)^(\s*)([A-Za-z_][A-Za-z0-9_]*):",
        r'\1"\2":',
        js_literal,
    )
    json_literal = re.sub(r",(\s*[}\]])", r"\1", json_literal)
    return json.loads(json_literal)


def _static_operator_packets(relative_path, const_name):
    packets = {}
    for entry in _static_js_array_payload(relative_path, const_name):
        packet = entry.get("operator_proof_packet")
        if packet:
            packets[packet["proof_id"]] = _normalize_current_matrix_run_id(packet)
    return packets


def _normalize_current_matrix_run_id(value):
    if isinstance(value, str):
        return value.replace(CURRENT_RUN_ID, "<run-id>")
    if isinstance(value, list):
        return [_normalize_current_matrix_run_id(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _normalize_current_matrix_run_id(item)
            for key, item in value.items()
        }
    return value


def _assert_propagated_snapshot_matches_source(boundary_snapshot, source_snapshot):
    assert boundary_snapshot["source"] == "agent-studio-proof-readiness"
    assert boundary_snapshot["source_snapshot"] == source_snapshot["source"]
    assert boundary_snapshot["checked_at"] == source_snapshot["checked_at"]
    assert boundary_snapshot["state"] == source_snapshot["state"]
    assert (
        boundary_snapshot["placeholder_only_inputs"]
        == source_snapshot["placeholder_only_inputs"]
    )
    assert boundary_snapshot["absent_inputs"] == source_snapshot["absent_inputs"]
    assert (
        boundary_snapshot["shell_values_loaded"]
        == source_snapshot["shell_values_loaded"]
    )
    assert (
        boundary_snapshot["secret_files_loaded"]
        == source_snapshot["secret_files_loaded"]
    )
    assert (
        boundary_snapshot["secret_values_printed"]
        == source_snapshot["secret_values_printed"]
    )
    assert boundary_snapshot["configured_inputs"] == source_snapshot["configured_inputs"]
    assert (
        boundary_snapshot["configured_file_inputs"]
        == source_snapshot["configured_file_inputs"]
    )
    assert (
        boundary_snapshot["configured_local_provider_inputs"]
        == source_snapshot["configured_local_provider_inputs"]
    )
    assert (
        boundary_snapshot["local_provider_config_loaded"]
        == source_snapshot["local_provider_config_loaded"]
    )
    assert boundary_snapshot["note"] == source_snapshot["note"]


def _assert_snapshot_matches_cli(html_snapshot, cli_snapshot):
    assert html_snapshot["source"] == cli_snapshot["source"]
    assert html_snapshot["checked_at"] == cli_snapshot["checked_at"]
    assert html_snapshot["state"] == cli_snapshot["state"]
    assert html_snapshot["shell_values_loaded"] == cli_snapshot["shell_values_loaded"]
    assert html_snapshot["secret_files_loaded"] == cli_snapshot["secret_files_loaded"]
    assert (
        html_snapshot["secret_values_printed"]
        == cli_snapshot["secret_values_printed"]
    )
    assert html_snapshot["configured_inputs"] == cli_snapshot["configured_inputs"]
    assert (
        html_snapshot["configured_file_inputs"]
        == cli_snapshot["configured_file_inputs"]
    )
    assert (
        html_snapshot["configured_local_provider_inputs"]
        == cli_snapshot["configured_local_provider_inputs"]
    )
    assert (
        html_snapshot["local_provider_config_loaded"]
        == cli_snapshot["local_provider_config_loaded"]
    )
    assert (
        html_snapshot["placeholder_only_inputs"]
        == cli_snapshot["placeholder_only_inputs"]
    )
    assert html_snapshot["absent_inputs"] == cli_snapshot["absent_inputs"]
    assert html_snapshot["note"] == cli_snapshot["note"]


def _assert_proof_plan_matches_cli(html_plan, cli_plan):
    assert html_plan["status"] == cli_plan["status"]
    assert html_plan["blocking_reasons"] == cli_plan["blocking_reasons"]
    assert html_plan["credential_state"] == cli_plan["credential_state"]
    assert (
        html_plan["credential_setup_requirements"]
        == cli_plan["credential_setup_requirements"]
    )
    assert (
        html_plan["credential_setup_commands"]
        == cli_plan["credential_setup_commands"]
    )
    assert html_plan["operator_sequence"] == cli_plan["operator_sequence"]
    assert html_plan["product_run_bootstrap"] == cli_plan["product_run_bootstrap"]
    assert html_plan["workspace_commands"] == cli_plan["workspace_commands"]
    assert (
        html_plan["workspace_validation_commands"]
        == cli_plan["workspace_validation_commands"]
    )
    assert (
        html_plan["workspace_validation_report_files"]
        == cli_plan["workspace_validation_report_files"]
    )
    assert (
        html_plan["workspace_validation_capture_commands"]
        == cli_plan["workspace_validation_capture_commands"]
    )
    assert (
        html_plan["workspace_expected_files"]
        == cli_plan["workspace_expected_files"]
    )
    assert html_plan["attempt_gate"] == cli_plan["attempt_gate"]
    assert html_plan["configured_inputs"] == cli_plan["configured_inputs"]
    assert html_plan["configured_file_inputs"] == cli_plan["configured_file_inputs"]
    assert (
        html_plan["configured_local_provider_inputs"]
        == cli_plan["configured_local_provider_inputs"]
    )
    assert (
        html_plan["local_provider_config_loaded"]
        == cli_plan["local_provider_config_loaded"]
    )
    assert html_plan["secret_files_loaded"] == cli_plan["secret_files_loaded"]
    assert html_plan["runtime_proof_required"] == cli_plan["runtime_proof_required"]
    assert html_plan["run_id_state"] == cli_plan["run_id_state"]
    assert html_plan["product_run_id_state"] == cli_plan["product_run_id_state"]
    assert (
        html_plan["run_id_required_before_execution"]
        == cli_plan["run_id_required_before_execution"]
    )
    assert html_plan["command_run_id"] == cli_plan["command_run_id"]
    assert html_plan["commands"] == cli_plan["commands"]
    assert html_plan["template_commands"] == cli_plan["template_commands"]
    assert html_plan["record_commands"] == cli_plan["record_commands"]
    assert (
        html_plan["completion_status_commands"]
        == cli_plan["completion_status_commands"]
    )
    assert html_plan["closeout_commands"] == cli_plan["closeout_commands"]
    assert html_plan["preflight_checks"] == cli_plan["preflight_checks"]
    assert html_plan["preflight_commands"] == cli_plan["preflight_commands"]
    assert html_plan["preflight_output_files"] == cli_plan["preflight_output_files"]
    assert (
        html_plan["preflight_capture_commands"]
        == cli_plan["preflight_capture_commands"]
    )
    assert (
        html_plan["proof_capture_commands_after_unblock"]
        == cli_plan["proof_capture_commands_after_unblock"]
    )
    assert html_plan["operator_proof_packet"] == cli_plan["operator_proof_packet"]
    assert (
        html_plan["preflight_artifact_id_fields"]
        == cli_plan["preflight_artifact_id_fields"]
    )
    assert (
        html_plan["preflight_validation_commands"]
        == cli_plan["preflight_validation_commands"]
    )
    assert (
        html_plan["preflight_validation_report_files"]
        == cli_plan["preflight_validation_report_files"]
    )
    assert (
        html_plan["preflight_validation_requirements"]
        == cli_plan["preflight_validation_requirements"]
    )
    assert (
        html_plan["preflight_validation_capture_commands"]
        == cli_plan["preflight_validation_capture_commands"]
    )
    assert html_plan["must_capture"] == cli_plan["must_capture"]
    assert html_plan["rejected_substitutes"] == cli_plan["rejected_substitutes"]
    assert (
        html_plan["proof_linkage_requirements"]
        == cli_plan["proof_linkage_requirements"]
    )
    assert (
        html_plan["post_capture_validation_checks"]
        == cli_plan["post_capture_validation_checks"]
    )
    assert (
        html_plan["failure_recording_requirements"]
        == cli_plan["failure_recording_requirements"]
    )
    assert (
        html_plan["success_recording_requirements"]
        == cli_plan["success_recording_requirements"]
    )
    assert html_plan["proof_artifact_schema"] == cli_plan["proof_artifact_schema"]
    assert html_plan["record_proof_in"] == cli_plan["record_proof_in"]
    assert html_plan["unblock_when"] == cli_plan["unblock_when"]
    if "manual_capture_steps" in cli_plan:
        assert html_plan["manual_capture_steps"] == cli_plan[
            "manual_capture_steps"
        ]


def _assert_propagated_proof_plan_matches_source(boundary_plan, source_plan):
    assert boundary_plan["status"] == source_plan["status"]
    assert boundary_plan["blocking_reasons"] == source_plan["blocking_reasons"]
    assert boundary_plan["credential_state"] == source_plan["credential_state"]
    assert (
        boundary_plan["credential_setup_requirements"]
        == source_plan["credential_setup_requirements"]
    )
    assert (
        boundary_plan["credential_setup_commands"]
        == source_plan["credential_setup_commands"]
    )
    assert boundary_plan["operator_sequence"] == source_plan["operator_sequence"]
    assert boundary_plan["workspace_commands"] == source_plan["workspace_commands"]
    assert (
        boundary_plan["workspace_validation_commands"]
        == source_plan["workspace_validation_commands"]
    )
    assert (
        boundary_plan["workspace_validation_report_files"]
        == source_plan["workspace_validation_report_files"]
    )
    assert (
        boundary_plan["workspace_validation_capture_commands"]
        == source_plan["workspace_validation_capture_commands"]
    )
    assert (
        boundary_plan["workspace_expected_files"]
        == source_plan["workspace_expected_files"]
    )
    assert boundary_plan["attempt_gate"] == source_plan["attempt_gate"]
    assert boundary_plan["configured_inputs"] == source_plan["configured_inputs"]
    assert (
        boundary_plan["configured_file_inputs"]
        == source_plan["configured_file_inputs"]
    )
    assert (
        boundary_plan["configured_local_provider_inputs"]
        == source_plan["configured_local_provider_inputs"]
    )
    assert (
        boundary_plan["local_provider_config_loaded"]
        == source_plan["local_provider_config_loaded"]
    )
    assert boundary_plan["secret_files_loaded"] == source_plan["secret_files_loaded"]
    assert (
        boundary_plan["runtime_proof_required"]
        == source_plan["runtime_proof_required"]
    )
    assert boundary_plan["run_id_state"] == source_plan["run_id_state"]
    assert (
        boundary_plan["product_run_id_state"]
        == source_plan["product_run_id_state"]
    )
    assert (
        boundary_plan["run_id_required_before_execution"]
        == source_plan["run_id_required_before_execution"]
    )
    assert boundary_plan["command_run_id"] == source_plan["command_run_id"]
    assert boundary_plan["commands"] == source_plan["commands"]
    assert boundary_plan["template_commands"] == source_plan["template_commands"]
    assert boundary_plan["record_commands"] == source_plan["record_commands"]
    assert (
        boundary_plan["completion_status_commands"]
        == source_plan["completion_status_commands"]
    )
    assert boundary_plan["closeout_commands"] == source_plan["closeout_commands"]
    assert boundary_plan["preflight_checks"] == source_plan["preflight_checks"]
    assert boundary_plan["preflight_commands"] == source_plan["preflight_commands"]
    assert (
        boundary_plan["preflight_output_files"]
        == source_plan["preflight_output_files"]
    )
    assert (
        boundary_plan["preflight_capture_commands"]
        == source_plan["preflight_capture_commands"]
    )
    assert (
        boundary_plan["proof_capture_commands_after_unblock"]
        == source_plan["proof_capture_commands_after_unblock"]
    )
    assert (
        boundary_plan["operator_proof_packet"]
        == source_plan["operator_proof_packet"]
    )
    assert (
        boundary_plan["preflight_artifact_id_fields"]
        == source_plan["preflight_artifact_id_fields"]
    )
    assert (
        boundary_plan["preflight_validation_commands"]
        == source_plan["preflight_validation_commands"]
    )
    assert (
        boundary_plan["preflight_validation_report_files"]
        == source_plan["preflight_validation_report_files"]
    )
    assert (
        boundary_plan["preflight_validation_requirements"]
        == source_plan["preflight_validation_requirements"]
    )
    assert (
        boundary_plan["preflight_validation_capture_commands"]
        == source_plan["preflight_validation_capture_commands"]
    )
    assert boundary_plan["must_capture"] == source_plan["must_capture"]
    assert (
        boundary_plan["rejected_substitutes"]
        == source_plan["rejected_substitutes"]
    )
    assert (
        boundary_plan["proof_linkage_requirements"]
        == source_plan["proof_linkage_requirements"]
    )
    assert (
        boundary_plan["post_capture_validation_checks"]
        == source_plan["post_capture_validation_checks"]
    )
    assert (
        boundary_plan["failure_recording_requirements"]
        == source_plan["failure_recording_requirements"]
    )
    assert (
        boundary_plan["success_recording_requirements"]
        == source_plan["success_recording_requirements"]
    )
    assert (
        boundary_plan["proof_artifact_schema"]
        == source_plan["proof_artifact_schema"]
    )
    assert boundary_plan["record_proof_in"] == source_plan["record_proof_in"]
    assert boundary_plan["unblock_when"] == source_plan["unblock_when"]
    if "manual_capture_steps" in source_plan:
        assert boundary_plan["manual_capture_steps"] == source_plan[
            "manual_capture_steps"
        ]


def test_blocker_credential_snapshots_keep_source_attribution_across_exports():
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
            voice_source = _export_json(page, "#readiness-export")["blockers"][0][
                "credential_snapshot"
            ]

            _open(
                page,
                "social_media_optimiser/02-research/openrouter-livekit-voice-boundary-map.html",
            )
            page.get_by_role("button", name="Proof gate").click()
            voice_boundary = _export_json(page, "#boundary-export")["routes"][0][
                "credential_snapshot"
            ]
            _assert_propagated_snapshot_matches_source(voice_boundary, voice_source)

            _open(
                page,
                "social_media_optimiser/01-work-tracking/"
                "agent-studio-proof-readiness.html",
            )
            page.get_by_role("button", name="Publication").click()
            publication_source = _export_json(page, "#readiness-export")["blockers"][
                0
            ]["credential_snapshot"]

            _open(
                page,
                "social_media_optimiser/03-review-packets/"
                "agent-studio-publication-boundary-map.html",
            )
            page.get_by_role("button", name="External proof").click()
            publication_boundary = _export_json(page, "#publication-export")["routes"][
                0
            ]["credential_snapshot"]
            _assert_propagated_snapshot_matches_source(
                publication_boundary, publication_source
            )
        finally:
            browser.close()


def test_static_operator_packets_use_current_matrix_checked_at():
    expected_checked_at = _current_blocker_matrix_checked_at()

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
            voice_blocker = _export_json(page, "#readiness-export")["blockers"][0]
            assert (
                voice_blocker["credential_snapshot"]["checked_at"]
                == expected_checked_at
            )
            assert (
                voice_blocker["operator_proof_packet"]["operator_input_readiness"][
                    "checked_at"
                ]
                == expected_checked_at
            )

            page.get_by_role("button", name="Publication").click()
            publication_blocker = _export_json(page, "#readiness-export")["blockers"][
                0
            ]
            assert (
                publication_blocker["credential_snapshot"]["checked_at"]
                == expected_checked_at
            )
            assert (
                publication_blocker["operator_proof_packet"][
                    "operator_input_readiness"
                ]["checked_at"]
                == expected_checked_at
            )

            _open(
                page,
                "social_media_optimiser/02-research/openrouter-livekit-voice-boundary-map.html",
            )
            page.get_by_role("button", name="Proof gate").click()
            voice_route = _export_json(page, "#boundary-export")["routes"][0]
            assert (
                voice_route["credential_snapshot"]["checked_at"]
                == expected_checked_at
            )
            assert (
                voice_route["operator_proof_packet"]["operator_input_readiness"][
                    "checked_at"
                ]
                == expected_checked_at
            )

            _open(
                page,
                "social_media_optimiser/03-review-packets/"
                "agent-studio-publication-boundary-map.html",
            )
            page.get_by_role("button", name="External proof").click()
            publication_route = _export_json(page, "#publication-export")["routes"][0]
            assert (
                publication_route["credential_snapshot"]["checked_at"]
                == expected_checked_at
            )
            assert (
                publication_route["operator_proof_packet"]["operator_input_readiness"][
                    "checked_at"
                ]
                == expected_checked_at
            )
        finally:
            browser.close()


def test_static_operator_packets_match_current_matrix_contracts():
    matrix_packets = {
        proof_id: _normalize_current_matrix_run_id(packet)
        for proof_id, packet in _current_operator_packets().items()
    }

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
            voice_blocker = _export_json(page, "#readiness-export")["blockers"][0]
            assert (
                _normalize_current_matrix_run_id(voice_blocker["operator_proof_packet"])
                == matrix_packets["provider-backed-live-voice-proof"]
            )

            page.get_by_role("button", name="Publication").click()
            publication_blocker = _export_json(page, "#readiness-export")[
                "blockers"
            ][0]
            assert (
                _normalize_current_matrix_run_id(
                    publication_blocker["operator_proof_packet"]
                )
                == matrix_packets["external-publication-proof"]
            )

            _open(
                page,
                "social_media_optimiser/02-research/openrouter-livekit-voice-boundary-map.html",
            )
            page.get_by_role("button", name="Proof gate").click()
            voice_route = _export_json(page, "#boundary-export")["routes"][0]
            assert (
                _normalize_current_matrix_run_id(voice_route["operator_proof_packet"])
                == matrix_packets["provider-backed-live-voice-proof"]
            )

            _open(
                page,
                "social_media_optimiser/03-review-packets/"
                "agent-studio-publication-boundary-map.html",
            )
            page.get_by_role("button", name="External proof").click()
            publication_route = _export_json(page, "#publication-export")["routes"][0]
            assert (
                _normalize_current_matrix_run_id(
                    publication_route["operator_proof_packet"]
                )
                == matrix_packets["external-publication-proof"]
            )
        finally:
            browser.close()


def test_static_embedded_operator_packets_match_current_matrix_without_browser():
    matrix_packets = {
        proof_id: _normalize_current_matrix_run_id(packet)
        for proof_id, packet in _current_operator_packets().items()
    }

    proof_readiness_packets = _static_operator_packets(
        "social_media_optimiser/01-work-tracking/"
        "agent-studio-proof-readiness.html",
        "blockers",
    )
    voice_boundary_packets = _static_operator_packets(
        "social_media_optimiser/02-research/openrouter-livekit-voice-boundary-map.html",
        "routes",
    )
    publication_boundary_packets = _static_operator_packets(
        "social_media_optimiser/03-review-packets/"
        "agent-studio-publication-boundary-map.html",
        "routes",
    )

    assert (
        proof_readiness_packets["provider-backed-live-voice-proof"]
        == matrix_packets["provider-backed-live-voice-proof"]
    )
    assert (
        proof_readiness_packets["external-publication-proof"]
        == matrix_packets["external-publication-proof"]
    )
    assert (
        voice_boundary_packets["provider-backed-live-voice-proof"]
        == matrix_packets["provider-backed-live-voice-proof"]
    )
    assert (
        publication_boundary_packets["external-publication-proof"]
        == matrix_packets["external-publication-proof"]
    )


def test_proof_plan_propagates_from_readiness_to_boundary_maps():
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
            voice_source = _export_json(page, "#readiness-export")["blockers"][0][
                "proof_plan"
            ]

            _open(
                page,
                "social_media_optimiser/02-research/openrouter-livekit-voice-boundary-map.html",
            )
            page.get_by_role("button", name="Proof gate").click()
            voice_boundary = _export_json(page, "#boundary-export")["routes"][0][
                "proof_plan"
            ]
            _assert_propagated_proof_plan_matches_source(
                voice_boundary,
                voice_source,
            )

            _open(
                page,
                "social_media_optimiser/01-work-tracking/"
                "agent-studio-proof-readiness.html",
            )
            page.get_by_role("button", name="Publication").click()
            publication_source = _export_json(page, "#readiness-export")[
                "blockers"
            ][0]["proof_plan"]

            _open(
                page,
                "social_media_optimiser/03-review-packets/"
                "agent-studio-publication-boundary-map.html",
            )
            page.get_by_role("button", name="External proof").click()
            publication_boundary = _export_json(page, "#publication-export")[
                "routes"
            ][0]["proof_plan"]
            _assert_propagated_proof_plan_matches_source(
                publication_boundary,
                publication_source,
            )
        finally:
            browser.close()


def test_proof_readiness_exports_match_no_secret_cli_provider_proof_plan():
    current_plans = _current_proof_plans()

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
            voice_source = _export_json(page, "#readiness-export")["blockers"][0]
            _assert_proof_plan_matches_cli(
                voice_source["proof_plan"],
                current_plans["provider-backed-live-voice-proof"],
            )

            page.get_by_role("button", name="Publication").click()
            publication_source = _export_json(page, "#readiness-export")[
                "blockers"
            ][0]
            _assert_proof_plan_matches_cli(
                publication_source["proof_plan"],
                current_plans["external-publication-proof"],
            )
        finally:
            browser.close()


def test_proof_readiness_snapshots_match_no_secret_cli_classifier():
    current_snapshots = _current_credential_snapshots()

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
            voice_source = _export_json(page, "#readiness-export")["blockers"][0][
                "credential_snapshot"
            ]
            _assert_snapshot_matches_cli(
                voice_source,
                current_snapshots["provider-backed-live-voice-proof"],
            )

            page.get_by_role("button", name="Publication").click()
            publication_source = _export_json(page, "#readiness-export")["blockers"][
                0
            ]["credential_snapshot"]
            _assert_snapshot_matches_cli(
                publication_source,
                current_snapshots["external-publication-proof"],
            )
        finally:
            browser.close()
