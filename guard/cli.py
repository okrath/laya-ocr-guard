"""
Complete CLI for Laya-OCR-Guard (`guard`).
Provides:
- `guard pre "<prompt>"`: Triage, Baseline Contracts, Invariants, Pre-task Note
- `guard post [--auto-fix] [--focus]`: Diff Audit, Build Check, OCR Rules, Laya Invariants, LLM Final Gate Verdict
- `guard config` [show | llm | test | sync]: Manage LLM and OCR credentials
- `guard hook` [install | uninstall | status]: Bind hooks and AI Agent directives to target repos
- `guard run "<prompt>" -- <cmd>`: Sandwich pattern wrapper
- `guard doctor`: System diagnostic check & supply-chain update quarantine audit
- `guard update` [ocr | self]: Safe upgrades respecting 3-day quarantine policy
- `guard review [--focus]`: Final Safety Gate Review by the configured LLM
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from guard import __app_name__, __version__
from guard.core.config import get_global_config_path, get_local_config_path, load_config, print_config_table
from guard.core.laya_engine import DomainType, LayaEngine
from guard.core.hygiene_engine import HygieneEngine
from guard.core.llm_reviewer import LLMReviewerEngine, ReviewVerdict
from guard.core.ocr_engine import GitDiffInspector, OCRRulebookRunner, RuleViolation
from guard.core.removal_check import check_removed_symbols
from guard.core.repo_setup import ensure_repo_setup, git_root, refresh_after_upgrade, refresh_repo
from guard.core.project_invariants import (
    INVARIANTS_FILENAME,
    InvariantsFileError,
    append_learned_invariants,
    evaluate_checks,
    init_invariants_file,
    load_project_invariants,
    removed_or_relaxed,
)
from guard.core.simplicity_engine import SimplicityEngine
from guard.core.session import BuildCheckResult, PostTaskRecord, SessionManager, SessionStatus
from guard.core.updater import (
    UpdateSecurityStatus,
    check_guard_self_update,
    check_ocr_update,
    get_cached_update_notice,
    maybe_trigger_background_update_check,
    perform_ocr_upgrade,
    perform_self_upgrade,
)
from guard.domains.detector import (
    analyzer_domain,
    detect_domain,
    detect_build_command,
    detect_repo_domain,
    extract_contracts_and_invariants,
)
from guard.hooks.installer import HookInstaller
from guard.reporters.markdown import generate_post_task_markdown, generate_pre_task_markdown
from guard.reporters.terminal import render_post_task_terminal, render_pre_task_terminal

app = typer.Typer(
    name=__app_name__,
    help="🛡️ Laya-OCR-Guard: Dual-gate impact analysis & regression guard for AI-assisted development",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()


def version_callback(value: bool):
    if value:
        console.print(f"[bold cyan]{__app_name__}[/bold cyan] version [bold green]{__version__}[/bold green]")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show guard version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
):
    pass


# ---------------------------------------------------------
# Core Task Execution Logic (Callable by CLI & Runner)
# ---------------------------------------------------------

def _fingerprint(path: Path) -> str:
    """Content hash used to tell whether a pre-existing dirty file was touched during the task."""
    if not path.is_file():
        return "<deleted>"
    return hashlib.sha1(path.read_bytes()).hexdigest()


def _file_at(repo: Path, ref: Optional[str], path: str) -> Optional[str]:
    """Content of `path` at commit `ref`, or None."""
    if not ref:
        return None
    res = subprocess.run(
        ["git", "-C", str(repo), "show", f"{ref}:{path}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )
    return res.stdout if res.returncode == 0 else None


def _drop_diff_files(raw_diff: str, drop: set) -> str:
    """Remove the per-file chunks of `drop` paths from a unified diff."""
    if not drop:
        return raw_diff
    chunks = raw_diff.split("diff --git ")
    kept = [c for c in chunks[1:] if not any(c.startswith(f"a/{p} b/") for p in drop)]
    return (chunks[0] + "".join("diff --git " + c for c in kept)) if kept else ""


def _prompt_paths(prompt: str, repo: Path) -> List[str]:
    """Paths named in the prompt: existing files/dirs, or new `dir/file.ext` paths to be created."""
    # Globs are only accepted through --scope: prose like "do not edit *.css" must not widen scope.
    tokens = re.findall(r"[\w\-\.\/\\\[\]]+\.[a-zA-Z0-9]+|[\w\-\.]+[\/\\][\w\-\.\/\\\[\]]*", prompt)
    out = []
    for t in tokens:
        t = t.replace("\\", "/")
        if t.startswith("./"):
            t = t[2:]
        is_new_file_path = "/" in t and bool(re.search(r"\.[a-zA-Z0-9]+$", t))
        if t and ((repo / t).exists() or is_new_file_path):
            out.append(t)
    return sorted(set(out))


def execute_pre_task(
    prompt: str,
    repo_path: Optional[Path] = None,
    quick: bool = False,
    scope: Optional[List[str]] = None,
    allow_dirty: bool = False,
    force: bool = False,
) -> bool:
    target_repo = Path(repo_path or Path.cwd()).resolve()
    invariants_existed = (target_repo / INVARIANTS_FILENAME).exists()
    for msg in ensure_repo_setup(target_repo):
        console.print(f"[cyan]🔧 guard setup: {msg}[/cyan]")
    config = load_config(target_repo)
    laya = LayaEngine(model_name=config.laya.model_name, device=config.laya.device)
    session_mgr = SessionManager(target_repo)

    # 0. A pre-task gate that can be re-run after editing would let scope be declared retroactively.
    #    An unfinished (AWAITING_POST) or rejected (NEEDS_FIX) session can only be superseded with
    #    --force, and the new session inherits its baseline, base commit and scope: a restart can
    #    never turn the task's own edits into "pre-existing" baseline or widen the audited scope.
    previous = session_mgr.load_local_session()
    superseded = previous if (
        previous and previous.pre and previous.status in (SessionStatus.AWAITING_POST, SessionStatus.NEEDS_FIX)
    ) else None
    if superseded and not force:
        state = "unfinished" if superseded.status == SessionStatus.AWAITING_POST else "rejected (REVISE)"
        console.print(
            f"[bold red]❌ The previous guard session {superseded.session_id} is {state}.[/bold red]\n"
            "Finish it with [bold]guard post[/bold]. [bold]guard pre --force[/bold] restarts it, keeping its baseline and scope; "
            "the restart is recorded and any scope added by it is reported as SCOPE-004."
        )
        return False

    diff_inspector = GitDiffInspector(target_repo)
    requested_scope = sorted(
        {p.replace("\\", "/").rstrip("/") for p in _prompt_paths(prompt, target_repo) + list(scope or [])} - {""}
    )
    if superseded:
        old = superseded.pre
        baseline_dirty = dict(old.baseline_dirty)
        base_ref = old.base_ref
        baseline_snapshot = old.baseline_snapshot  # never re-snapshot: that would absorb the task's edits
        candidate_files = list(old.expected_files)
        late_scope = sorted(set(old.late_scope) | (set(requested_scope) - set(old.expected_files)))
        restarts = old.restarts + [{
            "session_id": superseded.session_id,
            "status": superseded.status.value,
            "at": datetime.now(timezone.utc).isoformat(),
        }]
    else:
        working_files = diff_inspector.get_working_files()
        if not invariants_existed:
            # The file guard setup just created is not the user's pending work
            working_files = [f for f in working_files if f != INVARIANTS_FILENAME]
        if working_files and not allow_dirty:
            listing = "\n".join(f"  • {f}" for f in working_files[:20])
            more = f"\n  … and {len(working_files) - 20} more" if len(working_files) > 20 else ""
            console.print(
                f"[bold red]❌ Working tree already has {len(working_files)} modified file(s) before the task starts:[/bold red]\n{listing}{more}\n"
                "Pre-task must run BEFORE editing. Commit or stash them first. Only if they are unrelated work that must stay, "
                "pass [bold]--allow-dirty[/bold]: they are then reported as pre-existing and never vouched for."
            )
            return False
        baseline_dirty = {f: _fingerprint(target_repo / f) for f in working_files}
        base_ref = diff_inspector.get_head()
        baseline_snapshot = diff_inspector.create_baseline_snapshot() if working_files else None
        candidate_files = requested_scope
        late_scope = []
        restarts = []

    # 1. Domain comes from the repository itself; the prompt-based triage is only a hint.
    domain = detect_domain(target_repo)

    # 2. Laya System 1 Triage (<30ms)
    triage = laya.triage(prompt=prompt, context_files=candidate_files)

    # 3. Domain Contracts & Invariants Extraction
    try:
        contracts, invariants = extract_contracts_and_invariants(
            repo_path=target_repo,
            prompt=prompt,
            domain=domain,
            files=candidate_files,
        )
    except InvariantsFileError as e:
        console.print(f"[bold red]❌ {e}[/bold red]\nFix guard.invariants.json before starting the task.")
        return False
    baseline_eval = laya.evaluate_invariants(
        invariants=[inv.model_dump() for inv in invariants],
        git_diff="",
        files_changed=[],
        repo_path=target_repo,
    )
    # Only real checks have a meaningful baseline; diff heuristics trivially "pass" on an empty diff
    checked = {inv.id for inv in invariants if inv.checks}
    baseline_status = {c.id: c.status for c in baseline_eval.checks if c.id in checked}
    if superseded:
        baseline_status = dict(superseded.pre.baseline_invariant_status)

    # 4. Save Session
    session = session_mgr.start_pre_session(
        prompt=prompt,
        triage=triage,
        expected_files=candidate_files,
        contracts=contracts,
        invariants=invariants,
        non_regression_strategy=f"Isolate changes to domain {domain.value.upper()}. Maintain 100% existing baseline contracts.",
        domain=domain,
        baseline_dirty=baseline_dirty,
        baseline_invariant_status=baseline_status,
        base_ref=base_ref,
        late_scope=late_scope,
        baseline_snapshot=baseline_snapshot,
        restarts=restarts,
    )

    # 5. Output Terminal & Write Markdown
    render_pre_task_terminal(session.pre)
    md_content = generate_pre_task_markdown(session.pre)
    pre_note_path = target_repo / ".guard" / "PRE_TASK_NOTE.md"
    try:
        pre_note_path.write_text(md_content, encoding="utf-8")
        console.print(f"\n[dim]📄 Pre-Task Note written to: {pre_note_path}[/dim]")
    except Exception:
        pass

    return True


def execute_post_task(
    repo_path: Optional[Path] = None,
    auto_fix: bool = False,
    focus: str = "all",
    hook: bool = False,
) -> bool:
    target_repo = Path(repo_path or Path.cwd()).resolve()
    for msg in ensure_repo_setup(target_repo, create_invariants=not hook):
        console.print(f"[cyan]🔧 guard setup: {msg}[/cyan]")
    config = load_config(target_repo)
    session_mgr = SessionManager(target_repo)
    # In a git hook only this repo's own session counts; never adopt another repo's session.
    session = session_mgr.load_local_session() if hook else session_mgr.load_session()
    if hook and session is None:
        console.print("[dim]Laya-OCR-Guard: no guard session in this repository, skipping.[/dim]")
        return True
    if hook and session.status == SessionStatus.COMPLETED:
        # An approval covers only the exact file contents it approved, not later or unrelated work
        approved = session.post.approved_fingerprints if session.post else {}
        uncovered = [
            f for f in GitDiffInspector(target_repo).get_working_files()
            if approved.get(f) != _fingerprint(target_repo / f)
        ]
        if not uncovered:
            console.print("[dim]Laya-OCR-Guard: changes match the last approved guard session, skipping.[/dim]")
            return True
        listing = "\n".join(f"  • {f}" for f in uncovered[:20])
        console.print(
            f"[bold red]❌ {len(uncovered)} changed file(s) are not covered by the last approved guard session "
            f"({session.session_id}):[/bold red]\n{listing}\n"
            "Run [bold]guard pre \"<task>\"[/bold] before editing and [bold]guard post[/bold] after, or "
            "[bold]guard reset[/bold] to stop guarding this work."
        )
        return False

    pre = session.pre if session else None
    expected_files = pre.expected_files if pre else []
    scope_declared = bool(expected_files)
    baseline_dirty = pre.baseline_dirty if pre else {}
    invariants_dicts = [inv.model_dump() for inv in (pre.locked_invariants if pre else [])]

    # 1. OCR Diff & Blast Radius Audit (no declared scope -> no scope verdict, instead of flagging every file)
    diff_inspector = GitDiffInspector(target_repo)
    # Diff against the commit recorded at pre, so commits made mid-task are still audited
    raw_diff = diff_inspector.get_diff(base_ref=pre.base_ref if pre else None) or ""
    diff_summary = diff_inspector.parse_diff(raw_diff, expected_files=expected_files if scope_declared else None)

    # Files dirty before pre-task and untouched since are not attributed to this task.
    for f in diff_summary.files:
        if f.path in baseline_dirty and baseline_dirty[f.path] == _fingerprint(target_repo / f.path):
            f.preexisting = True
            f.is_out_of_scope = False
    # guard.invariants.json may grow outside the declared scope (guard writes learned rules into it);
    # removing or relaxing an existing rule is checked separately below and blocks.
    for f in diff_summary.files:
        if f.path == INVARIANTS_FILENAME:
            f.is_out_of_scope = False
    diff_summary.out_of_scope_files = [f.path for f in diff_summary.files if f.is_out_of_scope]
    preexisting_files = [f.path for f in diff_summary.files if f.preexisting]
    deleted_files = [f.path for f in diff_summary.files if f.status == "deleted" and not f.preexisting]

    # With a baseline snapshot, rules and the LLM see exactly the task's own edits; pre-existing
    # changes stay listed (and scope-audited) but are not reviewed as if the task wrote them.
    task_diff = raw_diff
    snapshot = pre.baseline_snapshot if pre else None
    if snapshot:
        task_diff = _drop_diff_files(diff_inspector.get_diff(base_ref=snapshot) or "", set(preexisting_files))
    task_summary = diff_inspector.parse_diff(task_diff)

    # 2. OCR Rulebook & Code Hygiene scan (Two-tier: diff-level vs full-file focus)
    rulebook = OCRRulebookRunner()
    violations = rulebook.scan_diff(task_diff)

    late_scope = pre.late_scope if pre else []
    for f in diff_summary.out_of_scope_files:
        if late_scope and diff_inspector._is_expected(f, late_scope):
            violations.append(RuleViolation(
                rule_id="SCOPE-004",
                severity="HIGH",
                file_path=f,
                message="Scope for this file was only declared by a `guard pre --force` restart after edits began.",
            ))
    for d in deleted_files:
        violations.append(RuleViolation(
            rule_id="SCOPE-002",
            severity="MEDIUM",
            file_path=d,
            message="File deleted. Confirm the task explicitly asked for this removal.",
        ))
    if baseline_dirty:
        attributable = bool(snapshot)
        violations.append(RuleViolation(
            rule_id="SCOPE-003",
            severity="MEDIUM" if attributable else "HIGH",
            file_path=", ".join(sorted(baseline_dirty)[:10]) + (" …" if len(baseline_dirty) > 10 else ""),
            message=(
                f"{len(baseline_dirty)} file(s) were already modified before pre-task (--allow-dirty). "
                + ("Review covers only edits made after pre-task (diff vs baseline snapshot); the pre-existing changes are not vouched for."
                   if attributable else "Guard cannot attribute or vouch for those changes.")
            ),
        ))

    # Removals a compiler cannot see (string keys, exports, CSS classes) checked over the whole repo
    removal_violations, removal_summary = check_removed_symbols(target_repo, task_diff)
    violations.extend(removal_violations)
    evidence = [removal_summary] if removal_summary else []

    # Weakening the rulebook is never a side effect: a removed or relaxed invariant blocks
    if pre and any(f.path == INVARIANTS_FILENAME for f in diff_summary.files):
        base_text = _file_at(target_repo, pre.baseline_snapshot or pre.base_ref, INVARIANTS_FILENAME)
        if base_text:
            try:
                old_items = json.loads(base_text).get("invariants", [])
                new_items = load_project_invariants(target_repo) or []
            except (ValueError, AttributeError, InvariantsFileError):
                old_items, new_items = [], []
            declared = scope_declared and diff_inspector._is_expected(INVARIANTS_FILENAME, expected_files)
            for note in removed_or_relaxed(old_items, new_items):
                violations.append(RuleViolation(
                    rule_id="INV-WEAKENED",
                    # An explicitly scoped rulebook edit is reviewed; a silent one blocks
                    severity="HIGH" if declared else "CRITICAL",
                    file_path=INVARIANTS_FILENAME,
                    message=f"Invariant {note}. Removing or relaxing a project invariant needs an explicit task and review.",
                ))

    hygiene = HygieneEngine(target_repo)
    if (focus or "").lower() in ("dead-code", "hygiene"):
        touched = [f.path for f in diff_summary.files]
        hygiene_violations = hygiene.scan_focus_level(touched)
    else:
        hygiene_violations = hygiene.scan_diff_level(task_diff, task_summary)
    violations.extend(hygiene_violations)

    simplicity = SimplicityEngine(target_repo)
    if (focus or "").lower() in ("simplicity", "yagni", "lazy"):
        touched = [f.path for f in diff_summary.files]
        simplicity_violations = simplicity.scan_focus_level(touched)
    else:
        simplicity_violations = simplicity.scan_diff_level(task_diff, task_summary)
    violations.extend(simplicity_violations)
    # 3. Deterministic Build Check (0 token)
    build_cmd = detect_build_command(target_repo)
    build_res: Optional[BuildCheckResult] = None
    if build_cmd:
        start_t = time.perf_counter()
        try:
            p = subprocess.run(
                build_cmd,
                shell=True,
                cwd=str(target_repo),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
            )
            duration = time.perf_counter() - start_t
            stdout_str = p.stdout or ""
            stderr_str = p.stderr or ""
            build_res = BuildCheckResult(
                command=build_cmd,
                passed=(p.returncode == 0),
                exit_code=p.returncode,
                output=stdout_str + stderr_str,
                duration_s=duration,
            )
        except Exception as e:
            duration = time.perf_counter() - start_t
            build_res = BuildCheckResult(
                command=build_cmd,
                passed=False,
                exit_code=1,
                output=str(e),
                duration_s=duration,
            )

    # 4. Invariants: project checks run on current files; template invariants only get diff heuristics
    laya = LayaEngine(model_name=config.laya.model_name, device=config.laya.device)
    inv_eval = laya.evaluate_invariants(
        invariants=invariants_dicts,
        git_diff=task_diff,
        files_changed=[f.path for f in diff_summary.files],
        repo_path=target_repo,
    )
    baseline_status = pre.baseline_invariant_status if pre else {}
    for c in inv_eval.checks:
        if c.status == "failed" and baseline_status.get(c.id) == "failed":
            # Not a regression caused by this task: warn, do not block
            c.status = "baseline_failed"
            c.passed = True
            c.notes += " (already failing before this task)"

    # A new or edited guard.invariants.json is not locked by this session, so self-check it on the
    # current tree: a rule that fails on the code it was written for is a broken rule.
    if any(f.path == INVARIANTS_FILENAME for f in diff_summary.files):
        try:
            new_items = load_project_invariants(target_repo) or []
        except InvariantsFileError as e:
            violations.append(RuleViolation(rule_id="INV-FILE", severity="CRITICAL", file_path=INVARIANTS_FILENAME, message=str(e)))
        else:
            self_check = laya.evaluate_invariants(
                invariants=[{"id": i["id"], "description": i["description"], "checks": i.get("checks") or []} for i in new_items],
                git_diff="",
                files_changed=[],
                repo_path=target_repo,
            )
            for c in self_check.checks:
                c.id = f"{c.id} (new {INVARIANTS_FILENAME}, self-check)"
                inv_eval.checks.append(c)
            inv_eval.unverified_count += self_check.unverified_count
    inv_eval.all_passed = not any(c.status == "failed" for c in inv_eval.checks)

    # 5. LLM Final Gatekeeper Review (Calling the user-configured LLM)
    reviewer = LLMReviewerEngine(config=config)
    domain = pre.domain if pre else DomainType.BACKEND
    prompt = pre.prompt if pre else "Post-task verification"

    review_verdict = reviewer.review(
        prompt=prompt,
        domain=domain,
        diff_summary=diff_summary.model_copy(update={"raw_diff": task_diff}),
        build_check=build_res,
        violations=violations,
        invariant_result=inv_eval,
        contracts=pre.existing_contracts if pre else None,
        use_llm=True,
        focus=focus,
        evidence=evidence,
    )

    all_passed = (review_verdict.verdict == ReviewVerdict.APPROVED)

    # Rules the reviewer discovered are written only after validation (new, and passing on this code),
    # before fingerprints are taken so the updated file is part of what was approved.
    learned, rejected_props = append_learned_invariants(
        target_repo, review_verdict.proposed_invariants, session.session_id if session else "unknown",
    )

    # 6. Save Post Record
    post_rec = PostTaskRecord(
        files_modified=[f.path for f in diff_summary.files],
        diff_summary=diff_summary,
        out_of_scope_files=diff_summary.out_of_scope_files,
        build_check=build_res,
        rule_violations=violations,
        invariant_result=inv_eval,
        all_passed=all_passed,
        muse_verdict=review_verdict.verdict.value,
        muse_score=review_verdict.score,
        muse_notes=review_verdict.summary,
        review_mode=review_verdict.review_mode,
        llm_error=review_verdict.llm_error,
        scope_declared=scope_declared,
        preexisting_files=preexisting_files,
        deleted_files=deleted_files,
        approved_fingerprints=(
            {
                p: _fingerprint(target_repo / p)
                for p in {f.path for f in diff_summary.files} | ({INVARIANTS_FILENAME} if learned else set())
            } if all_passed else {}
        ),
        learned_invariants=learned,
        rejected_invariant_proposals=rejected_props,
    )

    session_mgr.complete_post_session(post_rec)

    # 7. Render Terminal & Markdown
    render_post_task_terminal(post_rec, pre)
    md_content = generate_post_task_markdown(post_rec, pre)
    post_report_path = target_repo / ".guard" / "POST_TASK_REPORT.md"
    try:
        post_report_path.write_text(md_content, encoding="utf-8")
        console.print(f"\n[dim]📄 Post-Task Report written to: {post_report_path}[/dim]")
    except Exception:
        pass

    if not all_passed and review_verdict.remediation_steps:
        console.print(Panel(
            "\n".join(f"  [bold red]•[/bold red] {s}" for s in review_verdict.remediation_steps),
            title="🔧 Actionable Remediation Checklist",
            border_style="red",
        ))

    return all_passed


# ---------------------------------------------------------
# CLI Commands
# ---------------------------------------------------------

@app.command("pre")
def pre_cmd(
    prompt: str = typer.Argument(..., help="Prompt or task about to be executed by developer/agent"),
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Target repository directory"),
    quick: bool = typer.Option(False, "--quick", "-q", help="Quick mode (local triage only)"),
    scope: Optional[List[str]] = typer.Option(None, "--scope", "-s", help="Allowed file/dir/glob (repeatable), e.g. --scope 'src/ui/**'"),
    allow_dirty: bool = typer.Option(False, "--allow-dirty", help="Start even though files are already modified (recorded as pre-existing baseline)"),
    force: bool = typer.Option(False, "--force", help="Restart an unfinished or rejected session (inherits its baseline and scope)"),
):
    """
    Run Pre-Task Guard BEFORE editing: triage, scope declaration, baseline contracts & invariants.
    """
    success = execute_pre_task(
        prompt=prompt,
        repo_path=Path(repo) if repo else None,
        quick=quick,
        scope=scope,
        allow_dirty=allow_dirty,
        force=force,
    )
    if not success:
        raise typer.Exit(code=1)


@app.command("post")
def post_cmd(
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Target repository directory"),
    auto_fix: bool = typer.Option(False, "--auto-fix", help="Trigger self-healing suggestions"),
    focus: str = typer.Option("all", "--focus", "-f", help="Quality pillar focus: 'all', 'security', 'memory', 'performance', 'ux', 'dead-code', 'simplicity'"),
    hook: bool = typer.Option(False, "--hook", help="Git-hook mode: skip when this repository has no guard session"),
):
    """
    Run Post-Task Guard: diff audit, build checks, invariant checks & LLM final verification.
    """
    passed = execute_post_task(repo_path=Path(repo) if repo else None, auto_fix=auto_fix, focus=focus, hook=hook)
    if not passed:
        raise typer.Exit(code=1)


@app.command("reset")
def reset_cmd(
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Target repository directory"),
):
    """
    Close the current guard session (e.g. after its work was committed or abandoned).
    The session is archived under .guard/history/ so the decision stays auditable.
    """
    target_repo = Path(repo).resolve() if repo else Path.cwd().resolve()
    mgr = SessionManager(target_repo)
    session = mgr.load_local_session()
    if session is None:
        console.print("[yellow]No guard session in this repository.[/yellow]")
        return
    archived = mgr.archive_and_clear()
    console.print(
        f"[bold yellow]Guard session {session.session_id} ({session.status.value}) closed.[/bold yellow] "
        f"Archived to {archived}."
    )


@app.command("run")
def run_cmd(
    prompt: str = typer.Argument(..., help="Prompt/task to execute"),
    command: List[str] = typer.Argument(..., help="Command to run after pre-task (e.g. -- git status)"),
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Target repository directory"),
    auto_fix: bool = typer.Option(False, "--auto-fix", help="Auto-fix loop"),
    scope: Optional[List[str]] = typer.Option(None, "--scope", "-s", help="Allowed file/dir/glob (repeatable)"),
    allow_dirty: bool = typer.Option(False, "--allow-dirty", help="Start even though files are already modified"),
    force: bool = typer.Option(False, "--force", help="Restart an unfinished or rejected session (inherits its baseline and scope)"),
):
    """
    Execute Sandwich Pattern: `guard pre` -> `agent-command` -> `guard post`.
    """
    from guard.hooks.runner import run_sandwich_task
    code = run_sandwich_task(
        prompt=prompt,
        command=command,
        repo_path=Path(repo) if repo else None,
        auto_fix=auto_fix,
        scope=scope,
        allow_dirty=allow_dirty,
        force=force,
    )
    if code != 0:
        raise typer.Exit(code=code)


# Subcommand: guard invariants
invariants_app = typer.Typer(
    name="invariants",
    help="📜 Create and check guard.invariants.json (project rules checked by pre/post)",
    no_args_is_help=True,
)
app.add_typer(invariants_app, name="invariants")


@invariants_app.command("init")
def invariants_init_cmd(
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Target repository directory"),
):
    """
    Create guard.invariants.json, importing numbered items under an 'Invariants' / 'Bất biến'
    heading of AGENT.md / AGENTS.md / CLAUDE.md. Never overwrites an existing file.
    """
    target_repo = Path(repo).resolve() if repo else Path.cwd().resolve()
    path, created, imported = init_invariants_file(target_repo)
    if not created:
        console.print(f"[yellow]{path} already exists; nothing changed. Run `guard invariants check`.[/yellow]")
        return
    console.print(f"[bold green]✅ Created {path}[/bold green] with {imported} invariant(s) imported from agent docs.")
    if imported:
        console.print("[dim]Imported entries have no checks yet (UNVERIFIED): add {\"files\": glob, \"forbid\"|\"require\": regex} checks, then run `guard invariants check`.[/dim]")


@invariants_app.command("check")
def invariants_check_cmd(
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Target repository directory"),
):
    """
    Evaluate guard.invariants.json on the current tree, without a guard session.
    Exit code 1 when a check fails, 2 when the file is missing or malformed.
    """
    target_repo = Path(repo).resolve() if repo else Path.cwd().resolve()
    try:
        items = load_project_invariants(target_repo)
    except InvariantsFileError as e:
        console.print(f"[bold red]❌ {e}[/bold red]")
        raise typer.Exit(code=2)
    if items is None:
        console.print(f"[yellow]No {INVARIANTS_FILENAME} in {target_repo}. Create it with `guard invariants init`.[/yellow]")
        raise typer.Exit(code=2)

    table = Table(title=f"📜 {INVARIANTS_FILENAME} ({len(items)} invariants)", show_header=True)
    table.add_column("ID", style="bold")
    table.add_column("Status", justify="center")
    table.add_column("Notes", style="dim")
    failed = 0
    for inv in items:
        status, note = evaluate_checks(target_repo, inv.get("checks") or [])
        failed += status == "failed"
        badge = {"passed": "[green]✅ PASSED[/green]", "failed": "[bold red]❌ FAILED[/bold red]"}.get(status, "[yellow]⚪ UNVERIFIED[/yellow]")
        table.add_row(str(inv["id"]), badge, note)
    console.print(table)
    if failed:
        raise typer.Exit(code=1)


# Subcommand: guard config
config_app = typer.Typer(
    name="config",
    help="⚙️ Manage Guard configuration (LLM, Alibaba OCR, Laya)",
    no_args_is_help=False,
)
app.add_typer(config_app, name="config")


@config_app.callback(invoke_without_command=True)
def config_main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        local_p = get_local_config_path()
        global_p = get_global_config_path()
        active_p = local_p if local_p.is_file() else global_p
        info = f"Source: {active_p}" if active_p.is_file() else "Default (No config file saved yet)"
        cfg = load_config()
        print_config_table(cfg, info)


@config_app.command("llm")
def config_llm_cmd(
    local: bool = typer.Option(False, "--local", "-l", help="Save config to local repository (.guard/config.json)"),
):
    """
    Interactive Step-by-Step wizard to configure LLM (OpenAI-compatible or Anthropic) and auto-sync to Alibaba OCR.
    """
    from guard.core.config import run_llm_wizard
    run_llm_wizard(local=local)


@config_app.command("test")
def config_test_cmd(
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Target repository directory"),
):
    """
    Ping test the currently configured LLM endpoint.
    """
    from guard.core.llm_client import ping_llm
    cfg = load_config(Path(repo) if repo else None)
    console.print(f"[cyan]Testing connection to [bold]{cfg.llm.base_url}[/bold] (model: {cfg.llm.model})...[/cyan]")
    success, msg, latency = ping_llm(cfg.llm)
    if success:
        console.print(f"[bold green]✅ Ping SUCCESS![/bold green] Response time: {latency:.1f}ms")
    else:
        console.print(f"[bold red]❌ Ping FAILED:[/bold red] {msg}")


@config_app.command("sync")
def config_sync_cmd(
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Target repository directory"),
):
    """
    Manually synchronize LLM credentials to Alibaba Open Code Review (ocr) CLI.
    """
    from guard.core.config import sync_to_alibaba_ocr
    cfg = load_config(Path(repo) if repo else None)
    synced, msg = sync_to_alibaba_ocr(cfg.llm)
    if synced:
        console.print(f"[bold green]✅ {msg}[/bold green]")
    else:
        console.print(f"[yellow]⚠️ {msg}[/yellow]")


# Subcommand: guard hook
hook_app = typer.Typer(
    name="hook",
    help="🪝 Manage Guard Hooks in target repositories",
    no_args_is_help=False,
)
app.add_typer(hook_app, name="hook")


@hook_app.command("refresh")
def hook_refresh_cmd(
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Also set up / refresh this repository"),
):
    """
    Rewrite what guard installed earlier to the current version: global hooks, guard blocks in
    repository hooks and the directive block in agent docs (only where guard markers exist).
    """
    target = Path(repo).resolve() if repo else Path.cwd().resolve()
    messages = refresh_after_upgrade(force=True) + ensure_repo_setup(target, create_invariants=False) + refresh_repo_if_git(target)
    for msg in messages or ["everything is already up to date"]:
        style = "yellow" if msg.startswith("WARN") else "green"
        console.print(f"[{style}]• {msg}[/{style}]")


def refresh_repo_if_git(path: Path) -> List[str]:
    root = git_root(path)
    return refresh_repo(root) if root else []


@hook_app.command("install")
def hook_install_cmd(
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Target repository directory"),
    mode: Optional[str] = typer.Option(None, "--mode", "-m", help="Mode: 'git' (stealth), 'agent', or 'all'"),
    stealth: bool = typer.Option(False, "--stealth", "-s", help="Shortcut for --mode git (Zero workspace footprint, Git hooks only)"),
    global_hooks: bool = typer.Option(False, "--global", "-g", help="Configure Git hooks globally (git config --global core.hooksPath ~/.guard/hooks)"),
    all_repos: bool = typer.Option(False, "--all-repos", help="Install Git hooks to all discovered child Git repositories in workspace"),
    select_repos: Optional[str] = typer.Option(None, "--select-repos", help="Comma-separated indices (1,2) or names of child repositories"),
):
    """
    Install Guard hooks. Without options this installs the global hooks (every repository on
    the machine); each repository is then set up lazily the first time guard runs in it.
    Options keep the per-repository / workspace modes.
    """
    if not any([repo, mode, stealth, all_repos, select_repos]):
        global_hooks = True  # default: one global install instead of one per folder

    if global_hooks:
        console.print("[cyan]Configuring Global Git Hooks (~/.guard/hooks)...[/cyan]")
        success, msgs = HookInstaller.install_global_git_hooks()
        for m in msgs:
            console.print(f"[green]• {m}[/green]")
        if success:
            console.print("[bold green]✅ Global Git Hooks active! Every Git repository on this machine is protected.[/bold green]")
        else:
            console.print("[bold red]❌ Failed to configure global Git hooks.[/bold red]")
            raise typer.Exit(code=1)
        # Set up the current repository now instead of on the first guard run
        for msg in ensure_repo_setup(Path.cwd()):
            console.print(f"[green]• {msg}[/green]")
        console.print("[dim]Other repositories are set up automatically the first time guard runs in them.[/dim]")
        return

    target_path = Path(repo).resolve() if repo else Path.cwd().resolve()
    installer = HookInstaller(target_path)

    # 1. Multi-Repo Workspace Auto-Discovery (when current folder has no .git)
    if not installer.is_git_repo():
        child_repos = installer.find_child_git_repos()
        if child_repos:
            console.print(f"\n[bold cyan]🔍 Workspace Mode:[/bold cyan] Current directory has no .git, but found [bold green]{len(child_repos)}[/bold green] child Git repositories:")
            for idx, cr in enumerate(child_repos, start=1):
                rel = cr.relative_to(target_path)
                console.print(f"  [bold yellow][{idx}][/bold yellow] ./{rel} [dim](.git)[/dim]")
            console.print("  [bold green][A][/bold green] All repositories (Install to all child repos)")
            console.print("  [bold magenta][G][/bold magenta] Global Git Hooks (Configure git config --global core.hooksPath - protects ALL repos on machine)")
            console.print("  [dim][N][/dim] None (Skip Git hooks, install workspace Agent Directives at root only)\n")
            # Respect --mode / --stealth in workspace mode
            effective_mode = "git" if stealth else (mode.lower().strip() if mode else "all")

            chosen_repos: List[Path] = []
            if effective_mode != "agent":
                if all_repos:
                    chosen_repos = child_repos
                elif select_repos:
                    parts = [p.strip() for p in select_repos.split(",")]
                    for p in parts:
                        if p.lower() in ("a", "all"):
                            chosen_repos = child_repos
                            break
                        elif p.isdigit() and 1 <= int(p) <= len(child_repos):
                            chosen_repos.append(child_repos[int(p) - 1])
                        else:
                            for cr in child_repos:
                                if cr.name == p or str(cr.relative_to(target_path)) == p:
                                    chosen_repos.append(cr)
                    if not chosen_repos:
                        console.print(f"[bold yellow]⚠️ No child repositories matched '--select-repos {select_repos}'.[/bold yellow]")
                elif sys.stdin and sys.stdin.isatty():
                    ans = typer.prompt("Select repositories to install Git hooks into [A, 1-N, G, N]", default="A").strip()
                    if ans.lower() in ("g", "global"):
                        console.print("\n[cyan]Configuring Global Git Hooks (~/.guard/hooks)...[/cyan]")
                        g_success, g_msgs = HookInstaller.install_global_git_hooks()
                        for m in g_msgs:
                            console.print(f"[green]• {m}[/green]")
                        if g_success:
                            console.print("[bold green]✅ Global Git Hooks active! Every Git repository on this machine is protected.[/bold green]")
                        chosen_repos = []
                    elif ans.lower() in ("a", "all", "y", "yes"):
                        chosen_repos = child_repos
                    elif ans.lower() in ("n", "no", "none", ""):
                        chosen_repos = []
                    else:
                        for s in ans.replace(" ", ",").split(","):
                            s = s.strip()
                            if s.isdigit() and 1 <= int(s) <= len(child_repos):
                                chosen_repos.append(child_repos[int(s) - 1])
                else:
                    chosen_repos = child_repos
            installed_count = 0
            if chosen_repos:
                console.print(f"\n[cyan]Installing Git hooks into {len(chosen_repos)} repository(s)...[/cyan]")
                res = installer.install_multi(chosen_repos, mode="git")
                for r_path, r_info in res.items():
                    r_rel = Path(r_path).relative_to(target_path)
                    if r_info["success"]:
                        installed_count += 1
                        console.print(f"  [bold green]✅ Git hooks active in: ./{r_rel}[/bold green]")
                    else:
                        console.print(f"  [red]❌ Failed in: ./{r_rel}[/red]")

            # Install workspace agent directives at root if mode is 'agent' or 'all'
            agent_installed = False
            if effective_mode in ("agent", "all"):
                console.print("\n[cyan]Installing Workspace Agent Directives (CLAUDE.md & AGENT.md) at root...[/cyan]")
                success, msgs = installer.install(mode="agent")
                for m in msgs:
                    console.print(f"[green]• {m}[/green]")
                agent_installed = success

            if installed_count > 0 and agent_installed:
                console.print("[bold green]✅ Hybrid Workspace Protection Active (Git Hooks in sub-repos + Agent Directives at root)[/bold green]")
            elif installed_count > 0:
                console.print(f"[bold green]✅ Git hooks installed into {installed_count} repository(s).[/bold green]")
            elif agent_installed:
                console.print("[bold green]✅ Agent Directives installed at workspace root.[/bold green]")
            else:
                console.print("[yellow]ℹ️ No hooks or directives were installed.[/yellow]")
            return
    # 2. Standard Single-Repo Installation
    if stealth:
        selected_mode = "git"
    elif mode:
        m = mode.lower().strip()
        if m in ("git", "stealth", "1"):
            selected_mode = "git"
        elif m in ("agent", "2"):
            selected_mode = "agent"
        elif m in ("all", "dual", "3"):
            selected_mode = "all"
        else:
            console.print(f"[bold red]❌ Invalid mode '{mode}'. Choose 'git' (or --stealth), 'agent', or 'all'.[/bold red]")
            raise typer.Exit(code=1)
    else:
        # Interactive selection if terminal is interactive
        if sys.stdin and sys.stdin.isatty():
            console.print("\n[bold cyan]🛡️  Laya-OCR-Guard Installation Setup[/bold cyan]")
            console.print("Choose how you want Guard to protect this workspace:\n")
            console.print("  [bold green][1] 👻 Stealth Mode (Git Hooks Only - Recommended for company/shared repos)[/bold green]")
            console.print("      • Installs local .git/hooks/pre-commit gate")
            console.print("      • [bold]ZERO files added to workspace root[/bold] (Never pushed to remote repo)")
            console.print("  [bold yellow][2] 🤖 Agent Directives Only (CLAUDE.md & AGENT.md)[/bold yellow]")
            console.print("      • Injects AI guidelines directly into workspace root")
            console.print("      • No Git hooks installed")
            console.print("  [bold magenta][3] 🛡️  Dual-Gate Full Protection (Git Hooks + Agent Directives)[/bold magenta]")
            console.print("      • Maximum protection: both pre-commit gate and AI agent instructions\n")

            choice_map = {
                "1": "git", "git": "git", "stealth": "git",
                "2": "agent", "agent": "agent",
                "3": "all", "all": "all", "dual": "all",
            }
            while True:
                choice = typer.prompt("Select installation mode [1-3]", default="1")
                choice_clean = choice.strip().lower()
                if choice_clean in choice_map:
                    selected_mode = choice_map[choice_clean]
                    break
                console.print("[yellow]Invalid choice. Please enter 1, 2, or 3.[/yellow]")
        else:
            selected_mode = "all"
            console.print("[dim]• Non-interactive environment: defaulting to mode 'all' (use --stealth for git-only)[/dim]")

    success, messages = installer.install(mode=selected_mode)
    for m in messages:
        console.print(f"[green]• {m}[/green]")
    if success:
        mode_desc = {
            "git": "Ghost/Stealth Mode (Git hooks only, zero workspace footprint)",
            "agent": "Agent Directives Mode (CLAUDE.md & AGENT.md)",
            "all": "Dual-Gate Full Protection Mode (Git hooks + Agent directives)",
        }.get(selected_mode, selected_mode)
        console.print(f"[bold green]✅ Guard installed successfully! ({mode_desc})[/bold green]")
    else:
        console.print("[bold red]❌ Failed to install Guard hooks.[/bold red]")


@hook_app.command("uninstall")
def hook_uninstall_cmd(
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Target repository directory"),
    mode: str = typer.Option("all", "--mode", "-m", help="Mode to uninstall: 'git', 'agent', or 'all'"),
    global_hooks: bool = typer.Option(False, "--global", "-g", help="Uninstall global Git hooks (git config --global --unset core.hooksPath)"),
):
    """
    Safely uninstall Guard hooks and restore previous user files.
    """
    if global_hooks:
        success, messages = HookInstaller.uninstall_global_git_hooks()
        for m in messages:
            console.print(f"[yellow]• {m}[/yellow]")
        console.print("[bold green]✅ Global Git hooks uninstalled.[/bold green]")
        return

    installer = HookInstaller(Path(repo) if repo else None)
    success, messages = installer.uninstall(mode=mode)
    for m in messages:
        console.print(f"[yellow]• {m}[/yellow]")
    console.print("[bold green]✅ Guard hooks uninstalled.[/bold green]")


@hook_app.command("status")
def hook_status_cmd(
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Target repository directory"),
):
    """
    Check active hook status and AI agent directives in target repository.
    """
    installer = HookInstaller(Path(repo) if repo else None)
    status = installer.get_status()

    mode_labels = {
        "all": "[bold magenta]🛡️ Dual-Gate Full Protection (Git Hooks + Agent Directives)[/bold magenta]",
        "git": "[bold green]👻 Stealth Mode (Git Hooks Only - Zero Workspace Footprint)[/bold green]",
        "agent": "[bold yellow]🤖 Agent Directives Only (CLAUDE.md & AGENT.md)[/bold yellow]",
        "none": "[dim]⚪ Inactive (No Guard hooks or directives active)[/dim]",
    }
    mode_label = mode_labels.get(status.get("mode", "none"), "[dim]⚪ Inactive[/dim]")
    console.print(f"\n[bold]Active Profile:[/bold] {mode_label}\n")

    table = Table(title=f"🪝 Guard Hook & Agent Status ({installer.repo_path.name})", show_header=True)
    table.add_column("Component / Directive", style="bold")
    table.add_column("Status", justify="center")
    table.add_column("Target / Notes")

    table.add_row("Git Repository", "✅ Yes" if status["is_git_repo"] else "❌ No", "Git VCS")
    g_stat = HookInstaller.get_global_hooks_status()
    table.add_row("Global Git Hooks", "✅ Active" if g_stat["is_active"] else "⚪ Inactive", g_stat["configured_path"] or "git config --global core.hooksPath (~/.guard/hooks)")
    table.add_row("Git prepare-commit-msg", "✅ Active" if status["prepare_commit_msg_installed"] else "⚪ Inactive", ".git/hooks/prepare-commit-msg")
    table.add_row("Local Git Exclude", "✅ Active" if status.get("git_exclude_active") else "⚪ Inactive", ".git/info/exclude (.guard/ hidden)")
    table.add_row("CLAUDE.md Directive", "✅ Active" if status["claude_md_active"] else "⚪ Inactive", "Directives for omp & Claude Code")
    table.add_row("AGENT.md Directive", "✅ Active" if status["agent_md_active"] else "⚪ Inactive", "Directives for Cursor, Windsurf, Aider")
    table.add_row("Agent Wrapper (.guard/bin)", "✅ Active" if status["agent_wrapper_installed"] else "⚪ Inactive", ".guard/bin/guard-exec")

    console.print(table)

    # If in a multi-repo workspace (no root git), report status of child git repos
    if not status["is_git_repo"]:
        child_repos = installer.find_child_git_repos()
        if child_repos:
            console.print(f"\n[cyan]🔍 Discovered {len(child_repos)} child Git repositories in workspace:[/cyan]")
            sub_table = Table(title="Child Repositories Hook Status", show_header=True)
            sub_table.add_column("Repository", style="bold")
            sub_table.add_column("pre-commit", justify="center")
            sub_table.add_column("prepare-commit-msg", justify="center")
            for cr in child_repos:
                sub_installer = HookInstaller(cr)
                sub_stat = sub_installer.get_status()
                rel = cr.relative_to(installer.repo_path)
                sub_table.add_row(
                    f"./{rel}",
                    "✅ Active" if sub_stat["pre_commit_installed"] else "⚪ Inactive",
                    "✅ Active" if sub_stat["prepare_commit_msg_installed"] else "⚪ Inactive",
                )
            console.print(sub_table)


@app.command("review")
def review_cmd(
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Target repository directory"),
    focus: str = typer.Option("all", "--focus", "-f", help="Quality pillar focus: 'all', 'security', 'memory', 'performance', 'ux', 'dead-code', 'simplicity'"),
):
    """
    Run Final Safety Review on current Git diff using the configured LLM.
    """
    target_repo = Path(repo).resolve() if repo else Path.cwd().resolve()
    inspector = GitDiffInspector(target_repo)
    raw_diff = inspector.get_diff() or ""
    if not raw_diff.strip():
        console.print("[yellow]Working tree is clean. Nothing to review.[/yellow]")
        return

    summary = inspector.parse_diff(raw_diff)
    rulebook = OCRRulebookRunner()
    violations = rulebook.scan_diff(raw_diff)

    hygiene = HygieneEngine(target_repo)
    if (focus or "").lower() in ("dead-code", "hygiene"):
        touched = [f.path for f in summary.files]
        hygiene_violations = hygiene.scan_focus_level(touched)
    else:
        hygiene_violations = hygiene.scan_diff_level(raw_diff, summary)
    violations.extend(hygiene_violations)

    simplicity = SimplicityEngine(target_repo)
    if (focus or "").lower() in ("simplicity", "yagni", "lazy"):
        touched = [f.path for f in summary.files]
        simplicity_violations = simplicity.scan_focus_level(touched)
    else:
        simplicity_violations = simplicity.scan_diff_level(raw_diff, summary)
    violations.extend(simplicity_violations)
    reviewer = LLMReviewerEngine(config=load_config(target_repo))
    dom_type = detect_domain(target_repo)

    verdict = reviewer.review(
        prompt="Manual review requested",
        domain=dom_type,
        diff_summary=summary,
        violations=violations,
        focus=focus,
    )

    badge_color = "green" if verdict.verdict == ReviewVerdict.APPROVED else "red"
    focus_label = f" | Focus: {verdict.focus_area.upper()}" if verdict.focus_area != "all" else ""
    console.print(Panel(
        f"[bold]{verdict.verdict.value}[/bold] (Mode: {verdict.review_mode}, Model: {verdict.reviewer_model}{focus_label}, Score: {verdict.score:.1f}/10)\n{verdict.summary}",
        title="🤖 LLM Code Review & Approval" if verdict.review_mode == "llm_deep" else "⚙️ Heuristic Review (LLM did not answer)",
        border_style=badge_color,
    ))


@app.command("update")
def update_cmd(
    target: str = typer.Argument("ocr", help="Update target: 'ocr' (Alibaba OCR) or 'self' (Laya-OCR-Guard)"),
    check_only: bool = typer.Option(False, "--check", "-c", help="Check for available updates without installing"),
    force: bool = typer.Option(False, "--force", "-f", help="Bypass the 3-day supply-chain quarantine cooling period"),
    quarantine_days: float = typer.Option(3.0, "--quarantine-days", "-q", help="Quarantine cooling period in days"),
):
    """
    Safely update Alibaba OCR (with 3-day supply-chain quarantine) or Guard CLI itself.
    """
    if target.lower() in ["self", "guard"]:
        if check_only:
            console.print("[cyan]Checking for Laya-OCR-Guard updates on GitHub...[/cyan]")
            check_res = check_guard_self_update(force=True)
            console.print(f"Installed Version: v{check_res.installed_version}")
            console.print(f"Latest Version:    v{check_res.latest_version or 'N/A'}")
            console.print(f"Status:            [bold]{check_res.status.value}[/bold]")
            console.print(f"Recommendation:    {check_res.recommendation}")
            return
        console.print("[cyan]Upgrading Laya-OCR-Guard CLI from GitHub...[/cyan]")
        success, msg = perform_self_upgrade()
        if success:
            console.print(f"[bold green]{msg}[/bold green]")
        else:
            console.print(f"[bold red]{msg}[/bold red]")
            raise typer.Exit(code=1)
        return

    # Default target: ocr
    console.print(f"[cyan]Checking updates for Alibaba OCR (@alibaba-group/open-code-review)...[/cyan]")
    check_res = check_ocr_update(quarantine_days=quarantine_days)

    if check_only:
        console.print(f"Installed Version: {check_res.installed_version or '(none)'}")
        console.print(f"Latest Version: v{check_res.latest_version or 'N/A'}")
        console.print(f"Security Status: [bold]{check_res.status.value}[/bold]")
        console.print(f"Recommendation: {check_res.recommendation}")
        return

    success, msg = perform_ocr_upgrade(force=force, quarantine_days=quarantine_days)
    if success:
        console.print(f"[bold green]{msg}[/bold green]")
    else:
        console.print(f"[bold yellow]{msg}[/bold yellow]")
        if not force and "QUARANTINE" in msg:
            raise typer.Exit(code=1)


@app.command("doctor")
def doctor_cmd(
    check_updates: bool = typer.Option(True, "--updates/--no-updates", help="Check npm for Alibaba OCR updates with supply-chain quarantine"),
    quarantine_days: float = typer.Option(3.0, "--quarantine-days", "-q", help="Cooling period in days (default 3 days) to protect against zero-day backdoors"),
):
    """
    Check system health and audit Alibaba OCR supply-chain security updates.
    """
    console.print("[bold cyan]🩺 LAYA-OCR-GUARD SYSTEM DOCTOR[/bold cyan]\n")
    
    # 1. Environment Table
    table = Table(title="💻 System Environment & Engines", show_header=True, header_style="bold magenta")
    table.add_column("Component", style="bold")
    table.add_column("Status", justify="center")
    table.add_column("Version / Details")

    # Guard CLI itself
    table.add_row("Laya-OCR-Guard CLI", "✅ Active", f"v{__version__} (github.com/okrath/laya-ocr-guard)")

    # Python
    py_ver = sys.version.split()[0]
    table.add_row("Python Environment", "✅ OK", f"Python {py_ver}")

    # Git
    git_bin = shutil.which("git")
    if git_bin:
        try:
            gv = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            ).stdout or ""
            table.add_row("Git VCS", "✅ OK", gv.strip())
        except Exception:
            table.add_row("Git VCS", "⚠️ Warn", "Git installed but version query failed")
    else:
        table.add_row("Git VCS", "❌ Missing", "git not found in PATH")

    # Node & npm
    node_bin = shutil.which("node")
    if node_bin:
        try:
            nv = subprocess.run(
                ["node", "-v"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            ).stdout or ""
            table.add_row("Node.js Runtime", "✅ OK", f"Node {nv.strip()}")
        except Exception:
            table.add_row("Node.js Runtime", "⚠️ Warn", "Node installed but query failed")
    else:
        table.add_row("Node.js Runtime", "❌ Missing", "node not found in PATH")

    # Alibaba OCR CLI
    ocr_bin = shutil.which("ocr")
    if ocr_bin:
        table.add_row("Alibaba OCR CLI", "✅ OK", f"Binary found at {ocr_bin}")
    else:
        table.add_row("Alibaba OCR CLI", "ℹ️ Optional", "Run 'npm install -g @alibaba-group/open-code-review'")

    # Laya Engine
    from guard.core.laya_onnx import is_model_installed, get_model_path
    cfg = load_config()
    if is_model_installed(cfg.laya.model_name):
        sz_mb = get_model_path(cfg.laya.model_name).stat().st_size / (1024 * 1024)
        table.add_row("Laya Neural Engine", "✅ Active", f"Embedded ONNX ({cfg.laya.model_name}, {sz_mb:.1f} MB) on {cfg.laya.device.upper()}")
    else:
        table.add_row("Laya Neural Engine", "⚡ Ready", f"Assets OK. Run 'guard laya download' to cache {cfg.laya.model_name}")
    console.print(table)

    # 2. Supply-Chain Security & Update Quarantine Table (Focused on Alibaba OCR)
    if check_updates:
        console.print(f"\n[bold yellow]🛡️  RELEASES & SUPPLY-CHAIN AUDIT (Alibaba OCR Quarantine: {quarantine_days:.0f} days)[/bold yellow]")
        with console.status("[cyan]Checking GitHub & npm for releases...[/cyan]"):
            guard_check = check_guard_self_update(force=True)
            ocr_check = check_ocr_update(quarantine_days=quarantine_days)

        sec_table = Table(show_header=True, header_style="bold cyan")
        sec_table.add_column("Software Component", style="bold", width=34)
        sec_table.add_column("Installed", width=12)
        sec_table.add_column("Latest Release", width=18)
        sec_table.add_column("Status", justify="center", width=22)
        sec_table.add_column("Recommendation & Action")

        # Row 1: Laya-OCR-Guard
        g_inst = f"v{guard_check.installed_version}" if guard_check.installed_version else "v" + __version__
        g_latest = f"v{guard_check.latest_version}" if guard_check.latest_version else "N/A"
        if guard_check.status == UpdateSecurityStatus.SAFE_UPDATE_AVAILABLE:
            g_badge = "[bold white on blue]⬆️ UPDATE AVAILABLE[/bold white on blue]"
        elif guard_check.status == UpdateSecurityStatus.UP_TO_DATE:
            g_badge = "[bold green]✅ UP TO DATE[/bold green]"
        else:
            g_badge = "[yellow]⚠️ CHECK FAILED[/yellow]"
        sec_table.add_row(f"{guard_check.package_name} ({guard_check.registry})", g_inst, g_latest, g_badge, guard_check.recommendation)

        # Row 2: Alibaba OCR
        inst_str = ocr_check.installed_version or "(not installed)"
        latest_str = f"v{ocr_check.latest_version}" if ocr_check.latest_version else "N/A"
        if ocr_check.age_days is not None:
            latest_str += f" ({ocr_check.age_days:.1f}d)"

        if ocr_check.status == UpdateSecurityStatus.QUARANTINE_HOLD:
            status_badge = "[bold white on red]🛡️ QUARANTINE HOLD[/bold white on red]"
        elif ocr_check.status == UpdateSecurityStatus.SAFE_UPDATE_AVAILABLE:
            status_badge = "[bold white on blue]⬆️ SAFE UPDATE[/bold white on blue]"
        elif ocr_check.status == UpdateSecurityStatus.UP_TO_DATE:
            status_badge = "[bold green]✅ UP TO DATE[/bold green]"
        elif ocr_check.status == UpdateSecurityStatus.NOT_INSTALLED:
            status_badge = "[dim]⚪ NOT INSTALLED[/dim]"
        else:
            status_badge = "[yellow]⚠️ CHECK FAILED[/yellow]"

        sec_table.add_row(f"{ocr_check.package_name} ({ocr_check.registry})", inst_str, latest_str, status_badge, ocr_check.recommendation)

        console.print(sec_table)
        console.print(
            f"[dim]💡 Safety principle: Newly published Alibaba OCR releases < {quarantine_days:.0f} days are automatically placed "
            "on QUARANTINE HOLD to protect against npm supply-chain backdoors.[/dim]\n"
        )

# ---------------------------------------------------------
# Laya Neural Engine Subcommands
# ---------------------------------------------------------

laya_app = typer.Typer(
    name="laya",
    help="🧠 Manage Laya Neural Decision Engine (Embedded ONNX runtime)",
    no_args_is_help=False,
)
app.add_typer(laya_app, name="laya")


@laya_app.callback(invoke_without_command=True)
def laya_main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        laya_status_cmd()


@laya_app.command("status")
def laya_status_cmd():
    """Show Laya ONNX Neural Engine status, model paths, and device support."""
    from guard.core.laya_onnx import (
        DEFAULT_MODEL,
        get_assets_dir,
        get_laya_model_dir,
        get_model_path,
        is_model_installed,
    )
    import onnxruntime as ort

    cfg = load_config()
    model_name = cfg.laya.model_name or DEFAULT_MODEL
    installed = is_model_installed(model_name)
    m_path = get_model_path(model_name)

    table = Table(title="🧠 Laya ONNX Neural Engine Status", show_header=True, header_style="bold magenta")
    table.add_column("Property", style="bold", width=24)
    table.add_column("Value")

    table.add_row("Configured Model", model_name)
    table.add_row("Model Cache Dir", str(get_laya_model_dir()))
    table.add_row("Model File Path", str(m_path))

    if installed:
        sz_mb = m_path.stat().st_size / (1024 * 1024)
        table.add_row("Model Status", f"✅ Active ({sz_mb:.1f} MB cached)")
    else:
        table.add_row("Model Status", "⚡ Not yet downloaded (Run 'guard laya download')")

    available_providers = ort.get_available_providers()
    cuda_avail = "CUDAExecutionProvider" in available_providers
    table.add_row("Hardware Acceleration", f"CUDA: {'✅ Available' if cuda_avail else '⚪ Inactive'}, CPU: ✅ Active")
    table.add_row("Configured Device", cfg.laya.device.upper())

    tok_file = get_assets_dir() / "tokenizer.json"
    table.add_row("Embedded Tokenizer", "✅ Ready" if tok_file.exists() else "❌ Missing")

    console.print(table)


@laya_app.command("calibrate")
def laya_calibrate_cmd(
    model: str = typer.Option("laya-int8", "--model", "-m", help="Model checkpoint to calibrate"),
):
    """
    Measure the installed Laya model on a labelled prompt set. Triage uses the neural model only
    when this passes; otherwise it keeps the keyword reflex engine.
    """
    from guard.core.laya_calibration import LABELLED_PROMPTS, PASS_ACCURACY, calibrate
    from guard.core.laya_onnx import get_model_path, is_model_installed

    if not is_model_installed(model):
        console.print(f"[yellow]Model {model} is not installed. Run `guard laya download` first.[/yellow]")
        raise typer.Exit(code=2)
    neural = LayaEngine(model_name=model, require_calibration=False)
    reflex = LayaEngine(model_name=model, prefer_neural=False)
    console.print(f"[cyan]Calibrating {model} on {len(LABELLED_PROMPTS)} labelled prompts...[/cyan]")
    record = calibrate(get_model_path(model), lambda p: neural.triage(p).domain.value)
    reflex_correct = sum(reflex.triage(p).domain.value == e for p, e in LABELLED_PROMPTS)
    verdict = "[bold green]PASSED[/bold green]" if record["passed"] else "[bold red]FAILED[/bold red]"
    console.print(
        f"{verdict}: neural domain accuracy {record['correct']}/{record['total']} "
        f"({record['accuracy']:.0%}, threshold {PASS_ACCURACY:.0%}); "
        f"reflex engine on the same set: {reflex_correct}/{record['total']}."
    )
    if not record["passed"]:
        console.print("[yellow]Triage keeps using the reflex engine until a model passes calibration.[/yellow]")


@laya_app.command("download")
def laya_download_cmd(
    model: str = typer.Option("laya-int8", "--model", "-m", help="Model checkpoint: laya-int8 (554MB)"),
    force: bool = typer.Option(False, "--force", "-f", help="Re-download model even if already cached"),
):
    """Download quantized Laya ONNX weights from HuggingFace."""
    from guard.core.laya_onnx import (
        download_laya_model,
        get_model_path,
        is_model_installed,
    )
    from rich.progress import BarColumn, DownloadColumn, Progress, TextColumn, TimeRemainingColumn, TransferSpeedColumn

    norm_key = "laya-int8" if "int8" in model.lower() or "int4" not in model.lower() else "laya-int4"
    if is_model_installed(norm_key) and not force:
        console.print(f"[bold green]✅ Model '{norm_key}' is already downloaded at: {get_model_path(norm_key)}[/bold green]")
        return

    console.print(f"[bold cyan]📥 Downloading Laya ONNX ({norm_key}) from HuggingFace...[/bold cyan]")
    progress = Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    )

    with progress:
        task_id = progress.add_task(f"Downloading {norm_key}", total=100_000_000)

        def cb(downloaded, total):
            progress.update(task_id, completed=downloaded, total=total)

        try:
            dest = download_laya_model(model_name=norm_key, progress_callback=cb)
            console.print(f"[bold green]✅ Successfully downloaded and verified Laya ONNX ({norm_key}) at:[/bold green] {dest}")
        except Exception as e:
            console.print(f"[bold red]❌ Download failed:[/bold red] {e}")
            raise typer.Exit(1)


@laya_app.command("triage")
def laya_triage_cmd(
    prompt: str = typer.Argument(..., help="Task prompt to triage"),
):
    """Run interactive Laya System 1 Triage on a prompt."""
    cfg = load_config()
    laya = LayaEngine(model_name=cfg.laya.model_name, device=cfg.laya.device)
    res = laya.triage(prompt=prompt)

    table = Table(title=f"🛡️ Laya Triage Result ({res.engine_mode})", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Value")

    table.add_row("Prompt", prompt)
    dom_val = str(res.domain.value) if hasattr(res.domain, "value") else str(res.domain)
    table.add_row("Domain", f"[bold green]{dom_val.upper()}[/bold green]")
    int_val = str(res.intent.value) if hasattr(res.intent, "value") else str(res.intent)
    table.add_row("Intent", f"[bold yellow]{int_val.upper()}[/bold yellow]")
    table.add_row("Risk Level", f"[bold]{res.risk_score_label}[/bold]")
    table.add_row("Core Breach", "🚨 YES (High Risk Area)" if res.core_breach_risk else "✅ NO (Safe Scope)")
    table.add_row("Engine Latency", f"{res.latency_ms:.2f} ms")
    table.add_row("Reasoning", res.reasoning)

    console.print(table)

def _force_utf8_console():
    """Git hooks and legacy Windows consoles default to cp1252; emoji output would crash the run."""
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream and (stream.encoding or "").lower().replace("-", "") != "utf8":
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main():
    _force_utf8_console()
    # After an upgrade, refresh the hooks and directive blocks guard wrote earlier (once per version)
    try:
        for msg in refresh_after_upgrade():
            console.print(f"[cyan]🔄 guard {__version__}: {msg}[/cyan]")
    except Exception as e:  # never block the actual command
        console.print(f"[yellow]guard refresh skipped: {e}[/yellow]")
    maybe_trigger_background_update_check()
    try:
        app()
    finally:
        notice = get_cached_update_notice()
        if notice:
            console.print(f"\n[dim yellow]{notice}[/dim yellow]")


if __name__ == "__main__":
    main()
