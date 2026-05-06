"""Tests for comparison page rendering and mkdocs.yml nav updates."""
import yaml
from prompt_eval.docs_generator import (
    render_comparison_page,
    update_mkdocs_nav,
)


def test_comparison_page_shows_score_matrix():
    versions = [
        {
            "label": "v1",
            "prompt": "v1 prompt",
            "results": [
                {"test_case": {"scenario": "S1"}, "score": 5},
                {"test_case": {"scenario": "S2"}, "score": 7},
            ],
        },
        {
            "label": "v2",
            "prompt": "v2 prompt",
            "results": [
                {"test_case": {"scenario": "S1"}, "score": 8},
                {"test_case": {"scenario": "S2"}, "score": 9},
            ],
        },
    ]
    md = render_comparison_page(run_id="run_001", versions=versions)
    assert "S1" in md and "S2" in md
    assert "v1" in md and "v2" in md
    assert "+3" in md or "+2" in md  # delta column


def test_comparison_page_includes_tabbed_prompts():
    versions = [
        {"label": "v1", "prompt": "first", "results": []},
        {"label": "v2", "prompt": "second", "results": []},
    ]
    md = render_comparison_page("run_001", versions)
    assert '=== "v1"' in md
    assert '=== "v2"' in md
    assert '=== "v1 → v2 diff"' in md
    assert "```diff" in md


def test_update_mkdocs_nav_adds_run_section(tmp_path):
    cfg = tmp_path / "mkdocs.yml"
    cfg.write_text(yaml.safe_dump({
        "site_name": "Prompt Eval Reports",
        "nav": [{"Home": "index.md"}],
    }))

    update_mkdocs_nav(
        cfg,
        prompt_name="default",
        run_id="run_001",
        version_labels=["v1", "v2"],
    )

    parsed = yaml.safe_load(cfg.read_text())
    nav = parsed["nav"]
    prompts_entry = next(item for item in nav if "Prompts" in item)
    default = next(p for p in prompts_entry["Prompts"] if "default" in p)["default"]
    run_001 = next(r for r in default if "run_001" in r)
    pages = run_001["run_001"]
    titles = [list(p.keys())[0] for p in pages]
    assert "Summary" in titles
    assert "Comparison" in titles
    assert "v1" in titles
    assert "v2" in titles
