"""Test the Lead Scraper tool."""
import logging
from src.tools.lead_scraper import lead_scraper

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")


def main():
    print("\n--- Test: Scrape dental clinics in Manila ---")
    result = lead_scraper.run(query="dental clinic in Manila", max_results=5)
    print(f"Success: {result['success']}")
    print(f"Mode:    {result.get('mode', 'n/a')}")
    print(f"Count:   {result.get('count', 0)}")
    for i, lead in enumerate(result.get("data", []), 1):
        print(f"\n  [{i}] {lead.get('title', 'N/A')}")
        print(f"      Address: {lead.get('address', 'N/A')}")
        print(f"      Phone:   {lead.get('phone', 'N/A')}")
        print(f"      Rating:  {lead.get('review_rating', 'N/A')}")
        print(f"      Email:   {lead.get('email', 'N/A')}")


if __name__ == "__main__":
    main()
