"""Email Extractor tool - finds public business emails from a website."""
import os
import re
import shutil
import subprocess
import httpx
from typing import Any, Dict, List
from dotenv import load_dotenv
from src.tools.base_tool import BaseTool
load_dotenv()

MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"

# Public business email regex - matches mailto: links and plain emails
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


class EmailExtractorTool(BaseTool):
    name = "extract_emails"
    description = (
        "Extract publicly listed business emails from a website's contact pages. "
        "Only returns emails found on the site itself."
    )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Website URL to extract emails from"},
            },
            "required": ["url"],
        }

    def _extractor_available(self) -> bool:
        return shutil.which("email_extractor") is not None

    def _fetch_and_extract(self, url: str) -> List[str]:
        """Simple fallback: fetch homepage + /contact, regex for emails."""
        emails = set()
        paths = ["", "/contact", "/about", "/contact-us"]
        headers = {"User-Agent": "Mozilla/5.0 (compatible; AI-Email/1.0)"}
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            for path in paths:
                try:
                    resp = client.get(url.rstrip("/") + path, headers=headers)
                    if resp.status_code == 200:
                        for m in EMAIL_REGEX.findall(resp.text):
                            # Filter out obvious non-business emails
                            if not any(x in m.lower() for x in ["example", "sentry", "wixpress", ".png", ".jpg"]):
                                emails.add(m.lower())
                except Exception:
                    continue
        return sorted(emails)

    def _mock_emails(self, url: str) -> List[str]:
        domain = url.replace("https://", "").replace("http://", "").split("/")[0]
        if domain.startswith("www."):
            domain = domain[4:]
        return [f"info@{domain}", f"contact@{domain}"]

    def run(self, **kwargs) -> Dict[str, Any]:
        url = kwargs.get("url", "").strip()
        if not url:
            return {"success": False, "error": "url is required", "data": []}

        if MOCK_MODE or not self._extractor_available():
            emails = self._mock_emails(url)
            return {"success": True, "mode": "mock", "count": len(emails), "data": emails}

        try:
            emails = self._fetch_and_extract(url)
            return {"success": True, "mode": "live", "count": len(emails), "data": emails}
        except Exception as e:
            return {"success": False, "error": str(e), "data": []}


email_extractor = EmailExtractorTool()

