"""End-to-end test for the Day Agent."""
import logging
from src.agents.day_agent import day_agent

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")


def main():
    print("\n=== Running Day Agent: 'dental clinic in Manila' ===\n")
    result = day_agent.run(query="dental clinic in Manila", max_leads=2)

    if not result["success"]:
        print(f"FAILED: {result.get('error')}")
        return

    print(f"\nScraped: {result['scraped_count']}")
    print(f"Enriched: {result['enriched_count']}")

    for i, lead in enumerate(result["leads"], 1):
        print(f"\n{'='*60}")
        print(f"  LEAD {i}: {lead.get('title')}")
        print(f"{'='*60}")
        print(f"  Website:  {lead.get('website')}")
        print(f"  Rating:   {lead.get('review_rating')}")
        print(f"  Phone:    {lead.get('phone')}")

        print(f"\n  AUDIT:")
        audit = lead.get("audit", {})
        print(f"    Summary: {audit.get('summary', 'N/A')}")
        for p in audit.get("problems", [])[:3]:
            print(f"    - [{p.get('severity')}] {p.get('issue')}")

        print(f"\n  EMAILS FOUND:")
        for e in lead.get("emails", []):
            print(f"    - {e}")

        outreach = lead.get("outreach", {})
        print(f"\n  OUTREACH DRAFT (by {outreach.get('provider', 'n/a')}):")
        print(f"    Subject: {outreach.get('subject', 'N/A')}")
        print(f"    Body:")
        for line in outreach.get("body", "").split("\n"):
            print(f"      {line}")

    saved = day_agent.save(result)
    print(f"\n\n💾 Saved to: {saved}")


if __name__ == "__main__":
    main()
