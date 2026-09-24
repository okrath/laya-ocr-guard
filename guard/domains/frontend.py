"""
Frontend (FE) Domain Analyzer.
Handles React, Next.js, Vue, Svelte, Vite, Tailwind projects.
Extracts UI states (loading, disabled, modal, errors), event handlers, and responsive layout constraints.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from guard.core.session import DomainContract, LockedInvariant
from guard.domains.base import BaseDomainAnalyzer


class FrontendDomainAnalyzer(BaseDomainAnalyzer):
    @property
    def name(self) -> str:
        return "Frontend (Web UI/UX)"

    def detect(self, repo_path: Path) -> bool:
        fe_indicators = [
            "package.json",
            "vite.config.ts",
            "vite.config.js",
            "next.config.js",
            "next.config.mjs",
            "tailwind.config.js",
            "src/App.tsx",
            "src/App.vue",
        ]
        return any((repo_path / ind).exists() for ind in fe_indicators)

    def get_default_build_command(self, repo_path: Path) -> Optional[str]:
        pkg_json = repo_path / "package.json"
        if not pkg_json.exists():
            return None

        # Detect package manager
        pm = "npm"
        if (repo_path / "pnpm-lock.yaml").exists():
            pm = "pnpm"
        elif (repo_path / "yarn.lock").exists():
            pm = "yarn"
        elif (repo_path / "bun.lockb").exists() or (repo_path / "bun.lock").exists():
            pm = "bun"

        try:
            content = pkg_json.read_text(encoding="utf-8")
            if '"build":' in content:
                return f"{pm} run build"
            if '"check":' in content:
                return f"{pm} run check"
        except Exception:
            pass
        return f"{pm} test"

    def extract_baseline_contracts(self, repo_path: Path, files: List[str]) -> List[DomainContract]:
        contracts: List[DomainContract] = []
        ui_files = [f for f in files if any(f.endswith(ext) for ext in [".tsx", ".jsx", ".vue", ".svelte", ".html", ".css"])]

        for rel_path in ui_files[:5]:  # inspect up to 5 files
            p = repo_path / rel_path
            if not p.is_file():
                continue
            try:
                code = p.read_text(encoding="utf-8", errors="ignore")[:4000]

                # Check for loading states
                if re.search(r"\b(isLoading|loading|spinner|skeleton)\b", code):
                    contracts.append(DomainContract(
                        category="UI_STATE",
                        name=f"{Path(rel_path).stem}_loading_state",
                        description=f"Preserve loading/skeleton feedback in {rel_path}",
                    ))

                # Check for disabled button states
                if re.search(r"disabled\s*=\s*\{|disabled\s*:", code):
                    contracts.append(DomainContract(
                        category="UI_STATE",
                        name=f"{Path(rel_path).stem}_disabled_behavior",
                        description=f"Preserve button disabled states during submission in {rel_path}",
                    ))

                # Check for keyboard escape / modal dismissal
                if re.search(r"""(keydown|Escape|onClose|dismiss|backdrop)""", code):
                    contracts.append(DomainContract(
                        category="UX_INTERACTION",
                        name=f"{Path(rel_path).stem}_dismiss_interaction",
                        description=f"Preserve modal backdrop click & Escape key dismissal in {rel_path}",
                    ))

                # Check for responsive mobile classes
                if re.search(r"\b(sm:|md:|lg:|xl:|@media|mobile)\b", code):
                    contracts.append(DomainContract(
                        category="UX_RESPONSIVE",
                        name=f"{Path(rel_path).stem}_responsive_layout",
                        description=f"Maintain responsive mobile/desktop viewport layout in {rel_path}",
                    ))
            except Exception:
                pass

        return contracts

    def generate_recommended_invariants(self, prompt: str, files: List[str]) -> List[LockedInvariant]:
        invariants: List[LockedInvariant] = [
            LockedInvariant(
                id="FE-INV-01",
                description="Không làm mất phản hồi trực quan (loading spinner/skeleton) khi người dùng thao tác.",
                rationale="Tránh cảm giác đơ/treo giao diện (zero perceived latency).",
            ),
            LockedInvariant(
                id="FE-INV-02",
                description="Bảo đảm các phím tắt công thái học (Escape, Enter, ArrowUp/Down) và đóng popup ngoài backdrop tiếp tục hoạt động.",
                rationale="Chuẩn công thái học UI/UX và accessibility.",
            ),
            LockedInvariant(
                id="FE-INV-03",
                description="Giữ nguyên layout hiển thị tương thích trên màn hình mobile và tablet.",
                rationale="Ngăn ngừa vỡ viewport hoặc tràn thanh cuộn ngang.",
            ),
        ]
        return invariants

    def generate_targeted_test_plan(self, files: List[str], diff_text: str) -> List[str]:
        steps = [
            "Kiểm tra giao diện trên cả 2 độ phân giải: Mobile (390px) và Desktop (1440px).",
            "Bấm thử nút thao tác chính, kiểm tra trạng thái `disabled` và spinner xuất hiện tức thì.",
        ]
        if "modal" in diff_text.lower() or "dialog" in diff_text.lower():
            steps.append("Mở Modal/Dialog, ấn phím 'Escape' và click ra backdrop ngoài xem popup có đóng êm không.")
        if "input" in diff_text.lower() or "textarea" in diff_text.lower():
            steps.append("Thử gõ văn bản tiếng Việt có dấu (IME: telex/vni) xem có bị kẹt chữ hoặc mất focus không.")
        return steps
