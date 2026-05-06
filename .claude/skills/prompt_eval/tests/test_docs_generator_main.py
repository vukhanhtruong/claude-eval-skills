"""Tests for regenerate_for_run end-to-end Markdown generation."""
import json
import yaml
from prompt_eval.docs_generator import regenerate_for_run


def test_regenerate_for_run_writes_all_pages(tmp_path):
    # Arrange a runs/run_001 layout
    run_dir = tmp_path / "runs" / "run_001"
    (run_dir / "v1").mkdir(parents=True)
    (run_dir / "v2").mkdir(parents=True)
    (run_dir / "v1" / "prompt.txt").write_text("prompt v1")
    (run_dir / "v2" / "prompt.txt").write_text("prompt v2")
    (run_dir / "v1" / "output.json").write_text(json.dumps([
        {"test_case": {"scenario": "A", "solution_criteria": []}, "output": "x", "score": 6, "reasoning": "ok"},
    ]))
    (run_dir / "v2" / "output.json").write_text(json.dumps([
        {"test_case": {"scenario": "A", "solution_criteria": []}, "output": "y", "score": 9, "reasoning": "great"},
    ]))
    (run_dir / "metadata.json").write_text(json.dumps({
        "run_id": "run_001",
        "test_model": "haiku",
        "judge_model": "sonnet",
        "versions": ["v1", "v2"],
    }))

    docs_root = tmp_path / "docs-site" / "docs"
    (docs_root / "runs").mkdir(parents=True)
    cfg = tmp_path / "docs-site" / "mkdocs.yml"
    cfg.write_text(yaml.safe_dump({
        "site_name": "Prompt Eval Reports",
        "nav": [{"Home": "index.md"}],
    }))

    # Act
    regenerate_for_run(run_dir=run_dir, docs_root=docs_root, mkdocs_yml=cfg, prompt_name="default")

    # Assert pages exist
    out = docs_root / "prompts" / "default" / "runs" / "run_001"
    assert (out / "index.md").exists()
    assert (out / "comparison.md").exists()
    assert (out / "v1.md").exists()
    assert (out / "v2.md").exists()

    # mkdocs.yml updated
    nav = yaml.safe_load(cfg.read_text())["nav"]
    prompts_entry = next(item["Prompts"] for item in nav if "Prompts" in item)
    default = next(item["default"] for item in prompts_entry if "default" in item)
    assert any("run_001" in entry for entry in default)


def test_regenerate_for_run_skips_comparison_with_one_version(tmp_path):
    run_dir = tmp_path / "runs" / "run_002"
    (run_dir / "v1").mkdir(parents=True)
    (run_dir / "v1" / "prompt.txt").write_text("solo prompt")
    (run_dir / "v1" / "output.json").write_text(json.dumps([
        {"test_case": {"scenario": "A", "solution_criteria": []}, "output": "x", "score": 7, "reasoning": "ok"},
    ]))
    (run_dir / "metadata.json").write_text(json.dumps({
        "run_id": "run_002",
        "test_model": "haiku",
        "judge_model": "sonnet",
        "versions": ["v1"],
    }))

    docs_root = tmp_path / "docs-site" / "docs"
    (docs_root / "runs").mkdir(parents=True)
    cfg = tmp_path / "docs-site" / "mkdocs.yml"
    cfg.write_text(yaml.safe_dump({"site_name": "x", "nav": []}))

    regenerate_for_run(run_dir=run_dir, docs_root=docs_root, mkdocs_yml=cfg, prompt_name="default")

    out = docs_root / "prompts" / "default" / "runs" / "run_002"
    assert (out / "index.md").exists()
    assert (out / "v1.md").exists()
    assert not (out / "comparison.md").exists()
