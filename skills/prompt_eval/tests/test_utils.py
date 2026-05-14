"""Tests for shared utilities."""
import pytest
from prompt_eval._utils import strip_code_fence


def test_strip_code_fence_removes_json_fence():
    text = '```json\n{"key": "value"}\n```'
    assert strip_code_fence(text) == '{"key": "value"}'


def test_strip_code_fence_handles_no_fence():
    text = '{"key": "value"}'
    assert strip_code_fence(text) == '{"key": "value"}'


def test_strip_code_fence_handles_plain_fence():
    text = '```\nsome text\n```'
    assert strip_code_fence(text) == 'some text'


def test_strip_code_fence_strips_whitespace():
    text = '  \n```json\n{"a": 1}\n```\n  '
    assert strip_code_fence(text) == '{"a": 1}'
