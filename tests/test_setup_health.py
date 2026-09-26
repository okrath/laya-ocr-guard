"""
Setup check shown by `guard doctor`, after `guard update self` and on the first run of a new
version: every gap an older installation can have, with the command that fixes it.
"""

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from guard.cli import app
from guard.core.repo_setup import DIRECTIVE_END, DIRECTIVE_START, install_global, setup_health


@pytest.fixture
def fake_machine(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    return home


def make_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    return path


def by_item(rows):
    return {(r["item"], r["level"]): r for r in rows}


def test_old_install_reports_what_is_missing_and_how_to_fix(fake_machine, tmp_path):
    repo = make_repo(tmp_path / "app")
    rows = by_item(setup_health(repo))
    assert rows[("Git hooks", "missing")]["fix"].startswith("guard install")
    assert rows[("Agent directives", "missing")]["fix"].startswith("guard install")
    assert rows[("Invariants", "warn")]["fix"] == "guard invariants init"


def test_complete_install_reports_ok(fake_machine, tmp_path):
    repo = make_repo(tmp_path / "app")
    install_global(repo)  # also sets the repository up (invariants file)
    levels = {r["item"]: r["level"] for r in setup_health(repo)}
    assert levels["Git hooks"] == "ok"
    assert levels["Agent directives"] == "ok"
    assert "missing" not in levels.values()


def test_unmarked_directives_are_a_warning_with_instructions(fake_machine, tmp_path):
    repo = make_repo(tmp_path / "app")
    (repo / "CLAUDE.md").write_text("# LAYA-OCR-GUARD protocol pasted by hand\n", encoding="utf-8")
    rows = [r for r in setup_health(repo) if r["item"] == "Agent directives"]
    assert rows and all(r["level"] == "warn" for r in rows)
    assert "START/END markers" in rows[0]["fix"]


def test_repo_with_own_hooks_path_is_reported_until_refreshed(fake_machine, tmp_path):
    repo = make_repo(tmp_path / "app")
    install_global(tmp_path)
    subprocess.run(["git", "config", "core.hooksPath", ".husky"], cwd=repo, check=True)
    (repo / ".husky").mkdir()
    (repo / ".husky" / "pre-commit").write_text("#!/bin/sh\nnpm test\n", encoding="utf-8")
    assert ("Repository hook", "missing") in by_item(setup_health(repo))

    # The recommended fix works even for a repository guard already recorded
    from guard.core.repo_setup import ensure_repo_setup
    ensure_repo_setup(repo)
    (repo / ".husky" / "pre-commit").write_text("#!/bin/sh\nnpm test\n", encoding="utf-8")  # husky re-generated it
    assert ("Repository hook", "missing") in by_item(setup_health(repo))
    result = CliRunner().invoke(app, ["hook", "refresh", "--repo", str(repo)])
    assert result.exit_code == 0
    assert ("Repository hook", "missing") not in by_item(setup_health(repo))
    assert "npm test" in (repo / ".husky" / "pre-commit").read_text(encoding="utf-8")


def test_first_command_after_upgrade_prints_the_check_once(fake_machine, tmp_path, monkeypatch, capsys):
    """An old `guard update self` cannot refresh; the new version's first command must speak up."""
    import sys
    from guard import cli

    repo = make_repo(tmp_path / "app")
    monkeypatch.chdir(repo)
    monkeypatch.setattr(sys, "argv", ["guard", "--version"])
    for _ in range(2):
        try:
            cli.main()
        except SystemExit:
            pass
    out = capsys.readouterr().out
    assert out.count("setup check") == 1  # once per version, not on every command
    assert "guard install" in out


def test_doctor_shows_the_setup_table(fake_machine, tmp_path, monkeypatch):
    repo = make_repo(tmp_path / "app")
    monkeypatch.chdir(repo)
    result = CliRunner().invoke(app, ["doctor", "--no-updates"])
    assert result.exit_code == 0
    assert "Installation & Repository Setup" in result.output
    assert "MISSING" in result.output and "guard install" in result.output
