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


def _format_scenario(scenario: str) -> str:
    """Format scenario JSON as readable key-value lines."""
    try:
        data = json.loads(scenario) if isinstance(scenario, str) else scenario
        if isinstance(data, dict):
            lines = [f"**{k}:** {v}" for k, v in data.items()]
            return "<br>".join(lines)
        return str(data)
    except (json.JSONDecodeError, TypeError):
        return scenario


def _scenario_title(scenario: str) -> str:
    """Extract a short title from scenario for anchor text."""
    try:
        data = json.loads(scenario) if isinstance(scenario, str) else scenario
        if isinstance(data, dict):
            return data.get("title", data.get("id", "Case"))[:50]
        return str(data)[:50]
    except (json.JSONDecodeError, TypeError):
        return scenario[:50]


def _render_criteria_breakdown(breakdown: dict) -> str:
    """Render criteria breakdown dict as compact inline text."""
    if not breakdown:
        return ""
    parts = [f"{k}: {v}" for k, v in breakdown.items()]
    return "<br>".join(parts)


def render_version_page(version_label: str, prompt_text: str, results: list) -> str:
    """Render one version's Markdown page (prompt + per-case results table)."""
    scores = [r["score"] for r in results]
    avg = mean(scores) if scores else 0
    pass_rate = (
        100 * len([s for s in scores if s >= 7]) / len(scores) if scores else 0
    )
    rows = []
    has_breakdown = any(r.get("criteria_breakdown") for r in results)
    header = "| Scenario | Score | Reasoning | Criteria |" if has_breakdown else "| Scenario | Score | Reasoning |"
    sep = "|---|---|---|---|" if has_breakdown else "|---|---|---|"
    for i, r in enumerate(results):
        scenario_fmt = _format_scenario(r['test_case']['scenario'])
        output_link = f'<a href="#output-{i+1}">▶ output</a>'
        breakdown_cell = (
            f" {_render_criteria_breakdown(r.get('criteria_breakdown', {}))} |"
            if has_breakdown else ""
        )
        rows.append(
            f"| {scenario_fmt}<br>{output_link} | {score_badge(r['score'])} | "
            f"{r['reasoning']} |{breakdown_cell}"
        )

    table = "\n".join(rows)

    # Outputs section with anchors
    outputs = []
    for i, r in enumerate(results):
        title = _scenario_title(r['test_case']['scenario'])
        outputs.append(
            f'<h4 id="output-{i+1}">{i+1}. {title}</h4>\n\n'
            f'```text\n{r["output"]}\n```\n'
        )
    outputs_section = "\n".join(outputs)

    return f"""{_HIDE_TOC_FRONT_MATTER}# Version {version_label}

**Average:** {score_badge(round(avg))} {avg:.1f}/10  &nbsp;
**Pass rate (≥7):** {pass_rate:.0f}%

## Prompt

```text
{prompt_text}
```

## Per-case results

{header}
{sep}
{table}

## Outputs

{outputs_section}
"""




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
    prompt_name: str,
    run_id: str,
    version_labels: list,
) -> None:
    """Insert/replace one run's section under nav.Prompts.<prompt_name>.<run_id>."""
    config_path = Path(config_path)
    cfg = yaml.safe_load(config_path.read_text())
    nav = cfg.setdefault("nav", [])

    # Find or create the top-level Prompts entry
    prompts_entry = next(
        (item for item in nav if isinstance(item, dict) and "Prompts" in item),
        None,
    )
    if prompts_entry is None:
        prompts_entry = {"Prompts": []}
        nav.append(prompts_entry)

    # Find or create the per-prompt entry within Prompts
    prompts_list = prompts_entry["Prompts"]
    prompt_entry = next(
        (item for item in prompts_list if isinstance(item, dict) and prompt_name in item),
        None,
    )
    if prompt_entry is None:
        prompt_entry = {prompt_name: []}
        prompts_list.append(prompt_entry)

    # Build this run's page list
    base = f"prompts/{prompt_name}/runs/{run_id}"
    pages = [{"Summary": f"{base}/index.md"}]
    if len(version_labels) >= 2:
        pages.append({"Comparison": f"{base}/comparison.md"})
    for label in version_labels:
        pages.append({label: f"{base}/{label}.md"})

    # Replace or append this run's entry within the per-prompt list
    runs_list = prompt_entry[prompt_name]
    for i, item in enumerate(runs_list):
        if isinstance(item, dict) and run_id in item:
            runs_list[i] = {run_id: pages}
            break
    else:
        runs_list.append({run_id: pages})

    config_path.write_text(yaml.safe_dump(cfg, sort_keys=False))


def _crossval_banner(metadata: dict) -> str:
    cv = metadata.get("cross_validation_of")
    if not cv:
        return ""
    src_run, src_ver = cv["run_id"], cv["version"]
    return (
        f"> ← **Cross-validation of** [{src_run}/{src_ver}]"
        f"(../{src_run}/{src_ver}.md)\n\n"
    )


def _crossval_footer(cross_validations: list | None) -> str:
    if not cross_validations:
        return ""
    items = "\n".join(
        f"- [{cv['run_id']}](../{cv['run_id']}/index.md) "
        f"— `test={cv.get('test_model', '?')}, judge={cv.get('judge_model', '?')}`"
        for cv in cross_validations
    )
    return f"\n\n---\n**Cross-validations:**\n\n{items}\n"


def render_summary_page(
    run_id: str,
    metadata: dict,
    versions: list,
    cross_validations: list | None = None,
) -> str:
    """Render the per-run summary (links to versions, models used, dataset link)."""
    rows = []
    for v in versions:
        scores = [r["score"] for r in v["results"]]
        avg = _mean(scores) if scores else 0
        rows.append(f"| [{v['label']}]({v['label']}.md) | {avg:.1f}/10 | {len(scores)} |")
    table = "\n".join(rows)
    banner = _crossval_banner(metadata)
    footer = _crossval_footer(cross_validations)

    body = f"""{_HIDE_TOC_FRONT_MATTER}# Run {run_id} — Summary

{banner}**Test model:** `{metadata.get('test_model', '?')}`  &nbsp;
**Judge model:** `{metadata.get('judge_model', '?')}`

| Version | Average | Cases |
|---|---|---|
{table}

[View full comparison](comparison.md){{: .md-button }}
"""
    return body + footer


def _load_version_results(version_dir) -> list:
    """Load per-case results for one version directory.

    Supports two layouts:
    - New (scores.json + output.json): merges scores and outputs by case_index.
    - Legacy (output.json only): returns the combined records as-is.
    """
    from pathlib import Path as _Path
    version_dir = _Path(version_dir)
    scores_path = version_dir / "scores.json"
    output_path = version_dir / "output.json"

    if scores_path.exists():
        scores_data = json.loads(scores_path.read_text())
        cases = scores_data.get("cases", scores_data) if isinstance(scores_data, dict) else scores_data
        outputs_by_index = {}
        if output_path.exists():
            outputs = json.loads(output_path.read_text())
            for o in outputs:
                outputs_by_index[o.get("case_index", 0)] = o.get("output", "")
        results = []
        for i, case in enumerate(cases):
            results.append({
                "test_case": {"scenario": case.get("scenario", "")},
                "score": case["score"],
                "reasoning": case["reasoning"],
                "criteria_breakdown": case.get("criteria_breakdown", {}),
                "output": outputs_by_index.get(case.get("case_index", i), ""),
            })
        return results

    # Legacy: output.json contains combined records.
    # Returns [] for an unevaluated version (e.g. a freshly cloned run that
    # has prompt.txt but no output.json yet).
    if not output_path.exists():
        return []
    return json.loads(output_path.read_text())


def _find_cross_validations(run_dir: Path) -> list[dict]:
    """Return metadata for sibling runs whose cross_validation_of points at run_dir."""
    runs_dir = run_dir.parent
    this_run_id = run_dir.name
    siblings = []
    for sib in sorted(runs_dir.iterdir()):
        if not sib.is_dir() or sib == run_dir:
            continue
        meta_path = sib / "metadata.json"
        if not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text())
        cv = meta.get("cross_validation_of")
        if cv and cv.get("run_id") == this_run_id:
            siblings.append(meta)
    return siblings


def regenerate_for_run(run_dir, docs_root, mkdocs_yml, prompt_name: str) -> None:
    """Read run_dir/{metadata,outputs}, write Markdown to docs_root, update nav.

    Pages go to ``<docs_root>/prompts/<prompt_name>/runs/<run_id>/``. Nav is
    nested under ``Prompts > <prompt_name> > <run_id>``.
    """
    from pathlib import Path as _Path
    run_dir = _Path(run_dir)
    docs_root = _Path(docs_root)

    metadata = json.loads((run_dir / "metadata.json").read_text())
    run_id = metadata.get("run_id") or run_dir.name
    version_labels = metadata.get("versions", [])

    versions = []
    for label in version_labels:
        prompt_text = (run_dir / label / "prompt.txt").read_text()
        results = _load_version_results(run_dir / label)
        versions.append({"label": label, "prompt": prompt_text, "results": results})

    out_dir = docs_root / "prompts" / prompt_name / "runs" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # Summary
    cross_validations = _find_cross_validations(run_dir)
    (out_dir / "index.md").write_text(
        render_summary_page(run_id, metadata, versions, cross_validations)
    )

    # Per-version pages
    for v in versions:
        page = render_version_page(v["label"], v["prompt"], v["results"])
        (out_dir / f"{v['label']}.md").write_text(page)

    # Comparison (only if 2+ versions)
    if len(versions) >= 2:
        (out_dir / "comparison.md").write_text(
            render_comparison_page(run_id, versions)
        )

    update_mkdocs_nav(mkdocs_yml, prompt_name, run_id, version_labels)
