"""
Unit tests for Hook Installer and Templates.
"""

import pytest
from typer.testing import CliRunner

from guard.cli import app
from guard.hooks.installer import HookInstaller

runner = CliRunner()


@pytest.fixture
def mock_git_repo(tmp_path):
    repo = tmp_path / "target_repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / ".git" / "hooks").mkdir()
    return repo


def test_hook_status_initial(mock_git_repo):
    installer = HookInstaller(mock_git_repo)
    status = installer.get_status()
    assert status["is_git_repo"] is True
    assert status["pre_commit_installed"] is False
    assert status["prepare_commit_msg_installed"] is False
    assert status["claude_md_active"] is False
    assert status["agent_md_active"] is False
    assert status["mode"] == "none"


def test_hook_install_and_backup(mock_git_repo):
    # Pre-existing custom hook
    custom_pre_commit = mock_git_repo / ".git" / "hooks" / "pre-commit"
    custom_pre_commit.write_text("#!/bin/sh\necho 'my custom hook'\n", encoding="utf-8")

    installer = HookInstaller(mock_git_repo)
    success, messages = installer.install(mode="all")
    assert success is True

    # Check that custom hook was backed up
    backup_file = mock_git_repo / ".git" / "hooks" / "pre-commit.guard.bak"
    assert backup_file.exists()
    assert "my custom hook" in backup_file.read_text(encoding="utf-8")

    # Check new hook is Guard hook
    assert "LAYA-OCR-GUARD" in custom_pre_commit.read_text(encoding="utf-8")

    # Status check
    status = installer.get_status()
    assert status["pre_commit_installed"] is True
    assert status["prepare_commit_msg_installed"] is True
    assert status["agent_wrapper_installed"] is True
    assert status["claude_md_active"] is True
    assert status["agent_md_active"] is True
    assert status["mode"] == "all"

    # Check CLAUDE.md and AGENT.md exist
    assert (mock_git_repo / "CLAUDE.md").exists()
    assert (mock_git_repo / "AGENT.md").exists()


def test_hook_uninstall_and_restore(mock_git_repo):
    # Custom hook
    pre_commit = mock_git_repo / ".git" / "hooks" / "pre-commit"
    pre_commit.write_text("#!/bin/sh\necho 'original hook'\n", encoding="utf-8")

    installer = HookInstaller(mock_git_repo)
    installer.install(mode="all")

    # Uninstall
    uninstalled, msgs = installer.uninstall()
    assert uninstalled is True

    # Check original hook was restored
    assert pre_commit.exists()
    assert "original hook" in pre_commit.read_text(encoding="utf-8")
    assert not (mock_git_repo / ".git" / "hooks" / "pre-commit.guard.bak").exists()

    # Guard-generated CLAUDE.md and AGENT.md should be cleaned up
    assert not (mock_git_repo / "CLAUDE.md").exists()
    assert not (mock_git_repo / "AGENT.md").exists()


def test_hook_install_stealth_mode(mock_git_repo):
    installer = HookInstaller(mock_git_repo)
    success, messages = installer.install(mode="git")
    assert success is True

    # Hooks installed
    pre_commit = mock_git_repo / ".git" / "hooks" / "pre-commit"
    prep_msg = mock_git_repo / ".git" / "hooks" / "prepare-commit-msg"
    assert pre_commit.exists()
    assert "LAYA-OCR-GUARD" in pre_commit.read_text(encoding="utf-8")
    assert prep_msg.exists()

    # Zero workspace footprint: NO CLAUDE.md, NO AGENT.md, NO guard-exec
    assert not (mock_git_repo / "CLAUDE.md").exists()
    assert not (mock_git_repo / "AGENT.md").exists()
    assert not (mock_git_repo / ".guard" / "bin" / "guard-exec").exists()

    # Local .git/info/exclude must have .guard/
    exclude = mock_git_repo / ".git" / "info" / "exclude"
    assert exclude.exists()
    assert ".guard/" in exclude.read_text(encoding="utf-8")

    status = installer.get_status()
    assert status["mode"] == "git"
    assert status["pre_commit_installed"] is True
    assert status["claude_md_active"] is False
    assert status["agent_md_active"] is False
    assert status["git_exclude_active"] is True


def test_hook_install_agent_only_mode(mock_git_repo):
    installer = HookInstaller(mock_git_repo)
    success, messages = installer.install(mode="agent")
    assert success is True

    # Directives exist
    assert (mock_git_repo / "CLAUDE.md").exists()
    assert (mock_git_repo / "AGENT.md").exists()
    assert (mock_git_repo / ".guard" / "bin" / "guard-exec").exists()

    # Git hooks NOT installed
    assert not (mock_git_repo / ".git" / "hooks" / "pre-commit").exists()
    assert not (mock_git_repo / ".git" / "hooks" / "prepare-commit-msg").exists()

    status = installer.get_status()
    assert status["mode"] == "agent"
    assert status["pre_commit_installed"] is False
    assert status["claude_md_active"] is True
    assert status["agent_md_active"] is True


def test_hook_selective_uninstall(mock_git_repo):
    installer = HookInstaller(mock_git_repo)
    installer.install(mode="all")
    status = installer.get_status()
    assert status["mode"] == "all"

    # Uninstall git only
    installer.uninstall(mode="git")
    status = installer.get_status()
    assert status["mode"] == "agent"
    assert not (mock_git_repo / ".git" / "hooks" / "pre-commit").exists()
    assert (mock_git_repo / "CLAUDE.md").exists()

    # Reinstall all, then uninstall agent only
    installer.install(mode="all")
    installer.uninstall(mode="agent")
    status = installer.get_status()
    assert status["mode"] == "git"
    assert (mock_git_repo / ".git" / "hooks" / "pre-commit").exists()
    assert not (mock_git_repo / "CLAUDE.md").exists()


def test_cli_hook_install_stealth(mock_git_repo):
    result = runner.invoke(app, ["hook", "install", "--repo", str(mock_git_repo), "--stealth"])
    assert result.exit_code == 0
    assert "Ghost/Stealth Mode" in result.stdout
    assert (mock_git_repo / ".git" / "hooks" / "pre-commit").exists()
    assert not (mock_git_repo / "CLAUDE.md").exists()


def test_cli_hook_install_agent(mock_git_repo):
    result = runner.invoke(app, ["hook", "install", "--repo", str(mock_git_repo), "--mode", "agent"])
    assert result.exit_code == 0
    assert "Agent Directives Mode" in result.stdout
    assert (mock_git_repo / "CLAUDE.md").exists()
    assert not (mock_git_repo / ".git" / "hooks" / "pre-commit").exists()


def test_cli_hook_status(mock_git_repo):
    runner.invoke(app, ["hook", "install", "--repo", str(mock_git_repo), "--stealth"])
    result = runner.invoke(app, ["hook", "status", "--repo", str(mock_git_repo)])
    assert result.exit_code == 0
    assert "Stealth Mode" in result.stdout


def test_hook_invalid_mode_raises(mock_git_repo):
    installer = HookInstaller(mock_git_repo)
    with pytest.raises(ValueError):
        installer.install(mode="invalid_mode")
    with pytest.raises(ValueError):
        installer.uninstall(mode="invalid_mode")


def test_hook_uninstall_cleans_git_exclude(mock_git_repo):
    installer = HookInstaller(mock_git_repo)
    installer.install(mode="git")
    exclude = mock_git_repo / ".git" / "info" / "exclude"
    assert exclude.exists()
    assert ".guard/" in exclude.read_text(encoding="utf-8")

    installer.uninstall(mode="git")
    assert ".guard/" not in exclude.read_text(encoding="utf-8")
