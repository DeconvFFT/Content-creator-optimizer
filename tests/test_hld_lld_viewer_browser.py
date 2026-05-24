import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def test_hld_lld_viewer_comment_export_packet():
    viewer_path = (
        ROOT / "social_media_optimiser/00-system-design/agent-studio-hld-lld.html"
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(viewer_path.as_uri())
            page.evaluate("localStorage.clear()")
            page.reload()

            page.get_by_role("button", name="Comments and Decisions").click()
            page.locator("#comment-target").select_option("Retrieval")
            page.locator("#comment-priority").select_option("high")
            page.locator("#comment-author").fill("Codex Browser Proof")
            page.locator("#comment-body").fill(
                "Route retrieval design feedback to the Retrieval Intelligence Agent."
            )
            page.get_by_role("button", name="Save comment").click()

            expect(page.locator("#comment-list .record")).to_have_count(1)
            expect(page.locator("#comment-list")).to_contain_text(
                "Retrieval Intelligence Agent"
            )

            export_payload = json.loads(page.locator("#comment-export").input_value())
            assert export_payload["artifact"] == "agent-studio-hld-lld"
            assert export_payload["source"] == "Obsidian vault interactive HTML"
            assert (
                export_payload["requested_action"]
                == "Route comments to the right design or implementation agent."
            )
            assert export_payload["comments"][0]["target"] == "Retrieval"
            assert export_payload["comments"][0]["priority"] == "high"
            assert export_payload["comments"][0]["author"] == "Codex Browser Proof"
        finally:
            browser.close()
