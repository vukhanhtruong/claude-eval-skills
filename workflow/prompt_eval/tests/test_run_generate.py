"""Tests for the generate subcommand."""
import json
from unittest.mock import patch, MagicMock
from workflow.prompt_eval.run import _do_generate


@patch("workflow.prompt_eval.run.DatasetGenerator")
def test_generate_writes_dataset_json_and_metadata(gen_cls, tmp_path):
    gen = gen_cls.return_value
    gen.generate_dataset.return_value = [
        {"scenario": "A", "prompt_inputs": {"x": "1"}, "solution_criteria": ["c"], "task_description": "t"},
    ]

    out_dir = tmp_path / "runs" / "run_001"
    _do_generate(
        task="meal plan",
        inputs_json='{"height":"cm"}',
        num_cases=1,
        model="haiku",
        out_dir=out_dir,
    )

    dataset_file = out_dir / "dataset.json"
    assert dataset_file.exists()
    data = json.loads(dataset_file.read_text())
    assert len(data) == 1

    meta = json.loads((out_dir / "metadata.json").read_text())
    assert meta["run_id"] == "run_001"
    assert meta["test_model"] == "haiku"
    assert meta["dataset_size"] == 1
    assert meta["versions"] == []  # no versions yet

    gen_cls.assert_called_once_with(model="claude-haiku-4-5")
    gen.generate_dataset.assert_called_once()
