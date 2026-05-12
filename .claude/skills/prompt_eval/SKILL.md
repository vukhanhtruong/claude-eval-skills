---
name: prompt_eval
description: Build, test, and iteratively improve a Claude prompt with grounded coaching and empirical scoring. Walks the user through 5 steps applying Anthropic's prompt-engineering best practices, runs evaluations with DeepEval (Claude as judge), produces an MkDocs site, and proposes principle-grounded improvements.
argument-hint: "[--prompt name] [--model haiku|sonnet|opus] [--judge-model haiku|sonnet|opus] [--cases N] [--resume run_NNN] [--list] [--list-prompts] [--tools web_fetch,web_search] [--max-tool-turns N]"
allowed-tools: Read, Write, Edit, Bash
---

You are running the `/prompt_eval` workflow. Follow these steps strictly.

## What you get

After each evaluation, you get:

- A local **MkDocs site** (always, no setup) — for solo iteration
- An optional push to **Langfuse** (requires `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` in the environment) — for team review and historical comparison

Both run in the same workflow; Langfuse is purely additive.

## Argument parsing

Parse `$ARGUMENTS`:
- `--prompt <name>` — which prompt you're iterating on (e.g. `summarizer`, `code_reviewer`). Required for every flow except `--list-prompts`. Names must match `[a-z0-9_-]+`.
- `--model haiku|sonnet|opus` (default `haiku`) — model under test
- `--judge-model haiku|sonnet|opus` (default `sonnet`) — grader model
- `--cases N` (default `3`) — number of test cases
- `--resume run_NNN` — reopen an existing run (within the chosen `--prompt`)
- `--list` — list runs for the chosen `--prompt` and stop
- `--list-prompts` — list every prompt namespace with run counts and stop
- `--tools <list>` — comma-separated builtin tools to enable (e.g. `web_fetch,web_search`). When set, Claude can call these tools during evaluation and responses are mocked by Haiku. Builtins: `web_fetch`, `web_search`, `read_file`, `bash`.
- `--tool-schema <path>` — path to a custom tool schema JSON file (repeatable). Use for MCP tools or any non-builtin tool.
- `--max-tool-turns N` (default `5`) — maximum agentic turns per test case when tools are enabled

If `--list-prompts`:
```bash
uvx --from "${CLAUDE_SKILL_DIR}" prompt-eval list-prompts
```
Print output and stop.

If `--list` (requires `--prompt`):
```bash
uvx --from "${CLAUDE_SKILL_DIR}" prompt-eval list-runs --prompt {prompt}
```
Print output and stop.

If `--prompt` is missing for any flow other than `--list-prompts`:
- First, run `prompt-eval list-prompts` to show what's already in this project.
- Ask the user: "Which prompt are you iterating on? Pick one of the above, or type a new name (lowercase letters, digits, `_`, `-` only)."
- Use the user's answer as `--prompt` for the rest of the flow.

If `--resume {run_id}`:
- Verify `prompt_eval_runs/prompts/{prompt}/runs/{run_id}/dataset.json` exists (relative to the user's project dir). If not, run `prompt-eval list-runs --prompt {prompt}` and ask the user to pick.
- Read `prompt_eval_runs/prompts/{prompt}/runs/{run_id}/metadata.json`.
- Print: dataset size, prior versions, prior average scores, models used.
- If `metadata.json` contains `tools_config`, restore the tools settings for this session (tools list, max_tool_turns). Print: "Restoring tool config: --tools {tools} --max-tool-turns {N}"
- Skip Steps 1 & 2 below; jump to Step 5 with the latest version's data.

Otherwise, start fresh from Step 1. Auto-increment run number: count existing `prompt_eval_runs/prompts/{prompt}/runs/run_*` directories (relative to the user's project dir); the new one is `run_{count+1:03d}`.

---

## Step 1 — Guided prompt building

Ask one question at a time. After each answer, apply the coaching prompts below if input is weak.

### Phase A: Task description (always)

Ask: "Describe the task in one specific sentence — what should Claude do?"

**Coaching: WHEN task is vague (< 10 words, no specific verb, no output type):**
> "Your task description is too broad — Claude needs specifics to perform well. What's the exact output you want? (a summary? a list? a rewrite?) What's the audience or purpose?"

**Tool detection (ALWAYS run after Phase A — proactive, not optional):**

Analyze the task description for signals that Claude needs external data:
- **Explicit sources:** websites, URLs, domains (Hackernoon, Reddit, Twitter), APIs, MCP servers
- **Real-time data needs:** stock prices, weather, sports scores, currency rates, news
- **Current information:** "today's", "latest", "current", "now", "real-time"
- **Dynamic queries:** database lookups, user accounts, inventory, bookings
- **Domain-specific data:** flights, hotels, products, listings, market data

**IF any signal matches → assume tools are needed. Don't ask permission. Make the assumption, show it, let user override.**

> "This task needs external data Claude can't produce from training data alone. I'll assume the following tool setup — confirm or adjust:
>
> **Assumed tool:** `{inferred_tool_name}` (e.g. `get_stock_data`, `fetch_weather`, `web_fetch`)
> **Why:** {brief justification — 'stock analysis needs real-time market data'}
> **Mock strategy:** Haiku will generate realistic mock responses per test case (cached in `mocks.json`)
>
> Looks good? Or specify a different tool name?"

Set `tools_needed = true` and carry the assumed tool config to Phase H.

**Examples of tasks needing tools — assumption made by skill, not user:**
| Task description | Skill assumes tool | Skill auto-generates |
|---|---|---|
| "Summarize AI news from Hackernoon" | `web_fetch` (builtin) | URL → article content |
| "Get stock analysis for AAPL" | `get_stock_data` (custom) | Ticker → price/PE/volume |
| "Find current weather in Tokyo" | `get_weather` (custom) | City → temp/conditions |
| "Compare flight prices to NYC" | `search_flights` (custom) | Route → price list |
| "Latest crypto prices for BTC, ETH" | `get_crypto_price` (custom) | Symbol → USD price |
| "Summarize this article: [text]" | NO tools (content inline) | — |

**The skill does the work, not the user:** detects need → assumes tool → drafts schema → mocks data. User only confirms or overrides.

Optional follow-up: "Why does Claude need to do this? (Adding context helps Claude generalize.)"

### Phase B: Inputs (always)

Ask: "What variables will the prompt receive? List each as `name: description`."

Decide the structure:
- 1 short input → use `{var}` inline
- Multiple/long inputs → wrap them in a named XML block (e.g. `<athlete_information>...</athlete_information>`)

### Phase C: Output specification (always)

Ask: "What should the output look like? Format, length, structure?"

**Coaching: WHEN no output format described:**
> "What should the output look like? Format, length, structure? If you're unsure, I can suggest a default based on the task — say 'suggest'."

**Coaching: WHEN user uses negative phrasing ('don't use markdown'):**
> "Anthropic recommends telling Claude what TO do, not what NOT to do. Rewrite as: 'Use plain prose, no bullets or bold.' Apply this rewrite?"

### Phase D: Role (only if domain-specific)

If the task is in a specialized domain (medical, legal, code, finance, scientific, etc.), ask:

**Coaching: WHEN no role for a domain task:**
> "This task is domain-specific. A role like 'You are an expert {domain}' often improves accuracy. Want one? (yes / no / suggest)"

### Phase E: Examples (highly recommended)

Ask: "Provide 2–3 example input→output pairs. For each, briefly explain why the output is ideal."

**Coaching: WHEN zero examples provided:**
> "Examples are one of the most reliable ways to steer Claude (Anthropic recommends 3–5). They typically lift quality 20–30%. Options: (a) provide 2–3 examples, (b) let me draft candidates you can edit, (c) skip and rely on iteration. Pick one."

Wrap examples like this:

```
Here is an example input with an ideal response:
<example>
  <input>
    {input values}
  </input>
  <ideal_output>
    {output text}
  </ideal_output>
  <why_ideal>{why this output is correct}</why_ideal>
</example>
```

### Phase F: Failure modes (optional)

Ask: "Are there specific failure modes you've seen or anticipate?"

If yes, draft a targeted example covering that case and add it to the examples block.

### Phase G: Reasoning gate (only if task benefits from chain-of-thought)

Judge whether the task involves multi-step reasoning, comparison, judgment, or classification-with-rationale. If it's a single-shot transform, simple lookup, or format conversion, skip this phase silently.

**Coaching: WHEN task benefits from reasoning before output:**
> "This task involves {brief description of what Claude must reason through — e.g. 'weighing face shape, hair texture, and skin tone before each recommendation'}. Anthropic recommends letting Claude think first. Add a `<thinking>` block before the answer? (yes / no / suggest)"

If yes:
- Free-form output → add "Think step by step before responding." or wrap reasoning in `<thinking>...</thinking>`.
- Structured output (JSON/HTML) → keep reasoning inside `<thinking>` tags and add a final instruction: "After the `<thinking>` block, output ONLY the {format}."

### Phase H: Tool setup (only if `tools_needed = true` from Phase A)

If Phase A flagged `tools_needed = true`, proactively set up the tool config. **Do the work — don't ask the user to do it.**

**Step 1: Classify the assumed tool**

Check if the inferred tool name matches a builtin:
- `web_fetch`, `web_search`, `read_file`, `bash` → use `--tools {name}` (no schema needed)
- Anything else → custom tool, needs a schema

**Step 2: For custom tools, auto-draft the schema**

You (the skill orchestrator) have the task description and inferred tool name. Write the schema JSON file directly:

Path: `prompt_eval_runs/prompts/{prompt}/tools/{tool_name}.json`

Schema format (Anthropic tool spec):
```json
{
  "name": "{tool_name}",
  "description": "What this tool does (one sentence)",
  "input_schema": {
    "type": "object",
    "properties": {
      "{param_name}": {"type": "string", "description": "..."}
    },
    "required": ["{param_name}"]
  }
}
```

Infer parameters from the task: "stock analysis" → `ticker` param; "weather" → `location`; "flight search" → `origin`, `destination`, `date`. Use the Write tool to create the file.

Show the user the drafted schema:
> "Drafted tool schema at `prompt_eval_runs/prompts/{prompt}/tools/{tool_name}.json`:
> ```json
> {drafted_schema}
> ```
> Looks right? Or edit the file and I'll re-read it."

**Step 3: Confirm mock data strategy**

> "During evaluation, when Claude calls `{tool_name}`, Haiku will generate realistic mock responses per test case. For example:
>
> Input: `{example_args_from_test_case}`
> Mock output: `{example_mock_preview}`
>
> Mocks are cached in `mocks.json` so they're reproducible across versions."

**Step 4: Store config for `generate` and `evaluate`**

- Builtin tool: add `--tools {name}` to all subsequent commands
- Custom tool: add `--tool-schema {path}` to all subsequent commands
- Both flags can be combined (e.g. `--tools web_fetch --tool-schema custom.json`)

**Example end-to-end for "Get stock analysis for AAPL":**

```
Phase A → assumes tool: get_stock_data, reason: needs real-time market data
Phase H → drafts schema at prompt_eval_runs/prompts/stock_analyzer/tools/get_stock_data.json:
{
  "name": "get_stock_data",
  "description": "Fetch current stock data including price, PE ratio, volume",
  "input_schema": {
    "type": "object",
    "properties": {
      "ticker": {"type": "string", "description": "Stock ticker symbol"}
    },
    "required": ["ticker"]
  }
}

→ evaluate command:
uvx ... prompt-eval evaluate \
  --tool-schema prompt_eval_runs/prompts/stock_analyzer/tools/get_stock_data.json \
  ...

→ Claude calls get_stock_data({"ticker": "AAPL"})
→ ToolMocker generates: '{"price": 182.50, "pe": 28.5, "volume": 52M, "change": "+1.2%"}'
→ Claude produces stock analysis based on the mocked data
→ Mock cached in mocks.json for next version
```

### Coaching: WHEN instructions contradict
> "These conflict: '{a}' vs '{b}'. Resolve by picking one or describing the balance."

### Final assembly

Show the assembled prompt. Annotate which Anthropic principle each section serves. Ask:

> "Use as-is, edit inline, paste your own, or restart wizard?"

Save the chosen prompt to `prompt_eval_runs/prompts/{prompt}/runs/run_NNN/v1/prompt.txt` (create parent dirs as needed).

---

## Step 2 — Generate dataset

Run:
```bash
uvx --from "${CLAUDE_SKILL_DIR}" prompt-eval generate \
  --prompt {prompt} \
  --task "{task_description}" \
  --inputs '{inputs_spec_json}' \
  --num-cases {cases} \
  --model {model} \
  --run-id run_NNN
```

Read `prompt_eval_runs/prompts/{prompt}/runs/run_NNN/dataset.json`. Show the user a brief summary of each generated test case (scenario + key inputs).

---

## Step 3 — Run + grade

**Before the FIRST evaluate of this session:** check whether all three of `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and `LANGFUSE_HOST` are set in the environment. If they are, ask the user once:

> "Langfuse credentials detected. Push results to Langfuse for this run? [Y/n]"

If the user answers yes, add `--push-to-langfuse` to every `evaluate` invocation in this session. If no, omit the flag. Do not ask again unless the user explicitly changes their mind. If credentials are not all set, never ask — just proceed without the flag.

Run:
```bash
uvx --from "${CLAUDE_SKILL_DIR}" prompt-eval evaluate \
  --prompt {prompt} \
  --version v{n} \
  --model {model} \
  --judge-model {judge_model} \
  --run-id run_NNN \
  [--tools web_fetch,web_search] \
  [--tool-schema path/to/custom.json] \
  [--max-tool-turns N] \
  [--push-to-langfuse]
```

Include `--tools` and/or `--tool-schema` only if configured in Phase H. When tools are enabled:
- Claude can call them during evaluation
- `ToolMocker` generates realistic mock responses using Haiku (works for ANY tool, builtin or custom)
- Mocks are cached in `mocks.json` for reproducibility across versions

Stream output. When complete, the script auto-regenerates the docs site and starts `mkdocs serve` if it's not already running. The first invocation per project also bootstraps `prompt_eval_runs/docs-site/` from the bundled template.

If the output mentions `⚠ Langfuse flush failed`, run the suggested `prompt-eval push ...` command to retry. If the user said "no" earlier and changes their mind later, the same `prompt-eval push` command works retroactively.

(uvx builds the package from the skill dir on first run and caches it; subsequent invocations reuse the cached env.)

---

## Step 4 — Show results & analyze failures

Get the structured scoreboard:
```bash
uvx --from "${CLAUDE_SKILL_DIR}" prompt-eval show --prompt {prompt} --run-id run_NNN --version v{n} --json
```

Parse the JSON output (it has `run_id`, `version`, `average_score`, `pass_rate`, and a `cases` list with `scenario`, `score`, `output_length`, `reasoning` per case). Render it back to the user as this Markdown table:

| Scenario | Score | Reasoning |
|---|---|---|

Print average and pass rate. Print the URL to the version page (e.g. `http://127.0.0.1:8000/prompts/{prompt}/runs/run_001/v1/`).

**Baseline-coverage check (before failure analysis):** read `prompt_eval_runs/prompts/{prompt}/runs/run_NNN/v{n}/prompt.txt` and count `<example>` blocks. If zero, surface this as a recommendation alongside the #1 failure-pattern suggestion below:

> "Anthropic recommends 1–3 worked examples for non-trivial outputs; this prompt has none. Drafting 2–3 examples often lifts quality 20–30% — want me to draft candidates?"

Do not block iteration. The user may still proceed with the failure-pattern remedy or accept this recommendation instead.

Then analyze low-scoring cases (score < 7). For each, classify the failure pattern using this table:

| Pattern | Remedy |
|---|---|
| Wrong/missing output format | Tighten output spec; add example demonstrating exact format |
| Hallucinated values | Add "do not invent values; quote from input" rule + grounded example |
| Tone/expertise mismatch | Add or sharpen role |
| Ignored constraint | Move constraint into example with `<why_ideal>` annotation |
| Vague output | Add context (the "why") to drive specificity |
| Missed edge case | Add a few-shot example covering that case |

Pick the most prevalent pattern and remedy as the **#1 suggestion** for Step 5.

---

## Step 5 — Apply improvement

Offer:
> a) Apply Claude's #1 suggested fix (show diff first)
> b) Add a few-shot example built from a failed case
> c) Provide your own revised prompt
> d) Done

If a/b/c chosen:
- Compute the next version label `v{n+1}`.
- Save the new prompt to `prompt_eval_runs/prompts/{prompt}/runs/run_NNN/v{n+1}/prompt.txt` (create parent dirs as needed).
- Run Step 3 with `--version v{n+1}`.
- Run Step 4.
- Loop back to Step 5.

If d) Done:
- Stop the mkdocs server:
```bash
uvx --from "${CLAUDE_SKILL_DIR}" prompt-eval stop-server
```
- Tell the user: "Session complete. The mkdocs server has been stopped. To view results later, run `cd prompt_eval_runs/docs-site && uv run mkdocs serve`."
- Stop.
