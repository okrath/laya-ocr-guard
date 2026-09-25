"""
Terminal Rich UI Reporter for Laya-OCR-Guard.
Renders visually striking CLI outputs with colorized badges, tables, and panels.
"""

from __future__ import annotations

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from guard.core.session import PostTaskRecord, PreTaskRecord

console = Console()


def render_pre_task_terminal(pre: PreTaskRecord):
    # Header panel
    header_text = Text()
    header_text.append("🛡️ LAYA-OCR-GUARD: PRE-TASK IMPACT NOTE\n", style="bold cyan")
    header_text.append(f"Prompt: ", style="bold white")
    header_text.append(f"{pre.prompt}\n", style="italic yellow")
    header_text.append(f"Domain: ", style="bold white")
    header_text.append(f"{pre.domain.value.upper()}  ", style="bold green")
    header_text.append(f"Intent: ", style="bold white")
    header_text.append(f"{pre.intent.value.upper()}  ", style="cyan")
    header_text.append(f"Risk: ", style="bold white")
    risk_style = "bold red" if pre.risk_level >= 3 else "bold green"
    header_text.append(f"{pre.risk_score_label} ", style=risk_style)
    if pre.core_breach_risk:
        header_text.append("[CORE BREACH!]", style="bold white on red")

    console.print(Panel(header_text, border_style="cyan"))

    # Contracts Table
    if pre.existing_contracts:
        table = Table(title="📌 Existing Domain Contracts (Baseline)", show_header=True, header_style="bold magenta")
        table.add_column("Category", style="cyan", width=18)
        table.add_column("Contract Name", style="bold white", width=28)
        table.add_column("Constraint Description", style="dim")

        for c in pre.existing_contracts:
            table.add_row(c.category, c.name, c.description)
        console.print(table)

    # Invariants Panel
    if pre.locked_invariants:
        inv_table = Table(title="🔒 Locked Invariants (Must NOT be broken)", show_header=True, header_style="bold yellow")
        inv_table.add_column("ID", style="bold yellow", width=12)
        inv_table.add_column("Invariant Rule", style="bold white")
        inv_table.add_column("Rationale", style="dim")

        for inv in pre.locked_invariants:
            inv_table.add_row(inv.id, inv.description, inv.rationale)
        console.print(inv_table)

    # Target Files
    if pre.expected_files:
        files_str = "\n".join(f"  • [green]{f}[/green]" for f in pre.expected_files)
        console.print(Panel(files_str, title="📁 Expected Impact Range (Target Files)", border_style="green"))


def render_post_task_terminal(post: PostTaskRecord, pre: Optional[PreTaskRecord] = None):
    # Overall Verdict Badge (from the configured LLM / Gatekeeper)
    is_approved = post.muse_verdict == "APPROVED"
    badge_style = "bold white on green" if is_approved else "bold white on red"
    badge_title = "✅ FINAL LLM GATE: APPROVED" if is_approved else "❌ FINAL LLM GATE: REVISE REQUIRED"

    summary_text = Text()
    summary_text.append(f"{badge_title}\n\n", style=badge_style)
    summary_text.append(f"LLM Quality Score: ", style="bold")
    summary_text.append(f"{post.muse_score:.1f} / 10.0\n", style="bold yellow" if is_approved else "bold red")
    if post.muse_notes:
        summary_text.append(f"LLM Assessment: {post.muse_notes}\n", style="italic")

    console.print(Panel(summary_text, border_style="green" if is_approved else "red"))

    # Diff & Blast Radius Table
    if post.diff_summary:
        diff_table = Table(title="📊 Actual Impact Range & Blast Radius (OCR Inspector)", show_header=True)
        diff_table.add_column("File Path", style="bold")
        diff_table.add_column("Status", width=10)
        diff_table.add_column("+ Add", style="green", justify="right", width=8)
        diff_table.add_column("- Del", style="red", justify="right", width=8)
        diff_table.add_column("Scope Audit", justify="center")

        for f in post.diff_summary.files:
            is_oos = f.path in post.out_of_scope_files
            scope_badge = Text("⚠️ OUT OF SCOPE", style="bold red") if is_oos else Text("✅ In Scope", style="green")
            diff_table.add_row(f.path, f.status, str(f.insertions), str(f.deletions), scope_badge)
        console.print(diff_table)

    # Build Check status
    if post.build_check:
        b_color = "green" if post.build_check.passed else "red"
        b_icon = "✅" if post.build_check.passed else "❌"
        b_text = f"{b_icon} Command: [bold]{post.build_check.command}[/bold] | Exit Code: {post.build_check.exit_code} | Duration: {post.build_check.duration_s:.1f}s"
        if not post.build_check.passed:
            b_text += f"\n[dim]{post.build_check.output[:300]}[/dim]"
        console.print(Panel(b_text, title="⚙️ Project Health & Build Verification", border_style=b_color))

    # Invariants Verification
    if post.invariant_result:
        inv_table = Table(title="🧪 Invariant Compliance Verification (Laya System 1)", show_header=True)
        inv_table.add_column("ID", width=12)
        inv_table.add_column("Description")
        inv_table.add_column("Verdict", justify="center", width=12)
        inv_table.add_column("Notes", style="dim")

        for c in post.invariant_result.checks:
            v_text = Text("✅ PASSED", style="bold green") if c.passed else Text("❌ VIOLATED", style="bold red")
            inv_table.add_row(c.id, c.description, v_text, c.notes)
        console.print(inv_table)

    # Rule Violations (OCR & Code Hygiene)
    if post.rule_violations:
        ocr_viols = [v for v in post.rule_violations if not v.rule_id.startswith("DEAD-")]
        dead_viols = [v for v in post.rule_violations if v.rule_id.startswith("DEAD-")]

        if ocr_viols:
            viol_table = Table(title="🚨 Alibaba OCR Rulebook Violations", show_header=True, header_style="bold red")
            viol_table.add_column("Rule ID", style="bold red", width=10)
            viol_table.add_column("Severity", width=10)
            viol_table.add_column("Location")
            viol_table.add_column("Violation Message")

            for v in ocr_viols:
                loc = f"{v.file_path}:{v.line_number}" if v.line_number else v.file_path
                viol_table.add_row(v.rule_id, v.severity, loc, v.message)
            console.print(viol_table)

        if dead_viols:
            hygiene_table = Table(title="🧹 Code & Asset Hygiene Audit (Dead Code Gate)", show_header=True, header_style="bold yellow")
            hygiene_table.add_column("Rule ID", style="bold yellow", width=10)
            hygiene_table.add_column("Severity", width=10)
            hygiene_table.add_column("Location")
            hygiene_table.add_column("Hygiene Issue & Recommendation")

            for v in dead_viols:
                loc = f"{v.file_path}:{v.line_number}" if v.line_number else v.file_path
                hygiene_table.add_row(v.rule_id, v.severity, loc, v.message)
            console.print(hygiene_table)
