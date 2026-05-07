"""Verify Evaluator.run_evaluation calls on_case_complete with the right args."""
from unittest.mock import patch, MagicMock
from prompt_eval.evaluator import Evaluator


@patch("prompt_eval.evaluator.AnthropicLLM")
@patch("prompt_eval.evaluator.GEval")
@patch("prompt_eval.evaluator.Anthropic")
def test_on_case_complete_invoked_per_case_with_full_signature(
    anthropic_cls, geval_cls, anthropic_llm_cls, sample_test_case, tmp_path
):
    # Test model produces a known output
    anthropic_cls.return_value.messages.create.return_value.content = [
        MagicMock(text="produced output")
    ]
    # Judge gives score 0.7 → 7/10 after rounding
    metric = MagicMock(score=0.7, reason="good enough")
    geval_cls.return_value = metric

    calls = []

    def cb(index, case, rendered, output, score, reasoning, latency_ms):
        calls.append({
            "index": index, "case": case, "rendered": rendered,
            "output": output, "score": score, "reasoning": reasoning,
            "latency_ms": latency_ms,
        })

    dataset = [sample_test_case]
    evaluator = Evaluator(max_concurrent_tasks=1)
    evaluator.run_evaluation(
        dataset=dataset,
        prompt_template="Plan for {height} cm.",
        output_file=str(tmp_path / "out.json"),
        on_case_complete=cb,
    )

    assert len(calls) == 1
    call = calls[0]
    assert call["index"] == 0
    assert call["case"] is sample_test_case
    # Render should have substituted {height} → 175
    assert "175" in call["rendered"]
    assert call["output"] == "produced output"
    assert call["score"] == 7
    assert call["reasoning"] == "good enough"
    # Latency is an int (milliseconds)
    assert isinstance(call["latency_ms"], int)
    assert call["latency_ms"] >= 0


@patch("prompt_eval.evaluator.AnthropicLLM")
@patch("prompt_eval.evaluator.GEval")
@patch("prompt_eval.evaluator.Anthropic")
def test_on_case_complete_index_matches_submit_order_under_parallelism(
    anthropic_cls, geval_cls, anthropic_llm_cls, sample_test_case, tmp_path
):
    """Index must come from enumerate at submit time, not completion order."""
    anthropic_cls.return_value.messages.create.return_value.content = [
        MagicMock(text="x")
    ]
    geval_cls.return_value = MagicMock(score=0.5, reason="ok")

    dataset = [
        {**sample_test_case, "scenario": "A"},
        {**sample_test_case, "scenario": "B"},
        {**sample_test_case, "scenario": "C"},
    ]

    seen = []

    def cb(index, case, *args):
        seen.append((index, case["scenario"]))

    evaluator = Evaluator(max_concurrent_tasks=3)
    evaluator.run_evaluation(
        dataset=dataset,
        prompt_template="t {height}",
        output_file=str(tmp_path / "out.json"),
        on_case_complete=cb,
    )

    # Indices match the original dataset position regardless of completion order
    by_scenario = {scenario: idx for idx, scenario in seen}
    assert by_scenario == {"A": 0, "B": 1, "C": 2}


@patch("prompt_eval.evaluator.AnthropicLLM")
@patch("prompt_eval.evaluator.GEval")
@patch("prompt_eval.evaluator.Anthropic")
def test_run_evaluation_works_when_callback_is_none(
    anthropic_cls, geval_cls, anthropic_llm_cls, sample_test_case, tmp_path
):
    """Default callback=None preserves existing behavior."""
    anthropic_cls.return_value.messages.create.return_value.content = [
        MagicMock(text="x")
    ]
    geval_cls.return_value = MagicMock(score=0.6, reason="ok")

    evaluator = Evaluator(max_concurrent_tasks=1)
    results = evaluator.run_evaluation(
        dataset=[sample_test_case],
        prompt_template="t {height}",
        output_file=str(tmp_path / "out.json"),
        # no on_case_complete passed
    )
    assert len(results) == 1
    assert results[0]["score"] == 6
