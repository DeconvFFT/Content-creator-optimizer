"""Unit tests for a2a_discovery module – card building and helpers."""

from all_about_llms.a2a_discovery import (
    A2A_PROTOCOL_VERSION,
    DEFAULT_A2A_INPUT_MODES,
    DEFAULT_A2A_OUTPUT_MODES,
    INTERNAL_REALTIME_MODES,
    PUBLIC_PROJECTION_CONTRACT,
    build_a2a_http_json_interface,
    build_public_a2a_agent_card,
)
from all_about_llms.agents import AGENT_ROSTER, list_skill_cards


class TestBuildPublicA2AAgentCard:
    def setup_method(self):
        self.card = build_public_a2a_agent_card(
            a2a_url="http://localhost:8000/api/a2a",
            documentation_url="http://localhost:8000/docs",
        )

    def test_protocol_version(self):
        assert self.card["protocolVersion"] == A2A_PROTOCOL_VERSION

    def test_name_present(self):
        assert self.card["name"] == "All About LLMs Agent Studio"

    def test_url_set(self):
        assert self.card["url"] == "http://localhost:8000/api/a2a"

    def test_preferred_transport(self):
        assert self.card["preferredTransport"] == "HTTP+JSON"

    def test_provider_section(self):
        assert "provider" in self.card
        assert self.card["provider"]["url"] == "http://localhost:8000/docs"

    def test_capabilities_section(self):
        caps = self.card["capabilities"]
        assert caps["streaming"] is False
        assert caps["pushNotifications"] is False
        assert caps["stateTransitionHistory"] is False

    def test_default_input_modes(self):
        assert self.card["defaultInputModes"] == DEFAULT_A2A_INPUT_MODES

    def test_default_output_modes(self):
        assert self.card["defaultOutputModes"] == DEFAULT_A2A_OUTPUT_MODES

    def test_skills_list_matches_skill_cards(self):
        skills = self.card["skills"]
        assert len(skills) == len(list_skill_cards())
        for skill in skills:
            assert "id" in skill
            assert "name" in skill
            assert "description" in skill
            assert "tags" in skill
            assert "examples" in skill
            assert "inputModes" in skill
            assert "outputModes" in skill

    def test_x_agent_studio_internal_agent_count(self):
        x_studio = self.card["x-agentStudio"]
        assert x_studio["internalAgentCount"] == len(AGENT_ROSTER)

    def test_x_agent_studio_internal_agents_have_required_fields(self):
        x_studio = self.card["x-agentStudio"]
        for agent in x_studio["internalAgents"]:
            assert "id" in agent
            assert "name" in agent
            assert "role" in agent
            assert "skillIds" in agent
            assert "capabilities" in agent

    def test_internal_realtime_modes_in_x_agent_studio(self):
        x_studio = self.card["x-agentStudio"]
        assert x_studio["internalRealtimeModes"] == INTERNAL_REALTIME_MODES


class TestBuildA2AHttpJsonInterface:
    def setup_method(self):
        self.interface = build_a2a_http_json_interface(
            agent_card_url="http://localhost:8000/.well-known/agent-cards.json"
        )

    def test_protocol_version(self):
        assert self.interface["protocolVersion"] == A2A_PROTOCOL_VERSION

    def test_transport(self):
        assert self.interface["transport"] == "HTTP+JSON"

    def test_full_a2a_protocol_server_false(self):
        assert self.interface["fullA2AProtocolServer"] is False

    def test_agent_card_url(self):
        assert (
            self.interface["agentCardUrl"]
            == "http://localhost:8000/.well-known/agent-cards.json"
        )

    def test_endpoints_present(self):
        endpoints = self.interface["endpoints"]
        expected_endpoints = [
            "createTask",
            "getTask",
            "listRunMessages",
            "updateMessageStatus",
            "retryTask",
            "repairDependencies",
            "runWorker",
            "runWorkerCycle",
            "agentInbox",
            "agentCard",
            "agentSkills",
            "collaborationGraph",
            "listAgentCards",
            "listSkillCards",
        ]
        for ep in expected_endpoints:
            assert ep in endpoints
            assert "method" in endpoints[ep]
            assert "path" in endpoints[ep]

    def test_public_projection_included(self):
        assert "publicProjection" in self.interface
        assert self.interface["publicProjection"]["queryParameter"] == "projection"


class TestPublicProjectionContract:
    def test_query_parameter(self):
        assert PUBLIC_PROJECTION_CONTRACT["queryParameter"] == "projection"

    def test_default_value_is_private(self):
        assert PUBLIC_PROJECTION_CONTRACT["defaultValue"] == "private"

    def test_public_value(self):
        assert PUBLIC_PROJECTION_CONTRACT["publicValue"] == "public"

    def test_supported_endpoints_present(self):
        assert len(PUBLIC_PROJECTION_CONTRACT["supportedEndpoints"]) > 0

    def test_unsupported_endpoints_present(self):
        assert len(PUBLIC_PROJECTION_CONTRACT["unsupportedEndpoints"]) > 0
