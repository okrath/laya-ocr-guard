"""
Hook Installer and Manager for Laya-OCR-Guard.
Supports installing and managing:
1. Git Hooks: `.git/hooks/pre-commit` and `prepare-commit-msg`
2. Agent Directives: `CLAUDE.md` and `AGENT.md` (for omp, Claude Code, Cursor, Windsurf)
3. Agent Wrapper: `.guard/bin/guard-exec`
4. Stealth Mode: Configures `.git/info/exclude` so `.guard/` leaves zero footprint on repository.
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
        self.git_info_dir = self.repo_path / ".git" / "info"
        self.git_exclude_file = self.git_info_dir / "exclude"
        self.guard_bin_dir = self.repo_path / ".guard" / "bin"
        self.claude_md_path = self.repo_path / "CLAUDE.md"
        self.agent_md_path = self.repo_path / "AGENT.md"

    def is_git_repo(self) -> bool:
        return (self.repo_path / ".git").is_dir()

    def _ensure_git_exclude(self) -> bool:
        """
        Ensure .guard/ directory is ignored in .git/info/exclude (Stealth local ignore).
        Zero workspace footprint: never touches workspace .gitignore or triggers remote push.
        """
        if not self.is_git_repo():
            return False
        try:
            self.git_info_dir.mkdir(parents=True, exist_ok=True)
            content = ""
            if self.git_exclude_file.exists():
                content = self.git_exclude_file.read_text(encoding="utf-8", errors="ignore")
            lines = [line.strip() for line in content.splitlines()]
            if ".guard/" not in lines and ".guard" not in lines:
                new_content = content.rstrip() + ("\n" if content else "") + "\n# Laya-OCR-Guard stealth local exclude\n.guard/\n"
                self.git_exclude_file.write_text(new_content, encoding="utf-8")
                return True
        except Exception:
            pass
        return False

    def _remove_git_exclude(self) -> bool:
        """
        Remove .guard/ entry from .git/info/exclude if it exists.
        """
        if not self.is_git_repo() or not self.git_exclude_file.exists():
            return False
        try:
            content = self.git_exclude_file.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()
            new_lines = [
                line for line in lines
                if line.strip() not in (".guard/", ".guard", "# Laya-OCR-Guard stealth local exclude")
            ]
            if len(new_lines) != len(lines):
                new_content = "\n".join(new_lines).strip()
                if new_content:
                    new_content += "\n"
                self.git_exclude_file.write_text(new_content, encoding="utf-8")
                return True
        except Exception:
            pass
        return False

    def get_status(self) -> Dict[str, Any]:
        """
        Check which hooks and agent directives are currently installed.
        """
        pre_commit = self.git_hooks_dir / "pre-commit"
        prep_msg = self.git_hooks_dir / "prepare-commit-msg"
        agent_exec = self.guard_bin_dir / "guard-exec"

        claude_active = self.claude_md_path.exists() and "LAYA-OCR-GUARD" in self.claude_md_path.read_text(encoding="utf-8", errors="ignore")
        agent_active = self.agent_md_path.exists() and "LAYA-OCR-GUARD" in self.agent_md_path.read_text(encoding="utf-8", errors="ignore")
        pre_commit_installed = pre_commit.exists() and "LAYA-OCR-GUARD" in pre_commit.read_text(encoding="utf-8", errors="ignore")
        prep_msg_installed = prep_msg.exists() and "LAYA-OCR-GUARD" in prep_msg.read_text(encoding="utf-8", errors="ignore")

        git_exclude_active = False
        if self.git_exclude_file.exists():
            exclude_text = self.git_exclude_file.read_text(encoding="utf-8", errors="ignore")
            git_exclude_active = ".guard" in exclude_text

        has_git = pre_commit_installed or prep_msg_installed
        has_agent = claude_active or agent_active
        if has_git and has_agent:
            mode = "all"
        elif has_git:
            mode = "git"
        elif has_agent:
            mode = "agent"
        else:
            mode = "none"

        return {
            "is_git_repo": self.is_git_repo(),
            "pre_commit_installed": pre_commit_installed,
            "prepare_commit_msg_installed": prep_msg_installed,
            "agent_wrapper_installed": agent_exec.exists(),
            "claude_md_active": claude_active,
            "agent_md_active": agent_active,
            "git_exclude_active": git_exclude_active,
            "mode": mode,
        }

    def install(self, mode: str = "all") -> Tuple[bool, List[str]]:
        """
        Install hooks and/or agent directives into repository.
        mode:
          - 'git' (or 'stealth'): Local Git hooks only. Zero workspace files (no CLAUDE.md/AGENT.md).
          - 'agent': Workspace agent directives only (CLAUDE.md & AGENT.md). No Git hooks.
          - 'all' (or 'dual'): Both Git hooks and Agent directives.
        """
        valid_modes = {"git", "stealth", "agent", "all", "dual"}
        mode_clean = (mode or "").lower().strip()
        if mode_clean not in valid_modes:
            raise ValueError(f"Invalid mode '{mode}'. Expected one of: {sorted(valid_modes)}")

        messages = []
        normalized_mode = "git" if mode_clean in ["git", "stealth"] else ("agent" if mode_clean == "agent" else "all")

        if not self.is_git_repo() and normalized_mode in ["git", "all"]:
            return False, ["Target directory is not a Git repository. Cannot install git hooks."]

        # Ensure stealth local exclude so .guard/ session data is never pushed to remote
        if self.is_git_repo():
            if self._ensure_git_exclude():
                messages.append("Added '.guard/' to local .git/info/exclude (Stealth mode: zero workspace footprint)")

        # 1. Install Git Hooks (Stealth / Local only)
        if normalized_mode in ["git", "all"] and self.is_git_repo():
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
        if normalized_mode in ["agent", "all"]:
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

    def uninstall(self, mode: str = "all") -> Tuple[bool, List[str]]:
        """
        Safely uninstall Guard hooks and restore backups if they exist.
        mode: 'git', 'agent', or 'all'
        """
        valid_modes = {"git", "stealth", "agent", "all", "dual"}
        mode_clean = (mode or "").lower().strip()
        if mode_clean not in valid_modes:
            raise ValueError(f"Invalid mode '{mode}'. Expected one of: {sorted(valid_modes)}")

        messages = []
        normalized_mode = "git" if mode_clean in ["git", "stealth"] else ("agent" if mode_clean == "agent" else "all")

        # Remove git hooks
        if normalized_mode in ["git", "all"]:
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

            # Clean stealth local exclude
            if self._remove_git_exclude():
                messages.append("Cleaned '.guard/' entry from local .git/info/exclude")

        # Remove agent wrapper and directives
        if normalized_mode in ["agent", "all"]:
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
