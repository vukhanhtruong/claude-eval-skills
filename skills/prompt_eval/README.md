# prompt_eval

Build, test, and iteratively improve a Claude prompt with grounded coaching and empirical scoring.

**No API key required** — Claude Code performs all LLM work natively (dataset generation, prompt execution, grading).

[← Back to Claude Eval Plugin](../../README.md)

## What You Get

- **Coaching transcript** — applies Anthropic's prompt-engineering principles (role, examples, output spec, positive phrasing) at each step
- **Versioned artifacts** — `prompt_eval_runs/prompts/<name>/runs/run_NNN/v{n}/` keeps every prompt + output side-by-side
- **Local MkDocs site** — auto-built and served after first grading; browse runs and compare versions
- **Per-case scoreboard** — GEval methodology with Claude-as-judge, structured scenario / score / reasoning
- **Parallel grading** — `llm-judge` subagents score test cases simultaneously
- **Failure-pattern analysis** — classifies low-scoring cases and proposes the next iteration

## Usage

```bash
# Start with a task description (auto-generates prompt name)
/prompt-eval:prompt_eval summarize tech articles from hackernews

# Or specify a prompt name explicitly
/prompt-eval:prompt_eval --prompt summarizer

# List all prompts you've evaluated
/prompt-eval:prompt_eval --list-prompts

# List runs for a specific prompt
/prompt-eval:prompt_eval --prompt summarizer --list

# Resume an existing run (add new version)
/prompt-eval:prompt_eval --prompt summarizer --resume run_001

# Custom options
/prompt-eval:prompt_eval --prompt code_reviewer --model sonnet --cases 5
```

The skill auto-generates a prompt name from your description (e.g., `summarize_tech_hackernews`) and checks for similar existing prompts before creating a new one.

## Workflow

The skill walks you through 5 steps:

### Step 1 — Guided Prompt Building

Asks one question at a time across six phases:
- Task description
- Input variables
- Output specification
- Role assignment
- Few-shot examples
- Failure modes

Coaches when input is weak — flags vague tasks, negative phrasing, or missing examples.

### Step 2 — Generate Dataset

Claude creates N test cases (default 3) with explicit `solution_criteria` for each. Dataset is locked at v1 so cross-version score comparisons stay valid.

### Step 3 — Run + Grade

1. Executes the prompt against each test case
2. Spawns parallel `llm-judge` subagents (one per case) for grading
3. Each criterion scored: PASS (1.0) / PARTIAL (0.5) / FAIL (0.0)
4. Scores averaged and scaled to 1-10

### Step 4 — Show Results & Analyze Failures

Renders a scoreboard table:

| Scenario | Score | Criteria | Reasoning |
|----------|-------|----------|-----------|
| Tech startup pitch | 8/10 | Summary: PASS, Tone: PARTIAL | ... |

Classifies low-scoring cases against a remedy table to surface the #1 fix.

### Step 5 — Apply Improvement

Offers options:
- Apply Claude's suggested fix
- Add a few-shot from a failed case
- Paste your own revision
- Done

Loops back to Step 3 with `v{n+1}`.

## How Grading Works

The plugin uses **GEval methodology** (ported from DeepEval) with Claude as judge:

1. Each test case has explicit `solution_criteria`
2. The `llm-judge` agent evaluates each criterion independently
3. Assessments: PASS (1.0) / PARTIAL (0.5) / FAIL (0.0)
4. Final score = average × 10, rounded to integer (1-10 scale)

No external API calls — grading runs inside Claude Code via subagents.

## Artifacts

Each run produces versioned artifacts:

```
<project>/prompt_eval_runs/
├── prompts/<prompt_name>/runs/run_NNN/
│   ├── dataset.json        # test cases with solution_criteria (locked at v1)
│   ├── metadata.json       # run metadata, models, transitions
│   └── v1/
│       ├── prompt.txt      # the prompt being tested
│       ├── output.json     # execution results
│       └── scores.json     # grading results with criteria_breakdown
└── docs-site/              # auto-generated MkDocs site
    ├── mkdocs.yml
    └── docs/
        └── prompts/<name>/runs/run_NNN/...
```

## Examples

### Example 1: Build a new prompt from scratch

```
/prompt-eval:prompt_eval write product descriptions for e-commerce

Claude will:
1. Walk you through Step 1 coaching — task, inputs, output spec, role, examples
2. Auto-generate prompt name: product_descriptions_ecommerce
3. Save v1 prompt to prompt_eval_runs/prompts/product_descriptions_ecommerce/runs/run_001/v1/prompt.txt
4. Generate a 3-case test dataset
5. Run + grade v1 against the dataset
6. Show the scoreboard, classify failures, and propose v2
```

### Example 2: Iterate on an existing run

```
/prompt-eval:prompt_eval --prompt summarizer --resume run_001

Claude will:
1. Load metadata.json, print prior versions and average scores
2. Skip dataset generation (locked at v1)
3. Jump to Step 5 — propose v_{n+1} from the latest version's failures
4. Run + grade v_{n+1}, show side-by-side comparison
```

## CLI Commands

The skill invokes a Python CLI for validation and aggregation:

```bash
# List prompts
uvx --from "${CLAUDE_SKILL_DIR}" prompt-eval list-prompts

# List runs for a prompt
uvx --from "${CLAUDE_SKILL_DIR}" prompt-eval list-runs --prompt summarizer

# Show scores
uvx --from "${CLAUDE_SKILL_DIR}" prompt-eval show --prompt summarizer --run-id run_001 --version v1 --json
```

## Source Layout

```
skills/prompt_eval/
├── SKILL.md                # slash-command + step-by-step coaching script
├── README.md               # this file
├── pyproject.toml          # package "prompt-eval"
├── scripts/                # source folder (importable as `prompt_eval`)
│   ├── data_helpers.py     # DatasetHelper, ResultsHelper, OutputHelper
│   ├── docs_generator.py   # runs/ → Markdown + mkdocs.yml nav
│   ├── run.py              # argparse CLI
│   └── docs-site-template/ # bundled MkDocs template
└── tests/                  # pytest suite (81 tests)
```

## Development

```bash
cd skills/prompt_eval
uv sync
uv run pytest                   # unit tests (81 tests)
uv run pytest -m e2e            # opt-in e2e tests
```
