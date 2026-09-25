"""
Unit tests for Hook Installer and Templates.
"""

import pytest

from guard.hooks.installer import HookInstaller


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
