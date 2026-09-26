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

To download and cache the INT8 neural weights (~554 MB):
```bash
# Download standard INT8 weights from HuggingFace:
guard laya download

# Measure the installed model on a labelled prompt set (required before it is used):
guard laya calibrate

# Inspect engine status, cache directory, and hardware acceleration:
guard laya status

# Test interactive System 1 triage on a prompt:
guard laya triage "Center checkout button and fix responsive modal CSS"
```
**Calibration gate.** Triage uses the neural model only after that exact model file passed `guard laya calibrate` (domain accuracy of at least 70% on the labelled set, recorded in `~/.guard/laya_calibration.json`). Otherwise it uses the sub-1ms keyword reflex engine. On the current `laya-int8` weights the model scores 3/16 (19%, chance level; it returns near-uniform probabilities) against 11/16 for the reflex engine, so the reflex engine is what runs. Laya's triage (intent, risk) is informational: the domain used for invariants and the build command comes from the repository itself.

**Repository domain.** The domain is scored from several signals instead of the first marker file found: Node dependencies of every `package.json` (monorepos included), web framework configs, `index.html`, UI component files, `server/`/`api/` directories, Python/Go/Rust/Java manifests, Terraform/Helm/Kubernetes and container files. A Node backend is no longer reported as frontend, an app with a `Dockerfile` is not infra (and is built with its package script, not `docker build`), and a repository with both a web client and a server is `fullstack`.

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

### 1. Install (`guard install`)
There are two ways to install guard. Neither needs a per-repository step.

```bash
# Global (whole machine):
#  - Git hooks for every repository (git config --global core.hooksPath ~/.guard/hooks)
#  - the guard directives in the global instruction file of each agent found on this machine:
#    ~/.claude/CLAUDE.md (Claude Code), ~/.codex/AGENTS.md (Codex), ~/.gemini/GEMINI.md (Gemini CLI),
#    ~/.config/opencode/AGENTS.md (opencode). Existing content is kept (backup: *.guard.bak).
guard install

# Workspace (one folder only):
#  - the guard directives in CLAUDE.md and AGENT.md of that folder
#  - Git hooks in the folder's repository, or in every Git repository below it
guard install --workspace path/to/workspace

# Remove what install added (marked blocks and guard's hooks; a foreign core.hooksPath is kept):
guard uninstall [--workspace path/to/workspace]

# Rewrite what guard installed earlier to the current version. Runs automatically after upgrades.
guard hook refresh
```

**How it chains together.** The agent reads the guard directives (global or workspace) and runs `guard pre` before editing. The first guard run inside a repository sets it up (below), and the Git hook checks every commit. Agents without a global instruction file (Cursor, omp) see the directives through a workspace install.

The older `guard hook install` still works: without options it runs `guard install`, and its options (`--stealth`, `--mode`, `--all-repos`, `--select-repos`, `--global`) keep their previous per-repository behavior. `guard hook status` shows the current hooks and directives.

> 🔒 **Strict Safe-Append Policy:** Guard NEVER overwrites existing user `CLAUDE.md` or `AGENT.md` directives. It creates a `.guard.bak` backup and cleanly appends Guard protocol markers. Uninstallation cleanly restores user files.

**Automatic repository setup.** The first time guard runs inside a Git repository (`guard pre`, `guard post`, `guard hook install`), it:
- creates `guard.invariants.json` when missing, importing the agent docs' invariant section;
- checks which hook directory Git really uses there. With the global hooks nothing is added. When the repository sets its own `core.hooksPath` (for example husky's `.husky`), the global hook never runs, so guard inserts a marked block (`# >>> LAYA-OCR-GUARD >>>`) right after the shebang of that `pre-commit` (or creates it). Existing hook commands are kept.
- records the repository in `~/.guard/repos.json`.

Outside a Git repository only the agent directives apply.

**Refresh after an upgrade.** The first guard command after a version change rewrites, only where guard wrote them before: the global hooks (when `core.hooksPath` points at `~/.guard/hooks`), the guard block in hooks of recorded repositories, and the directive block between the `LAYA-OCR-GUARD DUAL-GATE HOOK: START/END` markers in agent docs (the repositories' `CLAUDE.md`/`AGENT.md`/`AGENTS.md`/`GEMINI.md` and the global `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.gemini/GEMINI.md`, `~/.config/opencode/AGENTS.md`). Guard directives pasted without markers are reported, never rewritten. `guard hook refresh` runs the same refresh on demand.
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

#### Upgrading from an older version
Old installations (per-repository hooks, directives pasted without markers, no invariants file) keep working, and guard tells you what is still missing:

- `guard update self` runs `guard hook refresh` with the new version and then prints a **setup check** listing each missing item and the command that fixes it.
- If guard was upgraded another way, the first guard command of the new version prints the same check once.
- `guard doctor` always shows it, in the "Installation & Repository Setup" table.

| Check says | Run |
|---|---|
| Git hooks missing / commits not checked | `guard install` (or `guard install --workspace <dir>`) |
| Agent directives missing (no agent is told to run guard) | `guard install` (or `guard install --workspace <dir>`) |
| Repository sets its own `core.hooksPath` and its hook does not call guard | `guard hook refresh` inside the repository |
| Guard directives without START/END markers | wrap the guard section as shown below, or delete it and run `guard install` |
| No `guard.invariants.json` / invariants without checks | `guard invariants init`, then add checks and run `guard invariants check` |
| Laya model never calibrated (optional) | `guard laya calibrate` |

Markers that let guard refresh a pasted directive section:
```markdown
<!-- === LAYA-OCR-GUARD DUAL-GATE HOOK: START === -->
...guard directives...
<!-- === LAYA-OCR-GUARD DUAL-GATE HOOK: END === -->
```

**After an upgrade nothing has to be done by hand.** `guard update self` starts the newly installed guard to run `guard hook refresh`, which rewrites the global hooks, the guard blocks in recorded repositories' hooks and every directive block between guard markers. If guard was upgraded another way (for example `pipx upgrade`), the first guard command of the new version does the same once. A repository installed by an older version is refreshed the first time guard runs in it. The only manual case is guard directives pasted into an agent doc without the START/END markers: guard reports them (`WARN ...`) and explains how to wrap or reinstall them.

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
