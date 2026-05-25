"""
=============================================================================
Lead Routes
=============================================================================
Flask Blueprint defining the API endpoints for lead processing.
Includes the main POST /generate-report endpoint, health check, and logs.
=============================================================================
"""

import logging
from flask import Blueprint, request, jsonify
from controllers.lead_controller import process_lead
from services.logging_service import get_all_logs

logger = logging.getLogger(__name__)

# Create Blueprint
lead_bp = Blueprint("lead", __name__)


@lead_bp.route("/generate-report", methods=["POST"])
def generate_report():
    """
    Main API endpoint — accepts lead data and triggers the full pipeline.

    Expects JSON body:
    {
        "name": "string",
        "email": "string",
        "company": "string",
        "website": "string"
    }

    Returns:
        JSON response with status, message, and request tracking ID.
    """
    # Ensure request has JSON content
    if not request.is_json:
        return jsonify({
            "status": "error",
            "message": "Request must be JSON. Set Content-Type: application/json",
        }), 400

    data = request.get_json()

    if not data:
        return jsonify({
            "status": "error",
            "message": "Empty request body",
        }), 400

    logger.info(f"Received lead request for company: {data.get('company', 'unknown')}")

    # Delegate to controller
    response, status_code = process_lead(data)
    return jsonify(response), status_code


@lead_bp.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint for monitoring.
    Returns basic service status.
    """
    return jsonify({
        "status": "healthy",
        "service": "LeadFlow AI Backend",
        "version": "1.0.0",
    }), 200


@lead_bp.route("/logs", methods=["GET"])
def view_logs():
    """
    Retrieve recent activity logs from the database.
    Useful for debugging and monitoring pipeline activity.
    """
    try:
        logs = get_all_logs()
        return jsonify({
            "status": "success",
            "count": len(logs),
            "logs": logs,
        }), 200
    except Exception as e:
        logger.error(f"Failed to retrieve logs: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve logs: {str(e)}",
        }), 500
