"""Tests for export_pdf.py — PDF generation with real fpdf2."""

from pathlib import Path

import pytest

from export_pdf import export_to_pdf, DocumentPDF


class TestExportToPdf:
    """Tests for export_to_pdf()."""

    def test_creates_pdf_file(self, tmp_drafts_dir, sample_document_text):
        path = export_to_pdf(sample_document_text, title="Test Doc")
        assert path is not None
        assert Path(path).exists()
        assert path.endswith(".pdf")

    def test_returns_none_for_empty_text(self, tmp_drafts_dir):
        assert export_to_pdf("") is None
        assert export_to_pdf("   ") is None
        assert export_to_pdf("\n\n") is None

    def test_uses_custom_output_path(self, tmp_drafts_dir, sample_document_text):
        custom = str(tmp_drafts_dir / "custom_output.pdf")
        path = export_to_pdf(sample_document_text, title="Custom", output_path=custom)
        assert path == custom
        assert Path(custom).exists()

    def test_auto_generates_filename_with_sanitized_title(self, tmp_drafts_dir):
        path = export_to_pdf("Some content here.", title="My Report!")
        filename = Path(path).name
        assert "!" not in filename
        assert filename.endswith(".pdf")

    def test_title_sanitization_truncates_long_names(self, tmp_drafts_dir):
        long_title = "A" * 100
        path = export_to_pdf("Content.", title=long_title)
        filename = Path(path).name
        # Title portion capped at 30 chars
        title_part = filename.split("_2")[0]  # Before timestamp
        assert len(title_part) <= 30

    def test_file_is_valid_pdf(self, tmp_drafts_dir, sample_document_text):
        path = export_to_pdf(sample_document_text, title="Valid PDF")
        with open(path, "rb") as f:
            header = f.read(5)
        assert header == b"%PDF-"

    def test_creates_parent_directories(self, tmp_path, sample_document_text):
        nested = tmp_path / "a" / "b" / "c" / "test.pdf"
        path = export_to_pdf(sample_document_text, output_path=str(nested))
        assert Path(path).exists()


class TestDocumentPDF:
    """Tests for DocumentPDF class."""

    def test_header_footer_no_crash(self, tmp_drafts_dir):
        """Multi-page document should render header/footer without errors."""
        # Use short lines separated by blanks to force clean page breaks
        paragraphs = []
        for i in range(100):
            paragraphs.append(f"Paragraph {i} text.")
            paragraphs.append("")
        long_text = "\n".join(paragraphs)
        path = export_to_pdf(long_text, title="Multi Page")
        assert path is not None
        assert Path(path).exists()

    def test_document_pdf_sets_title(self):
        pdf = DocumentPDF(title="My Title")
        assert pdf.doc_title == "My Title"
