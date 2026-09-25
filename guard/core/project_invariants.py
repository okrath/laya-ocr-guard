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


# ---------------------------------------------------------------------------
# Authoring: init from agent docs, LLM-learned additions, removal detection
# ---------------------------------------------------------------------------

AGENT_DOCS = ("AGENT.md", "AGENTS.md", "CLAUDE.md")
_SECTION_RE = re.compile(r"^#{1,6}\s.*(INVARIANT|BẤT BIẾN)", re.IGNORECASE)
_ITEM_RE = re.compile(r"^(\d+)\.\s+(.+?)\s*$")
_ID_RE = re.compile(r"^[A-Z][A-Z0-9_-]{1,39}$")

FILE_COMMENT = (
    "Project invariants checked by `guard pre`/`guard post`. Each check: "
    "{\"files\": glob, \"forbid\" | \"require\": regex} on current file contents. "
    "Entries without checks are reported UNVERIFIED. Validate with `guard invariants check`."
)


def _clean_md(text: str) -> str:
    # Keep underscores: identifiers such as update_project_synopsis must survive
    return re.sub(r"[*`]", "", text).strip().rstrip(":").strip()


def import_from_agent_docs(repo_path: Path) -> List[dict]:
    """Numbered items under an 'Invariants' / 'Bất biến' heading of AGENT.md / CLAUDE.md."""
    found: List[dict] = []
    seen = set()
    for name in AGENT_DOCS:
        path = repo_path / name
        if not path.is_file():
            continue
        in_section, current = False, None
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("#"):
                in_section = bool(_SECTION_RE.match(line))
                current = None
                continue
            if not in_section:
                continue
            m = _ITEM_RE.match(line)
            if m:
                title = _clean_md(m.group(2))
                if title and title.lower() not in seen:
                    seen.add(title.lower())
                    current = {"id": f"INV-{len(found) + 1:02d}", "description": title,
                               "rationale": f"Imported from {name}", "checks": []}
                    found.append(current)
                else:
                    current = None
            elif current is not None and line.strip().startswith(("*", "-")):
                detail = _clean_md(line.strip()[1:])
                if detail:
                    current["description"] += f". {detail}" if len(current["description"]) < 300 else ""
    return found


def dump_invariants(payload: dict) -> str:
    """
    Stable, review-friendly layout: one invariant per block, one check per line. Rewriting a file
    in this layout (e.g. after appending a learned rule) leaves existing entries byte-identical.
    """
    def value(v) -> str:
        return json.dumps(v, ensure_ascii=False)

    def check_line(c: dict) -> str:
        return "{ " + ", ".join(f"{value(k)}: {value(v)}" for k, v in c.items()) + " }"

    blocks = []
    for inv in payload.get("invariants", []):
        fields = []
        for k, v in inv.items():
            if k == "checks" and v:
                body = ",\n".join(f"        {check_line(c)}" for c in v)
                fields.append(f'      "checks": [\n{body}\n      ]')
            else:
                fields.append(f"      {value(k)}: {value(v)}")
        blocks.append("    {\n" + ",\n".join(fields) + "\n    }")
    head = [f'  "$comment": {value(payload["$comment"])},'] if "$comment" in payload else []
    return "\n".join(["{", *head, '  "invariants": [', ",\n".join(blocks), "  ]", "}"]) + "\n"


def write_invariants_file(repo_path: Path, items: List[dict], comment: str = FILE_COMMENT) -> Path:
    path = repo_path / INVARIANTS_FILENAME
    payload = {"$comment": comment, "invariants": items} if comment else {"invariants": items}
    path.write_text(dump_invariants(payload), encoding="utf-8", newline="\n")
    return path


def init_invariants_file(repo_path: Path) -> Tuple[Path, bool, int]:
    """Create guard.invariants.json if missing. Returns (path, created, imported_count)."""
    path = repo_path / INVARIANTS_FILENAME
    if path.exists():
        return path, False, 0
    items = import_from_agent_docs(repo_path)
    write_invariants_file(repo_path, items)
    return path, True, len(items)


def append_learned_invariants(repo_path: Path, proposals: List[dict], session_id: str) -> Tuple[List[str], List[str]]:
    """
    Add invariants the reviewer discovered. A proposal is kept only when its id and description
    are new and its checks pass on the current tree (a rule that fails on the code it describes
    is wrong). Returns (added ids, rejection notes).
    """
    if not proposals:
        return [], []
    try:
        items = load_project_invariants(repo_path) or []
    except InvariantsFileError as e:
        return [], [f"not written: {e}"]
    ids = {str(i["id"]) for i in items}
    descs = {str(i["description"]).strip().lower() for i in items}
    added, rejected = [], []
    for prop in proposals:
        pid = str(prop.get("id", "")).strip().upper()
        desc = str(prop.get("description", "")).strip()
        checks = [c for c in (prop.get("checks") or []) if isinstance(c, dict)]
        if not _ID_RE.match(pid) or not desc:
            rejected.append(f"{pid or '?'}: missing or invalid id/description")
            continue
        if pid in ids or desc.lower() in descs:
            rejected.append(f"{pid}: already present")
            continue
        if checks:
            status, note = evaluate_checks(repo_path, checks)
            if status != STATUS_PASSED:
                rejected.append(f"{pid}: check does not pass on the current code ({note})")
                continue
        items.append({
            "id": pid, "description": desc,
            "rationale": str(prop.get("rationale", "")).strip() or "Discovered by the LLM gate review",
            "checks": checks, "origin": f"llm:{session_id}",
        })
        ids.add(pid)
        descs.add(desc.lower())
        added.append(pid)
    if added:
        raw = {}
        path = repo_path / INVARIANTS_FILENAME
        if path.is_file():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except ValueError:
                raw = {}
        # Keep the file's own header (or lack of one); only the new entries change
        comment = raw.get("$comment", "") if isinstance(raw, dict) else ""
        write_invariants_file(repo_path, items, comment=comment)
    return added, rejected


def removed_or_relaxed(old_items: List[dict], new_items: List[dict]) -> List[str]:
    """Invariants that disappeared or whose checks changed between two versions of the file."""
    new_by_id = {str(i["id"]): i for i in new_items}
    notes = []
    for old in old_items:
        oid = str(old["id"])
        new = new_by_id.get(oid)
        if new is None:
            notes.append(f"`{oid}` was removed")
        elif (old.get("checks") or []) != (new.get("checks") or []):
            notes.append(f"`{oid}` checks were changed")
    return notes
