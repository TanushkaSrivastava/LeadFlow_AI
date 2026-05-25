"""
=============================================================================
Helper Utilities
=============================================================================
General-purpose utility functions used across the application.
Includes request ID generation, timestamps, filename sanitization, etc.
=============================================================================
"""

import re
import uuid
from datetime import datetime, timezone


def generate_request_id() -> str:
    """
    Generate a unique request ID for tracking a lead through the pipeline.
    Format: 'REQ-<short-uuid>' (e.g., REQ-a1b2c3d4)
    """
    short_id = uuid.uuid4().hex[:8]
    return f"REQ-{short_id}"


def get_timestamp() -> str:
    """
    Get the current UTC timestamp in ISO 8601 format.
    Example: '2026-05-18T02:15:30+00:00'
    """
    return datetime.now(timezone.utc).isoformat()


def sanitize_filename(name: str) -> str:
    """
    Convert a string into a safe filename by removing special characters
    and replacing spaces with underscores.

    Args:
        name: Raw string to sanitize.

    Returns:
        A filesystem-safe filename string.

    Example:
        >>> sanitize_filename("Acme Corp. (India)")
        'Acme_Corp_India'
    """
    # Remove characters that are not alphanumeric, spaces, hyphens, or underscores
    cleaned = re.sub(r'[^\w\s-]', '', name)
    # Replace whitespace with underscores
    cleaned = re.sub(r'\s+', '_', cleaned.strip())
    # Collapse multiple underscores
    cleaned = re.sub(r'_+', '_', cleaned)
    return cleaned


def truncate_text(text: str, max_len: int = 200) -> str:
    """
    Truncate text to a maximum length, appending '...' if truncated.
    Useful for logging and display purposes.

    Args:
        text:    The text to truncate.
        max_len: Maximum allowed length (default 200).

    Returns:
        The original text if short enough, or truncated text with ellipsis.
    """
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def format_timestamp_readable(iso_timestamp: str) -> str:
    """
    Convert an ISO 8601 timestamp to a human-readable format.

    Args:
        iso_timestamp: ISO 8601 timestamp string.

    Returns:
        Formatted string like 'May 18, 2026 at 02:15 AM UTC'
    """
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        return dt.strftime("%b %d, %Y at %I:%M %p UTC")
    except (ValueError, TypeError):
        return iso_timestamp
