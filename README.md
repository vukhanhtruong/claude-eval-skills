# Claude Eval Plugin

A Claude Code plugin for evaluating LLM applications: prompts, RAG pipelines, tool calls, and agents. Built for prompt engineers and AI builders who want a repeatable loop of "edit, eval, see scores, improve" instead of vibes-based iteration.

**No API key required** — Claude Code performs all LLM work natively.

## Installation

**Prerequisites:** [Node.js](https://nodejs.org/en/download) (for `npx`), [uv](https://docs.astral.sh/uv/) (skills invoke Python via `uvx`)

### User-level (personal use)

```bash
npx plugins add vukhanhtruong/claude-eval-skill
```

Then restart Claude Code or run `/reload-plugins`.

### Project-level (team sharing)

For committing the plugin with your repo:

```bash
# Option 1: Clone directly
git clone https://github.com/vukhanhtruong/claude-eval-skill.git .claude-plugins/prompt-eval

# Option 2: Git submodule (easier updates)
git submodule add https://github.com/vukhanhtruong/claude-eval-skill.git .claude-plugins/prompt-eval
```

Then add to `.claude/settings.json`:

```json
{
  "plugins": [".claude-plugins/prompt-eval"]
}
```

Or load manually:

```bash
claude --plugin-dir .claude-plugins/prompt-eval
```

## Available Skills

| Skill | Description | Status |
|-------|-------------|--------|
| [prompt_eval](skills/prompt_eval/README.md) | Build, test, and improve a Claude prompt. 5 coaching steps, test dataset generation, Claude-as-judge grading, MkDocs site for results. | Available |
| `rag_eval` | Evaluate retrieval quality (recall, precision, MRR) and answer quality (faithfulness, context relevance, answer correctness) for RAG pipelines. | Planned |
| `tool_eval` | Evaluate tool selection accuracy, argument correctness, and multi-step tool-call trajectories. | Planned |
| `agent_eval` | End-to-end agent evals — planning, multi-turn task completion, trajectory scoring, side-effect verification. | Planned |

## Quick Start

```bash
# Evaluate a prompt (auto-generates name from description)
/prompt-eval:prompt_eval summarize tech articles from hackernews

# Or specify a name explicitly
/prompt-eval:prompt_eval --prompt summarizer
```

See each skill's README for detailed usage.

## Plugin Structure

```
claude-eval-skill/
├── .claude-plugin/
│   └── plugin.json         # plugin manifest
├── skills/
│   └── prompt_eval/        # prompt evaluation skill
│       ├── SKILL.md
│       ├── README.md       # detailed documentation
│       └── scripts/
└── agents/
    └── llm-judge.md        # GEval grading subagent
```

## Development

```bash
cd skills/prompt_eval
uv sync
uv run pytest              # 81 tests
```

## License

MIT License
