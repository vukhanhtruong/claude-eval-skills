"""CLI entry point for /prompt_eval skill."""
import argparse
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from statistics import mean

# Telemetry opt-out before any deepeval import
os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "1")

from workflow.prompt_eval.evaluator import MODEL_MAP, DatasetGenerator, Evaluator
from workflow.prompt_eval.docs_generator import regenerate_for_run


MKDOCS_PORT = 8000


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def start_mkdocs_if_idle(docs_site_dir: Path) -> None:
    if _port_in_use(MKDOCS_PORT):
        print(f"mkdocs already serving at http://127.0.0.1:{MKDOCS_PORT}")
        return
    log_path = docs_site_dir / "mkdocs.log"
    subprocess.Popen(
        ["uv", "run", "mkdocs", "serve", "--dev-addr", f"127.0.0.1:{MKDOCS_PORT}"],
        cwd=docs_site_dir,
        stdout=open(log_path, "ab"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    print(f"Started mkdocs serve in background → http://127.0.0.1:{MKDOCS_PORT}")
    print(f"  log: {log_path}")


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


def _do_generate(task: str, inputs_json: str, num_cases: int, model: str, out_dir: Path) -> None:
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

    # Regenerate docs site
    here = Path(__file__).parent
    regenerate_for_run(
        run_dir=out_dir,
        docs_root=here / "docs-site" / "docs",
        mkdocs_yml=here / "docs-site" / "mkdocs.yml",
    )

    # Auto-start mkdocs serve
    start_mkdocs_if_idle(here / "docs-site")

    print(f"Evaluated {version}: average {avg:.1f}/10")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="prompt_eval")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list-runs", help="List existing runs and exit")

    g = sub.add_parser("generate", help="Generate dataset")
    g.add_argument("--task", required=True)
    g.add_argument("--inputs", required=True, help="JSON dict of input specs")
    g.add_argument("--num-cases", type=int, default=3)
    g.add_argument("--model", default="haiku", choices=["haiku", "sonnet", "opus"])
    g.add_argument("--out-dir", required=True)

    e = sub.add_parser("evaluate", help="Run + grade a prompt version")
    e.add_argument("--version", required=True, help="e.g. v1, v2")
    e.add_argument("--model", default="haiku", choices=["haiku", "sonnet", "opus"])
    e.add_argument("--judge-model", default="sonnet", choices=["haiku", "sonnet", "opus"])
    e.add_argument("--out-dir", required=True)
    e.add_argument("--extra-criteria", default=None)
    return p


def main(argv: list | None = None) -> int:
    args = _build_parser().parse_args(argv)
    here = Path(__file__).parent
    if args.cmd == "list-runs":
        list_runs(here / "runs")
        return 0
    if args.cmd == "generate":
        _do_generate(
            task=args.task,
            inputs_json=args.inputs,
            num_cases=args.num_cases,
            model=args.model,
            out_dir=Path(args.out_dir),
        )
        return 0
    if args.cmd == "evaluate":
        _do_evaluate(
            version=args.version,
            model=args.model,
            judge_model=args.judge_model,
            out_dir=Path(args.out_dir),
            extra_criteria=args.extra_criteria,
        )
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
