"""Lead Scraper tool."""
import os
import csv
import shutil
import subprocess
from typing import Any, Dict, List
from dotenv import load_dotenv
from src.tools.base_tool import BaseTool
load_dotenv()

DATA_DIR = os.path.join(os.getcwd(), "data")
MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"


class LeadScraperTool(BaseTool):
    name = "scrape_leads"
    description = (
        "Scrape business leads from Google Maps for a given query. "
        "Returns name, address, phone, website, rating, review count, and email."
    )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "default": 20},
            },
            "required": ["query"],
        }

    def _scraper_available(self) -> bool:
        return shutil.which("google-maps-scraper") is not None

    def _mock_data(self, query: str, max_results: int) -> List[Dict]:
        """Generate query-aware mock leads."""
        import hashlib
        seed = int(hashlib.md5(query.encode()).hexdigest()[:8], 16) % 10000
        names = ["Smile", "Bright", "Pearl", "Care", "Elite", "Premier", "Family", "Gentle"]
        cities = ["Manila", "Quezon City", "Cebu City", "Davao", "Makati", "Taguig", "Pasig", "Bacolod"]
        return [
            {
                "title": f"{names[(seed + i) % len(names)]} Dental Clinic {seed + i}",
                "address": f"{100 + i} Main St, {cities[(seed + i) % len(cities)]}, Philippines",
                "phone": f"+63 2 8{(seed + i):04d} 0000",
                "website": f"https://clinic{seed + i}.com.ph",
                "review_rating": f"{4.0 + ((seed + i) % 10) * 0.1:.1f}",
                "review_count": f"{50 + ((seed + i) * 7) % 500}",
                "email": f"info@clinic{seed + i}.com.ph",
                "query": query,
            }
            for i in range(min(max_results, 10))
        ]

    def _run_real_scraper(self, query: str, max_results: int) -> List[Dict]:
        os.makedirs(DATA_DIR, exist_ok=True)
        # The new scraper expects -input to be a FILE containing queries (one per line)
        query_file = os.path.join(DATA_DIR, "queries.txt")
        output_file = os.path.join(DATA_DIR, "scrape_raw.csv")

        # Write the query to the input file
        with open(query_file, "w", encoding="utf-8") as f:
            f.write(query + "\n")

        # Adjust concurrency based on available resources
        # GitHub Actions 2-core runner: use -c 1 to stay safe
        cmd = [
            "google-maps-scraper",
            "-input", query_file,
            "-results", output_file,
            "-depth", "1",
            "-email",
            "-c", "1",
            "-exit-on-inactivity", "2m",
        ]
        subprocess.run(cmd, check=True, timeout=600, capture_output=True)

        # Read results
        leads = []
        if os.path.exists(output_file):
            with open(output_file, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    leads.append(row)
                    if len(leads) >= max_results:
                        break
        return leads

    def run(self, **kwargs) -> Dict[str, Any]:
        query = kwargs.get("query", "").strip()
        max_results = int(kwargs.get("max_results", 20))
        if not query:
            return {"success": False, "error": "query is required", "data": []}
        if MOCK_MODE or not self._scraper_available():
            reason = "MOCK_MODE=true" if MOCK_MODE else "scraper not installed"
            leads = self._mock_data(query, max_results)
            return {"success": True, "mode": "mock", "reason": reason, "count": len(leads), "data": leads}
        try:
            leads = self._run_real_scraper(query, max_results)
            return {"success": True, "mode": "live", "count": len(leads), "data": leads}
        except Exception as e:
            return {"success": False, "error": str(e), "data": []}


lead_scraper = LeadScraperTool()
