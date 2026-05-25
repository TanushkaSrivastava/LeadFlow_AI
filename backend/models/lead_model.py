"""
=============================================================================
Lead Model
=============================================================================
Defines the Lead data structure and database schema for the application.
Uses Python dataclasses for clean, type-safe data representation.
=============================================================================
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Lead:
    """
    Represents a lead submission from the intake form.

    Attributes:
        name:       Full name of the person submitting the lead.
        email:      Contact email address for report delivery.
        company:    Company name to analyze.
        website:    Company website URL for enrichment scraping.
        request_id: Unique identifier for tracking this request through the pipeline.
        timestamp:  ISO 8601 timestamp of when the lead was received.
    """
    name: str
    email: str
    company: str
    website: str
    request_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        """Convert the Lead instance to a dictionary for serialization."""
        return {
            "name": self.name,
            "email": self.email,
            "company": self.company,
            "website": self.website,
            "request_id": self.request_id,
            "timestamp": self.timestamp,
        }

    def __str__(self) -> str:
        return f"Lead({self.name}, {self.company}, {self.request_id})"


# =============================================================================
# Database Schema SQL
# =============================================================================

LEADS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS leads (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id  TEXT    NOT NULL UNIQUE,
    name        TEXT    NOT NULL,
    email       TEXT    NOT NULL,
    company     TEXT    NOT NULL,
    website     TEXT    NOT NULL,
    timestamp   TEXT    NOT NULL
);
"""

ACTIVITY_LOGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS activity_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id  TEXT    NOT NULL,
    name        TEXT    NOT NULL,
    email       TEXT    NOT NULL,
    company     TEXT    NOT NULL,
    status      TEXT    NOT NULL,
    details     TEXT    DEFAULT '',
    timestamp   TEXT    NOT NULL,
    FOREIGN KEY (request_id) REFERENCES leads(request_id)
);
"""
