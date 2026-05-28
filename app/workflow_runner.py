"""
WorkflowRunner: compiles a graph_definition dict into a LangGraph StateGraph
and executes it, broadcasting WebSocket events at each step.

State keys:
    messages        List[str]   — accumulated text outputs
    current_output  Any         — output of the last node
    condition_result bool       — used by condition nodes for routing
    run_id          str         — UUID string of the current WorkflowRun
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.ws_manager import manager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _broadcast(run_id: str, event: dict) -> None:
    await manager.broadcast(run_id, event)


# ---------------------------------------------------------------------------
# Node factories
# ---------------------------------------------------------------------------

def _make_start_node(run_id: str):
    async def start_node(state: dict) -> dict:
        await _broadcast(run_id, {"event": "node_enter", "node_id": "start", "ts": _now_iso()})
        await _broadcast(run_id, {"event": "node_complete", "node_id": "start", "output": {}, "ts": _now_iso()})
        return state

    return start_node


def _make_end_node(run_id: str):
    async def end_node(state: dict) -> dict:
        await _broadcast(run_id, {"event": "node_enter", "node_id": "end", "ts": _now_iso()})
        await _broadcast(run_id, {"event": "node_complete", "node_id": "end", "output": {}, "ts": _now_iso()})
        return state

    return end_node


MAX_LOOPS = 5  # max times a feedback loop may repeat before forcing exit


def _make_agent_node(node_id: str, system_prompt: str, run_id: str):
    async def agent_node(state: dict) -> dict:
        await _broadcast(run_id, {"event": "node_enter", "node_id": node_id, "ts": _now_iso()})
        llm = ChatAnthropic(model="claude-haiku-4-5-20251001")
        messages_in = [SystemMessage(content=system_prompt or "You are a helpful assistant.")]
        history = state.get("messages", [])
        if history:
            messages_in.append(HumanMessage(content="\n".join(str(m) for m in history)))
        else:
            messages_in.append(HumanMessage(content="Begin."))
        result = await llm.ainvoke(messages_in)
        text = result.content if hasattr(result, "content") else str(result)
        new_messages = list(history) + [text]
        output = {"text": text}
        await _broadcast(run_id, {"event": "node_complete", "node_id": node_id, "output": output, "ts": _now_iso()})
        loop_count = state.get("loop_count", 0) + 1
        # After MAX_LOOPS passes set condition_result=True so the condition exits the loop
        condition_result = True if loop_count >= MAX_LOOPS else state.get("condition_result", False)
        return {**state, "messages": new_messages, "current_output": text,
                "loop_count": loop_count, "condition_result": condition_result}

    return agent_node


def _make_condition_node(node_id: str, run_id: str):
    async def condition_node(state: dict) -> dict:
        await _broadcast(run_id, {"event": "node_enter", "node_id": node_id, "ts": _now_iso()})
        result = bool(state.get("condition_result", False))
        await _broadcast(run_id, {"event": "node_complete", "node_id": node_id,
                                   "output": {"condition_result": result}, "ts": _now_iso()})
        return state

    return condition_node


def _condition_router(node_id: str, true_target: str, false_target: str):
    def router(state: dict) -> str:
        return true_target if bool(state.get("condition_result", False)) else false_target

    return router


# ---------------------------------------------------------------------------
# WorkflowRunner
# ---------------------------------------------------------------------------

class WorkflowRunner:
    @staticmethod
    def compile(
        graph_definition: Dict[str, Any],
        agents_map: Dict[str, Any],
        run_id: str,
    ) -> StateGraph:
        """
        Compile graph_definition into a LangGraph StateGraph.

        agents_map: dict of agent_id -> Agent ORM object (or dict with system_prompt)
        """
        nodes = graph_definition.get("nodes", [])
        edges = graph_definition.get("edges", [])

        # Build id -> node lookup
        node_map = {n["id"]: n for n in nodes}

        # Build edges: from -> list of (to, branch)
        from typing import DefaultDict
        from collections import defaultdict as _defaultdict

        out_edges: DefaultDict[str, list] = _defaultdict(list)
        for e in edges:
            out_edges[e["from"]].append(e)

        # Determine entry point
        entry_id = next((n["id"] for n in nodes if n["type"] == "start"), None)
        if not entry_id:
            raise ValueError("graph_definition has no start node")

        graph = StateGraph(dict)

        # Register nodes
        for node in nodes:
            nid = node["id"]
            ntype = node["type"]
            if ntype == "start":
                graph.add_node(nid, _make_start_node(run_id))
            elif ntype == "end":
                graph.add_node(nid, _make_end_node(run_id))
            elif ntype == "agent":
                agent_id = node.get("agent_id")
                agent_obj = agents_map.get(str(agent_id)) if agent_id else None
                system_prompt = ""
                if agent_obj:
                    system_prompt = (
                        agent_obj.system_prompt
                        if hasattr(agent_obj, "system_prompt")
                        else agent_obj.get("system_prompt", "")
                    ) or ""
                graph.add_node(nid, _make_agent_node(nid, system_prompt, run_id))
            elif ntype == "condition":
                graph.add_node(nid, _make_condition_node(nid, run_id))

        # Register edges
        for node in nodes:
            nid = node["id"]
            ntype = node["type"]
            node_out = out_edges.get(nid, [])

            if ntype == "end" or not node_out:
                # Terminal — connect to LangGraph END if no outgoing edges
                if ntype == "end":
                    graph.add_edge(nid, END)
                continue

            if ntype == "condition":
                # Find true and false targets
                true_edge = next((e for e in node_out if e.get("branch") == "true"), None)
                false_edge = next((e for e in node_out if e.get("branch") == "false"), None)
                true_target = true_edge["to"] if true_edge else END
                false_target = false_edge["to"] if false_edge else END
                # Map targets: "end" node id -> END if the target is actually an end node
                def _resolve(target):
                    if target != END and node_map.get(target, {}).get("type") == "end":
                        return target  # keep as node id; the end node itself connects to END
                    return target

                graph.add_conditional_edges(
                    nid,
                    _condition_router(nid, _resolve(true_target), _resolve(false_target)),
                )
            else:
                # Normal node: take first outgoing edge (simple linear flow)
                # For multiple outgoing edges without branches, add each
                for e in node_out:
                    graph.add_edge(nid, e["to"])

        graph.set_entry_point(entry_id)
        return graph


async def run_workflow(
    run_id: str,
    workflow_id: str,
    graph_definition: Dict[str, Any],
    agents_map: Dict[str, Any],
    input_data: Dict[str, Any],
    db: AsyncSession,
) -> None:
    """
    Execute the compiled workflow graph. Updates WorkflowRun record on
    completion or failure. Broadcasts WebSocket events throughout.
    """
    from app.models.workflow_run import WorkflowRun
    from sqlalchemy import select

    async def _update_run(**kwargs):
        run_obj = (
            await db.execute(
                select(WorkflowRun).where(WorkflowRun.id == uuid.UUID(run_id))
            )
        ).scalar_one_or_none()
        if run_obj:
            for k, v in kwargs.items():
                setattr(run_obj, k, v)
            await db.commit()

    try:
        await _update_run(
            status="running",
            started_at=datetime.now(timezone.utc),
        )

        compiled = WorkflowRunner.compile(graph_definition, agents_map, run_id)
        app_graph = compiled.compile()

        initial_state = {
            "messages": [],
            "current_output": None,
            "condition_result": input_data.get("condition_result", False),
            "loop_count": 0,
            "run_id": run_id,
        }

        final_state = await app_graph.ainvoke(
            initial_state,
            config={"recursion_limit": MAX_LOOPS * 10 + 20},
        )
        output = {"messages": final_state.get("messages", []), "current_output": final_state.get("current_output")}

        await _update_run(
            status="completed",
            output=output,
            finished_at=datetime.now(timezone.utc),
        )
        await _broadcast(
            run_id,
            {"event": "run_complete", "status": "completed", "output": output, "ts": _now_iso()},
        )

    except Exception as exc:
        error_msg = str(exc)
        await _update_run(
            status="failed",
            error=error_msg,
            finished_at=datetime.now(timezone.utc),
        )
        await _broadcast(run_id, {"event": "run_error", "error": error_msg, "ts": _now_iso()})
