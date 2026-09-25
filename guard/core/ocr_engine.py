"""
Alibaba Open Code Review (OCR) Engine & Git Diff Inspector.
Provides:
1. Deterministic Git Diff Parsing (added/modified/deleted files, +/- line counts)
2. Blast Radius & Out-of-Scope File Audit
3. Built-in Multi-Language OCR Rulebook Runner (Secrets, NPE, Memory Leaks, SQLi, XSS, Sync I/O)
4. Subprocess Bridge to Alibaba OCR CLI (`ocr review`)
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class FileDiffStat(BaseModel):
    path: str
    status: str  # "modified", "added", "deleted"
    insertions: int = 0
    deletions: int = 0
    is_out_of_scope: bool = False
    preexisting: bool = False  # Already dirty before pre-task and left unchanged by this task


class DiffSummary(BaseModel):
    files: List[FileDiffStat] = Field(default_factory=list)
    total_insertions: int = 0
    total_deletions: int = 0
    out_of_scope_files: List[str] = Field(default_factory=list)
    raw_diff: str = ""
    is_clean: bool = True


class RuleViolation(BaseModel):
    rule_id: str
    severity: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    file_path: str
    line_number: Optional[int] = None
    message: str
    snippet: str = ""


class OCRReviewResult(BaseModel):
    success: bool
    summary: DiffSummary
    violations: List[RuleViolation] = Field(default_factory=list)
    ocr_cli_output: Optional[str] = None
    passed_all_rules: bool = True
    error_message: Optional[str] = None


class GitDiffInspector:
    """
    Inspects local Git diffs and measures the exact Blast Radius of changes.
    """

    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path or Path.cwd()

    def is_git_repo(self) -> bool:
        git_dir = self.repo_path / ".git"
        return git_dir.exists()

    def get_diff(self, staged_only: bool = False, base_ref: Optional[str] = None) -> str:
        """
        Extract raw diff from Git, including synthetic diffs for untracked files.
        Always returns a valid string (never None).
        Safely decodes UTF-8 to prevent charmap/UnicodeDecodeError on Windows.
        """
        if not self.is_git_repo():
            return ""

        cmd = ["git", "-C", str(self.repo_path), "-c", "core.quotepath=false", "diff"]
        if staged_only:
            cmd.append("--staged")
        elif base_ref:
            cmd.append(base_ref)
        else:
            # Include both staged and unstaged (against HEAD if exists)
            cmd.append("HEAD")

        diff_output = ""
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if res.returncode == 0 and res.stdout:
                diff_output = res.stdout
            else:
                res2 = subprocess.run(
                    ["git", "-C", str(self.repo_path), "-c", "core.quotepath=false", "diff"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                )
                diff_output = res2.stdout or ""
        except Exception:
            diff_output = ""

        diff_output = diff_output or ""

        # Append synthetic diffs for untracked files (so rules engine can inspect secrets/NPE)
        untracked = self.get_untracked_files()
        synthetic_diffs = []
        for uf in untracked:
            if uf in [".gitignore", ".guard/session.json"] or uf.startswith(".guard/"):
                continue
            uf_path = self.repo_path / uf
            if uf_path.is_file():
                try:
                    content = uf_path.read_text(encoding="utf-8", errors="ignore")
                    lines = content.splitlines()
                    synth = [
                        f"diff --git a/{uf} b/{uf}",
                        "new file mode 100644",
                        "--- /dev/null",
                        f"+++ b/{uf}",
                        f"@@ -0,0 +1,{max(1, len(lines))} @@",
                    ]
                    for l in lines:
                        synth.append(f"+{l}")
                    synthetic_diffs.append("\n".join(synth))
                except Exception:
                    pass

        if synthetic_diffs:
            if diff_output:
                diff_output += "\n" + "\n".join(synthetic_diffs)
            else:
                diff_output = "\n".join(synthetic_diffs)

        return diff_output or ""

    def _porcelain_entries(self) -> List[tuple]:
        """
        (XY status, path) for every changed file. `-z` gives raw, unquoted paths (spaces, unicode)
        and reports renames as `new NUL old`; `-uall` lists files inside new directories.
        """
        if not self.is_git_repo():
            return []
        try:
            res = subprocess.run(
                ["git", "-C", str(self.repo_path), "status", "--porcelain", "-z", "-uall"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
        except Exception:
            return []
        parts = (res.stdout or "").split("\0")
        entries = []
        i = 0
        while i < len(parts):
            item = parts[i]
            i += 1
            if len(item) < 4:
                continue
            xy, path = item[:2], item[3:]
            if "R" in xy or "C" in xy:
                i += 1  # skip the original path of a rename/copy
            entries.append((xy, path))
        return entries

    def get_untracked_files(self) -> List[str]:
        return [path for xy, path in self._porcelain_entries() if xy == "??"]

    def get_working_files(self) -> List[str]:
        """
        Returns all files currently touched in the working directory (staged, modified, or untracked).
        """
        return [
            path for _, path in self._porcelain_entries()
            if not path.startswith(".guard") and path != ".gitignore"
        ]

    def create_baseline_snapshot(self) -> Optional[str]:
        """
        Commit object of the current dirty tracked state, without touching the working tree or
        index (`git stash create`). Pinned under refs/guard/baseline so gc cannot prune it.
        """
        try:
            res = subprocess.run(
                ["git", "-C", str(self.repo_path), "stash", "create", "guard pre-task baseline"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
            )
            sha = (res.stdout or "").strip()
            if not sha:
                return None
            subprocess.run(
                ["git", "-C", str(self.repo_path), "update-ref", "refs/guard/baseline", sha],
                capture_output=True, check=False,
            )
            return sha
        except Exception:
            return None

    def get_head(self) -> Optional[str]:
        try:
            res = subprocess.run(
                ["git", "-C", str(self.repo_path), "rev-parse", "--verify", "-q", "HEAD"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
            )
            return res.stdout.strip() or None
        except Exception:
            return None

    def parse_diff(self, raw_diff: Optional[str], expected_files: Optional[List[str]] = None) -> DiffSummary:
        """
        Parse raw git diff string into structured FileDiffStat and detect out-of-scope changes.
        """
        diff_text = raw_diff or ""
        if not diff_text.strip():
            return DiffSummary(files=[], raw_diff="", is_clean=True)

        files_map: Dict[str, FileDiffStat] = {}
        current_file: Optional[str] = None
        current_status = "modified"

        for line in diff_text.splitlines():
            if line.startswith("diff --git"):
                match = re.search(r"diff --git a/(.*) b/(.*)", line)
                if match:
                    current_file = match.group(2)
                    current_status = "modified"
                    files_map[current_file] = FileDiffStat(path=current_file, status=current_status)
            elif line.startswith("new file mode") and current_file:
                files_map[current_file].status = "added"
            elif line.startswith("deleted file mode") and current_file:
                files_map[current_file].status = "deleted"
            elif line.startswith("+") and not line.startswith("+++") and current_file:
                files_map[current_file].insertions += 1
            elif line.startswith("-") and not line.startswith("---") and current_file:
                files_map[current_file].deletions += 1

        stats_list = list(files_map.values())
        tot_ins = sum(s.insertions for s in stats_list)
        tot_del = sum(s.deletions for s in stats_list)

        out_of_scope: List[str] = []
        if expected_files is not None:
            for stat in stats_list:
                if not self._is_expected(stat.path, expected_files):
                    stat.is_out_of_scope = True
                    out_of_scope.append(stat.path)

        return DiffSummary(
            files=stats_list,
            total_insertions=tot_ins,
            total_deletions=tot_del,
            out_of_scope_files=out_of_scope,
            raw_diff=diff_text,
            is_clean=len(stats_list) == 0,
        )

    def _is_expected(self, file_path: str, expected_files: List[str]) -> bool:
        """
        Match on path boundaries only: exact path, bare filename, directory prefix, or glob.
        (Suffix matching would let `a.ts` cover `src/data.ts`.)
        """
        fp_norm = file_path.replace("\\", "/").lower()
        # System & Guard files are always allowed
        if fp_norm in [".gitignore", ".guard/session.json"] or fp_norm.startswith(".guard/"):
            return True
        basename = fp_norm.rsplit("/", 1)[-1]
        for exp in expected_files:
            exp_norm = exp.replace("\\", "/").lower()
            if exp_norm.startswith("./"):
                exp_norm = exp_norm[2:]
            if not exp_norm:
                continue
            # Literal match first, so paths like `app/[id]/page.tsx` still match themselves
            if fp_norm == exp_norm or fp_norm.startswith(exp_norm.rstrip("/") + "/"):
                return True
            if "/" not in exp_norm and basename == exp_norm:
                return True
            if any(ch in exp_norm for ch in "*?[") and glob_to_regex(exp_norm).match(fp_norm):
                return True
        return False


def glob_to_regex(pattern: str) -> "re.Pattern[str]":
    """Path glob: `*`/`?` stay inside one directory, `**` spans directories, `[...]` is a class."""
    out = []
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif c == "*":
            out.append("[^/]*")
            i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        elif c == "[" and "]" in pattern[i + 1:]:
            j = pattern.index("]", i + 1)
            out.append("[" + pattern[i + 1:j].replace("\\", "\\\\") + "]")
            i = j + 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("".join(out) + r"(?:/.*)?$")


def _unsafe_html_sinks(code: str) -> int:
    """
    Count innerHTML / outerHTML assignments on one line whose value is not provably safe.
    Safe values: an empty literal, or a value that is exactly one DOMPurify.sanitize(...) call.
    """
    code = re.sub(r"\s//.*$", "", code)  # drop trailing line comment
    unsafe = 0
    for m in re.finditer(r"\b(?:inner|outer)HTML\s*\+?=(?!=)", code):
        rhs = code[m.end():]
        # value runs until the first `;` that is not inside a string or parentheses
        depth, quote, end = 0, "", len(rhs)
        for k, ch in enumerate(rhs):
            if quote:
                if ch == quote and rhs[k - 1] != "\\":
                    quote = ""
            elif ch in "'\"`":
                quote = ch
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == ";" and depth <= 0:
                end = k
                break
        value = rhs[:end].strip()
        if re.fullmatch(r"(['\"`])\1", value):
            continue
        call = re.match(r"DOMPurify\.sanitize\(", value)
        if call:
            depth = 0
            for k, ch in enumerate(value[call.end() - 1:], start=call.end() - 1):
                depth += ch == "("
                depth -= ch == ")"
                if depth == 0:
                    if not value[k + 1:].strip():
                        break
                    unsafe += 1
                    break
            continue
        unsafe += 1
    return unsafe


class OCRRulebookRunner:
    """
    Multi-language deterministic static rules engine matching Alibaba OCR patterns.
    Operates at 0 cost, 0 latency across 5 Quality Pillars.
    """

    # Pillar: Security - Hardcoded Secrets
    SECRET_REGEX = re.compile(
        r"""(?i)(api[_-]?key|secret|token|password|auth[_-]?token|private[_-]?key)\s*[:=]\s*["']([A-Za-z0-9_\-\.]{12,})["']"""
    )
    # Pillar: Security - SQL Injection string concatenation
    SQLI_REGEX = re.compile(
        r"""(?i)(select\b.+?\bfrom\b|insert\s+into\b|update\b.+?\bset\b|delete\s+from\b).+?["']\s*\+\s*[a-zA-Z_]"""
    )
    # Pillar: Security - Cross-Site Scripting (XSS)
    XSS_REGEX = re.compile(
        r"""(?i)(dangerouslySetInnerHTML\s*=|(?:inner|outer)HTML\s*\+?=(?!=)|\bv-html\s*=)"""
    )
    # Explicit, reviewable suppression: `// guard-allow SEC-003: <reason>` on the same line
    SUPPRESS_REGEX = re.compile(r"guard-allow\s+([A-Z]+-\d+)\s*:\s*(\S.*)")
    # Pillar: Memory Safety - Dangling Listener without remover in component
    DANGLING_LISTENER = re.compile(
        r"""addEventListener\s*\(["'](resize|scroll|mousemove|keydown)["']"""
    )
    # Pillar: Stability - Deep property dereference without optional chaining
    NULL_DEREF = re.compile(
        r"""(?i)(data|res|response|user|item)\.([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)"""
    )
    # Pillar: Performance - Blocking synchronous I/O on async event loop
    BLOCKING_SYNC_IO = re.compile(
        r"""\b(readFileSync|writeFileSync|execSync|spawnSync)\b"""
    )

    def scan_diff(self, raw_diff: Optional[str]) -> List[RuleViolation]:
        diff_text = raw_diff or ""
        violations: List[RuleViolation] = []
        current_file = "unknown"
        line_num = 0

        for line in diff_text.splitlines():
            if line.startswith("+++ b/"):
                current_file = line[6:].strip()
                line_num = 0
                continue
            if line.startswith("@@"):
                match = re.search(r"\+(\d+)", line)
                if match:
                    line_num = int(match.group(1)) - 1
                continue

            if line.startswith("+") and not line.startswith("+++"):
                line_num += 1
                added_code = line[1:].strip()

                cf_lower = current_file.replace("\\", "/").lower()
                is_doc_file = any(cf_lower.endswith(ext) for ext in [".md", ".markdown", ".txt", ".rst"])
                is_test_file = "tests/" in cf_lower or "test_" in cf_lower
                is_js_ts = any(cf_lower.endswith(ext) for ext in [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"])

                # Rule 1: Hardcoded Secrets (Security - Always scanned on ALL files)
                if self.SECRET_REGEX.search(added_code):
                    # Exclude sample dummy tokens in test files or docs
                    if not (is_test_file and "sk_live_9988776655" in added_code):
                        violations.append(RuleViolation(
                            rule_id="SEC-001",
                            severity="CRITICAL",
                            file_path=current_file,
                            line_number=line_num,
                            message="Potential hardcoded secret or API key detected in code addition.",
                            snippet=added_code[:80],
                        ))

                # Rules 2-6 only apply to actual application source code (not doc markdown files)
                if is_doc_file:
                    continue

                # Rule 2: SQL Injection concatenation (Security)
                if self.SQLI_REGEX.search(added_code) and not is_test_file:
                    violations.append(RuleViolation(
                        rule_id="SEC-002",
                        severity="CRITICAL",
                        file_path=current_file,
                        line_number=line_num,
                        message="SQL string concatenation detected. Use parameterized queries/ORM.",
                        snippet=added_code[:80],
                    ))

                # Rule 3: Cross-Site Scripting (XSS) (Security)
                # A comment mentioning "sanitize" no longer exempts the line; only a provably safe
                # value or an explicit `guard-allow SEC-003: reason` marker does (reported as LOW).
                if self.XSS_REGEX.search(added_code) and not is_test_file and (
                    re.search(r"dangerouslySetInnerHTML|\bv-html", added_code, re.IGNORECASE)
                    or _unsafe_html_sinks(added_code) > 0
                ):
                    suppress = self.SUPPRESS_REGEX.search(added_code)
                    if suppress and suppress.group(1) == "SEC-003":
                        violations.append(RuleViolation(
                            rule_id="SEC-003",
                            severity="LOW",
                            file_path=current_file,
                            line_number=line_num,
                            message=f"innerHTML sink suppressed by author: {suppress.group(2).strip()[:120]}",
                            snippet=added_code[:80],
                        ))
                    else:
                        violations.append(RuleViolation(
                            rule_id="SEC-003",
                            severity="HIGH",
                            file_path=current_file,
                            line_number=line_num,
                            message="Raw HTML injection detected (dangerouslySetInnerHTML / innerHTML / v-html). Use textContent, DOMPurify.sanitize(), or mark `// guard-allow SEC-003: <reason>`.",
                            snippet=added_code[:80],
                        ))

                # Rule 4: Memory leak / Dangling Event Listener (Memory Safety)
                if self.DANGLING_LISTENER.search(added_code) and "removeEventListener" not in diff_text and not is_test_file:
                    violations.append(RuleViolation(
                        rule_id="PERF-001",
                        severity="HIGH",
                        file_path=current_file,
                        line_number=line_num,
                        message="Global window/document event listener added without cleanup remover.",
                        snippet=added_code[:80],
                    ))

                # Rule 5: Blocking Synchronous I/O on Event Loop (Performance - Only in JS/TS environments)
                if is_js_ts and self.BLOCKING_SYNC_IO.search(added_code) and not is_test_file:
                    violations.append(RuleViolation(
                        rule_id="PERF-002",
                        severity="MEDIUM",
                        file_path=current_file,
                        line_number=line_num,
                        message="Blocking synchronous I/O detected on thread. Prefer async/await non-blocking operations.",
                        snippet=added_code[:80],
                    ))

                # Rule 6: Deep property dereference without optional chaining (Stability)
                if self.NULL_DEREF.search(added_code) and "?." not in added_code and not is_test_file:
                    violations.append(RuleViolation(
                        rule_id="STAB-001",
                        severity="MEDIUM",
                        file_path=current_file,
                        line_number=line_num,
                        message="Deep object access without optional chaining (?.) may cause Null Pointer / TypeError.",
                        snippet=added_code[:80],
                    ))

        return violations


def run_ocr_audit(
    repo_path: Optional[Path] = None,
    expected_files: Optional[List[str]] = None,
    background_context: Optional[str] = None,
) -> OCRReviewResult:
    inspector = GitDiffInspector(repo_path)
    raw_diff = inspector.get_diff() or ""
    summary = inspector.parse_diff(raw_diff, expected_files=expected_files)

    rulebook = OCRRulebookRunner()
    violations = rulebook.scan_diff(raw_diff)

    for oos in summary.out_of_scope_files:
        violations.append(RuleViolation(
            rule_id="SCOPE-001",
            severity="HIGH",
            file_path=oos,
            line_number=None,
            message="Out-of-scope file modified. Not declared in Pre-Task Impact Note.",
            snippet=f"File: {oos}",
        ))

    passed_all = len([v for v in violations if v.severity in ["CRITICAL", "HIGH"]]) == 0

    ocr_bin = shutil.which("ocr")
    ocr_output: Optional[str] = None
    if ocr_bin and raw_diff.strip():
        try:
            cmd = [ocr_bin, "review"]
            if background_context:
                cmd.extend(["--background", background_context])
            res = subprocess.run(
                cmd,
                cwd=str(repo_path or Path.cwd()),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=45,
            )
            ocr_output = (res.stdout or "") + (res.stderr or "")
        except Exception as e:
            ocr_output = f"OCR CLI notice: {str(e)}"

    return OCRReviewResult(
        success=True,
        summary=summary,
        violations=violations,
        ocr_cli_output=ocr_output,
        passed_all_rules=passed_all,
    )
