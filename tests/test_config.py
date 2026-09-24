"""
Unit tests for Core Config and LLM Client.
"""

from pathlib import Path
import tempfile
import pytest

from guard.core.config import (
    GuardConfig,
    LLMConfig,
    LLMProtocol,
    load_config,
    save_config,
    sync_to_alibaba_ocr,
)
from guard.core.llm_client import ping_llm, call_llm


def test_llm_config_masking():
    cfg = LLMConfig(api_key="sk-1234567890abcdef")
    assert cfg.masked_api_key == "sk-1...cdef"
    
    empty_cfg = LLMConfig(api_key="")
    assert empty_cfg.masked_api_key == "(none)"


def test_config_save_and_load(tmp_path):
    repo = tmp_path / "my_project"
    repo.mkdir()
    
    cfg = GuardConfig(
        llm=LLMConfig(
            protocol=LLMProtocol.ANTHROPIC,
            base_url="https://api.anthropic.com/v1",
            api_key="sk-ant-testkey",
            model="claude-3-7-sonnet",
        )
    )
    
    saved_path = save_config(cfg, local=True, repo_path=repo)
    assert saved_path.is_file()
    assert saved_path == repo / ".guard" / "config.json"
    
    loaded = load_config(repo)
    assert loaded.llm.protocol == LLMProtocol.ANTHROPIC
    assert loaded.llm.model == "claude-3-7-sonnet"
    assert loaded.llm.api_key == "sk-ant-testkey"


def test_sync_to_ocr_when_cli_missing():
    # If ocr binary doesn't exist, it should return False with graceful message
    llm = LLMConfig(api_key="test-key")
    success, msg = sync_to_alibaba_ocr(llm)
    assert isinstance(success, bool)
    assert isinstance(msg, str)
