"""Tests for the list-runs subcommand."""
import json
import subprocess
import sys
from pathlib import Path


def test_list_runs_prints_each_run(tmp_path, capsys):
    # Build runs/run_001 and runs/run_002
    runs = tmp_path / "runs"
    for run_id, n_versions, avg in [("run_001", 3, 8.9), ("run_002", 1, 7.2)]:
        d = runs / run_id
        d.mkdir(parents=True)
        (d / "metadata.json").write_text(json.dumps({
            "run_id": run_id,
            "versions": [f"v{i+1}" for i in range(n_versions)],
            "dataset_size": 5,
            "latest_avg_score": avg,
        }))

    from workflow.prompt_eval.run import list_runs
    list_runs(runs)
    captured = capsys.readouterr()
    assert "run_001" in captured.out
    assert "run_002" in captured.out
    assert "8.9" in captured.out
    assert "v1→v3" in captured.out or "v3" in captured.out


def test_list_runs_with_empty_dir_says_so(tmp_path, capsys):
    runs = tmp_path / "runs"
    runs.mkdir()
    from workflow.prompt_eval.run import list_runs
    list_runs(runs)
    out = capsys.readouterr().out
    assert "No runs" in out or "no runs" in out.lower()
