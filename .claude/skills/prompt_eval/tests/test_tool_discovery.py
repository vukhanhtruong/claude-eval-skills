"""Tests for tool discovery module."""
import json
from unittest.mock import MagicMock, patch
import pytest
from prompt_eval.tool_discovery import detect_tool_needs, classify_detected_tools
from prompt_eval.evaluator import MODEL_MAP


@patch("prompt_eval.tool_discovery.Anthropic")
def test_detect_tool_needs_finds_web_fetch(anthropic_cls):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='["web_fetch"]')]
    anthropic_cls.return_value.messages.create.return_value = mock_response

    tools = detect_tool_needs("I would need to fetch the content from that URL", "Summarize web articles")
    assert tools == ["web_fetch"]
    call_kwargs = anthropic_cls.return_value.messages.create.call_args.kwargs
    assert call_kwargs["model"] == MODEL_MAP["haiku"]


@patch("prompt_eval.tool_discovery.Anthropic")
def test_detect_tool_needs_returns_empty_when_no_tools_needed(anthropic_cls):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='[]')]
    anthropic_cls.return_value.messages.create.return_value = mock_response

    tools = detect_tool_needs("The answer is 42.", "Answer math questions")
    assert tools == []


def test_classify_detected_tools_separates_builtin_and_custom():
    detected = ["web_fetch", "mcp__jira__get_issue", "web_search", "custom_tool"]
    safe, risky, custom = classify_detected_tools(detected)
    assert set(safe) == {"web_fetch", "web_search"}
    assert risky == []
    assert set(custom) == {"mcp__jira__get_issue", "custom_tool"}


def test_classify_detected_tools_identifies_risky_builtins():
    detected = ["web_fetch", "bash", "read_file"]
    safe, risky, custom = classify_detected_tools(detected)
    assert safe == ["web_fetch"]
    assert set(risky) == {"bash", "read_file"}
    assert custom == []
