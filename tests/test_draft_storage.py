"""Tests for draft_storage.py — file I/O with temporary directories."""

import json

import pytest

from draft_storage import Draft, save_draft, load_draft, list_drafts


@pytest.fixture
def saved_draft_path(tmp_drafts_dir):
    """Save a draft and return the file path."""
    path = save_draft(
        title="Test Draft",
        template_name="formal_letter",
        tone="Professional",
        notes="Some notes",
        document_text="Generated document text.",
    )
    return path


class TestSaveDraft:
    """Tests for save_draft()."""

    def test_creates_json_file(self, tmp_drafts_dir):
        path = save_draft("My Title", "memo", "Formal", "notes", "text body")
        assert path is not None
        assert path.endswith(".json")
        assert json.loads(open(path).read())

    def test_json_has_correct_structure(self, tmp_drafts_dir):
        path = save_draft("My Title", "memo", "Formal", "notes", "text body")
        data = json.loads(open(path).read())
        assert data["title"] == "My Title"
        assert data["template_name"] == "memo"
        assert data["tone"] == "Formal"
        assert data["notes"] == "notes"
        assert data["document_text"] == "text body"
        assert "saved_at" in data
        assert "filename" in data

    def test_sanitizes_special_chars_in_title(self, tmp_drafts_dir):
        path = save_draft("Hello! @World# $Test", "general", "Casual", "n", "t")
        filename = path.split("/")[-1]
        # Only alphanumeric, spaces, hyphens, underscores should remain
        assert "!" not in filename
        assert "@" not in filename
        assert "#" not in filename

    def test_sanitizes_long_titles(self, tmp_drafts_dir):
        long_title = "A" * 100
        path = save_draft(long_title, "general", "Casual", "n", "t")
        filename = path.split("/")[-1]
        # Title portion should be truncated (40 chars max + timestamp + .json)
        title_part = filename.split("_2")[0]  # Before timestamp
        assert len(title_part) <= 40

    def test_sanitizes_spaces_to_underscores(self, tmp_drafts_dir):
        path = save_draft("My Great Draft", "general", "Casual", "n", "t")
        filename = path.split("/")[-1]
        assert "My Great Draft" not in filename  # Spaces replaced
        assert "My_Great_Draft" in filename


class TestLoadDraft:
    """Tests for load_draft()."""

    def test_returns_valid_draft(self, tmp_drafts_dir, saved_draft_path):
        draft = load_draft(saved_draft_path)
        assert isinstance(draft, Draft)
        assert draft.title == "Test Draft"
        assert draft.template_name == "formal_letter"

    def test_returns_none_for_nonexistent_file(self, tmp_drafts_dir):
        result = load_draft("/nonexistent/path/file.json")
        assert result is None

    def test_returns_none_for_corrupted_json(self, tmp_drafts_dir):
        bad_file = tmp_drafts_dir / "bad.json"
        bad_file.write_text("not valid json {{{")
        result = load_draft(str(bad_file))
        assert result is None


class TestListDrafts:
    """Tests for list_drafts()."""

    def test_returns_empty_list_when_no_drafts(self, tmp_drafts_dir):
        assert list_drafts() == []

    def test_returns_drafts_sorted_newest_first(self, tmp_drafts_dir):
        import time

        save_draft("First", "general", "Casual", "n", "t")
        time.sleep(0.05)
        save_draft("Second", "memo", "Formal", "n", "t")

        drafts = list_drafts()
        assert len(drafts) == 2
        assert drafts[0]["title"] == "Second"
        assert drafts[1]["title"] == "First"

    def test_drafts_have_expected_keys(self, tmp_drafts_dir, saved_draft_path):
        drafts = list_drafts()
        assert len(drafts) == 1
        d = drafts[0]
        assert "title" in d
        assert "saved_at" in d
        assert "filepath" in d
        assert "template_name" in d

    def test_skips_corrupt_files(self, tmp_drafts_dir, saved_draft_path):
        bad_file = tmp_drafts_dir / "corrupt.json"
        bad_file.write_text("not json!")
        drafts = list_drafts()
        # Should still return the valid draft, skip the corrupt one
        assert len(drafts) == 1
        assert drafts[0]["title"] == "Test Draft"


class TestRoundTrip:
    """Save then load preserves all fields."""

    def test_round_trip(self, tmp_drafts_dir):
        path = save_draft(
            title="Round Trip Test",
            template_name="report",
            tone="Academic",
            notes="test notes here",
            document_text="Full document text content.",
        )
        draft = load_draft(path)
        assert draft.title == "Round Trip Test"
        assert draft.template_name == "report"
        assert draft.tone == "Academic"
        assert draft.notes == "test notes here"
        assert draft.document_text == "Full document text content."
        assert draft.saved_at  # Non-empty timestamp
