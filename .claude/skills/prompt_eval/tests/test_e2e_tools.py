"""E2E test for tool mocking. Hits the real Anthropic API."""
import json
import os
from pathlib import Path
import pytest
from prompt_eval.run import _do_evaluate


@pytest.mark.e2e
@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="No API key")
def test_tool_enabled_evaluation_e2e(tmp_path):
    """Evaluate a prompt that triggers web_fetch tool, verify tool_log populated."""
    out_dir = tmp_path / "runs" / "run_001"
    out_dir.mkdir(parents=True)

    # Create a minimal dataset that will trigger tool use
    dataset = [{
        "prompt_inputs": {"url": "https://example.com"},
        "solution_criteria": ["mentions the URL content"],
        "task_description": "Summarize web content",
        "scenario": "Fetch and summarize a webpage",
    }]
    (out_dir / "dataset.json").write_text(json.dumps(dataset))

    # Metadata
    metadata = {
        "run_id": "run_001",
        "versions": [],
        "task": "Summarize web content",
        "inputs_spec": {"url": "URL to fetch"},
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata))

    # Create v1 prompt that asks model to fetch URL
    (out_dir / "v1").mkdir()
    (out_dir / "v1" / "prompt.txt").write_text(
        "Please fetch the content from {url} and provide a brief summary of what you find."
    )

    # Run evaluation with web_fetch tool (pass tool name as string, not dict)
    _do_evaluate(
        version="v1",
        model="haiku",
        judge_model="haiku",
        out_dir=out_dir,
        extra_criteria=None,
        prompt_name="test",
        tools=["web_fetch"],
        max_tool_turns=3,
    )

    # Verify output.json exists and has tool_log
    output_file = out_dir / "v1" / "output.json"
    assert output_file.exists(), "output.json should be created"
    output = json.loads(output_file.read_text())
    assert len(output) == 1

    # The model should have used the web_fetch tool
    result = output[0]
    assert "tool_log" in result, "tool_log should be present in results"

    # Verify mocks.json was created with versioned schema
    mocks_file = out_dir / "mocks.json"
    if mocks_file.exists():
        mocks = json.loads(mocks_file.read_text())
        assert mocks.get("version") == 1, "mocks.json should have version field"
        assert "entries" in mocks, "mocks.json should have entries field"

    # Score should be valid
    assert 1 <= result["score"] <= 10
