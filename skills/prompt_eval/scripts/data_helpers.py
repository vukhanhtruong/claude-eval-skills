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
    def save(scores: list[dict], version: str, path: Path, model: str | None = None) -> None:
        """Validate schema and model lock, then write scores.json with aggregate
        summary. Rejects model mismatches when the run's models are locked."""
        errors = ResultsHelper.validate_scores(scores)
        if errors:
            raise ValueError(f"Invalid scores: {errors}")
        ResultsHelper._check_model_lock(path.parent.parent, model)
        result = {
            "version": version,
            "cases": scores,
            "summary": ResultsHelper.aggregate(scores),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2))

    @staticmethod
    def _check_model_lock(run_dir: Path, model: str | None) -> None:
        meta = MetadataHelper.read(run_dir)
        if not meta.get("models_locked"):
            return
        locked = meta.get("judge_model")
        if model is None:
            raise ValueError(f"Run has locked judge_model={locked!r}; pass --model")
        if model != locked:
            raise ValueError(
                f"--model {model!r} disagrees with locked judge_model={locked!r}"
            )


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
    def save(outputs: list[dict], path: Path, model: str | None = None) -> None:
        """Validate schema and model lock, then write output.json. Rejects payloads
        carrying scoring fields. Rejects model mismatches when the run's models
        are locked via MetadataHelper.set_models."""
        errors = OutputHelper.validate(outputs)
        if errors:
            raise ValueError(f"Invalid outputs: {errors}")
        OutputHelper._check_model_lock(path.parent.parent, model)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(outputs, indent=2))

    @staticmethod
    def _check_model_lock(run_dir: Path, model: str | None) -> None:
        meta = MetadataHelper.read(run_dir)
        if not meta.get("models_locked"):
            return
        locked = meta.get("test_model")
        if model is None:
            raise ValueError(f"Run has locked test_model={locked!r}; pass --model")
        if model != locked:
            raise ValueError(
                f"--model {model!r} disagrees with locked test_model={locked!r}"
            )


class MetadataHelper:
    """Read and write run-level metadata.json: model config, version list,
    cross-validation linkage."""

    @staticmethod
    def read(run_dir: Path) -> dict:
        meta_path = run_dir / "metadata.json"
        if not meta_path.exists():
            return {}
        return json.loads(meta_path.read_text())

    @staticmethod
    def write(run_dir: Path, meta: dict) -> None:
        meta_path = run_dir / "metadata.json"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(meta, indent=2))

    @staticmethod
    def set_models(run_dir: Path, test_model: str, judge_model: str) -> None:
        meta = MetadataHelper.read(run_dir)
        meta["test_model"] = test_model
        meta["judge_model"] = judge_model
        meta["models_locked"] = True
        MetadataHelper.write(run_dir, meta)

    @staticmethod
    def set_cross_validation_link(
        run_dir: Path, source_run_id: str, source_version: str
    ) -> None:
        meta = MetadataHelper.read(run_dir)
        meta["cross_validation_of"] = {
            "run_id": source_run_id,
            "version": source_version,
        }
        MetadataHelper.write(run_dir, meta)
