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
