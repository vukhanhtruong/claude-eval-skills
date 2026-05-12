"""Tests for AgenticRunner class."""
from unittest.mock import MagicMock
import pytest
from prompt_eval.agentic_runner import AgenticRunner
from prompt_eval.tool_mocker import ToolMocker


def make_text_response(text: str) -> MagicMock:
    """Create mock response with end_turn."""
    response = MagicMock()
    response.stop_reason = "end_turn"
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = text
    response.content = [text_block]
    return response


def make_tool_use_response(tool_name: str, tool_id: str, arguments: dict) -> MagicMock:
    """Create mock response with tool_use."""
    response = MagicMock()
    response.stop_reason = "tool_use"
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = tool_name
    tool_block.id = tool_id
    tool_block.input = arguments
    response.content = [tool_block]
    return response


def test_run_returns_text_and_empty_log_when_no_tools_used():
    client = MagicMock()
    client.messages.create.return_value = make_text_response("Final answer")
    mocker = ToolMocker(client=None, task_context="test")
    tools = [{"name": "web_fetch", "description": "...", "input_schema": {}}]
    runner = AgenticRunner(client=client, model="claude-haiku-4-5", tools=tools, mocker=mocker)

    output, tool_log = runner.run("What is 2+2?", case_context={})

    assert output == "Final answer"
    assert tool_log == []


def test_run_handles_single_tool_call_with_case_context():
    client = MagicMock()
    client.messages.create.side_effect = [
        make_tool_use_response("web_fetch", "tool_123", {"url": "https://example.com"}),
        make_text_response("The page says hello"),
    ]
    mock_cache = {'web_fetch::{"url": "https://example.com"}': {"content": "<html>Hello</html>", "generated_by": "haiku"}}
    mocker = ToolMocker(client=None, task_context="test", cache=mock_cache)
    tools = [{"name": "web_fetch", "description": "Fetch", "input_schema": {}}]
    runner = AgenticRunner(client=client, model="claude-haiku-4-5", tools=tools, mocker=mocker)

    output, tool_log = runner.run("What does example.com say?", case_context={"scenario": "test"})

    assert output == "The page says hello"
    assert len(tool_log) == 1
    assert tool_log[0]["tool"] == "web_fetch"


def test_run_forces_tool_choice_on_first_turn_only():
    """First turn must pass tool_choice={'type': 'any'} so Claude is forced to call a tool
    instead of replying 'I can't access URLs'. Subsequent turns use default (auto) so Claude
    can use the tool result to produce the final answer."""
    client = MagicMock()
    client.messages.create.side_effect = [
        make_tool_use_response("web_fetch", "tool_123", {"url": "https://example.com"}),
        make_text_response("Summary based on fetched content"),
    ]
    mock_cache = {'web_fetch::{"url": "https://example.com"}': {"content": "<html>...</html>", "generated_by": "haiku"}}
    mocker = ToolMocker(client=None, task_context="test", cache=mock_cache)
    tools = [{"name": "web_fetch", "description": "Fetch", "input_schema": {}}]
    runner = AgenticRunner(client=client, model="claude-haiku-4-5", tools=tools, mocker=mocker)

    runner.run("Summarize https://example.com", case_context={})

    assert client.messages.create.call_count == 2
    first_call_kwargs = client.messages.create.call_args_list[0].kwargs
    second_call_kwargs = client.messages.create.call_args_list[1].kwargs

    assert first_call_kwargs.get("tool_choice") == {"type": "any"}, \
        "First turn must force tool use"
    assert "tool_choice" not in second_call_kwargs, \
        "Subsequent turns must use default (auto) so Claude can finalize"


def test_run_respects_max_turns_limit():
    client = MagicMock()
    client.messages.create.return_value = make_tool_use_response("web_fetch", "tool_1", {"url": "https://loop.com"})
    mock_cache = {'web_fetch::{"url": "https://loop.com"}': {"content": "looping", "generated_by": "haiku"}}
    mocker = ToolMocker(client=None, task_context="test", cache=mock_cache)
    tools = [{"name": "web_fetch", "description": "Fetch", "input_schema": {}}]
    runner = AgenticRunner(client=client, model="claude-haiku-4-5", tools=tools, mocker=mocker, max_turns=3)

    output, tool_log = runner.run("Loop forever", case_context={})

    assert client.messages.create.call_count == 3
    assert len(tool_log) == 3
