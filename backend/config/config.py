"""
=============================================================================
Configuration Module
=============================================================================
Centralizes all application configuration. Loads values from environment
variables via python-dotenv. No secrets are hardcoded.
=============================================================================
"""

import os
from dotenv import load_dotenv

# Load .env file from the backend root directory
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))


class Config:
    """Application configuration loaded from environment variables."""

    # -------------------------------------------------------------------------
    # Gemini AI
    # -------------------------------------------------------------------------
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # -------------------------------------------------------------------------
    # SMTP Email
    # -------------------------------------------------------------------------
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_EMAIL: str = os.getenv("SMTP_EMAIL", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")

    # -------------------------------------------------------------------------
    # Flask
    # -------------------------------------------------------------------------
    FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    FLASK_SECRET_KEY: str = os.getenv("FLASK_SECRET_KEY", "default-secret-key")

    # -------------------------------------------------------------------------
    # Rate Limiting
    # -------------------------------------------------------------------------
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))

    # -------------------------------------------------------------------------
    # File Paths (resolved relative to backend/ root)
    # -------------------------------------------------------------------------
    _BASE_DIR: str = os.path.dirname(os.path.dirname(__file__))

    PDF_OUTPUT_DIR: str = os.path.join(
        _BASE_DIR, os.getenv("PDF_OUTPUT_DIR", "reports")
    )
    DATABASE_PATH: str = os.path.join(
        _BASE_DIR, os.getenv("DATABASE_PATH", "data/leadflow.db")
    )
    LOG_FILE_PATH: str = os.path.join(
        _BASE_DIR, os.getenv("LOG_FILE_PATH", "logs/app.log")
    )

    @classmethod
    def validate(cls) -> list[str]:
        """
        Validate that critical configuration values are set.
        Returns a list of warnings for missing values.
        """
        warnings = []
        if not cls.GEMINI_API_KEY:
            warnings.append("GEMINI_API_KEY is not set — AI service will fail")
        if not cls.SMTP_EMAIL or cls.SMTP_EMAIL == "your_email@gmail.com":
            warnings.append("SMTP_EMAIL is not configured — email service will fail")
        if not cls.SMTP_PASSWORD or cls.SMTP_PASSWORD == "your_gmail_app_password_here":
            warnings.append("SMTP_PASSWORD is not configured — email service will fail")
        return warnings
