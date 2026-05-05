"""CLI entry point for /prompt_eval skill."""
import argparse
import json
import os
import sys
from pathlib import Path

# Telemetry opt-out before any deepeval import
os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "1")


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
    # generate / evaluate handled in later tasks
    return 1


if __name__ == "__main__":
    sys.exit(main())
