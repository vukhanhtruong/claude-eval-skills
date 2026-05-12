"""Tests for tool_schemas module."""
import json
import pytest
from unittest.mock import patch, MagicMock
from prompt_eval.tool_schemas import (
    get_builtin_schema,
    is_builtin_tool,
    is_safe_builtin,
    is_risky_builtin,
    BUILTIN_TOOLS,
    SAFE_BUILTIN_TOOLS,
    RISKY_BUILTIN_TOOLS,
)
from prompt_eval.evaluator import MODEL_MAP


def test_get_builtin_schema_returns_web_fetch():
    schema = get_builtin_schema("web_fetch")
    assert schema is not None
    assert schema["name"] == "web_fetch"
    assert "input_schema" in schema
    assert schema["input_schema"]["properties"]["url"]["type"] == "string"


def test_get_builtin_schema_returns_none_for_unknown():
    schema = get_builtin_schema("unknown_tool")
    assert schema is None


def test_builtin_tools_contains_expected_tools():
    expected = {"web_fetch", "web_search", "read_file", "bash"}
    assert set(BUILTIN_TOOLS.keys()) == expected


def test_safe_builtin_tools():
    assert SAFE_BUILTIN_TOOLS == {"web_fetch", "web_search"}


def test_risky_builtin_tools():
    assert RISKY_BUILTIN_TOOLS == {"read_file", "bash"}


def test_is_builtin_tool():
    assert is_builtin_tool("web_fetch") is True
    assert is_builtin_tool("bash") is True
    assert is_builtin_tool("custom_tool") is False


def test_is_safe_builtin():
    assert is_safe_builtin("web_fetch") is True
    assert is_safe_builtin("web_search") is True
    assert is_safe_builtin("bash") is False
    assert is_safe_builtin("read_file") is False
    assert is_safe_builtin("custom_tool") is False


def test_is_risky_builtin():
    assert is_risky_builtin("bash") is True
    assert is_risky_builtin("read_file") is True
    assert is_risky_builtin("web_fetch") is False
    assert is_risky_builtin("web_search") is False
    assert is_risky_builtin("custom_tool") is False


@patch("prompt_eval.tool_schemas.Anthropic")
def test_draft_custom_schema_returns_valid_schema(anthropic_cls):
    from prompt_eval.tool_schemas import draft_custom_schema

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps({
        "name": "mcp__jira__get_issue",
        "description": "Fetch a Jira issue by key",
        "input_schema": {
            "type": "object",
            "properties": {
                "issue_key": {"type": "string", "description": "Jira issue key"}
            },
            "required": ["issue_key"],
        },
    }))]
    anthropic_cls.return_value.messages.create.return_value = mock_response

    schema = draft_custom_schema(
        tool_name="mcp__jira__get_issue",
        context="Summarize Jira tickets for sprint planning",
    )

    assert schema["name"] == "mcp__jira__get_issue"
    assert "input_schema" in schema
    assert "issue_key" in schema["input_schema"]["properties"]
    # Verify MODEL_MAP is used, not hardcoded string
    call_kwargs = anthropic_cls.return_value.messages.create.call_args.kwargs
    assert call_kwargs["model"] == MODEL_MAP["haiku"]
