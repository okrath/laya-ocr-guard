# Laya OCR Guard (`guard`)

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Documentation](https://img.shields.io/badge/docs-live_website-brightgreen.svg)](https://okrath.github.io/laya-ocr-guard/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](#-cross-platform-installation-windows-linux-macos)
[![Architecture](https://img.shields.io/badge/architecture-Dual--Gate-green.svg)](#-three-pillar-architecture)

**Dual-Gate Impact Analysis & Regression Guard for AI-Assisted Development.**

📖 **Live Documentation & Interactive Guide:** [https://okrath.github.io/laya-ocr-guard/](https://okrath.github.io/laya-ocr-guard/)

`guard` wraps coding workflows in an automated safety harness by uniting three distinct pillars:
1. **Laya** (System 1 fast reflex triage, <30ms, 0-cost, 0 token)
2. **Alibaba Open Code Review - OCR** (Deterministic git diff blast-radius & static rules engine, 0-cost)
3. **Your Configured LLM** (Claude 3.7 Sonnet, GPT-4o, DeepSeek, Ollama...): Acting as the Architectural Brain & **Final Safety Gatekeeper**.

Automates and enforces the rigorous **Impact & Regression Protocol** pioneered in `oh-my-ainovel`.

---

## 🏛️ Three-Pillar Architecture

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
│ • Hygiene Engine (0-cost): Detects orphan files & dead code │
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

## 🚀 Cross-Platform Installation (Windows, Linux, macOS)

Install the `guard` CLI globally on any platform using one of the following methods:

### Method 1: Install directly from GitHub (Recommended)
```bash
# On Linux / macOS (Recommended with pipx for isolated global binary):
pipx install git+https://github.com/okrath/laya-ocr-guard.git

# Or with standard pip across all platforms (Windows / Linux / macOS):
pip install git+https://github.com/okrath/laya-ocr-guard.git
```

### Method 2: Clone repository & install in editable mode
```bash
git clone https://github.com/okrath/laya-ocr-guard.git
cd laya-ocr-guard
pip install -e .
```

### 💡 Environment `$PATH` Setup:
* **Windows**: `guard.exe` is automatically installed into `Python3xx\Scripts\guard.exe`.
* **Linux / macOS**: The `guard` executable lives in `~/.local/bin/guard` or `/usr/local/bin/guard`.  
  If your terminal displays `command not found: guard`, add it to your shell configuration:
  ```bash
  # For bash:
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc

  # For zsh (default on macOS):
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
  ```

### Optional: Install Alibaba OCR CLI
`guard` bundles a built-in deterministic diff inspector and multi-language rules engine (0-cost). If you also want to enable the official Alibaba OCR CLI tool:
```bash
npm install -g @alibaba-group/open-code-review
```

Check system environment health:
```bash
guard doctor
```

---

## ⚙️ LLM Configuration & OCR Auto-Sync

Configure your LLM credentials once; `guard` automatically synchronizes settings with the Alibaba OCR CLI:

```bash
guard config llm
```

The interactive wizard supports two industry-standard protocols:
1. **OpenAI / OpenAI-Compatible**: OpenAI (`gpt-4o`), **Ollama** (`http://localhost:11434/v1`), **DeepSeek** (`https://api.deepseek.com/v1`), OpenRouter, vLLM, or Local Gateways (`http://127.0.0.1:8090/v1`).
2. **Anthropic**: Claude API (`claude-3-7-sonnet`).

Verify connectivity with an instant, token-free latency ping:
```bash
guard config test
```

---

## 🌐 Multi-Domain Coverage (FE, BE, Infra, MB)

`guard` automatically detects the repository's technology stack and applies domain-specific contracts:

| Domain | Tech Stacks | Baseline Contracts & Invariants | Automated Verification |
| :--- | :--- | :--- | :--- |
| **FE** (Frontend) | React, Next.js, Vue, Tailwind, Svelte | UI states (`loading`, `disabled`), keyboard shortcuts (`Escape`, `Enter`), responsive layouts | `pnpm run build` / `npm run build` |
| **BE** (Backend) | Go, Python (FastAPI/Django), NestJS, Rust | API JSON schema backwards-compatibility, SQLi prevention, atomic DB transactions | `pytest`, `go test ./...`, `cargo test` |
| **Infra** (DevOps) | Docker, Kubernetes, Terraform, Helm, CI/CD | Forbid hardcoded secrets, forbid 0.0.0.0 binding on internal DBs, zero-downtime healthchecks | `terraform validate`, `docker compose config` |
| **MB** (Mobile) | Flutter, React Native, iOS (Swift), Android | Hardware permission flows, SafeArea notch boundaries, offline cache fallback | `flutter analyze`, `./gradlew test` |

---

## 🧹 Code Hygiene & Dead Code Gate

AI coding agents often leave behind code rot: scratchpad files, commented-out dead code blocks, and unreferenced helper functions. `guard` prevents codebase rot via a **Two-Tier Hygiene Scanner**:

| Rule ID | Severity | Inspection Rule | Detection Target |
| :--- | :--- | :--- | :--- |
| **`DEAD-001`** | `HIGH` / `MEDIUM` | **Orphan & Draft Files** | Unreferenced newly added files or draft names (`*.tmp`, `*backup*`, `temp_*`, `test_scratch*`). |
| **`DEAD-002`** | `MEDIUM` | **Commented-Out Code** | Blocks of 3+ consecutive lines of commented source code instead of clean Git deletion. |
| **`DEAD-003`** | `MEDIUM` / `LOW` | **Unused Symbols & Imports** | AST analysis flags unreferenced private helpers (`def _foo`) and unused imported symbols. |

### Two-Tier Execution Strategy:
1. **Commit-Level (Diff-Level, <50ms):** Automatically runs during `guard post` and Git hooks. Checks newly added files for orphan status and diff additions (`+`) for commented-out code.
2. **Focus-Level (Full-File Deep Scan):** Triggered via `--focus dead-code`. Scans entire touched files and AST to detect all unreferenced helpers, unused imports, and zombie code blocks.

---

## 📖 CLI Usage Workflows

### 1. Bind Hooks to Any Target Repository (`guard hook`)
Navigate to any target project repository and run:
```bash
# Installs Git hooks and auto-configures CLAUDE.md & AGENT.md for AI agents
guard hook install

# Inspect hook and agent directive status
guard hook status

# Safely uninstall hooks and restore previous user files
guard hook uninstall
```

### 2. Pre-Task Phase (`guard pre`)
Execute before modifying source code:
```bash
guard pre "Refactor checkout button to sticky bottom on mobile, update CSS and responsive modal"
```
*Output:* Analyzes risk, locks baseline invariants, and generates `### 🔍 PRE-TASK IMPACT NOTE` in `.guard/PRE_TASK_NOTE.md`.

### 3. Post-Task Phase (`guard post`)
Execute after code modifications are complete:
```bash
# Standard verification:
guard post

# Deep focus on code hygiene & dead code:
guard post --focus dead-code
```
*Output:* Inspects git diff, detects out-of-scope files, scans Alibaba OCR rules and code hygiene, executes automated build/test commands, scores invariant compliance via Laya, and requests **Final Gate Approval from your configured LLM** (`APPROVED` or `REVISE`) in `.guard/POST_TASK_REPORT.md`.

### 4. Automated Sandwich Pattern Execution (`guard run`)
Wraps any developer or agent command in pre- and post-task gates:
```bash
guard run "Add shipping fee calculation endpoint" -- git status
```

### 5. On-Demand LLM Code Review (`guard review`)
Run an immediate architectural and safety review on the current Git diff:
```bash
# Standard on-demand review:
guard review

# Focused review on code hygiene & orphan files:
guard review --focus dead-code
```

### 6. Supply-Chain Security & Safe Updates (`guard update`)
Guard enforces a **3-day Quarantine Cooling Period** on Alibaba OCR npm releases to defend against zero-day backdoors:
```bash
# Check for new releases without installing:
guard update --check

# Safely upgrade Alibaba OCR (automatically halts if release is < 3 days old):
guard update

# Bypass quarantine hold explicitly:
guard update --force

# Upgrade the Guard CLI itself directly from GitHub:
guard update self
```

---

## 🧪 Running the Test Suite

The project includes an end-to-end integration and unit test suite (55+ tests):

```bash
pytest
```
