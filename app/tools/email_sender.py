"""Email channel tool — stub until SMTP/SendGrid integration is built."""

from langchain_core.tools import tool


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email to the specified recipient.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Email body content (plain text).

    Returns:
        Confirmation message or error description.
    """
    raise NotImplementedError(
        "Email integration is not yet configured. "
        "Set up an SMTP server or SendGrid API key and implement this tool."
    )
