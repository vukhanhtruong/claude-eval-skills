"""One-shot migration of legacy flat `runs/` layout into `prompts/default/runs/`."""
import json
from pathlib import Path
import yaml

from prompt_eval.run import _migrate_legacy_layout


def _seed_legacy(artifact_root):
    """Build the pre-multi-prompt layout under artifact_root."""
    runs = artifact_root / "runs" / "run_001"
    (runs / "v1").mkdir(parents=True)
    (runs / "v1" / "prompt.txt").write_text("p")
    (runs / "metadata.json").write_text(json.dumps({
        "run_id": "run_001", "versions": ["v1"], "dataset_size": 3,
        "test_model": "haiku", "judge_model": "sonnet", "latest_avg_score": 7.5,
    }))

    docs = artifact_root / "docs-site" / "docs"
    docs.mkdir(parents=True)
    (docs / "runs" / "run_001").mkdir(parents=True)
    (docs / "runs" / "run_001" / "index.md").write_text("# legacy summary")

    cfg = artifact_root / "docs-site" / "mkdocs.yml"
    cfg.write_text(yaml.safe_dump({
        "site_name": "x",
        "nav": [
            {"Home": "index.md"},
            {"Runs": [{"run_001": [{"Summary": "runs/run_001/index.md"}]}]},
        ],
    }))


def test_migrate_moves_runs_and_stamps_prompt_name(tmp_path, capsys):
    root = tmp_path / "prompt_eval_runs"
    _seed_legacy(root)

    moved = _migrate_legacy_layout(root)

    assert moved is True
    # Old paths gone
    assert not (root / "runs").exists()
    # New layout
    new_run = root / "prompts" / "default" / "runs" / "run_001"
    assert new_run.exists()
    meta = json.loads((new_run / "metadata.json").read_text())
    assert meta["prompt_name"] == "default"
    # Docs migrated
    assert (root / "docs-site" / "docs" / "prompts" / "default" / "runs" / "run_001" / "index.md").exists()
    assert not (root / "docs-site" / "docs" / "runs").exists()
    # Nav rewritten
    cfg = yaml.safe_load((root / "docs-site" / "mkdocs.yml").read_text())
    assert any("Prompts" in item for item in cfg["nav"])
    assert not any("Runs" in item for item in cfg["nav"])
    # Announces what it did
    assert "default" in capsys.readouterr().out.lower()


def test_migrate_is_noop_when_prompts_dir_already_exists(tmp_path):
    root = tmp_path / "prompt_eval_runs"
    _seed_legacy(root)
    (root / "prompts").mkdir()  # someone already on new layout

    moved = _migrate_legacy_layout(root)

    assert moved is False
    # Legacy paths untouched
    assert (root / "runs" / "run_001").exists()


def test_migrate_is_noop_when_no_legacy_runs(tmp_path):
    root = tmp_path / "prompt_eval_runs"
    root.mkdir()

    moved = _migrate_legacy_layout(root)

    assert moved is False


def test_migrate_handles_existing_prompt_name_in_metadata(tmp_path):
    """A re-stamped metadata file (e.g. user manually re-ran migration) keeps
    its existing prompt_name; we only fill it in when missing."""
    root = tmp_path / "prompt_eval_runs"
    _seed_legacy(root)
    meta_path = root / "runs" / "run_001" / "metadata.json"
    meta = json.loads(meta_path.read_text())
    meta["prompt_name"] = "summarizer"  # already stamped
    meta_path.write_text(json.dumps(meta))

    _migrate_legacy_layout(root)

    new_meta = json.loads(
        (root / "prompts" / "default" / "runs" / "run_001" / "metadata.json").read_text()
    )
    assert new_meta["prompt_name"] == "summarizer"
