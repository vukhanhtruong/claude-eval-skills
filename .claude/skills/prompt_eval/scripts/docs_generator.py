"""Generate MkDocs Material pages from runs/ data."""
import json
from statistics import mean


# Front matter that tells the Material theme to hide the right-hand TOC sidebar
# on generated pages. Reclaims horizontal reading space; users navigate via the
# left sidebar instead. Applied to summary, version, and comparison pages.
_HIDE_TOC_FRONT_MATTER = "---\nhide:\n  - toc\n---\n\n"

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

    return f"""{_HIDE_TOC_FRONT_MATTER}# Version {version_label}

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


import difflib
from pathlib import Path
import yaml
from statistics import mean as _mean  # already imported as mean above


def render_comparison_page(run_id: str, versions: list) -> str:
    """Render the comparison page: summary cards, score matrix, tabbed prompts/diffs."""
    labels = [v["label"] for v in versions]
    avg_by_version = {
        v["label"]: _mean([r["score"] for r in v["results"]]) if v["results"] else 0
        for v in versions
    }

    summary_cells = " | ".join(
        f"**{lbl}** {avg_by_version[lbl]:.1f}/10" for lbl in labels
    )

    # Score matrix
    scenarios = []
    if versions and versions[0]["results"]:
        scenarios = [r["test_case"]["scenario"] for r in versions[0]["results"]]

    matrix_header = "| Scenario | " + " | ".join(labels) + " | Δ |"
    matrix_sep = "|" + "|".join(["---"] * (len(labels) + 2)) + "|"
    matrix_rows = []
    for i, scenario in enumerate(scenarios):
        scores = [v["results"][i]["score"] for v in versions]
        cells = [score_badge(s) for s in scores]
        delta = scores[-1] - scores[0]
        delta_str = f"+{delta} ↑" if delta > 0 else (f"{delta} ↓" if delta < 0 else "0")
        matrix_rows.append(f"| {scenario} | " + " | ".join(cells) + f" | {delta_str} |")

    # Tabbed prompts
    tabs = []
    for v in versions:
        tabs.append(f'=== "{v["label"]}"\n\n    ```text\n    {_indent(v["prompt"])}\n    ```\n')
    # Diff tabs between consecutive versions
    for i in range(1, len(versions)):
        prev, curr = versions[i - 1], versions[i]
        diff = "\n".join(difflib.unified_diff(
            prev["prompt"].splitlines(),
            curr["prompt"].splitlines(),
            lineterm="",
            fromfile=prev["label"],
            tofile=curr["label"],
        ))
        tabs.append(
            f'=== "{prev["label"]} → {curr["label"]} diff"\n\n'
            f"    ```diff\n    {_indent(diff)}\n    ```\n"
        )

    tabs_block = "\n".join(tabs)

    return f"""{_HIDE_TOC_FRONT_MATTER}# Run {run_id} — Comparison

{summary_cells}

## Score matrix

{matrix_header}
{matrix_sep}
""" + "\n".join(matrix_rows) + f"""

## Prompts

{tabs_block}
"""


def _indent(text: str, n: int = 4) -> str:
    pad = " " * n
    return ("\n" + pad).join(text.splitlines())


def update_mkdocs_nav(
    config_path: Path,
    run_id: str,
    version_labels: list,
) -> None:
    """Insert/replace the run's section under nav.Runs in mkdocs.yml."""
    config_path = Path(config_path)
    cfg = yaml.safe_load(config_path.read_text())
    nav = cfg.setdefault("nav", [])

    # Find or create the Runs entry
    runs_entry = next((item for item in nav if isinstance(item, dict) and "Runs" in item), None)
    if runs_entry is None:
        runs_entry = {"Runs": []}
        nav.append(runs_entry)

    # Build the run pages list
    pages = [{"Summary": f"runs/{run_id}/index.md"}]
    if len(version_labels) >= 2:
        pages.append({"Comparison": f"runs/{run_id}/comparison.md"})
    for label in version_labels:
        pages.append({label: f"runs/{run_id}/{label}.md"})

    # Replace or append this run's entry
    runs_list = runs_entry["Runs"]
    for i, item in enumerate(runs_list):
        if isinstance(item, dict) and run_id in item:
            runs_list[i] = {run_id: pages}
            break
    else:
        runs_list.append({run_id: pages})

    config_path.write_text(yaml.safe_dump(cfg, sort_keys=False))


def render_summary_page(run_id: str, metadata: dict, versions: list) -> str:
    """Render the per-run summary (links to versions, models used, dataset link)."""
    rows = []
    for v in versions:
        scores = [r["score"] for r in v["results"]]
        avg = _mean(scores) if scores else 0
        rows.append(f"| [{v['label']}]({v['label']}.md) | {avg:.1f}/10 | {len(scores)} |")
    table = "\n".join(rows)

    return f"""{_HIDE_TOC_FRONT_MATTER}# Run {run_id} — Summary

**Test model:** `{metadata.get('test_model', '?')}`  &nbsp;
**Judge model:** `{metadata.get('judge_model', '?')}`

| Version | Average | Cases |
|---|---|---|
{table}

[View full comparison](comparison.md){{: .md-button }}
"""


def regenerate_for_run(run_dir, docs_root, mkdocs_yml) -> None:
    """Read run_dir/{metadata,outputs}, write Markdown to docs_root, update nav."""
    from pathlib import Path as _Path
    run_dir = _Path(run_dir)
    docs_root = _Path(docs_root)

    metadata = json.loads((run_dir / "metadata.json").read_text())
    run_id = metadata.get("run_id") or run_dir.name
    version_labels = metadata.get("versions", [])

    versions = []
    for label in version_labels:
        prompt_text = (run_dir / label / "prompt.txt").read_text()
        results = json.loads((run_dir / label / "output.json").read_text())
        versions.append({"label": label, "prompt": prompt_text, "results": results})

    out_dir = docs_root / "runs" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # Summary
    (out_dir / "index.md").write_text(render_summary_page(run_id, metadata, versions))

    # Per-version pages
    for v in versions:
        page = render_version_page(v["label"], v["prompt"], v["results"])
        (out_dir / f"{v['label']}.md").write_text(page)

    # Comparison (only if 2+ versions)
    if len(versions) >= 2:
        (out_dir / "comparison.md").write_text(
            render_comparison_page(run_id, versions)
        )

    update_mkdocs_nav(mkdocs_yml, run_id, version_labels)
