"""Tests for `prompt-eval show` — scoreboard inspection of a run+version."""
import json

import pytest

from prompt_eval.run import _do_show


def _write_output(out_dir, version, results):
    (out_dir / version).mkdir(parents=True, exist_ok=True)
    (out_dir / version / "output.json").write_text(json.dumps(results))


def test_show_pretty_prints_per_case_block(tmp_path, capsys):
    out_dir = tmp_path / "run_001"
    _write_output(out_dir, "v1", [
        {
            "test_case": {"scenario": "Vegan endurance runner"},
            "output": "x" * 1247,
            "score": 8,
            "reasoning": "Covers caloric total and excludes animal products.",
        },
    ])

    _do_show(out_dir, "v1", json_output=False)

    out = capsys.readouterr().out
    assert "Run: run_001" in out
    assert "Version: v1" in out
    assert "Average: 8.0/10" in out
    assert "Pass rate: 100.0%" in out
    assert "=== Case 1: Vegan endurance runner" in out
    assert "Score: 8/10" in out
    assert "Output length: 1247 chars" in out
    assert "Covers caloric total" in out


def test_show_json_emits_structured_summary(tmp_path, capsys):
    out_dir = tmp_path / "run_002"
    _write_output(out_dir, "v2", [
        {"test_case": {"scenario": "A"}, "output": "ok", "score": 9, "reasoning": "good"},
        {"test_case": {"scenario": "B"}, "output": "bad", "score": 4, "reasoning": "weak"},
    ])

    _do_show(out_dir, "v2", json_output=True)

    payload = json.loads(capsys.readouterr().out)
    assert payload["run_id"] == "run_002"
    assert payload["version"] == "v2"
    assert payload["average_score"] == 6.5
    assert payload["pass_rate"] == 50.0
    assert len(payload["cases"]) == 2
    assert payload["cases"][0] == {
        "scenario": "A",
        "score": 9,
        "output_length": 2,
        "reasoning": "good",
    }


def test_show_normalizes_scenario_when_model_returns_dict(tmp_path, capsys):
    """Models occasionally return scenario as {'title': ..., 'description': ...}
    instead of a plain string. Show must normalize so downstream code never
    has to defend against the shape."""
    out_dir = tmp_path / "run_003"
    _write_output(out_dir, "v1", [
        {
            "test_case": {"scenario": {"title": "Marathoner", "description": "..."}},
            "output": "ok",
            "score": 7,
            "reasoning": "ok",
        },
    ])

    _do_show(out_dir, "v1", json_output=True)

    payload = json.loads(capsys.readouterr().out)
    assert payload["cases"][0]["scenario"] == "Marathoner"


def test_show_errors_clearly_when_output_file_missing(tmp_path):
    out_dir = tmp_path / "run_404"
    out_dir.mkdir()  # run dir exists, but no version subdir

    with pytest.raises(SystemExit) as exc:
        _do_show(out_dir, "v1", json_output=False)

    assert exc.value.code == 1
