"""
=============================================================================
Enrichment Service
=============================================================================
Enriches lead data by scraping the company's website for insights.
Uses BeautifulSoup + requests to extract company description, industry
signals, and services. Falls back to structured mock data if scraping fails.
=============================================================================
"""

import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Request timeout in seconds
SCRAPE_TIMEOUT = 10

# User-Agent to avoid being blocked by websites
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


def enrich_company(website: str, company: str) -> dict:
    """
    Enrich company data by scraping the provided website.

    Attempts to extract:
        - Company description (from meta description or first paragraphs)
        - Industry signals (from keywords in content)
        - Services mentioned (from headings and list items)

    Falls back to mock data if scraping fails for any reason.

    Args:
        website: The company website URL to scrape.
        company: The company name (used in fallback data).

    Returns:
        A dictionary with keys: description, industry, services, source.
    """
    try:
        logger.info(f"Scraping website: {website}")

        response = requests.get(
            website,
            timeout=SCRAPE_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # --- Extract description ---
        description = _extract_description(soup)

        # --- Extract industry signals ---
        industry = _extract_industry(soup)

        # --- Extract services ---
        services = _extract_services(soup)

        # If we got essentially nothing, use fallback
        if not description and not services:
            logger.warning(f"Scraping returned empty results for {website}, using fallback")
            return _get_fallback_data(company)

        return {
            "description": description or f"{company} — no description could be extracted.",
            "industry": industry or "General Business",
            "services": services or ["Not identified from website"],
            "source": "web_scraping",
        }

    except requests.exceptions.Timeout:
        logger.warning(f"Timeout scraping {website}, using fallback data")
        return _get_fallback_data(company)

    except requests.exceptions.ConnectionError:
        logger.warning(f"Connection error for {website}, using fallback data")
        return _get_fallback_data(company)

    except requests.exceptions.HTTPError as e:
        logger.warning(f"HTTP error {e.response.status_code} for {website}, using fallback data")
        return _get_fallback_data(company)

    except Exception as e:
        logger.error(f"Unexpected error scraping {website}: {str(e)}, using fallback data")
        return _get_fallback_data(company)


def _extract_description(soup: BeautifulSoup) -> str:
    """
    Extract a company description from meta tags or page content.
    Priority: meta description > og:description > first few paragraphs.
    """
    # Try meta description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content", "").strip():
        return meta_desc["content"].strip()

    # Try Open Graph description
    og_desc = soup.find("meta", attrs={"property": "og:description"})
    if og_desc and og_desc.get("content", "").strip():
        return og_desc["content"].strip()

    # Fallback: concatenate first meaningful paragraphs
    paragraphs = soup.find_all("p")
    texts = []
    for p in paragraphs[:5]:
        text = p.get_text(strip=True)
        if len(text) > 30:  # Skip very short paragraphs (nav items, etc.)
            texts.append(text)
        if len(" ".join(texts)) > 500:
            break

    return " ".join(texts)[:600] if texts else ""


def _extract_industry(soup: BeautifulSoup) -> str:
    """
    Attempt to determine the industry from page content keywords.
    Uses a simple keyword-matching approach against common industries.
    """
    page_text = soup.get_text(separator=" ").lower()

    industry_keywords = {
        "Technology": ["software", "saas", "cloud", "ai", "machine learning", "data", "tech", "digital"],
        "Healthcare": ["health", "medical", "pharma", "hospital", "patient", "clinical"],
        "Finance": ["finance", "banking", "investment", "insurance", "fintech", "trading"],
        "E-Commerce": ["ecommerce", "e-commerce", "online store", "shopping", "retail"],
        "Education": ["education", "learning", "school", "university", "training", "course"],
        "Manufacturing": ["manufacturing", "factory", "production", "industrial", "machinery"],
        "Real Estate": ["real estate", "property", "housing", "construction", "building"],
        "Marketing": ["marketing", "advertising", "branding", "seo", "agency", "creative"],
        "Consulting": ["consulting", "advisory", "strategy", "management consulting"],
        "Logistics": ["logistics", "supply chain", "shipping", "transportation", "freight"],
    }

    # Score each industry by keyword matches
    scores = {}
    for industry, keywords in industry_keywords.items():
        score = sum(1 for kw in keywords if kw in page_text)
        if score > 0:
            scores[industry] = score

    if scores:
        return max(scores, key=scores.get)

    return ""


def _extract_services(soup: BeautifulSoup) -> list[str]:
    """
    Extract potential services from headings (h2, h3) and list items.
    Filters out navigation and boilerplate content.
    """
    services = []

    # Check h2 and h3 headings for service-like content
    for tag in soup.find_all(["h2", "h3"]):
        text = tag.get_text(strip=True)
        if 5 < len(text) < 100:  # Reasonable heading length
            services.append(text)

    # Check list items under sections that might be about services
    for ul in soup.find_all("ul"):
        for li in ul.find_all("li", limit=10):
            text = li.get_text(strip=True)
            if 5 < len(text) < 100:
                services.append(text)
            if len(services) >= 15:
                break
        if len(services) >= 15:
            break

    # Deduplicate and limit
    seen = set()
    unique_services = []
    for s in services:
        s_lower = s.lower()
        if s_lower not in seen:
            seen.add(s_lower)
            unique_services.append(s)

    return unique_services[:10]


def _get_fallback_data(company: str) -> dict:
    """
    Return structured mock data when scraping fails.
    Provides enough context for the AI to generate a useful report.
    """
    return {
        "description": (
            f"{company} is a business entity. Detailed information could not be "
            f"extracted from their website. The AI will generate insights based "
            f"on publicly available knowledge about {company}."
        ),
        "industry": "General Business",
        "services": [
            "Company services could not be determined from the website",
            "AI will infer services based on company name and industry",
        ],
        "source": "fallback_mock",
    }
