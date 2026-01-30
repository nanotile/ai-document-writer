"""Shared fixtures for AI Document Writer tests."""

import sys
from pathlib import Path

import pytest

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def tmp_drafts_dir(tmp_path, monkeypatch):
    """Temporary directory patched over config.DRAFTS_DIR."""
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    monkeypatch.setattr("config.DRAFTS_DIR", drafts)
    monkeypatch.setattr("draft_storage.DRAFTS_DIR", drafts)
    monkeypatch.setattr("export_pdf.DRAFTS_DIR", drafts)
    monkeypatch.setattr("export_docx.DRAFTS_DIR", drafts)
    return drafts


@pytest.fixture
def sample_document_text():
    """Multi-format text with headings, bullets, numbered lists, and paragraphs."""
    return (
        "EXECUTIVE SUMMARY\n"
        "\n"
        "This report covers the quarterly performance.\n"
        "\n"
        "KEY FINDINGS\n"
        "\n"
        "Important results:\n"
        "- Revenue increased by 15%\n"
        "- Customer satisfaction improved\n"
        "* New markets explored\n"
        "\n"
        "Action items:\n"
        "1. Hire two new engineers\n"
        "2) Expand to European market\n"
        "3. Update product roadmap\n"
        "\n"
        "Regular paragraph text goes here.\n"
    )


@pytest.fixture
def sample_notes():
    """Example user notes for document generation."""
    return (
        "To: City Council\n"
        "Re: Pothole on Main Street\n"
        "Been there 3 months, dangerous for cyclists"
    )
