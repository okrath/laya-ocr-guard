"""
Simplicity & Engineering Frugality Engine — The "Productive Laziness" (KISS & YAGNI) Pillar.
Inspired by Larry Wall's virtue of Laziness and Dietrich Gebert's Ponytail philosophy:
"The best code is the code you never wrote."

Enforces the Ponytail Necessity Ladder:
1. YAGNI: Don't write code unless strictly necessary.
2. Reuse: Leverage existing codebase helpers and components before creating new ones.
3. Stdlib & Native: Prioritize language standard libraries and runtime features (crypto, fetch, Intl, etc.).
4. Existing Dependencies: Use packages already installed before adding new dependencies.
5. Minimal / One-liner: Write the simplest, most readable solution (KISS).
6. Net Negative LOC: Reward code deletion and technical debt payoff.

Detects:
- LAZY-001 (Dependency Bloat): Unnecessary new dependencies added to package.json / pyproject.toml.
- LAZY-002 (Premature Abstraction): Single-use abstractions, redundant wrapper functions, over-engineered factories.
- LAZY-003 (Wheel Reinvention): Writing custom utility functions when standard library or native runtime suffices.
"""

from __future__ import annotations

import ast
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from guard.core.ocr_engine import DiffSummary, FileDiffStat, RuleViolation


# Known redundant npm packages easily replaced by native modern JS/TS runtime APIs
REDUNDANT_NPM_PACKAGES = {
    "is-odd": "Replace with `n % 2 !== 0`",
    "is-even": "Replace with `n % 2 === 0`",
    "left-pad": "Replace with native `str.padStart()`",
    "uuid": "Replace with native `crypto.randomUUID()`",
    "mkdirp": "Replace with native `fs.mkdirSync(path, { recursive: true })`",
    "rimraf": "Replace with native `fs.rmSync(path, { recursive: true, force: true })`",
    "node-fetch": "Replace with native global `fetch()`",
    "cross-fetch": "Replace with native global `fetch()`",
    "query-string": "Replace with native `new URLSearchParams()`",
    "lodash.get": "Replace with native optional chaining `obj?.prop?.sub`",
    "lodash.has": "Replace with `prop in obj` or `Object.hasOwn(obj, prop)`",
    "chalk": "Use standard ANSI terminal escape sequences or modern lightweight styling",
}

# Known redundant Python packages replaced by standard library
REDUNDANT_PY_PACKAGES = {
    "pathlib2": "Replace with native standard library `pathlib`",
    "mock": "Replace with native standard library `unittest.mock`",
    "simplejson": "Replace with native standard library `json`",
    "pytz": "Replace with native standard library `zoneinfo` (Python 3.9+)",
    "six": "Remove obsolete Python 2/3 compatibility layer",
}

# Common wheels that agents frequently write from scratch instead of using stdlib or 1-liners
COMMON_REINVENTED_FUNCTIONS = {
    # Name: (recommendation, regex_pattern)
    "clamp": "Use `max(min_val, min(val, max_val))` or `Math.min(Math.max(val, min), max)`",
    "slugify": "Check existing project utils or use standard regex string replacement",
    "is_empty": "Use standard falsy evaluation `if not obj:` or `!obj || obj.length === 0`",
    "flatten": "Use `itertools.chain.from_iterable()` in Python or `arr.flat()` in JS",
    "deep_clone": "Use native `structuredClone()` in JS or `copy.deepcopy()` in Python",
    "capitalize_words": "Use `str.title()` or `str.capitalize()`",
}


class SimplicityEngine:
    """
    Simplicity & Engineering Frugality (Productive Laziness) Gatekeeper.
    """

    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = Path(repo_path or Path.cwd()).resolve()

    def calculate_net_loc(self, diff_summary: Optional[DiffSummary]) -> Dict[str, Any]:
        """
        Calculate Net Lines of Code (LOC) change.
        Rewarding net negative code (deleting more code than adding).
        """
        if not diff_summary:
            return {"net_loc": 0, "is_net_negative": False, "bonus_label": "Neutral"}

        insertions = diff_summary.total_insertions
        deletions = diff_summary.total_deletions
        net = insertions - deletions

        is_net_negative = (net < 0 and deletions >= 10)
        bonus_label = "Neutral"
        if is_net_negative:
            bonus_label = f"⭐ Code Debt Reduction Bonus (Net: {net:+d} LOC)"
        elif net > 500:
            bonus_label = f"⚠️ High Blast Radius (+{net} LOC)"

        return {
            "insertions": insertions,
            "deletions": deletions,
            "net_loc": net,
            "is_net_negative": is_net_negative,
            "bonus_label": bonus_label,
        }

    def scan_dependency_bloat(self, raw_diff: str) -> List[RuleViolation]:
        """
        LAZY-001: Scan diff in manifest files (package.json, pyproject.toml, requirements.txt)
        to catch unnecessary new dependencies when native or stdlib suffices.
        """
        violations: List[RuleViolation] = []
        current_file = ""

        for line in raw_diff.splitlines():
            if line.startswith("+++ b/"):
                current_file = line[6:].strip()
                continue

            if not (line.startswith("+") and not line.startswith("+++")):
                continue

            added_content = line[1:].strip().lower()
            cf_lower = current_file.replace("\\", "/").lower()

            # Check package.json additions
            if cf_lower.endswith("package.json"):
                for pkg, rec in REDUNDANT_NPM_PACKAGES.items():
                    if f'"{pkg}"' in added_content or f"'{pkg}'" in added_content:
                        violations.append(RuleViolation(
                            rule_id="LAZY-001",
                            severity="HIGH",
                            file_path=current_file,
                            message=f"Dependency Bloat: Added redundant npm package `{pkg}`. {rec}.",
                            snippet=line[1:].strip()[:80],
                        ))

            # Check pyproject.toml / requirements.txt additions
            elif cf_lower.endswith("pyproject.toml") or "requirements" in cf_lower:
                for pkg, rec in REDUNDANT_PY_PACKAGES.items():
                    if re.search(rf"""(?i)\b{re.escape(pkg)}\b""", added_content):
                        violations.append(RuleViolation(
                            rule_id="LAZY-001",
                            severity="HIGH",
                            file_path=current_file,
                            message=f"Dependency Bloat: Added redundant Python package `{pkg}`. {rec}.",
                            snippet=line[1:].strip()[:80],
                        ))

        return violations

    def scan_wheel_reinventions(self, raw_diff: str) -> List[RuleViolation]:
        """
        LAZY-003: Scan added code for custom re-implementations of common utilities
        that already exist in standard library or native runtime.
        """
        violations: List[RuleViolation] = []
        current_file = ""
        line_num = 0

        for line in raw_diff.splitlines():
            if line.startswith("+++ b/"):
                current_file = line[6:].strip()
                line_num = 0
                continue

            if line.startswith("@@"):
                match = re.search(r"\+(\d+)", line)
                if match:
                    line_num = int(match.group(1)) - 1
                continue

            if not (line.startswith("+") and not line.startswith("+++")):
                continue

            line_num += 1
            added_line = line[1:].strip()

            # Skip test files and doc files
            cf_lower = current_file.replace("\\", "/").lower()
            if "test" in cf_lower or any(cf_lower.endswith(ext) for ext in (".md", ".txt", ".json")):
                continue

            # Skip comments
            if added_line.startswith("#") or added_line.startswith("//") or added_line.startswith("/*") or added_line.startswith("*"):
                continue
            # Look for function definitions matching common reinvented wheels
            # e.g., def clamp(...), function clamp(...), const clamp = (...) =>
            for func_name, rec in COMMON_REINVENTED_FUNCTIONS.items():
                pattern = rf"""(?i)\b(def|function|const|let|var)\s+{re.escape(func_name)}\s*(=|\()"""
                if re.search(pattern, added_line):
                    violations.append(RuleViolation(
                        rule_id="LAZY-003",
                        severity="MEDIUM",
                        file_path=current_file,
                        line_number=line_num,
                        message=f"Wheel Reinvention: Detected custom `{func_name}()` definition. {rec}.",
                        snippet=added_line[:80],
                    ))

        return violations

    def scan_python_overengineering(self, code_str: str, file_path: str) -> List[RuleViolation]:
        """
        LAZY-002: Detect premature abstractions and trivial pass-through wrappers in Python AST.
        """
        violations: List[RuleViolation] = []
        try:
            tree = ast.parse(code_str)
        except Exception:
            return violations

        for node in ast.walk(tree):
            # 1. Trivial pass-through function wrapper:
            # def wrapper(x, y): return underlying(x, y) with no extra logic
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if len(node.body) == 1 and isinstance(node.body[0], ast.Return):
                    ret_val = node.body[0].value
                    if isinstance(ret_val, ast.Call):
                        # Calling a single function with identical argument count
                        if isinstance(ret_val.func, ast.Name) and ret_val.func.id != node.name:
                            if len(node.args.args) > 0 and len(ret_val.args) == len(node.args.args):
                                # Pass through wrapper detected
                                violations.append(RuleViolation(
                                    rule_id="LAZY-002",
                                    severity="MEDIUM",
                                    file_path=file_path,
                                    line_number=node.lineno,
                                    message=f"Trivial Pass-Through Wrapper: Function `{node.name}` merely proxies to `{ret_val.func.id}` without added logic (KISS violation).",
                                    snippet=f"def {node.name}(...): return {ret_val.func.id}(...)",
                                ))

            # 2. Empty or single-method dummy abstract class / interface
            if isinstance(node, ast.ClassDef):
                # Check if it has ABC or Interface in name or bases
                is_abstract = any(
                    (isinstance(b, ast.Name) and b.id in ("ABC", "Protocol")) for b in node.bases
                ) or "interface" in node.name.lower() or "abstract" in node.name.lower()

                if is_abstract:
                    methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                    if len(methods) <= 1:
                        violations.append(RuleViolation(
                            rule_id="LAZY-002",
                            severity="LOW",
                            file_path=file_path,
                            line_number=node.lineno,
                            message=f"Premature Abstraction: Class `{node.name}` defines only {len(methods)} method(s). Consider YAGNI: prefer a simple concrete function over class hierarchies.",
                            snippet=f"class {node.name}(...)",
                        ))

        return violations

    def scan_diff_level(self, raw_diff: Optional[str], diff_summary: Optional[DiffSummary]) -> List[RuleViolation]:
        """
        Level 1: Fast commit-level check (Diff-level, <50ms).
        Detects dependency bloat and wheel reinventions in added diff lines.
        """
        violations: List[RuleViolation] = []
        diff_text = raw_diff or ""

        # 1. Check dependency bloat in manifests
        violations.extend(self.scan_dependency_bloat(diff_text))

        # 2. Check wheel reinventions in added lines
        violations.extend(self.scan_wheel_reinventions(diff_text))

        return violations

    def scan_focus_level(self, touched_files: List[str]) -> List[RuleViolation]:
        """
        Level 2: Deep focus check (Full-file scope) for `--focus simplicity` / `--focus yagni`.
        Scans entire files for premature abstractions, trivial wrappers, and wheel reinventions.
        """
        violations: List[RuleViolation] = []

        for rel_path in touched_files:
            abs_path = self.repo_path / rel_path
            if not abs_path.is_file():
                continue

            rp_lower = rel_path.replace("\\", "/").lower()
            is_doc = any(rp_lower.endswith(ext) for ext in (".md", ".txt", ".json"))
            is_test = "tests/" in rp_lower or "test_" in rp_lower or "/test/" in rp_lower

            if is_doc or is_test:
                continue

            try:
                content = abs_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            # Python AST over-engineering scan
            if rel_path.endswith(".py"):
                violations.extend(self.scan_python_overengineering(content, rel_path))

        return violations
