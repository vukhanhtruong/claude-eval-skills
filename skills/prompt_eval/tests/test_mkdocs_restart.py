"""Tests for mkdocs restart-on-evaluate behavior.

mkdocs serve's filesystem watcher silently misses files written to the docs
dir after server startup (observed on Linux + mkdocs 1.6.1 + Material). The
fix is to restart mkdocs on each regeneration. These tests pin that contract."""
from pathlib import Path
from unittest.mock import patch

from prompt_eval.run import restart_mkdocs


def test_restart_mkdocs_kills_existing_then_starts_new(tmp_path):
    docs_site = tmp_path / "docs-site"
    docs_site.mkdir()

    with patch("prompt_eval.run._port_in_use", return_value=True) as port_check, \
         patch("prompt_eval.run._kill_mkdocs") as kill, \
         patch("prompt_eval.run._start_mkdocs_background") as start:
        restart_mkdocs(docs_site)

    port_check.assert_called_once()
    kill.assert_called_once()
    start.assert_called_once_with(docs_site)


def test_restart_mkdocs_just_starts_when_port_free(tmp_path):
    docs_site = tmp_path / "docs-site"
    docs_site.mkdir()

    with patch("prompt_eval.run._port_in_use", return_value=False), \
         patch("prompt_eval.run._kill_mkdocs") as kill, \
         patch("prompt_eval.run._start_mkdocs_background") as start:
        restart_mkdocs(docs_site)

    kill.assert_not_called()
    start.assert_called_once_with(docs_site)


def test_kill_mkdocs_uses_pgrep_to_avoid_killing_unrelated_port_squatters():
    """If the port is held by something other than mkdocs (e.g., a different
    web server the user is running), we must not kill it. pgrep -f 'mkdocs serve'
    is the discriminator."""
    from prompt_eval.run import _kill_mkdocs

    with patch("prompt_eval.run.subprocess.check_output") as check_output, \
         patch("prompt_eval.run.os.kill") as os_kill, \
         patch("prompt_eval.run._port_in_use", return_value=False):
        # Simulate pgrep returning two PIDs
        check_output.return_value = b"12345\n12346\n"
        _kill_mkdocs()

    cmd = check_output.call_args.args[0]
    assert cmd[0] == "pgrep" and "-f" in cmd and "mkdocs serve" in cmd, (
        f"_kill_mkdocs must use pgrep -f 'mkdocs serve' to identify our processes "
        f"only, got cmd={cmd}"
    )
    assert os_kill.call_count == 2  # both PIDs got SIGTERMed


def test_kill_mkdocs_silent_when_no_mkdocs_running():
    """If pgrep finds nothing (exit 1), don't raise."""
    import subprocess as sp

    from prompt_eval.run import _kill_mkdocs

    with patch("prompt_eval.run.subprocess.check_output",
               side_effect=sp.CalledProcessError(1, "pgrep")), \
         patch("prompt_eval.run.os.kill") as os_kill:
        _kill_mkdocs()  # must not raise

    os_kill.assert_not_called()
