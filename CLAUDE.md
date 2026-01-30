# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Document Writer is a Python/Tkinter desktop application that uses Claude AI to generate and refine documents from user notes. Users select a template and tone, enter notes, and the app calls the Anthropic API to produce a draft that can be refined and exported as PDF or DOCX.

## Commands

```bash
# Install dependencies
uv sync

# Run the application
uv run python main_app.py

# Run with stub entry point
uv run python main.py
```

No test suite or linter is currently configured.

## Architecture

```
Tkinter GUI (main_app.py)
    ├── ai_writer.py      → Anthropic Claude API (generate_draft, refine_text)
    ├── templates.py       → 8 DocumentTemplate dataclasses with system prompts + tone options
    ├── draft_storage.py   → Pydantic Draft model, JSON persistence to ~/Documents/AI Writer Drafts/
    ├── export_pdf.py      → PDF export via fpdf2 with Unicode font detection
    ├── export_docx.py     → Word export via python-docx
    └── config.py          → API keys (.env), UI fonts/colors, window dimensions
```

**Key patterns:**
- `main_app.py` (DocumentWriterApp) uses background threading + Queue polling (`after()`) for API calls to keep the UI responsive — the Anthropic client is synchronous
- Templates define both the Claude system prompt and placeholder text; tone is injected into the user message
- All file exports go to `~/Documents/AI Writer Drafts/` using `Path.home()`
- `export_pdf.py` auto-detects formatting: ALL CAPS lines become section headings, lines ending with `:` become sub-headings, bullet/numbered lists are detected and indented
- API key loaded from `.env` via python-dotenv; `config.py` provides defaults

## Environment

- Python 3.13, managed with **uv** (never pip/conda)
- API key in `.env` file (ANTHROPIC_API_KEY) — not committed to git
- Default model: `claude-sonnet-4-20250514` (configurable via CLAUDE_MODEL env var)
- Max tokens per generation: 4096
