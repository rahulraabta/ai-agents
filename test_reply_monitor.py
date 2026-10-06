"""Test the Reply Monitor Agent in mock mode."""
import logging
from src.agents.reply_monitor import reply_monitor

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")


def main():
    print("\n=== Reply Monitor: Fetch + Classify ===")
    result = reply_monitor.run(days_back=7)

    print(f"Found:     {result['found']}")
    print(f"Matched:   {result['matched']}")
    print(f"Unmatched: {result['unmatched']}")
    print(f"Store:     {result['store_stats']}")

    print("\n=== CLASSIFIED REPLIES ===")
    for i, r in enumerate(result["replies"], 1):
        print(f"\n[{i}] From: {r['from']}")
        print(f"    Domain:  {r['domain'] or '(no match)'}")
        print(f"    Intent:  {r['intent']}")
        print(f"    Sentiment: {r['sentiment']}")
        print(f"    Summary: {r['summary']}")
        if r.get("suggested_reply"):
            print(f"    Suggested reply:")
            for line in r["suggested_reply"].split("\n"):
                print(f"      {line}")


if __name__ == "__main__":
    main()
