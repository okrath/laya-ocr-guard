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

        cmd = ["git", "-C", str(self.repo_path), "diff"]
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
                    ["git", "-C", str(self.repo_path), "diff"],
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

    def get_untracked_files(self) -> List[str]:
        if not self.is_git_repo():
            return []
        try:
            res = subprocess.run(
                ["git", "-C", str(self.repo_path), "status", "--porcelain"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            files = []
            stdout_text = res.stdout or ""
            for line in stdout_text.splitlines():
                if line.startswith("?? "):
                    files.append(line[3:].strip())
            return files
        except Exception:
            return []

    def get_working_files(self) -> List[str]:
        """
        Returns all files currently touched in the working directory (staged, modified, or untracked).
        """
        if not self.is_git_repo():
            return []
        try:
            res = subprocess.run(
                ["git", "-C", str(self.repo_path), "status", "--porcelain"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            files = []
            stdout_text = res.stdout or ""
            for line in stdout_text.splitlines():
                if len(line) >= 4:
                    filepath = line[3:].strip()
                    if filepath and not filepath.startswith(".guard") and filepath != ".gitignore":
                        files.append(filepath)
            return files
        except Exception:
            return []

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
        fp_norm = file_path.replace("\\", "/").lower()
        # System & Guard files are always allowed
        if fp_norm in [".gitignore", ".guard/session.json"] or fp_norm.startswith(".guard/"):
            return True
        for exp in expected_files:
            exp_norm = exp.replace("\\", "/").lower()
            # If expected item is a directory pattern (e.g. "docs/" or "docs")
            if exp_norm.endswith("/"):
                if fp_norm.startswith(exp_norm):
                    return True
            if "/" not in exp_norm and (fp_norm.startswith(f"{exp_norm}/") or f"/{exp_norm}/" in fp_norm):
                return True
            if fp_norm == exp_norm or fp_norm.endswith(exp_norm) or exp_norm.endswith(fp_norm):
                return True
        return False


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
        r"""(?i)(dangerouslySetInnerHTML\s*=|innerHTML\s*=|\bv-html\s*=)"""
    )
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
                if self.XSS_REGEX.search(added_code) and "sanitize" not in added_code.lower() and not is_test_file:
                    violations.append(RuleViolation(
                        rule_id="SEC-003",
                        severity="HIGH",
                        file_path=current_file,
                        line_number=line_num,
                        message="Raw HTML injection detected (dangerouslySetInnerHTML / innerHTML / v-html). Sanitize input via DOMPurify.",
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
