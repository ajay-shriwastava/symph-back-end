"""
Integration tests for agent config endpoints:
  - /api/v1/agents/{id}/schedules
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
# Schedules
# ---------------------------------------------------------------------------

class TestSchedules:
    async def test_create_schedule(self, client):
        agent_id = await _make_agent(client)
        res = await client.post(f"/api/v1/agents/{agent_id}/schedules",
                                json={"label": "daily", "cron_expression": "0 9 * * *"},
                                headers={"Authorization": "Bearer test"})
        assert res.status_code == 201
        data = res.json()
        assert data["label"] == "daily"
        assert data["cron_expression"] == "0 9 * * *"
        assert data["enabled"] is True
        assert data["agent_id"] == agent_id

    async def test_create_schedule_nonexistent_agent(self, client):
        res = await client.post(f"/api/v1/agents/{uuid.uuid4()}/schedules",
                                json={"label": "x", "cron_expression": "0 9 * * *"},
                                headers={"Authorization": "Bearer test"})
        assert res.status_code == 404

    async def test_create_schedule_missing_fields(self, client):
        agent_id = await _make_agent(client)
        res = await client.post(f"/api/v1/agents/{agent_id}/schedules",
                                json={"label": "no-cron"},
                                headers={"Authorization": "Bearer test"})
        assert res.status_code == 422

    async def test_list_schedules(self, client):
        agent_id = await _make_agent(client)
        await client.post(f"/api/v1/agents/{agent_id}/schedules",
                          json={"label": "s1", "cron_expression": "0 9 * * *"},
                          headers={"Authorization": "Bearer test"})
        await client.post(f"/api/v1/agents/{agent_id}/schedules",
                          json={"label": "s2", "cron_expression": "0 10 * * *"},
                          headers={"Authorization": "Bearer test"})
        res = await client.get(f"/api/v1/agents/{agent_id}/schedules",
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 200
        assert res.json()["total"] == 2

    async def test_update_schedule(self, client):
        agent_id = await _make_agent(client)
        sched_res = await client.post(f"/api/v1/agents/{agent_id}/schedules",
                                      json={"label": "original", "cron_expression": "0 9 * * *"},
                                      headers={"Authorization": "Bearer test"})
        sched_id = sched_res.json()["id"]

        res = await client.put(f"/api/v1/agents/{agent_id}/schedules/{sched_id}",
                               json={"label": "updated", "enabled": False},
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 200
        assert res.json()["label"] == "updated"
        assert res.json()["enabled"] is False
        assert res.json()["cron_expression"] == "0 9 * * *"  # unchanged

    async def test_update_nonexistent_schedule(self, client):
        agent_id = await _make_agent(client)
        res = await client.put(f"/api/v1/agents/{agent_id}/schedules/{uuid.uuid4()}",
                               json={"label": "x"},
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 404

    async def test_delete_schedule(self, client):
        agent_id = await _make_agent(client)
        sched_res = await client.post(f"/api/v1/agents/{agent_id}/schedules",
                                      json={"label": "del-me", "cron_expression": "* * * * *"},
                                      headers={"Authorization": "Bearer test"})
        sched_id = sched_res.json()["id"]

        res = await client.delete(f"/api/v1/agents/{agent_id}/schedules/{sched_id}",
                                  headers={"Authorization": "Bearer test"})
        assert res.status_code == 204

        res = await client.get(f"/api/v1/agents/{agent_id}/schedules",
                               headers={"Authorization": "Bearer test"})
        assert res.json()["total"] == 0

    async def test_delete_nonexistent_schedule(self, client):
        agent_id = await _make_agent(client)
        res = await client.delete(f"/api/v1/agents/{agent_id}/schedules/{uuid.uuid4()}",
                                  headers={"Authorization": "Bearer test"})
        assert res.status_code == 404


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
