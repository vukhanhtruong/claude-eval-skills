# Prompting best-practices checklist

Distilled from <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices>. Apply this when editing prompts listed in [`CLAUDE.md`](CLAUDE.md). Each item is a yes/no review question — answer for the prompt you're editing, then act.

## 1. Be clear and direct

- [ ] Does the prompt state the task in one sentence at the top?
- [ ] Are inputs, constraints, and the success criterion named explicitly?
- [ ] Would a new contractor, given only this prompt, know what to produce?

## 2. Use examples (multishot)

- [ ] For non-trivial outputs, does the prompt include 1–3 worked examples?
- [ ] Do the examples cover the shape of inputs the prompt actually sees (typical + edge)?
- [ ] Are examples consistent in format with the requested output?

## 3. Let Claude think (chain of thought)

- [ ] Does the prompt invite reasoning before the answer (e.g., "think step by step", a `<thinking>` block, or numbered analysis)?
- [ ] For judge prompts: is the rubric reasoned through *before* the score is emitted, not after?

## 4. Use XML tags

- [ ] Are distinct sections (instructions, context, examples, input, output spec) wrapped in named XML tags (`<task>`, `<context>`, `<example>`, `<output>`, etc.)?
- [ ] Are tag names consistent across examples and the live input?

## 5. Give Claude a role

- [ ] If a persona helps (judge, critic, reviewer, coach), is it set in the system prompt or first line?
- [ ] Is the role specific (e.g., "an evaluator scoring rubric criterion X") rather than generic ("a helpful assistant")?

## 6. Specify output format

- [ ] Is the expected output format specified (JSON schema, plain-text shape, length cap)?
- [ ] For structured output: is there a worked example of the exact shape?
- [ ] If JSON: are field names and types named, and is "no extra prose" stated explicitly?

## 7. Prefill the response

- [ ] For API calls where structure matters, does the assistant turn prefill the opening token (`{` for JSON, `<analysis>` for XML, etc.)?
- [ ] Is the prefill consistent with the output format spec?

## 8. Long-context tips

- [ ] If the prompt includes long documents, are they placed *before* the instructions and wrapped in tags?
- [ ] Is the core instruction restated at the end, after the long context?

## 9. Decompose complex prompts (chaining)

- [ ] If the prompt does multiple unrelated things, can it be split into chained calls instead?
- [ ] Is each chained step doing one thing well?

---

## How to use

1. Identify the prompt you're editing (one of the files in [`CLAUDE.md`](CLAUDE.md) scope).
2. Walk this checklist top-to-bottom against the *post-edit* prompt.
3. For every "no", choose: **(a) fix it**, or **(b) document why it doesn't apply** — briefly, in the response to the user, or as a one-line comment above the prompt if the reason isn't obvious from context.
4. Continue with your change.
