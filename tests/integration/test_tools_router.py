"""
Integration tests for GET /api/v1/tools/params
"""
import pytest

from app.tools import TOOL_PARAMS


class TestGetToolParams:
    async def test_returns_200(self, client):
        res = await client.get("/api/v1/tools/params",
                               headers={"Authorization": "Bearer test"})
        assert res.status_code == 200

    async def test_returns_dict(self, client):
        res = await client.get("/api/v1/tools/params",
                               headers={"Authorization": "Bearer test"})
        data = res.json()
        assert isinstance(data, dict)

    async def test_known_tools_present(self, client):
        res = await client.get("/api/v1/tools/params",
                               headers={"Authorization": "Bearer test"})
        data = res.json()
        for tool in ("scan_csv", "csv_scanner", "publish_report", "product_universe_filter"):
            assert tool in data, f"{tool} missing from /api/v1/tools/params"

    async def test_param_shape(self, client):
        """Each param entry has name, label, type, required."""
        res = await client.get("/api/v1/tools/params",
                               headers={"Authorization": "Bearer test"})
        data = res.json()
        for tool_name, params in data.items():
            assert isinstance(params, list), f"{tool_name} params should be a list"
            for p in params:
                assert "name" in p
                assert "label" in p
                assert "type" in p
                assert "required" in p

    async def test_matches_tool_params_constant(self, client):
        res = await client.get("/api/v1/tools/params",
                               headers={"Authorization": "Bearer test"})
        assert res.json() == TOOL_PARAMS
