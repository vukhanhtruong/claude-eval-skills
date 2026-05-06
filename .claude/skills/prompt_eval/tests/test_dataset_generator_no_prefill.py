"""Regression tests: Anthropic deprecated assistant-message prefill on newer models
(claude-sonnet-4-6 rejects it with HTTP 400). DatasetGenerator must use user-only
messages and tolerate code-fence-wrapped JSON in the response."""
import json
from unittest.mock import patch

from prompt_eval.evaluator import DatasetGenerator


@patch("prompt_eval.evaluator.Anthropic")
def test_generate_unique_ideas_uses_only_user_messages(anthropic_cls, mock_anthropic_response):
    client = anthropic_cls.return_value
    client.messages.create.return_value = mock_anthropic_response('["a", "b"]')

    gen = DatasetGenerator(model="claude-sonnet-4-6")
    gen.generate_unique_ideas("task", {"x": "desc"}, num_cases=2)

    messages = client.messages.create.call_args.kwargs["messages"]
    roles = [m["role"] for m in messages]
    assert roles == ["user"], (
        f"Newer Claude models reject assistant prefill. messages must end on a user "
        f"turn, got roles={roles}"
    )


@patch("prompt_eval.evaluator.Anthropic")
def test_generate_test_case_uses_only_user_messages(anthropic_cls, mock_anthropic_response):
    client = anthropic_cls.return_value
    client.messages.create.return_value = mock_anthropic_response(json.dumps({
        "prompt_inputs": {"x": "1"},
        "solution_criteria": ["c"],
    }))

    gen = DatasetGenerator(model="claude-sonnet-4-6")
    gen.generate_test_case("task", "idea", {"x": "desc"})

    messages = client.messages.create.call_args.kwargs["messages"]
    roles = [m["role"] for m in messages]
    assert roles == ["user"], (
        f"Newer Claude models reject assistant prefill. messages must end on a user "
        f"turn, got roles={roles}"
    )


@patch("prompt_eval.evaluator.Anthropic")
def test_generate_unique_ideas_strips_markdown_fence(anthropic_cls, mock_anthropic_response):
    client = anthropic_cls.return_value
    client.messages.create.return_value = mock_anthropic_response(
        '```json\n["idea1", "idea2"]\n```'
    )

    gen = DatasetGenerator(model="claude-sonnet-4-6")
    ideas = gen.generate_unique_ideas("task", {"x": "desc"}, num_cases=2)

    assert ideas == ["idea1", "idea2"]


@patch("prompt_eval.evaluator.Anthropic")
def test_generate_test_case_strips_markdown_fence(anthropic_cls, mock_anthropic_response):
    client = anthropic_cls.return_value
    payload = {"prompt_inputs": {"x": "1"}, "solution_criteria": ["c"]}
    client.messages.create.return_value = mock_anthropic_response(
        f"```json\n{json.dumps(payload)}\n```"
    )

    gen = DatasetGenerator(model="claude-sonnet-4-6")
    tc = gen.generate_test_case("task", "idea", {"x": "desc"})

    assert tc["prompt_inputs"] == {"x": "1"}
    assert tc["solution_criteria"] == ["c"]
