"""
Webhook Service
---------------
Sends a trip summary email via Resend after a completed agent run.
Called fire-and-forget from agent_runner — a failure here never
breaks the main response stream.
"""

import structlog
import resend

from app.config import get_settings
from app.database.db import AgentRun, User

log = structlog.get_logger()


def _build_html(user: User, run: AgentRun) -> str:
    """Build a clean HTML email body from the agent run data."""
    tools_list = "".join(f"<li>{t}</li>" for t in (run.tools_used or []))
    # Convert markdown newlines to <br> for email readability
    response_html = (run.response or "No response recorded.").replace("\n", "<br>")

    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 640px; margin: auto; color: #333;">
        <h2 style="color: #2563eb;">Your Travel Plan is Ready ✈️</h2>
        <p>Hi {user.email},</p>
        <p>Here is the travel plan generated for your query:</p>

        <blockquote style="border-left: 4px solid #2563eb; padding-left: 12px; color: #555;">
            {run.query}
        </blockquote>

        <hr style="border: none; border-top: 1px solid #eee;" />

        <div style="line-height: 1.7;">
            {response_html}
        </div>

        <hr style="border: none; border-top: 1px solid #eee;" />

        <p style="font-size: 0.85em; color: #888;">
            Tools used: <ul style="margin: 4px 0;">{tools_list}</ul>
            Tokens used: {run.haiku_tokens + run.sonnet_tokens}
        </p>

        <p style="font-size: 0.8em; color: #aaa;">
            Sent by AI Travel Planner · You received this because you enabled email summaries.
        </p>
    </body>
    </html>
    """


async def send_trip_summary(user: User, run: AgentRun) -> None:
    """
    Send the completed trip plan to the user's webhook_email.
    Logs errors but never raises — caller must not await this in a critical path.
    """
    if not user.webhook_email:
        return
    await send_to_email(user, run, user.webhook_email)


async def send_to_email(user: User, run: AgentRun, email: str) -> None:
    """Send a trip plan to an explicit email address (used by the on-demand endpoint)."""
    settings = get_settings()

    if not settings.resend_api_key:
        log.warning("webhook.skipped", reason="RESEND_API_KEY not set")
        return

    try:
        resend.api_key = settings.resend_api_key

        resend.Emails.send({
            "from": settings.resend_from_email,
            "to": [email],
            "subject": f"Your travel plan: {run.query[:60]}{'...' if len(run.query) > 60 else ''}",
            "html": _build_html(user, run),
        })

        log.info("webhook.sent", to=email, run_id=str(run.id))

    except Exception as exc:
        log.error("webhook.failed", error=str(exc), run_id=str(run.id))
