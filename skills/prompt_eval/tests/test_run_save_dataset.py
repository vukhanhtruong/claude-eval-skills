import json
import pytest
from prompt_eval.run import _do_save_dataset


class TestSaveDataset:
    def test_saves_valid_dataset(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
        dataset = [
            {
                "scenario": "Test",
                "prompt_inputs": {"x": "y"},
                "solution_criteria": ["C1"],
            }
        ]
        _do_save_dataset(
            prompt_name="test_prompt",
            run_id="run_001",
            json_data=json.dumps(dataset),
        )
        path = tmp_path / "prompt_eval_runs" / "prompts" / "test_prompt" / "runs" / "run_001" / "dataset.json"
        assert path.exists()
        saved = json.loads(path.read_text())
        assert saved == dataset

    def test_rejects_invalid_dataset(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
        dataset = [{"scenario": "Test"}]  # missing fields
        with pytest.raises(ValueError, match="Invalid dataset"):
            _do_save_dataset(
                prompt_name="test_prompt",
                run_id="run_001",
                json_data=json.dumps(dataset),
            )
