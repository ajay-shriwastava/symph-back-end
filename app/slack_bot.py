"""
Slack bot using Socket Mode.

Listens for:
  - Direct messages (message.im)
  - @mentions (app_mention)

Routes each message to the first agent in the DB that has "slack" in its
channels list. Falls back to a default system prompt if no agent is found.

Persists every inbound and outbound message to the messages table.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from slack_sdk.errors import SlackApiError
from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.web.async_client import AsyncWebClient
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.agent import Agent
from app.models.message import Message

logger = logging.getLogger(__name__)

_slack_client: SocketModeClient | None = None


# ---------------------------------------------------------------------------
# Message persistence
# ---------------------------------------------------------------------------

async def _save_message(role: str, content: str, agent_id: uuid.UUID | None, session_id: uuid.UUID) -> None:
    if agent_id is None:
        return  # agent_id is NOT NULL in schema; skip if no agent assigned
    async with AsyncSessionLocal() as db:
        msg = Message(
            id=uuid.uuid4(),
            session_id=session_id,
            agent_id=agent_id,
            role=role,
            content=content,
        )
        db.add(msg)
        await db.commit()


# ---------------------------------------------------------------------------
# Agent lookup
# ---------------------------------------------------------------------------

async def _get_slack_agent() -> Agent | None:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(Agent))).scalars().all()
        for agent in rows:
            channels = agent.channels or []
            if any(c.lower() == "slack" for c in channels):
                return agent
    return None


# ---------------------------------------------------------------------------
# Workflow lookup — find a message-triggered workflow for a given agent
# ---------------------------------------------------------------------------

async def _find_message_workflow(agent: Agent):
    """Return the first message-triggered Workflow whose graph contains this agent's id."""
    from app.models.workflow import Workflow
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        workflows = (
            await db.execute(
                select(Workflow).where(Workflow.trigger_type == "message")
            )
        ).scalars().all()

    agent_id_str = str(agent.id)
    for wf in workflows:
        for node in wf.graph_definition.get("nodes", []):
            if node.get("type") == "agent" and str(node.get("agent_id", "")) == agent_id_str:
                return wf
    return None


# ---------------------------------------------------------------------------
# LLM call (fallback — no workflow configured)
# ---------------------------------------------------------------------------

async def _run_agent_direct(agent: Agent | None, user_text: str) -> str:
    model_id = (agent.model if agent else None) or "claude-haiku-4-5-20251001"
    system_prompt = (agent.system_prompt if agent else None) or "You are a helpful assistant."

    llm = ChatAnthropic(model=model_id)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_text),
    ]
    result = await llm.ainvoke(messages)
    return result.content if hasattr(result, "content") else str(result)


# ---------------------------------------------------------------------------
# Workflow execution via message trigger
# ---------------------------------------------------------------------------

async def _run_via_workflow(workflow, agent: Agent, user_text: str) -> str:
    """Execute a message-triggered workflow and return the final text output."""
    import uuid as _uuid
    from app.database import AsyncSessionLocal
    from app.models.workflow_run import WorkflowRun
    from app.workflow_runner import run_workflow

    run_id = str(_uuid.uuid4())
    workflow_id = str(workflow.id)
    agents_map = {str(agent.id): agent}

    async with AsyncSessionLocal() as db:
        run = WorkflowRun(
            id=_uuid.UUID(run_id),
            workflow_id=workflow.id,
            status="pending",
        )
        db.add(run)
        await db.commit()

        await run_workflow(
            run_id=run_id,
            workflow_id=workflow_id,
            graph_definition=workflow.graph_definition,
            agents_map=agents_map,
            input_data={"input": user_text},
            db=db,
        )

        # Re-fetch final state
        from sqlalchemy import select
        run_obj = (
            await db.execute(select(WorkflowRun).where(WorkflowRun.id == _uuid.UUID(run_id)))
        ).scalar_one_or_none()

        if run_obj and run_obj.output:
            msgs = run_obj.output.get("messages", [])
            if msgs:
                return str(msgs[-1])
        return "Workflow completed."


# ---------------------------------------------------------------------------
# Event handler
# ---------------------------------------------------------------------------

async def _handle_event(client: SocketModeClient, req: SocketModeRequest) -> None:
    # Acknowledge immediately — Slack requires ACK within 3 seconds
    await client.send_socket_mode_response(SocketModeResponse(envelope_id=req.envelope_id))

    payload = req.payload
    event = payload.get("event", {})

    # Ignore bot's own messages
    if event.get("bot_id") or event.get("subtype") == "bot_message":
        return

    user_text = event.get("text", "").strip()
    channel = event.get("channel", "")

    if not user_text or not channel:
        return

    # Strip @mention prefix if present (e.g. "<@U12345> hello" → "hello")
    if user_text.startswith("<@"):
        user_text = user_text.split(">", 1)[-1].strip()

    if not user_text:
        return

    session_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"slack:{channel}")

    agent = await _get_slack_agent()
    agent_id = agent.id if agent else None

    # Persist user message
    await _save_message("user", user_text, agent_id, session_id)

    # Route: use a message-triggered workflow if one exists for this agent
    try:
        workflow = await _find_message_workflow(agent) if agent else None
        if workflow:
            logger.info("Routing Slack message to workflow '%s'", workflow.name)
            reply = await _run_via_workflow(workflow, agent, user_text)
        else:
            reply = await _run_agent_direct(agent, user_text)
    except Exception as exc:
        logger.error("Agent error: %s", exc)
        reply = "Sorry, I encountered an error processing your message."

    # Persist agent reply
    await _save_message("assistant", reply, agent_id, session_id)

    # Send reply to Slack
    web_client: AsyncWebClient = client.web_client
    try:
        await web_client.chat_postMessage(channel=channel, text=reply)
    except SlackApiError as exc:
        logger.error("Slack send error: %s", exc)


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

async def start_slack_bot() -> None:
    bot_token = os.environ.get("SLACK_BOT_TOKEN", "")
    app_token = os.environ.get("SLACK_APP_TOKEN", "")

    if not bot_token or not app_token:
        logger.warning("SLACK_BOT_TOKEN or SLACK_APP_TOKEN not set — Slack bot disabled.")
        return

    if bot_token.startswith("xoxb-your") or app_token.startswith("xapp-your"):
        logger.warning("Slack tokens are placeholders — Slack bot disabled.")
        return

    global _slack_client

    web_client = AsyncWebClient(token=bot_token)
    _slack_client = SocketModeClient(app_token=app_token, web_client=web_client)
    _slack_client.socket_mode_request_listeners.append(_handle_event)

    await _slack_client.connect()
    logger.info("Slack bot connected via Socket Mode.")


async def stop_slack_bot() -> None:
    global _slack_client
    if _slack_client:
        await _slack_client.close()
        _slack_client = None
        logger.info("Slack bot disconnected.")
