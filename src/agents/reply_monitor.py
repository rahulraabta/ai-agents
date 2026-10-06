"""Reply Monitor Agent - fetches replies from Gmail, classifies them, and updates the store."""
import os
import json
import email
import imaplib
import logging
from email.header import decode_header
from datetime import datetime, timedelta
from typing import Any, Dict, List

from src.memory.lead_store import LeadStore
from src.providers.llm_router import get_router

logger = logging.getLogger(__name__)

MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"
IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
IMAP_USER = os.getenv("IMAP_USER", "")
IMAP_PASS = os.getenv("IMAP_PASS", "")

CLASSIFIER_SYSTEM = (
    "You are an email classifier for a B2B outreach pipeline. "
    "Read the reply and return ONLY valid JSON with keys: "
    "'intent' (one of: interested, meeting_request, not_interested, question, unsubscribe), "
    "'sentiment' (positive, neutral, negative), "
    "'summary' (one sentence in plain English), "
    "'suggested_reply' (a short, warm, professional draft reply)."
)


class ReplyMonitorAgent:
    """Fetches Gmail replies, classifies intent, and updates lead status."""

    def __init__(self):
        self.store = LeadStore()
        self.router = get_router()

    def _mock_replies(self) -> List[Dict]:
        return [
            {
                "from": "info@urbansmiles.com.ph",
                "subject": "Re: Quick thought on your booking page",
                "body": (
                    "Hi, thanks for reaching out. We're actually looking into adding "
                    "online booking. Can you send over the demo? Also, what would this cost?"
                ),
            },
            {
                "from": "info@clinic7769.com.ph",
                "subject": "Re: Quick thought on clinic7769.com.ph",
                "body": "Not interested, please remove me from your list.",
            },
            {
                "from": "contact@clinic7768.com.ph",
                "subject": "Re: Quick thought on clinic7768.com.ph",
                "body": "Sounds interesting. Can we schedule a call next Tuesday at 10am?",
            },
        ]

    def _fetch_live_replies(self, days_back: int = 7) -> List[Dict]:
        if not IMAP_USER or not IMAP_PASS:
            raise ValueError("IMAP_USER or IMAP_PASS not set in .env")

        replies = []
        since = (datetime.utcnow() - timedelta(days=days_back)).strftime("%d-%b-%Y")

        with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT) as mail:
            mail.login(IMAP_USER, IMAP_PASS)
            mail.select("INBOX")
            status, messages = mail.search(None, f'(SINCE "{since}")')
            if status != "OK":
                return []
            for num in messages[0].split():
                try:
                    status, data = mail.fetch(num, "(RFC822)")
                    if status != "OK":
                        continue
                    msg = email.message_from_bytes(data[0][1])
                    from_addr = msg.get("From", "")
                    subject = self._decode_header(msg.get("Subject", ""))

                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                try:
                                    body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                                    break
                                except Exception:
                                    continue
                    else:
                        try:
                            body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                        except Exception:
                            body = str(msg.get_payload())

                    replies.append({"from": from_addr, "subject": subject, "body": body[:2000]})
                except Exception as e:
                    logger.warning("Failed to parse email %s: %s", num, e)
                    continue
        return replies

    @staticmethod
    def _decode_header(raw: str) -> str:
        try:
            parts = decode_header(raw)
            decoded = ""
            for content, charset in parts:
                if isinstance(content, bytes):
                    decoded += content.decode(charset or "utf-8", errors="ignore")
                else:
                    decoded += content
            return decoded
        except Exception:
            return raw

    @staticmethod
    def _extract_email(from_header: str) -> str:
        if "<" in from_header and ">" in from_header:
            return from_header.split("<")[1].split(">")[0].strip().lower()
        return from_header.strip().lower()

    def _classify(self, reply: Dict) -> Dict:
        prompt = (
            f"From: {reply['from']}\n"
            f"Subject: {reply['subject']}\n\n"
            f"Body:\n{reply['body'][:1500]}\n\n"
            "Classify this reply. Return JSON only."
        )
        result = self.router.ask(prompt, system=CLASSIFIER_SYSTEM, max_tokens=400)
        if not result["success"]:
            return {"intent": "unknown", "sentiment": "neutral",
                    "summary": "classification failed", "suggested_reply": ""}

        import re
        text = re.sub(r"^```(?:json)?|```$", "", result["text"].strip(), flags=re.MULTILINE).strip()
        try:
            parsed = json.loads(text)
            return {
                "intent": parsed.get("intent", "unknown"),
                "sentiment": parsed.get("sentiment", "neutral"),
                "summary": parsed.get("summary", ""),
                "suggested_reply": parsed.get("suggested_reply", ""),
                "provider": result["provider"],
            }
        except Exception as e:
            logger.warning("Classifier JSON parse failed: %s", e)
            return {"intent": "unknown", "sentiment": "neutral",
                    "summary": "parse failed", "suggested_reply": ""}

    def _find_lead_domain(self, from_email: str) -> str:
        if "@" not in from_email:
            return ""
        domain = from_email.split("@")[1].lower()
        cur = self.store.conn.execute("SELECT domain FROM leads WHERE domain = ?", (domain,)).fetchone()
        if cur:
            return cur["domain"]
        cur = self.store.conn.execute("SELECT domain FROM leads WHERE ? LIKE '%' || domain", (domain,)).fetchone()
        return cur["domain"] if cur else ""

    def run(self, days_back: int = 7) -> Dict[str, Any]:
        logger.info("Reply Monitor started (mock=%s)", MOCK_MODE)
        replies = self._mock_replies() if MOCK_MODE else self._fetch_live_replies(days_back)
        logger.info("Found %d replies", len(replies))

        classified = []
        matched = 0
        unmatched = 0

        for reply in replies:
            from_email = self._extract_email(reply["from"])
            domain = self._find_lead_domain(from_email)
            classification = self._classify(reply)

            record = {
                "from": from_email,
                "subject": reply["subject"],
                "domain": domain,
                "intent": classification["intent"],
                "sentiment": classification["sentiment"],
                "summary": classification["summary"],
                "suggested_reply": classification["suggested_reply"],
            }
            classified.append(record)

            if domain:
                matched += 1
                notes = json.dumps(record, ensure_ascii=False)
                if classification["intent"] in ("interested", "meeting_request", "question"):
                    self.store.mark_replied(domain, notes)
                elif classification["intent"] == "unsubscribe":
                    self.store.conn.execute(
                        "UPDATE leads SET status='unsubscribed', notes=?, last_updated=? WHERE domain=?",
                        (notes, datetime.utcnow().isoformat(), domain),
                    )
                    self.store.conn.commit()
                elif classification["intent"] == "not_interested":
                    self.store.conn.execute(
                        "UPDATE leads SET status='not_interested', notes=?, last_updated=? WHERE domain=?",
                        (notes, datetime.utcnow().isoformat(), domain),
                    )
                    self.store.conn.commit()
            else:
                unmatched += 1

        return {
            "success": True,
            "found": len(replies),
            "matched": matched,
            "unmatched": unmatched,
            "replies": classified,
            "store_stats": self.store.stats(),
        }


reply_monitor = ReplyMonitorAgent()