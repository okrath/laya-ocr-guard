# 🛡️ MANDATORY PROTOCOL: LAYA-OCR-GUARD DUAL-GATE HOOK

This document establishes **Mandatory Operational Directives** for any AI Coding Agent (`omp`, Claude Code, Cursor, Windsurf, Aider) working in this repository.

To prevent regressions and protect existing working features, **AI AGENTS MUST EXECUTE BOTH HOOK PHASES VIA THE BASH TOOL**:

```text
[Incoming Task / Bugfix Request]
             │
             ▼
┌────────────────────────────────────────────────────────┐
│ 1. PRE-TASK HOOK (MANDATORY BEFORE TOUCHING ANY CODE): │
│ • Run: `guard pre "<user_request>"`                    │
│ • Read: `.guard/PRE_TASK_NOTE.md` to learn Invariants  │
│ • Present format: ### 🔍 PRE-TASK IMPACT NOTE          │
└────────────────────────────────────────────────────────┘
             │
             ▼ (Agent performs minimal, scoped, precise code edits)
             │
┌────────────────────────────────────────────────────────┐
│ 2. POST-TASK HOOK (MANDATORY AFTER FINISHING EDITS):   │
│ • Run: `guard post`                                    │
│ • Verify build check, OCR diff rules & LLM Gate verdict│
│ • If REVISE: Self-heal and fix listed violations       │
│ • Present format: ### 🧪 POST-TASK VERIFICATION       │
└────────────────────────────────────────────────────────┘
```

---

### 📐 MANDATORY AGENT REPORTING FORMAT:

When replying to the user, the Agent must strictly structure the response:

```markdown
### 🔍 PRE-TASK IMPACT NOTE:
* **Current Baseline:** [Brief summary of existing functionality and contracts]
* **Expected Impact Range:** [List of files and components to be modified]
* **Locked Invariants:** [Technical constraints that must NOT be broken]

---
(Implementation content: clean, minimal, scoped code modifications)
---

### 🧪 POST-TASK VERIFICATION:
* **Actual Impact Range:** [Confirmed list of modified files]
* **Build Check:** [Automated compilation & test results from guard post]
* **LLM Gate Verdict:** [APPROVED or REVISE]
```
