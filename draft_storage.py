#!/usr/bin/env python3
"""
Module: Draft save/load for AI Document Writer
Version: 1.0.0
Development Iteration: v1

Project: AI Document Writer
Developer: Kent Benson
Created: 2026-01-29

Enhancement: Initial implementation

Features:
- Save drafts as JSON to ~/Documents/AI Writer Drafts/
- Load drafts back into the editor
- List available drafts

UV ENVIRONMENT: Run with `uv run python draft_storage.py`

INSTALLATION:
uv add pydantic
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from config import DRAFTS_DIR

logger = logging.getLogger(__name__)


class Draft(BaseModel):
    """A saved document draft."""
    title: str
    template_name: str
    tone: str
    notes: str
    document_text: str
    saved_at: str
    filename: str = ""


def save_draft(
    title: str,
    template_name: str,
    tone: str,
    notes: str,
    document_text: str,
) -> Optional[str]:
    """
    Save a draft to the drafts directory.

    Returns:
        Path to saved file, or None on error
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)[:40]
        clean_title = clean_title.strip().replace(" ", "_") or "untitled"
        filename = f"{clean_title}_{timestamp}.json"

        draft = Draft(
            title=title,
            template_name=template_name,
            tone=tone,
            notes=notes,
            document_text=document_text,
            saved_at=datetime.now().isoformat(),
            filename=filename,
        )

        filepath = DRAFTS_DIR / filename
        filepath.write_text(draft.model_dump_json(indent=2))
        logger.info(f"Draft saved: {filepath}")
        return str(filepath)

    except Exception as e:
        logger.error(f"Failed to save draft: {e}")
        return None


def load_draft(filepath: str) -> Optional[Draft]:
    """Load a draft from a JSON file."""
    try:
        path = Path(filepath)
        if not path.exists():
            logger.error(f"Draft not found: {filepath}")
            return None
        data = json.loads(path.read_text())
        return Draft(**data)
    except Exception as e:
        logger.error(f"Failed to load draft: {e}")
        return None


def list_drafts() -> list[dict]:
    """
    List all saved drafts, newest first.

    Returns:
        List of dicts with 'title', 'saved_at', 'filepath', 'template_name'
    """
    drafts = []
    try:
        for f in sorted(DRAFTS_DIR.glob("*.json"), reverse=True):
            try:
                data = json.loads(f.read_text())
                drafts.append({
                    "title": data.get("title", "Untitled"),
                    "saved_at": data.get("saved_at", ""),
                    "filepath": str(f),
                    "template_name": data.get("template_name", "general"),
                })
            except Exception:
                continue
    except Exception as e:
        logger.error(f"Failed to list drafts: {e}")
    return drafts
