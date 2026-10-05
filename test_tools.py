"""Test all three tools end-to-end in mock mode."""
import logging
from src.tools.lead_scraper import lead_scraper
from src.tools.website_auditor import website_auditor
from src.tools.email_extractor import email_extractor

logging.basicConfig(level=logging.WARNING)


def main():
    print("\n=== TOOL 1: Lead Scraper ===")
    leads = lead_scraper.run(query="dental clinic in Manila", max_results=2)
    print(f"Success: {leads['success']} | Mode: {leads.get('mode')} | Count: {leads.get('count')}")

    if not leads["data"]:
        return

    first_lead = leads["data"][0]
    website = first_lead.get("website", "")
    print(f"\nFirst lead: {first_lead.get('title')}")
    print(f"Website:    {website}")

    print("\n=== TOOL 2: Website Auditor ===")
    audit = website_auditor.run(url=website, business_type="dental clinic")
    print(f"Success: {audit['success']} | Mode: {audit.get('mode')}")
    if audit["success"]:
        data = audit["data"]
        print(f"Summary: {data.get('summary', 'N/A')}")
        for p in data.get("problems", []):
            print(f"  - [{p.get('severity')}] {p.get('issue')}")

    print("\n=== TOOL 3: Email Extractor ===")
    emails = email_extractor.run(url=website)
    print(f"Success: {emails['success']} | Mode: {emails.get('mode')} | Count: {emails.get('count')}")
    for e in emails.get("data", []):
        print(f"  - {e}")


if __name__ == "__main__":
    main()
