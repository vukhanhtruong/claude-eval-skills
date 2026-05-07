"""Tests for the `push` subcommand: retroactive Langfuse upload."""
import json
import sys
from unittest.mock import patch, MagicMock
import pytest

from prompt_eval.run import _build_parser, _do_push


def test_push_parser_accepts_required_args():
    parser = _build_parser()
    args = parser.parse_args([
        "push", "--prompt", "summarizer", "--run-id", "run_001",
    ])
    assert args.cmd == "push"
    assert args.prompt == "summarizer"
    assert args.run_id == "run_001"
    assert args.version is None  # optional, default None = all versions


def test_push_parser_accepts_optional_version():
    parser = _build_parser()
    args = parser.parse_args([
        "push", "--prompt", "summarizer", "--run-id", "run_001",
        "--version", "v2",
    ])
    assert args.version == "v2"


@patch("prompt_eval.run.langfuse_push")
def test_push_fails_loud_when_creds_missing(lf, tmp_path, monkeypatch, capsys):
    for k in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"):
        monkeypatch.delenv(k, raising=False)
    lf.is_configured.return_value = False
    lf.REQUIRED_ENV = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST")

    out_dir = tmp_path / "prompts" / "summarizer" / "runs" / "run_001"
    out_dir.mkdir(parents=True)
    (out_dir / "metadata.json").write_text("{}")

    with pytest.raises(SystemExit):
        _do_push(out_dir=out_dir, prompt_name="summarizer", version=None)
    err = capsys.readouterr().err
    assert "LANGFUSE_PUBLIC_KEY" in err


@patch("prompt_eval.run.langfuse_push")
def test_push_errors_when_no_metadata(lf, tmp_path, monkeypatch, capsys):
    for k in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"):
        monkeypatch.setenv(k, "x")
    lf.is_configured.return_value = True
    out_dir = tmp_path / "prompts" / "summarizer" / "runs" / "run_001"
    out_dir.mkdir(parents=True)

    with pytest.raises(SystemExit):
        _do_push(out_dir=out_dir, prompt_name="summarizer", version=None)
    err = capsys.readouterr().err
    assert "metadata.json" in err


@patch("prompt_eval.run.langfuse_push")
def test_push_all_versions_when_version_omitted(lf, tmp_path, monkeypatch):
    for k in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"):
        monkeypatch.setenv(k, "x")
    lf.is_configured.return_value = True
    client = MagicMock(name="LangfuseClient")
    lf.get_client.return_value = client
    lf.push_dataset.return_value = "summarizer-run_001"
    lf.flush_or_warn.return_value = True

    out_dir = tmp_path / "prompts" / "summarizer" / "runs" / "run_001"
    (out_dir / "v1").mkdir(parents=True)
    (out_dir / "v2").mkdir(parents=True)
    dataset = [{"scenario": "A", "prompt_inputs": {"x": "1"},
                "solution_criteria": ["c"], "task_description": "t"}]
    (out_dir / "dataset.json").write_text(json.dumps(dataset))
    (out_dir / "metadata.json").write_text(json.dumps({
        "run_id": "run_001", "prompt_name": "summarizer",
        "task": "t", "inputs_spec": {"x": "string"},
        "test_model": "haiku", "judge_model": "sonnet",
        "dataset_size": 1, "versions": ["v1", "v2"],
        "version_data": {"v1": {"avg_score": 7.0}, "v2": {"avg_score": 8.0}},
    }))
    output = [{"test_case": dataset[0], "output": "o", "score": 8, "reasoning": "r"}]
    (out_dir / "v1" / "output.json").write_text(json.dumps(output))
    (out_dir / "v2" / "output.json").write_text(json.dumps(output))

    _do_push(out_dir=out_dir, prompt_name="summarizer", version=None)

    # Dataset pushed once
    lf.push_dataset.assert_called_once()
    # push_run_case called once per case per version → 1 case × 2 versions
    assert lf.push_run_case.call_count == 2
    versions = sorted(c.kwargs["version"] for c in lf.push_run_case.call_args_list)
    assert versions == ["v1", "v2"]


@patch("prompt_eval.run.langfuse_push")
def test_push_targeted_version_only(lf, tmp_path, monkeypatch):
    for k in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"):
        monkeypatch.setenv(k, "x")
    lf.is_configured.return_value = True
    lf.get_client.return_value = MagicMock()
    lf.push_dataset.return_value = "summarizer-run_001"
    lf.flush_or_warn.return_value = True

    out_dir = tmp_path / "prompts" / "summarizer" / "runs" / "run_001"
    (out_dir / "v1").mkdir(parents=True)
    (out_dir / "v2").mkdir(parents=True)
    dataset = [{"scenario": "A", "prompt_inputs": {"x": "1"},
                "solution_criteria": ["c"], "task_description": "t"}]
    (out_dir / "dataset.json").write_text(json.dumps(dataset))
    (out_dir / "metadata.json").write_text(json.dumps({
        "run_id": "run_001", "prompt_name": "summarizer",
        "task": "t", "inputs_spec": {"x": "string"},
        "test_model": "haiku", "judge_model": "sonnet",
        "dataset_size": 1, "versions": ["v1", "v2"],
        "version_data": {},
    }))
    output = [{"test_case": dataset[0], "output": "o", "score": 8, "reasoning": "r"}]
    (out_dir / "v1" / "output.json").write_text(json.dumps(output))
    (out_dir / "v2" / "output.json").write_text(json.dumps(output))

    _do_push(out_dir=out_dir, prompt_name="summarizer", version="v2")

    # Only v2 pushed
    assert lf.push_run_case.call_count == 1
    assert lf.push_run_case.call_args.kwargs["version"] == "v2"


@patch("prompt_eval.run.langfuse_push")
def test_push_errors_when_version_not_found(lf, tmp_path, monkeypatch, capsys):
    for k in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"):
        monkeypatch.setenv(k, "x")
    lf.is_configured.return_value = True
    lf.get_client.return_value = MagicMock()
    lf.push_dataset.return_value = "summarizer-run_001"

    out_dir = tmp_path / "prompts" / "summarizer" / "runs" / "run_001"
    (out_dir / "v1").mkdir(parents=True)
    (out_dir / "dataset.json").write_text("[]")
    (out_dir / "metadata.json").write_text(json.dumps({
        "run_id": "run_001", "prompt_name": "summarizer",
        "task": "t", "inputs_spec": {},
        "test_model": "haiku", "judge_model": "sonnet",
        "dataset_size": 0, "versions": ["v1"], "version_data": {},
    }))

    with pytest.raises(SystemExit):
        _do_push(out_dir=out_dir, prompt_name="summarizer", version="v9")
    err = capsys.readouterr().err
    assert "v9" in err
    assert "v1" in err  # available versions listed
