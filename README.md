# Claude Eval Plugin

A Claude Code plugin for evaluating and iterating on prompts. Built for prompt engineers and AI builders who want a repeatable loop of "edit, eval, see scores, improve" instead of vibes-based iteration.

**No API key required** — Claude Code performs all LLM work natively (dataset generation, prompt execution, grading).

## What's Included

| Component | Description |
|-----------|-------------|
| `/prompt-eval:prompt_eval` | Skill that walks you through 5 coaching steps, generates test datasets, grades outputs with Claude-as-judge, and produces an MkDocs site |
| `llm-judge` agent | GEval grading subagent spawned in parallel for fast, consistent scoring |

## Installation

**Prerequisites:** [Node.js](https://nodejs.org/en/download) (for `npx`), [uv](https://docs.astral.sh/uv/) (the skill invokes Python via `uvx`)

```bash
npx plugins add vukhanhtruong/claude-eval-skill
```

Then restart Claude Code or run `/reload-plugins`.

### Alternative: Local Testing

```bash
# Clone and test locally
git clone https://github.com/vukhanhtruong/claude-eval-skill.git
claude --plugin-dir ./claude-eval-skill
```

### Uninstall

```bash
# Via Claude Code
/plugin uninstall prompt-eval

# Or remove manually
rm -rf ~/.claude/plugins/cache/vukhanhtruong-claude-eval-skill
```

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
```

The skill auto-generates a prompt name from your description (e.g., `summarize_tech_hackernews`) and checks for similar existing prompts before creating a new one.

The skill guides you through:
1. **Guided prompt building** — coaching grounded in Anthropic best practices
2. **Dataset generation** — Claude creates test cases with explicit success criteria
3. **Prompt execution + grading** — parallel `llm-judge` subagents score each case
4. **Results analysis** — scores table, failure patterns, suggested fixes
5. **Iteration** — apply fixes, re-run, compare versions

## How Grading Works

The plugin uses **GEval methodology** (ported from DeepEval) with Claude as judge:

1. Each test case has explicit `solution_criteria`
2. The `llm-judge` agent evaluates each criterion: PASS (1.0) / PARTIAL (0.5) / FAIL (0.0)
3. Scores are averaged and scaled to 1-10
4. Parallel execution: 3 test cases grade simultaneously

No external API calls — grading runs inside Claude Code via subagents.

## Artifacts

Each run produces versioned artifacts:

```
<project>/prompt_eval_runs/
├── prompts/<prompt_name>/runs/run_NNN/
│   ├── dataset.json        # test cases (locked at v1)
│   ├── metadata.json       # run metadata
│   └── v1/
│       ├── prompt.txt      # the prompt being tested
│       ├── output.json     # execution results
│       └── scores.json     # grading results
└── docs-site/              # auto-generated MkDocs site
    └── ...
```

The MkDocs site auto-starts after first grading, letting you browse and compare versions.

## Plugin Structure

```
claude-eval-skill/
├── .claude-plugin/
│   └── plugin.json         # plugin manifest
├── skills/
│   └── prompt_eval/        # the main skill
│       ├── SKILL.md
│       ├── scripts/        # Python CLI for validation/aggregation
│       └── tests/
└── agents/
    └── llm-judge.md        # GEval grading subagent
```

## Development

```bash
cd skills/prompt_eval
uv sync
uv run pytest              # 81 tests
```

## Why This Plugin

**The Problem:**
- Prompt iteration without measurement is vibes-based
- "Did v3 actually beat v2?" is hard to answer without versioned artifacts
- External eval tools require API keys and complex setup

**The Solution:**
- Claude Code does all LLM work natively — no API key needed
- Versioned artifacts + MkDocs site for easy comparison
- Parallel grading with explicit criteria (not black-box scoring)
- Coaching grounded in Anthropic's prompt engineering best practices

## License

MIT License

## Keywords

prompt engineering, prompt evaluation, Claude Code, Anthropic, LLM evals, GEval, MkDocs, Claude Code plugin
