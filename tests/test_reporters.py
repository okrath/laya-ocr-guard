"""
Unit tests for Markdown and Terminal Reporters.
"""

from guard.core.laya_engine import DomainType, InvariantCheck, LayaInvariantResult, RiskLevel, TaskIntent
from guard.core.ocr_engine import DiffSummary, FileDiffStat, RuleViolation
from guard.core.session import BuildCheckResult, DomainContract, LockedInvariant, PostTaskRecord, PreTaskRecord
from guard.reporters.markdown import generate_post_task_markdown, generate_pre_task_markdown
from guard.reporters.terminal import render_post_task_terminal, render_pre_task_terminal


def test_markdown_pre_task_generation():
    pre = PreTaskRecord(
        prompt="Thêm nút floating action button",
        domain=DomainType.FRONTEND,
        intent=TaskIntent.FEATURE,
        risk_level=RiskLevel.MEDIUM,
        risk_score_label="2/4 (Medium)",
        core_breach_risk=False,
        expected_files=["src/components/FAB.tsx"],
        existing_contracts=[
            DomainContract(category="UI_STATE", name="fab_animation", description="Must smooth pop"),
        ],
        locked_invariants=[
            LockedInvariant(id="FE-INV-01", description="Do not hide on scroll"),
        ],
        non_regression_strategy="Pure component",
    )

    md = generate_pre_task_markdown(pre)
    assert "### 🔍 PRE-TASK IMPACT NOTE:" in md
    assert "FRONTEND" in md
    assert "fab_animation" in md
    assert "FE-INV-01" in md
    assert "src/components/FAB.tsx" in md


def test_markdown_post_task_generation():
    post = PostTaskRecord(
        files_modified=["src/components/FAB.tsx", "src/BadFile.ts"],
        out_of_scope_files=["src/BadFile.ts"],
        diff_summary=DiffSummary(
            files=[
                FileDiffStat(path="src/components/FAB.tsx", status="modified", insertions=15, deletions=2),
                FileDiffStat(path="src/BadFile.ts", status="modified", insertions=5, deletions=0),
            ],
            total_insertions=20,
            total_deletions=2,
            out_of_scope_files=["src/BadFile.ts"],
        ),
        build_check=BuildCheckResult(
            command="npm run build",
            passed=True,
            exit_code=0,
            output="Done",
            duration_s=1.2,
        ),
        rule_violations=[
            RuleViolation(rule_id="SEC-001", severity="CRITICAL", file_path="src/BadFile.ts", message="Key leak"),
        ],
        invariant_result=LayaInvariantResult(
            all_passed=True,
            checks=[InvariantCheck(id="FE-INV-01", description="Visible", passed=True, confidence=0.9)],
            ui_regression_risk=False,
            latency_ms=0.5,
        ),
        all_passed=False,
        muse_verdict="REVISE",
        muse_score=4.5,
        muse_notes="Detected out of scope file and secret leak.",
    )

    md = generate_post_task_markdown(post)
    assert "### 🧪 POST-TASK VERIFICATION:" in md
    assert "[OUT-OF-SCOPE]" in md
    assert "src/BadFile.ts" in md
    assert "SEC-001" in md
    assert "REVISE" in md


def test_terminal_render_smoke(capsys):
    pre = PreTaskRecord(
        prompt="Test terminal",
        domain=DomainType.BACKEND,
        intent=TaskIntent.BUGFIX,
        risk_level=RiskLevel.LOW,
        risk_score_label="1/4 (Low)",
        core_breach_risk=False,
    )
    # Smoke test: ensure no exception thrown during render
    render_pre_task_terminal(pre)

    post = PostTaskRecord(
        files_modified=["test.py"],
        all_passed=True,
        muse_verdict="APPROVED",
        muse_score=9.8,
    )
    render_post_task_terminal(post, pre)
def test_hygiene_violations_reporter():
    post = PostTaskRecord(
        files_modified=["temp_helper.py"],
        rule_violations=[
            RuleViolation(rule_id="DEAD-001", severity="HIGH", file_path="temp_helper.py", message="Temporary draft file"),
            RuleViolation(rule_id="DEAD-002", severity="MEDIUM", file_path="temp_helper.py", line_number=5, message="Commented-out code"),
        ],
        all_passed=False,
        muse_verdict="REVISE",
        muse_score=5.0,
    )
    md = generate_post_task_markdown(post)
    assert "Code & Asset Hygiene Alerts (Dead Code Gate):" in md
    assert "DEAD-001" in md
    assert "DEAD-002" in md

    # Ensure terminal render handles hygiene table without errors
    render_post_task_terminal(post)
def test_simplicity_violations_and_net_loc_reporter():
    post = PostTaskRecord(
        files_modified=["package.json"],
        diff_summary=DiffSummary(
            total_insertions=10,
            total_deletions=45,
            files=[FileDiffStat(path="package.json", status="modified", insertions=10, deletions=45)],
        ),
        rule_violations=[
            RuleViolation(rule_id="LAZY-001", severity="HIGH", file_path="package.json", message="Added redundant package is-odd"),
        ],
        all_passed=False,
        muse_verdict="REVISE",
        muse_score=5.5,
    )
    md = generate_post_task_markdown(post)
    assert "Engineering Frugality & Simplicity Alerts (KISS / YAGNI):" in md
    assert "LAZY-001" in md
    assert "Code Debt Reduction Bonus" in md
    assert "-35 LOC" in md

    # Ensure terminal render runs cleanly
    render_post_task_terminal(post)
