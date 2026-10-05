"""Outreach Agent - sends emails to new leads and updates their status."""
import logging
from typing import Any, Dict, List

from src.memory.lead_store import LeadStore
from src.tools.email_sender import email_sender

logger = logging.getLogger(__name__)


class OutreachAgent:
    """Takes new leads from the store and sends their outreach emails."""

    def __init__(self):
        self.store = LeadStore()

    def send_to_lead(self, lead: Dict) -> Dict:
        """Send one email to one lead. Returns a result dict."""
        domain = lead.get("domain", "")

        # Parse emails JSON
        import json
        try:
            emails = json.loads(lead.get("emails", "[]")) if isinstance(lead.get("emails"), str) else lead.get("emails", [])
        except Exception:
            emails = []

        if not emails:
            logger.warning("No emails for %s — skipping", domain)
            return {"success": False, "reason": "no_email", "domain": domain}

        to = emails[0]
        subject = lead.get("outreach_subject", "")
        body = lead.get("outreach_body", "")

        if not subject or not body:
            return {"success": False, "reason": "no_draft", "domain": domain}

        result = email_sender.run(to=to, subject=subject, body=body)

        if result.get("success"):
            self.store.mark_emailed(domain)
            logger.info("Emailed %s → %s", domain, to)
        else:
            logger.error("Failed to email %s: %s", domain, result.get("error"))

        return {**result, "domain": domain, "to": to}

    def run(self, max_sends: int = 5) -> Dict[str, Any]:
        """Send outreach emails to up to `max_sends` new leads."""
        new_leads = self.store.get_new_leads()
        logger.info("Found %d new leads in store", len(new_leads))

        if not new_leads:
            return {"success": True, "sent": 0, "failed": 0, "skipped": 0, "results": []}

        results = []
        sent = failed = skipped = 0

        for lead in new_leads[:max_sends]:
            r = self.send_to_lead(lead)
            results.append(r)
            if r.get("success"):
                sent += 1
            elif r.get("reason") in ("no_email", "no_draft"):
                skipped += 1
            else:
                failed += 1

        return {
            "success": True,
            "sent": sent,
            "failed": failed,
            "skipped": skipped,
            "results": results,
            "store_stats": self.store.stats(),
        }


outreach_agent = OutreachAgent()
