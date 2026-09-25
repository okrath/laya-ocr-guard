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

---

## 3. `guard run`

Executes the automated Sandwich Pattern around any command.

```bash
guard run "<prompt>" -- <command...>
```

### Example:
```bash
guard run "Add customer discount calculation" -- git status
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

Manages Git hooks and AI Agent directives in target repositories.

```bash
# Install Git hooks and configure CLAUDE.md / AGENT.md:
guard hook install [--mode <git|agent|all>]

# Check active status of hooks and directives:
guard hook status

# Safely uninstall hooks and restore previous user files:
guard hook uninstall
```

---

## 7. `guard update`

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

---

## 8. `guard doctor`

Runs comprehensive system environment diagnostics and audits latest releases for both Laya-OCR-Guard CLI (GitHub) and Alibaba OCR (npm).

```bash
guard doctor [options]
```

### Options:
* `--updates / --no-updates`: Toggle npm registry update checking (default: on).
* `-q, --quarantine-days <float>`: Cooling period in days (default: 3.0 days).

---
*Created and maintained by [@okrath](https://github.com/okrath) &mdash; Source code available at [github.com/okrath/laya-ocr-guard](https://github.com/okrath/laya-ocr-guard).*
