import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def _open(page, relative_path):
    page.goto((ROOT / relative_path).as_uri())


def _json(page, selector):
    return json.loads(page.locator(selector).input_value())


def test_live_voice_acceptance_gate_is_preserved_across_blocker_exports():
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
            expect(page.locator("#blocker-detail")).to_contain_text("Acceptance gate")
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Credential presence is not proof"
            )
            readiness_gate = _json(page, "#readiness-export")["blockers"][0][
                "proof_acceptance_gate"
            ]
            assert readiness_gate["requires_runtime_proof"] is True
            assert readiness_gate["credential_presence_is_not_proof"] is True
            assert readiness_gate["same_session_required"] is True
            assert "HF router text/chat completion" in readiness_gate[
                "rejected_substitutes"
            ]
            assert "transcript rehearsal or local-only dry run" in readiness_gate[
                "rejected_substitutes"
            ]
            assert "credential existence without live calls" in readiness_gate[
                "rejected_substitutes"
            ]
            assert "provider-smoke ledger with execute_live_calls=true" in readiness_gate[
                "accepted_evidence"
            ]

            _open(
                page,
                "social_media_optimiser/02-research/openrouter-livekit-voice-boundary-map.html",
            )
            page.get_by_role("button", name="Proof gate").click()
            expect(page.locator("#route-detail")).to_contain_text("Acceptance gate")
            boundary_gate = _json(page, "#boundary-export")["routes"][0][
                "proof_acceptance_gate"
            ]
            assert boundary_gate == readiness_gate
        finally:
            browser.close()


def test_publication_acceptance_gate_is_preserved_across_blocker_exports():
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
            expect(page.locator("#blocker-detail")).to_contain_text("Acceptance gate")
            expect(page.locator("#blocker-detail")).to_contain_text(
                "Credential presence is not proof"
            )
            readiness_gate = _json(page, "#readiness-export")["blockers"][0][
                "proof_acceptance_gate"
            ]
            assert readiness_gate["requires_runtime_proof"] is True
            assert readiness_gate["credential_presence_is_not_proof"] is True
            assert readiness_gate["exact_destination_required"] is True
            assert "non-live channel smoke" in readiness_gate["rejected_substitutes"]
            assert "local draft preview or generated artifact only" in readiness_gate[
                "rejected_substitutes"
            ]
            assert "credential existence without destination proof" in readiness_gate[
                "rejected_substitutes"
            ]
            assert "durable platform ID or URL" in readiness_gate["accepted_evidence"]

            _open(
                page,
                "social_media_optimiser/03-review-packets/"
                "agent-studio-publication-boundary-map.html",
            )
            page.get_by_role("button", name="External proof").click()
            expect(page.locator("#publication-detail")).to_contain_text(
                "Acceptance gate"
            )
            boundary_gate = _json(page, "#publication-export")["routes"][0][
                "proof_acceptance_gate"
            ]
            assert boundary_gate == readiness_gate
        finally:
            browser.close()
