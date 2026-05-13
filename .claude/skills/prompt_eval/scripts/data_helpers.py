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
