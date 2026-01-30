"""Tests for templates.py — pure data, no mocks needed."""

from templates import TEMPLATES, TONE_OPTIONS, DocumentTemplate, get_template_by_name


class TestGetTemplateByName:
    """Tests for get_template_by_name()."""

    def test_returns_correct_template_for_each_name(self):
        for template in TEMPLATES:
            result = get_template_by_name(template.name)
            assert result is template

    def test_returns_general_for_unknown_name(self):
        result = get_template_by_name("nonexistent_template")
        assert result.name == "general"

    def test_returns_general_for_empty_string(self):
        result = get_template_by_name("")
        assert result.name == "general"


class TestTemplates:
    """Tests for TEMPLATES list and DocumentTemplate fields."""

    def test_eight_templates_defined(self):
        assert len(TEMPLATES) == 8

    def test_all_templates_have_required_fields(self):
        for t in TEMPLATES:
            assert isinstance(t, DocumentTemplate)
            assert t.name, f"Template missing name"
            assert t.display_name, f"Template {t.name} missing display_name"
            assert t.system_prompt, f"Template {t.name} missing system_prompt"
            assert t.placeholder, f"Template {t.name} missing placeholder"
            assert t.description, f"Template {t.name} missing description"

    def test_template_names_are_unique(self):
        names = [t.name for t in TEMPLATES]
        assert len(names) == len(set(names))

    def test_general_template_is_last(self):
        assert TEMPLATES[-1].name == "general"


class TestToneOptions:
    """Tests for TONE_OPTIONS."""

    def test_six_tone_options(self):
        assert len(TONE_OPTIONS) == 6

    def test_all_tones_are_nonempty_strings(self):
        for tone in TONE_OPTIONS:
            assert isinstance(tone, str)
            assert len(tone) > 0
