"""
Markdown Reporter for Laya-OCR-Guard.
Generates standardized Markdown notes strictly matching the dual-gate protocol:
- `### 🔍 PRE-TASK IMPACT NOTE:`
- `### 🧪 POST-TASK VERIFICATION:`
"""

from __future__ import annotations

from typing import Optional

from guard.core.session import PostTaskRecord, PreTaskRecord

INVARIANT_ICONS = {"passed": "✅", "failed": "❌", "unverified": "⚪", "baseline_failed": "⚠️"}


def restart_lines(pre: PreTaskRecord) -> list:
    lines = []
    for r in pre.restarts:
        lines.append(f"  - ⚠️ Restarted with --force over session `{r.get('session_id')}` ({r.get('status')}) at {r.get('at')}")
    if pre.late_scope:
        lines.append(f"  - ⚠️ Scope added only by a restart (reported as SCOPE-004): {', '.join(f'`{s}`' for s in pre.late_scope)}")
    return lines


def gate_label(post: PostTaskRecord) -> str:
    """Name the gate by what actually ran, never claim an LLM review that did not happen."""
    return "LLM Gate" if post.review_mode == "llm_deep" else "Heuristic Gate (no LLM review)"


def generate_pre_task_markdown(pre: PreTaskRecord) -> str:
    """
    Generate standard Pre-Task Impact Note.
    """
    md = []
    md.append("### 🔍 PRE-TASK IMPACT NOTE:\n")
    md.append(f"* **Task Request:** {pre.prompt}")
    hint = f", prompt triage guessed {pre.triage_domain.upper()}" if pre.triage_domain and pre.triage_domain != pre.domain.value else ""
    md.append(f"* **Technical Domain:** {pre.domain.value.upper()} (detected from repository{hint}; Intent: {pre.intent.value})")
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
        md.append("  - ⚠️ No scope declared (name files in the prompt or pass `--scope`). Scope will NOT be audited.")

    if pre.base_ref:
        md.append(f"\n* **Base commit:** `{pre.base_ref[:12]}` (post-task diffs against it, including mid-task commits)")
    if pre.restarts or pre.late_scope:
        md.append("\n* **Session restarts:**")
        md.extend(restart_lines(pre))

    if pre.baseline_dirty:
        md.append("\n* **⚠️ Pre-existing modifications (started with --allow-dirty):**")
        for f in sorted(pre.baseline_dirty):
            md.append(f"  - `{f}`")

    # Non-Regression Strategy & Invariants
    md.append("\n* **Non-Regression Strategy & Locked Invariants:**")
    if pre.non_regression_strategy:
        md.append(f"  - *Strategy:* {pre.non_regression_strategy}")
    if pre.locked_invariants and all(inv.source == "template" for inv in pre.locked_invariants):
        md.append("  - ⚠️ Generic domain templates (no `guard.invariants.json` in repo); most cannot be verified automatically. Create the file with `guard invariants init`, then validate it with `guard invariants check`.")
    for inv in pre.locked_invariants:
        status = pre.baseline_invariant_status.get(inv.id)
        badge = f" {INVARIANT_ICONS.get(status, '')} baseline: {status}" if status else (" ⚪ manual" if not inv.checks else "")
        md.append(f"  - `[{inv.id}]` **{inv.description}** {f'({inv.rationale})' if inv.rationale else ''}{badge}")

    return "\n".join(md)


def generate_post_task_markdown(post: PostTaskRecord, pre: Optional[PreTaskRecord] = None) -> str:
    """
    Generate standard Post-Task Verification report.
    """
    md = []
    md.append("### 🧪 POST-TASK VERIFICATION:\n")
    if pre and (pre.restarts or pre.late_scope):
        md.append("* **Session restarts:**")
        md.extend(restart_lines(pre))
        md.append("")

    # Actual Impact Range
    md.append("* **Actual Impact Range:**")
    if post.files_modified:
        for f in post.files_modified:
            if f in post.preexisting_files:
                badge = "⏸️ [PRE-EXISTING, untouched]"
            elif f in post.out_of_scope_files:
                badge = "⚠️ [OUT-OF-SCOPE]"
            elif f in post.deleted_files:
                badge = "🗑️ [DELETED]"
            elif not post.scope_declared:
                badge = "❔ [scope not declared]"
            else:
                badge = "✅"
            md.append(f"  - {badge} `{f}`")
    else:
        md.append("  - No files were modified.")

    if post.diff_summary:
        net = post.diff_summary.total_insertions - post.diff_summary.total_deletions
        md.append(f"  - *Diff Statistics:* +{post.diff_summary.total_insertions} lines / -{post.diff_summary.total_deletions} lines across {len(post.diff_summary.files)} files (net {net:+d} LOC, not scored).")

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

    if post.invariant_result:
        md.append("\n* **Invariant Verification (deterministic checks):**")
        for c in post.invariant_result.checks:
            icon = INVARIANT_ICONS.get(c.status, "❔")
            md.append(f"  - {icon} `[{c.id}]` {c.description} -> *{c.status.upper()}: {c.notes}*")

    # LLM Gate Review Report
    md.append(f"\n* **Final {gate_label(post)}:**")
    icon = "🤖" if post.review_mode == "llm_deep" else "⚙️"
    md.append(f"  - {icon} **[{post.muse_verdict}]** (Score: {post.muse_score:.1f}/10)")
    if post.muse_notes:
        md.append(f"  - *Assessment:* {post.muse_notes}")
    if post.llm_error:
        md.append(f"  - ⚠️ *LLM review did not run:* {post.llm_error}")

    if post.learned_invariants or post.rejected_invariant_proposals:
        md.append("\n* **Invariants learned in this review (`guard.invariants.json`):**")
        for i in post.learned_invariants:
            md.append(f"  - ➕ `{i}` added (passes on the current code; enforced from the next `guard pre`)")
        for r in post.rejected_invariant_proposals:
            md.append(f"  - ✖️ proposal not added: {r}")

    return "\n".join(md)
