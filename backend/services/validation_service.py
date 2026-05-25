"""
=============================================================================
Validation Service
=============================================================================
Validates incoming lead data from the API request.
Checks required fields, email format, and website URL format.
Returns structured validation results with clear error messages.
=============================================================================
"""

import re


def validate_lead(data: dict) -> tuple[bool, list[str]]:
    """
    Validate lead intake data.

    Args:
        data: Dictionary containing lead fields (name, email, company, website).

    Returns:
        A tuple of (is_valid: bool, errors: list[str]).
        If is_valid is True, errors will be an empty list.

    Example:
        >>> validate_lead({"name": "", "email": "bad", "company": "", "website": ""})
        (False, ['Name is required', 'Invalid email format', ...])
    """
    errors = []

    # --- Required Fields ---
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    company = (data.get("company") or "").strip()
    website = (data.get("website") or "").strip()

    if not name:
        errors.append("Name is required")

    if not email:
        errors.append("Email is required")

    if not company:
        errors.append("Company name is required")

    if not website:
        errors.append("Website URL is required")

    # --- Email Format Validation ---
    if email and not _is_valid_email(email):
        errors.append(
            f"Invalid email format: '{email}'. "
            "Please provide a valid email address (e.g., user@example.com)"
        )

    # --- Website URL Format Validation ---
    if website and not _is_valid_url(website):
        errors.append(
            f"Invalid website URL: '{website}'. "
            "URL must start with http:// or https:// (e.g., https://example.com)"
        )

    is_valid = len(errors) == 0
    return is_valid, errors


def _is_valid_email(email: str) -> bool:
    """
    Validate email format using a simplified RFC 5322 pattern.
    Covers the vast majority of real-world email addresses.
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def _is_valid_url(url: str) -> bool:
    """
    Validate that a URL starts with http:// or https:// and has a domain.
    """
    pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
    return bool(re.match(pattern, url))
