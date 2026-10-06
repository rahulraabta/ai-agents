"""Email Writer agent - generates personalized outreach emails via the LLM router."""
import json
import re
from typing import Any, Dict

from src.providers.llm_router import get_router


SYSTEM_PROMPT = (
    "You are a warm, human copywriter for a small web consultancy. "
    "You write short, specific, empathetic emails that show you genuinely noticed the "
    "recipient's business. You never sound like a salesperson. "
    "Return ONLY valid JSON with keys 'subject' and 'body'. No commentary. "
    "Do NOT include any signature, name, or unsubscribe text in the body — "
    "those are added automatically by the system."
)


def write_outreach_email(lead: Dict[str, Any], audit: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a personalized outreach email for one lead."""
    business_name = lead.get("title", "your business")
    business_type = audit.get("business_type", "business")
    website = lead.get("website", "")
    problems = audit.get("problems", [])
    summary = audit.get("summary", "")

    problem_lines = "\n".join(
        f"- [{p.get('severity', 'medium')}] {p.get('issue', '')} → {p.get('impact', '')}"
        for p in problems[:3]
    )

    prompt = (
        f"Write a short outreach email to the owner of '{business_name}', a {business_type}.\n"
        f"Their website: {website}\n\n"
        f"Findings from our analysis:\n{problem_lines}\n\n"
        f"Summary: {summary}\n\n"
        "Requirements:\n"
        "- Under 100 words in the body.\n"
        "- Open with a specific, warm, human detail.\n"
        "- Mention 1-2 concrete problems and their business impact.\n"
        "- Mention we've prepared a live demo of an improved version.\n"
        "- End with a low-commitment question (e.g. 'Would it be useful if I sent it over?').\n"
        "- Sign off with just 'Best,' — do NOT include a name or placeholder.\n"
        "- Do NOT include any signature, name, or 'unsubscribe' text.\n"
        "- No hype, no 'Dear Sir/Madam'. Use 'Hi there' if no name is known.\n\n"
        'Return JSON: {"subject": "...", "body": "..."}'
    )

    router = get_router()
    result = router.ask(prompt, system=SYSTEM_PROMPT, max_tokens=500)

    if not result["success"]:
        return {"success": False, "error": result.get("error"), "subject": "", "body": ""}

    text = result["text"].strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()

    try:
        parsed = json.loads(text)
        subject = parsed.get("subject", "")
        body = parsed.get("body", "")

        # Strip any trailing placeholder the LLM may have invented
        body = re.sub(r"\n?\[Your Name\]\s*$", "", body, flags=re.IGNORECASE)
        body = re.sub(r"\n?\[Your name\]\s*$", "", body, flags=re.IGNORECASE)
        body = re.sub(r"\n?Best,\s*$", "", body, flags=re.IGNORECASE)
        body = body.rstrip()

        # Hardcode the signature + unsubscribe footer (never trust the LLM with this)
        footer = (
            "\n\nBest,\n"
            "Rahul\n\n"
            "---\n"
            "If you'd prefer not to hear from me again, just reply 'unsubscribe' "
            "and I'll remove you right away."
        )

        return {
            "success": True,
            "provider": result["provider"],
            "subject": subject,
            "body": body + footer,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"JSON parse failed: {e}",
            "raw": text,
            "subject": "",
            "body": "",
        }