#!/usr/bin/env python3
"""
Module: Main Tkinter application for AI Document Writer
Version: 1.0.0
Development Iteration: v1

Project: AI Document Writer
Developer: Kent Benson
Created: 2026-01-29

Enhancement: Initial implementation

Features:
- Three-panel layout: templates, editor, actions
- Generate drafts from notes using Claude AI
- Refine text with custom instructions
- Export to PDF and Word
- Save/load drafts
- Background threading for API calls
- Large fonts for accessibility

UV ENVIRONMENT: Run with `uv run python main_app.py`

INSTALLATION:
uv add anthropic fpdf2 python-docx python-dotenv pydantic
"""

import threading
import tkinter as tk
import tkinter.simpledialog
from tkinter import ttk, messagebox, filedialog, scrolledtext
from queue import Queue, Empty

from config import (
    WINDOW_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT,
    WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_LARGE, FONT_SIZE_HEADING,
    FONT_SIZE_SMALL,
    BG_COLOR, SIDEBAR_BG, BUTTON_BG, BUTTON_FG, BUTTON_ACTIVE_BG,
    SELECTED_BG, STATUS_BG, TEXT_BG, HEADING_COLOR,
    BUTTON_WIDTH, BUTTON_HEIGHT, BUTTON_PADX, BUTTON_PADY,
    ANTHROPIC_API_KEY,
)
from templates import TEMPLATES, TONE_OPTIONS
from ai_writer import generate_draft, refine_text
from export_pdf import export_to_pdf
from export_docx import export_to_docx
from draft_storage import save_draft, load_draft, list_drafts


class DocumentWriterApp:
    """Main application window for AI Document Writer."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.root.configure(bg=BG_COLOR)

        # State
        self.selected_template_idx = 0
        self.result_queue = Queue()
        self.is_busy = False

        # Build UI
        self._build_ui()

        # Select first template
        self._select_template(0)

        # Poll for background results
        self.root.after(100, self._poll_queue)

    def _build_ui(self):
        """Build the three-panel layout."""

        # ── Top title bar ──
        title_frame = tk.Frame(self.root, bg=HEADING_COLOR, height=50)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        tk.Label(
            title_frame, text="AI Document Writer",
            font=(FONT_FAMILY, FONT_SIZE_HEADING, "bold"),
            bg=HEADING_COLOR, fg="white",
        ).pack(side=tk.LEFT, padx=15, pady=8)

        # ── Main content area ──
        main_frame = tk.Frame(self.root, bg=BG_COLOR)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ── Left sidebar: Templates ──
        self._build_sidebar(main_frame)

        # ── Center: Editor area ──
        self._build_editor(main_frame)

        # ── Right sidebar: Actions ──
        self._build_actions(main_frame)

        # ── Status bar ──
        self._build_status_bar()

    def _build_sidebar(self, parent):
        """Build the template selection sidebar."""
        sidebar = tk.Frame(parent, bg=SIDEBAR_BG, width=160)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        sidebar.pack_propagate(False)

        tk.Label(
            sidebar, text="Templates",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            bg=SIDEBAR_BG,
        ).pack(pady=(10, 5))

        self.template_buttons = []
        for i, template in enumerate(TEMPLATES):
            btn = tk.Button(
                sidebar,
                text=template.display_name,
                font=(FONT_FAMILY, FONT_SIZE_SMALL),
                width=16,
                height=1,
                relief=tk.FLAT,
                bg=SIDEBAR_BG,
                activebackground=SELECTED_BG,
                anchor="w",
                padx=10,
                command=lambda idx=i: self._select_template(idx),
            )
            btn.pack(fill=tk.X, padx=5, pady=2)
            self.template_buttons.append(btn)

    def _build_editor(self, parent):
        """Build the center editor with notes input and document output."""
        editor_frame = tk.Frame(parent, bg=BG_COLOR)
        editor_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        # ── Notes input ──
        notes_label = tk.Label(
            editor_frame, text="YOUR NOTES / BULLET POINTS:",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            bg=BG_COLOR, anchor="w",
        )
        notes_label.pack(fill=tk.X, pady=(0, 3))

        self.notes_text = scrolledtext.ScrolledText(
            editor_frame,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            height=8,
            wrap=tk.WORD,
            bg=TEXT_BG,
            relief=tk.SOLID,
            borderwidth=1,
        )
        self.notes_text.pack(fill=tk.X, pady=(0, 10))

        # ── Generated document output ──
        doc_label = tk.Label(
            editor_frame, text="GENERATED DOCUMENT:",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            bg=BG_COLOR, anchor="w",
        )
        doc_label.pack(fill=tk.X, pady=(0, 3))

        self.doc_text = scrolledtext.ScrolledText(
            editor_frame,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            wrap=tk.WORD,
            bg=TEXT_BG,
            relief=tk.SOLID,
            borderwidth=1,
        )
        self.doc_text.pack(fill=tk.BOTH, expand=True)

    def _build_actions(self, parent):
        """Build the right-side action panel."""
        actions = tk.Frame(parent, bg=BG_COLOR, width=180)
        actions.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        actions.pack_propagate(False)

        # Generate button
        self.generate_btn = tk.Button(
            actions, text="Generate\nDraft",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            width=BUTTON_WIDTH, height=BUTTON_HEIGHT,
            bg=BUTTON_BG, fg=BUTTON_FG,
            activebackground=BUTTON_ACTIVE_BG, activeforeground=BUTTON_FG,
            command=self._on_generate,
        )
        self.generate_btn.pack(pady=(10, 5), padx=BUTTON_PADX)

        # Refine section
        tk.Label(
            actions, text="Refine:",
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            bg=BG_COLOR, anchor="w",
        ).pack(fill=tk.X, padx=BUTTON_PADX, pady=(15, 2))

        self.refine_entry = tk.Entry(
            actions,
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            width=18,
        )
        self.refine_entry.pack(padx=BUTTON_PADX, pady=(0, 3))
        self.refine_entry.insert(0, "make it shorter")
        self.refine_entry.bind("<Return>", lambda e: self._on_refine())

        self.refine_btn = tk.Button(
            actions, text="Refine",
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            width=BUTTON_WIDTH, height=1,
            bg="#059669", fg=BUTTON_FG,
            activebackground="#047857", activeforeground=BUTTON_FG,
            command=self._on_refine,
        )
        self.refine_btn.pack(padx=BUTTON_PADX, pady=(0, 5))

        # Separator
        ttk.Separator(actions, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=10)

        # Tone selector
        tk.Label(
            actions, text="Tone:",
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            bg=BG_COLOR, anchor="w",
        ).pack(fill=tk.X, padx=BUTTON_PADX, pady=(0, 2))

        self.tone_var = tk.StringVar(value="Professional")
        self.tone_combo = ttk.Combobox(
            actions,
            textvariable=self.tone_var,
            values=TONE_OPTIONS,
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            width=16,
            state="readonly",
        )
        self.tone_combo.pack(padx=BUTTON_PADX, pady=(0, 10))

        # Separator
        ttk.Separator(actions, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=5)

        # Save/Load/Export buttons
        for text, cmd, color in [
            ("Save Draft", self._on_save, "#6B7280"),
            ("Load Draft", self._on_load, "#6B7280"),
            ("Export PDF", self._on_export_pdf, "#7C3AED"),
            ("Export Word", self._on_export_docx, "#7C3AED"),
        ]:
            tk.Button(
                actions, text=text,
                font=(FONT_FAMILY, FONT_SIZE_SMALL),
                width=BUTTON_WIDTH, height=1,
                bg=color, fg=BUTTON_FG,
                activebackground=color, activeforeground=BUTTON_FG,
                command=cmd,
            ).pack(padx=BUTTON_PADX, pady=3)

    def _build_status_bar(self):
        """Build the bottom status bar."""
        status_frame = tk.Frame(self.root, bg=STATUS_BG, height=30)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        status_frame.pack_propagate(False)

        self.status_label = tk.Label(
            status_frame, text="Ready",
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            bg=STATUS_BG, anchor="w",
        )
        self.status_label.pack(side=tk.LEFT, padx=10)

        self.word_count_label = tk.Label(
            status_frame, text="Words: 0",
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            bg=STATUS_BG, anchor="e",
        )
        self.word_count_label.pack(side=tk.RIGHT, padx=10)

        # Update word count when document text changes
        self.doc_text.bind("<<Modified>>", self._on_text_modified)
        self.doc_text.bind("<KeyRelease>", lambda e: self._update_word_count())

    # ── Template Selection ──

    def _select_template(self, idx: int):
        """Highlight the selected template and update placeholder text."""
        self.selected_template_idx = idx
        template = TEMPLATES[idx]

        # Update button highlights
        for i, btn in enumerate(self.template_buttons):
            if i == idx:
                btn.configure(bg=SELECTED_BG, relief=tk.SUNKEN)
            else:
                btn.configure(bg=SIDEBAR_BG, relief=tk.FLAT)

        # Update notes placeholder if notes area is empty
        current_notes = self.notes_text.get("1.0", tk.END).strip()
        if not current_notes:
            self.notes_text.delete("1.0", tk.END)
            self.notes_text.insert("1.0", template.placeholder)
            self.notes_text.configure(fg="#999999")

        self._set_status(f"Template: {template.display_name}")

    # ── Notes placeholder behavior ──

    def _get_notes(self) -> str:
        """Get notes text, ignoring placeholder."""
        text = self.notes_text.get("1.0", tk.END).strip()
        # Check if it's still the placeholder
        template = TEMPLATES[self.selected_template_idx]
        if text == template.placeholder:
            return ""
        return text

    # ── Generate Draft ──

    def _on_generate(self):
        """Generate a document draft in a background thread."""
        if self.is_busy:
            return

        notes = self._get_notes()
        if not notes:
            messagebox.showinfo("No Notes", "Please enter some notes or bullet points first.")
            return

        # Clear placeholder styling
        self.notes_text.configure(fg="black")

        template = TEMPLATES[self.selected_template_idx]
        tone = self.tone_var.get()

        self._set_busy(True, f"Generating {template.display_name}...")

        def _worker():
            result = generate_draft(template, notes, tone)
            self.result_queue.put(("draft", result))

        threading.Thread(target=_worker, daemon=True).start()

    # ── Refine Text ──

    def _on_refine(self):
        """Refine the current document text."""
        if self.is_busy:
            return

        current_text = self.doc_text.get("1.0", tk.END).strip()
        if not current_text:
            messagebox.showinfo("No Document", "Generate a draft first before refining.")
            return

        instruction = self.refine_entry.get().strip()
        if not instruction:
            messagebox.showinfo("No Instruction", "Enter a refinement instruction (e.g., 'make it shorter').")
            return

        template = TEMPLATES[self.selected_template_idx]
        self._set_busy(True, f"Refining document...")

        def _worker():
            result = refine_text(current_text, instruction, template.name)
            self.result_queue.put(("draft", result))

        threading.Thread(target=_worker, daemon=True).start()

    # ── Save / Load ──

    def _on_save(self):
        """Save the current draft."""
        doc_text = self.doc_text.get("1.0", tk.END).strip()
        notes = self._get_notes()

        if not doc_text and not notes:
            messagebox.showinfo("Nothing to Save", "Enter notes or generate a document first.")
            return

        template = TEMPLATES[self.selected_template_idx]

        # Ask for a title
        title = tk.simpledialog.askstring(
            "Save Draft",
            "Enter a title for this draft:",
            initialvalue=template.display_name,
            parent=self.root,
        )
        if not title:
            return

        filepath = save_draft(
            title=title,
            template_name=template.name,
            tone=self.tone_var.get(),
            notes=notes,
            document_text=doc_text,
        )

        if filepath:
            self._set_status(f"Draft saved: {filepath}")
            messagebox.showinfo("Saved", f"Draft saved to:\n{filepath}")
        else:
            messagebox.showerror("Error", "Failed to save draft.")

    def _on_load(self):
        """Load a saved draft."""
        drafts = list_drafts()
        if not drafts:
            messagebox.showinfo("No Drafts", "No saved drafts found.")
            return

        # Show a selection dialog
        load_win = tk.Toplevel(self.root)
        load_win.title("Load Draft")
        load_win.geometry("500x400")
        load_win.transient(self.root)
        load_win.grab_set()

        tk.Label(
            load_win, text="Select a draft to load:",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
        ).pack(pady=10)

        listbox = tk.Listbox(
            load_win,
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            height=15,
            selectmode=tk.SINGLE,
        )
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        for d in drafts:
            saved_at = d["saved_at"][:19].replace("T", " ") if d["saved_at"] else "Unknown"
            listbox.insert(tk.END, f"{d['title']}  ({saved_at})")

        def _do_load():
            sel = listbox.curselection()
            if not sel:
                return
            draft_info = drafts[sel[0]]
            draft = load_draft(draft_info["filepath"])
            if draft:
                # Restore template
                for i, t in enumerate(TEMPLATES):
                    if t.name == draft.template_name:
                        self._select_template(i)
                        break

                # Restore tone
                self.tone_var.set(draft.tone)

                # Restore notes
                self.notes_text.delete("1.0", tk.END)
                self.notes_text.insert("1.0", draft.notes)
                self.notes_text.configure(fg="black")

                # Restore document
                self.doc_text.delete("1.0", tk.END)
                self.doc_text.insert("1.0", draft.document_text)
                self._update_word_count()
                self._set_status(f"Loaded: {draft.title}")

            load_win.destroy()

        tk.Button(
            load_win, text="Load Selected",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            width=15, height=1,
            bg=BUTTON_BG, fg=BUTTON_FG,
            command=_do_load,
        ).pack(pady=10)

    # ── Export ──

    def _on_export_pdf(self):
        """Export the document to PDF."""
        doc_text = self.doc_text.get("1.0", tk.END).strip()
        if not doc_text:
            messagebox.showinfo("No Document", "Generate a document first.")
            return

        template = TEMPLATES[self.selected_template_idx]
        filepath = export_to_pdf(doc_text, title=template.display_name)

        if filepath:
            self._set_status(f"PDF exported: {filepath}")
            messagebox.showinfo("PDF Exported", f"Saved to:\n{filepath}")
        else:
            messagebox.showerror("Error", "Failed to export PDF.")

    def _on_export_docx(self):
        """Export the document to Word (.docx)."""
        doc_text = self.doc_text.get("1.0", tk.END).strip()
        if not doc_text:
            messagebox.showinfo("No Document", "Generate a document first.")
            return

        template = TEMPLATES[self.selected_template_idx]
        filepath = export_to_docx(doc_text, title=template.display_name)

        if filepath:
            self._set_status(f"Word exported: {filepath}")
            messagebox.showinfo("Word Exported", f"Saved to:\n{filepath}")
        else:
            messagebox.showerror("Error", "Failed to export Word document.")

    # ── Background Task Polling ──

    def _poll_queue(self):
        """Check for results from background threads."""
        try:
            while True:
                msg_type, data = self.result_queue.get_nowait()
                if msg_type == "draft":
                    self.doc_text.delete("1.0", tk.END)
                    self.doc_text.insert("1.0", data)
                    self._update_word_count()
                    self._set_busy(False, "Document ready")
        except Empty:
            pass
        self.root.after(100, self._poll_queue)

    # ── UI Helpers ──

    def _set_busy(self, busy: bool, message: str = ""):
        """Set the busy state and update UI."""
        self.is_busy = busy
        if busy:
            self.generate_btn.configure(state=tk.DISABLED)
            self.refine_btn.configure(state=tk.DISABLED)
            self._set_status(message or "Working...")
        else:
            self.generate_btn.configure(state=tk.NORMAL)
            self.refine_btn.configure(state=tk.NORMAL)
            self._set_status(message or "Ready")

    def _set_status(self, text: str):
        """Update the status bar text."""
        self.status_label.configure(text=text)

    def _update_word_count(self):
        """Update the word count display."""
        text = self.doc_text.get("1.0", tk.END).strip()
        words = len(text.split()) if text else 0
        self.word_count_label.configure(text=f"Words: {words}")

    def _on_text_modified(self, event=None):
        """Handle text modification events."""
        self.doc_text.edit_modified(False)
        self._update_word_count()

    def run(self):
        """Start the application."""
        if not ANTHROPIC_API_KEY:
            messagebox.showwarning(
                "API Key Missing",
                "ANTHROPIC_API_KEY not found in .env file.\n\n"
                "Create a .env file in the app directory with:\n"
                "ANTHROPIC_API_KEY=your_key_here"
            )
        self.root.mainloop()


def main():
    """Entry point."""
    app = DocumentWriterApp()
    app.run()


if __name__ == "__main__":
    main()
