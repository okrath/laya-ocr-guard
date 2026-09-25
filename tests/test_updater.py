"""
Unit tests for Supply-Chain Security & Update Quarantine Checker.
"""

from unittest.mock import MagicMock, patch
import pytest

from guard.core.updater import (
    UpdateSecurityStatus,
    check_laya_update,
    check_ocr_update,
    is_version_newer,
    parse_version_tuple,
)


def test_parse_version_tuple():
    assert parse_version_tuple("0.3.20") == (0, 3, 20)
    assert parse_version_tuple("1.12.9") == (1, 12, 9)
    assert parse_version_tuple("2.0.0-rc1") == (2, 0, 0, 1)


def test_is_version_newer():
    assert is_version_newer("0.3.20", "0.3.19") is True
    assert is_version_newer("0.3.20", "0.3.20") is False
    assert is_version_newer("0.3.19", "0.3.20") is False
    assert is_version_newer("1.13.0", "1.12.9") is True


def test_laya_update_quarantine_hold():
    # Mock PyPI response for a release published only 1.0 day ago
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "info": {"version": "0.4.0"},
        "releases": {
            "0.4.0": [{"upload_time_iso_8601": "2026-09-24T12:00:00Z"}]
        }
    }

    with patch("httpx.Client.get", return_value=mock_response), \
         patch("guard.core.updater.get_installed_laya_version", return_value="0.3.20"):
        res = check_laya_update(quarantine_days=3.0)
        assert res.status == UpdateSecurityStatus.QUARANTINE_HOLD
        assert "CÁCH LY BẢO MẬT" in res.recommendation


def test_laya_update_safe_available():
    # Mock PyPI response for a release published 5.0 days ago
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "info": {"version": "0.4.0"},
        "releases": {
            "0.4.0": [{"upload_time_iso_8601": "2026-09-20T12:00:00Z"}]
        }
    }

    with patch("httpx.Client.get", return_value=mock_response), \
         patch("guard.core.updater.get_installed_laya_version", return_value="0.3.20"):
        res = check_laya_update(quarantine_days=3.0)
        assert res.status == UpdateSecurityStatus.SAFE_UPDATE_AVAILABLE
        assert "Nâng cấp an toàn" in res.recommendation


def test_laya_update_up_to_date():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "info": {"version": "0.3.20"},
        "releases": {
            "0.3.20": [{"upload_time_iso_8601": "2026-09-20T12:00:00Z"}]
        }
    }

    with patch("httpx.Client.get", return_value=mock_response), \
         patch("guard.core.updater.get_installed_laya_version", return_value="0.3.20"):
        res = check_laya_update(quarantine_days=3.0)
        assert res.status == UpdateSecurityStatus.UP_TO_DATE


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
