"""WhatsApp channel tool — stub until Twilio/WhatsApp Business API integration is built."""

from langchain_core.tools import tool


@tool
def send_whatsapp(to: str, message: str) -> str:
    """Send a WhatsApp message to the specified phone number.

    Args:
        to: Recipient phone number in E.164 format (e.g. +14155238886).
        message: Message text to send.

    Returns:
        Confirmation message or error description.
    """
    raise NotImplementedError(
        "WhatsApp integration is not yet configured. "
        "Set up a Twilio account or WhatsApp Business API credentials and implement this tool."
    )
