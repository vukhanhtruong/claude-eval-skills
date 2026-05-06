"""list-prompts prints all prompt namespaces with run counts."""
import json
from prompt_eval.run import list_prompts


def test_list_prompts_prints_each_prompt_with_count(tmp_path, capsys):
    base = tmp_path / "prompts"
    for name, runs in [("summarizer", ["run_001", "run_002"]), ("code_reviewer", ["run_001"])]:
        for r in runs:
            d = base / name / "runs" / r
            d.mkdir(parents=True)
            (d / "metadata.json").write_text(json.dumps({
                "run_id": r, "prompt_name": name, "versions": ["v1"],
                "dataset_size": 3, "latest_avg_score": 7.0,
            }))

    list_prompts(base)
    out = capsys.readouterr().out
    assert "summarizer" in out and "2" in out
    assert "code_reviewer" in out and "1" in out


def test_list_prompts_empty_dir_says_so(tmp_path, capsys):
    list_prompts(tmp_path / "prompts")
    out = capsys.readouterr().out
    assert "no prompts" in out.lower() or "No prompts" in out
