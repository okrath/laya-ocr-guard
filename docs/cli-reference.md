# CLI Command Reference: `guard`

> 📦 **GitHub Repository:** [github.com/okrath/laya-ocr-guard](https://github.com/okrath/laya-ocr-guard) &bull; 👤 **Author:** [@okrath](https://github.com/okrath) &bull; 📖 **Live Documentation:** [okrath.github.io/laya-ocr-guard](https://okrath.github.io/laya-ocr-guard/)

Complete command-line manual for `laya-ocr-guard`.

---
## 1. `guard pre`

Runs the Pre-Task Guard phase before modifying code.

```bash
guard pre "<prompt>" [options]
```

### Arguments:
* `prompt` (required): Natural language description of the task about to be performed.

### Options:
* `-r, --repo <path>`: Target repository directory (default: current directory).
* `-q, --quick`: Quick triage mode (skips deep file scanning, runs fast reflex classification only).
* `-s, --scope <path|dir|glob>` (repeatable): Declare the files the task may change. Files named in the prompt are added automatically; globs are accepted only here. On Windows prefer a directory (`--scope src/ui`) over a quoted glob.
* `--allow-dirty`: Start although files are already modified. They are snapshotted (`git stash create`, working tree untouched) and reported as pre-existing; post reviews only the edits made after pre.
* `--force`: Restart an unfinished or rejected session. The restart keeps its baseline, snapshot, base commit and scope, is listed in the reports, and scope added by it fails as `SCOPE-004`.

Pre refuses to start on a dirty tree (without `--allow-dirty`) and over an unfinished or rejected session (without `--force`).

---

## 2. `guard post`

Runs the Post-Task Guard verification phase after code has been edited.

```bash
guard post [options]
```

### Options:
* `-r, --repo <path>`: Target repository directory.
* `-f, --focus <area>`: Quality pillar to focus scrutiny on (`all`, `security`, `memory`, `performance`, `ux`, `dead-code`, `simplicity`). Default: `all`.
* `--auto-fix`: Trigger self-healing remediation suggestions if verification fails.
* `--hook`: Git-hook mode. Skips when the repository has no guard session; with an approved session, passes only when the changes match what was approved.

Post audits against the base commit recorded at pre, runs the build command, invariant checks and the removed-symbol reference check, then asks the LLM. A new or edited `guard.invariants.json` is self-checked on the current tree, and rules the LLM discovers are written into it after validation.

---

## 3. `guard run`

Executes the automated Sandwich Pattern around any command.

```bash
guard run "<prompt>" -- <command...>
```

Accepts the same pre-task options: `--scope`, `--allow-dirty`, `--force`.

### Example:
```bash
guard run "Add customer discount calculation" --scope src/pricing -- git status
```

---

## 4. `guard review`

Performs an on-demand review of the current Git working tree diff using your configured LLM.

```bash
guard review [options]
```

### Options:
* `-r, --repo <path>`: Target repository directory.
* `-f, --focus <area>`: Quality pillar focus (`all`, `security`, `memory`, `performance`, `ux`, `dead-code`, `simplicity`).

---

## 5. `guard config`

Manages configuration for LLM providers, Alibaba OCR sync, and Laya.

```bash
# View active configuration table:
guard config

# Launch interactive configuration wizard:
guard config llm [--local]

# Test LLM connection with token-free latency ping:
guard config test

# Manually synchronize credentials to Alibaba OCR CLI:
guard config sync
```

---

## 6. `guard hook`

Manages Git hooks, AI Agent directives, and multi-repo workspace protection.

Without options, `guard hook install` installs the **global** hooks (`core.hooksPath ~/.guard/hooks`) and sets up the current repository. Every other repository is set up automatically the first time guard runs in it: `guard.invariants.json` is created when missing, and when the repository uses its own `core.hooksPath` (the global hook does not run there) a marked guard block is inserted after the shebang of its `pre-commit`. `guard hook refresh` rewrites what guard installed earlier to the current version; the same refresh runs once automatically after each upgrade.

```bash
guard hook install          # global hooks + set up this repository
guard hook refresh          # refresh global hooks, repository guard blocks and marked directive blocks
# Interactive setup (auto-detects single repo vs multi-repo workspace):
guard hook install

# Workspace / Multi-Repo Mode (auto-discovers child Git repositories):
# Interactive menu: [A] All repos, [1-N] specific repos (e.g. 2,3,7,8), [G] Global, [N] None
guard hook install --all-repos              # Install Git hooks to all discovered child repos
guard hook install --select-repos "1,2"     # Selectively install to specific child repos

# Global Git Protection (Protects EVERY repository on your machine automatically):
guard hook install --global                 # Sets git config --global core.hooksPath ~/.guard/hooks

# Single Repo Shortcuts:
guard hook install --stealth                # 👻 Stealth Mode (Git hook only, zero workspace files)
guard hook install --mode agent             # 🤖 Agent Directives only (CLAUDE.md & AGENT.md)
guard hook install --mode all               # 🛡️ Dual-Gate Full Protection (Git hooks + Agent directives)

# Check active status of hooks, child repositories, and global hooks:
guard hook status

# Safely uninstall hooks and restore previous user files:
guard hook uninstall [--mode <git|agent|all>] [--global]
```

### Options for `guard hook install`:
* `-r, --repo <path>`: Target repository or workspace directory.
* `-m, --mode <git|agent|all>`: Installation mode (`git`, `agent`, `all`).
* `-s, --stealth`: Shortcut for `--mode git` (Git hooks only, no `CLAUDE.md`/`AGENT.md`).

Every install mode creates `guard.invariants.json` when it is missing (see `guard invariants init`) and never overwrites an existing one.
* `-g, --global`: Configure Git hooks globally for all repositories via `git config --global core.hooksPath ~/.guard/hooks`.
* `--all-repos`: Automatically install Git hooks into all discovered child Git repositories in workspace mode.
* `--select-repos <indices|names>`: Comma-separated list of child repo numbers (e.g. `2,3,7,8`) or folder names.

> 🔒 **Strict Safe-Append Policy:** Guard NEVER overwrites existing user `CLAUDE.md` or `AGENT.md` files. It creates a `.guard.bak` backup and cleanly appends Guard protocol markers.
---

## 7. `guard invariants`

Create and validate the project's `guard.invariants.json` (kept in the root directory of each guarded repository).

```bash
# Create the file; imports numbered items under an "Invariants" (or Vietnamese "Bất biến") heading of AGENT.md / AGENTS.md / CLAUDE.md:
guard invariants init

# Evaluate every check on the current code, without a session (exit 1: a check fails, exit 2: file missing or invalid):
guard invariants check
```

---

## 8. `guard reset`

Close the current guard session, for example after its work was committed or abandoned. The session is archived to `.guard/history/<session_id>.json`.

```bash
guard reset
```

---

## 9. `guard update`

Safely updates Alibaba OCR respecting the 3-day supply-chain quarantine cooling period.

```bash
# Check update status without installing:
guard update --check

# Safely upgrade Alibaba OCR (halts if release is < 3 days old):
guard update

# Explicitly bypass quarantine hold:
guard update --force

# Upgrade Laya-OCR-Guard CLI itself from GitHub:
guard update self

# Check for Guard CLI updates on GitHub without installing:
guard update self --check
```

After a successful `guard update self`, the new version runs `guard hook refresh` automatically (global hooks, repository guard blocks and marked directive blocks). An upgrade done outside guard is refreshed by the first guard command of the new version.

---

## 10. `guard doctor`

Runs comprehensive system environment diagnostics and audits latest releases for both Laya-OCR-Guard CLI (GitHub) and Alibaba OCR (npm).

```bash
guard doctor [options]
```

### Options:
* `--updates / --no-updates`: Toggle npm registry update checking (default: on).
* `-q, --quarantine-days <float>`: Cooling period in days (default: 3.0 days).

---

## 11. `guard laya`

Manages the embedded Laya ONNX Native Neural Decision Engine.

```bash
# Check model caching status, hardware acceleration, and paths:
guard laya status

# Download quantized INT8 weights from HuggingFace (554MB):
guard laya download [--force]

# Run interactive System 1 triage classification test on a prompt:
guard laya triage "<prompt>"

# Measure the installed model on the labelled prompt set; the neural model is used only after it passes:
guard laya calibrate
```

Triage uses the neural model only when this exact model file passed `guard laya calibrate` (domain accuracy >= 70%). The current `laya-int8` weights score 19% (chance level), so the keyword reflex engine is used. The domain that selects invariants and the build command is scored from the repository itself, not from Laya.

### Options for `guard laya download`:
* `-m, --model <laya-int8>`: Model checkpoint to download (default: `laya-int8`, 554MB high-fidelity INT8).
* `-f, --force`: Re-download weights even if already cached.

> 💡 **Zero-Dependency Fallback:** If weights are not downloaded or not calibrated, Guard runs its sub-1ms reflex engine automatically so workflows are never blocked.

---
*Created and maintained by [@okrath](https://github.com/okrath) &mdash; Source code available at [github.com/okrath/laya-ocr-guard](https://github.com/okrath/laya-ocr-guard).*
