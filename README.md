# Claude Eval Skills

A collection of Claude Code skills for evaluating LLM applications end-to-end: prompts, RAG pipelines, tool calls, and agents. Built for prompt engineers, AI builders, and teams who want a repeatable loop of "edit → eval → see scores → improve" instead of vibes-based iteration.

## What are Skills?

Skills are markdown files plus optional supporting code that give AI agents specialized knowledge and workflows for specific tasks. When you add these skills to your project, Claude Code recognizes evaluation tasks and walks you through structured workflows grounded in Anthropic's best practices and standard eval methodology (DeepEval, RAGAS-style retrieval metrics, trajectory scoring, etc.).

## Available Skills

| Skill | Description | Status |
|-------|-------------|--------|
| [prompt_eval](.claude/skills/prompt_eval/README.md) | Build, test, and improve a Claude prompt. Walks 5 coaching steps, generates a test dataset, runs DeepEval with Claude-as-judge, produces an MkDocs site, and (optionally) pushes results to Langfuse. | Available |
| `rag_eval` | Evaluate retrieval quality (recall, precision, MRR) and answer quality (faithfulness, context relevance, answer correctness) for RAG pipelines. | Planned |
| `tool_eval` | Evaluate tool selection accuracy, argument correctness, and multi-step tool-call trajectories. | Planned |
| `agent_eval` | End-to-end agent evals — planning, multi-turn task completion, trajectory scoring, side-effect verification. | Planned |

## Installation

**Prerequisites:** [Node.js](https://nodejs.org/en/download) (for `npx`), [uv](https://docs.astral.sh/uv/) (skills may invoke Python via `uvx`), and an Anthropic API key in `ANTHROPIC_API_KEY`. Per-skill requirements (e.g. Langfuse credentials) are documented in each skill's README.

### Option 1: CLI Install (Recommended)

```bash
# See what's available in the repo (no install)
npx skills add vukhanhtruong/claude-eval-skill --list

# Interactive: prompts you to pick which skills to install
npx skills add vukhanhtruong/claude-eval-skill --agent claude-code

# Install a specific skill only (project-level)
npx skills add vukhanhtruong/claude-eval-skill --skill prompt_eval --agent claude-code -y

# Install everything in the repo, globally, no prompts
npx skills add vukhanhtruong/claude-eval-skill --agent claude-code -g --all

# List installed / global skills
npx skills list
npx skills list --global
```

> **Pass `--agent claude-code`** so files land in `.claude/skills/` (where Claude Code looks). Without it the CLI installs to the universal `.agents/skills/` path, which Claude Code does not read. To target multiple agents at once, use `--agent '*'`.

> Tip: as more skills land in this repo (`rag_eval`, `tool_eval`, `agent_eval`), `--skill <name>` lets you pull in just the ones you need.

### Option 2: Manual Install

```bash
# Clone and copy to project skills folder
git clone https://github.com/vukhanhtruong/claude-eval-skill.git
mkdir -p .claude/skills
cp -r claude-eval-skill/.claude/skills/prompt_eval .claude/skills/
```

Or for global use across all projects:

```bash
mkdir -p ~/.claude/skills
cp -r claude-eval-skill/.claude/skills/prompt_eval ~/.claude/skills/
```

### Uninstall

```bash
# Interactive remove (pick which to uninstall)
npx skills remove

# Remove a specific skill
npx skills remove --skill prompt_eval -y

# Remove everything from this repo, globally
npx skills remove -g --all

# Or remove the directory directly
rm -rf .claude/skills/prompt_eval         # project install
rm -rf ~/.claude/skills/prompt_eval       # global install
```

> First `uvx`-backed invocation of the skill takes ~30–90s while it builds the Python package; subsequent calls are sub-second.

## Supported AI Agents

These skills target:

- **Claude Code** (CLI) — primary target; each skill ships its own slash command and `SKILL.md`
- Other Claude Code-compatible agents that read `.claude/skills/`

Skill-specific CLIs are just Python entry points, so they can also be invoked directly from any environment with `uv` installed (see each skill's README for examples).

## Usage

Once installed, invoke a skill via its slash command in Claude Code, or call the CLI directly. See each skill's README for details:

- [prompt_eval](.claude/skills/prompt_eval/README.md) — `/prompt_eval` workflow, CLI usage, examples

## Why These Skills Matter

**The Problem:**
- Prompt, RAG, and agent iteration without measurement is vibes-based — improvements feel real but don't survive new inputs
- Rolling your own eval harness is yak-shaving; most teams skip it
- "Did v3 actually beat v2?" is hard to answer without versioned artifacts and shared scoring

**The Solution:**
- Skill-per-eval-type so you only install what you need (`prompt_eval` today; `rag_eval`, `tool_eval`, `agent_eval` next)
- Grounded coaching tied to named techniques (Anthropic's for prompts; RAGAS-style for retrieval; trajectory scoring for tools/agents)
- Versioned artifacts + regenerable docs sites so v1→v3 comparisons are one click away
- Optional Langfuse push for team review, dashboards, and dataset-run history

**The Results:**
- Faster iteration with empirical signal at every step
- Catch regressions before they ship — pass-rate / score is computed per version
- Shareable artifacts (MkDocs + Langfuse) so eval work isn't trapped in one engineer's terminal

## Repo Layout

```
.claude/skills/
└── <skill-name>/         # one folder per skill
    ├── SKILL.md          # slash-command + step-by-step instructions (machine-readable)
    ├── README.md         # human docs for this skill
    ├── pyproject.toml    # optional Python entry point
    ├── scripts/          # optional source code
    └── tests/            # optional test suite
```

Each skill's docs (usage, examples, artifact layout) live next to the skill itself — see the **Available Skills** table for links.

## Contributing

PRs and issues welcome — for bug reports, new coaching prompts, new eval skills, or doc clarifications.

### Ways to Contribute
- Improve an existing skill's coaching, scoring, or examples
- Propose a new skill (open an issue first to scope it)
- Add tests under each skill's `tests/` folder
- Report bugs or unclear steps

See each skill's README for skill-specific contribution notes and how to run its test suite.

## License

MIT License — use these skills however you want.

## About

A collection of Claude Code skills for grounded, measurable LLM evaluation — prompts today, RAG / tools / agents next. Coaching from Anthropic best practices, scoring from DeepEval, artifacts in MkDocs, optional Langfuse push.

**Keywords:** prompt engineering, prompt evaluation, RAG evaluation, tool evaluation, agent evaluation, DeepEval, Claude, Anthropic, LLM evals, Langfuse, MkDocs, Claude Code, AI agent skill
