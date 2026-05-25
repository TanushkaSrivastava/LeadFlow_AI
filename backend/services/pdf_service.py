"""
=============================================================================
PDF Generation Service
=============================================================================
Converts AI-generated report data into a professionally formatted PDF
using ReportLab. Includes title page, sections, bullet lists, and footers.
=============================================================================
"""

import os
import logging
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

from config.config import Config
from utils.helpers import sanitize_filename

logger = logging.getLogger(__name__)

# --- Color Palette ---
PRIMARY = HexColor("#1a237e")       # Deep indigo
ACCENT = HexColor("#0d47a1")        # Blue
LIGHT_BG = HexColor("#e8eaf6")      # Light indigo background
TEXT_DARK = HexColor("#212121")      # Near black
TEXT_GRAY = HexColor("#616161")      # Gray
SECTION_BG = HexColor("#c5cae9")    # Section header background


def generate_pdf(report_data: dict, lead, request_id: str) -> str:
    """
    Generate a professional PDF report from AI-generated data.

    Args:
        report_data: Structured report dict from the AI service.
        lead:        Lead model instance with name, company, etc.
        request_id:  Unique request identifier for the filename.

    Returns:
        Absolute path to the generated PDF file.
    """
    # Ensure output directory exists
    os.makedirs(Config.PDF_OUTPUT_DIR, exist_ok=True)

    # Build filename
    safe_company = sanitize_filename(lead.company)
    filename = f"Report_{safe_company}_{request_id}.pdf"
    filepath = os.path.join(Config.PDF_OUTPUT_DIR, filename)

    logger.info(f"Generating PDF: {filepath}")

    # Create document
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=25 * mm,
        bottomMargin=20 * mm,
    )

    # Build styles
    styles = _create_styles()

    # Build content
    story = []
    _add_title_page(story, styles, report_data, lead, request_id)
    story.append(PageBreak())
    _add_report_body(story, styles, report_data)
    _add_footer_note(story, styles, request_id)

    # Generate PDF
    doc.build(story)
    logger.info(f"PDF generated successfully: {filepath}")

    return os.path.abspath(filepath)


def _create_styles() -> dict:
    """Create custom paragraph styles for the PDF."""
    base = getSampleStyleSheet()
    custom = {}

    custom["title"] = ParagraphStyle(
        "CustomTitle", parent=base["Title"],
        fontSize=28, textColor=PRIMARY, spaceAfter=6,
        alignment=TA_CENTER, fontName="Helvetica-Bold",
    )
    custom["subtitle"] = ParagraphStyle(
        "CustomSubtitle", parent=base["Normal"],
        fontSize=14, textColor=ACCENT, spaceAfter=20,
        alignment=TA_CENTER, fontName="Helvetica",
    )
    custom["section_header"] = ParagraphStyle(
        "SectionHeader", parent=base["Heading2"],
        fontSize=16, textColor=PRIMARY, spaceBefore=20,
        spaceAfter=10, fontName="Helvetica-Bold",
        borderPadding=(5, 5, 5, 5),
    )
    custom["body"] = ParagraphStyle(
        "BodyText", parent=base["Normal"],
        fontSize=11, textColor=TEXT_DARK, spaceAfter=8,
        alignment=TA_JUSTIFY, fontName="Helvetica",
        leading=16,
    )
    custom["bullet"] = ParagraphStyle(
        "BulletText", parent=base["Normal"],
        fontSize=11, textColor=TEXT_DARK, spaceAfter=6,
        leftIndent=20, fontName="Helvetica", leading=15,
        bulletIndent=8,
    )
    custom["meta"] = ParagraphStyle(
        "MetaText", parent=base["Normal"],
        fontSize=9, textColor=TEXT_GRAY, alignment=TA_CENTER,
        spaceAfter=4, fontName="Helvetica",
    )
    custom["footer"] = ParagraphStyle(
        "FooterText", parent=base["Normal"],
        fontSize=8, textColor=TEXT_GRAY, alignment=TA_CENTER,
        spaceBefore=30, fontName="Helvetica-Oblique",
    )

    return custom


def _add_title_page(story, styles, report_data, lead, request_id):
    """Add the title page with company info and metadata."""
    story.append(Spacer(1, 80))

    # Title
    company_name = report_data.get("company_name", lead.company)
    story.append(Paragraph(f"Business Audit Report", styles["title"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph(company_name, styles["subtitle"]))

    # Horizontal rule
    story.append(Spacer(1, 10))
    story.append(HRFlowable(
        width="60%", thickness=2, color=ACCENT,
        spaceBefore=10, spaceAfter=20, hAlign="CENTER",
    ))

    # Metadata table
    now = datetime.now(timezone.utc).strftime("%B %d, %Y")
    industry = report_data.get("industry", "N/A")
    meta_data = [
        ["Prepared For:", lead.name],
        ["Company:", company_name],
        ["Industry:", industry],
        ["Date:", now],
        ["Request ID:", request_id],
    ]
    meta_table = Table(meta_data, colWidths=[120, 300])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("TEXTCOLOR", (0, 0), (0, -1), ACCENT),
        ("TEXTCOLOR", (1, 0), (1, -1), TEXT_DARK),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
    ]))
    story.append(meta_table)

    story.append(Spacer(1, 40))
    story.append(Paragraph(
        "This report was generated by LeadFlow AI — an automated business intelligence system.",
        styles["meta"],
    ))


def _add_report_body(story, styles, report_data):
    """Add the main report sections with content."""
    # --- Company Overview ---
    _add_section(story, styles, "1. Company Overview",
                 report_data.get("company_overview", "No overview available."))

    # --- Key Strengths ---
    _add_section_with_bullets(story, styles, "2. Key Strengths",
                              report_data.get("key_strengths", []))

    # --- Weaknesses ---
    _add_section_with_bullets(story, styles, "3. Weaknesses",
                              report_data.get("weaknesses", []))

    # --- Growth Opportunities ---
    _add_section_with_bullets(story, styles, "4. Growth Opportunities",
                              report_data.get("growth_opportunities", []))

    # --- Strategic Recommendations ---
    _add_section_with_bullets(story, styles, "5. Strategic Recommendations",
                              report_data.get("strategic_recommendations", []))


def _add_section(story, styles, title, body_text):
    """Add a text section with header and body paragraph."""
    story.append(HRFlowable(
        width="100%", thickness=1, color=LIGHT_BG,
        spaceBefore=10, spaceAfter=5,
    ))
    story.append(Paragraph(title, styles["section_header"]))
    story.append(Paragraph(body_text, styles["body"]))


def _add_section_with_bullets(story, styles, title, items):
    """Add a section with header and bullet-point list."""
    story.append(HRFlowable(
        width="100%", thickness=1, color=LIGHT_BG,
        spaceBefore=10, spaceAfter=5,
    ))
    story.append(Paragraph(title, styles["section_header"]))

    if not items:
        story.append(Paragraph("No data available for this section.", styles["body"]))
        return

    for item in items:
        bullet_text = f"\u2022  {item}"
        story.append(Paragraph(bullet_text, styles["bullet"]))


def _add_footer_note(story, styles, request_id):
    """Add a footer disclaimer to the report."""
    story.append(Spacer(1, 30))
    story.append(HRFlowable(
        width="80%", thickness=1, color=LIGHT_BG,
        spaceBefore=10, spaceAfter=10, hAlign="CENTER",
    ))
    story.append(Paragraph(
        f"Report ID: {request_id} | Generated by LeadFlow AI | "
        "This report is for informational purposes only.",
        styles["footer"],
    ))
