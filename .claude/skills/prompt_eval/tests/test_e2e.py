"""End-to-end test: generate → evaluate → docs. Hits the real Anthropic API."""
import json
import os
from pathlib import Path
import pytest
from prompt_eval.run import _do_generate, _do_evaluate


@pytest.mark.e2e
@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="No API key")
def test_full_pipeline_end_to_end(tmp_path):
    out_dir = tmp_path / "runs" / "run_001"
    out_dir.mkdir(parents=True)

    # Generate 1 case to keep it cheap
    _do_generate(
        task="Write a one-sentence haiku-style summary of an input topic",
        inputs_json='{"topic":"a topic to summarize"}',
        num_cases=1,
        model="haiku",
        out_dir=out_dir,
    )
    dataset = json.loads((out_dir / "dataset.json").read_text())
    assert len(dataset) == 1

    # Build a v1 prompt
    (out_dir / "v1").mkdir()
    (out_dir / "v1" / "prompt.txt").write_text(
        "Write a one-sentence summary of: {topic}"
    )

    # Stub docs/mkdocs side effects via env (or just let them no-op outside the package dir)
    # The auto-mkdocs helper checks port; if 8000 is free, it spawns. That's fine.

    _do_evaluate(
        version="v1",
        model="haiku",
        judge_model="haiku",  # haiku for speed
        out_dir=out_dir,
        extra_criteria=None,
    )

    assert (out_dir / "v1" / "output.json").exists()
    output = json.loads((out_dir / "v1" / "output.json").read_text())
    assert len(output) == 1
    assert 1 <= output[0]["score"] <= 10
