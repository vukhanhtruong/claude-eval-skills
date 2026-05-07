---
name: prompt_eval
description: Build, test, and iteratively improve a Claude prompt with grounded coaching and empirical scoring. Walks the user through 5 steps applying Anthropic's prompt-engineering best practices, runs evaluations with DeepEval (Claude as judge), produces an MkDocs site, and proposes principle-grounded improvements.
argument-hint: [--prompt name] [--model haiku|sonnet|opus] [--judge-model haiku|sonnet|opus] [--cases N] [--resume run_NNN] [--list] [--list-prompts]
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
- Skip Steps 1 & 2 below; jump to Step 5 with the latest version's data.

Otherwise, start fresh from Step 1. Auto-increment run number: count existing `prompt_eval_runs/prompts/{prompt}/runs/run_*` directories (relative to the user's project dir); the new one is `run_{count+1:03d}`.

---

## Step 1 — Guided prompt building

Ask one question at a time. After each answer, apply the coaching prompts below if input is weak.

### Phase A: Task description (always)

Ask: "Describe the task in one specific sentence — what should Claude do?"

**Coaching: WHEN task is vague (< 10 words, no specific verb, no output type):**
> "Your task description is too broad — Claude needs specifics to perform well. What's the exact output you want? (a summary? a list? a rewrite?) What's the audience or purpose?"

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
  [--push-to-langfuse]
```

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
- Tell the user: "Comparison report at `http://127.0.0.1:8000/prompts/{prompt}/runs/run_NNN/comparison/` (if 2+ versions). All runs at `http://127.0.0.1:8000/`."
- Stop.
