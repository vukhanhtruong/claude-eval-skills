# tests/test_tool_mocker.py
"""Tests for ToolMocker class."""
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, MagicMock
import pytest
from prompt_eval.tool_mocker import ToolMocker


def test_cache_key_is_deterministic():
    mocker = ToolMocker(client=None, task_context="test")
    key1 = mocker._cache_key("web_fetch", {"url": "https://example.com"})
    key2 = mocker._cache_key("web_fetch", {"url": "https://example.com"})
    assert key1 == key2
    assert key1 == 'web_fetch::{"url": "https://example.com"}'


def test_cache_key_sorts_arguments():
    mocker = ToolMocker(client=None, task_context="test")
    key1 = mocker._cache_key("tool", {"b": 2, "a": 1})
    key2 = mocker._cache_key("tool", {"a": 1, "b": 2})
    assert key1 == key2
    assert key1 == 'tool::{"a": 1, "b": 2}'


def test_get_or_generate_returns_cached_value():
    existing_cache = {
        'web_fetch::{"url": "https://example.com"}': {
            "content": "cached content",
            "generated_by": "haiku",
        }
    }
    mocker = ToolMocker(client=None, task_context="test", cache=existing_cache)
    result = mocker.get_or_generate("web_fetch", {"url": "https://example.com"}, case_context={"scenario": "test"})
    assert result == "cached content"


def test_get_or_generate_includes_case_context_in_generation():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="<html>News about climate</html>")]
    client = MagicMock()
    client.messages.create.return_value = mock_response

    mocker = ToolMocker(client=client, task_context="Summarize articles")
    case_context = {"scenario": "Climate change news summary", "prompt_inputs": {"topic": "climate"}}
    result = mocker.get_or_generate("web_fetch", {"url": "https://news.com"}, case_context=case_context)

    assert result == "<html>News about climate</html>"
    call_kwargs = client.messages.create.call_args.kwargs
    prompt_content = call_kwargs["messages"][0]["content"]
    assert "Climate change news summary" in prompt_content
    assert "climate" in prompt_content
    assert 'web_fetch::{"url": "https://news.com"}' in mocker.cache


def test_concurrent_requests_for_same_key_generate_once():
    """Verify per-key locking prevents duplicate generation."""
    generation_count = {"count": 0}

    def slow_generate(*args, **kwargs):
        generation_count["count"] += 1
        time.sleep(0.1)
        response = MagicMock()
        response.content = [MagicMock(text=f"mock_{generation_count['count']}")]
        return response

    client = MagicMock()
    client.messages.create.side_effect = slow_generate
    mocker = ToolMocker(client=client, task_context="test")

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(mocker.get_or_generate, "web_fetch", {"url": "https://same.com"}, {"scenario": f"worker_{i}"})
            for i in range(3)
        ]
        results = [f.result() for f in futures]

    assert all(r == results[0] for r in results)
    assert generation_count["count"] == 1
