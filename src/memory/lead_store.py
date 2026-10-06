"""SQLite-backed lead state store. Prevents duplicate outreach and tracks status."""
import os
import sqlite3
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

DATA_DIR = os.path.join(os.getcwd(), "output")
DB_PATH = os.path.join(DATA_DIR, "leads.db")


SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT UNIQUE NOT NULL,
    title TEXT,
    website TEXT,
    phone TEXT,
    address TEXT,
    rating REAL,
    review_count INTEGER,
    emails TEXT,
    audit_json TEXT,
    outreach_subject TEXT,
    outreach_body TEXT,
    status TEXT DEFAULT 'new',
    first_seen TEXT NOT NULL,
    last_updated TEXT NOT NULL,
    emailed_at TEXT,
    replied_at TEXT,
    notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_domain ON leads(domain);
"""


def _extract_domain(url: str) -> str:
    """Normalize a URL to a bare domain for deduplication."""
    if not url:
        return ""
    return url.replace("https://", "").replace("http://", "").split("/")[0].lower()


class LeadStore:
    """Persistent store for leads with deduplication and status tracking."""

    def __init__(self, db_path: str = DB_PATH):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def exists(self, domain: str) -> bool:
        cur = self.conn.execute("SELECT 1 FROM leads WHERE domain = ?", (domain,))
        return cur.fetchone() is not None

    def upsert_lead(self, lead: Dict[str, Any]) -> str:
        """Insert or update a lead. Returns the domain."""
        domain = _extract_domain(lead.get("website", ""))
        if not domain:
            return ""

        now = datetime.utcnow().isoformat()
        audit = lead.get("audit", {})
        outreach = lead.get("outreach", {})
        emails = lead.get("emails", [])

        existing = self.conn.execute(
            "SELECT id FROM leads WHERE domain = ?", (domain,)
        ).fetchone()

        if existing:
            self.conn.execute(
                """UPDATE leads SET
                    title=?, website=?, phone=?, address=?, rating=?, review_count=?,
                    emails=?, audit_json=?, outreach_subject=?, outreach_body=?,
                    last_updated=?
                WHERE domain=?""",
                (
                    lead.get("title", ""), lead.get("website", ""),
                    lead.get("phone", ""), lead.get("address", ""),
                    float(lead.get("review_rating", 0) or 0),
                    int(lead.get("review_count", 0) or 0),
                    json.dumps(emails), json.dumps(audit),
                    outreach.get("subject", ""), outreach.get("body", ""),
                    now, domain,
                ),
            )
        else:
            self.conn.execute(
                """INSERT INTO leads
                (domain, title, website, phone, address, rating, review_count,
                 emails, audit_json, outreach_subject, outreach_body,
                 status, first_seen, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?, ?)""",
                (
                    domain, lead.get("title", ""), lead.get("website", ""),
                    lead.get("phone", ""), lead.get("address", ""),
                    float(lead.get("review_rating", 0) or 0),
                    int(lead.get("review_count", 0) or 0),
                    json.dumps(emails), json.dumps(audit),
                    outreach.get("subject", ""), outreach.get("body", ""),
                    now, now,
                ),
            )
        self.conn.commit()
        return domain

    def mark_emailed(self, domain: str) -> None:
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            "UPDATE leads SET status='emailed', emailed_at=?, last_updated=? WHERE domain=?",
            (now, now, domain),
        )
        self.conn.commit()

    def mark_replied(self, domain: str, notes: str = "") -> None:
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            "UPDATE leads SET status='replied', replied_at=?, notes=?, last_updated=? WHERE domain=?",
            (now, notes, now, domain),
        )
        self.conn.commit()

    def get_new_leads(self) -> List[Dict]:
        cur = self.conn.execute("SELECT * FROM leads WHERE status='new' ORDER BY rating DESC")
        return [dict(r) for r in cur.fetchall()]

    def get_by_status(self, status: str) -> List[Dict]:
        cur = self.conn.execute("SELECT * FROM leads WHERE status=? ORDER BY rating DESC", (status,))
        return [dict(r) for r in cur.fetchall()]

    def stats(self) -> Dict[str, int]:
        cur = self.conn.execute("SELECT status, COUNT(*) as n FROM leads GROUP BY status")
        return {row["status"]: row["n"] for row in cur.fetchall()}

    def close(self):
        self.conn.close()
