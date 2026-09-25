"""
Unit tests for Supply-Chain Security & Update Quarantine Checker (Alibaba OCR).
"""

from unittest.mock import MagicMock, patch
import pytest

from guard.core.updater import (
    UpdateSecurityStatus,
    VersionCheckResult,
    check_ocr_update,
    is_version_newer,
    parse_version_tuple,
    perform_ocr_upgrade,
    perform_self_upgrade,
)


def test_parse_version_tuple():
    assert parse_version_tuple("1.12.9") == (1, 12, 9)
    assert parse_version_tuple("2.0.0-rc1") == (2, 0, 0, 1)


def test_is_version_newer():
    assert is_version_newer("1.13.0", "1.12.9") is True
    assert is_version_newer("1.12.9", "1.12.9") is False
    assert is_version_newer("1.12.8", "1.12.9") is False


def test_ocr_update_quarantine_hold():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "dist-tags": {"latest": "1.13.0"},
        "time": {
            "1.13.0": "2026-09-24T12:00:00Z"
        }
    }

    with patch("httpx.Client.get", return_value=mock_response), \
         patch("guard.core.updater.get_installed_ocr_version", return_value="1.12.9"):
        res = check_ocr_update(quarantine_days=3.0)
        assert res.status == UpdateSecurityStatus.QUARANTINE_HOLD
        assert "CÁCH LY BẢO MẬT" in res.recommendation


def test_ocr_update_safe_available():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "dist-tags": {"latest": "1.13.0"},
        "time": {
            "1.13.0": "2026-09-20T12:00:00Z"
        }
    }

    with patch("httpx.Client.get", return_value=mock_response), \
         patch("guard.core.updater.get_installed_ocr_version", return_value="1.12.9"):
        res = check_ocr_update(quarantine_days=3.0)
        assert res.status == UpdateSecurityStatus.SAFE_UPDATE_AVAILABLE
        assert "Nâng cấp an toàn" in res.recommendation


def test_ocr_update_up_to_date():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "dist-tags": {"latest": "1.12.9"},
        "time": {
            "1.12.9": "2026-09-22T12:00:00Z"
        }
    }

    with patch("httpx.Client.get", return_value=mock_response), \
         patch("guard.core.updater.get_installed_ocr_version", return_value="1.12.9"):
        res = check_ocr_update(quarantine_days=3.0)
        assert res.status == UpdateSecurityStatus.UP_TO_DATE


def test_perform_ocr_upgrade_blocked_by_quarantine():
    mock_check = VersionCheckResult(
        package_name="@alibaba-group/open-code-review",
        registry="npm",
        installed_version="1.12.9",
        latest_version="1.13.0",
        age_days=1.2,
        status=UpdateSecurityStatus.QUARANTINE_HOLD,
        recommendation="Quarantine active",
    )
    with patch("guard.core.updater.check_ocr_update", return_value=mock_check):
        success, msg = perform_ocr_upgrade(force=False, quarantine_days=3.0)
        assert success is False
        assert "CÁCH LY BẢO MẬT" in msg


def test_perform_ocr_upgrade_force_allowed():
    mock_check = VersionCheckResult(
        package_name="@alibaba-group/open-code-review",
        registry="npm",
        installed_version="1.12.9",
        latest_version="1.13.0",
        age_days=1.2,
        status=UpdateSecurityStatus.QUARANTINE_HOLD,
        recommendation="Quarantine active",
    )
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    with patch("guard.core.updater.check_ocr_update", return_value=mock_check), \
         patch("shutil.which", return_value="npm"), \
         patch("subprocess.run", return_value=mock_proc):
        success, msg = perform_ocr_upgrade(force=True, quarantine_days=3.0)
        assert success is True
        assert "Đã nâng cấp thành công" in msg
