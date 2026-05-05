"""Tests for the evaluate subcommand."""
import json
from unittest.mock import patch, MagicMock
from workflow.prompt_eval.run import _do_evaluate


@patch("workflow.prompt_eval.run.regenerate_for_run")
@patch("workflow.prompt_eval.run.start_mkdocs_if_idle")
@patch("workflow.prompt_eval.run.Evaluator")
def test_evaluate_writes_outputs_and_updates_metadata(
    eval_cls, start_mkdocs, regen, tmp_path
):
    # Set up out_dir with dataset + v1 prompt + initial metadata
    out_dir = tmp_path / "runs" / "run_001"
    (out_dir / "v1").mkdir(parents=True)
    (out_dir / "dataset.json").write_text(json.dumps([
        {"scenario": "A", "prompt_inputs": {"x": "1"}, "solution_criteria": ["c"], "task_description": "t"},
    ]))
    (out_dir / "v1" / "prompt.txt").write_text("Test prompt {x}")
    (out_dir / "metadata.json").write_text(json.dumps({
        "run_id": "run_001",
        "test_model": "haiku",
        "judge_model": None,
        "dataset_size": 1,
        "versions": [],
        "version_data": {},
    }))

    evaluator = eval_cls.return_value
    evaluator.run_evaluation.return_value = [
        {"test_case": {"scenario": "A", "solution_criteria": ["c"]}, "output": "x", "score": 8, "reasoning": "ok"},
    ]

    _do_evaluate(
        version="v1", model="haiku", judge_model="sonnet",
        out_dir=out_dir, extra_criteria=None,
    )

    # output.json written
    assert (out_dir / "v1" / "output.json").exists()

    # metadata updated
    meta = json.loads((out_dir / "metadata.json").read_text())
    assert meta["versions"] == ["v1"]
    assert meta["judge_model"] == "sonnet"
    assert meta["latest_avg_score"] == 8.0
    assert meta["version_data"]["v1"]["avg_score"] == 8.0

    # docs regen + mkdocs autostart called
    regen.assert_called_once()
    start_mkdocs.assert_called_once()


@patch("workflow.prompt_eval.run.regenerate_for_run")
@patch("workflow.prompt_eval.run.start_mkdocs_if_idle")
@patch("workflow.prompt_eval.run.Evaluator")
def test_evaluate_warns_when_judge_model_changes(
    eval_cls, start_mkdocs, regen, tmp_path, capsys
):
    out_dir = tmp_path / "runs" / "run_001"
    (out_dir / "v2").mkdir(parents=True)
    (out_dir / "dataset.json").write_text(json.dumps([
        {"scenario": "A", "prompt_inputs": {}, "solution_criteria": ["c"], "task_description": "t"},
    ]))
    (out_dir / "v2" / "prompt.txt").write_text("p")
    (out_dir / "metadata.json").write_text(json.dumps({
        "run_id": "run_001", "test_model": "haiku", "judge_model": "sonnet",
        "dataset_size": 1, "versions": ["v1"], "version_data": {"v1": {"avg_score": 5.0}},
    }))
    eval_cls.return_value.run_evaluation.return_value = [
        {"test_case": {"scenario": "A", "solution_criteria": []}, "output": "x", "score": 7, "reasoning": "ok"},
    ]

    _do_evaluate(
        version="v2", model="haiku", judge_model="haiku",  # different from sonnet
        out_dir=out_dir, extra_criteria=None,
    )
    out = capsys.readouterr().out
    assert "originally evaluated with judge_model=sonnet" in out.lower() or "warning" in out.lower()
