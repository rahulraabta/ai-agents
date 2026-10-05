"""Email Sender tool - sends outreach emails via SMTP (Gmail) or logs in mock mode."""
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Dict, List
from dotenv import load_dotenv
from src.tools.base_tool import BaseTool
load_dotenv()

logger = logging.getLogger(__name__)

MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
FROM_NAME = os.getenv("FROM_NAME", "Your Name")


class EmailSenderTool(BaseTool):
    name = "send_email"
    description = "Send a personalized outreach email to a lead."

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["to", "subject", "body"],
        }

    def _mock_send(self, to: str, subject: str, body: str) -> Dict:
        logger.info("[MOCK] Would send to %s — subject: %s", to, subject)
        return {"success": True, "mode": "mock", "to": to, "subject": subject}

    def _live_send(self, to: str, subject: str, body: str) -> Dict:
        if not SMTP_USER or not SMTP_PASS:
            return {"success": False, "error": "SMTP_USER or SMTP_PASS not set"}

        msg = MIMEMultipart()
        msg["From"] = f"{FROM_NAME} <{SMTP_USER}>"
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
            logger.info("Sent to %s", to)
            return {"success": True, "mode": "live", "to": to, "subject": subject}
        except Exception as e:
            logger.error("Send failed to %s: %s", to, e)
            return {"success": False, "error": str(e), "to": to}

    def run(self, **kwargs) -> Dict[str, Any]:
        to = kwargs.get("to", "").strip()
        subject = kwargs.get("subject", "").strip()
        body = kwargs.get("body", "").strip()

        if not to or not subject or not body:
            return {"success": False, "error": "to, subject, and body are required"}

        if MOCK_MODE:
            return self._mock_send(to, subject, body)
        return self._live_send(to, subject, body)


email_sender = EmailSenderTool()

