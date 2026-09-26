"""
Unit tests for Session Manager.
"""

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

    # Guard never creates or edits a .gitignore (outside Git there is nothing to keep clean)
    assert not (temp_repo / ".gitignore").exists()

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


def test_session_parent_walk_up(tmp_path):
    workspace = tmp_path / "workspace"
    sub_repo = workspace / "services" / "api"
    sub_repo.mkdir(parents=True)

    ws_mgr = SessionManager(workspace)
    triage = LayaTriageResult(
        domain=DomainType.BACKEND,
        intent=TaskIntent.FEATURE,
        risk_level=RiskLevel.LOW,
        risk_score_label="1/4 (Low)",
        core_breach_risk=False,
        latency_ms=0.5,
    )
    ws_session = ws_mgr.start_pre_session(
        prompt="Workspace task across sub-repos",
        triage=triage,
        expected_files=["services/api/main.py"],
        contracts=[],
        invariants=[],
    )

    # Sub-repo SessionManager should discover the parent workspace session via walk-up
    sub_mgr = SessionManager(sub_repo)
    discovered = sub_mgr.load_session()
    assert discovered is not None
    assert discovered.session_id == ws_session.session_id
    assert discovered.pre.prompt == "Workspace task across sub-repos"

    ws_mgr.clear()
