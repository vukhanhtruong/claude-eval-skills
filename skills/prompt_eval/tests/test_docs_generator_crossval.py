from prompt_eval.docs_generator import render_summary_page


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
        assert "run_001" in page
        assert "v3" in page
        # Banner appears before the test-model line so it's the first thing users see.
        assert page.index("Cross-validation of") < page.index("Test model")
