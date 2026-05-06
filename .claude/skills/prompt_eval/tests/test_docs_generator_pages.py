"""Tests for score-badge HTML and per-version page generation."""
from prompt_eval.docs_generator import score_badge, render_version_page


def test_score_badge_green_for_high_scores():
    html = score_badge(9)
    assert "#c8e6c9" in html
    assert ">9<" in html


def test_score_badge_yellow_for_mid_scores():
    html = score_badge(6)
    assert "#fff9c4" in html


def test_score_badge_red_for_low_scores():
    html = score_badge(3)
    assert "#ffcdd2" in html


def test_render_version_page_includes_prompt_and_table():
    output_data = [
        {
            "test_case": {"scenario": "S1", "solution_criteria": ["c"]},
            "output": "out 1",
            "score": 8,
            "reasoning": "good",
        },
        {
            "test_case": {"scenario": "S2", "solution_criteria": ["c"]},
            "output": "out 2",
            "score": 4,
            "reasoning": "bad",
        },
    ]
    md = render_version_page(
        version_label="v1",
        prompt_text="You are an assistant.\nDo the task.",
        results=output_data,
    )

    assert "# Version v1" in md
    assert "**Average:**" in md
    assert "6.0" in md  # avg of 8 and 4
    assert "S1" in md and "S2" in md
    assert "You are an assistant." in md
    assert "#c8e6c9" in md  # green badge for 8
    assert "#ffcdd2" in md  # red badge for 4
