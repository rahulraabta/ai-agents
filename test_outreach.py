"""Test the Outreach Agent end-to-end (mock send)."""
import logging
from src.agents.day_agent import day_agent
from src.agents.outreach_agent import outreach_agent

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")


def main():
    print("\n=== STEP 1: Generate new leads ===")
    r = day_agent.run(query="dental clinic in Cebu", max_leads=3, skip_known=True)
    print(f"Enriched: {r['enriched_count']} | Store: {r['store_stats']}")

    print("\n=== STEP 2: Send outreach emails ===")
    send_result = outreach_agent.run(max_sends=5)
    print(f"Sent:    {send_result['sent']}")
    print(f"Failed:  {send_result['failed']}")
    print(f"Skipped: {send_result['skipped']}")
    print(f"Store:   {send_result['store_stats']}")

    for r in send_result["results"]:
        status = "✓" if r.get("success") else "✗"
        print(f"  {status} {r.get('domain')} → {r.get('to')} [{r.get('reason', 'ok')}]")


if __name__ == "__main__":
    main()
