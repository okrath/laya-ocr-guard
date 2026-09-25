# The 2D Quality Matrix: Platform Domains × Quality Pillars

`guard` evaluates code safety across a two-dimensional matrix combining **4 Platform Domains** with **5 Cross-Cutting Quality Pillars**.

---

## 1. Matrix Overview

```text
                           QUALITY PILLARS (Cross-Cutting Concerns)
                 ┌──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
                 │ 🛡️ Security  │ 🧠 Memory    │ ⚡ Performance│ 🧱 Integrity │ ♿ UX/Ergo    │
                 │ & Secrets    │ & Leaks      │ & Latency    │ & Contracts  │ & a11y       │
  ┌──────────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
  │ 🌐 Frontend  │ XSS, CSP     │ Listeners,   │ Bundle size, │ State        │ Responsive,  │
P │              │ token leaks  │ DOM detached │ re-renders   │ invariants   │ Escape, IME  │
L ├──────────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
A │ ⚙️ Backend   │ SQLi, Auth,  │ Connections, │ N+1 queries, │ JSON Schema, │ Standard err │
T │              │ RBAC, IDOR   │ goroutine/mem│ async blocks │ ACID trans   │ status codes │
F ├──────────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
O │ ☁️ Infra/Dev │ Public ports,│ Container    │ Startup time,│ Zero-downtime│ Healthcheck  │
R │              │ root secrets │ OOM limits   │ image bloat  │ IaC drift    │ readiness    │
M ├──────────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
  │ 📱 Mobile    │ SecureStore, │ Native bridge│ FPS drops,   │ Offline sync,│ SafeArea,    │
  │              │ permissions  │ Bitmap leaks │ battery drain│ SQLite ACID  │ dynamic notch│
  └──────────────┴──────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

---

## 2. The 5 Quality Pillars Detailed

### Pillar 1: 🛡️ Security & Secret Hygiene
- **Secret Detection (`SEC-001`)**: Scans git diffs for API keys, private keys, passwords, and sensitive tokens.
- **SQL Injection Prevention (`SEC-002`)**: Detects raw SQL string concatenations and demands parameterized queries or ORM models.
- **Cross-Site Scripting Prevention (`SEC-003`)**: Flags unsanitized HTML injections (`dangerouslySetInnerHTML`, `innerHTML`, `v-html`).
- **Network Interface Protection**: Forbids binding internal database ports (PostgreSQL, Redis, MongoDB) to public `0.0.0.0/0`.

### Pillar 2: 🧠 Memory Safety & Resource Leaks
- **Dangling Event Listeners (`PERF-001`)**: Detects global window/document event listeners added inside React/Vue components without corresponding unmount removal handlers.
- **Unclosed Resource Handles**: Verifies file streams, database connections, and network sockets are closed or managed via RAII / `with` constructs.
- **Native Mobile Retain Cycles**: Audits mobile view controllers and unmanaged Bitmaps.

### Pillar 3: ⚡ Performance & Low Latency
- **Blocking Synchronous I/O (`PERF-002`)**: Flags blocking sync operations (`readFileSync`, `execSync`) on event loops or async worker threads.
- **Re-render Throttling**: Checks for unbounded re-renders and missing debounce on high-frequency UI events.
- **Database Query Efficiency**: Audits N+1 query patterns in database layers.

### Pillar 4: 🧱 Data Integrity & Schema Compatibility
- **Backwards Compatibility**: Guarantees existing API JSON response schemas do not break downstream mobile and web clients.
- **Atomic Mutations**: Ensures multi-table database operations are encapsulated in database transactions with rollback support.

### Pillar 5: ♿ Ergonomics & UX Accessibility
- **Keyboard Navigation**: Preserves standard keyboard interactions (`Escape` to close modals, `Enter` to submit, `ArrowUp/Down` to navigate history).
- **Responsive Layout**: Verifies CSS layouts adapt across Mobile (390px), Tablet, and Desktop (1440px) without horizontal scrollbar overflow.
- **Visual Feedback**: Enforces visual state feedback (spinners, skeletons, disabled states) during asynchronous operations.

### Pillar 6: 🧹 Code & Asset Hygiene (Dead Code Gate)
- **Orphan & Draft Files (`DEAD-001`)**: Detects unreferenced newly added files and scratchpad artifacts (`*.tmp`, `*backup*`, `temp_*`).
- **Commented-out Code (`DEAD-002`)**: Detects stale blocks of commented-out source code (3+ lines) instead of clean Git deletions.
- **Unused Local Helpers & Imports (`DEAD-003`)**: Flags unreferenced private helper functions and unused imported symbols.

---

## 3. Scrutiny Focus Flag (`--focus`)

By default, Guard verifies quality pillars simultaneously (`--focus all`). To instruct the LLM Gatekeeper to conduct a specialized deep-dive:

```bash
# Deep-dive on dead code, zombie blocks & orphan files:
guard review --focus dead-code

# Deep-dive on memory leaks & resource cleanup:
guard review --focus memory

# Deep-dive on security vulnerabilities & secret leaks:
guard review --focus security

# Deep-dive on blocking I/O and latency:
guard review --focus performance

# Deep-dive on responsive UX and keyboard shortcuts:
guard review --focus ux
```
