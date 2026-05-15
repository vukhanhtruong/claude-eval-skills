"""Tests for the --json-file flag on save-dataset/save-output/save-scores.

Motivation: passing JSON inline via --json '...' breaks shell quoting whenever
the payload contains an apostrophe (e.g. "product's rationale"). --json-file
lets callers write payloads via a file and skip the shell entirely.
"""
import json
import pytest
from prompt_eval.run import main
from prompt_eval.data_helpers import MetadataHelper


APOSTROPHE_DATASET = [
    {
        "scenario": "Product's tagline",
        "prompt_inputs": {"x": "y"},
        "solution_criteria": ["Don't repeat the brand name"],
    }
]
APOSTROPHE_OUTPUTS = [
    {"case_index": 0, "output": "It's the product's rationale.", "tool_calls": []},
]
APOSTROPHE_SCORES = [
    {
        "case_index": 0,
        "scenario": "Product's tagline",
        "score": 9,
        "reasoning": "Captures the product's value without repeating it.",
        "criteria_breakdown": {"clarity": "PASS"},
    }
]


def _seed_run(tmp_path, prompt="demo", run_id="run_001"):
    """Minimum run layout for save-output / save-scores."""
    run_dir = tmp_path / "prompt_eval_runs" / "prompts" / prompt / "runs" / run_id
    (run_dir / "v1").mkdir(parents=True)
    MetadataHelper.write(run_dir, {"run_id": run_id, "versions": []})
    (run_dir / "dataset.json").write_text(json.dumps(APOSTROPHE_DATASET))
    (run_dir / "v1" / "prompt.txt").write_text("dummy prompt")
    return run_dir


class TestSaveDatasetJsonFile:
    def test_reads_payload_from_file_with_apostrophes(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
        payload_path = tmp_path / "dataset_payload.json"
        payload_path.write_text(json.dumps(APOSTROPHE_DATASET))
        rc = main([
            "save-dataset", "--prompt", "demo", "--run-id", "run_001",
            "--json-file", str(payload_path),
        ])
        assert rc == 0
        saved = json.loads(
            (tmp_path / "prompt_eval_runs" / "prompts" / "demo" / "runs"
             / "run_001" / "dataset.json").read_text()
        )
        assert saved == APOSTROPHE_DATASET

    def test_rejects_both_json_and_json_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
        payload_path = tmp_path / "p.json"
        payload_path.write_text("[]")
        with pytest.raises(SystemExit):
            main([
                "save-dataset", "--prompt", "demo", "--run-id", "run_001",
                "--json", "[]", "--json-file", str(payload_path),
            ])

    def test_rejects_neither_json_nor_json_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
        with pytest.raises(SystemExit):
            main(["save-dataset", "--prompt", "demo", "--run-id", "run_001"])


class TestSaveOutputJsonFile:
    def test_reads_payload_from_file_with_apostrophes(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
        _seed_run(tmp_path)
        payload_path = tmp_path / "output_payload.json"
        payload_path.write_text(json.dumps(APOSTROPHE_OUTPUTS))
        rc = main([
            "save-output", "--prompt", "demo", "--run-id", "run_001",
            "--version", "v1", "--json-file", str(payload_path),
        ])
        assert rc == 0
        saved_path = (
            tmp_path / "prompt_eval_runs" / "prompts" / "demo" / "runs"
            / "run_001" / "v1" / "output.json"
        )
        saved = json.loads(saved_path.read_text())
        assert saved == APOSTROPHE_OUTPUTS


class TestSaveScoresJsonFile:
    def test_reads_payload_from_file_with_apostrophes(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
        monkeypatch.setattr("prompt_eval.run.restart_mkdocs", lambda *_a, **_k: None)
        _seed_run(tmp_path)
        payload_path = tmp_path / "scores_payload.json"
        payload_path.write_text(json.dumps(APOSTROPHE_SCORES))
        rc = main([
            "save-scores", "--prompt", "demo", "--run-id", "run_001",
            "--version", "v1", "--json-file", str(payload_path),
        ])
        assert rc == 0
        saved = json.loads(
            (tmp_path / "prompt_eval_runs" / "prompts" / "demo" / "runs"
             / "run_001" / "v1" / "scores.json").read_text()
        )
        assert saved["cases"] == APOSTROPHE_SCORES
