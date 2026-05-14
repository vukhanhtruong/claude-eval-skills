"""Validation rules and path resolution for the new prompt namespace."""
import pytest
from prompt_eval.run import (
    _validate_prompt_name,
    _resolve_prompts_dir,
    _resolve_runs_dir,
)


def test_valid_names_accepted():
    for name in ["summarizer", "code_reviewer", "v2-experiment", "x", "a-b-c_1"]:
        _validate_prompt_name(name)  # must not raise


def test_invalid_names_rejected():
    for bad in ["", "Summarizer", "has space", "has/slash", "has.dot", "a" * 65]:
        with pytest.raises(ValueError, match="prompt name"):
            _validate_prompt_name(bad)


def test_resolve_prompts_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
    assert _resolve_prompts_dir() == tmp_path / "prompt_eval_runs" / "prompts"


def test_resolve_runs_dir_namespaces_under_prompt(tmp_path, monkeypatch):
    monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
    runs = _resolve_runs_dir("summarizer")
    assert runs == tmp_path / "prompt_eval_runs" / "prompts" / "summarizer" / "runs"


def test_resolve_runs_dir_validates_name(tmp_path, monkeypatch):
    monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
    with pytest.raises(ValueError, match="prompt name"):
        _resolve_runs_dir("Bad Name")
