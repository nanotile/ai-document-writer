"""Tests for ai_writer.py — API calls mocked via unittest.mock."""

from unittest.mock import patch, MagicMock

import pytest

from templates import get_template_by_name


@pytest.fixture
def mock_client():
    """Patch the Anthropic client in ai_writer module."""
    with patch("ai_writer.client") as mock:
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Generated document text.")]
        mock.messages.create.return_value = mock_response
        yield mock


@pytest.fixture
def mock_api_key():
    """Ensure ANTHROPIC_API_KEY is set so generate/refine don't short-circuit."""
    with patch("ai_writer.ANTHROPIC_API_KEY", "test-key-123"):
        yield


class TestGenerateDraft:
    """Tests for generate_draft()."""

    def test_calls_api_with_correct_system_prompt(self, mock_client, mock_api_key):
        from ai_writer import generate_draft

        template = get_template_by_name("formal_letter")
        generate_draft(template, "My notes", "Formal")

        call_kwargs = mock_client.messages.create.call_args
        system = call_kwargs.kwargs["system"]
        assert template.system_prompt in system

    def test_includes_tone_in_system_prompt(self, mock_client, mock_api_key):
        from ai_writer import generate_draft

        template = get_template_by_name("memo")
        generate_draft(template, "My notes", "Persuasive")

        call_kwargs = mock_client.messages.create.call_args
        system = call_kwargs.kwargs["system"]
        assert "Persuasive" in system

    def test_returns_generated_text(self, mock_client, mock_api_key):
        from ai_writer import generate_draft

        template = get_template_by_name("general")
        result = generate_draft(template, "Some notes")
        assert result == "Generated document text."

    def test_returns_error_for_empty_notes(self, mock_client, mock_api_key):
        from ai_writer import generate_draft

        template = get_template_by_name("general")
        result = generate_draft(template, "")
        assert "notes" in result.lower() or "enter" in result.lower()
        mock_client.messages.create.assert_not_called()

    def test_returns_error_for_whitespace_notes(self, mock_client, mock_api_key):
        from ai_writer import generate_draft

        template = get_template_by_name("general")
        result = generate_draft(template, "   \n  ")
        mock_client.messages.create.assert_not_called()

    def test_returns_error_on_api_exception(self, mock_client, mock_api_key):
        from ai_writer import generate_draft

        mock_client.messages.create.side_effect = Exception("API timeout")
        template = get_template_by_name("general")
        result = generate_draft(template, "Some notes")
        assert "error" in result.lower()

    def test_user_message_contains_notes(self, mock_client, mock_api_key):
        from ai_writer import generate_draft

        template = get_template_by_name("email_draft")
        generate_draft(template, "Follow up on project")

        call_kwargs = mock_client.messages.create.call_args
        messages = call_kwargs.kwargs["messages"]
        assert "Follow up on project" in messages[0]["content"]


class TestRefineText:
    """Tests for refine_text()."""

    def test_sends_text_and_instruction(self, mock_client, mock_api_key):
        from ai_writer import refine_text

        refine_text("Original text.", "Make it shorter")

        call_kwargs = mock_client.messages.create.call_args
        messages = call_kwargs.kwargs["messages"]
        user_msg = messages[0]["content"]
        assert "Original text." in user_msg
        assert "Make it shorter" in user_msg

    def test_returns_refined_text(self, mock_client, mock_api_key):
        from ai_writer import refine_text

        result = refine_text("Original text.", "Make it formal")
        assert result == "Generated document text."

    def test_returns_error_for_empty_text(self, mock_client, mock_api_key):
        from ai_writer import refine_text

        result = refine_text("", "Make it shorter")
        assert "no text" in result.lower() or "generate" in result.lower()
        mock_client.messages.create.assert_not_called()

    def test_returns_current_text_for_empty_instruction(self, mock_client, mock_api_key):
        from ai_writer import refine_text

        result = refine_text("Keep this text.", "")
        assert result == "Keep this text."
        mock_client.messages.create.assert_not_called()

    def test_returns_error_on_api_exception(self, mock_client, mock_api_key):
        from ai_writer import refine_text

        mock_client.messages.create.side_effect = Exception("Network error")
        result = refine_text("Some text.", "Fix it")
        assert "error" in result.lower()
