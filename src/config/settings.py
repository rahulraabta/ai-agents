"""Central configuration loader."""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    AGENT_ROUTER_KEY = os.getenv("AGENT_ROUTER_KEY")
    PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "gemini-3.5-flash-lite")
    FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "deepseek/deepseek-v4.1-flash")
    MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "2000"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
