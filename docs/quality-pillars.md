# Quality Pillars: What Guard Checks, and How

> 📦 **GitHub Repository:** [github.com/okrath/banh-mi-guard](https://github.com/okrath/banh-mi-guard) &bull; 👤 **Author:** [@okrath](https://github.com/okrath) &bull; 📖 **Live Documentation:** [okrath.github.io/banh-mi-guard](https://okrath.github.io/banh-mi-guard/)

`guard` looks at a change through several quality pillars. Each concern below is covered in one of three ways, and this page says which:

| How | What it means |
| :--- | :--- |
| **Rule** | A deterministic check on the diff or the repository, with a rule ID. It runs on every `guard post`, costs no tokens, and its findings are listed in the report. |
| **Project invariant** | A regex check you (or the LLM gate, locally) wrote in `guard.invariants.json` / `.guard/invariants.json`. Evaluated on the current files at pre and post. |
| **LLM review** | Something the configured LLM is asked to look at in the diff (the default 360° audit, or a `--focus` area). Not a deterministic check. |

When a repository has no project invariants, guard adds a few generic **template invariants** for the detected domain (frontend, backend, fullstack, infra, mobile). Most of them are only heuristics on the diff and are reported as `UNVERIFIED` when no heuristic applies.

---

## 1. 🛡️ Security & Secrets

| Concern | How | ID |
| :--- | :--- | :--- |
| Hardcoded API keys, tokens, passwords in added lines | Rule | `SEC-001` (CRITICAL) |
| SQL built by string concatenation | Rule | `SEC-002` (CRITICAL) |
| Unsanitized HTML sinks: `innerHTML`/`outerHTML` `=` and `+=`, `dangerouslySetInnerHTML`, `v-html`. A comment mentioning "sanitize" does not exempt a line; only an empty literal, a single `DOMPurify.sanitize(...)` value or `// guard-allow SEC-003: <reason>` (listed as LOW) does | Rule | `SEC-003` (HIGH) |
| Auth, RBAC, IDOR, public ports, secrets in manifests | LLM review (`--focus security`); template invariants for backend/infra | — |

## 2. 🧠 Memory Safety & Resource Leaks

| Concern | How | ID |
| :--- | :--- | :--- |
| Global `resize`/`scroll`/`mousemove`/`keydown` listener added with no `removeEventListener` in the diff | Rule | `PERF-001` (HIGH) |
| Unclosed streams, sockets, DB connections; retained closures; DOM leaks | LLM review (`--focus memory`) | — |

## 3. ⚡ Performance & Latency

| Concern | How | ID |
| :--- | :--- | :--- |
| Blocking sync I/O (`readFileSync`, `writeFileSync`, `execSync`, `spawnSync`) in JS/TS | Rule | `PERF-002` (MEDIUM) |
| N+1 queries, excessive re-renders, thread lockups | LLM review (`--focus performance`) | — |

## 4. 🧱 Integrity, Scope & Contracts

| Concern | How | ID |
| :--- | :--- | :--- |
| Files changed outside the declared scope | Scope audit (marked OUT-OF-SCOPE; blocks) | `SCOPE-001` in `guard review` |
| File deleted (confirm the task asked for it) | Rule | `SCOPE-002` (MEDIUM) |
| Files already modified before pre (`--allow-dirty`) | Rule | `SCOPE-003` |
| File covered only by scope added in a `--force` restart | Rule | `SCOPE-004` (HIGH) |
| Project rules (behavior that must not break) | Project invariant | your IDs |
| Invariants file removed or relaxed; malformed invariants file | Rule | `INV-WEAKENED`, `INV-FILE` |
| Deep property access without optional chaining (`a.b.c.d`) | Rule | `STAB-001` (MEDIUM) |
| API schema compatibility, atomic multi-table writes | LLM review; backend template invariants (UNVERIFIED) | — |
| The project still builds / tests pass | Build command (`pnpm run build`, `pytest`, `go test ./...`, ...) | build check (blocks on failure) |

## 5. ♿ Ergonomics & UX

| Concern | How | ID |
| :--- | :--- | :--- |
| Removed keyboard handlers (`keydown`, `'Escape'`, `keyCode 27`) when a template invariant asks to keep them | Template invariant heuristic | frontend template |
| Responsive layout, focus handling, visual feedback, modal dismissal | LLM review (`--focus ux`) | — |

## 6. 🧹 Code & Asset Hygiene (Dead Code Gate)

| Concern | How | ID |
| :--- | :--- | :--- |
| New files that nothing references, draft names (`*.tmp`, `*backup*`, `temp_*`) | Rule | `DEAD-001` |
| 3+ consecutive lines of commented-out code | Rule | `DEAD-002` |
| Unused private helpers and imports (AST, with `--focus dead-code`) | Rule | `DEAD-003` |
| A removed string key (`case 'edit':`), export or CSS class that is still referenced somewhere in the repository | Rule | `DEAD-REF` (HIGH) |

## 7. 🛋️ Simplicity (KISS & YAGNI)

*Inspired by Larry Wall's virtue of Laziness and Dietrich Gebert's Ponytail philosophy: "The best code is the code you never wrote."*

| Concern | How | ID |
| :--- | :--- | :--- |
| Redundant packages (`is-odd`, `uuid`, `mkdirp`, `rimraf`, `pathlib2`, `mock`) when stdlib or the runtime suffices | Rule | `LAZY-001` |
| Single-use interfaces, pass-through wrappers, deep class hierarchies | Rule | `LAZY-002` |
| Re-implemented utilities (`clamp`, `slugify`, `is_empty`, `flatten`, `deep_clone`) | Rule | `LAZY-003` |
| Net lines added or removed | Informational only (deleting code earns no score bonus) | `NET-LOC` |

---

## Scoring and the final verdict

- **Blocks outright** (no LLM can approve): a failed build, a violated invariant, a CRITICAL rule, a file out of scope, and in `--focus dead-code` / `--focus simplicity` any finding of that pillar.
- Otherwise the heuristic score starts at 10 and loses points for HIGH findings (and, lightly, for hygiene and simplicity findings); below 7.5 the heuristic verdict is REVISE.
- The configured LLM then reviews the report, the verified evidence and the diff (in parts when it is large) and gives the final `APPROVED` / `REVISE`. If it does not answer, the report says "Heuristic Gate (no LLM review)" and why.

## Focus flag (`--focus`)

By default the LLM runs a 360° audit (`--focus all`). A focus narrows the review, and for `dead-code` and `simplicity` also makes that pillar's rules blocking:

```bash
guard post --focus security      # injection, secrets, CSRF, auth bypass
guard post --focus memory        # listeners, unclosed resources, leaks
guard post --focus performance   # blocking I/O, N+1, re-renders
guard post --focus ux            # keyboard, modals, responsiveness, feedback
guard post --focus dead-code     # orphans, commented code, unused symbols (full-file AST scan)
guard post --focus simplicity    # over-engineering, bloat, reinvented wheels
```
The same `--focus` values work with `guard review`.

---
*Created and maintained by [@okrath](https://github.com/okrath) &mdash; Source code available at [github.com/okrath/banh-mi-guard](https://github.com/okrath/banh-mi-guard).*
