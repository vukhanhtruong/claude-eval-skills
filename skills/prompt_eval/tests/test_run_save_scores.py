import json
import pytest
from prompt_eval.run import _do_save_scores


class TestSaveScores:
    def test_saves_scores_with_aggregation(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
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
