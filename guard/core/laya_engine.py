"""
Laya Fast-Reflex Decision Engine for Laya-OCR-Guard.
Provides sub-30ms System 1 triage:
- Domain Classification (FE, BE, Infra, MB, Fullstack)
- Intent/Task Type (Feature, Bugfix, Refactor, Hotfix, Security)
- Risk Scoring (1 to 4)
- Core Breach Detection (Auth, Billing, DB Schema)
- Post-Task Invariant Compliance Scoring (Yes/No)

Features Dual-Mode execution:
Mode A: Native Laya Router (Neural Model via `pip install laya`)
Mode B: Sub-1ms Lightweight Reflex Engine (Zero-dependency heuristic matcher)
"""

from __future__ import annotations

import re
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


class DomainType(str, Enum):
    FRONTEND = "frontend"
    BACKEND = "backend"
    INFRA = "infra"
    MOBILE = "mobile"
    FULLSTACK = "fullstack"


class TaskIntent(str, Enum):
    FEATURE = "feature"
    BUGFIX = "bugfix"
    REFACTOR = "refactor"
    HOTFIX = "hotfix"
    SECURITY = "security"


class RiskLevel(int, Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class LayaTriageResult(BaseModel):
    domain: DomainType
    intent: TaskIntent
    risk_level: RiskLevel
    risk_score_label: str
    core_breach_risk: bool
    confidence: float = 0.95
    latency_ms: float
    engine_mode: str = "reflex"  # "laya_neural" or "reflex_fast"
    reasoning: str = ""


class InvariantCheck(BaseModel):
    id: str
    description: str
    passed: bool
    confidence: float
    notes: str = ""


class LayaInvariantResult(BaseModel):
    all_passed: bool
    checks: List[InvariantCheck]
    ui_regression_risk: bool
    latency_ms: float
    engine_mode: str = "reflex"


# Standard typed questions definitions for Laya
LAYA_TRIAGE_QUESTIONS = {
    "domain": {
        "type": "choice",
        "instructions": "Which technical domain is primarily affected by this prompt/task?",
        "criteria": {
            "frontend": "UI, CSS, HTML, React, Vue, Web components, layout, styling, responsive, modals",
            "backend": "API, Database, SQL, migrations, ORM, business logic, endpoints, controllers, backend services",
            "infra": "Docker, Kubernetes, Terraform, Helm, CI/CD, nginx, cloud resources, secrets, deployment, env vars",
            "mobile": "Flutter, React Native, iOS, Android, Swift, Kotlin, native permissions, screen orientation, offline cache",
            "fullstack": "Both frontend and backend changes across multiple layers",
        },
    },
    "intent": {
        "type": "choice",
        "instructions": "What is the primary intent of this task?",
        "criteria": {
            "feature": "Adding new functionality, new UI view, new API endpoint",
            "bugfix": "Fixing an existing defect, resolving unexpected behavior or error",
            "refactor": "Restructuring code, improving architecture without changing external behavior",
            "hotfix": "Urgent critical fix for production outage or crash",
            "security": "Fixing vulnerabilities, authentication, authorization, secret management",
        },
    },
    "risk_level": {
        "type": "score",
        "instructions": "What is the blast radius and risk level of this change?",
        "criteria": [
            "Low risk - localized change with minimal dependencies",
            "Medium risk - affects a secondary workflow or non-critical component",
            "High risk - modifies primary user flows, API schemas or state management",
            "Critical risk - modifies core authentication, billing, database migrations or root infrastructure",
        ],
    },
    "core_breach": {
        "type": "noul",
        "instructions": "Does this prompt modify authentication, payments, database migrations or root infrastructure?",
    },
}


class LayaEngine:
    """
    Dual-mode Laya decision engine.
    Attempts to initialize `laya.Router` if available; otherwise operates in
    sub-1ms Lightweight Reflex mode.
    """

    def __init__(self, prefer_neural: bool = False):
        self.prefer_neural = prefer_neural
        self._router = None
        self._mode = "reflex_fast"

        if prefer_neural:
            try:
                from laya import Router
                self._router = Router(preload=False)
                self._mode = "laya_neural"
            except Exception:
                self._router = None
                self._mode = "reflex_fast"

    @property
    def mode(self) -> str:
        return self._mode

    def triage(self, prompt: str, context_files: Optional[List[str]] = None) -> LayaTriageResult:
        """
        Fast triage of incoming prompt.
        Latency: <30ms (neural) or <1ms (reflex_fast).
        """
        start = time.perf_counter()

        if self._mode == "laya_neural" and self._router is not None:
            try:
                state = {
                    "prompt": prompt,
                    "context_files": ", ".join(context_files or []),
                }
                res = self._router.predict(state, LAYA_TRIAGE_QUESTIONS)
                answers = res.get("answers", {})

                domain_str = answers.get("domain", {}).get("choice", "backend")
                intent_str = answers.get("intent", {}).get("choice", "feature")
                risk_idx = int(answers.get("risk_level", {}).get("score", 1))
                core_breach = answers.get("core_breach", {}).get("answer", False)

                latency = (time.perf_counter() - start) * 1000
                return LayaTriageResult(
                    domain=DomainType(domain_str),
                    intent=TaskIntent(intent_str),
                    risk_level=RiskLevel(min(max(risk_idx + 1, 1), 4)),
                    risk_score_label=f"Risk {risk_idx + 1}/4",
                    core_breach_risk=bool(core_breach),
                    latency_ms=latency,
                    engine_mode="laya_neural",
                    reasoning=f"Neural triage via Laya Router in {latency:.1f}ms",
                )
            except Exception:
                # Fall back to reflex engine
                pass

        # Lightweight Reflex Engine (Sub-1ms)
        p_lower = prompt.lower()
        files_str = " ".join(context_files or []).lower()
        combined = f"{p_lower} {files_str}"

        # 1. Domain Detection
        domain = self._classify_domain(combined)

        # 2. Intent Detection
        intent = self._classify_intent(p_lower)

        # 3. Core Breach Detection (Deep back-office, auth, db migrations, payment gateway)
        core_breach = bool(re.search(
            r"\b(auth|jwt|password|stripe|payment\s+gateway|migration|secret|rbac|schema\s+change|drop\s+table)\b",
            combined,
        ))

        # 4. Risk Level Scoring
        risk_level = self._compute_risk_level(domain, intent, core_breach, combined)

        latency = (time.perf_counter() - start) * 1000
        labels = {
            RiskLevel.LOW: "1/4 (Low)",
            RiskLevel.MEDIUM: "2/4 (Medium)",
            RiskLevel.HIGH: "3/4 (High)",
            RiskLevel.CRITICAL: "4/4 (Critical)",
        }

        return LayaTriageResult(
            domain=domain,
            intent=intent,
            risk_level=risk_level,
            risk_score_label=labels[risk_level],
            core_breach_risk=core_breach,
            latency_ms=latency,
            engine_mode="reflex_fast",
            reasoning=f"Classified via Reflex Heuristic Matrix in {latency:.2f}ms",
        )

    def evaluate_invariants(
        self,
        invariants: List[Dict[str, str]],
        git_diff: str,
        files_changed: List[str],
    ) -> LayaInvariantResult:
        """
        Evaluate code diff against invariants locked in pre-task.
        """
        start = time.perf_counter()
        checks: List[InvariantCheck] = []
        all_passed = True
        diff_lower = git_diff.lower()

        # Check for common regression signals
        removed_lines = [line[1:].strip() for line in git_diff.splitlines() if line.startswith("-") and not line.startswith("---")]

        for inv in invariants:
            inv_id = inv.get("id", "INV-UNKNOWN")
            desc = inv.get("description", "")
            desc_lower = desc.lower()

            passed = True
            note = "Maintained"

            # Check if negative patterns (deleted key handlers, deleted endpoints) match
            if "escape" in desc_lower and any("keydown" in line.lower() or "escape" in line.lower() for line in removed_lines):
                passed = False
                note = "Detected removal of keyboard/escape handler in diff"
            elif "disabled" in desc_lower and any("disabled" in line.lower() for line in removed_lines):
                passed = False
                note = "Detected removal of disabled state in diff"
            elif "timeout" in desc_lower and any("timeout" in line.lower() for line in git_diff.splitlines() if line.startswith("+")):
                passed = False
                note = "Detected forbidden addition of timeout construct"
            elif "secret" in desc_lower and any(re.search(r"\b(api_key|secret|password)\s*[:=]\s*['\"].+['\"]", line.lower()) for line in git_diff.splitlines() if line.startswith("+")):
                passed = False
                note = "Detected potential hardcoded secret in diff additions"

            if not passed:
                all_passed = False

            checks.append(InvariantCheck(
                id=inv_id,
                description=desc,
                passed=passed,
                confidence=0.92,
                notes=note,
            ))

        ui_regression_risk = any(
            any(k in f.lower() for k in [".tsx", ".jsx", ".vue", ".html", ".css", ".swift", ".dart"])
            for f in files_changed
        ) and any(not c.passed for c in checks)

        latency = (time.perf_counter() - start) * 1000
        return LayaInvariantResult(
            all_passed=all_passed,
            checks=checks,
            ui_regression_risk=ui_regression_risk,
            latency_ms=latency,
            engine_mode=self._mode,
        )

    def _classify_domain(self, text: str) -> DomainType:
        scores = {
            DomainType.FRONTEND: len(re.findall(r"\b(css|ui|ux|component|modal|button|screen|view|html|react|vue|tailwind|responsive|layout|state|render|sticky)\b", text)),
            DomainType.BACKEND: len(re.findall(r"\b(api|endpoint|sql|database|query|service|controller|orm|route|prisma|postgres|fastapi|express|nest)\b", text)),
            DomainType.INFRA: len(re.findall(r"\b(docker|k8s|kubernetes|terraform|helm|ingress|port|env|deployment|ci|pipeline|aws|deploy)\b", text)),
            DomainType.MOBILE: len(re.findall(r"\b(flutter|ios|android|swift|kotlin|widget|screen|backstack|permission|camera|notch|safearray)\b", text)),
        }

        high_domains = [d for d, s in scores.items() if s >= 2]
        if len(high_domains) >= 2:
            return DomainType.FULLSTACK

        best_domain = max(scores, key=lambda k: scores[k])
        if scores[best_domain] == 0:
            return DomainType.BACKEND  # Default fallback
        return best_domain

    def _classify_intent(self, text: str) -> TaskIntent:
        if re.search(r"\b(fix|bug|issue|broken|error|crash|problem|resolve)\b", text):
            return TaskIntent.BUGFIX
        if re.search(r"\b(hotfix|urgent|critical|outage)\b", text):
            return TaskIntent.HOTFIX
        if re.search(r"\b(refactor|clean|cleanup|reorganize|rename|restructure)\b", text):
            return TaskIntent.REFACTOR
        if re.search(r"\b(security|vulnerability|cve|sanitize|encrypt|rbac)\b", text):
            return TaskIntent.SECURITY
        return TaskIntent.FEATURE

    def _compute_risk_level(self, domain: DomainType, intent: TaskIntent, core_breach: bool, text: str) -> RiskLevel:
        if core_breach or intent == TaskIntent.HOTFIX or re.search(r"\b(drop\s+table|delete\s+from|alter\s+table|format|wipe)\b", text):
            return RiskLevel.CRITICAL
        if intent == TaskIntent.SECURITY or domain == DomainType.INFRA:
            return RiskLevel.HIGH
        if domain == DomainType.FRONTEND:
            if re.search(r"\b(checkout|payment|auth|login)\b", text):
                return RiskLevel.HIGH
            return RiskLevel.MEDIUM
        if intent in [TaskIntent.BUGFIX, TaskIntent.REFACTOR] and domain != DomainType.FULLSTACK:
            return RiskLevel.LOW
        return RiskLevel.MEDIUM
