import json
import pytest
from prompt_eval.run import _do_save_output


class TestSaveOutput:
    def test_saves_outputs(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
        outputs = [
            {"case_index": 0, "output": "Response", "tool_calls": []},
        ]
        _do_save_output(
            prompt_name="test_prompt",
            run_id="run_001",
            version="v1",
            json_data=json.dumps(outputs),
        )
        path = tmp_path / "prompt_eval_runs" / "prompts" / "test_prompt" / "runs" / "run_001" / "v1" / "output.json"
        assert path.exists()
        saved = json.loads(path.read_text())
        assert saved == outputs
