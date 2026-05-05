# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository status (read this first)

This repo is **pre-implementation**. As of 2026-05-05 there is no source code, no `pyproject.toml`, and no git history — only a design doc and an implementation plan. The codebase referenced throughout the planning docs (`workflow/prompt_eval/...`, `.claude/skills/prompt_eval/SKILL.md`, etc.) does **not exist yet**. Treat the docs as intent, not as documentation of working code.

The two source-of-truth documents are:

- `docs/superpowers/specs/2026-05-05-prompt-eval-skill-design.md` — design rationale, decision table, directory layout
- `docs/superpowers/plans/2026-05-05-prompt-eval-skill.md` — 17-task step-by-step build plan with full code blocks

When implementing, use the plan, not the spec, as the build instructions; the spec is the "why" and resolves ambiguity.

## What is being built

A Claude Code slash command (`/prompt_eval`) that turns prompt iteration into a measurable loop:

1. Coaches the user through 6 phases (task / inputs / output / role / examples / failure modes) using verbatim Anthropic-best-practice prompts.
2. Generates a synthetic eval dataset with Claude.
3. Scores prompt outputs with DeepEval's per-case `GEval` metric, using Claude as judge (no OpenAI dependency).
4. Persists every run/version under `workflow/prompt_eval/runs/run_NNN/` and projects them into a MkDocs Material site.
5. Supports `--resume run_NNN` to add a new version against the original dataset + judge for fair A/B comparison.

The skill is a thin SKILL.md orchestrator that shells out to a Python CLI; nearly all logic lives in Python.

## Planned architecture

```
.claude/skills/prompt_eval/SKILL.md       # slash-command + step-by-step coaching script
workflow/prompt_eval/
  anthropic_llm.py                        # AnthropicLLM(DeepEvalBaseLLM) — Claude as judge
  evaluator.py                            # MODEL_MAP, render_prompt, DatasetGenerator, Evaluator
  docs_generator.py                       # runs/ → Markdown + mkdocs.yml nav updates
  run.py                                  # argparse CLI: generate | evaluate | list-runs
  runs/run_NNN/                           # raw eval data (source of truth)
    dataset.json                          # locked at v1, reused across versions
    metadata.json                         # prompts, scores, models, transitions
    v{n}/{prompt.txt, output.json}
  docs-site/                              # projected view; regenerated, not edited by hand
    mkdocs.yml
    docs/{index.md, runs/run_NNN/...}
  tests/                                  # pytest, alongside source
```

Key invariants worth preserving when implementing:

- **`runs/` is the source of truth; `docs-site/docs/` is regenerated.** Never hand-edit pages under `docs-site/docs/runs/`. `docs_generator.regenerate_for_run()` rewrites them.
- **Dataset is locked at v1 of a run.** Resuming a run must not regenerate `dataset.json` — that would invalidate cross-version score comparisons.
- **One `GEval` metric per test case**, built from that case's `solution_criteria`. A single shared metric loses specificity (this is an explicit decision in the spec, not an oversight).
- **Telemetry must be off.** Set `os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = "1"` at module import time in `evaluator.py` — before any `deepeval` import does network I/O.
- **Model map is fixed** (`evaluator.py`): `haiku → claude-haiku-4-5`, `sonnet → claude-sonnet-4-6`, `opus → claude-opus-4-7`. Default test model is `haiku`; default judge is `sonnet`.
- **Concurrency = 3** (`ThreadPoolExecutor`) and **default `--cases` = 3**. These are rate-limit-safe defaults from the source notebook; don't bump them without reason.
- **Auto-start `mkdocs serve` in the background** after the first `evaluate` per session, and print the URL. Don't block the CLI on it.

## Commands (once implemented)

These don't work yet — they will after Task 1 (`uv sync`) of the plan.

```bash
# Install deps (Python 3.12, uv-managed)
uv sync

# Run the CLI directly
cd workflow/prompt_eval
uv run python run.py list-runs
uv run python run.py generate --task "..." --inputs '...' --num-cases 3 --model haiku --out-dir runs/run_001
uv run python run.py evaluate --version v1 --model haiku --judge-model sonnet --out-dir runs/run_001

# Tests
cd workflow/prompt_eval && uv run pytest
cd workflow/prompt_eval && uv run pytest tests/test_evaluator.py::test_grade_with_geval  # single test

# Docs site (auto-started by `evaluate`, but to run manually)
cd workflow/prompt_eval/docs-site && uv run mkdocs serve

# Invoke the skill end-to-end
/prompt_eval                                    # fresh run
/prompt_eval --list                             # list prior runs
/prompt_eval --resume run_001                   # add v_{n+1} to existing run
/prompt_eval --model sonnet --judge-model opus --cases 5
```

## Plugins enabled

`.claude/settings.json` enables `superpowers` and `skill-creator`. The implementation plan explicitly calls out **`superpowers:subagent-driven-development`** (preferred) or **`superpowers:executing-plans`** as the sub-skill to drive task-by-task execution. The plan's `- [ ]` checkboxes are designed for those skills' progress tracking.

`.claude/settings.local.json` allow-lists `WebFetch(domain:deepeval.com)` for looking up DeepEval API details during implementation.

## Working in this repo

- **Don't invent file locations.** If something isn't on disk, it's a planning artifact. Check `ls workflow/prompt_eval/` before assuming a module exists.
- **Follow the plan's task order.** Tasks 1–17 have explicit dependencies (e.g. `evaluator.py` constants land in Task 3 before `DatasetGenerator` in Task 4). Don't skip ahead — later tasks assume earlier scaffolding.
- **The verbatim coaching prompts and the failure-pattern→remedy table in `SKILL.md` are not boilerplate.** They are the product. Copy them exactly from the spec/plan; rewording weakens the skill's grounding in named Anthropic techniques.
- **Run isolation:** each `/prompt_eval` invocation = one new `run_NNN` directory; resume is opt-in via `--resume`. Don't fold versions across runs.
