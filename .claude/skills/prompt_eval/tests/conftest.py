"""Shared pytest fixtures for prompt_eval tests."""
import pytest


@pytest.fixture
def tmp_run_dir(tmp_path):
    """Create a temp run_NNN directory with v1 subdir."""
    run_dir = tmp_path / "run_001"
    (run_dir / "v1").mkdir(parents=True)
    return run_dir
