from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def test_system_design_vault_home_links_agent_studio_design_sources():
    home_path = ROOT / "system_design_vault/agent-studio-system-design-home.html"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(home_path.as_uri())

            expect(page.locator("h1")).to_have_text("Agent Studio System Design Vault")
            expect(page.locator("body")).to_contain_text("Planning memory only")
            expect(page.locator("body")).to_contain_text(
                "provider-backed live voice path is OpenRouter + LiveKit + Kokoro"
            )
            expect(page.get_by_role("link", name="Objective Completion Audit Mirror")).to_have_attribute(
                "href",
                "04-agent-studio-implications/agent-studio-objective-completion-audit.md",
            )
            expect(page.get_by_role("link", name="OpenRouter And Legacy Provider Sources")).to_have_attribute(
                "href",
                "01-sources/official-open/gemma4-and-realtime-sources.md",
            )
            expect(page.get_by_role("link", name="Social Publishing Governance")).to_have_attribute(
                "href",
                "01-sources/official-open/social-publishing-api-governance.md",
            )
            expect(page.get_by_role("link", name="Project Proof Readiness Surface")).to_have_attribute(
                "href",
                "../social_media_optimiser/01-work-tracking/agent-studio-proof-readiness.html",
            )
            expect(page.get_by_role("link", name="Project Work Tracker")).to_have_attribute(
                "href",
                "../social_media_optimiser/01-work-tracking/agent-studio-work-tracker.html",
            )
            expect(page.locator("body")).to_contain_text("planning board stays out of product UI")
            expect(page.get_by_role("link", name="Project A2A Map")).to_have_attribute(
                "href",
                "../social_media_optimiser/00-system-design/agent-studio-a2a-map.html",
            )
            expect(page.get_by_role("link", name="Project Skill Matrix")).to_have_attribute(
                "href",
                "../social_media_optimiser/00-system-design/agent-studio-skill-matrix.html",
            )
            expect(page.get_by_role("link", name="Project HLD/LLD Review Surface")).to_have_attribute(
                "href",
                "../social_media_optimiser/00-system-design/agent-studio-hld-lld.html",
            )
            expect(page.get_by_role("link", name="Project System Design Viewer")).to_have_attribute(
                "href",
                "../social_media_optimiser/output/viewers/agent-studio-system-design-viewer.html",
            )
            expect(page.locator("body")).to_contain_text("projection=public")
            expect(page.locator("body")).to_contain_text("agent-studio-guardrails-review")
            expect(page.locator("body")).to_contain_text("comment export")
            expect(page.locator("body")).to_contain_text("generated viewer")
            expect(page.get_by_role("link", name="Project OpenRouter LiveKit Voice Boundary Map")).to_have_attribute(
                "href",
                "../social_media_optimiser/02-research/openrouter-livekit-voice-boundary-map.html",
            )
            expect(page.get_by_role("link", name="Project Publication Boundary Map")).to_have_attribute(
                "href",
                "../social_media_optimiser/03-review-packets/agent-studio-publication-boundary-map.html",
            )
            expect(page.get_by_role("link", name="Project Feedback Loop Map")).to_have_attribute(
                "href",
                "../social_media_optimiser/03-review-packets/agent-studio-feedback-loop-map.html",
            )
            expect(page.locator("body")).to_contain_text("leibniz-review-watch-escalation")
            expect(page.locator("body")).to_contain_text("severity, files, and next action")
            expect(page.locator("body")).to_contain_text("credential snapshot exports")
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
                "../social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-proof-status.md",
            )
            expect(
                page.get_by_role("link", name="Open Current Blocker Matrix")
            ).to_have_attribute(
                "href",
                "../social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/current-blocker-matrix.json",
            )
            expect(
                page.get_by_role("link", name="Open Operator Unblocker Checklist")
            ).to_have_attribute(
                "href",
                "../social_media_optimiser/output/provider-proof/190ae2f9-a74b-4a23-b39c-aaf2d636bd8e/operator-unblocker-checklist.md",
            )
            expect(page.locator("body")).to_contain_text("secret_values_printed=false")
            expect(page.get_by_role("link", name="Production Agent Studio Canon")).to_have_attribute(
                "href",
                "03-patterns/system-design/production-agent-studio-canon.md",
            )
            expect(page.get_by_role("link", name="System Design Source Map", exact=True)).to_have_attribute(
                "href",
                "00-index/source-map.md",
            )
            expect(page.get_by_role("link", name="System Design Source Map Viewer")).to_have_attribute(
                "href",
                "output/viewers/system-design-source-map.html",
            )
            expect(page.locator("body")).to_contain_text(
                "generated source-map viewer"
            )
        finally:
            browser.close()
