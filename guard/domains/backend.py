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
                description="Không làm thay đổi schema của JSON Response cũ (tránh breaking changes cho client Mobile & FE).",
                rationale="Bảo vệ tương thích ngược API Contract.",
            ),
            LockedInvariant(
                id="BE-INV-02",
                description="Bắt buộc sử dụng Parameterized Query hoặc ORM, tuyệt đối không nối chuỗi thô trong SQL.",
                rationale="Chặn đứng nguy cơ SQL Injection.",
            ),
            LockedInvariant(
                id="BE-INV-03",
                description="Mọi thao tác ghi dữ liệu nhiều bảng phải nằm trong Database Transaction có Rollback khi lỗi.",
                rationale="Bảo vệ tính toàn vẹn dữ liệu (ACID).",
            ),
        ]

    def generate_targeted_test_plan(self, files: List[str], diff_text: str) -> List[str]:
        return [
            "Chạy integration/unit tests cho các endpoint bị chỉnh sửa.",
            "Test trường hợp lỗi (Negative Test): gửi payload thiếu trường bắt buộc xem API có trả 400 Bad Request chuẩn không.",
            "Kiểm tra xác thực: gọi API khi không truyền Auth Token xem có bị chặn 401 Unauthorized không.",
        ]
