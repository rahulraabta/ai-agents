"""Test that the store prevents duplicate processing across runs."""
import logging
from src.agents.day_agent import day_agent
from src.memory.lead_store import LeadStore

logging.basicConfig(level=logging.WARNING)


def main():
    print("\n=== RUN 1 ===")
    r1 = day_agent.run(query="dental clinic in Manila", max_leads=2)
    print(f"Enriched: {r1['enriched_count']} | Skipped known: {r1['skipped_known']}")
    print(f"Store stats: {r1['store_stats']}")

    print("\n=== RUN 2 (same query, should skip all) ===")
    r2 = day_agent.run(query="dental clinic in Manila", max_leads=2)
    print(f"Enriched: {r2['enriched_count']} | Skipped known: {r2['skipped_known']}")
    print(f"Store stats: {r2['store_stats']}")

    print("\n=== STORE CONTENTS ===")
    store = LeadStore()
    for lead in store.get_new_leads():
        print(f"  [{lead['status']}] {lead['title']} ({lead['domain']}) - rating {lead['rating']}")


if __name__ == "__main__":
    main()
