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

# Emails we never want to include (tracking pixels, image filenames, etc.)
BLOCKED_SUBSTRINGS = [
    "example.com",
    "sentry.io",
    "wixpress.com",
    "wordpress.org",
    "google.com",
    "schema.org",
    "sentry.wixpress",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    "noreply@",
    "no-reply@",
]


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

    @staticmethod
    def _clean_domain(url: str) -> str:
        """Strip protocol, path, and www. from a URL to get the bare domain."""
        domain = url.replace("https://", "").replace("http://", "").split("/")[0]
        domain = domain.split(":")[0]  # strip port if present
        if domain.startswith("www."):
            domain = domain[4:]
        return domain.lower()

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Return True if email looks like a legitimate business email."""
        email = email.lower().strip()
        if "@" not in email:
            return False
        local, _, domain = email.partition("@")
        if not local or not domain or "." not in domain:
            return False
        # Reject domains with 'www.' (always a parsing bug)
        if domain.startswith("www."):
            return False
        # Reject domain endings with a dot
        if domain.endswith("."):
            return False
        # Reject blocked substrings
        for blocked in BLOCKED_SUBSTRINGS:
            if blocked in email:
                return False
        # Reject emails that are too long (likely garbage)
        if len(email) > 100:
            return False
        return True

    def _run_cli_extractor(self, url: str) -> List[str]:
        """Run the Go binary email_extractor as a subprocess."""
        proc = subprocess.run(
            [
                "email_extractor",
                f"-url={url}",
                "-depth=-1",
                "-limit-urls=50",
                "-out=/tmp/emails_cli.txt",
                "-parallel=true",
                "-timeout=10000",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"email_extractor failed: {proc.stderr[:200]}")
        try:
            with open("/tmp/emails_cli.txt", "r") as f:
                raw = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            raw = []
        return [e for e in raw if self._is_valid_email(e)]

    def _fetch_and_extract(self, url: str) -> List[str]:
        """Fallback: fetch homepage + contact pages and regex for emails."""
        emails = set()
        base = url.rstrip("/")
        paths = ["", "/contact", "/contact-us", "/about", "/about-us", "/team"]
        headers = {"User-Agent": "Mozilla/5.0 (compatible; AI-Email/1.0)"}

        with httpx.Client(timeout=15, follow_redirects=True) as client:
            for path in paths:
                try:
                    resp = client.get(base + path, headers=headers)
                    if resp.status_code == 200:
                        for m in EMAIL_REGEX.findall(resp.text):
                            if self._is_valid_email(m):
                                emails.add(m.lower())
                except Exception:
                    continue
        return sorted(emails)

    def _mock_emails(self, url: str) -> List[str]:
        """Generate mock emails using the cleaned domain."""
        domain = self._clean_domain(url)
        if not domain:
            return []
        return [f"info@{domain}", f"contact@{domain}"]

    def run(self, **kwargs) -> Dict[str, Any]:
        url = kwargs.get("url", "").strip()
        if not url:
            return {"success": False, "error": "url is required", "data": []}

        if MOCK_MODE or not self._extractor_available():
            reason = "MOCK_MODE=true" if MOCK_MODE else "email_extractor not installed"
            emails = self._mock_emails(url)
            return {
                "success": True,
                "mode": "mock",
                "reason": reason,
                "count": len(emails),
                "data": emails,
            }

        # Try the Go binary first
        try:
            emails = self._run_cli_extractor(url)
            if emails:
                return {"success": True, "mode": "live-cli", "count": len(emails), "data": emails}
        except Exception as e:
            # Log and fall through to HTTP fallback
            print(f"  [email_extractor CLI failed: {e}]")

        # Fallback to HTTP fetch
        try:
            emails = self._fetch_and_extract(url)
            return {"success": True, "mode": "live-http", "count": len(emails), "data": emails}
        except Exception as e:
            return {"success": False, "error": str(e), "data": []}


email_extractor = EmailExtractorTool()