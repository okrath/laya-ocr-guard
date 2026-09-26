"""
Deterministic invariant evaluation (diff heuristics for template invariants).
"""

from guard.core.invariant_eval import evaluate_invariants


def test_evaluate_invariants_violation():
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
    eval_res = evaluate_invariants(invariants, diff, files)
    assert eval_res.all_passed is False
    assert eval_res.checks[0].passed is False
    assert "Escape" in eval_res.checks[0].description


def test_evaluate_invariants_pass():
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
    eval_res = evaluate_invariants(invariants, diff, files)
    assert eval_res.all_passed is True
    assert eval_res.checks[0].passed is True


def test_evaluate_invariants_ignore_escape_html():
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
    eval_res = evaluate_invariants(invariants, diff, files)
    assert eval_res.all_passed is True
    assert eval_res.checks[0].passed is True
