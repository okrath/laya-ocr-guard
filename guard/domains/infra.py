"""
Infrastructure (Infra) Domain Analyzer.
Handles Docker, Kubernetes, Terraform, Helm, GitHub Actions, Nginx, Cloud resources.
Extracts port mappings, secret bindings, volume mounts, resource quotas, and downtime risks.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from guard.core.session import DomainContract, LockedInvariant
from guard.domains.base import BaseDomainAnalyzer


class InfraDomainAnalyzer(BaseDomainAnalyzer):
    @property
    def name(self) -> str:
        return "Infrastructure & DevOps (IaC / Containers / CI-CD)"

    def detect(self, repo_path: Path) -> bool:
        infra_indicators = [
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose.yaml",
            "main.tf",
            ".github/workflows",
            "k8s",
            "helm",
            "nginx.conf",
        ]
        return any((repo_path / ind).exists() for ind in infra_indicators)

    def get_default_build_command(self, repo_path: Path) -> Optional[str]:
        if (repo_path / "main.tf").exists() or any(repo_path.glob("*.tf")):
            return "terraform validate"
        if (repo_path / "docker-compose.yml").exists() or (repo_path / "docker-compose.yaml").exists():
            return "docker compose config"
        if (repo_path / "Dockerfile").exists():
            return "docker build -t guard-temp-check . -f Dockerfile"
        return None

    def extract_baseline_contracts(self, repo_path: Path, files: List[str]) -> List[DomainContract]:
        contracts: List[DomainContract] = []
        infra_files = [f for f in files if any(f.endswith(ext) or "/" in f for ext in [".tf", ".yml", ".yaml", "Dockerfile", ".conf"])]

        for rel_path in infra_files[:5]:
            p = repo_path / rel_path
            if not p.is_file():
                continue
            try:
                code = p.read_text(encoding="utf-8", errors="ignore")[:4000]

                # Check for exposed ports
                ports = re.findall(r"""\b(EXPOSE|ports:|targetPort:)\s*(\d+)""", code)
                for prefix, port in ports:
                    contracts.append(DomainContract(
                        category="INFRA_PORT",
                        name=f"Port_{port}_binding",
                        description=f"Preserve standard port binding {port} in {rel_path}",
                    ))

                # Check for volume persistence
                if re.search(r"\b(volumes:|mountPath:|volumeMounts)\b", code):
                    contracts.append(DomainContract(
                        category="DATA_PERSISTENCE",
                        name=f"{Path(rel_path).stem}_volume_mount",
                        description=f"Preserve persistent storage volume mounts in {rel_path}",
                    ))

                # Check for environment / secret references
                if re.search(r"\b(secretKeyRef|valueFrom|env_file|secrets:)\b", code):
                    contracts.append(DomainContract(
                        category="SECRET_HYGIENE",
                        name=f"{Path(rel_path).stem}_secret_binding",
                        description=f"Preserve external secret resolution without hardcoding values in {rel_path}",
                    ))
            except Exception:
                pass

        return contracts

    def generate_recommended_invariants(self, prompt: str, files: List[str]) -> List[LockedInvariant]:
        return [
            LockedInvariant(
                id="INFRA-INV-01",
                description="Tuyệt đối không hardcode mật khẩu, Private Key, hoặc Production API Key vào manifest/Dockerfile.",
                rationale="Chặn đứng nguy cơ rò rỉ secret ra git history.",
            ),
            LockedInvariant(
                id="INFRA-INV-02",
                description="Không mở port 0.0.0.0/0 cho các dịch vụ Database nội bộ (Postgres, Redis, Mongo).",
                rationale="Ngăn ngừa tấn công quét cổng công khai.",
            ),
            LockedInvariant(
                id="INFRA-INV-03",
                description="Bảo đảm tính Zero-Downtime: cấu hình readiness/liveness probe hợp lệ trước khi route traffic.",
                rationale="Tránh rớt service khi rolling update.",
            ),
        ]

    def generate_targeted_test_plan(self, files: List[str], diff_text: str) -> List[str]:
        return [
            "Chạy cú pháp kiểm tra cấu hình: `docker compose config` hoặc `terraform validate`.",
            "Soát lại git diff: xác nhận 100% không có chuỗi secret/token nào bị dán trực tiếp.",
            "Kiểm tra port mapping và biến môi trường không làm gãy kết nối giữa các containers.",
        ]
