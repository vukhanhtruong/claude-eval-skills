"""Tests for Evaluator.run_test_case."""
from unittest.mock import patch
from workflow.prompt_eval.evaluator import Evaluator


@patch("workflow.prompt_eval.evaluator.Anthropic")
def test_run_test_case_renders_template_and_calls_model(
    anthropic_cls, mock_anthropic_response, sample_test_case
):
    client = anthropic_cls.return_value
    client.messages.create.return_value = mock_anthropic_response("Generated meal plan…")

    evaluator = Evaluator(test_model="claude-haiku-4-5")
    template = "Generate a plan for height={height}, weight={weight}."

    output = evaluator.run_test_case(sample_test_case, template)

    assert output == "Generated meal plan…"
    sent = client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "height=175" in sent
    assert "weight=65" in sent
    assert client.messages.create.call_args.kwargs["model"] == "claude-haiku-4-5"
