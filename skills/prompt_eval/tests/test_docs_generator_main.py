"""Tests for regenerate_for_run end-to-end Markdown generation."""
import json
import yaml
from prompt_eval.docs_generator import regenerate_for_run, _load_version_results


def test_load_version_results_new_format(tmp_path):
    """_load_version_results merges scores.json + output.json when both present."""
    version_dir = tmp_path / "v1"
    version_dir.mkdir()
    scores = {
        "version": "v1",
        "cases": [
            {
                "case_index": 0,
                "scenario": "Test S1",
                "score": 8,
                "reasoning": "good",
                "criteria_breakdown": {"C1": "PASS", "C2": "PARTIAL"},
            }
        ],
        "summary": {"average_score": 8.0, "pass_rate": 1.0, "total_cases": 1},
    }
    outputs = [{"case_index": 0, "output": "The answer is 42", "tool_calls": []}]
    (version_dir / "scores.json").write_text(json.dumps(scores))
    (version_dir / "output.json").write_text(json.dumps(outputs))

    results = _load_version_results(version_dir)

    assert len(results) == 1
    r = results[0]
    assert r["score"] == 8
    assert r["reasoning"] == "good"
    assert r["criteria_breakdown"] == {"C1": "PASS", "C2": "PARTIAL"}
    assert r["output"] == "The answer is 42"
    assert r["test_case"]["scenario"] == "Test S1"


def test_load_version_results_falls_back_to_dataset_for_scenario(tmp_path):
    """When scores.json cases lack 'scenario' (the real-world shape written by
    save-scores), _load_version_results sources scenario from dataset.json by
    case_index. Otherwise the per-case results table renders an empty first
    column."""
    run_dir = tmp_path / "run_001"
    version_dir = run_dir / "v1"
    version_dir.mkdir(parents=True)

    dataset = [
        {"scenario": "Happy path", "prompt_inputs": {"x": 1}, "solution_criteria": ["C1"]},
        {"scenario": "Edge case", "prompt_inputs": {"x": 2}, "solution_criteria": ["C2"]},
    ]
    (run_dir / "dataset.json").write_text(json.dumps(dataset))

    scores = {
        "version": "v1",
        "cases": [
            {"case_index": 0, "score": 8, "reasoning": "ok", "criteria_breakdown": {"C1": "PASS"}},
            {"case_index": 1, "score": 6, "reasoning": "meh", "criteria_breakdown": {"C2": "FAIL"}},
        ],
        "summary": {"average_score": 7.0, "pass_rate": 0.5, "total_cases": 2},
    }
    outputs = [
        {"case_index": 0, "output": "out-0", "tool_calls": []},
        {"case_index": 1, "output": "out-1", "tool_calls": []},
    ]
    (version_dir / "scores.json").write_text(json.dumps(scores))
    (version_dir / "output.json").write_text(json.dumps(outputs))

    results = _load_version_results(version_dir)

    assert [r["test_case"]["scenario"] for r in results] == ["Happy path", "Edge case"]


def test_load_version_results_legacy_format(tmp_path):
    """_load_version_results falls back to output.json when scores.json absent."""
    version_dir = tmp_path / "v1"
    version_dir.mkdir()
    legacy = [
        {
            "test_case": {"scenario": "S1", "solution_criteria": ["C1"]},
            "output": "out",
            "score": 7,
            "reasoning": "ok",
        }
    ]
    (version_dir / "output.json").write_text(json.dumps(legacy))

    results = _load_version_results(version_dir)

    assert results == legacy


def test_regenerate_for_run_writes_all_pages(tmp_path):
    # Arrange a runs/run_001 layout
    run_dir = tmp_path / "runs" / "run_001"
    (run_dir / "v1").mkdir(parents=True)
    (run_dir / "v2").mkdir(parents=True)
    (run_dir / "v1" / "prompt.txt").write_text("prompt v1")
    (run_dir / "v2" / "prompt.txt").write_text("prompt v2")
    (run_dir / "v1" / "output.json").write_text(json.dumps([
        {"test_case": {"scenario": "A", "solution_criteria": []}, "output": "x", "score": 6, "reasoning": "ok"},
    ]))
    (run_dir / "v2" / "output.json").write_text(json.dumps([
        {"test_case": {"scenario": "A", "solution_criteria": []}, "output": "y", "score": 9, "reasoning": "great"},
    ]))
    (run_dir / "metadata.json").write_text(json.dumps({
        "run_id": "run_001",
        "test_model": "haiku",
        "judge_model": "sonnet",
        "versions": ["v1", "v2"],
    }))

    docs_root = tmp_path / "docs-site" / "docs"
    (docs_root / "runs").mkdir(parents=True)
    cfg = tmp_path / "docs-site" / "mkdocs.yml"
    cfg.write_text(yaml.safe_dump({
        "site_name": "Prompt Eval Reports",
        "nav": [{"Home": "index.md"}],
    }))

    # Act
    regenerate_for_run(run_dir=run_dir, docs_root=docs_root, mkdocs_yml=cfg, prompt_name="default")

    # Assert pages exist
    out = docs_root / "prompts" / "default" / "runs" / "run_001"
    assert (out / "index.md").exists()
    assert (out / "comparison.md").exists()
    assert (out / "v1.md").exists()
    assert (out / "v2.md").exists()

    # mkdocs.yml updated
    nav = yaml.safe_load(cfg.read_text())["nav"]
    prompts_entry = next(item["Prompts"] for item in nav if "Prompts" in item)
    default = next(item["default"] for item in prompts_entry if "default" in item)
    assert any("run_001" in entry for entry in default)


def test_regenerate_for_run_new_format_scores(tmp_path):
    """regenerate_for_run reads scores.json + output.json when scores.json present."""
    run_dir = tmp_path / "runs" / "run_003"
    (run_dir / "v1").mkdir(parents=True)
    (run_dir / "v1" / "prompt.txt").write_text("prompt v1")
    scores = {
        "version": "v1",
        "cases": [
            {
                "case_index": 0,
                "scenario": "S1",
                "score": 9,
                "reasoning": "excellent",
                "criteria_breakdown": {"Accuracy": "PASS"},
            }
        ],
        "summary": {"average_score": 9.0, "pass_rate": 1.0, "total_cases": 1},
    }
    outputs = [{"case_index": 0, "output": "great output", "tool_calls": []}]
    (run_dir / "v1" / "scores.json").write_text(json.dumps(scores))
    (run_dir / "v1" / "output.json").write_text(json.dumps(outputs))
    (run_dir / "metadata.json").write_text(json.dumps({
        "run_id": "run_003",
        "test_model": "haiku",
        "judge_model": "sonnet",
        "versions": ["v1"],
    }))

    docs_root = tmp_path / "docs-site" / "docs"
    docs_root.mkdir(parents=True)
    cfg = tmp_path / "docs-site" / "mkdocs.yml"
    cfg.write_text(yaml.safe_dump({"site_name": "x", "nav": []}))

    regenerate_for_run(run_dir=run_dir, docs_root=docs_root, mkdocs_yml=cfg, prompt_name="default")

    v1_page = (docs_root / "prompts" / "default" / "runs" / "run_003" / "v1.md").read_text()
    assert "excellent" in v1_page
    assert "Accuracy" in v1_page
    assert "PASS" in v1_page
    assert "great output" in v1_page


def test_regenerate_for_run_skips_comparison_with_one_version(tmp_path):
    run_dir = tmp_path / "runs" / "run_002"
    (run_dir / "v1").mkdir(parents=True)
    (run_dir / "v1" / "prompt.txt").write_text("solo prompt")
    (run_dir / "v1" / "output.json").write_text(json.dumps([
        {"test_case": {"scenario": "A", "solution_criteria": []}, "output": "x", "score": 7, "reasoning": "ok"},
    ]))
    (run_dir / "metadata.json").write_text(json.dumps({
        "run_id": "run_002",
        "test_model": "haiku",
        "judge_model": "sonnet",
        "versions": ["v1"],
    }))

    docs_root = tmp_path / "docs-site" / "docs"
    (docs_root / "runs").mkdir(parents=True)
    cfg = tmp_path / "docs-site" / "mkdocs.yml"
    cfg.write_text(yaml.safe_dump({"site_name": "x", "nav": []}))

    regenerate_for_run(run_dir=run_dir, docs_root=docs_root, mkdocs_yml=cfg, prompt_name="default")

    out = docs_root / "prompts" / "default" / "runs" / "run_002"
    assert (out / "index.md").exists()
    assert (out / "v1.md").exists()
    assert not (out / "comparison.md").exists()
