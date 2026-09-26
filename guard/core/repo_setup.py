"""
Zero-touch setup and refresh of the files guard writes outside its own package.

- Setup happens lazily: the first time guard runs inside a Git repository it creates
  guard.invariants.json and, when the repository overrides `core.hooksPath` (so the global
  guard hook never runs there), adds a guard block to that repository's own pre-commit hook.
- Refresh happens when the installed guard version changes (e.g. after `guard update self`):
  global hooks, guard blocks in repository hooks, and the directive block in agent docs are
  rewritten, but only where guard already wrote them. Files without guard markers are never
  touched; a guard block without markers is only reported.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from guard import __version__

DIRECTIVE_START = "<!-- === LAYA-OCR-GUARD DUAL-GATE HOOK: START === -->"
DIRECTIVE_END = "<!-- === LAYA-OCR-GUARD DUAL-GATE HOOK: END === -->"
HOOK_BLOCK_START = "# >>> LAYA-OCR-GUARD >>>"
HOOK_BLOCK_END = "# <<< LAYA-OCR-GUARD <<<"
HOOK_BLOCK = f"""{HOOK_BLOCK_START}
# Added by guard: this repository sets its own core.hooksPath, so the global guard hook does not run here.
if command -v guard >/dev/null 2>&1; then
  guard post --hook || exit 1
fi
{HOOK_BLOCK_END}
"""
AGENT_DOC_NAMES = ("CLAUDE.md", "AGENT.md", "AGENTS.md", "GEMINI.md")
GLOBAL_AGENT_DOCS = (
    Path(".claude") / "CLAUDE.md",
    Path(".codex") / "AGENTS.md",
    Path(".gemini") / "GEMINI.md",
    Path(".config") / "opencode" / "AGENTS.md",
)


def guard_home() -> Path:
    """~/.guard, overridable with GUARD_HOME (tests, portable installs)."""
    return Path(os.environ.get("GUARD_HOME") or (Path.home() / ".guard"))


def _registry_file() -> Path:
    return guard_home() / "repos.json"


def _state_file() -> Path:
    return guard_home() / "state.json"


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _git(repo: Path, *args: str) -> Optional[str]:
    try:
        res = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                             encoding="utf-8", errors="replace", check=False)
    except OSError:
        return None
    return res.stdout.strip() if res.returncode == 0 else None


def git_root(path: Path) -> Optional[Path]:
    top = _git(path, "rev-parse", "--show-toplevel")
    return Path(top).resolve() if top else None


def _same(a: Path, b: Path) -> bool:
    try:
        return a.resolve() == b.resolve()
    except OSError:
        return False


def effective_hooks_dir(repo: Path) -> Optional[Path]:
    """The directory Git actually runs hooks from (respects local and global core.hooksPath)."""
    rel = _git(repo, "rev-parse", "--git-path", "hooks")
    if not rel:
        return None
    p = Path(rel)
    return (p if p.is_absolute() else repo / p).resolve()


def _write_exec(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    try:
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        pass


def _ensure_hook_block(hook: Path) -> Optional[str]:
    """Make `hook` run guard. Returns a message when the file changed."""
    from guard.hooks.templates import GIT_PRE_COMMIT_HOOK

    if not hook.exists():
        _write_exec(hook, GIT_PRE_COMMIT_HOOK)
        return f"created guard pre-commit hook {hook}"
    text = hook.read_text(encoding="utf-8", errors="ignore")
    if HOOK_BLOCK_START in text and HOOK_BLOCK_END in text:
        new = re.sub(re.escape(HOOK_BLOCK_START) + r".*?" + re.escape(HOOK_BLOCK_END) + r"\n?",
                     lambda _m: HOOK_BLOCK, text, flags=re.DOTALL)
    elif "LAYA-OCR-GUARD AUTO-GENERATED HOOK" in text:
        new = GIT_PRE_COMMIT_HOOK  # a whole file guard generated earlier
    elif "LAYA-OCR-GUARD" in text:
        return None  # guard is referenced in some other form; leave the author's file alone
    else:
        # Insert right after the shebang so a trailing `exit 0` in the existing hook cannot skip it
        lines = text.splitlines(keepends=True)
        at = 1 if lines and lines[0].startswith("#!") else 0
        new = "".join(lines[:at]) + HOOK_BLOCK + "".join(lines[at:])
    if new == text:
        return None
    _write_exec(hook, new)
    return f"updated guard block in {hook}"


def refresh_directive_block(doc: Path) -> Optional[str]:
    """Replace the guard directive block between its markers. Never adds a block."""
    from guard.hooks.templates import AGENT_DIRECTIVES_TEMPLATE

    if not doc.is_file():
        return None
    text = doc.read_text(encoding="utf-8", errors="ignore")
    if DIRECTIVE_START not in text or DIRECTIVE_END not in text:
        if "LAYA-OCR-GUARD" in text:
            return (
                f"WARN {doc}: guard directives without START/END markers were not refreshed. Wrap the guard "
                f"section in `{DIRECTIVE_START}` ... `{DIRECTIVE_END}` (guard then keeps it current), or delete "
                f"it and run `guard hook install --mode agent`."
            )
        return None
    block = f"{DIRECTIVE_START}\n{AGENT_DIRECTIVES_TEMPLATE.strip()}\n{DIRECTIVE_END}"
    new = re.sub(re.escape(DIRECTIVE_START) + r".*?" + re.escape(DIRECTIVE_END),
                 lambda _m: block, text, count=1, flags=re.DOTALL)
    if new == text:
        return None
    doc.write_text(new, encoding="utf-8", newline="\n")
    return f"refreshed guard directives in {doc}"


def refresh_repo(repo: Path) -> List[str]:
    """Refresh guard-owned hook blocks and directive blocks inside one repository."""
    messages: List[str] = []
    hooks = effective_hooks_dir(repo)
    global_dir = guard_home() / "hooks"
    if hooks and not _same(hooks, global_dir):
        hook = hooks / "pre-commit"
        if hook.exists():
            text = hook.read_text(encoding="utf-8", errors="ignore")
            if "LAYA-OCR-GUARD" in text:
                msg = _ensure_hook_block(hook)
                if msg:
                    messages.append(msg)
    for name in AGENT_DOC_NAMES:
        msg = refresh_directive_block(repo / name)
        if msg:
            messages.append(msg)
    return messages


def ensure_repo_setup(start: Path, create_invariants: bool = True) -> List[str]:
    """
    First run in a repository: create guard.invariants.json and make sure the hook Git really
    runs calls guard. Later runs only refresh when the guard version changed.
    """
    repo = git_root(start)
    if repo is None:
        return []  # not a Git repository: only the agent directives apply
    registry: Dict[str, Dict[str, str]] = _read_json(_registry_file(), {})
    key = str(repo)
    known = registry.get(key)
    messages: List[str] = []

    if known is None:
        if create_invariants:
            from guard.core.project_invariants import init_invariants_file
            path, created, imported = init_invariants_file(repo)
            if created:
                messages.append(f"created {path.name} ({imported} invariant(s) imported from agent docs); commit it with your code")
        hooks = effective_hooks_dir(repo)
        if hooks and not _same(hooks, guard_home() / "hooks"):
            msg = _ensure_hook_block(hooks / "pre-commit")
            if msg:
                messages.append(msg)
        # A repository set up by an older guard (before repositories were recorded) may carry
        # outdated guard blocks: refresh them on this first visit too.
        messages.extend(refresh_repo(repo))
    elif known.get("version") != __version__:
        messages.extend(refresh_repo(repo))

    if known is None or known.get("version") != __version__:
        registry[key] = {"version": __version__}
        _write_json(_registry_file(), registry)
    return messages


def refresh_after_upgrade(force: bool = False) -> List[str]:
    """
    Once per installed version: rewrite global hooks (only if Git's global hooksPath points at
    guard's hooks directory), refresh global agent docs and every registered repository.
    """
    state = _read_json(_state_file(), {})
    if not force and state.get("refreshed_version") == __version__:
        return []
    messages: List[str] = []
    global_dir = guard_home() / "hooks"
    configured = None
    try:
        res = subprocess.run(["git", "config", "--global", "--get", "core.hooksPath"], capture_output=True,
                             text=True, encoding="utf-8", errors="replace", check=False)
        configured = res.stdout.strip() or None
    except OSError:
        pass
    if configured and _same(Path(os.path.expanduser(configured)), global_dir):
        from guard.hooks.templates import GIT_PRE_COMMIT_HOOK, GIT_PREPARE_COMMIT_MSG_HOOK
        for name, content in (("pre-commit", GIT_PRE_COMMIT_HOOK), ("prepare-commit-msg", GIT_PREPARE_COMMIT_MSG_HOOK)):
            hook = global_dir / name
            if not hook.exists() or hook.read_text(encoding="utf-8", errors="ignore") != content:
                _write_exec(hook, content)
                messages.append(f"refreshed global hook {hook}")

    for rel in GLOBAL_AGENT_DOCS:
        msg = refresh_directive_block(Path.home() / rel)
        if msg:
            messages.append(msg)

    registry: Dict[str, Dict[str, str]] = _read_json(_registry_file(), {})
    for key in list(registry):
        repo = Path(key)
        if not (repo / ".git").exists():
            continue
        messages.extend(refresh_repo(repo))
        registry[key] = {"version": __version__}
    if registry:
        _write_json(_registry_file(), registry)

    state["refreshed_version"] = __version__
    _write_json(_state_file(), state)
    return messages
