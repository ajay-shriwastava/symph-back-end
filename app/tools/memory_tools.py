"""
memory_tools — agent-bound remember / forget LangChain tools.

Not added to TOOL_REGISTRY (which holds static instances).
Call make_memory_tools(agent_id) inside _make_agent_node to get tool
instances bound to the specific agent being executed.
"""
import logging
import uuid as _uuid

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def make_memory_tools(agent_id: str) -> list:
    """Return [remember, forget] tools bound to agent_id."""

    @tool
    async def remember(key: str, value: str) -> str:
        """Store or update a fact in this agent's memory for use in future runs."""
        from app.database import AsyncSessionLocal
        from app.models.memory import AgentMemory
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlalchemy import func

        try:
            async with AsyncSessionLocal() as db:
                stmt = (
                    pg_insert(AgentMemory)
                    .values(
                        id=_uuid.uuid4(),
                        agent_id=_uuid.UUID(agent_id),
                        key=key,
                        value=value,
                    )
                    .on_conflict_do_update(
                        constraint="uq_agent_memory_agent_key",
                        set_={"value": value, "updated_at": func.now()},
                    )
                )
                await db.execute(stmt)
                await db.commit()
            return f"Remembered: {key}"
        except Exception as exc:
            logger.warning("remember tool failed for agent %s: %s", agent_id, exc)
            return f"Failed to remember '{key}': {exc}"

    @tool
    async def forget(key: str) -> str:
        """Delete a fact from this agent's memory by key."""
        from app.database import AsyncSessionLocal
        from app.models.memory import AgentMemory
        from sqlalchemy import delete

        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    delete(AgentMemory).where(
                        AgentMemory.agent_id == _uuid.UUID(agent_id),
                        AgentMemory.key == key,
                    )
                )
                await db.commit()
            return f"Forgot: {key}"
        except Exception as exc:
            logger.warning("forget tool failed for agent %s: %s", agent_id, exc)
            return f"Failed to forget '{key}': {exc}"

    return [remember, forget]
