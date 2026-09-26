"""
Lazy repository setup and refresh-after-upgrade of the files guard writes outside its package.
"""

import subprocess
from pathlib import Path

from guard.cli import execute_pre_task
from guard.core import repo_setup
from guard.core.repo_setup import (
    DIRECTIVE_END,
    DIRECTIVE_START,
    HOOK_BLOCK_START,
    ensure_repo_setup,
    guard_home,
    refresh_after_upgrade,
    refresh_directive_block,
)
from guard.hooks.templates import AGENT_DIRECTIVES_TEMPLATE

AGENT_MD = "# App\n\n## Core invariants\n\n1. **Chat never times out**\n"


def git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def make_repo(tmp_path: Path, hooks_path: str) -> Path:
    repo = tmp_path / "app"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "t@t")
    git(repo, "config", "user.name", "t")
    git(repo, "config", "core.hooksPath", hooks_path)
    (repo / "AGENT.md").write_text(AGENT_MD, encoding="utf-8")
    (repo / "package.json").write_text('{"scripts": {"build": "node -e \\"process.exit(0)\\""}}', encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "init")
    return repo


def test_repo_on_global_hooks_gets_invariants_but_no_hook_edit(tmp_path):
    global_hooks = guard_home() / "hooks"
    repo = make_repo(tmp_path, str(global_hooks))
    msgs = ensure_repo_setup(repo)
    assert (repo / "guard.invariants.json").is_file()
    assert any("guard.invariants.json" in m for m in msgs)
    assert not (global_hooks / "pre-commit").exists()  # the global hook is installed separately
    assert ensure_repo_setup(repo) == []  # second run: nothing to do


def test_repo_with_own_hooks_path_gets_guard_block_before_exit(tmp_path):
    repo = make_repo(tmp_path, ".husky")
    hook = repo / ".husky" / "pre-commit"
    hook.parent.mkdir()
    hook.write_text("#!/usr/bin/env sh\nnpm run lint\nexit 0\n", encoding="utf-8")

    ensure_repo_setup(repo)
    text = hook.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env sh\n" + HOOK_BLOCK_START)  # runs before the trailing exit 0
    assert "npm run lint\nexit 0\n" in text
    assert text.count(HOOK_BLOCK_START) == 1

    # Idempotent, and a later refresh keeps a single block
    ensure_repo_setup(repo)
    assert hook.read_text(encoding="utf-8").count(HOOK_BLOCK_START) == 1


def test_repo_without_hook_file_gets_guard_hook(tmp_path):
    repo = make_repo(tmp_path, ".githooks")
    ensure_repo_setup(repo)
    hook = repo / ".githooks" / "pre-commit"
    assert hook.is_file() and "guard post --hook" in hook.read_text(encoding="utf-8")


def test_directive_block_refresh_only_touches_marked_blocks(tmp_path):
    marked = tmp_path / "CLAUDE.md"
    marked.write_text(f"# Mine\n\nkeep me\n\n{DIRECTIVE_START}\nold directives\n{DIRECTIVE_END}\n\nafter\n", encoding="utf-8")
    assert "refreshed" in refresh_directive_block(marked)
    text = marked.read_text(encoding="utf-8")
    assert "keep me" in text and "after" in text and "old directives" not in text
    assert AGENT_DIRECTIVES_TEMPLATE.strip().splitlines()[0] in text
    assert refresh_directive_block(marked) is None  # already current

    unmarked = tmp_path / "AGENT.md"
    unmarked.write_text("# LAYA-OCR-GUARD protocol, pasted by hand\n", encoding="utf-8")
    assert refresh_directive_block(unmarked).startswith("WARN")
    assert unmarked.read_text(encoding="utf-8") == "# LAYA-OCR-GUARD protocol, pasted by hand\n"

    plain = tmp_path / "GEMINI.md"
    plain.write_text("# nothing about guard\n", encoding="utf-8")
    assert refresh_directive_block(plain) is None


def test_refresh_after_upgrade_updates_registered_repos_once(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, ".husky")
    ensure_repo_setup(repo)
    hook = repo / ".husky" / "pre-commit"
    # Simulate a block written by an older guard version
    hook.write_text(hook.read_text(encoding="utf-8").replace("guard post --hook", "guard post"), encoding="utf-8")
    (repo / "CLAUDE.md").write_text(f"{DIRECTIVE_START}\nold\n{DIRECTIVE_END}\n", encoding="utf-8")
    monkeypatch.setattr(repo_setup, "__version__", "9.9.9")

    msgs = refresh_after_upgrade()
    assert any("guard block" in m for m in msgs) and any("directives" in m for m in msgs)
    assert "guard post --hook" in hook.read_text(encoding="utf-8")
    assert refresh_after_upgrade() == []  # once per version


def test_pre_ignores_the_invariants_file_setup_just_created(tmp_path):
    repo = make_repo(tmp_path, str(guard_home() / "hooks"))
    assert execute_pre_task("Fix src/chat.ts", repo_path=repo) is True
    assert (repo / "guard.invariants.json").is_file()
