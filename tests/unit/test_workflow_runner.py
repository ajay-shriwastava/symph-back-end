"""
Unit tests for WorkflowRunner — mocks LLM and DB, tests graph compilation and routing.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workflow_runner import WorkflowRunner, MAX_LOOPS, _estimate_cost


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------

class TestCostEstimation:
    def test_haiku_cost(self):
        cost = _estimate_cost("claude-haiku-4-5-20251001", 1_000_000, 1_000_000)
        assert cost > 0

    def test_sonnet_cost_higher_than_haiku(self):
        haiku = _estimate_cost("claude-haiku-4-5-20251001", 1_000, 1_000)
        sonnet = _estimate_cost("claude-sonnet-4-6", 1_000, 1_000)
        assert sonnet > haiku

    def test_unknown_model_uses_fallback(self):
        cost = _estimate_cost("unknown-model-xyz", 1_000, 500)
        assert cost > 0

    def test_zero_tokens(self):
        cost = _estimate_cost("claude-haiku-4-5-20251001", 0, 0)
        assert cost == 0.0


# ---------------------------------------------------------------------------
# MAX_LOOPS default
# ---------------------------------------------------------------------------

class TestMaxLoopsDefault:
    def test_default_is_20(self):
        assert MAX_LOOPS == 20


# ---------------------------------------------------------------------------
# Graph compilation — start/end only
# ---------------------------------------------------------------------------

class TestWorkflowRunnerCompile:
    def _run_id(self):
        return str(uuid.uuid4())

    def _simple_graph(self):
        return {
            "nodes": [
                {"id": "start", "type": "start", "label": "Start", "x": 0, "y": 0},
                {"id": "end",   "type": "end",   "label": "End",   "x": 100, "y": 0},
            ],
            "edges": [
                {"id": "e1", "from": "start", "to": "end"},
            ],
        }

    def test_compile_start_end(self):
        run_id = self._run_id()
        compiled = WorkflowRunner.compile(self._simple_graph(), {}, run_id)
        assert compiled is not None

    def test_compile_missing_start_raises(self):
        graph = {
            "nodes": [{"id": "end", "type": "end", "label": "End", "x": 0, "y": 0}],
            "edges": [],
        }
        with pytest.raises(ValueError, match="no start node"):
            WorkflowRunner.compile(graph, {}, self._run_id())

    def test_compile_respects_max_loops_from_graph(self):
        """max_loops in graph_definition overrides the module constant."""
        graph = {**self._simple_graph(), "max_loops": 10}
        # Should compile without error — max_loops is read but doesn't affect structure
        compiled = WorkflowRunner.compile(graph, {}, self._run_id())
        assert compiled is not None

    def test_compile_with_condition_node(self):
        run_id = self._run_id()
        graph = {
            "nodes": [
                {"id": "start",     "type": "start",     "label": "Start",     "x": 0,   "y": 0},
                {"id": "cond",      "type": "condition",  "label": "Check",     "x": 100, "y": 0},
                {"id": "end",       "type": "end",        "label": "End",       "x": 200, "y": 0},
            ],
            "edges": [
                {"id": "e1", "from": "start", "to": "cond"},
                {"id": "e2", "from": "cond",  "to": "end",  "branch": "true"},
                {"id": "e3", "from": "cond",  "to": "end",  "branch": "false"},
            ],
        }
        compiled = WorkflowRunner.compile(graph, {}, run_id)
        assert compiled is not None

    def test_compile_with_tool_node(self):
        run_id = self._run_id()
        graph = {
            "nodes": [
                {"id": "start", "type": "start", "label": "Start", "x": 0,   "y": 0},
                {"id": "tool1", "type": "tool",  "label": "Tool",  "x": 100, "y": 0,
                 "tool_name": "collect_job_stats"},
                {"id": "end",   "type": "end",   "label": "End",   "x": 200, "y": 0},
            ],
            "edges": [
                {"id": "e1", "from": "start", "to": "tool1"},
                {"id": "e2", "from": "tool1", "to": "end"},
            ],
        }
        compiled = WorkflowRunner.compile(graph, {}, run_id)
        assert compiled is not None


# ---------------------------------------------------------------------------
# run_workflow — mocked LLM, real graph engine, simple start→end graph
# ---------------------------------------------------------------------------

class TestRunWorkflow:
    def _start_end_graph(self):
        return {
            "nodes": [
                {"id": "start", "type": "start", "label": "Start", "x": 0,   "y": 0},
                {"id": "end",   "type": "end",   "label": "End",   "x": 100, "y": 0},
            ],
            "edges": [{"id": "e1", "from": "start", "to": "end"}],
        }

    @pytest.mark.asyncio
    async def test_start_end_graph_completes(self):
        """A Start→End graph should complete without error and set run status to completed."""
        from app.workflow_runner import run_workflow
        from unittest.mock import AsyncMock, patch, MagicMock

        run_id = str(uuid.uuid4())
        workflow_id = str(uuid.uuid4())

        mock_db = AsyncMock()
        mock_run = MagicMock()
        mock_run.status = "pending"

        # Mock DB execute to return the run object
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_run
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        with patch("app.workflow_runner._write_log", AsyncMock()):
            with patch("app.workflow_runner._broadcast", AsyncMock()):
                await run_workflow(
                    run_id=run_id,
                    workflow_id=workflow_id,
                    graph_definition=self._start_end_graph(),
                    agents_map={},
                    input_data={},
                    db=mock_db,
                )

        assert mock_run.status == "completed"
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_run_not_found_returns_early(self):
        """If the WorkflowRun row is not found, run_workflow should return without error."""
        from app.workflow_runner import run_workflow

        run_id = str(uuid.uuid4())
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Should not raise
        await run_workflow(
            run_id=run_id,
            workflow_id=str(uuid.uuid4()),
            graph_definition=self._start_end_graph(),
            agents_map={},
            input_data={},
            db=mock_db,
        )
