"""
=============================================================================
AI Report Generation Service
=============================================================================
Generates personalized business audit reports using the Google Gemini API.
Includes structured prompting, JSON output parsing, and retry logic.
=============================================================================
"""

import json
import logging
import time

from google import genai
from config.config import Config

logger = logging.getLogger(__name__)

_client = None


def _get_client() -> genai.Client:
    """Lazy-initialize the Gemini client."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=Config.GEMINI_API_KEY)
    return _client


def generate_report(company: str, industry: str, enrichment_data: dict) -> dict:
    """
    Generate a personalized AI business audit report with retry logic.

    Args:
        company:         Company name.
        industry:        Detected or inferred industry.
        enrichment_data: Dict from enrichment service (description, services, etc.)

    Returns:
        Structured report dict.

    Raises:
        RuntimeError: If generation fails after all retries.
    """
    prompt = _build_prompt(company, industry, enrichment_data)
    max_attempts = 2

    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"AI attempt {attempt}/{max_attempts} for '{company}'")
            result = _call_gemini(prompt)
            logger.info(f"AI report generated for '{company}'")
            return result
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed attempt {attempt}: {e}")
            if attempt < max_attempts:
                time.sleep(2)
                continue
            raise RuntimeError(f"AI returned invalid JSON after {max_attempts} attempts")
        except Exception as e:
            logger.error(f"AI error attempt {attempt}: {e}")
            if attempt < max_attempts:
                time.sleep(3)
                continue
            raise RuntimeError(f"AI generation failed: {e}")


def _build_prompt(company: str, industry: str, enrichment_data: dict) -> str:
    """Build structured prompt for Gemini."""
    services = enrichment_data.get("services", [])
    services_text = ", ".join(services) if services else "Not available"
    desc = enrichment_data.get("description", "No description available")

    return f"""You are a senior business analyst. Generate a professional business audit report.
Return ONLY valid JSON — no markdown fences, no extra text.

Company: {company}
Industry: {industry}
Description: {desc}
Services: {services_text}

Return this JSON structure:
{{
    "company_name": "{company}",
    "industry": "{industry}",
    "report_date": "auto-generated",
    "company_overview": "3-4 sentence overview of the company.",
    "key_strengths": ["Strength 1 — explanation", "Strength 2", "Strength 3", "Strength 4"],
    "weaknesses": ["Weakness 1 — explanation", "Weakness 2", "Weakness 3"],
    "growth_opportunities": ["Opportunity 1 — actionable steps", "Opportunity 2", "Opportunity 3", "Opportunity 4"],
    "strategic_recommendations": ["Rec 1 — specific action", "Rec 2", "Rec 3", "Rec 4", "Rec 5"]
}}

Make analysis specific to {company} in {industry}. Be professional and actionable.
Each point should be 1-2 detailed sentences. Return ONLY JSON."""


def _call_gemini(prompt: str) -> dict:
    """Call Gemini API and parse JSON response."""
    client = _get_client()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    if not response or not response.text:
        raise RuntimeError("Gemini returned empty response")

    text = response.text.strip()
    # Remove markdown fences
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    return json.loads(text)
