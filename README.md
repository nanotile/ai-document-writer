# AI Document Writer

A desktop application that uses Claude AI to generate polished documents from your notes. Select a template, choose a tone, paste your notes, and get a ready-to-export document in seconds.

## Features

- **8 Document Templates** — Formal Letter, Memo, Report, Email, Thank You, Meeting Summary, Personal Letter, General
- **6 Tone Options** — Formal, Professional, Friendly, Casual, Academic, Persuasive
- **Draft Refinement** — Iterate on generated documents with natural language instructions (e.g., "make it shorter", "add more detail")
- **Export to PDF & DOCX** — Auto-formatted with headings, bullet points, and numbered lists
- **Save & Load Drafts** — Persist work as JSON files for later editing

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- An [Anthropic API key](https://console.anthropic.com/)

## Setup

```bash
# Clone the repository
git clone https://github.com/nanotile/ai-document-writer.git
cd ai-document-writer

# Install dependencies
uv sync

# Add your API key
echo "ANTHROPIC_API_KEY=your-key-here" > .env

# Run the application
uv run python main_app.py
```

## Configuration

Environment variables (set in `.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | *(required)* | Your Anthropic API key |
| `CLAUDE_MODEL` | `claude-sonnet-4-20250514` | Claude model to use |

## How It Works

1. **Select a template** from the sidebar — each template provides Claude with a specialized system prompt
2. **Enter your notes** — bullet points, rough ideas, or structured content
3. **Choose a tone** and click **Generate Draft**
4. **Refine** the output with follow-up instructions
5. **Export** as PDF or DOCX, or **save** as a draft to continue later

All exports and drafts are saved to `~/Documents/AI Writer Drafts/`.
