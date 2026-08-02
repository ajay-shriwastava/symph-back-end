"""
Integration tests for agent config endpoints:
  - /api/v1/agents/{id}/interaction-rules
  - /api/v1/agents/{id}/guardrails
"""
import uuid
import pytest


async def _make_agent(client):
    res = await client.post("/api/v1/agents", json={"name": "config-agent"},
                            headers={"Authorization": "Bearer test"})
    assert res.status_code == 201
    return res.json()["id"]


# ---------------------------------------------------------------------------
# Interaction Rules
# ---------------------------------------------------------------------------

class TestInteractionRules:
    async def test_update_interaction_rules(self, client):
        agent_id = await _make_agent(client)
        res = await client.put(f"/api/v1/agents/{agent_id}/interaction-rules",
                               json={"interaction_rules": {
                                   "temperature": 0.5,
                                   "max_turns": 5,
                                   "response_style": "concise",
                                   "language": "es",
                               }},
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 200
        rules = res.json()["interaction_rules"]
        assert rules["temperature"] == 0.5
        assert rules["max_turns"] == 5
        assert rules["language"] == "es"

    async def test_temperature_out_of_range(self, client):
        agent_id = await _make_agent(client)
        res = await client.put(f"/api/v1/agents/{agent_id}/interaction-rules",
                               json={"interaction_rules": {"temperature": 3.0, "max_turns": 5,
                                                           "response_style": "balanced",
                                                           "language": "en"}},
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 422

    async def test_max_turns_out_of_range(self, client):
        agent_id = await _make_agent(client)
        res = await client.put(f"/api/v1/agents/{agent_id}/interaction-rules",
                               json={"interaction_rules": {"temperature": 0.7, "max_turns": 0,
                                                           "response_style": "balanced",
                                                           "language": "en"}},
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 422

    async def test_update_nonexistent_agent(self, client):
        res = await client.put(f"/api/v1/agents/{uuid.uuid4()}/interaction-rules",
                               json={"interaction_rules": {"temperature": 0.7, "max_turns": 10,
                                                           "response_style": "balanced",
                                                           "language": "en"}},
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# Guardrails
# ---------------------------------------------------------------------------

class TestGuardrails:
    async def test_update_guardrails(self, client):
        agent_id = await _make_agent(client)
        res = await client.put(f"/api/v1/agents/{agent_id}/guardrails",
                               json={"guardrails": {
                                   "max_tokens_per_response": 512,
                                   "restricted_topics": ["politics", "religion"],
                                   "content_filter_level": "strict",
                                   "rate_limit_per_minute": 10,
                               }},
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 200
        g = res.json()["guardrails"]
        assert g["max_tokens_per_response"] == 512
        assert "politics" in g["restricted_topics"]
        assert g["rate_limit_per_minute"] == 10

    async def test_rate_limit_too_low(self, client):
        agent_id = await _make_agent(client)
        res = await client.put(f"/api/v1/agents/{agent_id}/guardrails",
                               json={"guardrails": {
                                   "max_tokens_per_response": 512,
                                   "restricted_topics": [],
                                   "content_filter_level": "medium",
                                   "rate_limit_per_minute": 0,
                               }},
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 422

    async def test_update_nonexistent_agent(self, client):
        res = await client.put(f"/api/v1/agents/{uuid.uuid4()}/guardrails",
                               json={"guardrails": {
                                   "max_tokens_per_response": 2048,
                                   "restricted_topics": [],
                                   "content_filter_level": "medium",
                                   "rate_limit_per_minute": 60,
                               }},
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 404
