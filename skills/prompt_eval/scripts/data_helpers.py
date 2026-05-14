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

    @staticmethod
    def save(dataset: list[dict], path: Path) -> None:
        """Validate and write dataset.json."""
        errors = DatasetHelper.validate(dataset)
        if errors:
            raise ValueError(f"Invalid dataset: {errors}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(dataset, indent=2))


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

    @staticmethod
    def aggregate(scores: list[dict]) -> dict:
        """Calculate summary statistics."""
        values = [s["score"] for s in scores]
        return {
            "average_score": round(sum(values) / len(values), 2),
            "pass_rate": round(sum(1 for v in values if v >= 7) / len(values), 2),
            "total_cases": len(values),
        }

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


class OutputHelper:
    """Save prompt execution outputs."""

    FORBIDDEN_KEYS = frozenset(
        {"score", "reasoning", "criteria_breakdown", "test_case", "scenario"}
    )
    REQUIRED_KEYS = frozenset({"case_index", "output"})

    @staticmethod
    def validate(outputs: list[dict]) -> list[str]:
        """Return list of validation errors. Empty list = valid."""
        errors = []
        for i, o in enumerate(outputs):
            if not isinstance(o, dict):
                errors.append(f"Output {i}: expected dict, got {type(o).__name__}")
                continue
            leaked = OutputHelper.FORBIDDEN_KEYS & o.keys()
            if leaked:
                errors.append(
                    f"Output {i}: contains scoring keys {sorted(leaked)} — "
                    f"those belong in save-scores, not save-output"
                )
            missing = OutputHelper.REQUIRED_KEYS - o.keys()
            if missing:
                errors.append(
                    f"Output {i}: missing required keys {sorted(missing)}"
                )
        return errors

    @staticmethod
    def save(outputs: list[dict], path: Path) -> None:
        """Validate schema, then write output.json. Rejects payloads carrying
        scoring fields (score / reasoning / criteria_breakdown / test_case /
        scenario) — those belong in save-scores."""
        errors = OutputHelper.validate(outputs)
        if errors:
            raise ValueError(f"Invalid outputs: {errors}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(outputs, indent=2))
