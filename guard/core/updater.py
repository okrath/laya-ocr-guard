"""
Supply-Chain Security & Update Quarantine Checker for Alibaba Open Code Review (OCR).
Monitors `@alibaba-group/open-code-review` releases on the npm registry.

Implements Supply-Chain Backdoor Protection (Quarantine Period):
- New releases < 2-3 days old are put on QUARANTINE HOLD to allow
  the open-source security community to detect malicious code/backdoors.
- Only releases >= 3 days old are marked SAFE TO UPGRADE.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Tuple

import httpx
from pydantic import BaseModel, Field


class UpdateSecurityStatus(str, Enum):
    UP_TO_DATE = "UP_TO_DATE"
    QUARANTINE_HOLD = "QUARANTINE_HOLD"
    SAFE_UPDATE_AVAILABLE = "SAFE_UPDATE_AVAILABLE"
    NOT_INSTALLED = "NOT_INSTALLED"
    CHECK_FAILED = "CHECK_FAILED"


class VersionCheckResult(BaseModel):
    package_name: str
    registry: str = "npm"
    installed_version: Optional[str] = None
    latest_version: Optional[str] = None
    release_date: Optional[str] = None
    age_days: Optional[float] = None
    status: UpdateSecurityStatus
    recommendation: str


def parse_version_tuple(ver_str: str) -> Tuple[int, ...]:
    """Parse version string into tuple of integers for comparison (e.g. '1.12.9' -> (1, 12, 9))."""
    nums = re.findall(r"\d+", ver_str)
    return tuple(int(n) for n in nums) if nums else (0,)


def is_version_newer(latest: str, current: str) -> bool:
    try:
        return parse_version_tuple(latest) > parse_version_tuple(current)
    except Exception:
        return latest != current


def get_installed_ocr_version() -> Optional[str]:
    ocr_bin = shutil.which("ocr")
    if not ocr_bin:
        return None
    try:
        res = subprocess.run([ocr_bin, "--version"], capture_output=True, text=True, timeout=5)
        nums = re.findall(r"\d+\.\d+\.\d+", res.stdout + res.stderr)
        return nums[0] if nums else "installed"
    except Exception:
        return "installed"


def check_ocr_update(quarantine_days: float = 3.0, timeout: float = 4.0) -> VersionCheckResult:
    """
    Check npm registry for `@alibaba-group/open-code-review` and verify against quarantine period.
    """
    installed = get_installed_ocr_version()
    package_name = "@alibaba-group/open-code-review"
    registry = "npm"

    try:
        with httpx.Client(timeout=timeout) as client:
            res = client.get("https://registry.npmjs.org/@alibaba-group%2Fopen-code-review")
            if res.status_code != 200:
                return VersionCheckResult(
                    package_name=package_name,
                    registry=registry,
                    installed_version=installed,
                    status=UpdateSecurityStatus.CHECK_FAILED,
                    recommendation=f"HTTP {res.status_code} khi kiểm tra npm registry",
                )
            data = res.json()
            latest = data.get("dist-tags", {}).get("latest", "")
            times = data.get("time", {})
            upload_iso = times.get(latest)

            age_days: Optional[float] = None
            date_display = "Không rõ"
            if upload_iso:
                rel_dt = datetime.fromisoformat(upload_iso.replace("Z", "+00:00"))
                now_dt = datetime.now(timezone.utc)
                age_days = (now_dt - rel_dt).total_seconds() / 86400.0
                date_display = rel_dt.strftime("%Y-%m-%d %H:%M UTC")

            if not installed:
                return VersionCheckResult(
                    package_name=package_name,
                    registry=registry,
                    installed_version=None,
                    latest_version=latest,
                    release_date=date_display,
                    age_days=age_days,
                    status=UpdateSecurityStatus.NOT_INSTALLED,
                    recommendation="Tùy chọn: cài bằng `npm install -g @alibaba-group/open-code-review`.",
                )

            if installed == "installed" or not is_version_newer(latest, installed):
                return VersionCheckResult(
                    package_name=package_name,
                    registry=registry,
                    installed_version=installed,
                    latest_version=latest,
                    release_date=date_display,
                    age_days=age_days,
                    status=UpdateSecurityStatus.UP_TO_DATE,
                    recommendation="Đã cài đặt bản mới nhất hoặc bản hiện hành ổn định.",
                )

            # Newer version on npm! Check quarantine period
            if age_days is not None and age_days < quarantine_days:
                return VersionCheckResult(
                    package_name=package_name,
                    registry=registry,
                    installed_version=installed,
                    latest_version=latest,
                    release_date=date_display,
                    age_days=age_days,
                    status=UpdateSecurityStatus.QUARANTINE_HOLD,
                    recommendation=f"🛡️ CÁCH LY BẢO MẬT: v{latest} mới ra mắt {age_days:.1f} ngày (< {quarantine_days:.0f} ngày). Giữ v{installed} để chờ kiểm chứng cộng đồng (chống backdoor).",
                )

            return VersionCheckResult(
                package_name=package_name,
                registry=registry,
                installed_version=installed,
                latest_version=latest,
                release_date=date_display,
                age_days=age_days,
                status=UpdateSecurityStatus.SAFE_UPDATE_AVAILABLE,
                recommendation=f"⬆️ Nâng cấp an toàn (Đã phát hành {age_days:.1f} ngày trước): `npm install -g {package_name}`",
            )

    except Exception as e:
        return VersionCheckResult(
            package_name=package_name,
            registry=registry,
            installed_version=installed,
            status=UpdateSecurityStatus.CHECK_FAILED,
            recommendation=f"Không thể kiểm tra npm ({str(e)[:60]})",
        )
