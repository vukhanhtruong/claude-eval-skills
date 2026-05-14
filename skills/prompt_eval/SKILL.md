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

**If `--resume` is present but `--prompt` is missing:**

List all existing prompts with:
```bash
uvx --from "${CLAUDE_SKILL_DIR}" prompt-eval list-prompts
```

Ask:
> "Which prompt does `{run_id}` belong to? (Use the name from the list above)"

Wait for user response, then verify that `prompt_eval_runs/prompts/{prompt}/runs/{run_id}/dataset.json` exists. If not, list the runs for that prompt and ask the user to pick a valid run ID.

Once `--prompt` is known, proceed to the resume flow below.

**Otherwise, auto-generate from task description:**
1. Extract the task text from `$ARGUMENTS` (everything after flags).
2. Remove stop words: `the`, `a`, `an`, `from`, `for`, `with`, `to`, `in`, `on`, `of`, `and`, `or`, `that`, `this`, `it`.
3. Extract 2-4 key terms (prioritize nouns, verbs, proper nouns).
4. Join with underscores, lowercase: e.g., `ai_news_hackernoon`.

**Check for similar existing prompts:**
1. Run `prompt-eval list-prompts`.
2. For each existing prompt name, check if at least half the terms from the generated slug appear in it.
3. If a similar prompt exists:
   > "Found existing prompt '{name}' ({N} runs). Resume it or create '{generated_slug}'?"
   
   Wait for user response, then proceed.
4. If no similar prompt exists:
   > "Using prompt name: {generated_slug}"
   
   Proceed immediately.

**Fallback:** If `$ARGUMENTS` contains no task text or fewer than 3 words after stop-word removal, fall back to asking:
> "What prompt are you iterating on? Type a name (lowercase letters, digits, `_`, `-` only)."

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

**IF any signal matches → assume tools are needed. Show brief status and proceed.**

> "Detected tool need: `{inferred_tool_name}` ({brief justification}).
> Mocks will be generated during evaluation."

Set `tools_needed = true` and carry the assumed tool config to Phase H. Proceed immediately to Phase B (Inputs).

**Override:** User can interrupt with "change tool to X" or "remove tools" at any point.

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

### Phase B: Inputs (conditional)

**If `tools_needed = true` (from Phase A tool detection), skip to "No user inputs needed" below — the tools will fetch the data.**

**Analyze task for data source pattern:**

| Pattern detected | Inputs needed | Signals |
|------------------|---------------|---------|
| Tool-fetched data | None | URL, site name, API, "from [source]", real-time keywords (latest, current, today's) |
| User-provided data | Yes | "this", "my", "given", transform verbs with object (summarize this, convert my, analyze given) |
| Ambiguous | Ask once | Neither pattern clear |

**If no inputs needed (tool-fetched task):**
> "No user inputs needed — the AI will fetch data via tools.
> (Say 'add input' if you want to include any)"

Proceed immediately to Phase C.

**If inputs needed (user-provided task), show multiple choice:**
> "These are the inputs your prompt will receive. Select which to include:"
>
> [ ] `{suggested_input_1}` — {description}
> [ ] `{suggested_input_2}` — {description}
> [ ] `{suggested_input_3}` — {description} (optional)
> [ ] Other (specify your own)

Pre-select the most likely required inputs. Wait for user selection.

**Inference rules by task type:**

| Task type | Suggested inputs |
|-----------|------------------|
| Summarize/analyze content | `content`, `max_length` |
| Code review/fix | `code`, `language`, `context` |
| Translation | `text`, `target_language` |
| Data extraction | `source_data`, `fields_to_extract` |
| Q&A/RAG | `question`, `context_documents` |
| Comparison | `item_a`, `item_b`, `criteria` |

**Structure decision (after inputs determined):**
- 0 inputs → skip variable placeholders
- 1 short input → use `{var}` inline
- Multiple/long inputs → wrap in named XML block (e.g. `<article_content>...</article_content>`)

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

If Phase A flagged `tools_needed = true`, set up the tool config silently. **Do the work, log what you did, proceed without confirmation.**

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

Log the schema creation (no confirmation):
> "Created tool schema: `prompt_eval_runs/prompts/{prompt}/tools/{tool_name}.json`"

Proceed immediately to Step 3.

**Step 3: Store config (silent)**

- Builtin tool: add `--tools {name}` to all subsequent commands
- Custom tool: add `--tool-schema {path}` to all subsequent commands
- Both flags can be combined

**Override:** User can say "edit tool schema" to open the file for manual editing.

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

**If tools are configured, include a tools summary section:**

```
---
**Tools enabled:** {tool_name} ({builtin or custom})
**Mock strategy:** Haiku generates realistic responses per test case
---
```

Show this summary above the assembled prompt as a pre-header to the user; do not include it in `prompt.txt`.

Show the assembled prompt. Annotate which Anthropic principle each section serves. Ask:

> "Use as-is, edit inline, paste your own, or restart wizard?"

Save the chosen prompt to `prompt_eval_runs/prompts/{prompt}/runs/run_NNN/v1/prompt.txt` (create parent dirs as needed).

---

## Step 2 — Generate dataset

Generate {cases} diverse test cases for this task. For each case, create:

1. **scenario**: Brief description of what’s being tested (1 sentence)
2. **prompt_inputs**: Concrete values matching the input spec from Phase B
3. **solution_criteria**: 2-4 specific, measurable criteria for judging the output

Think through scenarios that test different aspects:
- Happy path (typical use case)
- Edge cases (empty input, very long input, special characters)
- Boundary conditions (limits, constraints)

Output as a JSON array. Example:
```json
[
  {
    "scenario": "Standard product description",
    "prompt_inputs": {"product": "Wireless headphones", "audience": "tech enthusiasts"},
    "solution_criteria": [
      "Mentions at least 2 key features",
      "Under 100 words",
      "Includes a call to action"
    ]
  },
  {
    "scenario": "Minimal input edge case",
    "prompt_inputs": {"product": "X", "audience": "general"},
    "solution_criteria": [
      "Handles short product name gracefully",
      "Still produces coherent output",
      "Under 100 words"
    ]
  }
]
```

After generating, save via CLI:
```bash
uvx --from "${CLAUDE_SKILL_DIR}" prompt-eval save-dataset \
  --prompt {prompt} \
  --run-id {run_id} \
  --json '{generated_json}'
```

Read `prompt_eval_runs/prompts/{prompt}/runs/{run_id}/dataset.json` and show the user a summary of each test case.

---

## Step 3 — Run + grade

### 3a. Execute prompts

For each test case in `dataset.json`:

1. Read the prompt template from `v{n}/prompt.txt`
2. Render: replace `{variable}` placeholders with values from `prompt_inputs`
3. Execute the rendered prompt (respond as the prompt instructs)
4. If tools are enabled and you need external data, generate a realistic mock response
5. Collect the output

After executing all cases, save outputs:
```bash
uvx --from "${CLAUDE_SKILL_DIR}" prompt-eval save-output \
  --prompt {prompt} \
  --run-id {run_id} \
  --version v{n} \
  --json '[{"case_index": 0, "output": "...", "tool_calls": []}, ...]'
```

### 3b. Grade outputs (parallel subagents)

Spawn one `llm-judge` subagent per test case. Send ALL Agent calls in a single message for parallel execution.

The `llm-judge` agent (defined in `.claude/agents/llm-judge.md`) implements the GEval methodology. Each subagent prompt provides the test case data:

**Subagent prompt template:**
```
## Test Case
case_index: {i}
scenario: {scenario}
prompt_inputs: {prompt_inputs as JSON}

## Solution Criteria
{criteria as bullet list}

## Output to Evaluate
{output text}
```

**Example spawning 3 subagents:**
```
Agent(description="Grade case 0", subagent_type="llm-judge", prompt="## Test Case\ncase_index: 0\n...")
Agent(description="Grade case 1", subagent_type="llm-judge", prompt="## Test Case\ncase_index: 1\n...")
Agent(description="Grade case 2", subagent_type="llm-judge", prompt="## Test Case\ncase_index: 2\n...")
```

Collect all subagent JSON results into an array, then save:
```bash
uvx --from "${CLAUDE_SKILL_DIR}" prompt-eval save-scores \
  --prompt {prompt} \
  --run-id {run_id} \
  --version v{n} \
  --json '[{subagent_0_result}, {subagent_1_result}, ...]'
```

The CLI validates scores and calculates summary statistics (average_score, pass_rate).

---

## Step 4 — Show results & analyze failures

Get the structured scoreboard:
```bash
uvx --from "${CLAUDE_SKILL_DIR}" prompt-eval show \
  --prompt {prompt} \
  --run-id {run_id} \
  --version v{n} \
  --json
```

Parse the JSON output. Render as this Markdown table:

| Scenario | Score | Criteria | Reasoning |
|----------|-------|----------|-----------|
| {scenario} | {score}/10 | {breakdown summary} | {reasoning} |

Print average score and pass rate from the summary.

**Analyze failures (score < 7):**

For each low-scoring case, examine the `criteria_breakdown`:
- Which criteria got FAIL or PARTIAL?
- What pattern emerges?

Use this table to suggest improvements:

| Pattern | Remedy |
|---------|--------|
| Output too long/short | Add explicit length constraint in prompt |
| Missing required element | Add example showing the element |
| Wrong format | Tighten output spec with exact format |
| Tone mismatch | Add or refine role |
| Hallucinated content | Add "quote from input only" rule |

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
