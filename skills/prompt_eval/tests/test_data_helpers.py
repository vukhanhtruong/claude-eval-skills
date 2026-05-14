import json
import pytest
from prompt_eval.data_helpers import DatasetHelper, OutputHelper, ResultsHelper


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
        scores = [{"case_index": 0, "score": 11, "reasoning": "X", "criteria_breakdown": {}}]
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

    def test_validate_accepts_minimal_payload(self):
        # tool_calls is optional; only case_index + output are required
        errors = OutputHelper.validate([{"case_index": 0, "output": "x"}])
        assert errors == []

    def test_validate_rejects_scoring_keys(self):
        outputs = [
            {"case_index": 0, "output": "x", "score": 9, "reasoning": "ok"}
        ]
        errors = OutputHelper.validate(outputs)
        assert len(errors) == 1
        assert "scoring keys" in errors[0]
        assert "'reasoning'" in errors[0]
        assert "'score'" in errors[0]

    def test_validate_rejects_test_case_and_scenario(self):
        outputs = [
            {
                "case_index": 0,
                "output": "x",
                "test_case": {"scenario": "..."},
                "scenario": "...",
            }
        ]
        errors = OutputHelper.validate(outputs)
        assert any("scoring keys" in e for e in errors)
        assert any("'test_case'" in e for e in errors)
        assert any("'scenario'" in e for e in errors)

    def test_validate_requires_case_index_and_output(self):
        errors = OutputHelper.validate([{}])
        assert len(errors) == 1
        assert "missing required keys" in errors[0]
        assert "'case_index'" in errors[0]
        assert "'output'" in errors[0]

    def test_validate_reports_each_case_separately(self):
        outputs = [
            {"case_index": 0, "output": "valid"},
            {"case_index": 1, "output": "x", "score": 8},
            {"output": "missing case_index"},
        ]
        errors = OutputHelper.validate(outputs)
        assert len(errors) == 2
        assert "Output 1" in errors[0]
        assert "Output 2" in errors[1]

    def test_save_raises_on_scoring_keys_and_skips_write(self, tmp_path):
        outputs = [
            {"case_index": 0, "output": "x", "criteria_breakdown": {}}
        ]
        path = tmp_path / "v1" / "output.json"
        with pytest.raises(ValueError, match="scoring keys"):
            OutputHelper.save(outputs, path)
        assert not path.exists()

    def test_save_raises_on_missing_required_keys(self, tmp_path):
        path = tmp_path / "v1" / "output.json"
        with pytest.raises(ValueError, match="missing required keys"):
            OutputHelper.save([{"case_index": 0}], path)
