"""Pages are written under docs/prompts/<prompt>/runs/<run_id>/."""
import json
import yaml

from prompt_eval.docs_generator import regenerate_for_run


def _seed_run(run_dir, run_id):
    (run_dir / "v1").mkdir(parents=True)
    (run_dir / "v1" / "prompt.txt").write_text("prompt v1")
    (run_dir / "v1" / "output.json").write_text(json.dumps([
        {"test_case": {"scenario": "S1", "solution_criteria": []},
         "output": "x", "score": 8, "reasoning": "ok"},
    ]))
    (run_dir / "metadata.json").write_text(json.dumps({
        "run_id": run_id, "test_model": "haiku", "judge_model": "sonnet",
        "versions": ["v1"],
    }))


def test_regenerate_writes_pages_under_prompt_namespace(tmp_path):
    run_dir = tmp_path / "prompts" / "summarizer" / "runs" / "run_001"
    _seed_run(run_dir, "run_001")

    docs_root = tmp_path / "docs-site" / "docs"
    (docs_root).mkdir(parents=True)
    cfg = tmp_path / "docs-site" / "mkdocs.yml"
    cfg.write_text(yaml.safe_dump({"site_name": "x", "nav": [{"Home": "index.md"}]}))

    regenerate_for_run(
        run_dir=run_dir, docs_root=docs_root, mkdocs_yml=cfg,
        prompt_name="summarizer",
    )

    out = docs_root / "prompts" / "summarizer" / "runs" / "run_001"
    assert (out / "index.md").exists()
    assert (out / "v1.md").exists()
    # No comparison page yet (single version)
    assert not (out / "comparison.md").exists()


from prompt_eval.docs_generator import update_mkdocs_nav


def _read_nav(cfg_path):
    return yaml.safe_load(cfg_path.read_text())["nav"]


def test_nav_creates_prompts_section_and_groups_under_prompt(tmp_path):
    cfg = tmp_path / "mkdocs.yml"
    cfg.write_text(yaml.safe_dump({"nav": [{"Home": "index.md"}]}))

    update_mkdocs_nav(cfg, prompt_name="summarizer", run_id="run_001",
                      version_labels=["v1", "v2"])

    nav = _read_nav(cfg)
    prompts_entry = next(item for item in nav if "Prompts" in item)
    summarizer = next(item for item in prompts_entry["Prompts"] if "summarizer" in item)
    runs = summarizer["summarizer"]
    assert any("run_001" in entry for entry in runs)

    run_001_pages = next(entry["run_001"] for entry in runs if "run_001" in entry)
    titles = [list(p.keys())[0] for p in run_001_pages]
    assert titles == ["Summary", "Comparison", "v1", "v2"]


def test_nav_replaces_existing_run_in_place(tmp_path):
    cfg = tmp_path / "mkdocs.yml"
    cfg.write_text(yaml.safe_dump({"nav": [{"Home": "index.md"}]}))

    update_mkdocs_nav(cfg, prompt_name="summarizer", run_id="run_001",
                      version_labels=["v1"])
    update_mkdocs_nav(cfg, prompt_name="summarizer", run_id="run_001",
                      version_labels=["v1", "v2"])

    nav = _read_nav(cfg)
    summarizer = next(p for p in next(i for i in nav if "Prompts" in i)["Prompts"]
                      if "summarizer" in p)["summarizer"]
    # exactly one run_001 entry, with the v2-included page list
    run_001_entries = [e for e in summarizer if "run_001" in e]
    assert len(run_001_entries) == 1
    titles = [list(p.keys())[0] for p in run_001_entries[0]["run_001"]]
    assert "Comparison" in titles and "v2" in titles


def test_nav_keeps_separate_prompts_separate(tmp_path):
    cfg = tmp_path / "mkdocs.yml"
    cfg.write_text(yaml.safe_dump({"nav": [{"Home": "index.md"}]}))

    update_mkdocs_nav(cfg, prompt_name="summarizer", run_id="run_001",
                      version_labels=["v1"])
    update_mkdocs_nav(cfg, prompt_name="code_reviewer", run_id="run_001",
                      version_labels=["v1"])

    prompts = next(i for i in _read_nav(cfg) if "Prompts" in i)["Prompts"]
    names = [list(p.keys())[0] for p in prompts]
    assert "summarizer" in names and "code_reviewer" in names
