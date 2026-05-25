"""
=============================================================================
Lead Controller
=============================================================================
Orchestrates the entire lead processing pipeline. Calls each service in
sequence: validate → enrich → AI report → PDF → email → log.
Each step has try-except with appropriate fallbacks.
=============================================================================
"""

import logging

from models.lead_model import Lead
from utils.helpers import generate_request_id, get_timestamp
from services.validation_service import validate_lead
from services.enrichment_service import enrich_company
from services.ai_service import generate_report
from services.pdf_service import generate_pdf
from services.email_service import send_report_email
from services.logging_service import save_lead, log_activity

logger = logging.getLogger(__name__)


def process_lead(data: dict) -> tuple[dict, int]:
    """
    Main orchestration function for processing a lead submission.

    Pipeline:
        1. Generate request ID
        2. Validate input
        3. Create Lead model
        4. Log "processing" status
        5. Enrich company data (with fallback)
        6. Generate AI report (with retry)
        7. Generate PDF
        8. Send email (with retry)
        9. Log "success" status
        10. Return success response

    Args:
        data: Raw JSON data from the API request.

    Returns:
        Tuple of (response_dict, http_status_code).
    """
    # --- Step 1: Generate unique request ID ---
    request_id = generate_request_id()
    logger.info(f"[{request_id}] New lead processing started")

    # --- Step 2: Validate input ---
    is_valid, errors = validate_lead(data)
    if not is_valid:
        logger.warning(f"[{request_id}] Validation failed: {errors}")
        return {
            "status": "error",
            "request_id": request_id,
            "message": "Validation failed",
            "errors": errors,
        }, 400

    # --- Step 3: Create Lead model ---
    lead = Lead(
        name=data["name"].strip(),
        email=data["email"].strip(),
        company=data["company"].strip(),
        website=data["website"].strip(),
        request_id=request_id,
        timestamp=get_timestamp(),
    )
    logger.info(f"[{request_id}] Lead created: {lead}")

    # --- Step 4: Save lead and log "processing" ---
    try:
        save_lead(lead)
        log_activity(lead, "processing", request_id, "Pipeline started")
    except Exception as e:
        logger.error(f"[{request_id}] Failed to save lead: {e}")
        # Non-fatal: continue processing even if logging fails

    # --- Step 5: Enrich company data ---
    try:
        logger.info(f"[{request_id}] Enriching company data from {lead.website}")
        enrichment_data = enrich_company(lead.website, lead.company)
        enrichment_source = enrichment_data.get("source", "unknown")
        logger.info(f"[{request_id}] Enrichment complete (source: {enrichment_source})")
    except Exception as e:
        logger.error(f"[{request_id}] Enrichment failed: {e}")
        # Fallback: use minimal enrichment data
        enrichment_data = {
            "description": f"{lead.company} — enrichment unavailable",
            "industry": "General Business",
            "services": [],
            "source": "fallback_error",
        }

    industry = enrichment_data.get("industry", "General Business")

    # --- Step 6: Generate AI report ---
    try:
        logger.info(f"[{request_id}] Generating AI report")
        report_data = generate_report(lead.company, industry, enrichment_data)
        logger.info(f"[{request_id}] AI report generated successfully")
    except Exception as e:
        logger.error(f"[{request_id}] AI report generation failed: {e}")
        log_activity(lead, "failed", request_id, f"AI generation error: {str(e)}")
        return {
            "status": "error",
            "request_id": request_id,
            "message": f"AI report generation failed: {str(e)}",
        }, 500

    # --- Step 7: Generate PDF ---
    try:
        logger.info(f"[{request_id}] Generating PDF")
        pdf_path = generate_pdf(report_data, lead, request_id)
        logger.info(f"[{request_id}] PDF generated: {pdf_path}")
    except Exception as e:
        logger.error(f"[{request_id}] PDF generation failed: {e}")
        log_activity(lead, "failed", request_id, f"PDF error: {str(e)}")
        return {
            "status": "error",
            "request_id": request_id,
            "message": f"PDF generation failed: {str(e)}",
        }, 500

    # --- Step 8: Send email ---
    email_sent = False
    try:
        logger.info(f"[{request_id}] Sending email to {lead.email}")
        email_sent = send_report_email(lead.email, lead.name, lead.company, pdf_path)
        if email_sent:
            logger.info(f"[{request_id}] Email sent successfully")
        else:
            logger.warning(f"[{request_id}] Email sending returned False")
    except Exception as e:
        logger.error(f"[{request_id}] Email sending failed: {e}")
        # Non-fatal: report was still generated

    # --- Step 9: Log final status ---
    if email_sent:
        status = "success"
        details = "Report generated and emailed successfully"
    else:
        status = "partial_success"
        details = "Report generated but email delivery failed"

    try:
        log_activity(lead, status, request_id, details)
    except Exception as e:
        logger.error(f"[{request_id}] Failed to log final status: {e}")

    # --- Step 10: Return response ---
    response = {
        "status": "success",
        "request_id": request_id,
        "message": "Report generated and sent successfully" if email_sent
                   else "Report generated successfully (email delivery failed — check SMTP config)",
        "data": {
            "company": lead.company,
            "email": lead.email,
            "pdf_path": pdf_path,
            "email_sent": email_sent,
            "enrichment_source": enrichment_data.get("source", "unknown"),
        },
        "report_data": report_data,  # AI report data for frontend preview
    }

    logger.info(f"[{request_id}] Pipeline complete — status: {status}")
    return response, 200
