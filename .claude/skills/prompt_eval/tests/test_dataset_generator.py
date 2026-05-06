"""Tests for DatasetGenerator (Anthropic API mocked)."""
import json
from unittest.mock import patch
from prompt_eval.evaluator import DatasetGenerator


@patch("prompt_eval.evaluator.Anthropic")
def test_generate_unique_ideas_parses_json_array(anthropic_cls, mock_anthropic_response):
    client = anthropic_cls.return_value
    client.messages.create.return_value = mock_anthropic_response(
        '\n["Vegan runner", "Diabetic powerlifter", "High-cholesterol athlete"]'
    )
    gen = DatasetGenerator(model="claude-haiku-4-5")
    ideas = gen.generate_unique_ideas("meal plan", {"height": "cm"}, num_cases=3)
    assert ideas == ["Vegan runner", "Diabetic powerlifter", "High-cholesterol athlete"]


@patch("prompt_eval.evaluator.Anthropic")
def test_generate_test_case_returns_full_record(anthropic_cls, mock_anthropic_response):
    client = anthropic_cls.return_value
    client.messages.create.return_value = mock_anthropic_response(json.dumps({
        "prompt_inputs": {"height": "175", "weight": "65", "goal": "x", "restrictions": "vegan"},
        "solution_criteria": ["Includes calories", "Excludes animal products"],
    }))
    gen = DatasetGenerator(model="claude-haiku-4-5")
    tc = gen.generate_test_case(
        "meal plan",
        "Vegan runner",
        {"height": "cm", "weight": "kg", "goal": "g", "restrictions": "r"},
    )
    assert tc["task_description"] == "meal plan"
    assert tc["scenario"] == "Vegan runner"
    assert tc["prompt_inputs"]["restrictions"] == "vegan"
    assert "Includes calories" in tc["solution_criteria"]


@patch("prompt_eval.evaluator.Anthropic")
def test_generate_dataset_writes_json(anthropic_cls, mock_anthropic_response, tmp_path):
    # First call → ideas list. Subsequent calls → test cases.
    client = anthropic_cls.return_value
    client.messages.create.side_effect = [
        mock_anthropic_response('\n["A", "B"]'),
        mock_anthropic_response(json.dumps({
            "prompt_inputs": {"x": "1"},
            "solution_criteria": ["c"],
        })),
        mock_anthropic_response(json.dumps({
            "prompt_inputs": {"x": "2"},
            "solution_criteria": ["d"],
        })),
    ]
    out_file = tmp_path / "dataset.json"
    gen = DatasetGenerator(model="claude-haiku-4-5", max_concurrent_tasks=1)
    dataset = gen.generate_dataset(
        task_description="task",
        prompt_inputs_spec={"x": "an x"},
        num_cases=2,
        output_file=str(out_file),
    )
    assert len(dataset) == 2
    assert out_file.exists()
    on_disk = json.loads(out_file.read_text())
    assert len(on_disk) == 2
