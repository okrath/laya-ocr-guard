"""
Project-defined invariants (`guard.invariants.json` at the repository root).

Each invariant may carry machine checks evaluated against the CURRENT file contents:
  {"files": "src/ai/**/*.ts", "forbid": "AbortSignal\\.timeout"}   -> no file may match
  {"files": "src/ui/main-screen.ts", "require": "pushSentHistory"} -> at least one file must match
An invariant without checks is reported as UNVERIFIED (manual), never as passed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Optional, Tuple

INVARIANTS_FILENAME = "guard.invariants.json"

STATUS_PASSED = "passed"
STATUS_FAILED = "failed"
STATUS_UNVERIFIED = "unverified"


class InvariantsFileError(ValueError):
    pass


def load_project_invariants(repo_path: Path) -> Optional[List[dict]]:
    """Return the raw invariant dicts, or None when the repo defines no invariants file."""
    path = repo_path / INVARIANTS_FILENAME
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise InvariantsFileError(f"{INVARIANTS_FILENAME} is not valid JSON: {e}") from e
    items = data.get("invariants", []) if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise InvariantsFileError(f"{INVARIANTS_FILENAME}: 'invariants' must be a list")
    return [i for i in items if isinstance(i, dict) and i.get("id") and i.get("description")]


SKIP_DIRS = {"node_modules", ".git", ".guard", "dist", "build", ".venv", "venv", "__pycache__"}


def _match_files(repo_path: Path, pattern: str) -> List[Path]:
    return sorted(
        p for p in repo_path.glob(pattern)
        if p.is_file() and not SKIP_DIRS.intersection(p.relative_to(repo_path).parts)
    )


def evaluate_checks(repo_path: Path, checks: List[dict]) -> Tuple[str, str]:
    """Evaluate one invariant's checks. Returns (status, note)."""
    if not checks:
        return STATUS_UNVERIFIED, "No automated check defined (manual verification required)"

    for check in checks:
        pattern = check.get("files", "")
        files = _match_files(repo_path, pattern) if pattern else []
        if not files:
            return STATUS_FAILED, f"Check target `{pattern}` matches no file (renamed or deleted?)"

        forbid = check.get("forbid")
        require = check.get("require")
        try:
            forbid_rx = re.compile(forbid, re.MULTILINE) if forbid else None
            require_rx = re.compile(require, re.MULTILINE) if require else None
        except re.error as e:
            return STATUS_FAILED, f"Invalid regex in check for `{pattern}`: {e}"
        if forbid_rx:
            rx = forbid_rx
            for f in files:
                text = f.read_text(encoding="utf-8", errors="ignore")
                m = rx.search(text)
                if m:
                    line = text.count("\n", 0, m.start()) + 1
                    rel = f.relative_to(repo_path).as_posix()
                    return STATUS_FAILED, f"Forbidden pattern `{forbid}` found at {rel}:{line}"
        if require_rx:
            rx = require_rx
            if not any(rx.search(f.read_text(encoding="utf-8", errors="ignore")) for f in files):
                return STATUS_FAILED, f"Required pattern `{require}` not found in `{pattern}`"

    return STATUS_PASSED, f"{len(checks)} automated check(s) passed"
