"""Verifies how the CLI resolves the user's project / artifact directory."""
import pytest

from prompt_eval.run import _resolve_artifact_root


def test_uses_prompt_eval_project_dir_when_set(tmp_path, monkeypatch):
    monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/should/be/ignored")

    root = _resolve_artifact_root()

    assert root == tmp_path / "prompt_eval_runs"


def test_falls_back_to_claude_project_dir(tmp_path, monkeypatch):
    other = tmp_path / "claude_project"
    other.mkdir()
    monkeypatch.delenv("PROMPT_EVAL_PROJECT_DIR", raising=False)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(other))
    # cwd has no prompt_eval_runs/ so CLAUDE_PROJECT_DIR must be used
    monkeypatch.chdir(tmp_path)

    root = _resolve_artifact_root()

    assert root == other / "prompt_eval_runs"


def test_cwd_wins_over_claude_project_dir(tmp_path, monkeypatch):
    """Stale CLAUDE_PROJECT_DIR must not override a cwd that already has prompt_eval_runs/."""
    stale = tmp_path / "stale_project"
    stale.mkdir()
    cwd = tmp_path / "current_project"
    cwd.mkdir()
    (cwd / "prompt_eval_runs").mkdir()

    monkeypatch.delenv("PROMPT_EVAL_PROJECT_DIR", raising=False)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(stale))
    monkeypatch.chdir(cwd)

    root = _resolve_artifact_root()

    assert root == cwd / "prompt_eval_runs"


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
