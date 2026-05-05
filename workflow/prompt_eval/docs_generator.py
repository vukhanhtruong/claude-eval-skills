"""Generate MkDocs Material pages from runs/ data."""
from statistics import mean


_BADGE_STYLE = (
    "background:{bg};color:{fg};padding:5px 10px;"
    "border-radius:3px;font-weight:bold"
)


def score_badge(score: int) -> str:
    """Return inline-HTML span for a 1-10 score, color-coded like the notebook report."""
    if score >= 8:
        bg, fg = "#c8e6c9", "#2e7d32"
    elif score <= 4:
        bg, fg = "#ffcdd2", "#c62828"
    else:
        bg, fg = "#fff9c4", "#f57f17"
    style = _BADGE_STYLE.format(bg=bg, fg=fg)
    return f'<span style="{style}">{score}</span>'


def render_version_page(version_label: str, prompt_text: str, results: list) -> str:
    """Render one version's Markdown page (prompt + per-case results table)."""
    scores = [r["score"] for r in results]
    avg = mean(scores) if scores else 0
    pass_rate = (
        100 * len([s for s in scores if s >= 7]) / len(scores) if scores else 0
    )
    rows = []
    for r in results:
        rows.append(
            f"| {r['test_case']['scenario']} | {score_badge(r['score'])} | "
            f"{r['reasoning']} |"
        )

    table = "\n".join(rows)

    return f"""# Version {version_label}

**Average:** {score_badge(round(avg))} {avg:.1f}/10  &nbsp;
**Pass rate (≥7):** {pass_rate:.0f}%

## Prompt

```text
{prompt_text}
```

## Per-case results

| Scenario | Score | Reasoning |
|---|---|---|
{table}

## Outputs

{_render_outputs(results)}
"""


def _render_outputs(results: list) -> str:
    blocks = []
    for r in results:
        scenario = r["test_case"]["scenario"]
        blocks.append(f"### {scenario}\n\n```text\n{r['output']}\n```\n")
    return "\n".join(blocks)
