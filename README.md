# Laya OCR Guard (`guard`)

<p align="center">
  <img src="docs/assets/logo.svg" width="160" height="160" alt="Laya OCR Guard Logo - The Bánh Mì Sandwich Pattern">
  <br>
  <strong>Dual-Gate Impact Analysis & Regression Guard for AI-Assisted Development</strong>
  <br>
  <em>Enforcing the Sandwich Pattern with sub-30ms triage, deterministic diff auditing, and LLM gatekeeping.</em>
</p>

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

> 🥖 **The Bánh Mì Sandwich Pattern:**
> Just like a crisp Vietnamese Bánh Mì, `guard` sandwiches code modifications between two protective crusts:
> * **Top Crust (`guard pre`):** Fast reflex triage, invariant locking & domain contract extraction.
> * **Core Filling (Developer / AI Agent edits):** Safe, scoped code implementation within contract boundaries.
> * **Bottom Crust (`guard post`):** Deterministic diff blast-radius audit, OCR static rulebook, project build/test command, `guard.invariants.json` checks, and LLM Gatekeeper approval.

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
│ • Invariant checks (0-cost): guard.invariants.json rules    │
│ ➔ Compiles: "### 🧪 POST-TASK VERIFICATION"                 │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. FINAL SAFETY GATE: YOUR CONFIGURED LLM                   │
│ (Claude-3.7-Sonnet / GPT-4o / DeepSeek / Ollama...)         │
│ • Reviews the report, verified evidence & batched diff      │
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

### 🧠 Laya Neural Engine Setup (Embedded ONNX)
`guard` embeds the native **Laya System 1 Neural Engine** using ONNX Runtime and ModernBERT tokenizers. **No `pip install laya` or 2.5 GB PyTorch dependencies required!**

To download and cache the standard high-fidelity INT8 neural weights (~554 MB, 99.8% accuracy parity):
```bash
# Download standard INT8 weights from HuggingFace:
guard laya download

# Inspect engine status, cache directory, and hardware acceleration:
guard laya status

# Test interactive System 1 triage on a prompt:
guard laya triage "Center checkout button and fix responsive modal CSS"
```
*(If weights are not yet downloaded, Guard runs its sub-1ms Zero-Overhead Reflex Matrix automatically so workflows are never blocked).*

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

## 🛋️ Simplicity & Engineering Frugality (KISS & YAGNI)

Inspired by Larry Wall's virtue of Laziness and [Dietrich Gebert's Ponytail](https://github.com/DietrichGebert/ponytail) philosophy: *"The best code is the code you never wrote."*

AI coding agents tend to be hyperactive—installing heavy libraries for trivial tasks or building 4-layer abstract classes for 10 lines of logic. `guard` enforces the **Ponytail Necessity Ladder**:

| Rule ID | Severity | Inspection Rule | Detection Target |
| :--- | :--- | :--- | :--- |
| **`LAZY-001`** | `HIGH` | **Dependency Bloat** | Redundant npm/pip packages (`is-odd`, `uuid`, `mkdirp`, `rimraf`, `pathlib2`, `mock`) when native APIs or stdlib suffice. |
| **`LAZY-002`** | `MEDIUM` | **Premature Abstraction** | Single-use interfaces, trivial pass-through wrapper functions, and over-engineered class hierarchies. |
| **`LAZY-003`** | `MEDIUM` | **Wheel Reinvention** | Re-implementing common utilities (`clamp`, `slugify`, `is_empty`, `flatten`, `deep_clone`) when stdlib or 1-liners suffice. |
| **`NET-LOC`** | ℹ️ **Info** | **Change Size** | Reports net lines added or removed. It is informational only: deleting code earns no score bonus. |

---

## 📖 CLI Usage Workflows

### 1. Bind Hooks to Any Target Repository or Workspace (`guard hook`)
Navigate to any target project repository, multi-repo workspace, or install globally across your machine:

```bash
# Interactive setup (auto-detects single repo vs multi-repo workspace):
guard hook install

# Workspace / Multi-Repo Mode (auto-discovers child Git repositories):
# Prompts to select: [A] All repos, [1-N] specific repos (e.g. 2,3,7,8), [G] Global, or [N] None
guard hook install --all-repos              # Install Git hooks to all discovered child repos
guard hook install --select-repos "1,2"     # Selectively install to specific child repos

# Global Git Protection (Protects EVERY repository on your machine automatically):
guard hook install --global                 # Sets git config --global core.hooksPath ~/.guard/hooks

# Single Repo Shortcuts:
guard hook install --stealth                # 👻 Stealth Mode (Git hook only, zero workspace files, never pushed to remote)
guard hook install --mode agent             # 🤖 Workspace Agent Directives (CLAUDE.md & AGENT.md)
guard hook install --mode all               # 🛡️ Dual-Gate Full Protection (Git hooks + Agent Directives)

# Inspect hook and agent directive status (including child repos and global hooks):
guard hook status

# Safely uninstall hooks and restore previous user files:
guard hook uninstall [--mode <git|agent|all>] [--global]
```

> 🔒 **Strict Safe-Append Policy:** Guard NEVER overwrites existing user `CLAUDE.md` or `AGENT.md` directives. It creates a `.guard.bak` backup and cleanly appends Guard protocol markers. Uninstallation cleanly restores user files.
### 2. Pre-Task Phase (`guard pre`)
Execute before modifying source code:
```bash
guard pre "Refactor checkout button to sticky bottom on mobile, update CSS and responsive modal"

# Declare scope explicitly (repeatable, globs allowed) when the prompt names no files:
guard pre "Review and fix bugs in the chat UI" --scope src/ui --scope src/ai/service.ts
```
A directory scope (`src/ui`) covers everything below it. Prefer it over `"src/ui/**"` on Windows, where the `guard.exe` launcher expands glob arguments even when they are quoted.
*Output:* Analyzes risk, locks baseline invariants, and generates `### 🔍 PRE-TASK IMPACT NOTE` in `.guard/PRE_TASK_NOTE.md`.

Gate rules that keep the pre-task gate meaningful:
- The domain comes from the repository files; the prompt triage is only shown as a hint.
- Scope is only what the prompt names or `--scope` declares. Files that are already dirty are never added to it. With no scope, the post report says scope was not audited instead of flagging every file.
- A dirty working tree is refused. `--allow-dirty` records those files as a pre-existing baseline and snapshots them with `git stash create` (pinned at `refs/guard/baseline`; the working tree is not touched). Post then reviews only the edits made after pre (diff against the snapshot), marks untouched files `PRE-EXISTING`, and raises `SCOPE-003` as a MEDIUM notice.
- An unfinished (pre without post) or rejected (`REVISE`) session is refused. `--force` restarts it but keeps its baseline, snapshot, base commit and scope. The restart is listed in both reports, and files covered only by scope added in the restart fail as `SCOPE-004`. Stashing, restarting and popping, or committing mid-task, is still audited, because post diffs against the base commit recorded at the first pre.
- Paths come from `git status --porcelain -z`, so renamed files and names with spaces or Vietnamese characters are tracked correctly. Globs are accepted only via `--scope`: prose such as "do not edit *.css" never widens scope.

#### Project invariants (`guard.invariants.json`)
Each guarded repository keeps its own `guard.invariants.json` in its root directory, committed with the code. It turns the rules an agent is told to respect (for example the invariant section of `AGENT.md`) into checks guard runs on every task, replacing the generic domain templates.

```bash
guard invariants init    # create the file; imports numbered items under an "Invariants" / "Bất biến" heading of AGENT.md / AGENTS.md / CLAUDE.md
guard invariants check   # evaluate every check on the current code, no session needed (exit 1 = a check fails, 2 = file missing/invalid)
```
`guard hook install` creates the file too (in every mode) and never overwrites an existing one. Imported entries start without checks (`UNVERIFIED`) until you add them:
```json
{"invariants": [
  {"id": "CHAT-01", "description": "Chat requests never time out",
   "checks": [{"files": "src/ai/**/*.ts", "forbid": "AbortSignal\\.timeout"}]},
  {"id": "UX-01", "description": "Message renders within 1ms"}
]}
```
Every check runs on the current file contents. `forbid` fails when any matched file contains the regex, and `require` fails when none of them does. A check whose `files` glob matches nothing also fails, and so does an invalid regex. A malformed `guard.invariants.json` makes `guard pre` stop with the parse error. Invariants without checks are reported as `UNVERIFIED` (manual) and never counted as passed. A check that was already failing when pre ran is reported as `BASELINE_FAILED` (a warning), so an old defect does not block unrelated tasks; a check that starts failing during the task blocks approval. When a task adds or edits `guard.invariants.json`, post also self-checks the new file on the current tree (`... (new guard.invariants.json, self-check)`), so a rule that fails on the code it was written for blocks approval. This repository's own gate-integrity invariants live in [`guard.invariants.json`](guard.invariants.json).

**Rules learned during review.** The LLM gate may propose durable rules it notices in the diff (`INVARIANTS:` section of its answer). Guard writes a proposal into `guard.invariants.json` only when its id and description are new and its check passes on the current code; it is tagged `"origin": "llm:<session>"`, listed under "Invariants learned in this review", and enforced from the next `guard pre`. The additions are part of the approved change, so they are committed with the task. Rejected proposals are listed with the reason.

**The rulebook cannot be weakened as a side effect.** Adding invariants never counts as out of scope. Removing an invariant or changing its checks raises `INV-WEAKENED`: CRITICAL (blocks) unless the task declares `guard.invariants.json` in its scope, in which case it is HIGH and left to the reviewer.

### 3. Post-Task Phase (`guard post`)
Execute after code modifications are complete:
```bash
# Standard verification:
guard post

# Deep focus on code hygiene & dead code:
guard post --focus dead-code

# Deep focus on KISS, YAGNI & over-engineering:
guard post --focus simplicity
```
*Output:* Inspects git diff, detects out-of-scope and deleted files, scans Alibaba OCR rules and code hygiene, executes the build command, runs invariant checks, and requests **Final Gate Approval from your configured LLM** (`APPROVED` or `REVISE`) in `.guard/POST_TASK_REPORT.md`.

The report names the gate that actually ran. It says "LLM Gate" only when the LLM answered. Otherwise it says "Heuristic Gate (no LLM review)" and records the failure reason (`llm_error`, `review_mode` in `.guard/session.json`). A review request waits at least 180 s, whatever `llm.timeout` is (that value is sized for `guard config test` pings). Deleting code earns no score bonus.

Removals that a compiler cannot see are checked over the whole repository: every string key (`case 'edit':`), export and CSS class deleted by the diff is searched for. One that is no longer defined but still referenced raises `DEAD-REF` (HIGH) with the locations. The summary line goes into every LLM review part as verified evidence, so a batched review does not have to guess about references in another part.

`SEC-003` (`innerHTML`/`outerHTML` `=` and `+=` sinks) checks every assignment on a line, and a comment that mentions "sanitize" does not silence it. Only an empty literal, a value that is exactly one `DOMPurify.sanitize(...)` call, or an explicit `// guard-allow SEC-003: <reason>` exempts a line, and that marker is still listed as a `LOW` finding.

Git hooks call `guard post --hook`. It skips repositories that have no guard session, and it also skips when `guard` is not on `PATH`. An approved session covers only the exact file contents it approved: committing them passes, while any file changed after the approval (or unrelated to it) is blocked until a new `guard pre`/`guard post` round. `guard reset` closes the current session (for work that was committed or abandoned) and archives it to `.guard/history/`. With global hooks (`core.hooksPath`), each repository's own hook (and a `.guard.bak` original) in its common `hooks/` directory still runs first, including from linked worktrees. `guard run` and the agent wrapper script accept the same pre-task flags (`--scope`, `--allow-dirty`, `--force`; the wrapper script reads them from `GUARD_PRE_ARGS`).

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

# Focused review acting as "The Laziest Senior Architect in the Room":
guard review --focus simplicity
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

# Check for Guard CLI updates on GitHub without installing:
guard update self --check

# Check system diagnostics & release audits:
guard doctor
```

### 7. Laya Neural Engine (`guard laya`)
Manage the embedded non-autoregressive neural classification model:
```bash
# Check Laya cache, model paths, and device:
guard laya status

# Download standard INT8 neural checkpoint weights (554MB):
guard laya download

# Run standalone System 1 triage test on a prompt:
guard laya triage "<prompt>"
```

---

## 🧪 Running the Test Suite

The project includes a comprehensive end-to-end integration and unit test suite (120+ tests):
```bash
pytest
```
