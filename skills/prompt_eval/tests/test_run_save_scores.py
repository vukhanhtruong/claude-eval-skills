import json
import pytest
from prompt_eval.run import _do_save_scores


class TestSaveScores:
    def test_saves_scores_with_aggregation(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
        monkeypatch.setattr("prompt_eval.run.restart_mkdocs", lambda *_a, **_k: None)
        # save-scores now also regenerates docs, which needs prompt.txt to exist
        version_dir = tmp_path / "prompt_eval_runs" / "prompts" / "test_prompt" / "runs" / "run_001" / "v1"
        version_dir.mkdir(parents=True)
        (version_dir / "prompt.txt").write_text("dummy prompt")
        scores = [
            {
                "case_index": 0,
                "scenario": "Test",
                "score": 8,
                "reasoning": "Good",
                "criteria_breakdown": {"C1": "PASS"},
            },
        ]
        _do_save_scores(
            prompt_name="test_prompt",
            run_id="run_001",
            version="v1",
            json_data=json.dumps(scores),
        )
        path = tmp_path / "prompt_eval_runs" / "prompts" / "test_prompt" / "runs" / "run_001" / "v1" / "scores.json"
        assert path.exists()
        saved = json.loads(path.read_text())
        assert saved["version"] == "v1"
        assert saved["cases"] == scores
        assert saved["summary"]["average_score"] == 8.0

    def test_rejects_invalid_scores(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
        scores = [{"score": 8}]  # missing fields
        with pytest.raises(ValueError, match="Invalid scores"):
            _do_save_scores(
                prompt_name="test_prompt",
                run_id="run_001",
                version="v1",
                json_data=json.dumps(scores),
            )


class TestSaveScoresWiresDocsPipeline:
    """save-scores should bootstrap the docs site, register the version in
    metadata.json, regenerate the per-run pages, and restart mkdocs serve."""

    def test_save_scores_regenerates_docs_and_starts_mkdocs(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))

        restart_calls = []
        monkeypatch.setattr(
            "prompt_eval.run.restart_mkdocs",
            lambda docs_site_dir: restart_calls.append(docs_site_dir),
        )

        run_dir = tmp_path / "prompt_eval_runs" / "prompts" / "demo" / "runs" / "run_001"
        (run_dir / "v1").mkdir(parents=True)
        (run_dir / "v1" / "prompt.txt").write_text("Test prompt body")
        (run_dir / "v1" / "output.json").write_text(json.dumps([
            {"case_index": 0, "output": "Some output", "tool_calls": []},
        ]))

        scores = [{
            "case_index": 0,
            "scenario": "Happy path",
            "score": 9,
            "reasoning": "Solid",
            "criteria_breakdown": {"clarity": "PASS"},
        }]
        _do_save_scores(
            prompt_name="demo", run_id="run_001", version="v1",
            json_data=json.dumps(scores),
        )

        # metadata.json registers v1
        meta_path = run_dir / "metadata.json"
        assert meta_path.exists(), "save-scores should create metadata.json"
        meta = json.loads(meta_path.read_text())
        assert "v1" in meta.get("versions", []), "v1 must be appended to metadata.versions"

        # docs-site bootstrapped + version page regenerated
        docs_site = tmp_path / "prompt_eval_runs" / "docs-site"
        assert (docs_site / "mkdocs.yml").exists(), "docs-site template must be copied"
        version_page = docs_site / "docs" / "prompts" / "demo" / "runs" / "run_001" / "v1.md"
        assert version_page.exists(), "regenerate_for_run must produce v1.md"
        assert "Happy path" in version_page.read_text()

        # mkdocs restart triggered
        assert len(restart_calls) == 1, "restart_mkdocs must be called exactly once"
        assert restart_calls[0] == docs_site
