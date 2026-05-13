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
        import json
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
