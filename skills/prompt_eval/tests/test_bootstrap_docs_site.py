"""Verifies the docs-site template gets copied to the user's artifact dir on first evaluate."""
from pathlib import Path

from prompt_eval.run import _bootstrap_docs_site


def test_bootstrap_copies_template_when_target_missing(tmp_path):
    target = tmp_path / "docs-site"

    _bootstrap_docs_site(target)

    assert (target / "mkdocs.yml").exists()
    assert (target / "docs" / "index.md").exists()
    assert "site_name: Prompt Eval Reports" in (target / "mkdocs.yml").read_text()


def test_bootstrap_is_idempotent(tmp_path):
    target = tmp_path / "docs-site"
    _bootstrap_docs_site(target)
    # Mutate so we can detect overwrite:
    (target / "mkdocs.yml").write_text("# user-modified\n")

    _bootstrap_docs_site(target)

    assert (target / "mkdocs.yml").read_text() == "# user-modified\n", \
        "_bootstrap_docs_site overwrote a user-modified mkdocs.yml — must skip if target exists"
