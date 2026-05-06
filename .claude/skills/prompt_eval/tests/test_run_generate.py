"""generate subcommand: writes namespaced runs and persists prompt_name."""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from prompt_eval.run import _do_generate


def test_generate_writes_dataset_and_metadata_with_prompt_name(tmp_path):
    out_dir = tmp_path / "prompts" / "summarizer" / "runs" / "run_001"

    fake_dataset = [{"scenario": "S1", "input_kwargs": {}, "solution_criteria": ["x"]}]

    with patch("prompt_eval.run.DatasetGenerator") as DG:
        instance = MagicMock()
        instance.generate_dataset.return_value = fake_dataset
        DG.return_value = instance

        _do_generate(
            task="summarize x",
            inputs_json='{"text": "string"}',
            num_cases=1,
            model="haiku",
            out_dir=out_dir,
            prompt_name="summarizer",
        )

    assert (out_dir / "dataset.json").exists()
    meta = json.loads((out_dir / "metadata.json").read_text())
    assert meta["run_id"] == "run_001"
    assert meta["prompt_name"] == "summarizer"
    assert meta["task"] == "summarize x"
    assert meta["test_model"] == "haiku"
    assert meta["dataset_size"] == 1
