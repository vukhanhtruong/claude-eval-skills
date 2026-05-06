"""CLI entry point for /prompt_eval skill."""
import argparse
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from statistics import mean

# Telemetry opt-out before any deepeval import
os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "1")

from prompt_eval.evaluator import MODEL_MAP, DatasetGenerator, Evaluator
from prompt_eval.docs_generator import regenerate_for_run


MKDOCS_PORT = 8000


def _resolve_artifact_root() -> Path:
    """Return `<project_dir>/prompt_eval_runs/`.

    Priority for `<project_dir>`:
    1. ``$PROMPT_EVAL_PROJECT_DIR`` (explicit override)
    2. ``$CLAUDE_PROJECT_DIR`` (set by Claude Code on skill invocation)
    3. current working directory
    """
    project_dir = (
        os.environ.get("PROMPT_EVAL_PROJECT_DIR")
        or os.environ.get("CLAUDE_PROJECT_DIR")
        or os.getcwd()
    )
    return Path(project_dir) / "prompt_eval_runs"


_PROMPT_NAME_RE = re.compile(r"^[a-z0-9_-]+$")


def _validate_prompt_name(name: str) -> None:
    """Reject prompt names that aren't filesystem- and URL-safe.

    Allowed: lowercase letters, digits, underscore, hyphen. 1-64 chars.
    Restrictive on purpose so paths don't need escaping anywhere.
    """
    if not isinstance(name, str) or not (1 <= len(name) <= 64) or not _PROMPT_NAME_RE.match(name):
        raise ValueError(
            f"prompt name must match [a-z0-9_-]+ and be 1-64 chars; got {name!r}"
        )


def _resolve_prompts_dir() -> Path:
    """Return ``<artifact_root>/prompts/`` (the parent of all prompt namespaces)."""
    return _resolve_artifact_root() / "prompts"


def _resolve_runs_dir(prompt_name: str) -> Path:
    """Return ``<artifact_root>/prompts/<prompt_name>/runs/``. Validates name."""
    _validate_prompt_name(prompt_name)
    return _resolve_prompts_dir() / prompt_name / "runs"


def _migrate_legacy_layout(artifact_root: Path) -> bool:
    """Move legacy ``runs/`` and ``docs-site/docs/runs/`` into the new
    ``prompts/default/`` namespace. Returns True if anything moved.

    Only runs when ``runs/`` exists AND ``prompts/`` does not. Anything
    else is a no-op so we never clobber a partially-migrated tree.
    """
    artifact_root = Path(artifact_root)
    legacy_runs = artifact_root / "runs"
    new_prompts = artifact_root / "prompts"

    if not legacy_runs.exists() or new_prompts.exists():
        return False

    # 1. Move the runs/ directory under prompts/default/runs/
    target_runs = new_prompts / "default" / "runs"
    target_runs.parent.mkdir(parents=True, exist_ok=True)
    legacy_runs.rename(target_runs)

    # 2. Stamp prompt_name="default" into each run's metadata if missing
    for run_dir in target_runs.iterdir():
        if not run_dir.is_dir():
            continue
        meta_path = run_dir / "metadata.json"
        if not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text())
        meta.setdefault("prompt_name", "default")
        meta_path.write_text(json.dumps(meta, indent=2))

    # 3. Move docs-site pages: docs/runs/ -> docs/prompts/default/runs/
    docs_runs = artifact_root / "docs-site" / "docs" / "runs"
    if docs_runs.exists():
        target_docs_runs = artifact_root / "docs-site" / "docs" / "prompts" / "default" / "runs"
        target_docs_runs.parent.mkdir(parents=True, exist_ok=True)
        docs_runs.rename(target_docs_runs)

    # 4. Rewrite mkdocs.yml nav: replace top-level "Runs" with nested
    #    "Prompts > default > <run_id>" structure
    cfg_path = artifact_root / "docs-site" / "mkdocs.yml"
    if cfg_path.exists():
        import yaml as _yaml  # local import to avoid widening top-of-file imports
        cfg = _yaml.safe_load(cfg_path.read_text())
        nav = cfg.get("nav", [])
        new_nav = []
        legacy_runs_entries = []
        for item in nav:
            if isinstance(item, dict) and "Runs" in item:
                legacy_runs_entries = item["Runs"]  # list of {run_id: [pages]}
            else:
                new_nav.append(item)
        if legacy_runs_entries:
            # Rewrite each page path: runs/<id>/X.md -> prompts/default/runs/<id>/X.md
            rewritten = []
            for run_dict in legacy_runs_entries:
                # run_dict looks like {"run_001": [{"Summary": "runs/run_001/index.md"}, ...]}
                for run_id, pages in run_dict.items():
                    new_pages = []
                    for page in pages:
                        for title, path in page.items():
                            new_pages.append({
                                title: path.replace(
                                    f"runs/{run_id}/",
                                    f"prompts/default/runs/{run_id}/",
                                    1,
                                ),
                            })
                    rewritten.append({run_id: new_pages})
            new_nav.append({"Prompts": [{"default": rewritten}]})
        cfg["nav"] = new_nav
        cfg_path.write_text(_yaml.safe_dump(cfg, sort_keys=False))

    print(f"Migrated legacy runs/ to prompts/default/")
    return True


def _bootstrap_docs_site(target: Path) -> None:
    """Copy the bundled docs-site template to `target` if `target/mkdocs.yml` doesn't exist.

    Runs once per project — first time the user evaluates a prompt. After that, the per-project
    docs-site is the source of truth (the user can theme it, add nav entries, etc.).
    """
    if (target / "mkdocs.yml").exists():
        return
    template_dir = Path(__file__).parent / "docs-site-template"
    target.mkdir(parents=True, exist_ok=True)
    # Copy contents (not the template_dir itself).
    for item in template_dir.iterdir():
        dest = target / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def _kill_mkdocs() -> None:
    """Send SIGTERM to any 'mkdocs serve' processes. Best-effort.

    We use ``pgrep -f 'mkdocs serve'`` instead of port-based discovery so we
    only kill our own processes, not whatever else might be on port 8000.
    """
    try:
        out = subprocess.check_output(
            ["pgrep", "-f", "mkdocs serve"],
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return  # nothing to kill, or no pgrep on PATH

    for raw in out.decode().split():
        try:
            os.kill(int(raw), signal.SIGTERM)
        except (ProcessLookupError, ValueError):
            pass

    # Wait up to 2s for the OS to release the port
    for _ in range(20):
        if not _port_in_use(MKDOCS_PORT):
            return
        time.sleep(0.1)


def _start_mkdocs_background(docs_site_dir: Path) -> None:
    log_path = docs_site_dir / "mkdocs.log"
    subprocess.Popen(
        ["uv", "run", "mkdocs", "serve", "--dev-addr", f"127.0.0.1:{MKDOCS_PORT}"],
        cwd=docs_site_dir,
        stdout=open(log_path, "ab"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    print(f"mkdocs serve at http://127.0.0.1:{MKDOCS_PORT}  (log: {log_path})")


def restart_mkdocs(docs_site_dir: Path) -> None:
    """Stop any running ``mkdocs serve`` and start a fresh one.

    mkdocs serve's filesystem watcher silently misses files written to docs/
    after the server starts (mkdocs 1.6 + Material on Linux), so we restart
    it on every regeneration. Costs ~1 sec; cheap relative to the LLM calls
    that surround it.
    """
    if _port_in_use(MKDOCS_PORT):
        _kill_mkdocs()
    _start_mkdocs_background(docs_site_dir)


def list_runs(runs_dir: Path) -> None:
    runs_dir = Path(runs_dir)
    if not runs_dir.exists() or not any(runs_dir.iterdir()):
        print("No runs found.")
        return

    print("Available runs:")
    for run_path in sorted(runs_dir.iterdir()):
        if not run_path.is_dir():
            continue
        meta_file = run_path / "metadata.json"
        if not meta_file.exists():
            continue
        meta = json.loads(meta_file.read_text())
        versions = meta.get("versions", [])
        version_str = (
            f"{versions[0]}→{versions[-1]}" if len(versions) > 1 else
            (versions[0] if versions else "—")
        )
        avg = meta.get("latest_avg_score", 0)
        size = meta.get("dataset_size", "?")
        print(f"  {run_path.name}  {size} cases  {version_str}  avg {avg}")


def list_prompts(prompts_dir: Path) -> None:
    """Print each prompt namespace with its run count."""
    prompts_dir = Path(prompts_dir)
    if not prompts_dir.exists() or not any(prompts_dir.iterdir()):
        print("No prompts found.")
        return

    print("Available prompts:")
    for entry in sorted(prompts_dir.iterdir()):
        if not entry.is_dir():
            continue
        runs_dir = entry / "runs"
        if not runs_dir.exists():
            count = 0
        else:
            count = sum(
                1 for r in runs_dir.iterdir()
                if r.is_dir() and (r / "metadata.json").exists()
            )
        print(f"  {entry.name}  {count} runs")


def _do_generate(
    task: str, inputs_json: str, num_cases: int, model: str,
    out_dir: Path, prompt_name: str,
) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    inputs_spec = json.loads(inputs_json)
    sdk_model = MODEL_MAP[model]

    gen = DatasetGenerator(model=sdk_model)
    dataset_file = out_dir / "dataset.json"
    dataset = gen.generate_dataset(
        task_description=task,
        prompt_inputs_spec=inputs_spec,
        num_cases=num_cases,
        output_file=str(dataset_file),
    )
    if not dataset_file.exists():
        dataset_file.write_text(json.dumps(dataset, indent=2))

    meta_file = out_dir / "metadata.json"
    metadata = {
        "run_id": out_dir.name,
        "prompt_name": prompt_name,
        "task": task,
        "inputs_spec": inputs_spec,
        "test_model": model,
        "judge_model": None,  # filled on first evaluate
        "dataset_size": len(dataset),
        "versions": [],
        "version_data": {},
        "latest_avg_score": None,
    }
    meta_file.write_text(json.dumps(metadata, indent=2))
    print(f"Generated {len(dataset)} test cases at {out_dir / 'dataset.json'}")


def _do_evaluate(
    version: str, model: str, judge_model: str,
    out_dir: Path, extra_criteria: str | None,
    prompt_name: str,
    docs_site_dir: Path | None = None,
) -> None:
    out_dir = Path(out_dir)
    meta_file = out_dir / "metadata.json"
    metadata = json.loads(meta_file.read_text())

    # Warn if judge_model changes from prior runs
    prior_judge = metadata.get("judge_model")
    if prior_judge and prior_judge != judge_model:
        print(
            f"⚠ Warning: run_id was originally evaluated with judge_model={prior_judge}; "
            f"you passed judge_model={judge_model}. Cross-version comparability may suffer."
        )

    dataset = json.loads((out_dir / "dataset.json").read_text())
    prompt_template = (out_dir / version / "prompt.txt").read_text()

    evaluator = Evaluator(
        test_model=MODEL_MAP[model],
        judge_model=MODEL_MAP[judge_model],
    )
    results = evaluator.run_evaluation(
        dataset=dataset,
        prompt_template=prompt_template,
        output_file=str(out_dir / version / "output.json"),
        extra_criteria=extra_criteria,
    )

    # Ensure output.json is written (works for real + mocked run_evaluation).
    (out_dir / version / "output.json").write_text(json.dumps(results, indent=2))

    # Update metadata
    if version not in metadata["versions"]:
        metadata["versions"].append(version)
    metadata["judge_model"] = judge_model
    avg = mean(r["score"] for r in results)
    metadata.setdefault("version_data", {})[version] = {
        "avg_score": avg,
        "pass_rate": 100 * len([r for r in results if r["score"] >= 7]) / len(results),
    }
    metadata["latest_avg_score"] = round(avg, 1)
    meta_file.write_text(json.dumps(metadata, indent=2))

    # Regenerate docs site (bootstrap from template on first evaluate per project)
    if docs_site_dir is None:
        docs_site_dir = _resolve_artifact_root() / "docs-site"
    _bootstrap_docs_site(docs_site_dir)
    regenerate_for_run(
        run_dir=out_dir,
        docs_root=docs_site_dir / "docs",
        mkdocs_yml=docs_site_dir / "mkdocs.yml",
        prompt_name=prompt_name,
    )

    # mkdocs's file watcher silently misses post-startup writes; restart on each evaluate.
    restart_mkdocs(docs_site_dir)

    print(f"Evaluated {version}: average {avg:.1f}/10")


def _do_show(out_dir: Path, version: str, json_output: bool = False) -> None:
    """Print a scoreboard for one (run, version). With --json, emit structured
    JSON for programmatic consumption (Claude can parse it without re-reading
    output.json itself)."""
    output_file = out_dir / version / "output.json"
    if not output_file.exists():
        print(f"No results at {output_file}", file=sys.stderr)
        sys.exit(1)

    results = json.loads(output_file.read_text())
    cases = []
    for r in results:
        sc = r["test_case"].get("scenario", "")
        scenario = sc.get("title", str(sc)) if isinstance(sc, dict) else str(sc)
        cases.append({
            "scenario": scenario,
            "score": r["score"],
            "output_length": len(r["output"]),
            "reasoning": r["reasoning"],
        })

    scores = [c["score"] for c in cases]
    avg = round(sum(scores) / len(scores), 1) if scores else 0.0
    pass_rate = round(100 * len([s for s in scores if s >= 7]) / len(scores), 1) if scores else 0.0

    summary = {
        "run_id": out_dir.name,
        "version": version,
        "average_score": avg,
        "pass_rate": pass_rate,
        "cases": cases,
    }

    if json_output:
        print(json.dumps(summary, indent=2))
        return

    print(f"Run: {summary['run_id']}  Version: {version}")
    print(f"Average: {avg}/10  Pass rate: {pass_rate}%")
    print()
    for i, c in enumerate(cases, 1):
        print(f"=== Case {i}: {c['scenario']}")
        print(f"  Score: {c['score']}/10")
        print(f"  Output length: {c['output_length']} chars")
        print(f"  Reasoning: {c['reasoning']}")
        print()


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="prompt-eval")
    sub = p.add_subparsers(dest="cmd", required=True)

    lr = sub.add_parser("list-runs", help="List existing runs for one prompt")
    lr.add_argument("--prompt", required=True, help="prompt name, e.g. summarizer")

    sub.add_parser("list-prompts", help="List all prompt namespaces with run counts")

    g = sub.add_parser("generate", help="Generate dataset")
    g.add_argument("--task", required=True)
    g.add_argument("--inputs", required=True, help="JSON dict of input specs")
    g.add_argument("--num-cases", type=int, default=3)
    g.add_argument("--model", default="haiku", choices=["haiku", "sonnet", "opus"])
    g.add_argument("--run-id", required=True, help="e.g. run_001")
    g.add_argument("--prompt", required=True, help="prompt name, e.g. summarizer")

    e = sub.add_parser("evaluate", help="Run + grade a prompt version")
    e.add_argument("--version", required=True, help="e.g. v1, v2")
    e.add_argument("--model", default="haiku", choices=["haiku", "sonnet", "opus"])
    e.add_argument("--judge-model", default="sonnet", choices=["haiku", "sonnet", "opus"])
    e.add_argument("--run-id", required=True, help="e.g. run_001")
    e.add_argument("--extra-criteria", default=None)
    e.add_argument("--prompt", required=True, help="prompt name, e.g. summarizer")

    s = sub.add_parser("show", help="Print scoreboard for one (run, version)")
    s.add_argument("--run-id", required=True, help="e.g. run_001")
    s.add_argument("--version", required=True, help="e.g. v1, v2")
    s.add_argument("--json", action="store_true", help="Emit structured JSON")
    s.add_argument("--prompt", required=True, help="prompt name, e.g. summarizer")
    return p


def main(argv: list | None = None) -> int:
    args = _build_parser().parse_args(argv)
    artifact_root = _resolve_artifact_root()
    _migrate_legacy_layout(artifact_root)

    if args.cmd == "list-runs":
        list_runs(_resolve_runs_dir(args.prompt))
        return 0
    if args.cmd == "list-prompts":
        list_prompts(_resolve_prompts_dir())
        return 0
    if args.cmd == "generate":
        runs_dir = _resolve_runs_dir(args.prompt)
        out_dir = runs_dir / args.run_id
        _do_generate(
            task=args.task,
            inputs_json=args.inputs,
            num_cases=args.num_cases,
            model=args.model,
            out_dir=out_dir,
            prompt_name=args.prompt,
        )
        return 0
    if args.cmd == "evaluate":
        runs_dir = _resolve_runs_dir(args.prompt)
        out_dir = runs_dir / args.run_id
        _do_evaluate(
            version=args.version,
            model=args.model,
            judge_model=args.judge_model,
            out_dir=out_dir,
            extra_criteria=args.extra_criteria,
            prompt_name=args.prompt,
            docs_site_dir=artifact_root / "docs-site",
        )
        return 0
    if args.cmd == "show":
        runs_dir = _resolve_runs_dir(args.prompt)
        out_dir = runs_dir / args.run_id
        _do_show(out_dir, args.version, json_output=args.json)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
