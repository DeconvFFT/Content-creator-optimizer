import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def test_agent_studio_a2a_map_filters_public_boundary_and_exports_context():
    map_path = ROOT / "social_media_optimiser/00-system-design/agent-studio-a2a-map.html"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(map_path.as_uri())

            expect(page.locator("h1")).to_have_text("Agent Studio A2A Map")
            expect(page.locator("body")).to_contain_text("Planning memory only")
            expect(page.locator("#surface-count")).to_have_text("6 surfaces")

            page.get_by_role("button", name="Public boundary").click()
            expect(page.locator("[data-surface-card]:visible")).to_have_count(1)
            expect(page.locator("#surface-count")).to_have_text("1 surface")
            expect(page.locator("#surface-detail")).to_contain_text(
                "public-a2a-discovery-boundary"
            )
            expect(page.locator("#surface-detail")).to_contain_text(
                "/.well-known/agent-card.json"
            )
            expect(page.locator("#surface-detail")).to_contain_text("/api/a2a")
            expect(page.locator("#surface-detail")).to_contain_text(
                "fullA2AProtocolServer=false"
            )
            expect(page.locator("#surface-detail")).to_contain_text(
                "JSON/text HTTP+JSON only"
            )
            expect(page.locator("#surface-detail")).to_contain_text(
                "method-aware endpoint records"
            )
            expect(page.locator("#surface-detail")).to_contain_text(
                "projection=public"
            )
            expect(page.locator("#surface-detail")).to_contain_text(
                "agent-message-public-projection-v1"
            )
            expect(page.locator("#surface-detail")).to_contain_text(
                "Realtime audio and image modes remain internal extension metadata"
            )

            export_payload = json.loads(page.locator("#a2a-export").input_value())
            assert export_payload["artifact"] == "agent-studio-a2a-map"
            assert export_payload["source"] == (
                "social_media_optimiser/00-system-design/agent-studio-a2a-map.html"
            )
            assert [surface["id"] for surface in export_payload["surfaces"]] == [
                "public-a2a-discovery-boundary"
            ]
            assert export_payload["surfaces"][0]["status"] == "scoped"
            assert "method-aware endpoint records" in export_payload["surfaces"][0][
                "proof_terms"
            ]
            assert "projection=public" in export_payload["surfaces"][0]["proof_terms"]
            assert (
                export_payload["surfaces"][0]["public_projection"]["redactionPolicy"]
                == "agent-message-public-projection-v1"
            )
            assert export_payload["surfaces"][0]["public_projection"][
                "supportedEndpoints"
            ] == ["getTask", "listRunMessages", "agentInbox"]
            assert (
                "Realtime audio and image modes remain internal extension metadata."
                in export_payload["surfaces"][0]["caveats"]
            )
        finally:
            browser.close()


def test_agent_studio_a2a_map_filters_repair_cycle_context():
    map_path = ROOT / "social_media_optimiser/00-system-design/agent-studio-a2a-map.html"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(map_path.as_uri())

            page.get_by_role("button", name="Repair").click()
            expect(page.locator("[data-surface-card]:visible")).to_have_count(1)
            expect(page.locator("#surface-detail")).to_contain_text(
                "dependency-repair-and-retry"
            )
            expect(page.locator("#surface-detail")).to_contain_text(
                "/api/a2a/messages/{message_id}/retry"
            )
            expect(page.locator("#surface-detail")).to_contain_text(
                "/api/a2a/messages/{message_id}/dependencies/repair"
            )
            expect(page.locator("#surface-detail")).to_contain_text(
                "a2a_graph_blocked"
            )
            expect(page.locator("#surface-detail")).to_contain_text(
                "dependency_cycle_message_ids"
            )
            expect(page.locator("#surface-detail")).to_contain_text(
                "default-roster fallback is not valid repair"
            )
        finally:
            browser.close()
