#!/usr/bin/env python3
"""
Module: PDF export for AI Document Writer
Version: 1.0.0
Development Iteration: v1

Project: AI Document Writer
Developer: Kent Benson
Created: 2026-01-29

Enhancement: Initial implementation - adapted from deep-research-agent

Features:
- Convert plain text documents to PDF
- Unicode font support
- Clean document formatting with title and date

UV ENVIRONMENT: Run with `uv run python export_pdf.py`

INSTALLATION:
uv add fpdf2
"""

import os
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fpdf import FPDF

from config import DRAFTS_DIR

logger = logging.getLogger(__name__)


def _get_unicode_font_path() -> Optional[str]:
    """Find a Unicode-capable TTF font on the system."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


class DocumentPDF(FPDF):
    """Custom PDF for document export with header/footer."""

    def __init__(self, title: str = "Document"):
        super().__init__()
        self.doc_title = title
        self.set_auto_page_break(auto=True, margin=20)
        self._setup_fonts()

    def _setup_fonts(self):
        """Register Unicode font if available."""
        font_path = _get_unicode_font_path()
        if font_path:
            self.add_font("UniSans", "", font_path, uni=True)
            bold_path = font_path.replace("Sans.ttf", "Sans-Bold.ttf").replace("Regular.ttf", "Bold.ttf")
            self.add_font("UniSans", "B", bold_path if os.path.exists(bold_path) else font_path, uni=True)
            self.add_font("UniSans", "I", font_path, uni=True)
            self._font_family = "UniSans"
        else:
            self._font_family = "Helvetica"

    @property
    def font_name(self):
        return self._font_family

    def header(self):
        self.set_font(self.font_name, "B", 11)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, self.doc_title, align="L")
        self.cell(0, 10, datetime.now().strftime("%B %d, %Y"), align="R", new_x="LMARGIN", new_y="NEXT")
        self.line(10, 22, 200, 22)
        self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.font_name, "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def export_to_pdf(
    text: str,
    title: str = "Document",
    output_path: Optional[str] = None,
) -> Optional[str]:
    """
    Export plain text document to PDF.

    Args:
        text: The document text to export
        title: Title for the PDF header
        output_path: Where to save. If None, saves to drafts directory.

    Returns:
        Path to saved PDF, or None on error
    """
    if not text.strip():
        logger.error("No text to export")
        return None

    try:
        pdf = DocumentPDF(title=title)
        pdf.alias_nb_pages()
        pdf.add_page()

        # Render text line by line, detecting simple structure
        lines = text.split('\n')
        for line in lines:
            stripped = line.strip()

            if not stripped:
                pdf.ln(4)
                continue

            # ALL CAPS lines treated as section headings
            if stripped.isupper() and len(stripped) > 3 and len(stripped) < 80:
                pdf.ln(4)
                pdf.set_font(pdf.font_name, "B", 13)
                pdf.set_text_color(0, 51, 102)
                pdf.multi_cell(0, 7, stripped)
                pdf.ln(2)
            # Lines ending with colon could be sub-headings
            elif stripped.endswith(':') and len(stripped) < 60 and '\n' not in stripped:
                pdf.ln(2)
                pdf.set_font(pdf.font_name, "B", 11)
                pdf.set_text_color(51, 51, 51)
                pdf.multi_cell(0, 6, stripped)
                pdf.ln(1)
            # Bullet points
            elif stripped.startswith('- ') or stripped.startswith('* '):
                pdf.set_font(pdf.font_name, "", 11)
                pdf.set_text_color(0, 0, 0)
                pdf.set_x(pdf.l_margin + 5)
                pdf.multi_cell(0, 6, f"  {stripped}")
            # Numbered items
            elif re.match(r'^\d+[\.\)]\s', stripped):
                pdf.set_font(pdf.font_name, "", 11)
                pdf.set_text_color(0, 0, 0)
                pdf.set_x(pdf.l_margin + 5)
                pdf.multi_cell(0, 6, f"  {stripped}")
            # Regular text
            else:
                pdf.set_font(pdf.font_name, "", 11)
                pdf.set_text_color(0, 0, 0)
                pdf.multi_cell(0, 6, stripped)

        # Determine output path
        if output_path is None:
            clean_name = re.sub(r'[^\w\s-]', '', title)[:30].replace(' ', '_')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{clean_name}_{timestamp}.pdf"
            output_path = str(DRAFTS_DIR / filename)

        # Ensure directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        pdf.output(output_path)
        logger.info(f"PDF exported: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Failed to export PDF: {e}", exc_info=True)
        return None
