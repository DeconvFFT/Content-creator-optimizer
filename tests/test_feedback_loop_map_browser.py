import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def test_feedback_loop_map_filters_guardrails_and_exports_held_outcomes():
    map_path = (
        ROOT / "social_media_optimiser/03-review-packets/agent-studio-feedback-loop-map.html"
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(map_path.as_uri())

            expect(page.locator("h1")).to_have_text("Agent Studio Feedback Loop Map")
            expect(page.locator("body")).to_contain_text("Planning memory only")
            expect(page.locator("#loop-count")).to_have_text("6 loops")

            page.get_by_role("button", name="Guardrails").click()
            expect(page.locator("[data-loop-card]:visible")).to_have_count(1)
            expect(page.locator("#loop-count")).to_have_text("1 loop")
            expect(page.locator("#loop-detail")).to_contain_text(
                "guardrails-feedback-resolution"
            )
            expect(page.locator("#loop-detail")).to_contain_text(
                "feedback_resolution_ledger"
            )
            expect(page.locator("#loop-detail")).to_contain_text(
                "accepted/revised/held/rejected"
            )
            expect(page.locator("#loop-detail")).to_contain_text(
                "failed linked task ids"
            )
            expect(page.locator("#loop-detail")).to_contain_text(
                "held until retry or review"
            )

            export_payload = json.loads(page.locator("#feedback-export").input_value())
            assert export_payload["artifact"] == "agent-studio-feedback-loop-map"
            assert export_payload["source"] == (
                "social_media_optimiser/03-review-packets/"
                "agent-studio-feedback-loop-map.html"
            )
            assert [loop["id"] for loop in export_payload["loops"]] == [
                "guardrails-feedback-resolution"
            ]
            assert "held_feedback_count" in export_payload["loops"][0]["evidence"]
        finally:
            browser.close()


def test_feedback_loop_map_filters_review_watch_context():
    map_path = (
        ROOT / "social_media_optimiser/03-review-packets/agent-studio-feedback-loop-map.html"
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(map_path.as_uri())

            page.get_by_role("button", name="Review watch").click()
            expect(page.locator("[data-loop-card]:visible")).to_have_count(1)
            expect(page.locator("#loop-count")).to_have_text("1 loop")
            expect(page.locator("#loop-detail")).to_contain_text(
                "leibniz-review-watch-escalation"
            )
            expect(page.locator("#loop-detail")).to_contain_text(
                "standing reviewer 019e3899-5ab3-7171-9d3c-32e7c57bbde7"
            )
            expect(page.locator("#loop-detail")).to_contain_text(
                "Critical/Important findings"
            )
            expect(page.locator("#loop-detail")).to_contain_text(
                "severity, files, and next action"
            )
            expect(page.locator("#loop-detail")).to_contain_text(
                "Leibniz latest status: no Critical/Important findings"
            )

            export_payload = json.loads(page.locator("#feedback-export").input_value())
            assert [loop["id"] for loop in export_payload["loops"]] == [
                "leibniz-review-watch-escalation"
            ]
            assert "reviewer_agent_id" in export_payload["loops"][0]["evidence"]
            assert (
                export_payload["loops"][0]["review_watch"]["reviewer_agent_id"]
                == "019e3899-5ab3-7171-9d3c-32e7c57bbde7"
            )
            assert (
                export_payload["loops"][0]["review_watch"]["latest_status"]
                == "no Critical/Important findings"
            )
        finally:
            browser.close()


def test_feedback_loop_map_filters_publish_gate_context():
    map_path = (
        ROOT / "social_media_optimiser/03-review-packets/agent-studio-feedback-loop-map.html"
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(map_path.as_uri())

            page.get_by_role("button", name="Publish gate").click()
            expect(page.locator("[data-loop-card]:visible")).to_have_count(1)
            expect(page.locator("#loop-detail")).to_contain_text(
                "publish-readiness-feedback-gate"
            )
            expect(page.locator("#loop-detail")).to_contain_text(
                "publish_readiness_checked"
            )
            expect(page.locator("#loop-detail")).to_contain_text(
                "unsupported_claims"
            )
            expect(page.locator("#loop-detail")).to_contain_text(
                "blocked_guardrail_audit"
            )
            expect(page.locator("#loop-detail")).to_contain_text(
                "publish_channel_checks"
            )
            expect(page.locator("#loop-detail")).to_contain_text(
                "missing accepted evidence"
            )
            expect(page.locator("#loop-detail")).to_contain_text(
                "external publication proof remains blocked"
            )
        finally:
            browser.close()
