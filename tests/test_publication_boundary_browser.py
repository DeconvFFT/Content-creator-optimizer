import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def test_publication_boundary_filters_external_proof_and_exports_blocker():
    map_path = (
        ROOT
        / "social_media_optimiser/03-review-packets/agent-studio-publication-boundary-map.html"
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(map_path.as_uri())

            expect(page.locator("h1")).to_have_text(
                "Agent Studio Publication Boundary Map"
            )
            expect(page.locator("body")).to_contain_text("Planning memory only")
            expect(page.locator("#publication-count")).to_have_text("6 routes")

            page.get_by_role("button", name="External proof").click()
            expect(page.locator("[data-publication-card]:visible")).to_have_count(1)
            expect(page.locator("#publication-count")).to_have_text("1 route")
            expect(page.locator("#publication-detail")).to_contain_text(
                "external-publication-proof"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "POST /api/runs/"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "/publish-readiness"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "build-distribution-package --run-id"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "record-provider-proof-blocker-state-update --run-id"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "blocked_by_placeholder_only_configuration"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "Credential setup"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "Operator sequence"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "external-publication-proof.template.json"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "durable platform ID or URL"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "API response proof or manual-completion proof"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "postcondition monitoring"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "live or approved manual destination evidence"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "rollback, delete, private, or correction path"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "rollback proof"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "external publication proof remains blocked"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "LINKEDIN_ACCESS_TOKEN"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "Credential snapshot"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "placeholder-only"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "No secret values printed"
            )
            publication_detail = page.locator("#publication-detail").inner_text()
            credential_setup_block = publication_detail.split(
                "Credential setup",
                1,
            )[1].split("Operator sequence", 1)[0]
            assert "LINKEDIN_ACCESS_TOKEN" in credential_setup_block
            assert "INSTAGRAM_ACCESS_TOKEN" not in credential_setup_block
            assert "X_ACCESS_TOKEN" not in credential_setup_block
            assert "SUBSTACK_API_TOKEN" not in credential_setup_block
            assert publication_detail.count("Proof capture commands after unblock") == 2
            expect(page.locator("#publication-detail")).to_contain_text(
                "Proof record schema"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "external_publication_proof_record"
            )
            assert "validate-provider-proof-record --proof external-publication-proof" in (
                publication_detail
            )

            export_payload = json.loads(
                page.locator("#publication-export").input_value()
            )
            assert export_payload["artifact"] == (
                "agent-studio-publication-boundary-map"
            )
            assert export_payload["source"] == (
                "social_media_optimiser/03-review-packets/"
                "agent-studio-publication-boundary-map.html"
            )
            assert [route["id"] for route in export_payload["routes"]] == [
                "external-publication-proof"
            ]
            assert export_payload["routes"][0]["status"] == "blocked"
            publication_packet = export_payload["routes"][0]["operator_proof_packet"]
            assert publication_packet["proof_record_schema"]["artifact_type"] == (
                "external_publication_proof_record"
            )
            assert publication_packet["proof_record_schema"]["allowed_outcomes"] == [
                "accepted",
                "failed",
            ]
            assert publication_packet["proof_record_schema"]["state_field"] == (
                "external-publication-proof"
            )
            assert (
                "durable_platform_id_or_url"
                in publication_packet["proof_record_required_fields"]
            )
            assert export_payload["routes"][0]["proof_plan"][
                "blocking_reasons"
            ] == ["blocked_by_placeholder_only_configuration"]
            assert export_payload["routes"][0]["proof_plan"][
                "credential_setup_requirements"
            ] == [
                "configure LINKEDIN_ACCESS_TOKEN_FILE or LINKEDIN_ACCESS_TOKEN",
            ]
            assert (
                "run preflight_checks and stop if any readiness gate fails"
                in export_payload["routes"][0]["proof_plan"]["operator_sequence"]
            )
            bootstrap = export_payload["routes"][0]["proof_plan"][
                "product_run_bootstrap"
            ]
            assert bootstrap["api_path"] == "POST /api/runs"
            assert "product-run.create.json" in bootstrap["commands"][2]
            workspace_commands = export_payload["routes"][0]["proof_plan"][
                "workspace_commands"
            ]
            assert len(workspace_commands) == 1
            assert workspace_commands[0].startswith(
                "uv run all-about-llms-admin init-provider-proof-workspace --run-id "
            )
            assert (
                "--output-dir social_media_optimiser/output/provider-proof/"
                in workspace_commands[0]
            )
            assert export_payload["routes"][0]["proof_plan"][
                "workspace_expected_files"
            ][1].endswith("external-publication-proof.template.json")
            preflight_commands = export_payload["routes"][0]["proof_plan"][
                "preflight_commands"
            ]
            assert preflight_commands[0].startswith(
                "curl -sS http://127.0.0.1:8000/api/runs/"
            )
            assert "/publish-readiness" in preflight_commands[1]
            assert '"acknowledge_publish_channel_policy":false' in preflight_commands[1]
            preflight_output_files = export_payload["routes"][0]["proof_plan"][
                "preflight_output_files"
            ]
            assert preflight_output_files[0].endswith("product-run.preflight.json")
            assert preflight_output_files[1].endswith(
                "publish-readiness.preflight.json"
            )
            assert export_payload["routes"][0]["proof_plan"][
                "preflight_capture_commands"
            ][1].startswith("curl -sS -X POST -o ")
            run_id = export_payload["routes"][0]["proof_plan"]["command_run_id"]
            distribution_capture_command = (
                "uv run all-about-llms-admin build-distribution-package "
                f"--run-id {run_id} > social_media_optimiser/output/provider-proof/"
                f"{run_id}/distribution-package.json"
            )
            assert distribution_capture_command in export_payload["routes"][0][
                "proof_plan"
            ]["proof_capture_commands_after_unblock"]
            assert distribution_capture_command in publication_packet[
                "proof_capture_commands_after_unblock"
            ]
            current_gate = publication_packet["current_gate"]
            assert current_gate["latest_failed_proofs"] == [
                "external-publication-proof"
            ]
            assert all(
                "provider-backed-live-voice-proof" not in command
                for command in current_gate["completion_next_action_commands"]
            )
            assert any(
                "provider-proof-operator-input-readiness" in command
                and "--fail-on-blocked" in command
                for command in current_gate["completion_next_action_commands"]
            )
            assert all(
                "/publish-readiness" not in command
                for command in current_gate["completion_next_action_commands"]
            )
            gate_commands = current_gate["completion_next_action_commands"]
            assert gate_commands[-1] == (
                "uv run all-about-llms-admin provider-proof-completion-status "
                f"--run-id {run_id} --output-dir "
                f"social_media_optimiser/output/provider-proof/{run_id}"
            )
            strict_gate_index = next(
                index
                for index, command in enumerate(gate_commands)
                if "provider-proof-operator-input-readiness" in command
                and "--fail-on-blocked" in command
            )
            snapshot_index = next(
                index
                for index, command in enumerate(gate_commands)
                if "blocker-credential-snapshot" in command
            )
            assert strict_gate_index < snapshot_index
            assert "API response proof or manual-completion proof" in json.dumps(
                export_payload["routes"][0]
            )
            assert "postcondition monitoring" in json.dumps(
                export_payload["routes"][0]
            )
            assert "live or approved manual destination evidence" in json.dumps(
                export_payload["routes"][0]
            )
            assert "rollback proof" in json.dumps(export_payload["routes"][0])
            snapshot = export_payload["routes"][0]["credential_snapshot"]
            assert snapshot["source"] == "agent-studio-proof-readiness"
            assert snapshot["source_snapshot"] == "non-secret local classifier"
            assert snapshot["shell_values_loaded"] is False
            assert snapshot["secret_values_printed"] is False
            assert snapshot["placeholder_only_inputs"] == [
                "LINKEDIN_ACCESS_TOKEN",
            ]
        finally:
            browser.close()


def test_publication_boundary_filters_non_live_smoke_boundary():
    map_path = (
        ROOT
        / "social_media_optimiser/03-review-packets/agent-studio-publication-boundary-map.html"
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(map_path.as_uri())

            page.get_by_role("button", name="Non-live smoke").click()
            expect(page.locator("[data-publication-card]:visible")).to_have_count(1)
            expect(page.locator("#publication-detail")).to_contain_text(
                "non-live-channel-smoke"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "publish_channel_checks"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "missing_publish_channel_credentials"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "publish_channel_policy_review_required"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "not real API publish proof"
            )
        finally:
            browser.close()


def test_publication_boundary_switches_filters_without_stale_proof_context():
    map_path = (
        ROOT
        / "social_media_optimiser/03-review-packets/agent-studio-publication-boundary-map.html"
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(map_path.as_uri())

            page.get_by_role("button", name="External proof").click()
            expect(page.locator("#publication-detail")).to_contain_text(
                "external-publication-proof"
            )

            page.get_by_role("button", name="Policy review").click()
            expect(page.locator("[data-publication-card]:visible")).to_have_count(1)
            expect(page.locator("#publication-detail")).to_contain_text(
                "channel-policy-review"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "exact destination set"
            )
            expect(page.locator("#publication-detail")).not_to_contain_text(
                "external-publication-proof"
            )
            policy_export = json.loads(
                page.locator("#publication-export").input_value()
            )
            assert [route["id"] for route in policy_export["routes"]] == [
                "channel-policy-review"
            ]
            assert "external-publication-proof" not in json.dumps(policy_export)

            page.get_by_role("button", name="Rollback").click()
            expect(page.locator("#publication-detail")).to_contain_text(
                "rollback-and-correction-path"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "publish_rollback_record"
            )
            expect(page.locator("#publication-detail")).not_to_contain_text(
                "channel-policy-review"
            )
        finally:
            browser.close()
