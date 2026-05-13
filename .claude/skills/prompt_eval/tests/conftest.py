"""Shared pytest fixtures for prompt_eval tests."""
import sys
import types
from unittest.mock import MagicMock, patch
import pytest

# Stub out optional heavy dependencies that are not installed in the dev venv.
# These modules are only needed at runtime (evaluate/generate commands); unit
# tests for the other CLI commands should not require them.
def _stub_module(name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod

for _name in ("anthropic", "deepeval", "deepeval.metrics", "deepeval.test_case",
              "deepeval.models", "langfuse"):
    if _name not in sys.modules:
        _m = _stub_module(_name)
        # Provide the specific names imported by the source modules.
        _m.Anthropic = MagicMock
        _m.GEval = MagicMock
        _m.LLMTestCase = MagicMock
        _m.LLMTestCaseParams = MagicMock
        _m.DeepEvalBaseLLM = MagicMock
        _m.Langfuse = MagicMock


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
