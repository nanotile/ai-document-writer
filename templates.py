#!/usr/bin/env python3
"""
Module: Document templates with system prompts for AI Document Writer
Version: 1.0.0
Development Iteration: v1

Project: AI Document Writer
Developer: Kent Benson
Created: 2026-01-29

Enhancement: Initial implementation - 8 document templates

Features:
- Formal Letter, Memo, Report, Email Draft
- Thank You Note, Meeting Summary, Personal Letter, General Document
- Each template has a system prompt controlling tone and structure

UV ENVIRONMENT: Run with `uv run python templates.py`
"""

from dataclasses import dataclass


@dataclass
class DocumentTemplate:
    """A document template with its AI system prompt."""
    name: str
    display_name: str
    description: str
    system_prompt: str
    placeholder: str  # Example input text for the notes area


TEMPLATES = [
    DocumentTemplate(
        name="formal_letter",
        display_name="Formal Letter",
        description="Business correspondence, requests, official letters",
        system_prompt=(
            "You are a professional letter writer. Generate a formal business letter "
            "based on the user's notes and bullet points. Use proper letter format with "
            "date, recipient address placeholder, salutation, body paragraphs, and closing. "
            "Tone should be professional, clear, and courteous. "
            "Output plain text only - no markdown formatting."
        ),
        placeholder="Recipient: John Smith, ABC Corp\nPurpose: Request meeting to discuss Q2 results\nKey points: revenue up 15%, new product launch in March",
    ),
    DocumentTemplate(
        name="memo",
        display_name="Memo",
        description="Internal communications, policy announcements",
        system_prompt=(
            "You are an internal communications writer. Generate a professional memo "
            "based on the user's notes. Use standard memo format: TO, FROM, DATE, "
            "SUBJECT header, then clear body paragraphs. Keep it concise and action-oriented. "
            "Output plain text only - no markdown formatting."
        ),
        placeholder="To: All staff\nSubject: New remote work policy\nKey changes: 3 days in office, flexible hours, equipment stipend",
    ),
    DocumentTemplate(
        name="report",
        display_name="Report",
        description="Research findings, analysis, structured reports",
        system_prompt=(
            "You are a report writer. Generate a structured report based on the user's notes. "
            "Include a title, executive summary, main sections with clear headings, and a "
            "conclusion or recommendations section. Use professional, analytical tone. "
            "Output plain text only - no markdown formatting. Use ALL CAPS for section headings."
        ),
        placeholder="Topic: Q4 Sales Performance\nFindings: Revenue $2.3M (up 12%), top product: Widget Pro, weak region: Northeast\nRecommendation: Increase Northeast marketing budget",
    ),
    DocumentTemplate(
        name="email_draft",
        display_name="Email Draft",
        description="Professional emails, follow-ups, introductions",
        system_prompt=(
            "You are an email writer. Generate a professional email based on the user's notes. "
            "Include a clear subject line suggestion, appropriate greeting, concise body, "
            "and professional sign-off. Keep it brief and action-oriented. "
            "Output plain text only - no markdown formatting."
        ),
        placeholder="To: Client (Sarah)\nContext: Follow up on proposal sent last week\nAsk: Schedule call to discuss questions, available Tue/Wed afternoon",
    ),
    DocumentTemplate(
        name="thank_you",
        display_name="Thank You Note",
        description="Gratitude, acknowledgments, appreciation",
        system_prompt=(
            "You are writing a thoughtful thank-you note. Based on the user's notes, "
            "generate a warm, sincere thank-you message. Be specific about what you're "
            "thanking them for and why it matters. Keep it genuine and heartfelt. "
            "Output plain text only - no markdown formatting."
        ),
        placeholder="Who: Dr. Martinez\nWhat: Excellent care during hospital stay\nSpecifics: Always took time to explain, very reassuring",
    ),
    DocumentTemplate(
        name="meeting_summary",
        display_name="Meeting Summary",
        description="Meeting notes to structured minutes",
        system_prompt=(
            "You are a meeting minutes writer. Convert the user's rough meeting notes "
            "into a structured meeting summary. Include: Meeting title, Date, Attendees "
            "(if provided), Key Discussion Points, Decisions Made, and Action Items "
            "with owners (if mentioned). Use clear, concise language. "
            "Output plain text only - no markdown formatting. Use ALL CAPS for section headings."
        ),
        placeholder="Meeting: Weekly team standup, Jan 29\nAttendees: Kent, Sarah, Mike\nDiscussed: Project deadline moved to Feb 15, need extra QA\nAction: Mike to hire contractor, Sarah to update timeline",
    ),
    DocumentTemplate(
        name="personal_letter",
        display_name="Personal Letter",
        description="Family, friends, personal correspondence",
        system_prompt=(
            "You are helping write a personal letter. Based on the user's notes, "
            "generate a warm, friendly letter suitable for family or friends. "
            "Match the tone to the relationship described. Be natural and conversational. "
            "Output plain text only - no markdown formatting."
        ),
        placeholder="To: My grandson Alex\nOccasion: His college graduation\nThemes: Proud of him, remember when he was little, excited for his future",
    ),
    DocumentTemplate(
        name="general",
        display_name="General Document",
        description="Freeform writing, no structure imposed",
        system_prompt=(
            "You are a versatile writer. Based on the user's notes and bullet points, "
            "generate a well-written document. Infer the appropriate tone, structure, "
            "and format from the content. Write clearly and professionally. "
            "Output plain text only - no markdown formatting."
        ),
        placeholder="Write about anything - enter your notes, ideas, or bullet points here",
    ),
]


TONE_OPTIONS = [
    "Formal",
    "Professional",
    "Friendly",
    "Casual",
    "Academic",
    "Persuasive",
]


def get_template_by_name(name: str) -> DocumentTemplate:
    """Look up a template by its internal name."""
    for t in TEMPLATES:
        if t.name == name:
            return t
    return TEMPLATES[-1]  # Default to General
