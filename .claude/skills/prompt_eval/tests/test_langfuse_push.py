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


def test_get_client_returns_none_when_not_configured(monkeypatch):
    for k in langfuse_push.REQUIRED_ENV:
        monkeypatch.delenv(k, raising=False)
    assert langfuse_push.get_client() is None


def test_get_client_returns_langfuse_instance_when_configured(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    monkeypatch.setenv("LANGFUSE_HOST", "https://example")
    sentinel = MagicMock(name="LangfuseClient")
    with patch("prompt_eval.langfuse_push.Langfuse", return_value=sentinel) as ctor:
        client = langfuse_push.get_client()
    assert client is sentinel
    ctor.assert_called_once_with()  # SDK auto-reads env vars
