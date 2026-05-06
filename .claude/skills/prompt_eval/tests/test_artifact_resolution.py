"""Verifies how the CLI resolves the user's project / artifact directory."""
import pytest

from prompt_eval.run import _resolve_artifact_root


def test_uses_prompt_eval_project_dir_when_set(tmp_path, monkeypatch):
    monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/should/be/ignored")

    root = _resolve_artifact_root()

    assert root == tmp_path / "prompt_eval_runs"


def test_falls_back_to_claude_project_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("PROMPT_EVAL_PROJECT_DIR", raising=False)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

    root = _resolve_artifact_root()

    assert root == tmp_path / "prompt_eval_runs"


def test_falls_back_to_cwd_when_no_env(tmp_path, monkeypatch):
    monkeypatch.delenv("PROMPT_EVAL_PROJECT_DIR", raising=False)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "prompt_eval_runs").mkdir()

    root = _resolve_artifact_root()

    assert root == tmp_path / "prompt_eval_runs"


def test_raises_when_not_in_project_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("PROMPT_EVAL_PROJECT_DIR", raising=False)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    # Don't create prompt_eval_runs/

    with pytest.raises(FileNotFoundError, match="prompt_eval_runs.*not found"):
        _resolve_artifact_root()
