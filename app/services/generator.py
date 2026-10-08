from datetime import date
from pathlib import Path
from typing import Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from app.utils.logger import logger


class CertificateGenerator:
    """Predefined professional certificate template generator using ReportLab."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def generate_pdf(
        self,
        certificate_id: str,
        job_id: str,
        recipient_name: str,
        title: str,
        course_name: str,
        issuer_name: str,
        issue_date: Optional[date] = None,
    ) -> Path:
        """
        Generates a professional landscape PDF certificate.
        Returns the resolved Path to the generated PDF.
        """
        # Ensure job-specific output directory exists
        job_output_dir = self.output_dir / str(job_id)
        job_output_dir.mkdir(parents=True, exist_ok=True)

        file_path = job_output_dir / f"{certificate_id}.pdf"

        # Dimensions: A4 Landscape
        page_width, page_height = landscape(A4)
        c = canvas.Canvas(str(file_path), pagesize=landscape(A4))

        # Color Palette
        navy_primary = colors.HexColor("#0F172A")
        navy_secondary = colors.HexColor("#1E3A8A")
        gold_accent = colors.HexColor("#D97706")
        gold_light = colors.HexColor("#F59E0B")
        slate_muted = colors.HexColor("#64748B")
        bg_warm_white = colors.HexColor("#FAFAF9")

        # Background fill
        c.setFillColor(bg_warm_white)
        c.rect(0, 0, page_width, page_height, fill=1, stroke=0)

        # Outer border
        margin = 30
        c.setStrokeColor(navy_secondary)
        c.setLineWidth(3)
        c.rect(margin, margin, page_width - (2 * margin), page_height - (2 * margin), fill=0, stroke=1)

        # Inner decorative border
        inner_margin = margin + 8
        c.setStrokeColor(gold_accent)
        c.setLineWidth(1.5)
        c.rect(
            inner_margin,
            inner_margin,
            page_width - (2 * inner_margin),
            page_height - (2 * inner_margin),
            fill=0,
            stroke=1,
        )

        # Corner corner ornaments
        ornament_size = 14
        c.setFillColor(gold_light)
        # Top-left corner
        c.rect(inner_margin + 2, page_height - inner_margin - ornament_size - 2, ornament_size, ornament_size, fill=1, stroke=0)
        # Top-right corner
        c.rect(page_width - inner_margin - ornament_size - 4, page_height - inner_margin - ornament_size - 2, ornament_size, ornament_size, fill=1, stroke=0)
        # Bottom-left corner
        c.rect(inner_margin + 2, inner_margin + 4, ornament_size, ornament_size, fill=1, stroke=0)
        # Bottom-right corner
        c.rect(page_width - inner_margin - ornament_size - 4, inner_margin + 4, ornament_size, ornament_size, fill=1, stroke=0)

        # Header Subtitle
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(gold_accent)
        c.drawCentredString(page_width / 2.0, page_height - 90, "O F F I C I A L   C E R T I F I C A T I O N")

        # Main Certificate Title
        c.setFont("Helvetica-Bold", 28)
        c.setFillColor(navy_primary)
        c.drawCentredString(page_width / 2.0, page_height - 128, title.upper())

        # Decorative line below title
        c.setStrokeColor(gold_accent)
        c.setLineWidth(1)
        c.line(page_width / 2.0 - 120, page_height - 142, page_width / 2.0 + 120, page_height - 142)

        # Presentation lead text
        c.setFont("Helvetica", 12)
        c.setFillColor(slate_muted)
        c.drawCentredString(page_width / 2.0, page_height - 180, "THIS IS PROUDLY PRESENTED TO")

        # Recipient Name (prominent)
        c.setFont("Helvetica-Bold", 32)
        c.setFillColor(navy_secondary)
        c.drawCentredString(page_width / 2.0, page_height - 230, recipient_name)

        # Accent underline under name
        name_line_width = min(len(recipient_name) * 16, 420)
        c.setStrokeColor(gold_light)
        c.setLineWidth(2)
        c.line(
            page_width / 2.0 - (name_line_width / 2.0),
            page_height - 245,
            page_width / 2.0 + (name_line_width / 2.0),
            page_height - 245,
        )

        # Achievement description
        c.setFont("Helvetica", 12)
        c.setFillColor(slate_muted)
        c.drawCentredString(
            page_width / 2.0,
            page_height - 280,
            "for successfully completing and fulfilling all requirements of the program",
        )

        # Course / Event Name
        c.setFont("Helvetica-Bold", 20)
        c.setFillColor(navy_primary)
        c.drawCentredString(page_width / 2.0, page_height - 318, course_name)

        # Lower Section: Date (Left), Verification Badge (Center), Issuer / Signature (Right)
        # Left: Date
        date_str = (issue_date or date.today()).strftime("%B %d, %Y")
        c.setFont("Helvetica", 10)
        c.setFillColor(slate_muted)
        c.drawString(inner_margin + 60, 140, "DATE OF ISSUANCE")
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(navy_primary)
        c.drawString(inner_margin + 60, 120, date_str)
        c.setStrokeColor(slate_muted)
        c.setLineWidth(0.8)
        c.line(inner_margin + 60, 112, inner_margin + 220, 112)

        # Center: Verification Badge Icon
        badge_x = page_width / 2.0
        badge_y = 125
        c.setStrokeColor(gold_accent)
        c.setLineWidth(2)
        c.circle(badge_x, badge_y, 24, fill=0, stroke=1)
        c.circle(badge_x, badge_y, 21, fill=0, stroke=1)
        c.setFont("Helvetica-Bold", 7)
        c.setFillColor(gold_accent)
        c.drawCentredString(badge_x, badge_y + 3, "OFFICIAL")
        c.drawCentredString(badge_x, badge_y - 6, "VERIFIED")

        # Right: Issuer and Signature line
        right_start = page_width - inner_margin - 220
        c.setStrokeColor(slate_muted)
        c.setLineWidth(0.8)
        c.line(right_start, 112, right_start + 160, 112)
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(navy_primary)
        c.drawRightString(right_start + 160, 120, issuer_name)
        c.setFont("Helvetica", 10)
        c.setFillColor(slate_muted)
        c.drawRightString(right_start + 160, 95, "AUTHORIZED SIGNATURE")

        # Bottom verification footer
        c.setFont("Helvetica", 8)
        c.setFillColor(slate_muted)
        c.drawCentredString(
            page_width / 2.0,
            inner_margin + 16,
            f"Certificate ID: {certificate_id}  |  Issued by {issuer_name}  |  Secure Verification Record",
        )

        c.showPage()
        c.save()

        logger.info(f"Certificate PDF generated: {file_path}")
        return file_path
