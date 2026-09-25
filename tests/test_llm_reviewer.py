"""
Unit tests for LLM Reviewer Engine (Final Safety Gate).
"""

import pytest

from guard.core.laya_engine import DomainType, InvariantCheck, LayaInvariantResult
from guard.core.llm_reviewer import LLMReviewerEngine, ReviewVerdict
from guard.core.ocr_engine import DiffSummary, FileDiffStat, RuleViolation
from guard.core.session import BuildCheckResult


@pytest.fixture
def reviewer():
    return LLMReviewerEngine(config=None)


def test_reviewer_approve_clean_task(reviewer):
    build_check = BuildCheckResult(
        command="npm run build",
        passed=True,
        exit_code=0,
        output="Build succeeded in 2.1s",
        duration_s=2.1,
    )
    diff = DiffSummary(
        files=[FileDiffStat(path="src/App.tsx", status="modified", insertions=10, deletions=2)],
        total_insertions=10,
        total_deletions=2,
        out_of_scope_files=[],
    )
    inv_res = LayaInvariantResult(
        all_passed=True,
        checks=[InvariantCheck(id="FE-INV-01", description="Keep loading state", passed=True, confidence=0.95)],
        ui_regression_risk=False,
        latency_ms=1.0,
    )

    verdict = reviewer.review(
        prompt="Update heading style in App.tsx",
        domain=DomainType.FRONTEND,
        diff_summary=diff,
        build_check=build_check,
        violations=[],
        invariant_result=inv_res,
        use_llm=False,
    )

    assert verdict.verdict == ReviewVerdict.APPROVED
    assert verdict.score >= 9.0
    assert len(verdict.remediation_steps) == 0


def test_reviewer_reject_on_build_failure(reviewer):
    build_check = BuildCheckResult(
        command="npm run build",
        passed=False,
        exit_code=1,
        output="TS2304: Cannot find name 'unknownVariable'",
        duration_s=1.5,
    )
    verdict = reviewer.review(
        prompt="Add feature",
        domain=DomainType.FRONTEND,
        build_check=build_check,
        use_llm=False,
    )

    assert verdict.verdict == ReviewVerdict.REVISE
    assert verdict.score < 7.5
    assert any("TS2304" in step for step in verdict.remediation_steps)


def test_reviewer_reject_on_critical_secret_and_scope_breach(reviewer):
    diff = DiffSummary(
        files=[FileDiffStat(path="src/Secret.ts", status="modified")],
        out_of_scope_files=["src/Secret.ts"],
    )
    violations = [
        RuleViolation(
            rule_id="SEC-001",
            severity="CRITICAL",
            file_path="src/Secret.ts",
            message="Hardcoded API key detected",
        )
    ]
    verdict = reviewer.review(
        prompt="Update login",
        domain=DomainType.BACKEND,
        diff_summary=diff,
        violations=violations,
        use_llm=False,
    )

    assert verdict.verdict == ReviewVerdict.REVISE
    assert verdict.score <= 5.0
    assert any("SEC-001" in step for step in verdict.remediation_steps)


def test_reviewer_llm_response_parsing(reviewer):
    raw_llm = """
SCORE: 9.2
VERDICT: APPROVED
SUMMARY: Source code is architecturally sound and clean of memory leaks.
TECHNICAL:
* No orphaned listeners
* Build verification passed
ERGONOMICS:
* Responsive UI layout preserved
REMEDIATION:
None
    """
    parsed = reviewer._parse_llm_response(raw_llm)
    assert parsed is not None
    assert parsed.score == 9.2
    assert parsed.verdict == ReviewVerdict.APPROVED
    assert len(parsed.technical_audit) == 2
    assert len(parsed.remediation_steps) == 0
def test_reviewer_reject_on_dead_code_focus(reviewer):
    diff = DiffSummary(
        files=[FileDiffStat(path="temp_draft.py", status="added", insertions=10, deletions=0)],
        raw_diff="diff --git a/temp_draft.py ...",
    )
    violations = [
        RuleViolation(
            rule_id="DEAD-001",
            severity="HIGH",
            file_path="temp_draft.py",
            message="Temporary draft file detected.",
        )
    ]
    # In normal mode without dead-code focus, score is penalized slightly
    normal_verdict = reviewer.review(
        prompt="Add feature",
        domain=DomainType.BACKEND,
        diff_summary=diff,
        violations=violations,
        use_llm=False,
        focus="all",
    )
    assert normal_verdict.score >= 7.5

    # In dead-code focus mode, DEAD-001 is a hard blocker
    focus_verdict = reviewer.review(
        prompt="Add feature",
        domain=DomainType.BACKEND,
        diff_summary=diff,
        violations=violations,
        use_llm=False,
        focus="dead-code",
    )
    assert focus_verdict.verdict == ReviewVerdict.REVISE
    assert focus_verdict.focus_area == "dead-code"
    assert any("DEAD-001" in step for step in focus_verdict.remediation_steps)
def test_reviewer_simplicity_focus_and_net_loc(reviewer):
    # 1. Net negative LOC is reported but never scored (deleting code is not evidence of quality)
    diff_reduced = DiffSummary(
        total_insertions=5,
        total_deletions=50,
        files=[FileDiffStat(path="src/legacy.py", status="modified", insertions=5, deletions=50)],
        raw_diff="diff --git a/src/legacy.py ...",
    )
    verdict_clean = reviewer.review(
        prompt="Delete deprecated code",
        domain=DomainType.BACKEND,
        diff_summary=diff_reduced,
        use_llm=False,
        focus="all",
    )
    assert verdict_clean.verdict == ReviewVerdict.APPROVED
    assert any("Net -45 LOC (informational, not scored)" in note for note in verdict_clean.technical_audit)
    assert verdict_clean.score == 10.0
    assert verdict_clean.review_mode == "heuristic"

    # 2. In simplicity focus mode, LAZY-001 is a hard blocker
    violations = [
        RuleViolation(
            rule_id="LAZY-001",
            severity="HIGH",
            file_path="package.json",
            message="Added redundant dependency is-odd",
        )
    ]
    focus_verdict = reviewer.review(
        prompt="Add helper",
        domain=DomainType.BACKEND,
        diff_summary=diff_reduced,
        violations=violations,
        use_llm=False,
        focus="simplicity",
    )
    assert focus_verdict.verdict == ReviewVerdict.REVISE
    assert focus_verdict.focus_area == "simplicity"
    assert any("LAZY-001" in step for step in focus_verdict.remediation_steps)
