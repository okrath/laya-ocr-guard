"""
Unit tests for Session Manager.
"""

from pathlib import Path
import pytest

from guard.core.laya_engine import DomainType, LayaTriageResult, RiskLevel, TaskIntent
from guard.core.session import (
    DomainContract,
    LockedInvariant,
    PostTaskRecord,
    SessionManager,
    SessionStatus,
)


@pytest.fixture
def temp_repo(tmp_path):
    repo = tmp_path / "target_project"
    repo.mkdir()
    return repo


def test_session_lifecycle(temp_repo):
    mgr = SessionManager(temp_repo)
    assert mgr.load_session() is None

    triage = LayaTriageResult(
        domain=DomainType.FRONTEND,
        intent=TaskIntent.FEATURE,
        risk_level=RiskLevel.MEDIUM,
        risk_score_label="2/4 (Medium)",
        core_breach_risk=False,
        latency_ms=1.2,
    )

    contracts = [
        DomainContract(category="UI_STATE", name="loading_spinner", description="Must show spinner on click"),
    ]
    invariants = [
        LockedInvariant(id="INV-01", description="Do not remove Escape key handler"),
    ]

    # 1. Start Pre-Session
    session = mgr.start_pre_session(
        prompt="Add sticky checkout button",
        triage=triage,
        expected_files=["src/Checkout.tsx"],
        contracts=contracts,
        invariants=invariants,
        non_regression_strategy="Isolate component in portal",
    )

    assert session.status == SessionStatus.AWAITING_POST
    assert session.pre is not None
    assert session.pre.expected_files == ["src/Checkout.tsx"]

    # Check gitignore
    gitignore = temp_repo / ".gitignore"
    assert gitignore.exists()
    assert ".guard/" in gitignore.read_text(encoding="utf-8")

    # 2. Complete Post-Session
    post_rec = PostTaskRecord(
        files_modified=["src/Checkout.tsx"],
        all_passed=True,
        muse_verdict="APPROVED",
        muse_score=9.5,
        muse_notes="Clean component styling and proper responsive handling.",
    )
    completed_session = mgr.complete_post_session(post_rec)

    assert completed_session.status == SessionStatus.COMPLETED
    assert completed_session.post is not None
    assert completed_session.post.muse_verdict == "APPROVED"

    # Reload from disk
    reloaded = mgr.load_session()
    assert reloaded is not None
    assert reloaded.session_id == session.session_id
    assert reloaded.status == SessionStatus.COMPLETED
    assert len(reloaded.pre.existing_contracts) == 1

    # 3. Clear session
    mgr.clear()
    assert mgr.load_session() is None
