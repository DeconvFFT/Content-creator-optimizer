import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def test_work_tracker_advances_status_and_exports_packet():
    tracker_path = (
        ROOT / "social_media_optimiser/01-work-tracking/agent-studio-work-tracker.html"
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(tracker_path.as_uri())
            page.evaluate("localStorage.clear()")
            page.reload()

            expect(page.locator("#items .item")).to_have_count(8)
            cockpit_item = page.locator("#items .item").filter(
                has_text="Functional Content Studio Cockpit"
            )
            expect(cockpit_item).to_have_attribute("data-status", "in_progress")
            expect(cockpit_item).to_contain_text("Lead UI/UX Designer")

            cockpit_item.get_by_role("button", name="Advance status").click()

            expect(cockpit_item).to_have_attribute("data-status", "blocked")
            export_payload = json.loads(page.locator("#export-box").input_value())
            exported_cockpit = next(
                item for item in export_payload["items"] if item["id"] == "cockpit-usable"
            )
            assert export_payload["artifact"] == "agent-studio-work-tracker"
            assert exported_cockpit["status"] == "blocked"
            assert (
                export_payload["requested_action"]
                == "Use this tracker as the active planning state for the next implementation slice."
            )
        finally:
            browser.close()
