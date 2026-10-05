"""LLM Router - pools Gemini Flash-Lite (primary) and DeepSeek via Agent Router (fallback)."""
import os
import logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class LLMRouter:
    """Central LLM access point with automatic failover."""

    def __init__(self):
        from google import genai
        gemini_key = os.getenv("GEMINI_API_KEY")
        agent_router_key = os.getenv("AGENT_ROUTER_KEY")

        if not gemini_key:
            raise ValueError("GEMINI_API_KEY not set in .env")

        self._gemini_client = genai.Client(api_key=gemini_key)
        self.gemini_model = os.getenv("PRIMARY_MODEL", "gemini-3.5-flash-lite")
        self.agent_router_key = agent_router_key
        self.fallback_model = os.getenv("FALLBACK_MODEL", "deepseek/deepseek-v4.1-flash")
        logger.info("LLMRouter initialized (primary=%s)", self.gemini_model)

    def _call_gemini(self, prompt: str, system: Optional[str], max_tokens: int) -> str:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        response = self._gemini_client.models.generate_content(
            model=self.gemini_model,
            contents=full_prompt,
            config={"max_output_tokens": max_tokens},
        )
        return response.text

    def _call_deepseek(self, prompt: str, system: Optional[str], max_tokens: int) -> str:
        from openai import OpenAI
        client = OpenAI(
            api_key=self.agent_router_key,
            base_url="https://api.theagentrouter.ai/v1",
        )
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(
            model=self.fallback_model,
            messages=messages,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def ask(self, prompt: str, system: Optional[str] = None, max_tokens: int = 2000) -> dict:
        """Send a prompt. Tries Gemini first, falls back to DeepSeek."""
        try:
            text = self._call_gemini(prompt, system, max_tokens)
            return {"text": text, "provider": "gemini", "model": self.gemini_model, "success": True}
        except Exception as e:
            logger.warning("Gemini failed: %s - trying DeepSeek fallback", e)
            if not self.agent_router_key:
                return {"text": "", "provider": "none", "model": "none", "success": False, "error": str(e)}
            try:
                text = self._call_deepseek(prompt, system, max_tokens)
                return {"text": text, "provider": "deepseek", "model": self.fallback_model, "success": True}
            except Exception as e2:
                logger.error("DeepSeek fallback also failed: %s", e2)
                return {"text": "", "provider": "none", "model": "none", "success": False, "error": str(e2)}


_router: Optional[LLMRouter] = None


def get_router() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
