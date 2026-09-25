"""
Unit tests for Laya Fast-Reflex Engine.
"""

import pytest
from guard.core.laya_engine import (
    DomainType,
    LayaEngine,
    RiskLevel,
    TaskIntent,
)


@pytest.fixture
def engine():
    return LayaEngine(prefer_neural=False)


def test_triage_frontend(engine):
    res = engine.triage("Chuyển nút checkout sang sticky ở bottom mobile, chỉnh CSS và responsive modal")
    assert res.domain == DomainType.FRONTEND
    assert res.latency_ms < 30.0  # Must be fast reflex (<30ms)
    assert res.risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.LOW]


def test_triage_backend(engine):
    res = engine.triage("Thêm API endpoint /api/v1/orders và câu truy vấn database Postgres")
    assert res.domain == DomainType.BACKEND
    assert res.intent == TaskIntent.FEATURE


def test_triage_infra(engine):
    res = engine.triage("Cập nhật file Dockerfile và Kubernetes Helm chart ingress")
    assert res.domain == DomainType.INFRA
    assert res.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]


def test_triage_mobile(engine):
    res = engine.triage("Thêm màn hình Flutter widget và xin cấp quyền camera trên Android/iOS")
    assert res.domain == DomainType.MOBILE


def test_triage_critical_core_breach(engine):
    res = engine.triage("Sửa lại bảng users trong database migration và đổi cơ chế JWT auth token")
    assert res.core_breach_risk is True
    assert res.risk_level == RiskLevel.CRITICAL


def test_evaluate_invariants_violation(engine):
    invariants = [
        {"id": "INV-01", "description": "Không được bỏ phím Escape để đóng modal"},
        {"id": "INV-02", "description": "Không được hardcode secret token trong code"},
    ]
    # Diff that removes keydown / escape
    diff = """
--- a/src/Modal.tsx
+++ b/src/Modal.tsx
@@ -10,3 +10,1 @@
- window.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });
+ console.log("modal opened");
    """
    files = ["src/Modal.tsx"]
    eval_res = engine.evaluate_invariants(invariants, diff, files)
    assert eval_res.all_passed is False
    assert eval_res.checks[0].passed is False
    assert "Escape" in eval_res.checks[0].description


def test_evaluate_invariants_pass(engine):
    invariants = [
        {"id": "INV-01", "description": "Nút thanh toán phải disabled khi giỏ hàng trống"},
    ]
    diff = """
--- a/src/Button.tsx
+++ b/src/Button.tsx
@@ -10,3 +10,3 @@
- const color = "blue";
+ const color = "indigo";
    """
    files = ["src/Button.tsx"]
    eval_res = engine.evaluate_invariants(invariants, diff, files)
    assert eval_res.all_passed is True
    assert eval_res.checks[0].passed is True


def test_evaluate_invariants_ignore_escape_html(engine):
    invariants = [
        {"id": "INV-01", "description": "Không được bỏ phím Escape để đóng modal"},
    ]
    # Diff that removes escapeHtml helper, NOT keyboard escape handler
    diff = """
--- a/src/utils.ts
+++ b/src/utils.ts
@@ -5,3 +5,1 @@
- const safe = escapeHtml(userInput);
+ const safe = sanitize(userInput);
    """
    files = ["src/utils.ts"]
    eval_res = engine.evaluate_invariants(invariants, diff, files)
    assert eval_res.all_passed is True
    assert eval_res.checks[0].passed is True
