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
                "POST /api/runs/<run-id>/publish-readiness"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "build-distribution-package --run-id <run-id>"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "record-provider-proof-blocker-state-update --run-id <run-id>"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "run_id_not_concrete"
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
                "init-provider-proof-workspace --run-id <run-id>"
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
                "INSTAGRAM_ACCESS_TOKEN"
            )
            expect(page.locator("#publication-detail")).to_contain_text(
                "SUBSTACK_API_TOKEN"
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
            ] == [
                "run_id_not_concrete",
                "blocked_by_placeholder_only_configuration",
            ]
            assert export_payload["routes"][0]["proof_plan"][
                "credential_setup_requirements"
            ] == [
                "configure INSTAGRAM_ACCESS_TOKEN_FILE or INSTAGRAM_ACCESS_TOKEN",
                "configure LINKEDIN_ACCESS_TOKEN_FILE or LINKEDIN_ACCESS_TOKEN",
                "configure X_ACCESS_TOKEN_FILE or X_ACCESS_TOKEN or X_API_KEY_FILE or X_API_KEY",
                "configure SUBSTACK_API_TOKEN_FILE or SUBSTACK_API_TOKEN",
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
            assert export_payload["routes"][0]["proof_plan"][
                "workspace_commands"
            ] == [
                (
                    "uv run all-about-llms-admin init-provider-proof-workspace "
                    "--run-id <run-id> --output-dir "
                    "social_media_optimiser/output/provider-proof/<run-id>"
                )
            ]
            assert export_payload["routes"][0]["proof_plan"][
                "workspace_expected_files"
            ][1].endswith("external-publication-proof.template.json")
            assert export_payload["routes"][0]["proof_plan"][
                "preflight_commands"
            ] == [
                "curl -sS 'http://127.0.0.1:8000/api/runs/<run-id>'",
                (
                    "curl -sS -X POST "
                    "'http://127.0.0.1:8000/api/runs/<run-id>/publish-readiness' "
                    "-H 'Content-Type: application/json' "
                    "--data "
                    "'{\"open_feedback_gate\":false,"
                    "\"mark_run_completed_if_ready\":false,"
                    "\"check_publish_channel_readiness\":true,"
                    "\"acknowledge_publish_channel_policy\":false}'"
                )
            ]
            assert export_payload["routes"][0]["proof_plan"][
                "preflight_output_files"
            ] == [
                (
                    "social_media_optimiser/output/provider-proof/<run-id>/"
                    "product-run.preflight.json"
                ),
                (
                    "social_media_optimiser/output/provider-proof/<run-id>/"
                    "publish-readiness.preflight.json"
                )
            ]
            assert export_payload["routes"][0]["proof_plan"][
                "preflight_capture_commands"
            ][1].startswith("curl -sS -X POST -o ")
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
            assert snapshot["shell_values_loaded"] is False
            assert snapshot["secret_values_printed"] is False
            assert snapshot["placeholder_only_inputs"] == [
                "INSTAGRAM_ACCESS_TOKEN",
                "LINKEDIN_ACCESS_TOKEN",
                "X_ACCESS_TOKEN",
                "X_API_KEY",
                "SUBSTACK_API_TOKEN",
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
