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


class TestCloneForCrossvalCommand:
    def _setup_source_run(self, tmp_path, prompt="demo"):
        run_dir = _setup_run(tmp_path, prompt=prompt, run_id="run_001")
        # Seed v1 prompt.txt and metadata that the clone command will read.
        version_dir = run_dir / "v1"
        version_dir.mkdir()
        (version_dir / "prompt.txt").write_text("You are a helpful assistant.")
        meta = MetadataHelper.read(run_dir)
        meta["versions"] = ["v1"]
        MetadataHelper.write(run_dir, meta)
        return run_dir

    def test_clone_creates_new_run_with_copied_dataset_and_prompt(
        self, tmp_path, monkeypatch
    ):
        src = self._setup_source_run(tmp_path)
        monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
        rc = main([
            "clone-for-crossval", "--prompt", "demo",
            "--from-run-id", "run_001", "--from-version", "v1",
            "--test-model", "sonnet", "--judge-model", "opus",
        ])
        assert rc == 0
        new_run = src.parent / "run_002"
        assert new_run.exists()
        assert (new_run / "dataset.json").read_bytes() == (src / "dataset.json").read_bytes()
        assert (new_run / "v1" / "prompt.txt").read_text() == "You are a helpful assistant."
        meta = MetadataHelper.read(new_run)
        assert meta["run_id"] == "run_002"
        assert meta["versions"] == ["v1"]
        assert meta["test_model"] == "sonnet"
        assert meta["judge_model"] == "opus"
        assert meta["models_locked"] is True
        assert meta["cross_validation_of"] == {"run_id": "run_001", "version": "v1"}

    def test_clone_allocates_next_free_run_id(self, tmp_path, monkeypatch):
        src = self._setup_source_run(tmp_path)
        # Pre-create run_002 to force allocator to pick run_003.
        (src.parent / "run_002").mkdir()
        monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
        rc = main([
            "clone-for-crossval", "--prompt", "demo",
            "--from-run-id", "run_001", "--from-version", "v1",
            "--test-model", "sonnet", "--judge-model", "opus",
        ])
        assert rc == 0
        assert (src.parent / "run_003").exists()

    def test_clone_raises_when_source_run_missing(self, tmp_path, monkeypatch):
        _setup_run(tmp_path)  # creates run_001 but no v1/prompt.txt
        monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
        with pytest.raises(FileNotFoundError, match="prompt.txt"):
            main([
                "clone-for-crossval", "--prompt", "demo",
                "--from-run-id", "run_999", "--from-version", "v1",
                "--test-model", "sonnet", "--judge-model", "opus",
            ])

    def test_clone_raises_when_source_version_missing(self, tmp_path, monkeypatch):
        _setup_run(tmp_path)
        monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
        with pytest.raises(FileNotFoundError, match="prompt.txt"):
            main([
                "clone-for-crossval", "--prompt", "demo",
                "--from-run-id", "run_001", "--from-version", "v1",
                "--test-model", "sonnet", "--judge-model", "opus",
            ])

    def test_clone_refreshes_docs_for_both_source_and_new_run(
        self, tmp_path, monkeypatch
    ):
        src = self._setup_source_run(tmp_path)
        monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
        calls: list[tuple[str, str]] = []
        from prompt_eval import run as run_module
        monkeypatch.setattr(
            run_module, "_refresh_docs",
            lambda prompt, run_id: calls.append((prompt, run_id)),
        )
        rc = main([
            "clone-for-crossval", "--prompt", "demo",
            "--from-run-id", "run_001", "--from-version", "v1",
            "--test-model", "sonnet", "--judge-model", "opus",
        ])
        assert rc == 0
        # Source refreshed first so its "Cross-validations:" footer reflects the
        # new sibling; new run refreshed second so its banner appears.
        assert calls == [("demo", "run_001"), ("demo", "run_002")]
        # Defensive: make sure the clone itself still happened.
        assert (src.parent / "run_002" / "metadata.json").exists()
