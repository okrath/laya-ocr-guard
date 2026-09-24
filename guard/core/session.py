"""
Session Manager for Laya-OCR-Guard.
Persists and transitions state between PRE-TASK and POST-TASK:
- Pre-task: intent, risk score, baseline contracts, locked invariants, target files
- Post-task: actual diff stats, out-of-scope files, build status, rule violations, Muse verdict
Stored at `<repo_root>/.guard/session.json`.
Automatically ensures `.guard/` is ignored in `.gitignore`.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from guard.core.laya_engine import DomainType, LayaInvariantResult, LayaTriageResult, RiskLevel, TaskIntent
from guard.core.ocr_engine import DiffSummary, RuleViolation


class SessionStatus(str, Enum):
    IDLE = "idle"
    AWAITING_POST = "awaiting_post"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_FIX = "needs_fix"


class DomainContract(BaseModel):
    category: str  # "UI_STATE", "API_ENDPOINT", "INFRA_PORT", "MOBILE_PERMISSION", etc.
    name: str
    description: str
    must_preserve: bool = True


class LockedInvariant(BaseModel):
    id: str  # e.g., "INV-01"
    description: str
    rationale: str = ""


class PreTaskRecord(BaseModel):
    prompt: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    domain: DomainType
    intent: TaskIntent
    risk_level: RiskLevel
    risk_score_label: str
    core_breach_risk: bool
    expected_files: List[str] = Field(default_factory=list)
    existing_contracts: List[DomainContract] = Field(default_factory=list)
    locked_invariants: List[LockedInvariant] = Field(default_factory=list)
    non_regression_strategy: str = ""


class BuildCheckResult(BaseModel):
    command: str
    passed: bool
    exit_code: int
    output: str
    duration_s: float


class PostTaskRecord(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    files_modified: List[str] = Field(default_factory=list)
    diff_summary: Optional[DiffSummary] = None
    out_of_scope_files: List[str] = Field(default_factory=list)
    build_check: Optional[BuildCheckResult] = None
    rule_violations: List[RuleViolation] = Field(default_factory=list)
    invariant_result: Optional[LayaInvariantResult] = None
    all_passed: bool = False
    muse_verdict: str = "PENDING"  # "APPROVED", "REVISE"
    muse_score: float = 0.0
    muse_notes: str = ""


class GuardSession(BaseModel):
    session_id: str
    status: SessionStatus = SessionStatus.IDLE
    repo_path: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    pre: Optional[PreTaskRecord] = None
    post: Optional[PostTaskRecord] = None


class SessionManager:
    """
    Manages `.guard/session.json` lifecycle.
    """

    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = Path(repo_path or Path.cwd()).resolve()
        self.guard_dir = self.repo_path / ".guard"
        self.session_file = self.guard_dir / "session.json"

    def ensure_gitignore(self):
        """
        Ensure `.guard/` is added to repository's `.gitignore`.
        """
        gitignore_path = self.repo_path / ".gitignore"
        entry = "\n# Laya-OCR-Guard sessions\n.guard/\n"
        try:
            if gitignore_path.exists():
                content = gitignore_path.read_text(encoding="utf-8")
                if ".guard/" not in content and ".guard" not in content:
                    gitignore_path.write_text(content.rstrip() + entry, encoding="utf-8")
            else:
                gitignore_path.write_text(entry.strip() + "\n", encoding="utf-8")
        except Exception:
            pass

    def load_session(self) -> Optional[GuardSession]:
        if not self.session_file.exists():
            return None
        try:
            with open(self.session_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return GuardSession.model_validate(data)
        except Exception:
            return None

    def start_pre_session(
        self,
        prompt: str,
        triage: LayaTriageResult,
        expected_files: List[str],
        contracts: List[DomainContract],
        invariants: List[LockedInvariant],
        non_regression_strategy: str = "",
    ) -> GuardSession:
        self.guard_dir.mkdir(parents=True, exist_ok=True)
        self.ensure_gitignore()

        session_id = f"guard-{int(time.time())}"
        pre_rec = PreTaskRecord(
            prompt=prompt,
            domain=triage.domain,
            intent=triage.intent,
            risk_level=triage.risk_level,
            risk_score_label=triage.risk_score_label,
            core_breach_risk=triage.core_breach_risk,
            expected_files=expected_files,
            existing_contracts=contracts,
            locked_invariants=invariants,
            non_regression_strategy=non_regression_strategy,
        )

        session = GuardSession(
            session_id=session_id,
            status=SessionStatus.AWAITING_POST,
            repo_path=str(self.repo_path),
            pre=pre_rec,
            post=None,
        )

        self._save(session)
        return session

    def complete_post_session(self, post_rec: PostTaskRecord) -> GuardSession:
        session = self.load_session()
        if not session:
            session = GuardSession(
                session_id=f"guard-{int(time.time())}",
                status=SessionStatus.COMPLETED if post_rec.all_passed else SessionStatus.NEEDS_FIX,
                repo_path=str(self.repo_path),
                pre=None,
                post=post_rec,
            )
        else:
            session.post = post_rec
            session.status = SessionStatus.COMPLETED if post_rec.all_passed else SessionStatus.NEEDS_FIX
            session.updated_at = datetime.now(timezone.utc).isoformat()

        self._save(session)
        return session

    def clear(self):
        if self.session_file.exists():
            try:
                self.session_file.unlink()
            except Exception:
                pass

    def _save(self, session: GuardSession):
        self.guard_dir.mkdir(parents=True, exist_ok=True)
        temp_file = self.guard_dir / f"session.json.tmp.{int(time.time()*1000)}"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(session.model_dump(mode="json"), f, indent=2)
            temp_file.replace(self.session_file)
        except Exception:
            # Fallback direct write
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump(session.model_dump(mode="json"), f, indent=2)
            if temp_file.exists():
                temp_file.unlink(missing_ok=True)
