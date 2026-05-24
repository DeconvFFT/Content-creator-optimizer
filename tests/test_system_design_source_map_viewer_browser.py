from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def test_system_design_source_map_viewer_renders_and_filters_records():
    viewer_path = ROOT / "system_design_vault/output/viewers/system-design-source-map.html"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(viewer_path.as_uri())

            expect(page.locator("h1")).to_have_text("Agent Studio Source Map")
            expect(page.locator("#allowed li")).to_have_count(4)
            expect(page.locator("#excluded li")).to_have_count(4)
            expect(page.locator("#groups .card")).to_have_count(11)
            expect(page.locator("#slice li")).to_have_count(40)
            expect(page.locator("#implications li")).to_have_count(126)
            expect(page.locator("#implication-count")).to_have_text("126 design implications")
            expect(page.locator("#records .record")).to_have_count(175)
            expect(page.locator("#record-count")).to_have_text("175 source records")
            expect(page.locator("#kind-filter option")).to_contain_text(
                ["official_source_note", "pattern_note"]
            )
            expect(page.locator("#granularity-filter option")).to_contain_text(
                ["chapter_note", "chapter_sweep"]
            )

            page.get_by_label("Search source records").fill("pgvector")
            expect(page.locator("#records .record")).to_have_count(1)
            expect(page.locator("#record-count")).to_have_text("1 source record")
            expect(page.locator("#records .record")).to_contain_text(
                "pgvector And Postgres Hybrid Retrieval"
            )
            expect(
                page.get_by_role(
                    "link",
                    name="01-sources/official-open/pgvector-postgres-hybrid-retrieval.md",
                )
            ).to_have_attribute(
                "href",
                "../../01-sources/official-open/pgvector-postgres-hybrid-retrieval.md",
            )

            page.get_by_label("Search source records").fill("")
            page.get_by_label("Filter by source kind").select_option("pattern_note")
            expect(page.locator("#records .record").first).to_contain_text(
                "pattern_note"
            )

            page.get_by_label("Filter by local book coverage granularity").select_option(
                "chapter_note"
            )
            page.get_by_label("Filter by source kind").select_option("")
            expect(page.locator("#records .record").first).to_contain_text(
                "chapter_note"
            )

            page.get_by_label("Search source records").fill("not-a-real-source-record")
            expect(page.locator("#records .record")).to_have_count(0)
            expect(page.locator("#record-count")).to_have_text("0 source records")
            expect(page.locator("#records")).to_contain_text(
                "No source records match the current filters."
            )

            page.get_by_label("Search design implications").fill("pgvector")
            expect(page.locator("#implications li")).to_have_count(1)
            expect(page.locator("#implication-count")).to_have_text("1 design implication")
            expect(page.locator("#implications")).to_contain_text("pgvector")

            page.get_by_label("Search design implications").fill(
                "not-a-real-implication"
            )
            expect(page.locator("#implications li")).to_have_count(0)
            expect(page.locator("#implication-count")).to_have_text(
                "0 design implications"
            )
            expect(page.locator("#implications")).to_contain_text(
                "No design implications match the current search."
            )
        finally:
            browser.close()
