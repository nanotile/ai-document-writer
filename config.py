#!/usr/bin/env python3
"""
Module: Configuration and settings for AI Document Writer
Version: 1.0.0
Development Iteration: v1

Project: AI Document Writer
Developer: Kent Benson
Created: 2026-01-29

Enhancement: Initial implementation

Features:
- API key loading from .env
- Font and UI configuration
- Default paths

UV ENVIRONMENT: Run with `uv run python config.py`

INSTALLATION:
uv add python-dotenv
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project directory
load_dotenv(Path(__file__).parent / ".env")

# API Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

# Paths
DRAFTS_DIR = Path.home() / "Documents" / "AI Writer Drafts"
DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

# UI Configuration
FONT_FAMILY = "DejaVu Sans"
FONT_SIZE_NORMAL = 14
FONT_SIZE_LARGE = 16
FONT_SIZE_HEADING = 18
FONT_SIZE_SMALL = 12

# Window
WINDOW_TITLE = "AI Document Writer"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
WINDOW_MIN_WIDTH = 900
WINDOW_MIN_HEIGHT = 600

# Colors
BG_COLOR = "#FAFAFA"
SIDEBAR_BG = "#E8E8E8"
BUTTON_BG = "#2563EB"
BUTTON_FG = "#FFFFFF"
BUTTON_ACTIVE_BG = "#1D4ED8"
SELECTED_BG = "#BFDBFE"
STATUS_BG = "#F3F4F6"
TEXT_BG = "#FFFFFF"
HEADING_COLOR = "#1E3A5F"

# Button dimensions
BUTTON_WIDTH = 18
BUTTON_HEIGHT = 2
BUTTON_PADX = 10
BUTTON_PADY = 5
