import json
import pytest
from prompt_eval.run import main
from prompt_eval.data_helpers import MetadataHelper


def _setup_run(tmp_path, prompt="demo", run_id="run_001"):
    """Create the minimum run layout the CLI expects."""
    runs_root = tmp_path / "prompt_eval_runs" / "prompts" / prompt / "runs" / run_id
    runs_root.mkdir(parents=True)
    MetadataHelper.write(runs_root, {"run_id": run_id, "versions": []})
    (runs_root / "dataset.json").write_text(
        '[{"scenario": "s", "prompt_inputs": {}, "solution_criteria": ["c"]}]'
    )
    return runs_root


class TestSaveOutputWithModelFlag:
    def test_save_output_passes_when_lock_matches(self, tmp_path, monkeypatch):
        run_dir = _setup_run(tmp_path)
        MetadataHelper.set_models(run_dir, "haiku", "sonnet")
        monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
        payload = json.dumps([{"case_index": 0, "output": "hi"}])
        rc = main([
            "save-output", "--prompt", "demo", "--run-id", "run_001",
            "--version", "v1", "--model", "haiku", "--json", payload,
        ])
        assert rc == 0
        assert (run_dir / "v1" / "output.json").exists()

    def test_save_output_rejects_mismatched_model(self, tmp_path, monkeypatch):
        run_dir = _setup_run(tmp_path)
        MetadataHelper.set_models(run_dir, "haiku", "sonnet")
        monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
        payload = json.dumps([{"case_index": 0, "output": "hi"}])
        with pytest.raises(ValueError, match="disagrees with locked test_model"):
            main([
                "save-output", "--prompt", "demo", "--run-id", "run_001",
                "--version", "v1", "--model", "opus", "--json", payload,
            ])


class TestSetModelsCommand:
    def test_set_models_writes_config(self, tmp_path, monkeypatch):
        run_dir = _setup_run(tmp_path)
        monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
        rc = main([
            "set-models", "--prompt", "demo", "--run-id", "run_001",
            "--test-model", "haiku", "--judge-model", "sonnet",
        ])
        assert rc == 0
        meta = MetadataHelper.read(run_dir)
        assert meta["test_model"] == "haiku"
        assert meta["judge_model"] == "sonnet"
        assert meta["models_locked"] is True

    def test_set_models_overwrites_existing(self, tmp_path, monkeypatch):
        run_dir = _setup_run(tmp_path)
        MetadataHelper.set_models(run_dir, "old_test", "old_judge")
        monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
        rc = main([
            "set-models", "--prompt", "demo", "--run-id", "run_001",
            "--test-model", "sonnet", "--judge-model", "opus",
        ])
        assert rc == 0
        meta = MetadataHelper.read(run_dir)
        assert meta["test_model"] == "sonnet"
        assert meta["judge_model"] == "opus"
