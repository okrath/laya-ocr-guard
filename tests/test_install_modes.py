"""
`guard install` (global) and `guard install --workspace`, fully isolated from the real machine:
fake home directory, throwaway global git config and GUARD_HOME.
"""

import subprocess
from pathlib import Path

import pytest

from guard.core.repo_setup import (
    DIRECTIVE_START,
    guard_home,
    install_global,
    install_workspace,
    uninstall_global,
    uninstall_workspace,
)


@pytest.fixture
def fake_machine(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".claude").mkdir()
    (home / ".codex").mkdir()  # no ~/.gemini: Gemini CLI is "not installed"
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    return home


def global_hooks_path():
    res = subprocess.run(["git", "config", "--global", "--get", "core.hooksPath"], capture_output=True, text=True)
    return res.stdout.strip()


def make_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    return path


def test_global_install_writes_hooks_and_agent_docs_of_installed_agents(fake_machine, tmp_path):
    user_doc = fake_machine / ".claude" / "CLAUDE.md"
    user_doc.write_text("# My own global rules\n", encoding="utf-8")

    ok, msgs = install_global(tmp_path)
    assert ok
    assert Path(global_hooks_path()).resolve() == (guard_home() / "hooks").resolve()
    assert (guard_home() / "hooks" / "pre-commit").is_file()

    claude = user_doc.read_text(encoding="utf-8")
    assert claude.startswith("# My own global rules") and claude.count(DIRECTIVE_START) == 1
    assert (fake_machine / ".claude" / "CLAUDE.md.guard.bak").is_file()
    assert DIRECTIVE_START in (fake_machine / ".codex" / "AGENTS.md").read_text(encoding="utf-8")
    assert not (fake_machine / ".gemini").exists()  # agents that are not installed are left alone

    install_global(tmp_path)  # idempotent
    assert user_doc.read_text(encoding="utf-8").count(DIRECTIVE_START) == 1

    msgs = uninstall_global()
    assert global_hooks_path() == ""
    assert user_doc.read_text(encoding="utf-8") == "# My own global rules\n"
    assert not (fake_machine / ".codex" / "AGENTS.md").exists()  # it only held guard directives
    assert any("removed" in m for m in msgs) and any("deleted" in m for m in msgs)


def test_global_uninstall_keeps_a_foreign_hooks_path(fake_machine):
    subprocess.run(["git", "config", "--global", "core.hooksPath", "/somewhere/else"], check=True)
    msgs = uninstall_global()
    assert global_hooks_path() == "/somewhere/else"
    assert any("kept global core.hooksPath" in m for m in msgs)


def test_workspace_install_covers_only_that_folder_and_its_repos(fake_machine, tmp_path):
    ws = tmp_path / "workspace"
    a = make_repo(ws / "service-a")
    b = make_repo(ws / "service-b")
    (ws / "notes").mkdir()

    ok, msgs = install_workspace(ws)
    assert ok
    for doc in ("CLAUDE.md", "AGENT.md"):
        assert DIRECTIVE_START in (ws / doc).read_text(encoding="utf-8")
    for repo in (a, b):
        assert "guard post --hook" in (repo / ".git" / "hooks" / "pre-commit").read_text(encoding="utf-8")
        assert (repo / "guard.invariants.json").is_file()
    assert global_hooks_path() == ""  # nothing global
    assert not (fake_machine / ".claude" / "CLAUDE.md").exists()

    uninstall_workspace(ws)
    assert not (ws / "CLAUDE.md").exists() and not (ws / "AGENT.md").exists()
    assert not (a / ".git" / "hooks" / "pre-commit").exists()


def test_workspace_that_is_itself_a_repo(fake_machine, tmp_path):
    repo = make_repo(tmp_path / "single")
    install_workspace(repo)
    assert DIRECTIVE_START in (repo / "CLAUDE.md").read_text(encoding="utf-8")
    assert (repo / ".git" / "hooks" / "pre-commit").is_file()


def test_workspace_without_git_gets_directives_only(fake_machine, tmp_path):
    folder = tmp_path / "docs-only"
    folder.mkdir()
    ok, msgs = install_workspace(folder)
    assert (folder / "AGENT.md").is_file()
    assert any("only the agent directives apply" in m for m in msgs)
