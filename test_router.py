"""Quick smoke test for the LLM router."""
import logging
from src.providers.llm_router import get_router

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")


def main():
    router = get_router()

    print("\n--- Test 1: Simple hello ---")
    result = router.ask("Reply with exactly: 'Router online.'")
    print(f"Provider: {result['provider']}")
    print(f"Model:    {result['model']}")
    print(f"Text:     {result['text']}")
    print(f"Success:  {result['success']}")

    print("\n--- Test 2: Structured JSON output ---")
    result = router.ask(
        prompt='Return ONLY valid JSON: {"status": "ok", "number": 42}',
        system="You are a JSON-only API. Never add commentary.",
    )
    print(f"Provider: {result['provider']}")
    print(f"Text:     {result['text']}")


if __name__ == "__main__":
    main()
