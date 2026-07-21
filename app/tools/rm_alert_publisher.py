"""
rm_alert_publisher — LangChain @tool (TOOL_REGISTRY)

Publishes RM-ready portfolio recommendations to a Slack channel.
Used by the RM Recommendation Writer agent node.

Consolidates all investor alerts into a single Slack message grouped by investor.
Long messages are chunked to respect Slack's 4000-character limit.
"""

import logging
import os

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

SLACK_REPORT_CHANNEL = os.environ.get("SLACK_REPORT_CHANNEL", "portfolio-reco")


def _chunk_message(text: str, max_chars: int = 3500) -> list[str]:
    """Split on double-newlines to keep investor blocks intact."""
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    current_parts: list[str] = []
    current_len = 0
    for para in text.split("\n\n"):
        segment_len = len(para) + 2
        if current_len + segment_len > max_chars and current_parts:
            chunks.append("\n\n".join(current_parts))
            current_parts, current_len = [], 0
        current_parts.append(para)
        current_len += segment_len
    if current_parts:
        chunks.append("\n\n".join(current_parts))
    return chunks


@tool
async def publish_rm_alert(
    recommendations: str,
    slack_channel: str = "",
    event_title: str = "Market Alert — Portfolio Action Required",
) -> str:
    """Publish RM-ready portfolio recommendations to a Slack channel.
    Posts a consolidated message grouped by investor — each block under 60 words
    so the RM can review it in under 30 seconds.
    recommendations: formatted per-investor recommendation text.
    slack_channel: target channel name without # (defaults to SLACK_REPORT_CHANNEL env var).
    event_title: header for the Slack message.
    Returns: confirmation string indicating what was posted."""
    channel   = slack_channel or SLACK_REPORT_CHANNEL
    bot_token = os.environ.get("SLACK_BOT_TOKEN", "")

    if not bot_token:
        logger.warning("SLACK_BOT_TOKEN not set — RM alert not sent.")
        return "RM alert not sent — SLACK_BOT_TOKEN missing."

    if not channel:
        logger.warning("No Slack channel configured — RM alert not sent.")
        return "RM alert not sent — no Slack channel configured."

    try:
        from slack_sdk.web.async_client import AsyncWebClient
        client = AsyncWebClient(token=bot_token)
        chunks = _chunk_message(recommendations)

        for i, chunk in enumerate(chunks):
            if i == 0:
                text = f"*🔔 {event_title}*\n\n{chunk}"
            else:
                text = f"*{event_title} (cont. {i + 1}/{len(chunks)})*\n\n{chunk}"
            await client.chat_postMessage(channel=channel, text=text)

        logger.info(
            "RM alert posted to #%s — %d message(s), %d chars total",
            channel, len(chunks), len(recommendations),
        )
        return f"RM alert posted to #{channel} ({len(chunks)} message(s))."

    except Exception as exc:
        logger.warning("Failed to post RM alert to Slack: %s", exc)
        return f"RM alert failed: {exc}"


async def run(state: dict) -> dict:
    recommendations = state.get("current_output", "")
    channel         = state.get("slack_channel") or SLACK_REPORT_CHANNEL
    event_title     = state.get("event_title", "Market Alert — Portfolio Action Required")
    result = await publish_rm_alert.ainvoke({
        "recommendations": recommendations,
        "slack_channel":   channel,
        "event_title":     event_title,
    })
    return {
        **state,
        "messages":      list(state.get("messages", [])) + [result],
        "rm_alert_sent": result,
    }
