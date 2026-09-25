"""
Unit tests for Muse / LLM Reviewer Engine.
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
