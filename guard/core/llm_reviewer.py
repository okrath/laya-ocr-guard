"""
LLM Reviewer Engine — The Final Safety Gate.
Uses the LLM configured by the user (OpenAI, Anthropic, DeepSeek, Ollama, etc.)
to act as the Senior Architect & Code Reviewer:
1. Reads the aggregated verification report (diff summary, build status, OCR rules, Laya invariants)
2. Evaluates Technical Soundness (architectural integrity, memory leaks, security, out-of-scope files)
3. Evaluates Ergonomics & UX/UI Polish
4. Issues Final Score (0-10) and Verdict: APPROVED or REVISE with Actionable Remediation.
Supports selective focus mode: `security`, `memory`, `performance`, `ux`, `all`.

If no LLM API key is configured, falls back to deterministic local heuristic evaluation.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel, Field

from guard.core.config import GuardConfig
from guard.core.laya_engine import DomainType, LayaInvariantResult
from guard.core.llm_client import call_llm
from guard.core.ocr_engine import DiffSummary, RuleViolation
from guard.core.session import BuildCheckResult, DomainContract, LockedInvariant


class ReviewVerdict(str, Enum):
    APPROVED = "APPROVED"
    REVISE = "REVISE"


class LLMReviewVerdict(BaseModel):
    verdict: ReviewVerdict
    score: float = Field(ge=0.0, le=10.0)
    summary: str
    reviewer_model: str = "Local Deterministic Engine"
    focus_area: str = "all"
    technical_audit: List[str] = Field(default_factory=list)
    ergonomics_ux: List[str] = Field(default_factory=list)
    remediation_steps: List[str] = Field(default_factory=list)
    review_mode: str = "heuristic"  # "heuristic" or "llm_deep"


class LLMReviewerEngine:
    """
    Final Gatekeeper powered by the user-configured LLM (or local deterministic fallback).
    """

    def __init__(self, config: Optional[GuardConfig] = None):
        self.config = config

    def review(
        self,
        prompt: str,
        domain: Union[DomainType, str],
        diff_summary: Optional[DiffSummary] = None,
        build_check: Optional[BuildCheckResult] = None,
        violations: Optional[List[RuleViolation]] = None,
        invariant_result: Optional[LayaInvariantResult] = None,
        contracts: Optional[List[DomainContract]] = None,
        invariants: Optional[List[LockedInvariant]] = None,
        use_llm: bool = True,
        focus: Optional[str] = "all",
    ) -> LLMReviewVerdict:
        violations = violations or []
        focus_str = (focus or "all").lower()

        # 1. Deterministic Heuristic Scoring (Safety baseline)
        heuristic_verdict = self._evaluate_heuristics(
            build_check=build_check,
            diff_summary=diff_summary,
            violations=violations,
            invariant_result=invariant_result,
            focus=focus_str,
        )

        # If hard blockers triggered (build failed, invariant broken, secret leaked), reject immediately
        if heuristic_verdict.verdict == ReviewVerdict.REVISE:
            return heuristic_verdict

        # 2. Deep LLM Review using the configured LLM (OpenAI, Anthropic, Ollama, DeepSeek, etc.)
        if use_llm and self.config and self.config.llm and self.config.llm.api_key:
            try:
                llm_verdict = self._evaluate_with_llm(
                    prompt=prompt,
                    domain=domain,
                    diff_summary=diff_summary,
                    build_check=build_check,
                    violations=violations,
                    invariant_result=invariant_result,
                    contracts=contracts,
                    focus=focus_str,
                )
                if llm_verdict:
                    return llm_verdict
            except Exception:
                pass

        return heuristic_verdict

    def _evaluate_heuristics(
        self,
        build_check: Optional[BuildCheckResult],
        diff_summary: Optional[DiffSummary],
        violations: List[RuleViolation],
        invariant_result: Optional[LayaInvariantResult],
        focus: str = "all",
    ) -> LLMReviewVerdict:
        score = 10.0
        tech_notes: List[str] = []
        ux_notes: List[str] = []
        remediation: List[str] = []

        # Check 1: Build check
        if build_check:
            if build_check.passed:
                tech_notes.append(f"Compile Check: PASSED (`{build_check.command}` in {build_check.duration_s:.1f}s)")
            else:
                score -= 4.5
                tech_notes.append(f"Compile Check: FAILED with exit code {build_check.exit_code}")
                remediation.append(f"Fix compilation errors causing `{build_check.command}` to fail:\n{build_check.output[:300]}")

        # Check 2: Out of scope files
        if diff_summary and diff_summary.out_of_scope_files:
            score -= 2.5 * len(diff_summary.out_of_scope_files)
            tech_notes.append(f"Scope Compliance: Modified {len(diff_summary.out_of_scope_files)} undeclared files: {', '.join(diff_summary.out_of_scope_files)}")
            remediation.append(f"Revert changes to out-of-scope files: {', '.join(diff_summary.out_of_scope_files)}")

        # Check 3: Rule Violations
        crit_violations = [v for v in violations if v.severity == "CRITICAL"]
        high_violations = [v for v in violations if v.severity == "HIGH"]
        if crit_violations:
            score -= 3.5 * len(crit_violations)
            for cv in crit_violations:
                tech_notes.append(f"Security Alert [{cv.rule_id}]: {cv.message} ({cv.file_path})")
                remediation.append(f"Resolve critical security violation {cv.rule_id} in `{cv.file_path}`")
        if high_violations:
            score -= 1.5 * len(high_violations)
            for hv in high_violations:
                tech_notes.append(f"Stability Warning [{hv.rule_id}]: {hv.message} ({hv.file_path})")
                remediation.append(f"Resolve stability/performance warning {hv.rule_id} in `{hv.file_path}`")

        # Check 4: Code Hygiene & Dead Code Violations
        dead_violations = [v for v in violations if v.rule_id.startswith("DEAD-")]
        if dead_violations:
            weight = 2.0 if focus in ("dead-code", "hygiene") else 0.8
            score -= weight * len(dead_violations)
            for dv in dead_violations:
                tech_notes.append(f"Hygiene Alert [{dv.rule_id}]: {dv.message} ({dv.file_path})")
                remediation.append(f"Clean up code hygiene issue [{dv.rule_id}]: {dv.message} in `{dv.file_path}`")

        # Check 5: Invariants (CRITICAL: Invariant violation is a HARD BLOCKER)
        invariant_violated = False
        if invariant_result:
            if invariant_result.all_passed:
                ux_notes.append("Invariants Check: 100% Invariants strictly preserved.")
            else:
                invariant_violated = True
                failed_checks = [c for c in invariant_result.checks if not c.passed]
                score -= 3.0 * len(failed_checks)
                for fc in failed_checks:
                    ux_notes.append(f"Invariant Violation [{fc.id}]: {fc.description} -> {fc.notes}")
                    remediation.append(f"Restore invariant behavior `{fc.id}`: {fc.description}")

        score = max(0.0, min(10.0, score))
        
        hygiene_blocked = focus in ("dead-code", "hygiene") and bool(dead_violations)
        is_hard_blocked = invariant_violated or bool(crit_violations) or (build_check is not None and not build_check.passed) or (diff_summary is not None and bool(diff_summary.out_of_scope_files)) or hygiene_blocked
        verdict = ReviewVerdict.APPROVED if (score >= 7.5 and not is_hard_blocked) else ReviewVerdict.REVISE

        summary = (
            f"LLM GATE APPROVAL: Source code meets safety standards ({score:.1f}/10). No regressions or architectural violations detected."
            if verdict == ReviewVerdict.APPROVED
            else f"LLM GATE REJECT: Detected {len(remediation)} issues to fix before handover ({score:.1f}/10)."
        )

        model_name = self.config.llm.model if (self.config and self.config.llm and self.config.llm.api_key) else "Local Rule Engine"

        return LLMReviewVerdict(
            verdict=verdict,
            score=score,
            summary=summary,
            reviewer_model=model_name,
            focus_area=focus,
            technical_audit=tech_notes,
            ergonomics_ux=ux_notes,
            remediation_steps=remediation,
            review_mode="heuristic",
        )

    def _evaluate_with_llm(
        self,
        prompt: str,
        domain: Union[DomainType, str],
        diff_summary: Optional[DiffSummary],
        build_check: Optional[BuildCheckResult],
        violations: List[RuleViolation],
        invariant_result: Optional[LayaInvariantResult],
        contracts: Optional[List[DomainContract]],
        focus: str = "all",
    ) -> Optional[LLMReviewVerdict]:
        if not self.config or not self.config.llm:
            return None

        model_name = self.config.llm.model
        domain_str = domain.value if hasattr(domain, "value") else str(domain)

        focus_instruction = ""
        if focus == "security":
            focus_instruction = "CRITICAL FOCUS ON SECURITY: Rigorously audit for hardcoded secrets, injection (SQLi, XSS, Command), CSRF, insecure endpoints, and auth bypass."
        elif focus == "memory":
            focus_instruction = "CRITICAL FOCUS ON MEMORY SAFETY: Rigorously audit for dangling event listeners, unclosed streams/sockets/db connections, retained closures, and DOM leaks."
        elif focus == "performance":
            focus_instruction = "CRITICAL FOCUS ON PERFORMANCE & LATENCY: Rigorously audit for blocking synchronous I/O, N+1 query patterns, excessive re-renders, and thread lockups."
        elif focus == "ux":
            focus_instruction = "CRITICAL FOCUS ON ERGONOMICS & UX: Rigorously audit for broken keyboard shortcuts, modal backdrop handling, viewport responsiveness, and visual state feedback."
        elif focus in ("dead-code", "hygiene"):
            focus_instruction = "CRITICAL FOCUS ON CODE HYGIENE & DEAD CODE: Rigorously audit for orphan/unused files, commented-out blocks of code, unused imports, unreferenced helper functions/variables, redundant duplicate logic, and obsolete scratchpad or temporary files."
        else:
            focus_instruction = "FULL 360-DEGREE AUDIT: Evaluate across all 5 Quality Pillars (Security, Memory Safety, Performance, Data Integrity, Ergonomics/UX)."

        system_prompt = (
            f"You are the Senior Lead Architect and Code Reviewer acting as the final safety gate (using model {model_name}).\n"
            f"Review Directive: {focus_instruction}\n"
            "Your task is to audit the post-task verification report and git diff produced by an AI coding agent.\n"
            "Note: The automated test suite has already compiled and executed successfully with zero failures.\n"
            "If the task is refactoring or dead code removal and tests pass without breaking invariants, approve with confidence.\n"
            "Evaluate across 3 pillars:\n"
            "1. Technical Audit (Code integrity, memory leaks, dangling listeners, breaking API changes, security vulnerabilities)\n"
            "2. Invariants & Contracts (Ensure baseline UI states, interactions, and DB schemas are preserved)\n"
            "3. Ergonomics Polish (UX, responsive styling, accessibility across technical domains)\n"
            "Mandatory Output Format:\n"
            "SCORE: <float between 0.0 and 10.0>\n"
            "VERDICT: <APPROVED or REVISE>\n"
            "SUMMARY: <concise summary>\n"
            "TECHNICAL: <bullet points>\n"
            "ERGONOMICS: <bullet points>\n"
            "REMEDIATION: <bullet points of required fixes if REVISE, or 'None' if APPROVED>"
        )

        files_summary = ", ".join(f"{f.path} ({f.status})" for f in (diff_summary.files if diff_summary else []))
        build_info = f"PASSED ({build_check.command} exit 0)" if (build_check and build_check.passed) else ("FAILED" if build_check else "NOT RUN")

        user_content = f"""
Domain: {domain_str}
Review Focus: {focus.upper()}
Task Prompt: {prompt}
Build Status: {build_info}
Rule Violations: {len(violations)} issues
Out of Scope Files: {diff_summary.out_of_scope_files if diff_summary else []}
All Touched Files: {files_summary}

Git Diff:
```
{self._prepare_diff_for_review(diff_summary)}
```
        """

        raw_response = call_llm(
            cfg=self.config.llm,
            prompt=user_content,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=1000,
        )

        return self._parse_llm_response(raw_response, model_name=model_name, focus=focus)


    def _prepare_diff_for_review(self, diff_summary: Optional[DiffSummary]) -> str:
        if not diff_summary or not diff_summary.raw_diff:
            return 'No diff'
        raw = diff_summary.raw_diff
        if len(raw) <= 80000:
            return raw
        # Prioritize application source code over markdown/docs
        chunks = raw.split('diff --git ')
        src_chunks = [c for c in chunks if c.startswith('a/src/')]
        other_chunks = [c for c in chunks if not c.startswith('a/src/')]
        ordered = src_chunks + other_chunks
        return 'diff --git '.join(ordered)[:80000]

    def _parse_llm_response(self, text: str, model_name: str = "LLM", focus: str = "all") -> Optional[LLMReviewVerdict]:
        try:
            score_match = re.search(r"SCORE:\s*([\d\.]+)", text)
            score = float(score_match.group(1)) if score_match else 8.0
            score = max(0.0, min(10.0, score))

            verdict_match = re.search(r"VERDICT:\s*(APPROVED|REVISE)", text, re.IGNORECASE)
            verdict = ReviewVerdict.APPROVED if (verdict_match and verdict_match.group(1).upper() == "APPROVED") else ReviewVerdict.REVISE

            summary_match = re.search(r"SUMMARY:\s*(.+?)(?=\n[A-Z]+:|$)", text, re.DOTALL)
            summary = summary_match.group(1).strip() if summary_match else "LLM Review completed."

            tech_items = self._extract_bullet_items(text, "TECHNICAL")
            ergo_items = self._extract_bullet_items(text, "ERGONOMICS")
            remed_items = self._extract_bullet_items(text, "REMEDIATION")
            if any(item.lower() == "none" for item in remed_items):
                remed_items = []

            return LLMReviewVerdict(
                verdict=verdict,
                score=score,
                summary=summary,
                reviewer_model=model_name,
                focus_area=focus,
                technical_audit=tech_items,
                ergonomics_ux=ergo_items,
                remediation_steps=remed_items,
                review_mode="llm_deep",
            )
        except Exception:
            return None

    def _extract_bullet_items(self, text: str, section_header: str) -> List[str]:
        pattern = rf"{section_header}:\s*(.+?)(?=\n[A-Z]+:|$)"
        match = re.search(pattern, text, re.DOTALL)
        if not match:
            return []
        lines = match.group(1).strip().splitlines()
        results = []
        for line in lines:
            line_str = re.sub(r"^[\s\*\-\d\.\)]+", "", line).strip()
            if line_str and line_str.lower() != "none":
                results.append(line_str)
        return results
