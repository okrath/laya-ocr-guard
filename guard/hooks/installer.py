"""
Hook Installer and Manager for Laya-OCR-Guard.
Supports installing and managing:
1. Git Hooks: `.git/hooks/pre-commit` and `prepare-commit-msg`
2. Agent Directives: `CLAUDE.md` and `AGENT.md` (for omp, Claude Code, Cursor, Windsurf)
3. Agent Wrapper: `.guard/bin/guard-exec`
Safely backs up any existing user files before modification.
"""

from __future__ import annotations

import stat
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from guard.hooks.templates import (
    AGENT_DIRECTIVES_TEMPLATE,
    AGENT_WRAPPER_SCRIPT,
    GIT_PRE_COMMIT_HOOK,
    GIT_PREPARE_COMMIT_MSG_HOOK,
)


class HookInstaller:
    """
    Manages hook lifecycle and AI Agent directives in target repositories.
    """

    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = Path(repo_path or Path.cwd()).resolve()
        self.git_hooks_dir = self.repo_path / ".git" / "hooks"
        self.guard_bin_dir = self.repo_path / ".guard" / "bin"
        self.claude_md_path = self.repo_path / "CLAUDE.md"
        self.agent_md_path = self.repo_path / "AGENT.md"

    def is_git_repo(self) -> bool:
        return (self.repo_path / ".git").is_dir()

    def get_status(self) -> Dict[str, Any]:
        """
        Check which hooks and agent directives are currently installed.
        """
        pre_commit = self.git_hooks_dir / "pre-commit"
        prep_msg = self.git_hooks_dir / "prepare-commit-msg"
        agent_exec = self.guard_bin_dir / "guard-exec"

        claude_active = self.claude_md_path.exists() and "LAYA-OCR-GUARD" in self.claude_md_path.read_text(encoding="utf-8", errors="ignore")
        agent_active = self.agent_md_path.exists() and "LAYA-OCR-GUARD" in self.agent_md_path.read_text(encoding="utf-8", errors="ignore")

        return {
            "is_git_repo": self.is_git_repo(),
            "pre_commit_installed": pre_commit.exists() and "LAYA-OCR-GUARD" in pre_commit.read_text(encoding="utf-8", errors="ignore"),
            "prepare_commit_msg_installed": prep_msg.exists() and "LAYA-OCR-GUARD" in prep_msg.read_text(encoding="utf-8", errors="ignore"),
            "agent_wrapper_installed": agent_exec.exists(),
            "claude_md_active": claude_active,
            "agent_md_active": agent_active,
        }

    def install(self, mode: str = "all") -> Tuple[bool, List[str]]:
        """
        Install hooks and agent directives into repository.
        mode: 'git', 'agent', or 'all'
        """
        messages = []

        if not self.is_git_repo() and mode in ["git", "all"]:
            return False, ["Target directory is not a Git repository. Cannot install git hooks."]

        # 1. Install Git Hooks
        if mode in ["git", "all"] and self.is_git_repo():
            self.git_hooks_dir.mkdir(parents=True, exist_ok=True)

            # Pre-commit hook
            pre_commit_path = self.git_hooks_dir / "pre-commit"
            self._write_hook_file(pre_commit_path, GIT_PRE_COMMIT_HOOK)
            messages.append(f"Installed Git pre-commit hook at {pre_commit_path}")

            # Prepare commit message hook
            prep_msg_path = self.git_hooks_dir / "prepare-commit-msg"
            self._write_hook_file(prep_msg_path, GIT_PREPARE_COMMIT_MSG_HOOK)
            messages.append(f"Installed Git prepare-commit-msg hook at {prep_msg_path}")

        # 2. Install Agent Directives (CLAUDE.md & AGENT.md)
        if mode in ["agent", "all"]:
            # Harness wrapper script
            self.guard_bin_dir.mkdir(parents=True, exist_ok=True)
            agent_path = self.guard_bin_dir / "guard-exec"
            self._write_hook_file(agent_path, AGENT_WRAPPER_SCRIPT)
            messages.append(f"Installed Agent harness wrapper at {agent_path}")

            # Inject or create CLAUDE.md
            self._inject_directive(self.claude_md_path)
            messages.append(f"Configured Agent directives in {self.claude_md_path.name}")

            # Inject or create AGENT.md
            self._inject_directive(self.agent_md_path)
            messages.append(f"Configured Agent directives in {self.agent_md_path.name}")

        return True, messages

    def uninstall(self) -> Tuple[bool, List[str]]:
        """
        Safely uninstall Guard hooks and restore backups if they exist.
        """
        messages = []

        # Remove git hooks
        for hook_name in ["pre-commit", "prepare-commit-msg"]:
            hook_file = self.git_hooks_dir / hook_name
            backup_file = self.git_hooks_dir / f"{hook_name}.guard.bak"

            if hook_file.exists():
                content = hook_file.read_text(encoding="utf-8", errors="ignore")
                if "LAYA-OCR-GUARD" in content:
                    hook_file.unlink()
                    messages.append(f"Removed Guard hook: {hook_file}")

                    # Restore backup if available
                    if backup_file.exists():
                        backup_file.rename(hook_file)
                        messages.append(f"Restored previous hook backup from {backup_file}")

        # Remove agent wrapper
        agent_file = self.guard_bin_dir / "guard-exec"
        if agent_file.exists():
            agent_file.unlink()
            messages.append(f"Removed Agent harness wrapper: {agent_file}")

        # Clean directives from CLAUDE.md & AGENT.md
        for doc_path in [self.claude_md_path, self.agent_md_path]:
            bak_path = doc_path.with_suffix(".guard.bak")
            if bak_path.exists():
                doc_path.unlink(missing_ok=True)
                bak_path.rename(doc_path)
                messages.append(f"Restored previous {doc_path.name} from backup")
            elif doc_path.exists():
                content = doc_path.read_text(encoding="utf-8", errors="ignore")
                if content.strip() == AGENT_DIRECTIVES_TEMPLATE.strip():
                    doc_path.unlink()
                    messages.append(f"Removed Guard-generated {doc_path.name}")

        return True, messages

    def _write_hook_file(self, target_path: Path, script_content: str):
        # Backup existing hook if not created by Guard
        if target_path.exists():
            existing_content = target_path.read_text(encoding="utf-8", errors="ignore")
            if "LAYA-OCR-GUARD" not in existing_content:
                backup_path = target_path.with_suffix(".guard.bak")
                target_path.rename(backup_path)

        target_path.write_text(script_content, encoding="utf-8")

        try:
            current_mode = target_path.stat().st_mode
            target_path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except Exception:
            pass

    def _inject_directive(self, target_path: Path):
        if target_path.exists():
            existing_content = target_path.read_text(encoding="utf-8", errors="ignore")
            if "LAYA-OCR-GUARD" in existing_content:
                return  # Already injected

            # Backup original
            backup_path = target_path.with_suffix(".guard.bak")
            if not backup_path.exists():
                backup_path.write_text(existing_content, encoding="utf-8")

            # Append directive
            new_content = existing_content.rstrip() + "\n\n" + AGENT_DIRECTIVES_TEMPLATE
            target_path.write_text(new_content, encoding="utf-8")
        else:
            target_path.write_text(AGENT_DIRECTIVES_TEMPLATE, encoding="utf-8")
