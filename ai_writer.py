#!/usr/bin/env python3
"""
Module: AI writing engine using Claude API for AI Document Writer
Version: 1.0.0
Development Iteration: v1

Project: AI Document Writer
Developer: Kent Benson
Created: 2026-01-29

Enhancement: Initial implementation

Features:
- Generate document drafts from notes + template
- Refine existing text (change tone, shorten, expand, custom instruction)
- Sync Anthropic client for use with threading

UV ENVIRONMENT: Run with `uv run python ai_writer.py`

INSTALLATION:
uv add anthropic python-dotenv
"""

import logging
from anthropic import Anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from templates import DocumentTemplate

logger = logging.getLogger(__name__)

# Initialize sync client
client = Anthropic(api_key=ANTHROPIC_API_KEY)


def generate_draft(
    template: DocumentTemplate,
    notes: str,
    tone: str = "Professional",
) -> str:
    """
    Generate a document draft from user notes using a template's system prompt.

    Args:
        template: The document template to use
        notes: User's rough notes / bullet points
        tone: Desired tone (Formal, Professional, Friendly, etc.)

    Returns:
        Generated document text (plain text, no markdown)
    """
    if not notes.strip():
        return "Please enter some notes or bullet points first."

    if not ANTHROPIC_API_KEY:
        return "Error: ANTHROPIC_API_KEY not set. Please add it to your .env file."

    system_prompt = (
        f"{template.system_prompt}\n\n"
        f"Tone: {tone}\n"
        f"Important: Output ONLY the document text. No preamble, no explanations, "
        f"no markdown. Just the finished document ready to read or print."
    )

    user_message = (
        f"Document type: {template.display_name}\n\n"
        f"My notes and bullet points:\n{notes}"
    )

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text.strip()

    except Exception as e:
        logger.error(f"Failed to generate draft: {e}")
        return f"Error generating draft: {e}"


def refine_text(
    current_text: str,
    instruction: str,
    template_name: str = "general",
) -> str:
    """
    Refine existing document text based on user instruction.

    Args:
        current_text: The current document text
        instruction: What to change (e.g., "make it shorter", "more formal")
        template_name: Template name for context

    Returns:
        Refined document text
    """
    if not current_text.strip():
        return "No text to refine. Generate a draft first."

    if not instruction.strip():
        return current_text

    if not ANTHROPIC_API_KEY:
        return "Error: ANTHROPIC_API_KEY not set. Please add it to your .env file."

    system_prompt = (
        "You are a document editor. The user has a document and wants changes made. "
        "Apply the requested changes while preserving the document's overall structure "
        "and meaning unless told otherwise. "
        "Output ONLY the revised document text. No preamble, no explanations, no markdown."
    )

    user_message = (
        f"Here is the current document:\n\n{current_text}\n\n"
        f"Please make this change: {instruction}"
    )

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text.strip()

    except Exception as e:
        logger.error(f"Failed to refine text: {e}")
        return f"Error refining text: {e}"


if __name__ == "__main__":
    # Quick test
    from templates import TEMPLATES
    template = TEMPLATES[0]  # Formal Letter
    notes = "To: City Council\nRe: Pothole on Main Street\nBeen there 3 months, dangerous"
    print("Generating draft...")
    result = generate_draft(template, notes, "Formal")
    print(result)
