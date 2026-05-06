"""Tests for the AnthropicLLM adapter."""
from unittest.mock import MagicMock, patch
from prompt_eval.anthropic_llm import AnthropicLLM


def test_get_model_name_returns_configured_model():
    llm = AnthropicLLM(model="claude-haiku-4-5")
    assert llm.get_model_name() == "claude-haiku-4-5"


def test_generate_calls_anthropic_with_user_message(mock_anthropic_response):
    with patch("prompt_eval.anthropic_llm.Anthropic") as cls:
        client = MagicMock()
        client.messages.create.return_value = mock_anthropic_response("graded: 8")
        cls.return_value = client

        llm = AnthropicLLM(model="claude-sonnet-4-6")
        result = llm.generate("Score this output: ...")

        assert result == "graded: 8"
        client.messages.create.assert_called_once()
        kwargs = client.messages.create.call_args.kwargs
        assert kwargs["model"] == "claude-sonnet-4-6"
        assert kwargs["messages"] == [{"role": "user", "content": "Score this output: ..."}]


def test_load_model_returns_client():
    with patch("prompt_eval.anthropic_llm.Anthropic"):
        llm = AnthropicLLM()
        assert llm.load_model() is llm.client
