from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def test_retrieval_research_filters_cards_by_research_area():
    research_path = (
        ROOT / "social_media_optimiser/02-research/retrieval-quality-research.html"
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(research_path.as_uri())

            expect(page.locator(".card:not(.hidden)")).to_have_count(10)
            expect(page.locator("#research-count")).to_have_text("10 shown")

            page.get_by_role("button", name="Graph").click()

            expect(page.locator(".card:not(.hidden)")).to_have_count(2)
            expect(page.locator(".card[data-kind='graph']:not(.hidden)")).to_have_count(
                2
            )
            expect(page.locator(".card[data-kind='retrieval']:not(.hidden)")).to_have_count(
                0
            )
            expect(page.locator("#research-count")).to_have_text("2 shown")
            expect(page.locator("#filter-summary")).to_contain_text("Graph")
            expect(page.locator("main")).to_contain_text("Build Evidence Graph")
            expect(page.locator("main")).to_contain_text(
                "GraphRAG for multi-hop and corpus-level questions"
            )
        finally:
            browser.close()
