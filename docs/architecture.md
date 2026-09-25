# Architectural Specification: Dual-Gate Safety Harness

`laya-ocr-guard` implements a **Dual-Gate Agentic Architecture** (the Sandwich Pattern) designed to eliminate silent regressions, security violations, and memory leaks when using AI Coding Agents.

---

## 1. System Taxonomy & Separation of Concerns

The architecture strictly decouples reflexive, deterministic, and generative responsibilities:

| Component | Nature | Execution Latency | Token Cost | Core Responsibility |
| :--- | :--- | :--- | :--- | :--- |
| **Laya** (System 1 Engine) | Non-autoregressive Transformer Classifier / Heuristic Matrix | Sub-30ms (Neural) / <1ms (Reflex) | **0 tokens ($0.00)** | Instant intent triage, platform domain routing, risk scoring (1–4), and post-task invariant verification. |
| **Alibaba Open Code Review (OCR)** | Deterministic AST & Git Diff Inspector | Sub-50ms (Local) | **0 tokens ($0.00)** | Precise git diff measurement, blast-radius enforcement (out-of-scope breach detection), and multi-language deterministic static rules. |
| **Your Configured LLM** | Autoregressive Model (Claude, GPT, DeepSeek, Ollama) | 2–60 seconds | User standard pricing | Contract extraction during pre-task and **Final Safety Gatekeeper** auditing technical architecture, memory leaks, and UX ergonomics. |

---

## 2. End-to-End Workflow Pipeline

```text
               [User Task / Issue Prompt]
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. PRE-TASK PHASE: `guard pre "<prompt>"`                   │
│ • Laya (<30ms, 0-cost): Intent, domain & risk triage        │
│ • Domain Contract Extractor (FE / BE / Infra / MB)          │
│ • Lock Invariant Rules (Must NOT be broken)                 │
│ ➔ Emits: "### 🔍 PRE-TASK IMPACT NOTE"                      │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼ (AI Coding Agent / Developer modifies code)
                           │
┌─────────────────────────────────────────────────────────────┐
│ 2. POST-TASK PHASE: `guard post`                            │
│ • OCR Inspector (0-cost): Diff audit & blast radius check   │
│ • Static Rulebook: Detect Secrets, SQLi, Memory Leaks, NPE  │
│ • Project Health Check: Automated compile & test execution  │
│ • Laya Scoring (0-cost): Score invariant compliance (Yes/No)│
│ ➔ Compiles: "### 🧪 POST-TASK VERIFICATION"                 │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. FINAL SAFETY GATE: YOUR CONFIGURED LLM                   │
│ (Claude-3.7-Sonnet / GPT-4o / DeepSeek / Ollama...)         │
│ • Reviews the aggregated post-task verification report      │
│ • Technical Audit (Architecture, Memory Leaks, Scope)       │
│ • Cross-Platform UX/UI & Ergonomics Assessment              │
│ • Verdict: [APPROVED] or [REVISE] with Actionable Remediation│
└─────────────────────────────────────────────────────────────┘
```

---

## 3. The Three Defense Layers

### Layer 1: Agent Directives (`CLAUDE.md` & `AGENT.md`)
AI Coding Agents (`omp`, Claude Code, Cursor, Windsurf, Aider) automatically ingest `CLAUDE.md` and `AGENT.md` at the start of every session. The directives mandate executing `guard pre` prior to editing and `guard post` upon task completion.

### Layer 2: Git Hook Defense (`.git/hooks/pre-commit`)
If an agent fails to run the post-task check or makes out-of-scope edits, the Git `pre-commit` hook intercepts `git commit`, executes the full verification pipeline, and automatically aborts the commit if compilation fails, invariants are broken, or the LLM rejects the change.

### Layer 3: Process Harness Wrapper (`guard run`)
For external CI/CD pipelines or headless scripts, `guard run "<prompt>" -- <command>` enforces the complete sandwich sequence as a single atomic process.
