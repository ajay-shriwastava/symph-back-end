"""
Integration tests for /api/v1/logs
"""
import uuid
import pytest


async def _make_log(client, level="INFO", message="test log", **kwargs):
    payload = {"level": level, "message": message, **kwargs}
    res = await client.post("/api/v1/logs", json=payload,
                            headers={"Authorization": "Bearer test"})
    assert res.status_code == 201
    return res.json()


class TestCreateLog:
    async def test_creates_info_log(self, client):
        res = await client.post("/api/v1/logs", json={"level": "INFO", "message": "started"},
                                headers={"Authorization": "Bearer test"})
        assert res.status_code == 201
        data = res.json()
        assert data["level"] == "INFO"
        assert data["message"] == "started"
        assert uuid.UUID(data["id"])

    async def test_all_valid_levels(self, client):
        for level in ("DEBUG", "INFO", "WARNING", "ERROR"):
            res = await client.post("/api/v1/logs", json={"level": level, "message": "ok"},
                                    headers={"Authorization": "Bearer test"})
            assert res.status_code == 201, f"Failed for level={level}"

    async def test_invalid_level_returns_422(self, client):
        res = await client.post("/api/v1/logs", json={"level": "TRACE", "message": "x"},
                                headers={"Authorization": "Bearer test"})
        assert res.status_code == 422

    async def test_optional_fields_accepted(self, client):
        agent_res = await client.post("/api/v1/agents", json={"name": "log-agent"},
                                      headers={"Authorization": "Bearer test"})
        agent_id = agent_res.json()["id"]
        res = await client.post("/api/v1/logs", json={
            "level": "INFO",
            "message": "agent did something",
            "agent_id": agent_id,
            "metadata": {"duration_ms": 42},
        }, headers={"Authorization": "Bearer test"})
        assert res.status_code == 201
        data = res.json()
        assert data["agent_id"] == agent_id
        assert data["metadata"]["duration_ms"] == 42

    async def test_missing_message_returns_422(self, client):
        res = await client.post("/api/v1/logs", json={"level": "INFO"},
                                headers={"Authorization": "Bearer test"})
        assert res.status_code == 422


class TestListLogs:
    async def test_empty_list(self, client):
        res = await client.get("/api/v1/logs", headers={"Authorization": "Bearer test"})
        assert res.status_code == 200
        assert res.json()["total"] == 0

    async def test_filter_by_level(self, client):
        await _make_log(client, level="INFO")
        await _make_log(client, level="ERROR")
        await _make_log(client, level="ERROR")

        res = await client.get("/api/v1/logs?level=ERROR",
                               headers={"Authorization": "Bearer test"})
        data = res.json()
        assert data["total"] == 2
        assert all(l["level"] == "ERROR" for l in data["items"])

    async def test_filter_by_agent_id(self, client):
        agent_res = await client.post("/api/v1/agents", json={"name": "filter-agent"},
                                      headers={"Authorization": "Bearer test"})
        agent_id = agent_res.json()["id"]
        await _make_log(client, agent_id=agent_id)
        await _make_log(client)  # no agent_id

        res = await client.get(f"/api/v1/logs?agent_id={agent_id}",
                               headers={"Authorization": "Bearer test"})
        assert res.json()["total"] == 1
        assert res.json()["items"][0]["agent_id"] == agent_id

    async def test_pagination(self, client):
        for i in range(6):
            await _make_log(client, message=f"log {i}")
        res = await client.get("/api/v1/logs?skip=0&limit=4",
                               headers={"Authorization": "Bearer test"})
        data = res.json()
        assert data["total"] == 6
        assert len(data["items"]) == 4

    async def test_ordered_by_created_at_desc(self, client):
        await _make_log(client, message="first")
        await _make_log(client, message="second")
        res = await client.get("/api/v1/logs", headers={"Authorization": "Bearer test"})
        items = res.json()["items"]
        # Most recent first
        assert items[0]["message"] == "second"


class TestGetLog:
    async def test_get_existing(self, client):
        log = await _make_log(client, message="find me")
        res = await client.get(f"/api/v1/logs/{log['id']}",
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 200
        assert res.json()["message"] == "find me"

    async def test_get_nonexistent_returns_404(self, client):
        res = await client.get(f"/api/v1/logs/{uuid.uuid4()}",
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()
