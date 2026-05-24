from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def test_memory_os_viewer_filter_promotes_visible_tier_detail():
    viewer_path = (
        ROOT / "social_media_optimiser/output/viewers/agent-studio-memory-os-viewer.html"
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(viewer_path.as_uri())

            expect(page.locator("#tier-track .tier")).to_have_count(3)
            expect(page.locator("#detail-title")).to_have_text("Raw Memory")

            page.locator("#search").fill("generated deliverables")

            expect(page.locator("#tier-track .tier")).to_have_count(1)
            expect(page.locator("#tier-track .tier")).to_contain_text("Output Memory")
            expect(page.locator("#detail-title")).to_have_text("Output Memory")
            expect(page.locator("#detail")).to_contain_text(
                "What did we generate from the current memory?"
            )
        finally:
            browser.close()
