"""
Unit tests for the tool_config ContextVar — verifies isolation between calls.
"""
import asyncio
import pytest

from app.tools.tool_context import tool_config


class TestToolContextVar:
    def test_default_is_empty_dict(self):
        assert tool_config.get() == {}

    def test_set_and_reset(self):
        token = tool_config.set({"scan_csv": {"dataset_dir": "/tmp/data"}})
        try:
            assert tool_config.get() == {"scan_csv": {"dataset_dir": "/tmp/data"}}
        finally:
            tool_config.reset(token)
        assert tool_config.get() == {}

    def test_nested_set(self):
        outer = tool_config.set({"publish_report": {"slack_channel": "general"}})
        try:
            inner = tool_config.set({"publish_report": {"slack_channel": "dev"}})
            try:
                assert tool_config.get()["publish_report"]["slack_channel"] == "dev"
            finally:
                tool_config.reset(inner)
            assert tool_config.get()["publish_report"]["slack_channel"] == "general"
        finally:
            tool_config.reset(outer)

    @pytest.mark.asyncio
    async def test_async_tasks_are_isolated(self):
        """Two concurrent coroutines each see their own ContextVar value."""
        results: dict = {}

        async def task_a():
            token = tool_config.set({"scan_csv": {"dataset_dir": "/a"}})
            await asyncio.sleep(0)  # yield, let task_b run
            results["a"] = tool_config.get().get("scan_csv", {}).get("dataset_dir")
            tool_config.reset(token)

        async def task_b():
            token = tool_config.set({"scan_csv": {"dataset_dir": "/b"}})
            await asyncio.sleep(0)
            results["b"] = tool_config.get().get("scan_csv", {}).get("dataset_dir")
            tool_config.reset(token)

        await asyncio.gather(task_a(), task_b())
        assert results["a"] == "/a"
        assert results["b"] == "/b"
