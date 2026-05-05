"""Tests for Evaluator.grade_with_geval (GEval mocked)."""
from unittest.mock import patch, MagicMock
from workflow.prompt_eval.evaluator import Evaluator


@patch("workflow.prompt_eval.evaluator.AnthropicLLM")
@patch("workflow.prompt_eval.evaluator.GEval")
@patch("workflow.prompt_eval.evaluator.Anthropic")
def test_grade_returns_score_and_reasoning(
    anthropic_cls, geval_cls, anthropic_llm_cls, sample_test_case
):
    metric = MagicMock()
    metric.score = 0.8
    metric.reason = "All criteria met."
    geval_cls.return_value = metric

    evaluator = Evaluator(judge_model="claude-sonnet-4-6")
    result = evaluator.grade_with_geval(
        test_case=sample_test_case,
        output="Some meal plan output",
        extra_criteria="Must include macros",
    )

    assert result == {"score": 8, "reasoning": "All criteria met."}
    metric.measure.assert_called_once()


@patch("workflow.prompt_eval.evaluator.AnthropicLLM")
@patch("workflow.prompt_eval.evaluator.GEval")
@patch("workflow.prompt_eval.evaluator.Anthropic")
def test_grade_builds_evaluation_steps_from_solution_criteria(
    anthropic_cls, geval_cls, anthropic_llm_cls, sample_test_case
):
    metric = MagicMock(score=0.9, reason="ok")
    geval_cls.return_value = metric

    Evaluator().grade_with_geval(sample_test_case, "out", extra_criteria=None)

    kwargs = geval_cls.call_args.kwargs
    steps_text = "\n".join(kwargs["evaluation_steps"])
    assert "Includes daily caloric total" in steps_text
    assert "Excludes all animal products" in steps_text
