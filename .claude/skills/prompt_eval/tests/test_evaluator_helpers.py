"""Tests for module-level helpers in evaluator.py."""
import os
from prompt_eval.evaluator import MODEL_MAP, render_prompt


def test_model_map_has_three_aliases():
    assert MODEL_MAP == {
        "haiku": "claude-haiku-4-5",
        "sonnet": "claude-sonnet-4-6",
        "opus": "claude-opus-4-7",
    }


def test_render_prompt_substitutes_placeholders():
    template = "Hello {name}, your goal is {goal}."
    result = render_prompt(template, {"name": "Alex", "goal": "marathon"})
    assert result == "Hello Alex, your goal is marathon."


def test_render_prompt_leaves_unknown_placeholders_intact():
    template = "Hi {name}, {undefined}"
    result = render_prompt(template, {"name": "Sam"})
    assert result == "Hi Sam, {undefined}"


def test_render_prompt_handles_escaped_braces():
    template = "Show {{literal}} and {var}."
    result = render_prompt(template, {"var": "x"})
    assert result == "Show {literal} and x."


def test_telemetry_opt_out_set_on_import():
    # importing the module should opt out
    import prompt_eval.evaluator  # noqa: F401
    assert os.environ.get("DEEPEVAL_TELEMETRY_OPT_OUT") == "1"
