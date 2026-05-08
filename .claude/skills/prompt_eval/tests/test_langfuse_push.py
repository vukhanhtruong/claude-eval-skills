"""Unit tests for the langfuse_push module (all SDK calls mocked)."""
from unittest.mock import patch, MagicMock
import pytest

from prompt_eval import langfuse_push


def test_is_configured_true_when_all_three_env_vars_set(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    monkeypatch.setenv("LANGFUSE_HOST", "https://example")
    assert langfuse_push.is_configured() is True


def test_is_configured_false_when_any_env_var_missing(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    monkeypatch.setenv("LANGFUSE_HOST", "https://example")
    assert langfuse_push.is_configured() is False


def test_is_configured_false_when_env_var_empty(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    monkeypatch.setenv("LANGFUSE_HOST", "https://example")
    assert langfuse_push.is_configured() is False


def test_get_client_returns_none_when_not_configured(monkeypatch):
    for k in langfuse_push.REQUIRED_ENV:
        monkeypatch.delenv(k, raising=False)
    assert langfuse_push.get_client() is None


def test_get_client_returns_langfuse_instance_when_configured(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    monkeypatch.setenv("LANGFUSE_HOST", "https://example")
    sentinel = MagicMock(name="LangfuseClient")
    with patch("prompt_eval.langfuse_push.Langfuse", return_value=sentinel) as ctor:
        client = langfuse_push.get_client()
    assert client is sentinel
    ctor.assert_called_once_with()  # SDK auto-reads env vars


@pytest.fixture
def sample_dataset():
    return [
        {
            "scenario": "scenario A",
            "prompt_inputs": {"x": "1"},
            "solution_criteria": ["c1", "c2"],
            "task_description": "task t",
        },
        {
            "scenario": "scenario B",
            "prompt_inputs": {"x": "2"},
            "solution_criteria": ["c3"],
            "task_description": "task t",
        },
    ]


def test_push_dataset_creates_dataset_and_items_when_absent(sample_dataset, capsys):
    client = MagicMock(name="LangfuseClient")
    # Simulate "dataset does not exist": get_dataset raises
    client.get_dataset.side_effect = Exception("not found")

    name = langfuse_push.push_dataset(
        client=client,
        prompt_name="summarizer",
        run_id="run_001",
        dataset=sample_dataset,
        task_description="task t",
        inputs_spec={"x": "string"},
    )

    assert name == "summarizer-run_001"
    client.create_dataset.assert_called_once()
    create_kwargs = client.create_dataset.call_args.kwargs
    assert create_kwargs["name"] == "summarizer-run_001"
    assert create_kwargs["description"] == "task t"
    assert create_kwargs["metadata"]["prompt_name"] == "summarizer"
    assert create_kwargs["metadata"]["run_id"] == "run_001"
    assert create_kwargs["metadata"]["dataset_size"] == 2
    assert create_kwargs["metadata"]["inputs_spec"] == {"x": "string"}

    # Two items, deterministic IDs
    item_calls = client.create_dataset_item.call_args_list
    assert len(item_calls) == 2
    ids = [c.kwargs["id"] for c in item_calls]
    assert ids == ["summarizer-run_001-item-0", "summarizer-run_001-item-1"]
    assert item_calls[0].kwargs["dataset_name"] == "summarizer-run_001"
    assert item_calls[0].kwargs["input"] == {"x": "1"}
    assert item_calls[0].kwargs["expected_output"] == ["c1", "c2"]
    assert item_calls[0].kwargs["metadata"]["scenario"] == "scenario A"

    # No warning printed on first create
    out = capsys.readouterr().out
    assert "exists in Langfuse" not in out


def test_push_dataset_upserts_and_warns_when_present(sample_dataset, capsys):
    client = MagicMock(name="LangfuseClient")
    # Simulate "dataset exists": get_dataset returns truthy
    client.get_dataset.return_value = MagicMock(name="ExistingDataset")

    name = langfuse_push.push_dataset(
        client=client,
        prompt_name="summarizer",
        run_id="run_001",
        dataset=sample_dataset,
        task_description="task t",
        inputs_spec={"x": "string"},
    )

    assert name == "summarizer-run_001"
    client.create_dataset.assert_not_called()  # already exists
    # Items still pushed (upsert by deterministic ID)
    assert client.create_dataset_item.call_count == 2

    out = capsys.readouterr().out
    assert "exists in Langfuse" in out
    assert "summarizer-run_001" in out


def test_push_run_case_creates_span_score_and_dataset_run_item():
    client = MagicMock(name="LangfuseClient")

    # client.get_dataset(name) → DatasetClient with .items containing one item
    # whose deterministic id matches what push_run_case computes for index 0.
    item_obj = MagicMock(name="DatasetItem")
    item_obj.id = "summarizer-run_001-item-0"
    item_obj.dataset_id = "ds-uuid"
    dataset_obj = MagicMock(name="DatasetClient")
    dataset_obj.items = [item_obj]
    client.get_dataset.return_value = dataset_obj

    # start_as_current_observation returns a context manager whose __enter__
    # yields a span with .trace_id and .id attributes.
    span = MagicMock(name="Span")
    span.trace_id = "trace-uuid"
    span.id = "obs-uuid"
    span_ctx = MagicMock()
    span_ctx.__enter__ = MagicMock(return_value=span)
    span_ctx.__exit__ = MagicMock(return_value=None)
    client.start_as_current_observation.return_value = span_ctx

    langfuse_push.push_run_case(
        client=client,
        dataset_name="summarizer-run_001",
        item_index=0,
        run_id="run_001",
        version="v1",
        prompt_name="summarizer",
        rendered_prompt="Summarize: hello world",
        output="hello world summary",
        score=8,
        reasoning="meets all criteria",
        model="claude-haiku-4-5",
        latency_ms=1234,
    )

    # 1. Span created with input, output, metadata, name
    client.start_as_current_observation.assert_called_once()
    span_kwargs = client.start_as_current_observation.call_args.kwargs
    assert span_kwargs["input"] == "Summarize: hello world"
    assert span_kwargs["output"] == "hello world summary"
    assert span_kwargs["metadata"]["model"] == "claude-haiku-4-5"
    assert span_kwargs["metadata"]["latency_ms"] == 1234
    assert span_kwargs["metadata"]["version"] == "v1"
    assert span_kwargs["metadata"]["raw_score"] == 8
    assert "summarizer/run_001/v1" in span_kwargs["name"]

    # 2. Dataset run item created — links trace to dataset run and lazily
    #    creates the run by run_name on first call.
    client.api.dataset_run_items.create.assert_called_once()
    dri_kwargs = client.api.dataset_run_items.create.call_args.kwargs
    assert dri_kwargs["run_name"] == "v1"
    assert dri_kwargs["dataset_item_id"] == "summarizer-run_001-item-0"
    assert dri_kwargs["trace_id"] == "trace-uuid"
    assert dri_kwargs["observation_id"] == "obs-uuid"
    assert dri_kwargs["run_description"] == "test_model=claude-haiku-4-5"
    assert dri_kwargs["metadata"]["prompt_name"] == "summarizer"
    assert dri_kwargs["metadata"]["run_id"] == "run_001"
    assert dri_kwargs["metadata"]["version"] == "v1"
    assert dri_kwargs["metadata"]["test_model"] == "claude-haiku-4-5"

    # 3. Score created and attached to trace, value normalized to 0..1
    client.create_score.assert_called_once()
    sc_kwargs = client.create_score.call_args.kwargs
    assert sc_kwargs["name"] == "Task Quality"
    assert sc_kwargs["value"] == pytest.approx(0.8)
    assert sc_kwargs["trace_id"] == "trace-uuid"
    assert sc_kwargs["comment"] == "meets all criteria"
    assert sc_kwargs["data_type"] == "NUMERIC"


def test_push_run_case_raises_when_dataset_item_not_found():
    client = MagicMock(name="LangfuseClient")
    dataset_obj = MagicMock(name="DatasetClient")
    dataset_obj.items = []  # no items
    client.get_dataset.return_value = dataset_obj

    with pytest.raises(ValueError, match="not found"):
        langfuse_push.push_run_case(
            client=client,
            dataset_name="summarizer-run_001",
            item_index=0,
            run_id="run_001",
            version="v1",
            prompt_name="summarizer",
            rendered_prompt="x",
            output="y",
            score=5,
            reasoning="r",
            model="m",
            latency_ms=1,
        )


def test_flush_or_warn_returns_true_on_success(capsys):
    client = MagicMock(name="LangfuseClient")
    assert langfuse_push.flush_or_warn(client) is True
    client.flush.assert_called_once()
    assert "flush failed" not in capsys.readouterr().out


def test_flush_or_warn_returns_false_and_warns_on_exception(capsys):
    client = MagicMock(name="LangfuseClient")
    client.flush.side_effect = ConnectionError("boom")
    assert langfuse_push.flush_or_warn(client) is False
    out = capsys.readouterr().out
    assert "Langfuse flush failed" in out
    assert "boom" in out


def test_is_configured_accepts_base_url_alias(monkeypatch):
    """LANGFUSE_BASE_URL satisfies the host requirement (Langfuse SDK convention)."""
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://example")
    assert langfuse_push.is_configured() is True


def test_is_configured_false_when_neither_host_nor_base_url(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)
    monkeypatch.delenv("LANGFUSE_BASE_URL", raising=False)
    assert langfuse_push.is_configured() is False


def test_missing_env_vars_treats_host_and_base_url_as_one_slot(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)
    monkeypatch.delenv("LANGFUSE_BASE_URL", raising=False)
    missing = langfuse_push.missing_env_vars()
    assert "LANGFUSE_PUBLIC_KEY" in missing
    assert "LANGFUSE_SECRET_KEY" not in missing
    assert any("HOST" in m and "BASE_URL" in m for m in missing)


def test_missing_env_vars_empty_when_base_url_satisfies_host(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://example")
    assert langfuse_push.missing_env_vars() == []
