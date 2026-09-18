"""
Minimal integration tests for MCP REST endpoints and auth middleware.
"""
import uuid

import pytest
from httpx import AsyncClient

from app.models.mcp_audit_log import McpAuditLog


class TestMcpTools:
    async def test_list_tools_returns_eight(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/v1/mcp/tools", headers=auth_headers)
        assert resp.status_code == 200
        tools = resp.json()
        assert len(tools) == 8
        names = {t["name"] for t in tools}
        assert {"get_memory", "list_memory", "set_memory", "delete_memory",
                "list_knowledge", "add_knowledge", "add_knowledge_file",
                "search_knowledge"} == names


class TestMcpAuditLog:
    async def test_audit_log_empty_initially(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/v1/mcp/audit-log", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_caller_id_filter(self, client: AsyncClient, auth_headers, db_session):
        db_session.add(McpAuditLog(id=uuid.uuid4(), caller_id="slack:U111", tool_name="get_memory", params_summary={}))
        db_session.add(McpAuditLog(id=uuid.uuid4(), caller_id="slack:U999", tool_name="list_memory", params_summary={}))
        await db_session.commit()

        resp = await client.get("/api/v1/mcp/audit-log?caller_id=slack:U111", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["caller_id"] == "slack:U111"


class TestMcpAuth:
    async def test_no_api_key_returns_503(self, client: AsyncClient, monkeypatch):
        monkeypatch.delenv("MCP_API_KEY", raising=False)
        resp = await client.post("/mcp/", json={})
        assert resp.status_code == 503

    async def test_wrong_api_key_returns_401(self, client: AsyncClient, monkeypatch):
        monkeypatch.setenv("MCP_API_KEY", "secret-key")
        resp = await client.post("/mcp/", headers={"X-MCP-API-Key": "wrong-key"}, json={})
        assert resp.status_code == 401