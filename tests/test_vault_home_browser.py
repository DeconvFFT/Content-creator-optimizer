from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def test_vault_home_links_to_generated_knowledge_viewers():
    home_path = ROOT / "social_media_optimiser/agent-studio-vault-home.html"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(home_path.as_uri())

            page.get_by_role("link", name="Open Agent Studio Memory OS").click()
            expect(page.locator("h1")).to_have_text("Agent Studio Memory OS")
            expect(page.locator("body")).to_contain_text(
                "Obsidian-backed three-tier memory system"
            )

            page.goto(home_path.as_uri())
            page.get_by_role(
                "link", name="Open Agent Studio System Design Viewer"
            ).click()
            expect(page.locator("h1")).to_have_text("Agent Studio System Design Viewer")
            expect(page.locator("body")).to_contain_text("Objective Completion Audit")

            page.goto(home_path.as_uri())
            page.get_by_role(
                "link", name="Open System Design Source Map Viewer"
            ).click()
            expect(page.locator("h1")).to_have_text("Agent Studio Source Map")
            expect(page.locator("#record-count")).to_have_text("175 source records")
            expect(page.locator("#implication-count")).to_have_text(
                "126 design implications"
            )

            page.goto(home_path.as_uri())
            page.get_by_role("link", name="Open Agent Studio A2A Map").click()
            expect(page.locator("h1")).to_have_text("Agent Studio A2A Map")
            expect(page.locator("body")).to_contain_text(
                "public-a2a-discovery-boundary"
            )

            page.goto(home_path.as_uri())
            page.get_by_role(
                "link", name="Open OpenRouter LiveKit Voice Boundary Map"
            ).click()
            expect(page.locator("h1")).to_have_text(
                "OpenRouter LiveKit Voice Boundary Map"
            )
            expect(page.locator("body")).to_contain_text(
                "provider-backed-live-voice-proof"
            )

            page.goto(home_path.as_uri())
            page.get_by_role("link", name="Open Agent Studio Skill Matrix").click()
            expect(page.locator("h1")).to_have_text("Agent Studio Skill Matrix")
            expect(page.locator("body")).to_contain_text(
                "Agent Studio Guardrails Review"
            )

            page.goto(home_path.as_uri())
            expect(page.locator("body")).to_contain_text("proof-plan packets")
            expect(page.locator("body")).to_contain_text("proof_plan")
            expect(page.locator("body")).to_contain_text("current-proof-status.md")
            expect(page.locator("body")).to_contain_text("current-blocker-matrix.json")
            expect(page.locator("body")).to_contain_text(
                "operator-unblocker-checklist.md"
            )
            expect(
                page.get_by_role("link", name="Open Current Proof Status")
            ).to_have_attribute(
                "href",
                "output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-proof-status.md",
            )
            expect(
                page.get_by_role("link", name="Open Current Blocker Matrix")
            ).to_have_attribute(
                "href",
                "output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-blocker-matrix.json",
            )
            expect(
                page.get_by_role("link", name="Open Operator Unblocker Checklist")
            ).to_have_attribute(
                "href",
                "output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-unblocker-checklist.md",
            )
            page.get_by_role("link", name="Open Agent Studio Proof Readiness").click()
            expect(page.locator("h1")).to_have_text("Agent Studio Proof Readiness")
            expect(page.locator("body")).to_contain_text(
                "provider-backed-live-voice-proof"
            )

            page.goto(home_path.as_uri())
            page.get_by_role(
                "link", name="Open Agent Studio Publication Boundary Map"
            ).click()
            expect(page.locator("h1")).to_have_text(
                "Agent Studio Publication Boundary Map"
            )
            expect(page.locator("body")).to_contain_text(
                "external-publication-proof"
            )

            page.goto(home_path.as_uri())
            page.get_by_role(
                "link", name="Open Agent Studio Feedback Loop Map"
            ).click()
            expect(page.locator("h1")).to_have_text(
                "Agent Studio Feedback Loop Map"
            )
            expect(page.locator("body")).to_contain_text(
                "guardrails-feedback-resolution"
            )
        finally:
            browser.close()
