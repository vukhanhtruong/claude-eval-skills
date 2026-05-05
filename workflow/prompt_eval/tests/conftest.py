"""Shared pytest fixtures for prompt_eval tests."""
import json
from unittest.mock import MagicMock, patch
import pytest


@pytest.fixture
def mock_anthropic_response():
    """Build a mock Anthropic API response with given text content."""
    def _make(text: str):
        msg = MagicMock()
        msg.content = [MagicMock(text=text)]
        return msg
    return _make


@pytest.fixture
def mock_anthropic_client(mock_anthropic_response):
    """Patch anthropic.Anthropic to return canned responses."""
    with patch("anthropic.Anthropic") as cls:
        client = MagicMock()
        client.messages.create.return_value = mock_anthropic_response("dummy")
        cls.return_value = client
        yield client


@pytest.fixture
def sample_test_case():
    """A representative test case dict (matches DatasetGenerator output)."""
    return {
        "task_description": "Write a one-day meal plan",
        "scenario": "Vegan endurance runner",
        "prompt_inputs": {
            "height": "175",
            "weight": "65",
            "goal": "marathon training",
            "restrictions": "vegan",
        },
        "solution_criteria": [
            "Includes daily caloric total",
            "Lists portion sizes in grams",
            "Excludes all animal products",
        ],
    }


@pytest.fixture
def tmp_run_dir(tmp_path):
    """Create a temp run_NNN directory with v1 subdir."""
    run_dir = tmp_path / "run_001"
    (run_dir / "v1").mkdir(parents=True)
    return run_dir
