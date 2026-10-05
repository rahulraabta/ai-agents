"""Website Auditor tool - fetches a site and asks the LLM for a structured diagnosis."""
import os
import httpx
from typing import Any, Dict
from dotenv import load_dotenv
from src.tools.base_tool import BaseTool
load_dotenv()
from src.providers.llm_router import get_router

MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"
MAX_HTML_CHARS = 8000  # Byte-cap the HTML to save tokens


class WebsiteAuditorTool(BaseTool):
    name = "audit_website"
    description = (
        "Analyze a business website to find performance issues, SEO problems, "
        "missing features (like online booking), and business impact."
    )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The website URL to audit"},
                "business_type": {"type": "string", "description": "e.g. 'dental clinic'"},
            },
            "required": ["url"],
        }

    def _fetch_html(self, url: str) -> str:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; AI-Audit/1.0)"}
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            return response.text[:MAX_HTML_CHARS]

    def _mock_audit(self, url: str, business_type: str) -> Dict:
        return {
            "url": url,
            "business_type": business_type,
            "problems": [
                {"issue": "No online booking system", "impact": "Lost appointments after hours", "severity": "high"},
                {"issue": "Missing mobile viewport meta tag", "impact": "Poor mobile experience", "severity": "medium"},
                {"issue": "No schema.org LocalBusiness markup", "impact": "Lower Google Maps visibility", "severity": "medium"},
            ],
            "opportunities": [
                "Add AI chatbot for patient FAQs",
                "Integrate calendar-based booking",
                "Add patient review widget",
            ],
            "summary": "Site lacks online booking and mobile optimization. High potential for AI-driven appointment automation.",
        }

    def run(self, **kwargs) -> Dict[str, Any]:
        url = kwargs.get("url", "").strip()
        business_type = kwargs.get("business_type", "business")

        if not url:
            return {"success": False, "error": "url is required", "data": {}}

        if MOCK_MODE:
            return {"success": True, "mode": "mock", "data": self._mock_audit(url, business_type)}

        try:
            html = self._fetch_html(url)
            router = get_router()
            prompt = (
                f"You are a senior web consultant analyzing a {business_type} website.\n"
                f"URL: {url}\n\n"
                f"HTML (truncated):\n{html}\n\n"
                "Return ONLY valid JSON with this structure:\n"
                '{"problems": [{"issue": "...", "impact": "...", "severity": "high|medium|low"}], '
                '"opportunities": ["..."], "summary": "..."}\n'
                "Max 5 problems, max 3 opportunities. Be specific and business-focused."
            )
            result = router.ask(prompt, system="You are a JSON-only API. Return only valid JSON, no commentary.")
            if not result["success"]:
                return {"success": False, "error": result.get("error"), "data": {}}

            import json, re
            text = result["text"].strip()
            # Strip markdown fences if the LLM added them
            text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
            parsed = json.loads(text)
            parsed["url"] = url
            parsed["business_type"] = business_type
            return {"success": True, "mode": "live", "provider": result["provider"], "data": parsed}
        except Exception as e:
            return {"success": False, "error": str(e), "data": {}}


website_auditor = WebsiteAuditorTool()

