"""
Backend (BE) Domain Analyzer.
Handles Python (FastAPI/Django), Go, Node.js (NestJS/Express), Rust (Actix/Axum), SQL/ORM.
Extracts API endpoint contracts, DB schemas, auth middleware, and transactional invariants.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from guard.core.session import DomainContract, LockedInvariant
from guard.domains.base import BaseDomainAnalyzer


class BackendDomainAnalyzer(BaseDomainAnalyzer):
    @property
    def name(self) -> str:
        return "Backend (API & Database Services)"

    def detect(self, repo_path: Path) -> bool:
        be_indicators = [
            "go.mod",
            "Cargo.toml",
            "requirements.txt",
            "pyproject.toml",
            "prisma/schema.prisma",
            "alembic.ini",
            "src/main.go",
            "main.py",
            "nest-cli.json",
        ]
        return any((repo_path / ind).exists() for ind in be_indicators)

    def get_default_build_command(self, repo_path: Path) -> Optional[str]:
        if (repo_path / "go.mod").exists():
            return "go test ./... -v"
        if (repo_path / "Cargo.toml").exists():
            return "cargo test"
        if (repo_path / "pyproject.toml").exists() or (repo_path / "requirements.txt").exists():
            if (repo_path / "pytest.ini").exists() or (repo_path / "tests").exists():
                return "pytest"
            return "python -m unittest"
        if (repo_path / "package.json").exists():
            return "npm test"
        return None

    def extract_baseline_contracts(self, repo_path: Path, files: List[str]) -> List[DomainContract]:
        contracts: List[DomainContract] = []
        be_files = [f for f in files if any(f.endswith(ext) for ext in [".go", ".py", ".rs", ".ts", ".js", ".sql"])]

        for rel_path in be_files[:5]:
            p = repo_path / rel_path
            if not p.is_file():
                continue
            try:
                code = p.read_text(encoding="utf-8", errors="ignore")[:4000]

                # Check for API Routes/Endpoints
                routes = re.findall(r"""@?(app|router)\.(get|post|put|delete|patch)\(["']([^"']+)["']""", code, re.IGNORECASE)
                for _, method, path in routes:
                    contracts.append(DomainContract(
                        category="API_ENDPOINT",
                        name=f"{method.upper()}_{path}",
                        description=f"Preserve endpoint signature for {method.upper()} {path} in {rel_path}",
                    ))

                # Check for Auth / Middleware guards
                if re.search(r"\b(Depends|AuthGuard|authenticate|jwt|bearer|authorize)\b", code):
                    contracts.append(DomainContract(
                        category="SECURITY_AUTH",
                        name=f"{Path(rel_path).stem}_auth_protection",
                        description=f"Preserve authentication & authorization guard in {rel_path}",
                    ))

                # Check for DB transactions
                if re.search(r"\b(transaction|commit|rollback|session\.begin)\b", code):
                    contracts.append(DomainContract(
                        category="DATA_INTEGRITY",
                        name=f"{Path(rel_path).stem}_transaction_rollback",
                        description=f"Ensure atomic database transactions with rollback in {rel_path}",
                    ))
            except Exception:
                pass

        return contracts

    def generate_recommended_invariants(self, prompt: str, files: List[str]) -> List[LockedInvariant]:
        return [
            LockedInvariant(
                id="BE-INV-01",
                description="Do not break existing JSON response schemas (maintain backwards compatibility for mobile & web clients).",
                rationale="Prevent client-side breaking API contracts.",
            ),
            LockedInvariant(
                id="BE-INV-02",
                description="Must use parameterized queries or ORM models. Never concatenate raw untrusted input in SQL.",
                rationale="Prevent SQL Injection vulnerabilities.",
            ),
            LockedInvariant(
                id="BE-INV-03",
                description="Multi-table database mutations must be encapsulated within an atomic transaction with rollback.",
                rationale="Protect database consistency (ACID).",
            ),
        ]

    def generate_targeted_test_plan(self, files: List[str], diff_text: str) -> List[str]:
        return [
            "Execute unit and integration tests for modified API endpoints.",
            "Negative testing: send requests missing mandatory fields to verify standard 400 Bad Request responses.",
            "Authentication testing: verify unauthenticated calls receive 401 Unauthorized.",
        ]
