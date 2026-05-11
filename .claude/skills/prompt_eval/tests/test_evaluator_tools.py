"""Tests for Evaluator with tool support."""
from unittest.mock import MagicMock, patch
import pytest


@pytest.fixture
def sample_test_case():
    return {
        "prompt_inputs": {"height": "180cm"},
        "solution_criteria": ["includes height"],
        "task_description": "Create meal plan",
        "scenario": "Tall person",
    }


# ---------------------------------------------------------------------------
# API guarantee: run_test_case must return str, not tuple
# ---------------------------------------------------------------------------

@patch("prompt_eval.evaluator.AnthropicLLM")
@patch("prompt_eval.evaluator.GEval")
@patch("prompt_eval.evaluator.Anthropic")
def test_run_test_case_returns_string_not_tuple(
    anthropic_cls, geval_cls, anthropic_llm_cls, sample_test_case
):
    """API guarantee: run_test_case returns str, not tuple."""
    from prompt_eval.evaluator import Evaluator
    anthropic_cls.return_value.messages.create.return_value.content = [MagicMock(text="output")]
    evaluator = Evaluator()
    output = evaluator.run_test_case(sample_test_case, "Template {height}")
    assert isinstance(output, str)  # CRITICAL assertion


# ---------------------------------------------------------------------------
# __init__ accepts tools and max_tool_turns
# ---------------------------------------------------------------------------

def test_evaluator_accepts_tools_param():
    """Evaluator can be constructed with tools and max_tool_turns."""
    from prompt_eval.evaluator import Evaluator
    with patch("prompt_eval.evaluator.Anthropic"):
        tools = [{"name": "web_fetch", "description": "Fetch", "input_schema": {}}]
        ev = Evaluator(tools=tools, max_tool_turns=3)
        assert ev.tools == tools
        assert ev.max_tool_turns == 3


def test_evaluator_tools_defaults_to_none():
    """Default tools=None, max_tool_turns=5."""
    from prompt_eval.evaluator import Evaluator
    with patch("prompt_eval.evaluator.Anthropic"):
        ev = Evaluator()
        assert ev.tools is None
        assert ev.max_tool_turns == 5


# ---------------------------------------------------------------------------
# run_test_case_with_tools exists and returns (str, list, dict)
# ---------------------------------------------------------------------------

@patch("prompt_eval.evaluator.Anthropic")
def test_run_test_case_with_tools_returns_tuple(anthropic_cls, sample_test_case):
    """run_test_case_with_tools returns (str, list[dict], dict)."""
    from prompt_eval.evaluator import Evaluator

    tools = [{"name": "web_fetch", "description": "Fetch", "input_schema": {}}]
    with patch("prompt_eval.agentic_runner.AgenticRunner") as runner_cls, \
         patch("prompt_eval.tool_mocker.ToolMocker") as mocker_cls:
        mocker_instance = MagicMock()
        mocker_instance.cache = {}
        mocker_cls.return_value = mocker_instance

        runner_instance = MagicMock()
        runner_instance.run.return_value = ("final answer", [{"tool": "web_fetch"}])
        runner_cls.return_value = runner_instance

        ev = Evaluator(tools=tools)
        result = ev.run_test_case_with_tools(
            test_case=sample_test_case,
            prompt_template="Plan for {height}",
            task_context="Create meal plan",
            mock_cache={},
        )

    output, tool_log, updated_cache = result
    assert isinstance(output, str)
    assert isinstance(tool_log, list)
    assert isinstance(updated_cache, dict)


@patch("prompt_eval.evaluator.Anthropic")
def test_run_test_case_with_tools_mutates_mock_cache(anthropic_cls, sample_test_case):
    """mock_cache dict is mutated in place after run."""
    from prompt_eval.evaluator import Evaluator

    tools = [{"name": "web_fetch", "description": "Fetch", "input_schema": {}}]
    shared_cache = {}
    generated_cache = {'web_fetch::{}': {"content": "some content", "generated_by": "haiku"}}

    with patch("prompt_eval.agentic_runner.AgenticRunner") as runner_cls, \
         patch("prompt_eval.tool_mocker.ToolMocker") as mocker_cls:
        mocker_instance = MagicMock()
        mocker_instance.cache = generated_cache
        mocker_cls.return_value = mocker_instance

        runner_instance = MagicMock()
        runner_instance.run.return_value = ("output", [])
        runner_cls.return_value = runner_instance

        ev = Evaluator(tools=tools)
        ev.run_test_case_with_tools(
            test_case=sample_test_case,
            prompt_template="Plan for {height}",
            task_context="Create meal plan",
            mock_cache=shared_cache,
        )

    # shared_cache was updated from mocker.cache
    assert 'web_fetch::{}' in shared_cache


# ---------------------------------------------------------------------------
# run_evaluation uses tool path when self.tools is set
# ---------------------------------------------------------------------------

@patch("prompt_eval.evaluator.AnthropicLLM")
@patch("prompt_eval.evaluator.GEval")
@patch("prompt_eval.evaluator.Anthropic")
def test_run_evaluation_with_tools_includes_tool_log(
    anthropic_cls, geval_cls, anthropic_llm_cls, sample_test_case, tmp_path
):
    """When tools enabled, results contain tool_log."""
    from prompt_eval.evaluator import Evaluator

    tools = [{"name": "web_fetch", "description": "Fetch", "input_schema": {}}]
    metric = MagicMock(score=0.8, reason="good")
    geval_cls.return_value = metric

    ev = Evaluator(tools=tools, max_concurrent_tasks=1)

    tool_log = [{"tool": "web_fetch", "input": {}, "output": "data"}]
    with patch.object(ev, "run_test_case_with_tools") as mock_run:
        mock_run.return_value = ("tool output", tool_log, {})
        results = ev.run_evaluation(
            dataset=[sample_test_case],
            prompt_template="Plan for {height}",
            output_file=str(tmp_path / "out.json"),
            task_context="Create meal plan",
            mock_cache={},
        )

    assert len(results) == 1
    assert results[0]["output"] == "tool output"
    assert results[0]["tool_log"] == tool_log


@patch("prompt_eval.evaluator.AnthropicLLM")
@patch("prompt_eval.evaluator.GEval")
@patch("prompt_eval.evaluator.Anthropic")
def test_run_evaluation_without_tools_no_tool_log(
    anthropic_cls, geval_cls, anthropic_llm_cls, sample_test_case, tmp_path
):
    """When tools not enabled, results do NOT contain tool_log."""
    from prompt_eval.evaluator import Evaluator

    anthropic_cls.return_value.messages.create.return_value.content = [
        MagicMock(text="plain output")
    ]
    metric = MagicMock(score=0.7, reason="ok")
    geval_cls.return_value = metric

    ev = Evaluator(max_concurrent_tasks=1)
    results = ev.run_evaluation(
        dataset=[sample_test_case],
        prompt_template="Plan for {height}",
        output_file=str(tmp_path / "out.json"),
    )

    assert len(results) == 1
    assert "tool_log" not in results[0]
