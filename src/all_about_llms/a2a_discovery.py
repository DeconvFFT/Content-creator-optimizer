from all_about_llms.agents import AGENT_ROSTER, list_skill_cards


A2A_PROTOCOL_VERSION = "0.3.0"
DEFAULT_A2A_INPUT_MODES = [
    "application/json",
    "text/plain",
]
DEFAULT_A2A_OUTPUT_MODES = [
    "application/json",
    "text/plain",
]
INTERNAL_REALTIME_MODES = [
    "audio/pcm",
    "audio/wav",
    "image/jpeg",
    "image/png",
]
PUBLIC_PROJECTION_CONTRACT = {
    "queryParameter": "projection",
    "defaultValue": "private",
    "publicValue": "public",
    "redactionPolicy": "agent-message-public-projection-v1",
    "rawFieldsRedacted": True,
    "tokenStringsRedacted": True,
    "supportedEndpoints": [
        "getTask",
        "listRunMessages",
        "agentInbox",
    ],
    "unsupportedEndpoints": [
        "createTask",
        "updateMessageStatus",
        "retryTask",
        "repairDependencies",
    ],
}


def build_public_a2a_agent_card(
    *,
    a2a_url: str,
    documentation_url: str,
) -> dict:
    """Build the public A2A discovery card for the local studio orchestrator."""
    return {
        "protocolVersion": A2A_PROTOCOL_VERSION,
        "name": "All About LLMs Agent Studio",
        "description": (
            "Local-first realtime multi-agent content studio for source-backed "
            "social posts, reels, Substack drafts, voice dialogue, review gates, "
            "and autonomous specialist handoffs."
        ),
        "url": a2a_url,
        "preferredTransport": "HTTP+JSON",
        "additionalInterfaces": [
            {"url": a2a_url, "transport": "HTTP+JSON"},
        ],
        "provider": {
            "organization": "All About LLMs local workspace",
            "url": documentation_url,
        },
        "version": "0.1.0",
        "documentationUrl": documentation_url,
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": False,
        },
        "securitySchemes": {},
        "security": [],
        "defaultInputModes": DEFAULT_A2A_INPUT_MODES,
        "defaultOutputModes": DEFAULT_A2A_OUTPUT_MODES,
        "skills": [_a2a_skill_payload(skill) for skill in list_skill_cards()],
        "supportsAuthenticatedExtendedCard": False,
        "x-agentStudio": {
            "fullA2AProtocolServer": False,
            "compatibility": "a2a-0.3-discovery-card-for-local-http-json-routes",
            "publicProjection": PUBLIC_PROJECTION_CONTRACT.copy(),
            "internalRealtimeModes": INTERNAL_REALTIME_MODES,
            "internalRealtimeNote": (
                "Voice, image, and event-stream features are internal Agent Studio "
                "surfaces until public A2A-compatible media/task routes exist."
            ),
            "internalAgentCount": len(AGENT_ROSTER),
            "internalAgents": [
                {
                    "id": agent.id,
                    "name": agent.name,
                    "role": agent.role,
                    "skillIds": agent.skill_ids,
                    "capabilities": agent.capabilities,
                }
                for agent in AGENT_ROSTER
            ],
        },
    }


def build_a2a_http_json_interface(
    *,
    agent_card_url: str,
) -> dict:
    return {
        "protocol": "a2a-http-json-interface",
        "protocolVersion": A2A_PROTOCOL_VERSION,
        "transport": "HTTP+JSON",
        "agentCardUrl": agent_card_url,
        "fullA2AProtocolServer": False,
        "summary": (
            "This local interface exposes Agent Studio's durable A2A-style "
            "HTTP routes. It is a compatibility/discovery surface, not a full "
            "public JSON-RPC A2A server."
        ),
        "endpoints": {
            "createTask": _endpoint("POST", "/api/a2a/messages"),
            "getTask": _endpoint("GET", "/api/a2a/messages/{message_id}"),
            "listRunMessages": _endpoint(
                "GET", "/api/runs/{run_id}/agent-messages"
            ),
            "updateMessageStatus": _endpoint(
                "POST", "/api/a2a/messages/{message_id}/status"
            ),
            "retryTask": _endpoint("POST", "/api/a2a/messages/{message_id}/retry"),
            "repairDependencies": _endpoint(
                "POST", "/api/a2a/messages/{message_id}/dependencies/repair"
            ),
            "runWorker": _endpoint("POST", "/api/a2a/workers/{agent_id}/run"),
            "runWorkerCycle": _endpoint("POST", "/api/a2a/workers/run-cycle"),
            "agentInbox": _endpoint("GET", "/api/a2a/agents/{agent_id}/inbox"),
            "agentCard": _endpoint("GET", "/api/a2a/agents/{agent_id}/card"),
            "agentSkills": _endpoint("GET", "/api/a2a/agents/{agent_id}/skills"),
            "collaborationGraph": _endpoint(
                "POST", "/api/runs/{run_id}/a2a-collaboration-graph"
            ),
            "listAgentCards": _endpoint("GET", "/.well-known/agent-cards.json"),
            "listSkillCards": _endpoint("GET", "/.well-known/agent-skills.json"),
        },
        "publicProjection": PUBLIC_PROJECTION_CONTRACT.copy(),
    }


def _endpoint(method: str, path: str) -> dict[str, str]:
    return {"method": method, "path": path}


def _a2a_skill_payload(skill) -> dict:
    return {
        "id": skill.id,
        "name": skill.name,
        "description": skill.description,
        "tags": _skill_tags(skill),
        "examples": _skill_examples(skill),
        "inputModes": DEFAULT_A2A_INPUT_MODES,
        "outputModes": _skill_output_modes(skill),
    }


def _skill_tags(skill) -> list[str]:
    tags = set(skill.capabilities)
    tags.update(part for part in skill.id.split("-") if part and part != "agent")
    if "content" in skill.id:
        tags.add("content_creation")
    if "conversation" in skill.id:
        tags.add("voice_dialogue")
    if "retrieval" in skill.id:
        tags.add("retrieval_quality")
    if "guardrails" in skill.id:
        tags.add("review_gate")
    return sorted(tags)


def _skill_examples(skill) -> list[str]:
    first_output = skill.outputs[0] if skill.outputs else "artifact"
    first_input = skill.required_inputs[0] if skill.required_inputs else "user_goal"
    return [
        (
            f"Use {skill.name} with {first_input} to produce a "
            f"{first_output}."
        )
    ]


def _skill_output_modes(skill) -> list[str]:
    return DEFAULT_A2A_OUTPUT_MODES.copy()
