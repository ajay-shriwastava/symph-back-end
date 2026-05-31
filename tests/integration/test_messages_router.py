"""
Integration tests for /api/v1/messages
"""
import uuid
import pytest


async def _make_agent(client):
    res = await client.post("/api/v1/agents", json={"name": "msg-agent"},
                            headers={"Authorization": "Bearer test"})
    assert res.status_code == 201
    return res.json()["id"]


async def _make_message(client, agent_id, role="user", content="hello", session_id=None):
    payload = {
        "agent_id": agent_id,
        "session_id": str(session_id or uuid.uuid4()),
        "role": role,
        "content": content,
    }
    res = await client.post("/api/v1/messages", json=payload,
                            headers={"Authorization": "Bearer test"})
    assert res.status_code == 201
    return res.json()


class TestCreateMessage:
    async def test_creates_user_message(self, client):
        agent_id = await _make_agent(client)
        session_id = uuid.uuid4()
        res = await client.post("/api/v1/messages", json={
            "agent_id": agent_id,
            "session_id": str(session_id),
            "role": "user",
            "content": "Hello!",
        }, headers={"Authorization": "Bearer test"})
        assert res.status_code == 201
        data = res.json()
        assert data["role"] == "user"
        assert data["content"] == "Hello!"
        assert data["agent_id"] == agent_id
        assert data["session_id"] == str(session_id)

    async def test_all_valid_roles(self, client):
        agent_id = await _make_agent(client)
        for role in ("user", "assistant", "system", "tool", "agent"):
            res = await client.post("/api/v1/messages", json={
                "agent_id": agent_id,
                "session_id": str(uuid.uuid4()),
                "role": role,
                "content": f"msg as {role}",
            }, headers={"Authorization": "Bearer test"})
            assert res.status_code == 201, f"Failed for role={role}"

    async def test_invalid_role_returns_422(self, client):
        agent_id = await _make_agent(client)
        res = await client.post("/api/v1/messages", json={
            "agent_id": agent_id,
            "session_id": str(uuid.uuid4()),
            "role": "invalid-role",
            "content": "x",
        }, headers={"Authorization": "Bearer test"})
        assert res.status_code == 422

    async def test_missing_fields_returns_422(self, client):
        res = await client.post("/api/v1/messages", json={"role": "user", "content": "hi"},
                                headers={"Authorization": "Bearer test"})
        assert res.status_code == 422


class TestListMessages:
    async def test_empty_list(self, client):
        res = await client.get("/api/v1/messages", headers={"Authorization": "Bearer test"})
        assert res.status_code == 200
        assert res.json()["items"] == []
        assert res.json()["total"] == 0

    async def test_filter_by_session_id(self, client):
        agent_id = await _make_agent(client)
        session_a = uuid.uuid4()
        session_b = uuid.uuid4()
        await _make_message(client, agent_id, session_id=session_a)
        await _make_message(client, agent_id, session_id=session_a)
        await _make_message(client, agent_id, session_id=session_b)

        res = await client.get(f"/api/v1/messages?session_id={session_a}",
                               headers={"Authorization": "Bearer test"})
        data = res.json()
        assert data["total"] == 2
        assert all(m["session_id"] == str(session_a) for m in data["items"])

    async def test_filter_by_agent_id(self, client):
        agent_a = await _make_agent(client)
        agent_b = await _make_agent(client)
        await _make_message(client, agent_a)
        await _make_message(client, agent_b)

        res = await client.get(f"/api/v1/messages?agent_id={agent_a}",
                               headers={"Authorization": "Bearer test"})
        data = res.json()
        assert data["total"] == 1
        assert data["items"][0]["agent_id"] == agent_a

    async def test_filter_by_role(self, client):
        agent_id = await _make_agent(client)
        await _make_message(client, agent_id, role="user")
        await _make_message(client, agent_id, role="agent")
        await _make_message(client, agent_id, role="agent")

        res = await client.get("/api/v1/messages?role=agent",
                               headers={"Authorization": "Bearer test"})
        data = res.json()
        assert data["total"] == 2
        assert all(m["role"] == "agent" for m in data["items"])

    async def test_pagination(self, client):
        agent_id = await _make_agent(client)
        for i in range(5):
            await _make_message(client, agent_id, content=f"msg {i}")
        res = await client.get("/api/v1/messages?skip=0&limit=3",
                               headers={"Authorization": "Bearer test"})
        data = res.json()
        assert data["total"] == 5
        assert len(data["items"]) == 3


class TestGetMessage:
    async def test_get_existing(self, client):
        agent_id = await _make_agent(client)
        msg = await _make_message(client, agent_id)
        res = await client.get(f"/api/v1/messages/{msg['id']}",
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 200
        assert res.json()["id"] == msg["id"]

    async def test_get_nonexistent_returns_404(self, client):
        res = await client.get(f"/api/v1/messages/{uuid.uuid4()}",
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 404


class TestDeleteMessage:
    async def test_delete_returns_204(self, client):
        agent_id = await _make_agent(client)
        msg = await _make_message(client, agent_id)
        res = await client.delete(f"/api/v1/messages/{msg['id']}",
                                  headers={"Authorization": "Bearer test"})
        assert res.status_code == 204

    async def test_deleted_message_not_found(self, client):
        agent_id = await _make_agent(client)
        msg = await _make_message(client, agent_id)
        await client.delete(f"/api/v1/messages/{msg['id']}",
                            headers={"Authorization": "Bearer test"})
        res = await client.get(f"/api/v1/messages/{msg['id']}",
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 404

    async def test_delete_nonexistent_returns_404(self, client):
        res = await client.delete(f"/api/v1/messages/{uuid.uuid4()}",
                                  headers={"Authorization": "Bearer test"})
        assert res.status_code == 404
