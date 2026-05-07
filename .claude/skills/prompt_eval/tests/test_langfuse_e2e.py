"""End-to-end test: push synthetic data to a real Langfuse instance.

Skipped by default. Run with `pytest -m e2e` AND with LANGFUSE_* env vars set.
"""
import os
import time
import pytest

from prompt_eval import langfuse_push


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not langfuse_push.is_configured(),
        reason="Langfuse env vars not set",
    ),
]


def test_round_trip_push_dataset_and_run():
    """Push a synthetic dataset + one trace + one score, then flush."""
    client = langfuse_push.get_client()
    assert client is not None

    # Use a unique run_id to avoid colliding with prior test runs
    run_id = f"pytest-{int(time.time())}"
    dataset = [
        {
            "scenario": "smoke test",
            "prompt_inputs": {"x": "hello"},
            "solution_criteria": ["mentions hello"],
            "task_description": "echo input",
        }
    ]

    name = langfuse_push.push_dataset(
        client=client,
        prompt_name="pytest_smoke",
        run_id=run_id,
        dataset=dataset,
        task_description="echo input",
        inputs_spec={"x": "string"},
    )
    assert name == f"pytest_smoke-{run_id}"

    langfuse_push.push_run_case(
        client=client,
        dataset_name=name,
        item_index=0,
        run_id=run_id,
        version="v1",
        prompt_name="pytest_smoke",
        rendered_prompt="echo: hello",
        output="hello",
        score=8,
        reasoning="echoed correctly",
        model="claude-haiku-4-5",
        latency_ms=42,
    )

    assert langfuse_push.flush_or_warn(client) is True
