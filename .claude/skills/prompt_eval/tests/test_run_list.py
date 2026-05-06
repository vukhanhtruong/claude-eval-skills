"""list-runs prints runs scoped to a prompt."""
import json

from prompt_eval.run import list_runs


def test_list_runs_prints_each_run_for_a_prompt(tmp_path, capsys):
    runs = tmp_path / "prompts" / "summarizer" / "runs"
    for run_id, n_versions, avg in [("run_001", 3, 8.9), ("run_002", 1, 7.2)]:
        d = runs / run_id
        d.mkdir(parents=True)
        (d / "metadata.json").write_text(json.dumps({
            "run_id": run_id,
            "prompt_name": "summarizer",
            "versions": [f"v{i+1}" for i in range(n_versions)],
            "dataset_size": 5,
            "latest_avg_score": avg,
        }))

    list_runs(runs)
    captured = capsys.readouterr()
    assert "run_001" in captured.out
    assert "run_002" in captured.out
    assert "8.9" in captured.out


def test_list_runs_with_empty_dir_says_so(tmp_path, capsys):
    runs = tmp_path / "prompts" / "summarizer" / "runs"
    runs.mkdir(parents=True)
    list_runs(runs)
    out = capsys.readouterr().out
    assert "no runs" in out.lower() or "No runs" in out


def test_list_runs_with_missing_dir_says_so(tmp_path, capsys):
    list_runs(tmp_path / "prompts" / "ghost" / "runs")
    out = capsys.readouterr().out
    assert "no runs" in out.lower() or "No runs" in out
