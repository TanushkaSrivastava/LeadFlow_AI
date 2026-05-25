"""
=============================================================================
Logging Service
=============================================================================
Handles activity logging to SQLite database and Python file logger.
Stores lead processing events (success, failure, etc.) for audit trail.
Thread-safe database operations.
=============================================================================
"""

import os
import sqlite3
import logging
import threading
from datetime import datetime, timezone

from config.config import Config
from models.lead_model import Lead, LEADS_TABLE_SQL, ACTIVITY_LOGS_TABLE_SQL

logger = logging.getLogger(__name__)

# Thread lock for SQLite write operations
_db_lock = threading.Lock()


def init_database() -> None:
    """
    Initialize the SQLite database and create tables if they don't exist.
    Also ensures the data directory and logs directory exist.
    """
    # Ensure directories exist
    db_dir = os.path.dirname(Config.DATABASE_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    log_dir = os.path.dirname(Config.LOG_FILE_PATH)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    os.makedirs(Config.PDF_OUTPUT_DIR, exist_ok=True)

    # Create tables
    with _db_lock:
        conn = sqlite3.connect(Config.DATABASE_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute(LEADS_TABLE_SQL)
            cursor.execute(ACTIVITY_LOGS_TABLE_SQL)
            conn.commit()
            logger.info(f"Database initialized at {Config.DATABASE_PATH}")
        finally:
            conn.close()


def save_lead(lead: Lead) -> None:
    """
    Save a lead record to the database.

    Args:
        lead: The Lead instance to persist.
    """
    with _db_lock:
        conn = sqlite3.connect(Config.DATABASE_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT OR IGNORE INTO leads
                   (request_id, name, email, company, website, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (lead.request_id, lead.name, lead.email,
                 lead.company, lead.website, lead.timestamp),
            )
            conn.commit()
            logger.info(f"Lead saved: {lead.request_id}")
        except Exception as e:
            logger.error(f"Failed to save lead: {e}")
        finally:
            conn.close()


def log_activity(lead: Lead, status: str, request_id: str, details: str = "") -> None:
    """
    Log a processing activity event to the database.

    Args:
        lead:       The Lead instance being processed.
        status:     Status string (e.g., 'processing', 'success', 'failed').
        request_id: The unique request identifier.
        details:    Optional additional details or error message.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    with _db_lock:
        conn = sqlite3.connect(Config.DATABASE_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO activity_logs
                   (request_id, name, email, company, status, details, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (request_id, lead.name, lead.email,
                 lead.company, status, details, timestamp),
            )
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")
        finally:
            conn.close()

    # Also log to file
    logger.info(f"[{request_id}] {lead.company} — Status: {status} | {details}")


def get_all_logs() -> list[dict]:
    """
    Retrieve all activity logs from the database, newest first.

    Returns:
        List of log entry dictionaries.
    """
    conn = sqlite3.connect(Config.DATABASE_PATH)
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM activity_logs ORDER BY id DESC LIMIT 100")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to fetch logs: {e}")
        return []
    finally:
        conn.close()


def setup_file_logging() -> None:
    """
    Configure Python's logging module to write to both console and file.
    Uses rotating-style approach with a single log file.
    """
    log_dir = os.path.dirname(Config.LOG_FILE_PATH)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_fmt)

    # File handler
    file_handler = logging.FileHandler(Config.LOG_FILE_PATH, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)

    # Add handlers (avoid duplicates on reload)
    if not root_logger.handlers:
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
