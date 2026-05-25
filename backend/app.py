"""
=============================================================================
LeadFlow AI — Application Entry Point
=============================================================================
Flask application factory. Initializes the database, configures logging,
sets up CORS, rate limiting, and registers route blueprints.

Usage:
    python app.py
=============================================================================
"""

import os
import logging
from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config.config import Config
from routes.lead_routes import lead_bp
from services.logging_service import init_database, setup_file_logging

# Absolute path to the frontend folder (one level up from backend/)
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))


def create_app() -> Flask:
    """
    Application factory — creates and configures the Flask app.

    Returns:
        Configured Flask application instance.
    """
    # --- Initialize logging first ---
    setup_file_logging()
    logger = logging.getLogger(__name__)

    # --- Log config warnings ---
    warnings = Config.validate()
    for w in warnings:
        logger.warning(f"CONFIG WARNING: {w}")

    # --- Create Flask app ---
    app = Flask(__name__)
    app.secret_key = Config.FLASK_SECRET_KEY

    # --- Enable CORS for frontend integration ---
    CORS(app, resources={r"/*": {"origins": "*"}})

    # --- Rate Limiting ---
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[f"{Config.RATE_LIMIT_PER_MINUTE} per minute"],
        storage_uri="memory://",
    )
    # Apply stricter limit to the report generation endpoint
    limiter.limit(f"{Config.RATE_LIMIT_PER_MINUTE} per minute")(lead_bp)

    # --- Initialize database ---
    init_database()

    # --- Register API blueprints ---
    app.register_blueprint(lead_bp)

    # --- Serve frontend static files ---
    @app.route("/")
    def serve_index():
        """Serve the main frontend HTML file."""
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.route("/<path:filename>")
    def serve_static(filename):
        """Serve any other frontend static file (CSS, JS, images)."""
        return send_from_directory(FRONTEND_DIR, filename)

    logger.info("=" * 60)
    logger.info("  LeadFlow AI Backend — Initialized Successfully")
    logger.info(f"  Debug Mode: {Config.FLASK_DEBUG}")
    logger.info(f"  Database:   {Config.DATABASE_PATH}")
    logger.info(f"  PDF Output: {Config.PDF_OUTPUT_DIR}")
    logger.info(f"  Rate Limit: {Config.RATE_LIMIT_PER_MINUTE} req/min")
    logger.info("=" * 60)

    return app


# --- Entry Point ---
if __name__ == "__main__":
    app = create_app()
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=Config.FLASK_DEBUG,
    )
