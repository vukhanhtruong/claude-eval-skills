# Design: Claude-Native Grading for prompt_eval

**Date:** 2026-05-13  
**Status:** Approved  
**Breaking change:** Yes (clean break from v0.1.0-geval)

## Summary

Restructure the `prompt_eval` skill to eliminate the Anthropic API key dependency by having Claude Code perform all LLM work natively. Grading uses parallel subagents with a ported GEval methodology.

## Problem

The current implementation requires `ANTHROPIC_API_KEY` because:
- Python code calls the Anthropic API via the `anthropic` SDK
- DeepEval's GEval uses `AnthropicLLM` class for LLM-as-judge scoring
- External Python processes cannot access Claude Code's OAuth

Users without an API key cannot use the skill.

## Solution

Move all LLM work to Claude Code:
- **Main agent**: Dataset generation, prompt execution, tool mocking
- **Parallel subagents**: Grading (one per test case)
- **Python CLI**: Validation, aggregation, docs generation (no LLM calls)

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           /prompt_eval skill                            │
│                                                                         │
│  SKILL.md (LLM orchestrator)                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Step 1: Guided prompt building (main agent)                     │   │
│  │  Step 2: Dataset generation (main agent) → save via Python CLI   │   │
│  │  Step 3: Prompt execution + grading                              │   │
│  │          ├── Execute prompts (main agent) → save via Python CLI  │   │
│  │          └── Grade outputs (parallel subagents) → aggregate      │   │
│  │  Step 4: Show results (main agent)                               │   │
│  │  Step 5: Apply improvement (main agent)                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  /llm-judge skill (reusable grading methodology)                       │
│                                                                         │
│  Python CLI (validation + aggregation + docs)                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  DatasetHelper: validate_dataset(), save()                       │   │
│  │  ResultsHelper: validate_scores(), aggregate(), save()           │   │
│  │  Commands: save-dataset, save-output, save-scores, docs, show,   │   │
│  │            serve, stop                                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Grading Subagents

Main agent spawns N subagents (one per test case in dataset.json) in a single message for parallel execution.

```
Main agent reads dataset.json (N test cases)
    ↓
Spawn N subagents in parallel
    ↓
┌─────────────────┬─────────────────┬─────────────────┐
│   Subagent 0    │   Subagent 1    │   Subagent N    │
│   (Case 0)      │   (Case 1)      │   (Case N)      │
│                 │                 │                 │
│  GEval method   │  GEval method   │  GEval method   │
│  + criteria     │  + criteria     │  + criteria     │
│  + output       │  + output       │  + output       │
│                 │                 │                 │
│  → JSON result  │  → JSON result  │  → JSON result  │
└────────┬────────┴────────┬────────┴────────┬────────┘
         └────────────────┬┴─────────────────┘
                          ↓
              Main agent aggregates results
                          ↓
              prompt-eval save-scores --json '[...]'
```

Concurrency limit: Max 5 parallel subagents (rate limit safety).

## GEval Methodology (ported)

Each subagent follows this evaluation process:

1. **Understand the criteria** — list each criterion from `solution_criteria`
2. **Assess each criterion independently**:
   - Find evidence in output (quote relevant parts)
   - Assess: PASS | PARTIAL | FAIL
   - Brief explanation
3. **Calculate overall score** — PASS=1.0, PARTIAL=0.5, FAIL=0.0, average and scale to 1-10
4. **Synthesize reasoning** — 2-3 sentence summary

Output format:
```json
{
  "case_index": 0,
  "score": 8,
  "reasoning": "Meets criteria 1 and 2 fully. Criterion 3 partially met.",
  "criteria_breakdown": {
    "Criterion 1 text": "PASS",
    "Criterion 2 text": "PARTIAL"
  }
}
```

## File Structure

Unchanged from current:
```
<project>/prompt_eval_runs/
├── prompts/<prompt_name>/runs/run_NNN/
│   ├── dataset.json
│   ├── metadata.json
│   └── v1/
│       ├── prompt.txt
│       ├── output.json
│       └── scores.json    # NEW format with criteria_breakdown
└── docs-site/
```

## scores.json Format

```json
{
  "version": "v1",
  "cases": [
    {
      "case_index": 0,
      "scenario": "Tech startup pitch",
      "score": 8,
      "reasoning": "...",
      "criteria_breakdown": {
        "Summary under 100 words": "PASS",
        "Mentions key product benefit": "PASS",
        "Professional tone": "PARTIAL"
      }
    }
  ],
  "summary": {
    "average_score": 8.0,
    "pass_rate": 0.67,
    "total_cases": 3
  }
}
```

## Python CLI Changes

**Dependencies removed:**
- `anthropic`
- `deepeval`

**Dependencies kept:**
- `mkdocs-material`
- `pymdown-extensions`

**Refactored classes:**

| Old | New | Purpose |
|-----|-----|---------|
| `DatasetGenerator` | `DatasetHelper` | Validate and save dataset.json |
| `Evaluator` | `ResultsHelper` | Validate, aggregate, and save scores |

**CLI commands:**

| Command | Purpose |
|---------|---------|
| `save-dataset --prompt X --run-id Y --json '{...}'` | Validate + save dataset.json |
| `save-output --prompt X --run-id Y --version V --json '{...}'` | Save output.json |
| `save-scores --prompt X --run-id Y --version V --json '[...]'` | Validate + aggregate + save scores.json |
| `docs` | Regenerate mkdocs site |
| `show --prompt X --run-id Y --version V` | Display scores as table |
| `serve` | Start mkdocs server |
| `stop` | Stop mkdocs server |

## Files to Delete

| File | Reason |
|------|--------|
| `scripts/anthropic_llm.py` | No more direct API calls |
| `scripts/agentic_runner.py` | Tool mocking moves to main agent |
| `tests/test_anthropic_llm.py` | Testing deleted code |
| `tests/test_agentic_runner.py` | Testing deleted code |
| `tests/test_e2e.py` | Old e2e test |
| `tests/test_e2e_tools.py` | Old e2e test |
| `tests/test_evaluator_grade.py` | GEval-specific tests |

## New Files

| File | Purpose |
|------|---------|
| `.claude/skills/llm-judge/SKILL.md` | Reusable GEval methodology for subagents |
| `scripts/data_helpers.py` | DatasetHelper, ResultsHelper classes |

## Migration

- Git tag `v0.1.0-geval` preserves old version
- Clean break — old runs not resumable with new skill
- Users can checkout tag for old behavior

## Design Decisions

### Why parallel subagents for grading?

- 3 test cases × 1 evaluation time vs 3 sequential evaluations
- Each case has explicit `solution_criteria` — no cross-case calibration needed
- Token overhead (~1K extra per subagent) is negligible cost

### Why keep Python for validation/aggregation?

- Single source of truth for file formats
- Consistent aggregation logic (average_score, pass_rate)
- Schema validation catches Claude Code output errors
- Easier to test file operations

### Why clean break (no backwards compatibility)?

- Scores from different evaluators aren't comparable
- Mixing old/new scores in version history would be misleading
- Old version preserved via git tag
