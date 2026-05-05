"""Tests for Evaluator.run_evaluation."""
import json
from unittest.mock import patch, MagicMock
from workflow.prompt_eval.evaluator import Evaluator


@patch("workflow.prompt_eval.evaluator.AnthropicLLM")
@patch("workflow.prompt_eval.evaluator.GEval")
@patch("workflow.prompt_eval.evaluator.Anthropic")
def test_run_evaluation_writes_output_json(
    anthropic_cls, geval_cls, anthropic_llm_cls, sample_test_case, tmp_path
):
    # Stub the test-model call
    anthropic_cls.return_value.messages.create.return_value.content = [
        MagicMock(text="produced output")
    ]
    # Stub the grader
    metric = MagicMock(score=0.7, reason="adequate")
    geval_cls.return_value = metric

    dataset = [sample_test_case]
    output_file = tmp_path / "output.json"

    evaluator = Evaluator(max_concurrent_tasks=1)
    results = evaluator.run_evaluation(
        dataset=dataset,
        prompt_template="Plan for {height} cm.",
        output_file=str(output_file),
    )

    assert len(results) == 1
    assert results[0]["score"] == 7
    assert results[0]["reasoning"] == "adequate"
    assert results[0]["output"] == "produced output"
    assert results[0]["test_case"]["scenario"] == sample_test_case["scenario"]

    on_disk = json.loads(output_file.read_text())
    assert len(on_disk) == 1
