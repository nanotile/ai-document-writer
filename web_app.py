#!/usr/bin/env python3
"""
Module: FastAPI web application for AI Document Writer
Version: 1.1.0
Development Iteration: v2

Project: AI Document Writer
Developer: Kent Benson
Created: 2026-01-31

Enhancement: Security hardening (rate limiting, input validation, error handling),
             draft deletion, session timeout

Features:
- FastAPI + Jinja2 + htmx web interface
- Session-based password authentication with inactivity timeout
- Generate and refine documents via Claude API
- Save/load/delete drafts, export PDF and DOCX
- 3-panel layout: templates | notes | document
- Rate limiting on all POST/DELETE routes (10/min per IP)
- Input length validation on all user-submitted fields

UV ENVIRONMENT: Run with `uv run python web_app.py`

INSTALLATION:
uv add fastapi "uvicorn[standard]" jinja2 python-multipart slowapi
"""

import hmac
import logging
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.sessions import SessionMiddleware

from ai_writer import generate_draft, refine_text
from config import DRAFTS_DIR, WEB_PASSWORD, WEB_PORT, WEB_SECRET_KEY, WEB_SESSION_TIMEOUT
from draft_storage import delete_draft, list_drafts, load_draft, save_draft
from export_docx import export_to_docx
from export_pdf import export_to_pdf
from templates import TEMPLATES, TONE_OPTIONS, get_template_by_name

# ── Logging ──────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Rate Limiter ─────────────────────────────────────────


def _get_real_ip(request: Request) -> str:
    """Get real client IP behind Cloudflare Tunnel (X-Forwarded-For)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=_get_real_ip)

# ── App Setup ────────────────────────────────────────────
BASE_DIR = Path(__file__).parent

app = FastAPI(
    title="AI Document Writer",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.state.limiter = limiter
app.add_middleware(SessionMiddleware, secret_key=WEB_SECRET_KEY)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

tpl = Jinja2Templates(directory=BASE_DIR / "templates")

# Thread pool for blocking API calls
_executor = ThreadPoolExecutor(max_workers=2)


# ── Exception Handlers ───────────────────────────────────

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred"},
    )


# ── Input Validation ─────────────────────────────────────

def validate_length(value: str, field_name: str, max_len: int) -> Optional[HTMLResponse]:
    """Return an error HTMLResponse if value exceeds max_len, else None."""
    if len(value) > max_len:
        return HTMLResponse(
            f'<div class="alert alert-error">{field_name} exceeds maximum length of {max_len} characters.</div>',
            status_code=400,
        )
    return None


# ── Auth Helpers ─────────────────────────────────────────

def is_logged_in(request: Request) -> bool:
    """Check if session is authenticated."""
    return request.session.get("authenticated") is True


def require_auth(request: Request) -> Optional[RedirectResponse]:
    """Return a redirect to /login if not authenticated or session expired, else None."""
    if not WEB_PASSWORD:
        # No password configured — allow access
        return None
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=303)
    # Check session timeout
    last_active = request.session.get("last_active", 0)
    if time.time() - last_active > WEB_SESSION_TIMEOUT:
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)
    # Sliding window — update timestamp on every authenticated request
    request.session["last_active"] = time.time()
    return None


# ── Routes: Health ───────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


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
        request.session["last_active"] = time.time()
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
@limiter.limit("10/minute")
async def generate(
    request: Request,
    template_name: str = Form(...),
    notes: str = Form(...),
    tone: str = Form("Professional"),
):
    redirect = require_auth(request)
    if redirect:
        return redirect

    for err in [
        validate_length(template_name, "Template name", 200),
        validate_length(notes, "Notes", 10_000),
        validate_length(tone, "Tone", 200),
    ]:
        if err:
            return err

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
@limiter.limit("10/minute")
async def refine(
    request: Request,
    current_text: str = Form(...),
    instruction: str = Form(...),
    template_name: str = Form("general"),
):
    redirect = require_auth(request)
    if redirect:
        return redirect

    for err in [
        validate_length(current_text, "Document text", 10_000),
        validate_length(instruction, "Instruction", 2_000),
        validate_length(template_name, "Template name", 200),
    ]:
        if err:
            return err

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
@limiter.limit("10/minute")
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

    for err in [
        validate_length(title, "Title", 200),
        validate_length(template_name, "Template name", 200),
        validate_length(tone, "Tone", 200),
        validate_length(notes, "Notes", 10_000),
        validate_length(document_text, "Document text", 10_000),
    ]:
        if err:
            return err

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


@app.delete("/drafts/{filename}", response_class=HTMLResponse)
@limiter.limit("10/minute")
async def delete_draft_route(request: Request, filename: str):
    redirect = require_auth(request)
    if redirect:
        return redirect

    if not delete_draft(filename):
        return HTMLResponse('<div class="alert alert-error">Could not delete draft.</div>', status_code=400)

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
# POST generates the file and redirects to a GET download URL.
# Browsers block file downloads from POST on insecure (HTTP) origins,
# but allow them from GET requests.

@app.post("/export/pdf")
@limiter.limit("10/minute")
async def export_pdf_route(
    request: Request,
    text: str = Form(...),
    title: str = Form("Document"),
):
    redirect = require_auth(request)
    if redirect:
        return redirect

    for err in [
        validate_length(text, "Document text", 10_000),
        validate_length(title, "Title", 200),
    ]:
        if err:
            return err

    if not text.strip():
        return HTMLResponse('<div class="alert alert-error">No text to export.</div>')

    filepath = export_to_pdf(text, title)
    if not filepath:
        return HTMLResponse('<div class="alert alert-error">PDF export failed.</div>')

    filename = Path(filepath).name
    return RedirectResponse(url=f"/download/{filename}", status_code=303)


@app.post("/export/docx")
@limiter.limit("10/minute")
async def export_docx_route(
    request: Request,
    text: str = Form(...),
    title: str = Form("Document"),
):
    redirect = require_auth(request)
    if redirect:
        return redirect

    for err in [
        validate_length(text, "Document text", 10_000),
        validate_length(title, "Title", 200),
    ]:
        if err:
            return err

    if not text.strip():
        return HTMLResponse('<div class="alert alert-error">No text to export.</div>')

    filepath = export_to_docx(text, title)
    if not filepath:
        return HTMLResponse('<div class="alert alert-error">DOCX export failed.</div>')

    filename = Path(filepath).name
    return RedirectResponse(url=f"/download/{filename}", status_code=303)


@app.get("/download/{filename}")
async def download_file(request: Request, filename: str):
    redirect = require_auth(request)
    if redirect:
        return redirect

    # Only serve files from the drafts directory (prevent path traversal)
    safe_name = Path(filename).name
    filepath = DRAFTS_DIR / safe_name
    if not filepath.exists():
        return HTMLResponse('<div class="alert alert-error">File not found.</div>', status_code=404)

    suffix = filepath.suffix.lower()
    if suffix == ".pdf":
        media_type = "application/pdf"
    elif suffix == ".docx":
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        media_type = "application/octet-stream"

    return FileResponse(filepath, media_type=media_type, filename=safe_name)


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
    logger.info(f"Session timeout: {WEB_SESSION_TIMEOUT}s")

    uvicorn.run(app, host="0.0.0.0", port=port)
