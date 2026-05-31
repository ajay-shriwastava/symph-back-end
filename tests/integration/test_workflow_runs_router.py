"""
Integration tests for workflow run endpoints.
Background execution is patched so no real LLM calls are made.
"""
import asyncio
import uuid
from unittest.mock import patch, AsyncMock

import pytest


SIMPLE_GRAPH = {
    "nodes": [
        {"id": "start", "type": "start", "label": "Start", "x": 0,   "y": 0},
        {"id": "end",   "type": "end",   "label": "End",   "x": 100, "y": 0},
    ],
    "edges": [{"id": "e1", "from": "start", "to": "end"}],
}

# Patch target: run_workflow is imported inside the router's _background closure,
# so we patch it at the source module. This lets asyncio.create_task work normally
# (patching create_task breaks SQLAlchemy's session cleanup via asyncio.shield).
_RW_PATCH = "app.workflow_runner.run_workflow"


async def _make_workflow(client, graph=None):
    res = await client.post("/api/v1/workflows",
                            json={"name": "Test WF", "graph_definition": graph or SIMPLE_GRAPH},
                            headers={"Authorization": "Bearer test"})
    assert res.status_code == 201
    return res.json()


async def _start_run(client, workflow_id, input_data=None):
    """Start a run with run_workflow mocked; wait for background task to finish."""
    with patch(_RW_PATCH, AsyncMock(return_value=None)):
        res = await client.post(f"/api/v1/workflows/{workflow_id}/run",
                                json={"input": input_data or {}},
                                headers={"Authorization": "Bearer test"})
    await asyncio.sleep(0.1)  # let background task complete
    return res


class TestStartRun:
    async def test_start_run_returns_pending(self, client):
        wf = await _make_workflow(client)
        res = await _start_run(client, wf["id"])
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "pending"
        assert data["workflow_id"] == wf["id"]
        assert uuid.UUID(data["id"])
        assert data["created_at"] is not None

    async def test_start_run_nonexistent_workflow_returns_404(self, client):
        res = await client.post(f"/api/v1/workflows/{uuid.uuid4()}/run",
                                json={"input": {}},
                                headers={"Authorization": "Bearer test"})
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    async def test_start_run_with_input_data(self, client):
        wf = await _make_workflow(client)
        res = await _start_run(client, wf["id"], input_data={"message": "go"})
        assert res.status_code == 201
        assert res.json()["input"] == {"message": "go"}

    async def test_start_run_empty_body(self, client):
        wf = await _make_workflow(client)
        with patch(_RW_PATCH, AsyncMock(return_value=None)):
            res = await client.post(f"/api/v1/workflows/{wf['id']}/run",
                                    json={},
                                    headers={"Authorization": "Bearer test"})
        await asyncio.sleep(0.1)
        assert res.status_code == 201


class TestListRuns:
    async def test_empty_list(self, client):
        wf = await _make_workflow(client)
        res = await client.get(f"/api/v1/workflows/{wf['id']}/runs",
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_lists_runs_for_workflow(self, client):
        wf = await _make_workflow(client)
        await _start_run(client, wf["id"])
        await _start_run(client, wf["id"])

        res = await client.get(f"/api/v1/workflows/{wf['id']}/runs",
                               headers={"Authorization": "Bearer test"})
        data = res.json()
        assert data["total"] == 2
        assert all(r["workflow_id"] == wf["id"] for r in data["items"])

    async def test_list_runs_nonexistent_workflow_returns_404(self, client):
        res = await client.get(f"/api/v1/workflows/{uuid.uuid4()}/runs",
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 404

    async def test_runs_ordered_newest_first(self, client):
        wf = await _make_workflow(client)
        r1 = await _start_run(client, wf["id"])
        r2 = await _start_run(client, wf["id"])

        res = await client.get(f"/api/v1/workflows/{wf['id']}/runs",
                               headers={"Authorization": "Bearer test"})
        items = res.json()["items"]
        # Most recent first
        assert items[0]["id"] == r2.json()["id"]


class TestGetRun:
    async def test_get_existing_run(self, client):
        wf = await _make_workflow(client)
        run_res = await _start_run(client, wf["id"])
        run_id = run_res.json()["id"]

        res = await client.get(f"/api/v1/workflows/{wf['id']}/runs/{run_id}",
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 200
        assert res.json()["id"] == run_id
        assert res.json()["workflow_id"] == wf["id"]

    async def test_get_nonexistent_run_returns_404(self, client):
        wf = await _make_workflow(client)
        res = await client.get(f"/api/v1/workflows/{wf['id']}/runs/{uuid.uuid4()}",
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 404

    async def test_run_belongs_to_correct_workflow(self, client):
        wf_a = await _make_workflow(client)
        wf_b = await _make_workflow(client)
        run_res = await _start_run(client, wf_a["id"])
        run_id = run_res.json()["id"]

        # Getting run_a under wf_b should 404
        res = await client.get(f"/api/v1/workflows/{wf_b['id']}/runs/{run_id}",
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 404


class TestWorkflowExecution:
    async def test_start_end_workflow_completes(self, client):
        """
        Run a real Start→End graph (no agents, no LLM).
        The background task is patched to use the test DB session so status
        updates land in the same DB that the test reads from.
        """
        from tests.conftest import _TestSessionLocal

        wf = await _make_workflow(client, graph=SIMPLE_GRAPH)

        # Redirect the background task's DB session to the test DB.
        # AsyncSessionLocal is imported inside the endpoint & workflow_runner,
        # so we patch it at the source module (app.database).
        with patch("app.database.AsyncSessionLocal", _TestSessionLocal):
            run_res = await client.post(f"/api/v1/workflows/{wf['id']}/run",
                                        json={"input": {}},
                                        headers={"Authorization": "Bearer test"})
        assert run_res.status_code == 201
        run_id = run_res.json()["id"]

        # Give the background task time to finish
        await asyncio.sleep(2)

        res = await client.get(f"/api/v1/workflows/{wf['id']}/runs/{run_id}",
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 200
        assert res.json()["status"] == "completed"
        assert res.json()["finished_at"] is not None
