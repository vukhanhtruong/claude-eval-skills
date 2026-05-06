# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A portable Claude Code skill: `/prompt_eval`. The skill helps users build, test, and iteratively improve a Claude prompt with grounded coaching (Anthropic best practices) and empirical scoring (DeepEval with Claude as judge).

The entire skill lives under `.claude/skills/prompt_eval/`. Everything else in the repo is documentation or git metadata.

## Architecture

```
.claude/skills/prompt_eval/
├── SKILL.md                       # slash-command + step-by-step coaching script
├── pyproject.toml                 # package "prompt-eval", entry point prompt-eval = prompt_eval.run:main
├── uv.lock
├── .gitignore
├── scripts/                       # source folder (skill-creator convention); imported as `prompt_eval`
│   ├── __init__.py
│   ├── anthropic_llm.py           # AnthropicLLM(DeepEvalBaseLLM) — Claude as judge
│   ├── evaluator.py               # MODEL_MAP, render_prompt, DatasetGenerator, Evaluator
│   ├── docs_generator.py          # runs/ → Markdown + mkdocs.yml nav updates
│   ├── run.py                     # argparse CLI: list-runs | generate | evaluate | show
│   └── docs-site-template/        # bundled template — copied to artifact dir on first evaluate
└── tests/                         # pytest, run from inside the skill dir
```

Note: the source folder is `scripts/` on disk but importable as `prompt_eval` — `pyproject.toml` uses setuptools' `package-dir = {"prompt_eval" = "scripts"}` mapping plus uv's `editable_mode = "strict"` so the rename survives editable installs (setuptools materializes the package layout via per-file symlinks under `build/`). Hatchling can't do this in editable mode, which is why the build backend is setuptools.

Artifacts (per user project):

```
<project>/prompt_eval_runs/
├── runs/run_NNN/                  # raw eval data (source of truth)
│   ├── dataset.json               # locked at v1, reused across versions
│   ├── metadata.json              # prompts, scores, models, transitions
│   └── v{n}/{prompt.txt, output.json}
└── docs-site/                     # projected view; regenerated from runs/, not edited by hand
    ├── mkdocs.yml
    ├── docs/{index.md, runs/run_NNN/...}
    └── mkdocs.log
```

The skill invokes Python via `uvx --from "${CLAUDE_SKILL_DIR}" prompt-eval ...`. uvx builds the package from the skill dir in an isolated env and runs the entry point. First invocation takes ~30-90s; subsequent calls are sub-second from cache.

## Invariants (preserve when changing the skill)

- **`prompt_eval_runs/runs/` is the source of truth; `docs-site/docs/` is regenerated.** Never hand-edit pages under `docs-site/docs/runs/`. `docs_generator.regenerate_for_run()` rewrites them.
- **Dataset is locked at v1 of a run.** Resuming a run must not regenerate `dataset.json` — that would invalidate cross-version score comparisons.
- **One `GEval` metric per test case**, built from that case's `solution_criteria`. A single shared metric loses specificity (deliberate decision in the spec).
- **Telemetry must be off.** `os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = "1"` is set at module import time in `evaluator.py` — before any `deepeval` import does network I/O.
- **Model map is fixed** (`evaluator.py`): `haiku → claude-haiku-4-5`, `sonnet → claude-sonnet-4-6`, `opus → claude-opus-4-7`. Default test model is `haiku`; default judge is `sonnet`.
- **Concurrency = 3** (`ThreadPoolExecutor`) and **default `--num-cases` = 3**. Rate-limit-safe defaults from the source notebook; don't bump them without reason.
- **Auto-start `mkdocs serve` in the background** after the first `evaluate` per session, and print the URL. Don't block the CLI on it.
- **Artifact dir resolution** (`run.py` → `_resolve_artifact_root`): `$PROMPT_EVAL_PROJECT_DIR` > `$CLAUDE_PROJECT_DIR` > `os.getcwd()`. Always preserve this priority.
- **`docs-site-template/` lives inside `scripts/`** so `Path(__file__).parent / "docs-site-template"` works in both editable-install (dev, via setuptools symlinks) and built-wheel (uvx) modes. Don't move it out.

## Commands

From inside the skill dir (development):

```bash
cd .claude/skills/prompt_eval
uv sync                                                 # install deps + editable install
uv run pytest                                           # 42 unit tests, e2e excluded by default
uv run pytest -m e2e                                    # run the API-hitting e2e test
uv run pytest tests/test_evaluator_grade.py             # single test file
```

From a user project (skill-style invocation):

```bash
uvx --from "${CLAUDE_SKILL_DIR}" prompt-eval list-runs
uvx --from "${CLAUDE_SKILL_DIR}" prompt-eval generate --task "..." --inputs '...' --num-cases 3 --model haiku --run-id run_001
uvx --from "${CLAUDE_SKILL_DIR}" prompt-eval evaluate --version v1 --model haiku --judge-model sonnet --run-id run_001
uvx --from "${CLAUDE_SKILL_DIR}" prompt-eval show --run-id run_001 --version v1 --json     # structured scoreboard
```

When testing `uvx` invocations manually outside Claude Code, set `CLAUDE_PROJECT_DIR` (or `PROMPT_EVAL_PROJECT_DIR`) to the dir you want artifacts in — otherwise the skill will inherit whatever `CLAUDE_PROJECT_DIR` your shell already had set from another project.

Or invoke the skill end-to-end (Claude Code parses `$ARGUMENTS` and orchestrates the steps):

```
/prompt_eval                                    # fresh run
/prompt_eval --list                             # list prior runs
/prompt_eval --resume run_001                   # add v_{n+1} to existing run
/prompt_eval --model sonnet --judge-model opus --cases 5
```

## Plugins enabled

`.claude/settings.json` enables `superpowers` and `skill-creator`. The `superpowers:subagent-driven-development` and `superpowers:executing-plans` sub-skills can drive task-by-task execution of any plan in `docs/superpowers/plans/`.

## Working in this repo

- **Run tests from inside the skill dir.** `cd .claude/skills/prompt_eval && uv run pytest`. The repo root has no `pyproject.toml`.
- **The verbatim coaching prompts and the failure-pattern→remedy table in `SKILL.md` are the product.** Copy them exactly from the design spec; rewording weakens the skill's grounding in named Anthropic techniques.
- **Run isolation:** each `/prompt_eval` invocation = one new `run_NNN` directory; resume is opt-in via `--resume`. Don't fold versions across runs.
- **Don't edit files under `prompt_eval_runs/docs-site/docs/runs/` directly** — they're regenerated from `runs/`. Edit the source data instead.
