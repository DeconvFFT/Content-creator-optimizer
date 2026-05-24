import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def test_openrouter_voice_boundary_filters_proof_gate_and_exports_current_evidence():
    map_path = (
        ROOT / "social_media_optimiser/02-research/gemma-voice-boundary-map.html"
    )
    run_id = "190ae2f9-a74b-4a23-b39c-aaf2d636bd8e"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(map_path.as_uri())

            expect(page.locator("h1")).to_have_text(
                "OpenRouter LiveKit Voice Boundary Map"
            )
            expect(page.locator("body")).to_contain_text("Planning memory only")
            expect(page.locator("#route-count")).to_have_text("8 routes")

            page.get_by_role("button", name="Proof gate").click()
            expect(page.locator("[data-route-card]:visible")).to_have_count(1)
            expect(page.locator("#route-count")).to_have_text("1 route")
            expect(page.locator("#route-detail")).to_contain_text(
                "provider-backed-live-voice-proof"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                f"build-provider-smoke-ledger --run-id {run_id} --live "
                "--realtime-provider openrouter_livekit --skip-gemma --skip-web-search"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                f"record-provider-proof-blocker-state-update --run-id {run_id}"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                "Credential setup"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                "OPENROUTER_API_KEY_FILE or OPENROUTER_API_KEY"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                "Operator sequence"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                f"init-provider-proof-workspace --run-id {run_id}"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                "provider-backed-live-voice-proof.template.json"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                "OPENROUTER_LIVEKIT_URL"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                "LIVEKIT_API_SECRET_FILE or LIVEKIT_API_SECRET"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                "realtime_voice_timing_ledger"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                "same-session OpenRouter/Kokoro/LiveKit proof is still required"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                "Credential snapshot"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                "placeholder-only"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                "LIVEKIT_URL absent"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                "No secret values printed"
            )
            route_detail = page.locator("#route-detail").inner_text()
            assert route_detail.count("Proof capture commands after unblock") == 2
            expect(page.locator("#route-detail")).to_contain_text(
                "Proof record schema"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                "provider_backed_live_voice_proof_record"
            )
            assert "validate-provider-proof-record --proof provider-backed-live-voice-proof" in (
                route_detail
            )

            export_payload = json.loads(page.locator("#boundary-export").input_value())
            assert export_payload["artifact"] == "openrouter-livekit-voice-boundary-map"
            assert export_payload["source"] == (
                "social_media_optimiser/02-research/gemma-voice-boundary-map.html"
            )
            assert [route["id"] for route in export_payload["routes"]] == [
                "provider-backed-live-voice-proof"
            ]
            assert export_payload["routes"][0]["status"] == "preflight-ready"
            voice_packet = export_payload["routes"][0]["operator_proof_packet"]
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
            assert export_payload["routes"][0]["proof_plan"][
                "blocking_reasons"
            ] == []
            assert (
                "configure OPENROUTER_API_KEY_FILE or OPENROUTER_API_KEY"
                in export_payload["routes"][0]["proof_plan"][
                    "credential_setup_requirements"
                ]
            )
            assert (
                "execute proof commands and capture must_capture evidence"
                in export_payload["routes"][0]["proof_plan"]["operator_sequence"]
            )
            bootstrap = export_payload["routes"][0]["proof_plan"][
                "product_run_bootstrap"
            ]
            assert bootstrap["api_path"] == "POST /api/runs"
            assert "provider_proof_closeout" in bootstrap["commands"][1]
            assert export_payload["routes"][0]["proof_plan"][
                "workspace_commands"
            ] == [
                (
                    "uv run all-about-llms-admin init-provider-proof-workspace "
                    f"--run-id {run_id} --output-dir "
                    f"social_media_optimiser/output/provider-proof/{run_id}"
                )
            ]
            assert export_payload["routes"][0]["proof_plan"][
                "workspace_expected_files"
            ][2].endswith("operator-inputs.template.env")
            assert export_payload["routes"][0]["proof_plan"][
                "workspace_expected_files"
            ][3].endswith("README.md")
            assert export_payload["routes"][0]["proof_plan"][
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
            assert export_payload["routes"][0]["proof_plan"][
                "preflight_output_files"
            ][2].endswith("voice-runtime-readiness.preflight.json")
            assert export_payload["routes"][0]["proof_plan"][
                "preflight_capture_commands"
            ][0].startswith("curl -sS -o ")
            snapshot = export_payload["routes"][0]["credential_snapshot"]
            assert snapshot["source"] == "agent-studio-proof-readiness"
            assert snapshot["shell_values_loaded"] is True
            assert snapshot["secret_values_printed"] is False
            assert snapshot["placeholder_only_inputs"] == []
            assert "LIVEKIT_URL" in snapshot["absent_inputs"]
        finally:
            browser.close()


def test_openrouter_voice_boundary_keeps_legacy_routes_separate():
    map_path = (
        ROOT / "social_media_optimiser/02-research/gemma-voice-boundary-map.html"
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(map_path.as_uri())

            page.get_by_role("button", name="Legacy").click()
            expect(page.locator("[data-route-card]:visible")).to_have_count(2)
            expect(page.locator("#route-detail")).to_contain_text(
                "hf-router-text-expert-route"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                "https://router.huggingface.co/v1/chat/completions"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                "google/gemma-4-31b-it"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                "not native-audio proof"
            )
        finally:
            browser.close()


def test_openrouter_voice_boundary_switches_filters_without_stale_route_context():
    map_path = (
        ROOT / "social_media_optimiser/02-research/gemma-voice-boundary-map.html"
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(map_path.as_uri())

            page.get_by_role("button", name="Proof gate").click()
            expect(page.locator("#route-detail")).to_contain_text(
                "provider-backed-live-voice-proof"
            )

            page.get_by_role("button", name="OpenRouter").click()
            expect(page.locator("[data-route-card]:visible")).to_have_count(1)
            expect(page.locator("#route-detail")).to_contain_text(
                "openrouter-deepseek-reasoning"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                "OpenRouter owns text-turn dialogue reasoning only"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                "raw microphone PCM is not sent to OpenRouter"
            )
            expect(page.locator("#route-detail")).not_to_contain_text(
                "provider-backed-live-voice-proof"
            )
            openrouter_export = json.loads(
                page.locator("#boundary-export").input_value()
            )
            assert [route["id"] for route in openrouter_export["routes"]] == [
                "openrouter-deepseek-reasoning"
            ]

            page.get_by_role("button", name="Kokoro TTS").click()
            expect(page.locator("[data-route-card]:visible")).to_have_count(1)
            expect(page.locator("#route-detail")).to_contain_text(
                "kokoro-speech-output"
            )
            expect(page.locator("#route-detail")).to_contain_text(
                "Kokoro owns speech synthesis for the current OpenRouter LiveKit path"
            )
            expect(page.locator("#route-detail")).not_to_contain_text(
                "openrouter-deepseek-reasoning"
            )
            kokoro_export = json.loads(
                page.locator("#boundary-export").input_value()
            )
            assert [route["id"] for route in kokoro_export["routes"]] == [
                "kokoro-speech-output"
            ]
            assert "provider-backed-live-voice-proof" not in json.dumps(
                kokoro_export
            )
        finally:
            browser.close()
