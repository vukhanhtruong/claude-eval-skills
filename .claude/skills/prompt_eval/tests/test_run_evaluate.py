"""Tests for the evaluate subcommand."""
import json
from unittest.mock import patch, MagicMock
from prompt_eval.run import _do_evaluate


@patch("prompt_eval.run.regenerate_for_run")
@patch("prompt_eval.run.restart_mkdocs")
@patch("prompt_eval.run._bootstrap_docs_site")
@patch("prompt_eval.run.Evaluator")
def test_evaluate_writes_outputs_and_updates_metadata(
    eval_cls, mock_bootstrap, start_mkdocs, regen, tmp_path, monkeypatch
):
    monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
    # Set up out_dir with dataset + v1 prompt + initial metadata
    out_dir = tmp_path / "prompts" / "summarizer" / "runs" / "run_001"
    (out_dir / "v1").mkdir(parents=True)
    (out_dir / "dataset.json").write_text(json.dumps([
        {"scenario": "A", "prompt_inputs": {"x": "1"}, "solution_criteria": ["c"], "task_description": "t"},
    ]))
    (out_dir / "v1" / "prompt.txt").write_text("Test prompt {x}")
    (out_dir / "metadata.json").write_text(json.dumps({
        "run_id": "run_001",
        "prompt_name": "summarizer",
        "test_model": "haiku",
        "judge_model": None,
        "dataset_size": 1,
        "versions": [],
        "version_data": {},
    }))

    evaluator = eval_cls.return_value
    evaluator.run_evaluation.return_value = [
        {"test_case": {"scenario": "A", "solution_criteria": ["c"]}, "output": "x", "score": 8, "reasoning": "ok"},
    ]

    _do_evaluate(
        version="v1", model="haiku", judge_model="sonnet",
        out_dir=out_dir, extra_criteria=None,
        prompt_name="summarizer",
    )

    # output.json written
    assert (out_dir / "v1" / "output.json").exists()

    # metadata updated
    meta = json.loads((out_dir / "metadata.json").read_text())
    assert meta["versions"] == ["v1"]
    assert meta["judge_model"] == "sonnet"
    assert meta["latest_avg_score"] == 8.0
    assert meta["version_data"]["v1"]["avg_score"] == 8.0

    # docs regen + mkdocs autostart called
    regen.assert_called_once()
    assert regen.call_args.kwargs["prompt_name"] == "summarizer"
    start_mkdocs.assert_called_once()


@patch("prompt_eval.run.regenerate_for_run")
@patch("prompt_eval.run.restart_mkdocs")
@patch("prompt_eval.run._bootstrap_docs_site")
@patch("prompt_eval.run.Evaluator")
def test_evaluate_warns_when_judge_model_changes(
    eval_cls, mock_bootstrap, start_mkdocs, regen, tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
    out_dir = tmp_path / "prompts" / "summarizer" / "runs" / "run_001"
    (out_dir / "v2").mkdir(parents=True)
    (out_dir / "dataset.json").write_text(json.dumps([
        {"scenario": "A", "prompt_inputs": {}, "solution_criteria": ["c"], "task_description": "t"},
    ]))
    (out_dir / "v2" / "prompt.txt").write_text("p")
    (out_dir / "metadata.json").write_text(json.dumps({
        "run_id": "run_001", "prompt_name": "summarizer",
        "test_model": "haiku", "judge_model": "sonnet",
        "dataset_size": 1, "versions": ["v1"], "version_data": {"v1": {"avg_score": 5.0}},
    }))
    eval_cls.return_value.run_evaluation.return_value = [
        {"test_case": {"scenario": "A", "solution_criteria": []}, "output": "x", "score": 7, "reasoning": "ok"},
    ]

    _do_evaluate(
        version="v2", model="haiku", judge_model="haiku",  # different from sonnet
        out_dir=out_dir, extra_criteria=None,
        prompt_name="summarizer",
    )
    out = capsys.readouterr().out
    assert "originally evaluated with judge_model=sonnet" in out.lower() or "warning" in out.lower()


import pytest
from prompt_eval.run import _build_parser, _do_evaluate


def test_evaluate_parser_accepts_push_to_langfuse_flag():
    parser = _build_parser()
    args = parser.parse_args([
        "evaluate", "--prompt", "summarizer",
        "--run-id", "run_001", "--version", "v1",
        "--push-to-langfuse",
    ])
    assert args.push_to_langfuse is True


def test_evaluate_parser_push_to_langfuse_defaults_false():
    parser = _build_parser()
    args = parser.parse_args([
        "evaluate", "--prompt", "summarizer",
        "--run-id", "run_001", "--version", "v1",
    ])
    assert args.push_to_langfuse is False


@patch("prompt_eval.run.regenerate_for_run")
@patch("prompt_eval.run.restart_mkdocs")
@patch("prompt_eval.run._bootstrap_docs_site")
@patch("prompt_eval.run.Evaluator")
def test_evaluate_fast_fails_when_push_set_but_creds_missing(
    eval_cls, mock_bootstrap, start_mkdocs, regen, tmp_path, monkeypatch, capsys
):
    for k in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))

    out_dir = tmp_path / "prompts" / "summarizer" / "runs" / "run_001"
    (out_dir / "v1").mkdir(parents=True)
    (out_dir / "dataset.json").write_text("[]")
    (out_dir / "v1" / "prompt.txt").write_text("p")
    (out_dir / "metadata.json").write_text(json.dumps({
        "run_id": "run_001", "prompt_name": "summarizer",
        "test_model": "haiku", "judge_model": None,
        "dataset_size": 0, "versions": [], "version_data": {},
    }))

    with pytest.raises(SystemExit) as exc:
        _do_evaluate(
            version="v1", model="haiku", judge_model="sonnet",
            out_dir=out_dir, extra_criteria=None,
            prompt_name="summarizer",
            push_to_langfuse=True,
        )
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "LANGFUSE_PUBLIC_KEY" in err
    # Critically: evaluator was NEVER instantiated — no LLM calls happened
    eval_cls.assert_not_called()


@patch("prompt_eval.run.regenerate_for_run")
@patch("prompt_eval.run.restart_mkdocs")
@patch("prompt_eval.run._bootstrap_docs_site")
@patch("prompt_eval.run.langfuse_push")
@patch("prompt_eval.run.Evaluator")
def test_evaluate_with_push_calls_push_dataset_callback_and_flush(
    eval_cls, lf, mock_bootstrap, start_mkdocs, regen,
    tmp_path, monkeypatch
):
    for k in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"):
        monkeypatch.setenv(k, "x")
    monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))

    out_dir = tmp_path / "prompts" / "summarizer" / "runs" / "run_001"
    (out_dir / "v1").mkdir(parents=True)
    dataset = [{"scenario": "A", "prompt_inputs": {"x": "1"},
                "solution_criteria": ["c"], "task_description": "t"}]
    (out_dir / "dataset.json").write_text(json.dumps(dataset))
    (out_dir / "v1" / "prompt.txt").write_text("p {x}")
    (out_dir / "metadata.json").write_text(json.dumps({
        "run_id": "run_001", "prompt_name": "summarizer",
        "task": "t", "inputs_spec": {"x": "string"},
        "test_model": "haiku", "judge_model": None,
        "dataset_size": 1, "versions": [], "version_data": {},
    }))

    # Configure langfuse_push module mock
    lf.is_configured.return_value = True
    lf.REQUIRED_ENV = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST")
    client = MagicMock(name="LangfuseClient")
    lf.get_client.return_value = client
    lf.push_dataset.return_value = "summarizer-run_001"
    lf.flush_or_warn.return_value = True

    # When the evaluator runs, simulate it invoking the callback once
    def fake_run_evaluation(*args, **kwargs):
        cb = kwargs["on_case_complete"]
        cb(0, dataset[0], "p 1", "out", 8, "good", 1234)
        return [{"test_case": dataset[0], "output": "out",
                 "score": 8, "reasoning": "good"}]

    eval_cls.return_value.run_evaluation.side_effect = fake_run_evaluation

    _do_evaluate(
        version="v1", model="haiku", judge_model="sonnet",
        out_dir=out_dir, extra_criteria=None,
        prompt_name="summarizer",
        push_to_langfuse=True,
    )

    # Dataset push: called with prompt name, run id, dataset, task, inputs_spec
    lf.push_dataset.assert_called_once()
    pd_kwargs = lf.push_dataset.call_args.kwargs
    assert pd_kwargs["prompt_name"] == "summarizer"
    assert pd_kwargs["run_id"] == "run_001"
    assert pd_kwargs["task_description"] == "t"
    assert pd_kwargs["inputs_spec"] == {"x": "string"}

    # Per-case push: called once for the single case
    lf.push_run_case.assert_called_once()
    rc_kwargs = lf.push_run_case.call_args.kwargs
    assert rc_kwargs["item_index"] == 0
    assert rc_kwargs["version"] == "v1"
    assert rc_kwargs["prompt_name"] == "summarizer"
    assert rc_kwargs["run_id"] == "run_001"
    assert rc_kwargs["score"] == 8
    assert rc_kwargs["model"] == "claude-haiku-4-5"

    # Flush called at the end
    lf.flush_or_warn.assert_called_once_with(client)


@patch("prompt_eval.run.regenerate_for_run")
@patch("prompt_eval.run.restart_mkdocs")
@patch("prompt_eval.run._bootstrap_docs_site")
@patch("prompt_eval.run.langfuse_push")
@patch("prompt_eval.run.Evaluator")
def test_evaluate_without_push_does_not_touch_langfuse(
    eval_cls, lf, mock_bootstrap, start_mkdocs, regen,
    tmp_path, monkeypatch
):
    monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
    out_dir = tmp_path / "prompts" / "summarizer" / "runs" / "run_001"
    (out_dir / "v1").mkdir(parents=True)
    (out_dir / "dataset.json").write_text(json.dumps([
        {"scenario": "A", "prompt_inputs": {"x": "1"},
         "solution_criteria": ["c"], "task_description": "t"},
    ]))
    (out_dir / "v1" / "prompt.txt").write_text("p")
    (out_dir / "metadata.json").write_text(json.dumps({
        "run_id": "run_001", "prompt_name": "summarizer",
        "test_model": "haiku", "judge_model": None,
        "dataset_size": 1, "versions": [], "version_data": {},
    }))
    eval_cls.return_value.run_evaluation.return_value = [
        {"test_case": {"scenario": "A", "solution_criteria": ["c"]},
         "output": "x", "score": 8, "reasoning": "ok"},
    ]

    _do_evaluate(
        version="v1", model="haiku", judge_model="sonnet",
        out_dir=out_dir, extra_criteria=None,
        prompt_name="summarizer",
        push_to_langfuse=False,
    )

    lf.get_client.assert_not_called()
    lf.push_dataset.assert_not_called()
    lf.push_run_case.assert_not_called()
    lf.flush_or_warn.assert_not_called()
