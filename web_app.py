#!/usr/bin/env python3
"""
Module: FastAPI web application for AI Document Writer
Version: 1.0.0
Development Iteration: v1

Project: AI Document Writer
Developer: Kent Benson
Created: 2026-01-31

Enhancement: Web-based UI replacing Tkinter — runs in browser, no X11 needed

Features:
- FastAPI + Jinja2 + htmx web interface
- Session-based password authentication
- Generate and refine documents via Claude API
- Save/load drafts, export PDF and DOCX
- 3-panel layout: templates | notes | document

UV ENVIRONMENT: Run with `uv run python web_app.py`

INSTALLATION:
uv add fastapi "uvicorn[standard]" jinja2 python-multipart
"""

import hmac
import logging
import socket
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from ai_writer import generate_draft, refine_text
from config import WEB_PASSWORD, WEB_PORT, WEB_SECRET_KEY
from draft_storage import list_drafts, load_draft, save_draft
from export_docx import export_to_docx
from export_pdf import export_to_pdf
from templates import TEMPLATES, TONE_OPTIONS, get_template_by_name

# ── Logging ──────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# ── App Setup ────────────────────────────────────────────
BASE_DIR = Path(__file__).parent

app = FastAPI(title="AI Document Writer")
app.add_middleware(SessionMiddleware, secret_key=WEB_SECRET_KEY)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

tpl = Jinja2Templates(directory=BASE_DIR / "templates")

# Thread pool for blocking API calls
_executor = ThreadPoolExecutor(max_workers=2)


# ── Auth Helpers ─────────────────────────────────────────

def is_logged_in(request: Request) -> bool:
    """Check if session is authenticated."""
    return request.session.get("authenticated") is True


def require_auth(request: Request) -> Optional[RedirectResponse]:
    """Return a redirect to /login if not authenticated, else None."""
    if not WEB_PASSWORD:
        # No password configured — allow access
        return None
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)
    return None


# ── Routes: Auth ─────────────────────────────────────────

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if not WEB_PASSWORD or is_logged_in(request):
        return RedirectResponse(url="/", status_code=303)
    return tpl.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, password: str = Form(...)):
    if hmac.compare_digest(password, WEB_PASSWORD):
        request.session["authenticated"] = True
        return RedirectResponse(url="/", status_code=303)
    return tpl.TemplateResponse("login.html", {"request": request, "error": "Incorrect password"})


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


# ── Routes: Main Page ────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    redirect = require_auth(request)
    if redirect:
        return redirect
    return tpl.TemplateResponse("index.html", {
        "request": request,
        "templates": TEMPLATES,
        "tones": TONE_OPTIONS,
        "selected_template": TEMPLATES[0].name,
    })


# ── Routes: Generate & Refine ────────────────────────────

@app.post("/generate", response_class=HTMLResponse)
async def generate(
    request: Request,
    template_name: str = Form(...),
    notes: str = Form(...),
    tone: str = Form("Professional"),
):
    redirect = require_auth(request)
    if redirect:
        return redirect

    template = get_template_by_name(template_name)

    import asyncio
    loop = asyncio.get_event_loop()
    text = await loop.run_in_executor(_executor, generate_draft, template, notes, tone)

    return tpl.TemplateResponse("fragments/document_result.html", {
        "request": request,
        "document_text": text,
        "error": None,
    })


@app.post("/refine", response_class=HTMLResponse)
async def refine(
    request: Request,
    current_text: str = Form(...),
    instruction: str = Form(...),
    template_name: str = Form("general"),
):
    redirect = require_auth(request)
    if redirect:
        return redirect

    import asyncio
    loop = asyncio.get_event_loop()
    text = await loop.run_in_executor(_executor, refine_text, current_text, instruction, template_name)

    return tpl.TemplateResponse("fragments/document_result.html", {
        "request": request,
        "document_text": text,
        "error": None,
    })


# ── Routes: Drafts ───────────────────────────────────────

@app.post("/save", response_class=HTMLResponse)
async def save(
    request: Request,
    title: str = Form(...),
    template_name: str = Form("general"),
    tone: str = Form("Professional"),
    notes: str = Form(""),
    document_text: str = Form(""),
):
    redirect = require_auth(request)
    if redirect:
        return redirect

    filepath = save_draft(title, template_name, tone, notes, document_text)
    if filepath:
        return HTMLResponse('<div class="alert alert-success">Draft saved.</div>')
    return HTMLResponse('<div class="alert alert-error">Failed to save draft.</div>')


@app.get("/drafts", response_class=HTMLResponse)
async def drafts(request: Request):
    redirect = require_auth(request)
    if redirect:
        return redirect

    all_drafts = list_drafts()
    return tpl.TemplateResponse("fragments/draft_list.html", {
        "request": request,
        "drafts": all_drafts,
    })


@app.post("/load", response_class=HTMLResponse)
async def load(request: Request, filepath: str = Form(...)):
    redirect = require_auth(request)
    if redirect:
        return redirect

    draft = load_draft(filepath)
    if not draft:
        return HTMLResponse('<div class="alert alert-error">Could not load draft.</div>')

    # Return the document text plus a script that restores the full state
    html = (
        f'<textarea id="document-text" oninput="updateWordCount()">{draft.document_text}</textarea>\n'
        f'<script>\n'
        f'loadDraftState({{\n'
        f'  template_name: "{draft.template_name}",\n'
        f'  tone: "{draft.tone}",\n'
        f'  notes: {_js_string(draft.notes)}\n'
        f'}});\n'
        f'</script>'
    )
    return HTMLResponse(html)


def _js_string(s: str) -> str:
    """Escape a Python string for safe embedding in a JS string literal."""
    escaped = (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("'", "\\'")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("<", "\\x3c")
        .replace(">", "\\x3e")
    )
    return f'"{escaped}"'


# ── Routes: Export ───────────────────────────────────────

@app.post("/export/pdf")
async def export_pdf_route(
    request: Request,
    text: str = Form(...),
    title: str = Form("Document"),
):
    redirect = require_auth(request)
    if redirect:
        return redirect

    if not text.strip():
        return HTMLResponse('<div class="alert alert-error">No text to export.</div>')

    filepath = export_to_pdf(text, title)
    if not filepath:
        return HTMLResponse('<div class="alert alert-error">PDF export failed.</div>')

    return FileResponse(
        filepath,
        media_type="application/pdf",
        filename=Path(filepath).name,
    )


@app.post("/export/docx")
async def export_docx_route(
    request: Request,
    text: str = Form(...),
    title: str = Form("Document"),
):
    redirect = require_auth(request)
    if redirect:
        return redirect

    if not text.strip():
        return HTMLResponse('<div class="alert alert-error">No text to export.</div>')

    filepath = export_to_docx(text, title)
    if not filepath:
        return HTMLResponse('<div class="alert alert-error">DOCX export failed.</div>')

    return FileResponse(
        filepath,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=Path(filepath).name,
    )


# ── Adaptive Port Detection ─────────────────────────────

def get_local_ip() -> str:
    """Get the LAN IP address of this machine."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def get_external_ip() -> Optional[str]:
    """Get public IP — checks GCP metadata first, then a public service."""
    import urllib.request

    # Try GCP metadata (instant, no external network call)
    try:
        req = urllib.request.Request(
            "http://metadata.google.internal/computeMetadata/v1/instance/"
            "network-interfaces/0/access-configs/0/external-ip",
            headers={"Metadata-Flavor": "Google"},
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            ip = resp.read().decode().strip()
            if ip:
                return ip
    except Exception:
        pass

    # Fallback: public IP service
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=3) as resp:
            return resp.read().decode().strip()
    except Exception:
        return None


def find_available_port(start_port: int = 8090, max_attempts: int = 100) -> int:
    """Find an available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"No available ports in range {start_port}-{start_port + max_attempts}")


# ── Entry Point ──────────────────────────────────────────

if __name__ == "__main__":
    port = find_available_port(WEB_PORT)
    if port != WEB_PORT:
        logger.info(f"Port {WEB_PORT} in use, using port {port} instead")

    local_ip = get_local_ip()
    external_ip = get_external_ip()
    logger.info(f"Starting AI Document Writer")
    logger.info(f"  Local:   http://127.0.0.1:{port}")
    logger.info(f"  LAN:     http://{local_ip}:{port}")
    if external_ip:
        logger.info(f"  Public:  http://{external_ip}:{port}")
    if WEB_PASSWORD:
        logger.info("Password authentication enabled")
    else:
        logger.info("No WEB_PASSWORD set — access is open (set WEB_PASSWORD in .env to enable auth)")

    uvicorn.run(app, host="0.0.0.0", port=port)
