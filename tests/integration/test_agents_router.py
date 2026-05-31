"""
Integration tests for /api/v1/agents and /api/v1/agents/{id}/memory
"""
import uuid
import pytest


AGENT_PAYLOAD = {
    "name": "Test Agent",
    "description": "A test agent",
    "model": "claude-haiku-4-5-20251001",
    "system_prompt": "You are helpful.",
    "tools": [],
    "channels": [],
    "memory_enabled": False,
}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def create_agent(client, payload=None):
    payload = payload or AGENT_PAYLOAD
    res = await client.post("/api/v1/agents", json=payload,
                            headers={"Authorization": "Bearer test"})
    assert res.status_code == 201
    return res.json()


# ---------------------------------------------------------------------------
# Agent CRUD
# ---------------------------------------------------------------------------

class TestCreateAgent:
    async def test_creates_agent_returns_201(self, client):
        res = await client.post("/api/v1/agents", json=AGENT_PAYLOAD,
                                headers={"Authorization": "Bearer test"})
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Test Agent"
        assert data["model"] == "claude-haiku-4-5-20251001"
        assert uuid.UUID(data["id"])
        assert data["created_at"] is not None

    async def test_missing_name_returns_422(self, client):
        res = await client.post("/api/v1/agents", json={"model": "claude-haiku-4-5-20251001"},
                                headers={"Authorization": "Bearer test"})
        assert res.status_code == 422

    async def test_default_model_applied(self, client):
        res = await client.post("/api/v1/agents", json={"name": "minimal"},
                                headers={"Authorization": "Bearer test"})
        assert res.status_code == 201
        assert res.json()["model"] == "claude-sonnet-4-6"

    async def test_tools_and_channels_stored(self, client):
        payload = {**AGENT_PAYLOAD, "tools": ["scan_csv"], "channels": ["slack"]}
        res = await client.post("/api/v1/agents", json=payload,
                                headers={"Authorization": "Bearer test"})
        assert res.status_code == 201
        assert res.json()["tools"] == ["scan_csv"]
        assert res.json()["channels"] == ["slack"]


class TestListAgents:
    async def test_empty_list(self, client):
        res = await client.get("/api/v1/agents", headers={"Authorization": "Bearer test"})
        assert res.status_code == 200
        data = res.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_returns_created_agent(self, client):
        await create_agent(client)
        res = await client.get("/api/v1/agents", headers={"Authorization": "Bearer test"})
        assert res.status_code == 200
        assert res.json()["total"] == 1
        assert len(res.json()["items"]) == 1

    async def test_pagination(self, client):
        for i in range(5):
            await create_agent(client, {**AGENT_PAYLOAD, "name": f"Agent {i}"})
        res = await client.get("/api/v1/agents?skip=0&limit=3",
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 5
        assert len(data["items"]) == 3


class TestGetAgent:
    async def test_get_existing_agent(self, client):
        agent = await create_agent(client)
        res = await client.get(f"/api/v1/agents/{agent['id']}",
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 200
        assert res.json()["id"] == agent["id"]

    async def test_get_nonexistent_returns_404(self, client):
        res = await client.get(f"/api/v1/agents/{uuid.uuid4()}",
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()


class TestUpdateAgent:
    async def test_update_name(self, client):
        agent = await create_agent(client)
        res = await client.put(f"/api/v1/agents/{agent['id']}",
                               json={"name": "Updated Name"},
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 200
        assert res.json()["name"] == "Updated Name"
        # Other fields unchanged
        assert res.json()["model"] == agent["model"]

    async def test_update_nonexistent_returns_404(self, client):
        res = await client.put(f"/api/v1/agents/{uuid.uuid4()}",
                               json={"name": "x"},
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 404

    async def test_update_channels(self, client):
        agent = await create_agent(client)
        res = await client.put(f"/api/v1/agents/{agent['id']}",
                               json={"channels": ["slack", "telegram"]},
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 200
        assert res.json()["channels"] == ["slack", "telegram"]


class TestDeleteAgent:
    async def test_delete_returns_204(self, client):
        agent = await create_agent(client)
        res = await client.delete(f"/api/v1/agents/{agent['id']}",
                                  headers={"Authorization": "Bearer test"})
        assert res.status_code == 204

    async def test_deleted_agent_not_found(self, client):
        agent = await create_agent(client)
        await client.delete(f"/api/v1/agents/{agent['id']}",
                            headers={"Authorization": "Bearer test"})
        res = await client.get(f"/api/v1/agents/{agent['id']}",
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 404

    async def test_delete_nonexistent_returns_404(self, client):
        res = await client.delete(f"/api/v1/agents/{uuid.uuid4()}",
                                  headers={"Authorization": "Bearer test"})
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# Agent Memory
# ---------------------------------------------------------------------------

class TestAgentMemory:
    async def test_upsert_and_retrieve(self, client):
        agent = await create_agent(client)
        aid = agent["id"]

        # Create
        res = await client.post(f"/api/v1/agents/{aid}/memory",
                                json={"key": "preference", "value": "concise"},
                                headers={"Authorization": "Bearer test"})
        assert res.status_code == 200
        assert res.json()["key"] == "preference"
        assert res.json()["value"] == "concise"

        # Retrieve single
        res = await client.get(f"/api/v1/agents/{aid}/memory/preference",
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 200
        assert res.json()["value"] == "concise"

    async def test_upsert_updates_existing(self, client):
        agent = await create_agent(client)
        aid = agent["id"]
        await client.post(f"/api/v1/agents/{aid}/memory",
                          json={"key": "tone", "value": "formal"},
                          headers={"Authorization": "Bearer test"})
        # Overwrite
        res = await client.post(f"/api/v1/agents/{aid}/memory",
                                json={"key": "tone", "value": "casual"},
                                headers={"Authorization": "Bearer test"})
        assert res.status_code == 200
        assert res.json()["value"] == "casual"

        # Verify only one row exists
        res = await client.get(f"/api/v1/agents/{aid}/memory",
                               headers={"Authorization": "Bearer test"})
        assert res.json()["total"] == 1

    async def test_list_memory(self, client):
        agent = await create_agent(client)
        aid = agent["id"]
        for k in ("k1", "k2", "k3"):
            await client.post(f"/api/v1/agents/{aid}/memory",
                              json={"key": k, "value": "v"},
                              headers={"Authorization": "Bearer test"})
        res = await client.get(f"/api/v1/agents/{aid}/memory",
                               headers={"Authorization": "Bearer test"})
        assert res.json()["total"] == 3

    async def test_delete_memory_entry(self, client):
        agent = await create_agent(client)
        aid = agent["id"]
        await client.post(f"/api/v1/agents/{aid}/memory",
                          json={"key": "del-me", "value": "x"},
                          headers={"Authorization": "Bearer test"})
        res = await client.delete(f"/api/v1/agents/{aid}/memory/del-me",
                                  headers={"Authorization": "Bearer test"})
        assert res.status_code == 204

        res = await client.get(f"/api/v1/agents/{aid}/memory/del-me",
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 404

    async def test_get_missing_memory_key_returns_404(self, client):
        agent = await create_agent(client)
        res = await client.get(f"/api/v1/agents/{agent['id']}/memory/nonexistent",
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 404
