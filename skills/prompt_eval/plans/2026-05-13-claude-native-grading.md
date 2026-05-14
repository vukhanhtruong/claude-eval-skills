# Claude-Native Grading Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure prompt_eval to eliminate Anthropic API key dependency by having Claude Code perform all LLM work natively.

**Architecture:** Main agent handles dataset generation and prompt execution. Parallel subagents handle grading using ported GEval methodology. Python CLI validates, aggregates, and generates docs.

**Tech Stack:** Python 3.12, pytest, mkdocs-material

---

## File Structure

**Create:**
- `scripts/data_helpers.py` — DatasetHelper, ResultsHelper classes
- `tests/test_data_helpers.py` — tests for validation and aggregation

**Modify:**
- `pyproject.toml` — remove anthropic, deepeval dependencies
- `scripts/run.py` — add save-dataset, save-output, save-scores commands; remove LLM-dependent code
- `SKILL.md` — update Steps 2, 3, 4 for native execution + subagent grading

**Delete:**
- `scripts/anthropic_llm.py`
- `scripts/agentic_runner.py`
- `scripts/evaluator.py` (replaced by data_helpers.py)
- `tests/test_anthropic_llm.py`
- `tests/test_agentic_runner.py`
- `tests/test_e2e.py`
- `tests/test_e2e_tools.py`
- `tests/test_evaluator_grade.py`
- `tests/test_dataset_generator.py`
- `tests/test_dataset_generator_no_prefill.py`
- `tests/test_evaluator_callback.py`
- `tests/test_evaluator_helpers.py`
- `tests/test_evaluator_pipeline.py`
- `tests/test_evaluator_run.py`
- `tests/test_evaluator_tools.py`

---

## Task 1: Create DatasetHelper with validation

**Files:**
- Create: `scripts/data_helpers.py`
- Create: `tests/test_data_helpers.py`

- [ ] **Step 1: Write failing test for DatasetHelper.validate**

```python
# tests/test_data_helpers.py
import pytest
from prompt_eval.data_helpers import DatasetHelper


class TestDatasetHelperValidate:
    def test_valid_dataset_returns_empty_errors(self):
        dataset = [
            {
                "scenario": "Test scenario",
                "prompt_inputs": {"topic": "AI"},
                "solution_criteria": ["Criterion 1", "Criterion 2"],
            }
        ]
        errors = DatasetHelper.validate(dataset)
        assert errors == []

    def test_missing_scenario_returns_error(self):
        dataset = [{"prompt_inputs": {}, "solution_criteria": ["C1"]}]
        errors = DatasetHelper.validate(dataset)
        assert "Case 0: missing 'scenario'" in errors

    def test_missing_prompt_inputs_returns_error(self):
        dataset = [{"scenario": "Test", "solution_criteria": ["C1"]}]
        errors = DatasetHelper.validate(dataset)
        assert "Case 0: missing 'prompt_inputs'" in errors

    def test_missing_solution_criteria_returns_error(self):
        dataset = [{"scenario": "Test", "prompt_inputs": {}}]
        errors = DatasetHelper.validate(dataset)
        assert "Case 0: missing 'solution_criteria'" in errors

    def test_empty_solution_criteria_returns_error(self):
        dataset = [{"scenario": "Test", "prompt_inputs": {}, "solution_criteria": []}]
        errors = DatasetHelper.validate(dataset)
        assert "Case 0: 'solution_criteria' is empty" in errors
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_data_helpers.py -v`
Expected: FAIL with "No module named 'prompt_eval.data_helpers'"

- [ ] **Step 3: Write minimal DatasetHelper.validate implementation**

```python
# scripts/data_helpers.py
"""Data validation and aggregation helpers for prompt_eval."""

from __future__ import annotations

import json
from pathlib import Path


class DatasetHelper:
    """Validate and save dataset files."""

    @staticmethod
    def validate(dataset: list[dict]) -> list[str]:
        """Return list of validation errors, empty if valid."""
        errors = []
        for i, case in enumerate(dataset):
            if "scenario" not in case:
                errors.append(f"Case {i}: missing 'scenario'")
            if "prompt_inputs" not in case:
                errors.append(f"Case {i}: missing 'prompt_inputs'")
            if "solution_criteria" not in case:
                errors.append(f"Case {i}: missing 'solution_criteria'")
            elif not case["solution_criteria"]:
                errors.append(f"Case {i}: 'solution_criteria' is empty")
        return errors
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_data_helpers.py::TestDatasetHelperValidate -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/data_helpers.py tests/test_data_helpers.py
git commit -m "feat(data_helpers): add DatasetHelper.validate"
```

---

## Task 2: Add DatasetHelper.save with validation

**Files:**
- Modify: `scripts/data_helpers.py`
- Modify: `tests/test_data_helpers.py`

- [ ] **Step 1: Write failing test for DatasetHelper.save**

```python
# tests/test_data_helpers.py (add to file)
class TestDatasetHelperSave:
    def test_save_writes_valid_dataset(self, tmp_path):
        dataset = [
            {
                "scenario": "Test",
                "prompt_inputs": {"x": "y"},
                "solution_criteria": ["C1"],
            }
        ]
        path = tmp_path / "runs" / "run_001" / "dataset.json"
        DatasetHelper.save(dataset, path)
        assert path.exists()
        saved = json.loads(path.read_text())
        assert saved == dataset

    def test_save_creates_parent_dirs(self, tmp_path):
        dataset = [
            {
                "scenario": "Test",
                "prompt_inputs": {},
                "solution_criteria": ["C1"],
            }
        ]
        path = tmp_path / "deep" / "nested" / "dataset.json"
        DatasetHelper.save(dataset, path)
        assert path.exists()

    def test_save_raises_on_invalid_dataset(self, tmp_path):
        dataset = [{"scenario": "Test"}]  # missing fields
        path = tmp_path / "dataset.json"
        with pytest.raises(ValueError, match="Invalid dataset"):
            DatasetHelper.save(dataset, path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_data_helpers.py::TestDatasetHelperSave -v`
Expected: FAIL with "AttributeError: type object 'DatasetHelper' has no attribute 'save'"

- [ ] **Step 3: Implement DatasetHelper.save**

```python
# scripts/data_helpers.py (add to DatasetHelper class)
    @staticmethod
    def save(dataset: list[dict], path: Path) -> None:
        """Validate and write dataset.json."""
        errors = DatasetHelper.validate(dataset)
        if errors:
            raise ValueError(f"Invalid dataset: {errors}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(dataset, indent=2))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_data_helpers.py::TestDatasetHelperSave -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/data_helpers.py tests/test_data_helpers.py
git commit -m "feat(data_helpers): add DatasetHelper.save"
```

---

## Task 3: Create ResultsHelper with score validation

**Files:**
- Modify: `scripts/data_helpers.py`
- Modify: `tests/test_data_helpers.py`

- [ ] **Step 1: Write failing test for ResultsHelper.validate_scores**

```python
# tests/test_data_helpers.py (add to file)
from prompt_eval.data_helpers import ResultsHelper


class TestResultsHelperValidate:
    def test_valid_scores_returns_empty_errors(self):
        scores = [
            {
                "case_index": 0,
                "score": 8,
                "reasoning": "Good output",
                "criteria_breakdown": {"C1": "PASS"},
            }
        ]
        errors = ResultsHelper.validate_scores(scores)
        assert errors == []

    def test_missing_score_returns_error(self):
        scores = [{"case_index": 0, "reasoning": "X", "criteria_breakdown": {}}]
        errors = ResultsHelper.validate_scores(scores)
        assert "Score 0: invalid score" in errors

    def test_score_out_of_range_returns_error(self):
        scores = [
            {"case_index": 0, "score": 11, "reasoning": "X", "criteria_breakdown": {}}
        ]
        errors = ResultsHelper.validate_scores(scores)
        assert "Score 0: invalid score" in errors

    def test_missing_reasoning_returns_error(self):
        scores = [{"case_index": 0, "score": 8, "criteria_breakdown": {}}]
        errors = ResultsHelper.validate_scores(scores)
        assert "Score 0: missing 'reasoning'" in errors

    def test_missing_criteria_breakdown_returns_error(self):
        scores = [{"case_index": 0, "score": 8, "reasoning": "X"}]
        errors = ResultsHelper.validate_scores(scores)
        assert "Score 0: missing 'criteria_breakdown'" in errors
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_data_helpers.py::TestResultsHelperValidate -v`
Expected: FAIL with "cannot import name 'ResultsHelper'"

- [ ] **Step 3: Implement ResultsHelper.validate_scores**

```python
# scripts/data_helpers.py (add class)
class ResultsHelper:
    """Validate, aggregate, and save evaluation results."""

    @staticmethod
    def validate_scores(scores: list[dict]) -> list[str]:
        """Return list of validation errors."""
        errors = []
        for i, s in enumerate(scores):
            if "score" not in s or not (1 <= s.get("score", 0) <= 10):
                errors.append(f"Score {i}: invalid score")
            if "reasoning" not in s:
                errors.append(f"Score {i}: missing 'reasoning'")
            if "criteria_breakdown" not in s:
                errors.append(f"Score {i}: missing 'criteria_breakdown'")
        return errors
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_data_helpers.py::TestResultsHelperValidate -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/data_helpers.py tests/test_data_helpers.py
git commit -m "feat(data_helpers): add ResultsHelper.validate_scores"
```

---

## Task 4: Add ResultsHelper.aggregate

**Files:**
- Modify: `scripts/data_helpers.py`
- Modify: `tests/test_data_helpers.py`

- [ ] **Step 1: Write failing test for ResultsHelper.aggregate**

```python
# tests/test_data_helpers.py (add to file)
class TestResultsHelperAggregate:
    def test_aggregate_calculates_average(self):
        scores = [
            {"score": 8, "reasoning": "X", "criteria_breakdown": {}},
            {"score": 6, "reasoning": "X", "criteria_breakdown": {}},
            {"score": 10, "reasoning": "X", "criteria_breakdown": {}},
        ]
        result = ResultsHelper.aggregate(scores)
        assert result["average_score"] == 8.0

    def test_aggregate_calculates_pass_rate(self):
        scores = [
            {"score": 8, "reasoning": "X", "criteria_breakdown": {}},  # pass
            {"score": 6, "reasoning": "X", "criteria_breakdown": {}},  # fail
            {"score": 7, "reasoning": "X", "criteria_breakdown": {}},  # pass
        ]
        result = ResultsHelper.aggregate(scores)
        assert result["pass_rate"] == 0.67  # 2/3 rounded

    def test_aggregate_includes_total_cases(self):
        scores = [
            {"score": 8, "reasoning": "X", "criteria_breakdown": {}},
            {"score": 6, "reasoning": "X", "criteria_breakdown": {}},
        ]
        result = ResultsHelper.aggregate(scores)
        assert result["total_cases"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_data_helpers.py::TestResultsHelperAggregate -v`
Expected: FAIL with "AttributeError: type object 'ResultsHelper' has no attribute 'aggregate'"

- [ ] **Step 3: Implement ResultsHelper.aggregate**

```python
# scripts/data_helpers.py (add to ResultsHelper class)
    @staticmethod
    def aggregate(scores: list[dict]) -> dict:
        """Calculate summary statistics."""
        values = [s["score"] for s in scores]
        return {
            "average_score": round(sum(values) / len(values), 2),
            "pass_rate": round(sum(1 for v in values if v >= 7) / len(values), 2),
            "total_cases": len(values),
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_data_helpers.py::TestResultsHelperAggregate -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/data_helpers.py tests/test_data_helpers.py
git commit -m "feat(data_helpers): add ResultsHelper.aggregate"
```

---

## Task 5: Add ResultsHelper.save

**Files:**
- Modify: `scripts/data_helpers.py`
- Modify: `tests/test_data_helpers.py`

- [ ] **Step 1: Write failing test for ResultsHelper.save**

```python
# tests/test_data_helpers.py (add to file)
class TestResultsHelperSave:
    def test_save_writes_scores_with_summary(self, tmp_path):
        scores = [
            {
                "case_index": 0,
                "scenario": "Test",
                "score": 8,
                "reasoning": "Good",
                "criteria_breakdown": {"C1": "PASS"},
            }
        ]
        path = tmp_path / "v1" / "scores.json"
        ResultsHelper.save(scores, "v1", path)
        assert path.exists()
        saved = json.loads(path.read_text())
        assert saved["version"] == "v1"
        assert saved["cases"] == scores
        assert "summary" in saved
        assert saved["summary"]["average_score"] == 8.0

    def test_save_raises_on_invalid_scores(self, tmp_path):
        scores = [{"score": 8}]  # missing fields
        path = tmp_path / "scores.json"
        with pytest.raises(ValueError, match="Invalid scores"):
            ResultsHelper.save(scores, "v1", path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_data_helpers.py::TestResultsHelperSave -v`
Expected: FAIL with "AttributeError: type object 'ResultsHelper' has no attribute 'save'"

- [ ] **Step 3: Implement ResultsHelper.save**

```python
# scripts/data_helpers.py (add to ResultsHelper class)
    @staticmethod
    def save(scores: list[dict], version: str, path: Path) -> None:
        """Validate, aggregate, and write scores.json."""
        errors = ResultsHelper.validate_scores(scores)
        if errors:
            raise ValueError(f"Invalid scores: {errors}")
        result = {
            "version": version,
            "cases": scores,
            "summary": ResultsHelper.aggregate(scores),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_data_helpers.py::TestResultsHelperSave -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/data_helpers.py tests/test_data_helpers.py
git commit -m "feat(data_helpers): add ResultsHelper.save"
```

---

## Task 6: Add OutputHelper for output.json

**Files:**
- Modify: `scripts/data_helpers.py`
- Modify: `tests/test_data_helpers.py`

- [ ] **Step 1: Write failing test for OutputHelper**

```python
# tests/test_data_helpers.py (add to file)
from prompt_eval.data_helpers import OutputHelper


class TestOutputHelper:
    def test_save_writes_outputs(self, tmp_path):
        outputs = [
            {"case_index": 0, "output": "Response text", "tool_calls": []},
            {"case_index": 1, "output": "Another response", "tool_calls": []},
        ]
        path = tmp_path / "v1" / "output.json"
        OutputHelper.save(outputs, path)
        assert path.exists()
        saved = json.loads(path.read_text())
        assert saved == outputs

    def test_save_creates_parent_dirs(self, tmp_path):
        outputs = [{"case_index": 0, "output": "X", "tool_calls": []}]
        path = tmp_path / "deep" / "nested" / "output.json"
        OutputHelper.save(outputs, path)
        assert path.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_data_helpers.py::TestOutputHelper -v`
Expected: FAIL with "cannot import name 'OutputHelper'"

- [ ] **Step 3: Implement OutputHelper**

```python
# scripts/data_helpers.py (add class)
class OutputHelper:
    """Save prompt execution outputs."""

    @staticmethod
    def save(outputs: list[dict], path: Path) -> None:
        """Write output.json."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(outputs, indent=2))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_data_helpers.py::TestOutputHelper -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/data_helpers.py tests/test_data_helpers.py
git commit -m "feat(data_helpers): add OutputHelper"
```

---

## Task 7: Update pyproject.toml dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Read current pyproject.toml**

Run: `cat pyproject.toml`

- [ ] **Step 2: Remove anthropic and deepeval dependencies**

Edit `pyproject.toml` to change dependencies from:
```toml
dependencies = [
    "anthropic>=0.97.0",
    "deepeval>=2.0",
    "langfuse>=4.0",
    "mkdocs-material>=9.5",
    "pymdown-extensions>=10.7",
    "python-dotenv>=1.2.2",
]
```

To:
```toml
dependencies = [
    "mkdocs-material>=9.5",
    "pymdown-extensions>=10.7",
]
```

- [ ] **Step 3: Run uv sync to update lockfile**

Run: `uv sync`
Expected: Dependencies updated, lockfile regenerated

- [ ] **Step 4: Verify pytest still works**

Run: `uv run pytest tests/test_data_helpers.py -v`
Expected: PASS (all data_helpers tests)

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore(deps): remove anthropic, deepeval dependencies"
```

---

## Task 8: Add CLI save-dataset command

**Files:**
- Modify: `scripts/run.py`
- Create: `tests/test_run_save_dataset.py`

- [ ] **Step 1: Write failing test for save-dataset command**

```python
# tests/test_run_save_dataset.py
import json
import pytest
from prompt_eval.run import _do_save_dataset


class TestSaveDataset:
    def test_saves_valid_dataset(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
        dataset = [
            {
                "scenario": "Test",
                "prompt_inputs": {"x": "y"},
                "solution_criteria": ["C1"],
            }
        ]
        _do_save_dataset(
            prompt_name="test_prompt",
            run_id="run_001",
            json_data=json.dumps(dataset),
        )
        path = tmp_path / "prompt_eval_runs" / "prompts" / "test_prompt" / "runs" / "run_001" / "dataset.json"
        assert path.exists()
        saved = json.loads(path.read_text())
        assert saved == dataset

    def test_rejects_invalid_dataset(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
        dataset = [{"scenario": "Test"}]  # missing fields
        with pytest.raises(ValueError, match="Invalid dataset"):
            _do_save_dataset(
                prompt_name="test_prompt",
                run_id="run_001",
                json_data=json.dumps(dataset),
            )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_run_save_dataset.py -v`
Expected: FAIL with "cannot import name '_do_save_dataset'"

- [ ] **Step 3: Implement _do_save_dataset in run.py**

Add to `scripts/run.py`:
```python
from prompt_eval.data_helpers import DatasetHelper

def _do_save_dataset(prompt_name: str, run_id: str, json_data: str) -> None:
    """Validate and save dataset.json."""
    import json
    dataset = json.loads(json_data)
    root = _resolve_artifact_root()
    path = root / "prompts" / prompt_name / "runs" / run_id / "dataset.json"
    DatasetHelper.save(dataset, path)
    print(f"Saved dataset to {path}")
```

Add argparse subcommand in `main()`:
```python
save_dataset_parser = subparsers.add_parser("save-dataset", help="Save dataset.json")
save_dataset_parser.add_argument("--prompt", required=True)
save_dataset_parser.add_argument("--run-id", required=True)
save_dataset_parser.add_argument("--json", required=True, dest="json_data")
```

Add handler:
```python
elif args.command == "save-dataset":
    _do_save_dataset(args.prompt, args.run_id, args.json_data)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_run_save_dataset.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/run.py tests/test_run_save_dataset.py
git commit -m "feat(cli): add save-dataset command"
```

---

## Task 9: Add CLI save-output command

**Files:**
- Modify: `scripts/run.py`
- Create: `tests/test_run_save_output.py`

- [ ] **Step 1: Write failing test for save-output command**

```python
# tests/test_run_save_output.py
import json
import pytest
from prompt_eval.run import _do_save_output


class TestSaveOutput:
    def test_saves_outputs(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
        outputs = [
            {"case_index": 0, "output": "Response", "tool_calls": []},
        ]
        _do_save_output(
            prompt_name="test_prompt",
            run_id="run_001",
            version="v1",
            json_data=json.dumps(outputs),
        )
        path = tmp_path / "prompt_eval_runs" / "prompts" / "test_prompt" / "runs" / "run_001" / "v1" / "output.json"
        assert path.exists()
        saved = json.loads(path.read_text())
        assert saved == outputs
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_run_save_output.py -v`
Expected: FAIL with "cannot import name '_do_save_output'"

- [ ] **Step 3: Implement _do_save_output in run.py**

Add to `scripts/run.py`:
```python
from prompt_eval.data_helpers import OutputHelper

def _do_save_output(prompt_name: str, run_id: str, version: str, json_data: str) -> None:
    """Save output.json."""
    import json
    outputs = json.loads(json_data)
    root = _resolve_artifact_root()
    path = root / "prompts" / prompt_name / "runs" / run_id / version / "output.json"
    OutputHelper.save(outputs, path)
    print(f"Saved outputs to {path}")
```

Add argparse subcommand and handler similarly to save-dataset.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_run_save_output.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add scripts/run.py tests/test_run_save_output.py
git commit -m "feat(cli): add save-output command"
```

---

## Task 10: Add CLI save-scores command

**Files:**
- Modify: `scripts/run.py`
- Create: `tests/test_run_save_scores.py`

- [ ] **Step 1: Write failing test for save-scores command**

```python
# tests/test_run_save_scores.py
import json
import pytest
from prompt_eval.run import _do_save_scores


class TestSaveScores:
    def test_saves_scores_with_aggregation(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
        scores = [
            {
                "case_index": 0,
                "scenario": "Test",
                "score": 8,
                "reasoning": "Good",
                "criteria_breakdown": {"C1": "PASS"},
            },
        ]
        _do_save_scores(
            prompt_name="test_prompt",
            run_id="run_001",
            version="v1",
            json_data=json.dumps(scores),
        )
        path = tmp_path / "prompt_eval_runs" / "prompts" / "test_prompt" / "runs" / "run_001" / "v1" / "scores.json"
        assert path.exists()
        saved = json.loads(path.read_text())
        assert saved["version"] == "v1"
        assert saved["cases"] == scores
        assert saved["summary"]["average_score"] == 8.0

    def test_rejects_invalid_scores(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROMPT_EVAL_PROJECT_DIR", str(tmp_path))
        scores = [{"score": 8}]  # missing fields
        with pytest.raises(ValueError, match="Invalid scores"):
            _do_save_scores(
                prompt_name="test_prompt",
                run_id="run_001",
                version="v1",
                json_data=json.dumps(scores),
            )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_run_save_scores.py -v`
Expected: FAIL with "cannot import name '_do_save_scores'"

- [ ] **Step 3: Implement _do_save_scores in run.py**

Add to `scripts/run.py`:
```python
from prompt_eval.data_helpers import ResultsHelper

def _do_save_scores(prompt_name: str, run_id: str, version: str, json_data: str) -> None:
    """Validate, aggregate, and save scores.json."""
    import json
    scores = json.loads(json_data)
    root = _resolve_artifact_root()
    path = root / "prompts" / prompt_name / "runs" / run_id / version / "scores.json"
    ResultsHelper.save(scores, version, path)
    print(f"Saved scores to {path}")
```

Add argparse subcommand and handler.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_run_save_scores.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/run.py tests/test_run_save_scores.py
git commit -m "feat(cli): add save-scores command"
```

---

## Task 11: Delete old LLM-dependent files

**Files:**
- Delete: `scripts/anthropic_llm.py`
- Delete: `scripts/agentic_runner.py`
- Delete: `scripts/evaluator.py`

- [ ] **Step 1: Identify imports of deleted modules**

Run: `grep -r "from prompt_eval.evaluator\|from prompt_eval.anthropic_llm\|from prompt_eval.agentic_runner" scripts/ tests/`

- [ ] **Step 2: Delete the files**

```bash
rm scripts/anthropic_llm.py scripts/agentic_runner.py scripts/evaluator.py
```

- [ ] **Step 3: Update any remaining imports in run.py**

Remove imports from `scripts/run.py`:
- `from prompt_eval.evaluator import ...`
- `from prompt_eval.anthropic_llm import ...`

Remove functions that depend on deleted code:
- `_do_generate` (dataset generation now done by Claude Code)
- `_do_evaluate` (evaluation now done by Claude Code + subagents)

Keep these functions (still needed):
- `_do_show`, `_do_list_runs`, `_do_list_prompts`, `_do_docs`, etc.

- [ ] **Step 4: Verify no import errors**

Run: `uv run python -c "from prompt_eval.run import main; print('OK')"`
Expected: "OK"

- [ ] **Step 5: Commit**

```bash
git add -u scripts/
git commit -m "refactor(cli): remove LLM-dependent code"
```

---

## Task 12: Delete old tests

**Files:**
- Delete multiple test files

- [ ] **Step 1: Delete tests for removed code**

```bash
rm tests/test_anthropic_llm.py
rm tests/test_agentic_runner.py
rm tests/test_e2e.py
rm tests/test_e2e_tools.py
rm tests/test_evaluator_grade.py
rm tests/test_dataset_generator.py
rm tests/test_dataset_generator_no_prefill.py
rm tests/test_evaluator_callback.py
rm tests/test_evaluator_helpers.py
rm tests/test_evaluator_pipeline.py
rm tests/test_evaluator_run.py
rm tests/test_evaluator_tools.py
```

- [ ] **Step 2: Update conftest.py if needed**

Remove any fixtures related to deleted code (e.g., `mock_anthropic_client`).

- [ ] **Step 3: Run remaining tests**

Run: `uv run pytest tests/ -v --ignore=tests/test_langfuse_e2e.py`
Expected: All remaining tests pass

- [ ] **Step 4: Commit**

```bash
git add -u tests/
git commit -m "test: remove tests for deleted LLM code"
```

---

## Task 13: Update SKILL.md Step 2 (Dataset Generation)

**Files:**
- Modify: `SKILL.md`

- [ ] **Step 1: Read current Step 2 in SKILL.md**

Find the section starting with `## Step 2 — Generate dataset`

- [ ] **Step 2: Replace with Claude Code native generation**

Replace the uvx generate command section with:

```markdown
## Step 2 — Generate dataset

Generate {cases} diverse test cases for this task. For each case, create:

1. **scenario**: Brief description of what's being tested (1 sentence)
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
```

- [ ] **Step 3: Verify SKILL.md syntax**

Run: `head -300 SKILL.md | tail -100` to check the edited section looks correct.

- [ ] **Step 4: Commit**

```bash
git add SKILL.md
git commit -m "docs(skill): update Step 2 for Claude-native dataset generation"
```

---

## Task 14: Update SKILL.md Step 3 (Execution + Grading)

**Files:**
- Modify: `SKILL.md`

- [ ] **Step 1: Read current Step 3**

Find the section starting with `## Step 3 — Run + grade`

- [ ] **Step 2: Replace with Claude Code native execution + subagent grading**

```markdown
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

Spawn one grading subagent per test case. Send ALL Agent calls in a single message for parallel execution.

For each test case, the subagent prompt includes:
- The test case (scenario, prompt_inputs, solution_criteria)  
- The output to evaluate
- The GEval methodology (below)
- Expected JSON output format

**Subagent prompt template:**
```
You are a grading subagent. Evaluate this output using the GEval methodology.

## Test Case
Scenario: {scenario}
Inputs: {prompt_inputs as JSON}

## Solution Criteria
{criteria as bullet list}

## Output to Evaluate
{output text}

## GEval Methodology

1. **List criteria**: Write out each criterion from solution_criteria.

2. **Assess each criterion**:
   For each criterion:
   - Quote evidence from the output (or note absence)
   - Assess: PASS (fully met) | PARTIAL (partially met) | FAIL (not met)
   - Brief explanation (1 sentence)

3. **Calculate score**:
   - PASS = 1.0, PARTIAL = 0.5, FAIL = 0.0
   - Average across criteria
   - Scale to 1-10 (multiply by 10)
   - Round to nearest integer

4. **Write reasoning**: 2-3 sentences summarizing the assessment.

## Output Format
Return ONLY this JSON, no markdown fences:
{"case_index": {i}, "scenario": "{scenario}", "score": 1-10, "reasoning": "...", "criteria_breakdown": {"Criterion 1": "PASS", "Criterion 2": "PARTIAL"}}
```

**Example spawning 3 subagents:**
```
Agent(description="Grade case 0", prompt="...case 0 context...")
Agent(description="Grade case 1", prompt="...case 1 context...")
Agent(description="Grade case 2", prompt="...case 2 context...")
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
```

- [ ] **Step 3: Commit**

```bash
git add SKILL.md
git commit -m "docs(skill): update Step 3 for native execution + subagent grading"
```

---

## Task 15: Update SKILL.md Step 4 (Show Results)

**Files:**
- Modify: `SKILL.md`

- [ ] **Step 1: Update Step 4 to read new scores.json format**

The `show` command output format changes slightly. Update Step 4 to reflect:

```markdown
## Step 4 — Show results & analyze failures

Read scores from:
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
```

- [ ] **Step 2: Commit**

```bash
git add SKILL.md
git commit -m "docs(skill): update Step 4 for new scores.json format"
```

---

## Task 16: Update docs_generator.py for new scores format

**Files:**
- Modify: `scripts/docs_generator.py`
- Modify: `tests/test_docs_generator_main.py`

- [ ] **Step 1: Check current scores reading logic**

Run: `grep -n "score\|reasoning" scripts/docs_generator.py | head -20`

- [ ] **Step 2: Update to read new scores.json structure**

The new format has `cases` array with `criteria_breakdown`. Update `_build_version_page` to render the criteria breakdown.

- [ ] **Step 3: Run docs generator tests**

Run: `uv run pytest tests/test_docs_generator_main.py -v`
Expected: Tests may fail if they use old format - update test fixtures

- [ ] **Step 4: Fix any failing tests**

Update test fixtures to use new scores.json format.

- [ ] **Step 5: Commit**

```bash
git add scripts/docs_generator.py tests/test_docs_generator*.py
git commit -m "feat(docs): update docs generator for new scores format"
```

---

## Task 17: Run full test suite and fix issues

**Files:**
- Various test files

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest tests/ -v --ignore=tests/test_langfuse_e2e.py`

- [ ] **Step 2: Fix any import errors**

Look for tests that import from deleted modules and either:
- Delete the test (if testing deleted functionality)
- Update the import (if testing functionality that moved)

- [ ] **Step 3: Fix any fixture issues**

Update `conftest.py` to remove unused fixtures.

- [ ] **Step 4: Verify all tests pass**

Run: `uv run pytest tests/ -v --ignore=tests/test_langfuse_e2e.py`
Expected: All tests pass

- [ ] **Step 5: Commit any fixes**

```bash
git add tests/
git commit -m "test: fix remaining test issues after refactor"
```

---

## Task 18: Update CLAUDE.md

**Files:**
- Modify: `../../CLAUDE.md` (repo root)

- [ ] **Step 1: Update architecture section**

Remove references to:
- `anthropic` and `deepeval` dependencies
- `AnthropicLLM` class
- `DatasetGenerator` and `Evaluator` classes (replace with new names)

Add:
- `DatasetHelper`, `ResultsHelper`, `OutputHelper` classes
- New CLI commands: `save-dataset`, `save-output`, `save-scores`
- Mention that all LLM work is done by Claude Code natively

- [ ] **Step 2: Update commands section**

Update the CLI command examples to show new commands.

- [ ] **Step 3: Commit**

```bash
git add ../../CLAUDE.md
git commit -m "docs: update CLAUDE.md for Claude-native architecture"
```

---

## Task 19: Final verification

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests pass (except langfuse e2e which needs credentials)

- [ ] **Step 2: Verify CLI help**

Run: `uv run prompt-eval --help`
Expected: Shows new commands (save-dataset, save-output, save-scores)

- [ ] **Step 3: Verify no anthropic/deepeval imports remain**

Run: `grep -r "import anthropic\|import deepeval\|from anthropic\|from deepeval" scripts/`
Expected: No matches

- [ ] **Step 4: Create completion commit**

```bash
git add -A
git commit -m "feat: complete Claude-native grading restructure

BREAKING CHANGE: Removes anthropic and deepeval dependencies.
All LLM work now done by Claude Code natively.

- Dataset generation: main agent
- Prompt execution: main agent  
- Grading: parallel subagents with GEval methodology
- Python CLI: validation, aggregation, docs only

Old runs are not compatible. Use git tag v0.1.0-geval for old behavior."
```

- [ ] **Step 5: Tag new version**

```bash
git tag -a v0.2.0-claude-native -m "Claude-native grading (no API key required)"
```
