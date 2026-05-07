"""Unit tests for the langfuse_push module (all SDK calls mocked)."""
from unittest.mock import patch, MagicMock
import pytest

from prompt_eval import langfuse_push


def test_is_configured_true_when_all_three_env_vars_set(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    monkeypatch.setenv("LANGFUSE_HOST", "https://example")
    assert langfuse_push.is_configured() is True


def test_is_configured_false_when_any_env_var_missing(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    monkeypatch.setenv("LANGFUSE_HOST", "https://example")
    assert langfuse_push.is_configured() is False


def test_is_configured_false_when_env_var_empty(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    monkeypatch.setenv("LANGFUSE_HOST", "https://example")
    assert langfuse_push.is_configured() is False
