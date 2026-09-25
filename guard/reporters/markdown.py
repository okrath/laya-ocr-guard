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
    md.append(f"* **Task Request:** {pre.prompt}")
    md.append(f"* **Technical Domain:** {pre.domain.value.upper()} (Intent: {pre.intent.value})")
    md.append(f"* **Risk Assessment (Laya System 1):** {pre.risk_score_label} {'⚠️ [CORE BREACH DETECTED]' if pre.core_breach_risk else '✅ [Standard Scope]'}")
    
    # Baseline
    md.append("\n* **Current Baseline Contracts:**")
    if pre.existing_contracts:
        for c in pre.existing_contracts:
            md.append(f"  - `[{c.category}]` **{c.name}**: {c.description}")
    else:
        md.append("  - Initializing scoped module or no conflicting baseline contracts detected.")

    # Expected Impact Range
    md.append("\n* **Expected Impact Range (Target Files):**")
    if pre.expected_files:
        for f in pre.expected_files:
            md.append(f"  - `{f}`")
    else:
        md.append("  - No local file boundaries specified (Global scope).")

    # Non-Regression Strategy & Invariants
    md.append("\n* **Non-Regression Strategy & Locked Invariants:**")
    if pre.non_regression_strategy:
        md.append(f"  - *Strategy:* {pre.non_regression_strategy}")
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
    md.append("* **Actual Impact Range:**")
    if post.files_modified:
        for f in post.files_modified:
            is_oos = f in post.out_of_scope_files
            badge = "⚠️ [OUT-OF-SCOPE]" if is_oos else "✅"
            md.append(f"  - {badge} `{f}`")
    else:
        md.append("  - No files were modified.")

    if post.diff_summary:
        md.append(f"  - *Diff Statistics:* +{post.diff_summary.total_insertions} lines / -{post.diff_summary.total_deletions} lines across {len(post.diff_summary.files)} files.")

    # Build Check
    md.append("\n* **Build & Project Health Check:**")
    if post.build_check:
        icon = "✅" if post.build_check.passed else "❌"
        md.append(f"  - {icon} Command: `{post.build_check.command}` (Exit Code: {post.build_check.exit_code}, Duration: {post.build_check.duration_s:.1f}s)")
        if not post.build_check.passed:
            md.append(f"    ```\n    {post.build_check.output[:400]}\n    ```")
    else:
        md.append("  - ℹ️ No automated build command detected.")

    # Rule Violations (OCR, Hygiene & Simplicity)
    if post.rule_violations:
        ocr_viols = [v for v in post.rule_violations if not v.rule_id.startswith("DEAD-") and not v.rule_id.startswith("LAZY-")]
        dead_viols = [v for v in post.rule_violations if v.rule_id.startswith("DEAD-")]
        lazy_viols = [v for v in post.rule_violations if v.rule_id.startswith("LAZY-")]

        if ocr_viols:
            md.append("\n* **Alibaba OCR Rulebook Alerts:**")
            for v in ocr_viols:
                md.append(f"  - `[{v.severity}]` **{v.rule_id}**: {v.message} at `{v.file_path}`")

        if dead_viols:
            md.append("\n* **Code & Asset Hygiene Alerts (Dead Code Gate):**")
            for v in dead_viols:
                md.append(f"  - `[{v.severity}]` **{v.rule_id}**: {v.message} at `{v.file_path}`")

        if lazy_viols:
            md.append("\n* **Engineering Frugality & Simplicity Alerts (KISS / YAGNI):**")
            for v in lazy_viols:
                md.append(f"  - `[{v.severity}]` **{v.rule_id}**: {v.message} at `{v.file_path}`")

    if post.diff_summary and post.diff_summary.total_deletions > post.diff_summary.total_insertions and post.diff_summary.total_deletions >= 10:
        net = post.diff_summary.total_insertions - post.diff_summary.total_deletions
        md.append(f"\n* **⭐ Code Debt Reduction Bonus:** Net {net:+d} LOC (Deleted more code than added).")
    if post.invariant_result:
        md.append("\n* **Invariant Verification (Laya Scoring):**")
        for c in post.invariant_result.checks:
            icon = "✅" if c.passed else "❌"
            md.append(f"  - {icon} `[{c.id}]` {c.description} -> *{c.notes}*")

    # LLM Gate Review Report
    md.append("\n* **Final LLM Gate Review & Approval:**")
    badge_verdict = f"🤖 **[{post.muse_verdict}]** (Quality Score: {post.muse_score:.1f}/10)"
    md.append(f"  - {badge_verdict}")
    if post.muse_notes:
        md.append(f"  - *LLM Assessment:* {post.muse_notes}")

    return "\n".join(md)
