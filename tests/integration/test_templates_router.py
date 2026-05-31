"""
Integration tests for /api/v1/templates
"""
import pytest
from unittest.mock import AsyncMock, patch


class TestListTemplates:
    async def test_returns_list(self, client):
        res = await client.get("/api/v1/templates",
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 2  # data-ingestion-pipeline + sre-job-summary

    async def test_template_fields(self, client):
        res = await client.get("/api/v1/templates",
                               headers={"Authorization": "Bearer test"})
        for tmpl in res.json():
            assert "id" in tmpl
            assert "name" in tmpl
            assert "description" in tmpl
            assert "trigger_type" in tmpl

    async def test_known_templates_present(self, client):
        res = await client.get("/api/v1/templates",
                               headers={"Authorization": "Bearer test"})
        ids = [t["id"] for t in res.json()]
        assert "data-ingestion-pipeline" in ids
        assert "sre-job-summary" in ids


class TestInstantiateTemplate:
    async def test_instantiate_data_ingestion(self, client):
        """data-ingestion-pipeline uses legacy agent_config (singular)."""
        with patch("app.scheduler.register_workflow", AsyncMock()):
            res = await client.post(
                "/api/v1/templates/data-ingestion-pipeline/instantiate",
                headers={"Authorization": "Bearer test"},
            )
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Data Ingestion Pipeline"
        assert data["status"] == "draft"
        assert data["graph_definition"] is not None

        # Agent node should have been patched with a real agent_id
        nodes = data["graph_definition"]["nodes"]
        agent_nodes = [n for n in nodes if n["type"] == "agent"]
        assert len(agent_nodes) == 1
        assert agent_nodes[0]["agent_id"] is not None

    async def test_instantiate_sre_job_summary(self, client):
        """sre-job-summary uses agent_configs (list) — creates two agents."""
        with patch("app.scheduler.register_workflow", AsyncMock()):
            res = await client.post(
                "/api/v1/templates/sre-job-summary/instantiate",
                headers={"Authorization": "Bearer test"},
            )
        assert res.status_code == 201
        data = res.json()
        assert "SRE Job Summary" in data["name"]

        # Both agent nodes should be patched with distinct agent IDs
        nodes = data["graph_definition"]["nodes"]
        agent_nodes = [n for n in nodes if n["type"] == "agent"]
        assert len(agent_nodes) == 2
        ids = [n["agent_id"] for n in agent_nodes]
        assert ids[0] is not None
        assert ids[1] is not None
        assert ids[0] != ids[1]

    async def test_instantiate_nonexistent_template(self, client):
        res = await client.post(
            "/api/v1/templates/nonexistent-template/instantiate",
            headers={"Authorization": "Bearer test"},
        )
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    async def test_each_instantiation_creates_new_workflow(self, client):
        """Calling instantiate twice creates two separate workflows."""
        with patch("app.scheduler.register_workflow", AsyncMock()):
            r1 = await client.post(
                "/api/v1/templates/sre-job-summary/instantiate",
                headers={"Authorization": "Bearer test"},
            )
            r2 = await client.post(
                "/api/v1/templates/sre-job-summary/instantiate",
                headers={"Authorization": "Bearer test"},
            )
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["id"] != r2.json()["id"]

    async def test_instantiated_workflow_visible_in_list(self, client):
        with patch("app.scheduler.register_workflow", AsyncMock()):
            await client.post(
                "/api/v1/templates/data-ingestion-pipeline/instantiate",
                headers={"Authorization": "Bearer test"},
            )
        res = await client.get("/api/v1/workflows",
                               headers={"Authorization": "Bearer test"})
        assert res.json()["total"] >= 1
