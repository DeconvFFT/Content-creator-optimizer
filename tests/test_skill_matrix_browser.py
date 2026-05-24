import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def test_agent_studio_skill_matrix_filters_and_exports_guardrails_context():
    matrix_path = (
        ROOT / "social_media_optimiser/00-system-design/agent-studio-skill-matrix.html"
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(matrix_path.as_uri())

            expect(page.locator("h1")).to_have_text("Agent Studio Skill Matrix")
            expect(page.locator("body")).to_contain_text("Planning memory only")
            expect(page.locator("#skill-count")).to_have_text("9 skills")

            page.get_by_role("button", name="Guardrails").click()
            expect(page.locator("[data-skill-card]:visible")).to_have_count(1)
            expect(page.locator("#skill-count")).to_have_text("1 skill")
            expect(page.locator("#skill-detail")).to_contain_text(
                "Agent Studio Guardrails Review"
            )
            expect(page.locator("#skill-detail")).to_contain_text(
                "feedback_resolution_ledger"
            )
            expect(page.locator("#skill-detail")).to_contain_text("guardrails-agent")
            expect(page.locator("#skill-detail")).to_contain_text(
                "critic-reviewer-agent"
            )

            page.get_by_label("Search skills").fill("feedback_resolution_ledger")
            export_payload = json.loads(page.locator("#matrix-export").input_value())
            assert export_payload["artifact"] == "agent-studio-skill-matrix"
            assert export_payload["source"] == (
                "social_media_optimiser/00-system-design/"
                "agent-studio-skill-matrix.html"
            )
            assert [skill["id"] for skill in export_payload["skills"]] == [
                "agent-studio-guardrails-review"
            ]
            assert export_payload["skills"][0]["source_path"] == (
                "skills/agent-studio-guardrails-review/SKILL.md"
            )
        finally:
            browser.close()
