"""
Markdown Reporter for Laya-OCR-Guard.
Generates standardized Markdown notes strictly matching the dual-gate protocol:
- `### 🔍 PRE-TASK IMPACT NOTE:`
- `### 🧪 POST-TASK VERIFICATION:`
"""

from __future__ import annotations

from typing import Optional

from guard.core.session import PostTaskRecord, PreTaskRecord


def generate_pre_task_markdown(pre: PreTaskRecord) -> str:
    """
    Generate standard Pre-Task Impact Note.
    """
    md = []
    md.append("### 🔍 PRE-TASK IMPACT NOTE:\n")
    md.append(f"* **Yêu cầu thực hiện:** {pre.prompt}")
    md.append(f"* **Technical Domain:** {pre.domain.value.upper()} (Tác vụ: {pre.intent.value})")
    md.append(f"* **Đánh giá rủi ro (Laya System 1):** {pre.risk_score_label} {'⚠️ [CORE BREACH DETECTED]' if pre.core_breach_risk else '✅ [Standard Scope]'}")
    
    # Baseline
    md.append("\n* **Hiện trạng chức năng (Current Baseline):**")
    if pre.existing_contracts:
        for c in pre.existing_contracts:
            md.append(f"  - `[{c.category}]` **{c.name}**: {c.description}")
    else:
        md.append("  - Đang chuẩn bị phân vùng chức năng mới hoặc chưa phát hiện contract xung đột.")

    # Expected Impact Range
    md.append("\n* **Dự kiến phạm vi tác động (Expected Impact Range):**")
    if pre.expected_files:
        for f in pre.expected_files:
            md.append(f"  - `{f}`")
    else:
        md.append("  - Không giới hạn file cục bộ (Tác vụ toàn cục).")

    # Non-Regression Strategy & Invariants
    md.append("\n* **Phương án giữ an toàn & Bất biến kỹ thuật (Locked Invariants):**")
    if pre.non_regression_strategy:
        md.append(f"  - *Chiến lược:* {pre.non_regression_strategy}")
    for inv in pre.locked_invariants:
        md.append(f"  - `[{inv.id}]` **{inv.description}** {f'({inv.rationale})' if inv.rationale else ''}")

    return "\n".join(md)


def generate_post_task_markdown(post: PostTaskRecord, pre: Optional[PreTaskRecord] = None) -> str:
    """
    Generate standard Post-Task Verification report.
    """
    md = []
    md.append("### 🧪 POST-TASK VERIFICATION:\n")

    # Actual Impact Range
    md.append("* **Phạm vi tác động thực tế (Actual Impact Range):**")
    if post.files_modified:
        for f in post.files_modified:
            is_oos = f in post.out_of_scope_files
            badge = "⚠️ [OUT-OF-SCOPE]" if is_oos else "✅"
            md.append(f"  - {badge} `{f}`")
    else:
        md.append("  - Không có file nào bị thay đổi.")

    if post.diff_summary:
        md.append(f"  - *Chi tiết Diff:* +{post.diff_summary.total_insertions} dòng / -{post.diff_summary.total_deletions} dòng across {len(post.diff_summary.files)} files.")

    # Build Check
    md.append("\n* **Kiểm tra biên dịch & Project Health Check:**")
    if post.build_check:
        icon = "✅" if post.build_check.passed else "❌"
        md.append(f"  - {icon} Lệnh: `{post.build_check.command}` (Exit Code: {post.build_check.exit_code}, Thời gian: {post.build_check.duration_s:.1f}s)")
        if not post.build_check.passed:
            md.append(f"    ```\n    {post.build_check.output[:400]}\n    ```")
    else:
        md.append("  - ℹ️ Không phát hiện lệnh build tự động.")

    # Rule Violations
    if post.rule_violations:
        md.append("\n* **Alibaba OCR Rulebook Alerts:**")
        for v in post.rule_violations:
            md.append(f"  - `[{v.severity}]` **{v.rule_id}**: {v.message} tại `{v.file_path}`")

    # Invariants Compliance
    if post.invariant_result:
        md.append("\n* **Kết quả kiểm thử Invariants (Laya Scoring):**")
        for c in post.invariant_result.checks:
            icon = "✅" if c.passed else "❌"
            md.append(f"  - {icon} `[{c.id}]` {c.description} -> *{c.notes}*")

    # LLM Gate Review Report
    md.append("\n* **Chốt chặn cuối: Phê duyệt từ LLM (Final LLM Gate Review):**")
    badge_verdict = f"🤖 **[{post.muse_verdict}]** (Điểm chất lượng: {post.muse_score:.1f}/10)"
    md.append(f"  - {badge_verdict}")
    if post.muse_notes:
        md.append(f"  - *Nhận xét từ LLM:* {post.muse_notes}")

    return "\n".join(md)
