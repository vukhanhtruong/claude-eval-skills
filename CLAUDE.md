# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A portable Claude Code skill: `/prompt_eval`. The skill helps users build, test, and iteratively improve a Claude prompt with grounded coaching (Anthropic best practices) and empirical scoring (Claude Code as judge — no API key required).

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
│   ├── data_helpers.py            # DatasetHelper, ResultsHelper, OutputHelper — save/validate artifacts
│   ├── docs_generator.py          # runs/ → Markdown + mkdocs.yml nav updates
│   ├── run.py                     # argparse CLI: save-dataset | save-output | save-scores | show | list-*
│   ├── tool_discovery.py          # discover available Claude Code tools
│   ├── tool_mocker.py             # mock tools for testing
│   └── docs-site-template/        # bundled template — copied to artifact dir on first docs run
└── tests/                         # pytest, run from inside the skill dir
```

All LLM work (dataset generation, prompt execution, scoring) is done by Claude Code natively. The Python CLI is a thin validation, aggregation, and docs layer — no Anthropic SDK or DeepEval dependency required.

Note: the source folder is `scripts/` on disk but importable as `prompt_eval` — `pyproject.toml` uses setuptools' `package-dir = {"prompt_eval" = "scripts"}` mapping plus uv's `editable_mode = "strict"` so the rename survives editable installs (setuptools materializes the package layout via per-file symlinks under `build/`). Hatchling can't do this in editable mode, which is why the build backend is setuptools.

Artifacts (per user project):

```
<project>/prompt_eval_runs/
├── prompts/                              # one subdir per prompt namespace
│   └── <prompt_name>/
│       └── runs/run_NNN/                 # raw eval data (source of truth)
│           ├── dataset.json              # locked at v1, reused across versions
│           ├── metadata.json             # prompts, scores, models, transitions, prompt_name
│           └── v{n}/{prompt.txt, output.json}
└── docs-site/                            # projected view; regenerated from runs/, not edited by hand
    ├── mkdocs.yml
    ├── docs/{index.md, prompts/<prompt_name>/runs/run_NNN/...}
    └── mkdocs.log
```

The skill invokes Python via `uvx --from "${CLAUDE_SKILL_DIR}" prompt-eval ...`. uvx builds the package from the skill dir in an isolated env and runs the entry point. First invocation takes ~30-90s; subsequent calls are sub-second from cache.

## Invariants (preserve when changing the skill)

- **`prompt_eval_runs/prompts/<name>/runs/` is the source of truth; `docs-site/docs/prompts/<name>/runs/` is regenerated.** Never hand-edit those pages. `docs_generator.regenerate_for_run()` rewrites them.
- **Prompt namespace is required.** Every `save-dataset`/`save-output`/`save-scores`/`show`/`list-runs` call must pass `--prompt <name>`. Names match `[a-z0-9_-]+`. Run IDs are scoped per prompt — `prompts/summarizer/runs/run_001` and `prompts/code_reviewer/runs/run_001` are independent.
- **Legacy migration is one-shot.** On first invocation per project after upgrading, if `prompt_eval_runs/runs/` exists and `prompt_eval_runs/prompts/` does not, the CLI moves runs into `prompts/default/runs/` and rewrites the docs nav. Re-runs are no-ops.
- **Dataset is locked at v1 of a run.** Resuming a run must not regenerate `dataset.json` — that would invalidate cross-version score comparisons.
- **Scoring is per-case.** Each test case carries its own `solution_criteria`; scores are saved individually via `save-scores` and aggregated by `ResultsHelper.aggregate()`.
- **Auto-start `mkdocs serve` in the background** after the first `save-scores` per session, and print the URL. Don't block the CLI on it.
- **Artifact dir resolution** (`run.py` → `_resolve_artifact_root`): `$PROMPT_EVAL_PROJECT_DIR` > `os.getcwd()` (when `prompt_eval_runs/` exists) > `$CLAUDE_PROJECT_DIR` > error. cwd is intentionally checked before `CLAUDE_PROJECT_DIR` to prevent stale env-var poisoning from prior sessions. Always preserve this priority.
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
uvx --from "${CLAUDE_SKILL_DIR}" prompt-eval list-prompts
uvx --from "${CLAUDE_SKILL_DIR}" prompt-eval list-runs --prompt summarizer
uvx --from "${CLAUDE_SKILL_DIR}" prompt-eval save-dataset --prompt summarizer --run-id run_001 --json '[{"input": "...", "solution_criteria": "..."}]'
uvx --from "${CLAUDE_SKILL_DIR}" prompt-eval save-output --prompt summarizer --run-id run_001 --version v1 --json '[{"input": "...", "output": "..."}]'
uvx --from "${CLAUDE_SKILL_DIR}" prompt-eval save-scores --prompt summarizer --run-id run_001 --version v1 --json '[{"input": "...", "score": 0.9, "reason": "..."}]'
uvx --from "${CLAUDE_SKILL_DIR}" prompt-eval show --prompt summarizer --run-id run_001 --version v1 --json
uvx --from "${CLAUDE_SKILL_DIR}" prompt-eval stop-server
```

When testing `uvx` invocations manually outside Claude Code, set `CLAUDE_PROJECT_DIR` (or `PROMPT_EVAL_PROJECT_DIR`) to the dir you want artifacts in — otherwise the skill will inherit whatever `CLAUDE_PROJECT_DIR` your shell already had set from another project.

Or invoke the skill end-to-end (Claude Code parses `$ARGUMENTS` and orchestrates the steps):

```
/prompt_eval --prompt summarizer                               # fresh run for summarizer
/prompt_eval --list-prompts                                    # list all prompts
/prompt_eval --prompt summarizer --list                        # list summarizer's runs
/prompt_eval --prompt summarizer --resume run_001              # add v_{n+1} to existing run
```

## Plugins enabled

`.claude/settings.json` enables `superpowers` and `skill-creator`. The `superpowers:subagent-driven-development` and `superpowers:executing-plans` sub-skills can drive task-by-task execution of any plan in `docs/superpowers/plans/`.

## Working in this repo

- **Run tests from inside the skill dir.** `cd .claude/skills/prompt_eval && uv run pytest`. The repo root has no `pyproject.toml`.
- **The verbatim coaching prompts and the failure-pattern→remedy table in `SKILL.md` are the product.** Copy them exactly from the design spec; rewording weakens the skill's grounding in named Anthropic techniques.
- **Run isolation:** each `/prompt_eval` invocation = one new `run_NNN` directory; resume is opt-in via `--resume`. Don't fold versions across runs.
- **Don't edit files under `prompt_eval_runs/docs-site/docs/prompts/<name>/runs/` directly** — they're regenerated from `prompt_eval_runs/prompts/<name>/runs/`. Edit the source data instead.
- **Working with multiple prompts:** keep them in distinct `--prompt` namespaces. Run IDs reset per prompt; both can have a `run_001`. The docs nav groups them under `Prompts > <name> > <run_id>`.
