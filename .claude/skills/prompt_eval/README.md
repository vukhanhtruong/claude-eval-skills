# `prompt_eval` — Build, test, and improve a Claude prompt

A Claude Code skill that walks you through 5 coaching steps grounded in Anthropic's prompt-engineering best practices, generates a test dataset, runs evaluations with DeepEval (Claude as judge), produces an MkDocs site, and (optionally) pushes results to Langfuse.

← Back to [Claude Eval Skills](../../../README.md)

## What you get

Per evaluated prompt, the skill produces:

- **Coaching transcript** — applies Anthropic's prompt-engineering principles (role, examples, output spec, positive phrasing, etc.) at each step
- **Versioned artifacts** — `prompt_eval_runs/prompts/<name>/runs/run_NNN/v{n}/` keeps every prompt + output side-by-side
- **Local MkDocs site** — auto-built and served on first `evaluate`; browse runs and compare versions in your browser
- **Per-case scoreboard** — DeepEval `GEval` metric with one rubric per case, Claude-as-judge, structured scenario / score / reasoning JSON
- **Failure-pattern analysis** — Claude classifies low-scoring cases against a fixed remedy table and proposes the next iteration
- **Optional Langfuse push** — datasets, traces, scores, and dataset-runs published to your Langfuse instance for team review and historical comparison

## Optional: set up Langfuse

Langfuse is **purely additive** — the skill always produces a local MkDocs site. Skip this section unless you want shared dashboards or run-history across a team.

You need three env vars:

| Var | Required? | Notes |
|---|---|---|
| `LANGFUSE_PUBLIC_KEY` | yes | from project settings in Langfuse |
| `LANGFUSE_SECRET_KEY` | yes | from project settings in Langfuse |
| `LANGFUSE_HOST` *or* `LANGFUSE_BASE_URL` | yes (one of) | e.g. `https://cloud.langfuse.com`, `https://us.cloud.langfuse.com`, or your self-hosted URL |

**1. Get keys.** [Sign up at cloud.langfuse.com](https://cloud.langfuse.com/) (free tier exists) or self-host. Create a project, then copy the public + secret keys from *Settings → API keys*.

**2. Load them into your shell.** Copy the example file and fill it in:

```bash
cp .env.example .env
# edit .env with your keys

# load into the current shell (skill reads from os.environ, doesn't auto-load .env)
set -a; source .env; set +a
```

`.env` is gitignored. Alternatively, `export LANGFUSE_PUBLIC_KEY=...` etc. directly, or put them in your shell rc.

**3. Verify.** The skill auto-detects Langfuse during `evaluate` — when keys are set, it prints "Pushed to Langfuse: <url>" alongside the local MkDocs URL. To push an existing run retroactively:

```bash
uvx --from .claude/skills/prompt_eval prompt-eval push --prompt summarizer --run-id run_001
```

If a var is missing, the CLI prints which one. If everything is set, you'll see Langfuse URLs in the output.

## Usage

Once installed, invoke the skill end-to-end via the slash command:

```
/prompt_eval --prompt summarizer
→ Walks you through building, evaluating, and improving the "summarizer" prompt

/prompt_eval --list-prompts
→ Lists every prompt namespace with run counts

/prompt_eval --prompt summarizer --list
→ Lists existing runs for "summarizer"

/prompt_eval --prompt summarizer --resume run_001
→ Adds v_{n+1} to an existing run

/prompt_eval --prompt code_reviewer --model sonnet --judge-model opus --cases 5
→ Runs with custom test/judge models and dataset size
```

You can also invoke the underlying CLI directly:

```bash
uvx --from .claude/skills/prompt_eval prompt-eval list-prompts
uvx --from .claude/skills/prompt_eval prompt-eval generate --prompt summarizer --task "..." --inputs '...' --num-cases 3 --model haiku --run-id run_001
uvx --from .claude/skills/prompt_eval prompt-eval evaluate --prompt summarizer --version v1 --model haiku --judge-model sonnet --run-id run_001
uvx --from .claude/skills/prompt_eval prompt-eval show --prompt summarizer --run-id run_001 --version v1 --json
uvx --from .claude/skills/prompt_eval prompt-eval push --prompt summarizer --run-id run_001 --version v1
```

## Workflow

The `/prompt_eval` skill walks 5 steps (see [SKILL.md](SKILL.md) for verbatim coaching prompts):

### Step 1 — Guided prompt building
Asks one question at a time across six phases (task, inputs, output spec, role, examples, failure modes). Coaches when input is weak — e.g. flags vague tasks, negative phrasing, or missing examples.

### Step 2 — Generate dataset
Produces N test cases (default 3) tailored to the task and inputs. Dataset is locked at v1 of the run so cross-version score comparisons stay valid.

### Step 3 — Run + grade
Runs the prompt against each case with the test model, scores with the judge model via DeepEval `GEval`. Concurrent (3 workers) and rate-limit-safe by default. Optionally pushes to Langfuse.

### Step 4 — Show results & analyze failures
Renders a scoreboard table (scenario / score / reasoning), prints average and pass rate, and classifies low-scoring cases against a remedy table to surface the #1 fix.

### Step 5 — Apply improvement
Offers four options: apply Claude's suggested fix, add a few-shot from a failed case, paste a hand-written revision, or stop. Loops back to Step 3 with `v{n+1}`.

## Quick start examples

### Example 1: Build a new prompt from scratch

```
User: /prompt_eval --prompt summarizer

Claude will:
1. Walk you through Step 1 coaching — task, inputs, output spec, role, examples
2. Save v1 prompt to prompt_eval_runs/prompts/summarizer/runs/run_001/v1/prompt.txt
3. Generate a 3-case test dataset
4. Run + grade v1 against the dataset
5. Show the scoreboard, classify failures, and propose v2
```

### Example 2: Iterate on an existing run

```
User: /prompt_eval --prompt summarizer --resume run_001

Claude will:
1. Load metadata.json, print prior versions and average scores
2. Skip dataset generation (locked at v1)
3. Jump to Step 5 — propose v_{n+1} from the latest version's failures
4. Run + grade v_{n+1}, show side-by-side comparison
```

### Example 3: Push existing run to Langfuse retroactively

```
User: prompt-eval push --prompt summarizer --run-id run_001

CLI will:
1. Read local artifacts (dataset.json + every v{n}/output.json)
2. Create-or-upsert the Langfuse dataset and items (deterministic IDs)
3. Push one trace + score + dataset-run-item per case per version
4. Flush and print the Langfuse URLs
```

## Artifact layout

Source of truth (raw eval data) and the regenerated docs site:

```
<project>/prompt_eval_runs/
├── prompts/<name>/runs/run_NNN/      # source of truth
│   ├── dataset.json                  # locked at v1
│   ├── metadata.json
│   └── v{n}/{prompt.txt, output.json}
└── docs-site/                        # regenerated from runs/, never hand-edited
```

## Source layout

```
.claude/skills/prompt_eval/
├── SKILL.md                # slash-command + step-by-step coaching script
├── README.md               # this file
├── pyproject.toml          # package "prompt-eval"; entry point prompt-eval = prompt_eval.run:main
├── scripts/                # source folder (importable as `prompt_eval`)
│   ├── anthropic_llm.py    # Claude as DeepEval judge
│   ├── evaluator.py        # MODEL_MAP, render_prompt, DatasetGenerator, Evaluator
│   ├── docs_generator.py   # runs/ → Markdown + mkdocs.yml nav
│   ├── langfuse_push.py    # optional Langfuse dataset/trace/score push
│   ├── run.py              # argparse CLI: list-prompts | list-runs | generate | evaluate | show | push
│   └── docs-site-template/ # bundled MkDocs template
└── tests/                  # pytest suite
```

## Development

```bash
cd .claude/skills/prompt_eval
uv sync
uv run pytest                   # unit tests
uv run pytest -m e2e            # opt-in network tests (hits Anthropic + Langfuse)
```
