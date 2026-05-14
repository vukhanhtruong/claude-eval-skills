from prompt_eval.data_helpers import MetadataHelper
from prompt_eval.docs_generator import regenerate_for_run, render_summary_page


class TestCrossValBanner:
    def test_no_banner_when_not_a_crossval(self):
        meta = {"run_id": "run_001", "test_model": "haiku", "judge_model": "sonnet"}
        page = render_summary_page("run_001", meta, versions=[])
        assert "Cross-validation of" not in page

    def test_banner_renders_with_source_link_when_crossval(self):
        meta = {
            "run_id": "run_002",
            "test_model": "sonnet",
            "judge_model": "sonnet",
            "cross_validation_of": {"run_id": "run_001", "version": "v3"},
        }
        page = render_summary_page("run_002", meta, versions=[])
        assert "Cross-validation of" in page
        assert "[run_001/v3](../run_001/v3.md)" in page
        # Banner appears before the test-model line so it's the first thing users see.
        assert page.index("Cross-validation of") < page.index("Test model")


class TestCrossValFooter:
    def test_no_footer_when_no_siblings(self):
        meta = {"run_id": "run_001", "test_model": "haiku", "judge_model": "sonnet"}
        page = render_summary_page("run_001", meta, versions=[], cross_validations=[])
        assert "Cross-validations:" not in page

    def test_footer_lists_sibling_runs(self):
        meta = {"run_id": "run_001", "test_model": "haiku", "judge_model": "sonnet"}
        page = render_summary_page(
            "run_001", meta, versions=[],
            cross_validations=[
                {"run_id": "run_002", "test_model": "sonnet", "judge_model": "sonnet"},
                {"run_id": "run_003", "test_model": "opus", "judge_model": "sonnet"},
            ],
        )
        assert "Cross-validations:" in page
        assert "run_002" in page
        assert "run_003" in page
        # "test=opus" only appears in the footer (the header uses test=haiku),
        # so this anchors the assertion to the footer rather than matching by accident.
        assert "test=opus" in page

    def test_regenerate_for_run_passes_siblings_when_source_has_them(self, tmp_path):
        runs_dir = tmp_path / "prompts" / "demo" / "runs"
        # Source run_001 has no cross_validation_of, no versions (kept minimal for the test).
        src = runs_dir / "run_001"
        src.mkdir(parents=True)
        MetadataHelper.write(src, {"run_id": "run_001", "versions": []})
        # Sibling run_002 cross-validates run_001.
        sib = runs_dir / "run_002"
        sib.mkdir()
        MetadataHelper.write(sib, {
            "run_id": "run_002", "versions": [],
            "test_model": "sonnet", "judge_model": "sonnet",
            "cross_validation_of": {"run_id": "run_001", "version": "v1"},
        })
        docs_root = tmp_path / "docs"
        mkdocs_yml = tmp_path / "mkdocs.yml"
        mkdocs_yml.write_text("site_name: x\nnav:\n  - Home: index.md\n")
        (docs_root).mkdir()
        (docs_root / "index.md").write_text("# index")
        regenerate_for_run(src, docs_root, mkdocs_yml, prompt_name="demo")
        page = (docs_root / "prompts" / "demo" / "runs" / "run_001" / "index.md").read_text()
        assert "Cross-validations:" in page
        assert "run_002" in page
