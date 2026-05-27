import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def test_agent_studio_proof_readiness_filters_live_voice_and_exports_blockers():
    readiness_path = (
        ROOT / "social_media_optimiser/01-work-tracking/agent-studio-proof-readiness.html"
    )
    run_id = "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(readiness_path.as_uri())

            expect(page.locator("h1")).to_have_text("Agent Studio Proof Readiness")
            expect(page.locator("body")).to_contain_text("Planning memory only")
            expect(page.locator("#blocker-count")).to_have_text("2 blockers")

            page.get_by_role("button", name="Live voice").click()
            expect(page.locator("[data-blocker-card]:visible")).to_have_count(1)
            expect(page.locator("#blocker-count")).to_have_text("1 blocker")
            expect(page.locator("#blocker-detail")).to_contain_text(
                "provider-backed-live-voice-proof"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                f"build-provider-smoke-ledger --run-id {run_id} --live "
                "--realtime-provider openrouter_livekit --skip-gemma --skip-web-search"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                f"record-provider-proof-blocker-state-update --run-id {run_id}"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "preflight-ready"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "blocked_by_latest_failed_proof_record"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Credential setup"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "OPENROUTER_API_KEY_FILE or OPENROUTER_API_KEY"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Operator sequence"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "create or select durable product run UUID"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                f"init-provider-proof-workspace --run-id {run_id}"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "provider-backed-live-voice-proof.template.json"
            )
            expect(page.locator("#blocker-detail")).to_contain_text("README.md")
            expect(page.locator("#blocker-detail")).to_contain_text(
                "OPENROUTER_LIVEKIT_URL"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "OPENROUTER_API_KEY_FILE"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "LIVEKIT_API_KEY_FILE or LIVEKIT_API_KEY"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "LIVEKIT_API_SECRET_FILE or LIVEKIT_API_SECRET"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "provider-smoke ledger"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "realtime_voice_timing_ledger"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "participant identity"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Credential snapshot"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "placeholder-only"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "LIVEKIT_URL absent"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "No secret values printed"
            )
            expect(page.locator("#blocker-detail")).to_contain_text("blocked")
            live_voice_detail = page.locator("#blocker-detail").inner_text()
            assert live_voice_detail.count("Proof capture commands after unblock") == 2
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Proof record schema"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "provider_backed_live_voice_proof_record"
            )
            assert "validate-provider-proof-record --proof provider-backed-live-voice-proof" in (
                live_voice_detail
            )

            export_payload = json.loads(page.locator("#readiness-export").input_value())
            assert export_payload["artifact"] == "agent-studio-proof-readiness"
            assert export_payload["source"] == (
                "social_media_optimiser/01-work-tracking/"
                "agent-studio-proof-readiness.html"
            )
            assert [blocker["id"] for blocker in export_payload["blockers"]] == [
                "provider-backed-live-voice-proof"
            ]
            assert export_payload["blockers"][0]["status"] == "preflight-ready"
            voice_packet = export_payload["blockers"][0]["operator_proof_packet"]
            assert voice_packet["proof_record_schema"]["artifact_type"] == (
                "provider_backed_live_voice_proof_record"
            )
            assert voice_packet["proof_record_schema"]["allowed_outcomes"] == [
                "accepted",
                "failed",
            ]
            assert voice_packet["proof_record_schema"]["state_field"] == (
                "provider-backed-live-voice-proof"
            )
            assert (
                "voice_agent_process_start_artifact_id"
                in voice_packet["proof_record_required_fields"]
            )
            assert voice_packet["current_gate"]["completion_next_action_commands"][
                -1
            ] == (
                "uv run all-about-llms-admin provider-proof-completion-status "
                f"--run-id {run_id} --output-dir "
                f"social_media_optimiser/output/provider-proof/{run_id}"
            )
            assert "OpenRouter live-dialogue reasoning check" in export_payload[
                "blockers"
            ][0]["required_evidence"]
            assert "provider smoke and realtime timing ledgers" in export_payload[
                "blockers"
            ][0]["required_evidence"]
            assert (
                "LiveKit room/session evidence"
                in export_payload["blockers"][0]["required_evidence"]
            )
            snapshot = export_payload["blockers"][0]["credential_snapshot"]
            assert export_payload["blockers"][0]["proof_plan"][
                "blocking_reasons"
            ] == []
            assert export_payload["blockers"][0]["proof_plan"][
                "credential_setup_requirements"
            ] == [
                "configure OPENROUTER_API_KEY_FILE or OPENROUTER_API_KEY",
                "configure OPENROUTER_LIVEKIT_URL",
                "configure LIVEKIT_API_KEY_FILE or LIVEKIT_API_KEY",
                "configure LIVEKIT_API_SECRET_FILE or LIVEKIT_API_SECRET",
            ]
            assert (
                "rerun provider-proof-completion-status after both proofs are recorded"
                in export_payload["blockers"][0]["proof_plan"]["operator_sequence"]
            )
            bootstrap = export_payload["blockers"][0]["proof_plan"][
                "product_run_bootstrap"
            ]
            assert bootstrap["api_path"] == "POST /api/runs"
            assert bootstrap["output_file"].endswith("product-run.create.json")
            assert "provider_proof_closeout" in bootstrap["commands"][1]
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Product run bootstrap"
            )
            assert export_payload["blockers"][0]["proof_plan"][
                "workspace_commands"
            ] == [
                (
                    "uv run all-about-llms-admin init-provider-proof-workspace "
                    f"--run-id {run_id} --output-dir "
                    f"social_media_optimiser/output/provider-proof/{run_id}"
                )
            ]
            assert export_payload["blockers"][0]["proof_plan"][
                "workspace_expected_files"
            ][0].endswith("provider-backed-live-voice-proof.template.json")
            assert export_payload["blockers"][0]["proof_plan"][
                "preflight_commands"
            ] == [
                f"curl -sS http://127.0.0.1:8000/api/runs/{run_id}",
                "curl -sS http://127.0.0.1:8000/api/provider-readiness",
                (
                    "curl -sS "
                    "'http://127.0.0.1:8000/api/voice-runtime-readiness?"
                    "preflight_gemma=true&preflight_tts=true&"
                    "preflight_livekit=true&preflight_edge=true&preflight_agent=true'"
                ),
            ]
            assert export_payload["blockers"][0]["proof_plan"][
                "preflight_output_files"
            ][1].endswith("provider-readiness.preflight.json")
            assert export_payload["blockers"][0]["proof_plan"][
                "preflight_capture_commands"
            ][1].startswith("curl -sS -o ")
            assert snapshot["source"] == "non-secret local classifier"
            assert snapshot["secret_values_printed"] is False
            assert snapshot["placeholder_only_inputs"] == []
            assert snapshot["configured_inputs"] == ["OPENROUTER_LIVEKIT_URL"]
            assert snapshot["configured_file_inputs"] == [
                "OPENROUTER_API_KEY_FILE",
                "LIVEKIT_API_KEY_FILE",
                "LIVEKIT_API_SECRET_FILE",
            ]
            assert "LIVEKIT_URL" in snapshot["absent_inputs"]
        finally:
            browser.close()


def test_agent_studio_proof_readiness_filters_publication_blocker():
    readiness_path = (
        ROOT / "social_media_optimiser/01-work-tracking/agent-studio-proof-readiness.html"
    )
    run_id = "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(readiness_path.as_uri())

            page.get_by_role("button", name="Publication").click()
            expect(page.locator("[data-blocker-card]:visible")).to_have_count(1)
            expect(page.locator("#blocker-detail")).to_contain_text(
                "external-publication-proof"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                f"POST /api/runs/{run_id}/publish-readiness"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                f"build-distribution-package --run-id {run_id}"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                f"provider-proof-closure-review-status --run-id {run_id}"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "runtime_configuration_present_unverified"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Credential setup"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Operator sequence"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                f"init-provider-proof-workspace --run-id {run_id}"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "external-publication-proof.template.json"
            )
            expect(page.locator("#blocker-detail")).not_to_contain_text(
                "LINKEDIN_ACCESS_TOKEN"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "channel policy acknowledgement"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "durable platform ID or URL"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "rollback, delete, private, or correction path"
            )
            publication_detail = page.locator("#blocker-detail").inner_text()
            credential_setup_block = publication_detail.split(
                "Credential setup",
                1,
            )[1].split("Operator sequence", 1)[0]
            assert "provide durable manual publication evidence" in credential_setup_block
            assert "LINKEDIN_ACCESS_TOKEN" not in credential_setup_block
            assert "INSTAGRAM_ACCESS_TOKEN" not in credential_setup_block
            assert "X_ACCESS_TOKEN" not in credential_setup_block
            assert "SUBSTACK_API_TOKEN" not in credential_setup_block
            assert publication_detail.count("Proof capture commands after unblock") == 2
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Proof record schema"
            )
            expect(page.locator("#blocker-detail")).to_contain_text(
                "external_publication_proof_record"
            )
            assert "validate-provider-proof-record --proof external-publication-proof" in (
                publication_detail
            )

            export_payload = json.loads(page.locator("#readiness-export").input_value())
            publication_packet = export_payload["blockers"][0]["operator_proof_packet"]
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
            assert export_payload["blockers"][0]["proof_plan"][
                "blocking_reasons"
            ] == []
            assert export_payload["blockers"][0]["proof_plan"][
                "credential_setup_requirements"
            ] == [
                "provide durable manual publication evidence",
            ]
            assert (
                "complete closure review, then record blocker-state update only after approved review"
                in export_payload["blockers"][0]["proof_plan"]["operator_sequence"]
            )
            bootstrap = export_payload["blockers"][0]["proof_plan"][
                "product_run_bootstrap"
            ]
            assert bootstrap["api_path"] == "POST /api/runs"
            assert bootstrap["created_run_id_field"] == "run_id"
            assert "product-run.create.json" in bootstrap["commands"][2]
            assert export_payload["blockers"][0]["proof_plan"][
                "preflight_commands"
            ] == [
                f"curl -sS http://127.0.0.1:8000/api/runs/{run_id}",
                (
                    "curl -sS -X POST "
                    f"http://127.0.0.1:8000/api/runs/{run_id}/publish-readiness "
                    "-H 'Content-Type: application/json' "
                    "--data "
                    "'{\"open_feedback_gate\":false,"
                    "\"mark_run_completed_if_ready\":false,"
                    "\"check_publish_channel_readiness\":true,"
                    "\"acknowledge_publish_channel_policy\":false}'"
                )
            ]
            assert export_payload["blockers"][0]["proof_plan"][
                "preflight_output_files"
            ] == [
                (
                    f"social_media_optimiser/output/provider-proof/{run_id}/"
                    "product-run.preflight.json"
                ),
                (
                    f"social_media_optimiser/output/provider-proof/{run_id}/"
                    "publish-readiness.preflight.json"
                )
            ]
            assert export_payload["blockers"][0]["proof_plan"][
                "preflight_capture_commands"
            ][1].startswith("curl -sS -X POST -o ")
            distribution_capture_command = (
                "uv run all-about-llms-admin build-distribution-package "
                f"--run-id {run_id} > social_media_optimiser/output/provider-proof/"
                f"{run_id}/distribution-package.json"
            )
            assert distribution_capture_command in export_payload["blockers"][0][
                "proof_plan"
            ]["proof_capture_commands_after_unblock"]
            assert distribution_capture_command in publication_packet[
                "proof_capture_commands_after_unblock"
            ]
            snapshot = export_payload["blockers"][0]["credential_snapshot"]
            assert snapshot["source"] == "non-secret local classifier"
            assert snapshot["secret_values_printed"] is False
            assert snapshot["placeholder_only_inputs"] == []
        finally:
            browser.close()
