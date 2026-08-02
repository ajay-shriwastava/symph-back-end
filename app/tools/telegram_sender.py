"""Telegram channel tool — stub until Telegram Bot API integration is built."""

from langchain_core.tools import tool


@tool
def send_telegram(chat_id: str, message: str) -> str:
    """Send a Telegram message to the specified chat.

    Args:
        chat_id: Telegram chat ID or username (e.g. @mychannel or 123456789).
        message: Message text to send.

    Returns:
        Confirmation message or error description.
    """
    raise NotImplementedError(
        "Telegram integration is not yet configured. "
        "Set up a Telegram Bot token (TELEGRAM_BOT_TOKEN env var) and implement this tool."
    )
