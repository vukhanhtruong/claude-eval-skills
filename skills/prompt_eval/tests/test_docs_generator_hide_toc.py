"""Regression: every generated page must hide the right-hand TOC sidebar
to maximize reading space. The Material theme honours `hide: [toc]` in
YAML front matter."""
from prompt_eval.docs_generator import (
    render_version_page,
    render_comparison_page,
    render_summary_page,
)


def _assert_hides_toc(md: str) -> None:
    head = md.split("\n\n", 1)[0]
    assert head.startswith("---\nhide:\n  - toc\n---"), (
        f"page must start with `hide: [toc]` front matter, got head:\n{head!r}"
    )


def test_version_page_hides_toc():
    md = render_version_page(
        version_label="v1",
        prompt_text="Summarize: {{text}}",
        results=[{
            "test_case": {"scenario": "S1"},
            "output": "ok",
            "score": 8,
            "reasoning": "good",
        }],
    )
    _assert_hides_toc(md)


def test_summary_page_hides_toc():
    versions = [
        {"label": "v1", "prompt": "p", "results": [
            {"test_case": {"scenario": "S1"}, "output": "ok", "score": 7, "reasoning": "r"},
        ]},
    ]
    md = render_summary_page("run_001", {"test_model": "haiku", "judge_model": "sonnet"}, versions)
    _assert_hides_toc(md)


def test_comparison_page_hides_toc():
    versions = [
        {"label": "v1", "prompt": "p1", "results": [
            {"test_case": {"scenario": "S1"}, "output": "a", "score": 6, "reasoning": "r1"},
        ]},
        {"label": "v2", "prompt": "p2", "results": [
            {"test_case": {"scenario": "S1"}, "output": "b", "score": 8, "reasoning": "r2"},
        ]},
    ]
    md = render_comparison_page("run_001", versions)
    _assert_hides_toc(md)
