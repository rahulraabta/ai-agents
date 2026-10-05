"""Day Agent - orchestrates scraping, auditing, and outreach with deduplication."""
import json
import os
import logging
from datetime import datetime
from typing import Any, Dict, List

from src.tools.lead_scraper import lead_scraper
from src.tools.website_auditor import website_auditor
from src.tools.email_extractor import email_extractor
from src.agents.email_writer import write_outreach_email
from src.memory.lead_store import LeadStore, _extract_domain

logger = logging.getLogger(__name__)
DATA_DIR = os.path.join(os.getcwd(), "data")


class DayAgent:
    """The main worker with deduplication via LeadStore."""

    def __init__(self, min_rating: float = 4.0):
        self.min_rating = min_rating
        self.store = LeadStore()

    def _passes_filter(self, lead: Dict) -> bool:
        try:
            rating = float(lead.get("review_rating", 0))
        except (ValueError, TypeError):
            return False
        return rating >= self.min_rating

    def enrich_lead(self, lead: Dict) -> Dict:
        website = lead.get("website", "")
        business_type = lead.get("query", "business")

        if not website:
            lead["audit"] = {"problems": [], "summary": "No website"}
            lead["emails"] = []
            lead["outreach"] = {"subject": "", "body": ""}
            return lead

        audit_result = website_auditor.run(url=website, business_type=business_type)
        lead["audit"] = audit_result.get("data", {})

        email_result = email_extractor.run(url=website)
        lead["emails"] = email_result.get("data", [])

        if audit_result.get("success"):
            outreach = write_outreach_email(lead, lead["audit"])
            lead["outreach"] = {
                "subject": outreach.get("subject", ""),
                "body": outreach.get("body", ""),
                "provider": outreach.get("provider", ""),
            }
        else:
            lead["outreach"] = {"subject": "", "body": ""}

        return lead

    def run(self, query: str, max_leads: int = 10, skip_known: bool = True) -> Dict[str, Any]:
        started = datetime.utcnow().isoformat()
        logger.info("Day Agent started: query=%s, max_leads=%d, skip_known=%s",
                    query, max_leads, skip_known)

        scrape = lead_scraper.run(query=query, max_results=max_leads * 3)
        if not scrape["success"]:
            return {"success": False, "error": scrape.get("error"), "leads": [], "started": started}

        raw_leads = scrape["data"]
        logger.info("Scraped %d raw leads", len(raw_leads))

        # Filter by rating
        filtered = [l for l in raw_leads if self._passes_filter(l)]

        # Deduplicate against the store
        new_leads = []
        skipped = 0
        for lead in filtered:
            domain = _extract_domain(lead.get("website", ""))
            if skip_known and domain and self.store.exists(domain):
                skipped += 1
                continue
            new_leads.append(lead)
            if len(new_leads) >= max_leads:
                break

        logger.info("New leads after dedup: %d (skipped %d known)", len(new_leads), skipped)

        enriched = []
        for i, lead in enumerate(new_leads, 1):
            logger.info("Enriching lead %d/%d: %s", i, len(new_leads), lead.get("title"))
            enriched_lead = self.enrich_lead(lead)
            self.store.upsert_lead(enriched_lead)
            enriched.append(enriched_lead)

        finished = datetime.utcnow().isoformat()
        return {
            "success": True,
            "query": query,
            "started": started,
            "finished": finished,
            "scraped_count": len(raw_leads),
            "skipped_known": skipped,
            "enriched_count": len(enriched),
            "leads": enriched,
            "store_stats": self.store.stats(),
        }

    def save(self, result: Dict[str, Any], filename: str = None) -> str:
        os.makedirs(DATA_DIR, exist_ok=True)
        if not filename:
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"leads_{ts}.json"
        path = os.path.join(DATA_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)
        return path


day_agent = DayAgent(min_rating=4.0)
