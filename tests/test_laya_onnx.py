"""
Unit tests for embedded Laya ONNX Native Neural Engine.
"""

from unittest.mock import MagicMock, patch
import numpy as np
import pytest

from guard.core.laya_onnx import (
    DEFAULT_MODEL,
    LayaONNXRuntime,
    get_assets_dir,
    get_laya_model_dir,
    get_model_path,
    is_model_installed,
)
from guard.core.laya_engine import LayaEngine, DomainType, TaskIntent, RiskLevel


def test_laya_model_paths():
    assert DEFAULT_MODEL == "laya-int8"
    p4 = get_model_path("laya-int4")
    p8 = get_model_path("laya-int8")
    assert "model_int4.onnx" in str(p4)
    assert "model_int8.onnx" in str(p8)
    assert get_laya_model_dir().exists()


def test_assets_exist():
    assets_dir = get_assets_dir()
    assert (assets_dir / "tokenizer.json").exists()
    assert (assets_dir / "rl_agent_config.json").exists()


def test_load_tokenizer_and_rl_config():
    tok = LayaONNXRuntime.load_tokenizer()
    assert tok is not None
    assert tok.get_vocab_size() > 10000

    cfg = LayaONNXRuntime.load_rl_config()
    assert isinstance(cfg, dict)
    assert "temperature_by_options" in cfg


def test_build_sequence():
    tok = LayaONNXRuntime.load_tokenizer()
    ids, markers = LayaONNXRuntime.build_sequence(
        tokenizer=tok,
        qtype_str="choice",
        instructions="Which technical domain is affected?",
        options=["frontend", "backend", "infra"],
        state="Fix button CSS alignment",
        max_len=128,
    )
    assert len(ids) > 0
    assert len(markers) == 3
    # Check that markers point to [MASK] token (50284)
    for m in markers:
        assert ids[m] == 50284


def test_mock_predict_questions():
    mock_session = MagicMock()
    # Batch size 2 questions, 3 markers
    # ort_outs = [logits, act_logits]
    fake_logits = np.array([
        [[2.0, 0.5, -1.0]],   # Q1
        [[-0.5, 3.0, 0.2]],   # Q2
    ]).squeeze(1)
    fake_act_logits = np.array([[1.0], [1.0]])
    mock_session.run.return_value = [fake_logits, fake_act_logits]

    questions = {
        "domain": {
            "type": "choice",
            "instructions": "Domain?",
            "options": ["frontend", "backend", "infra"],
        },
        "intent": {
            "type": "choice",
            "instructions": "Intent?",
            "options": ["feature", "bugfix", "refactor"],
        },
    }

    with patch.object(LayaONNXRuntime, "get_session", return_value=mock_session):
        answers = LayaONNXRuntime.predict_questions(
            state="Fix button CSS",
            questions=questions,
            model_name="laya-int4",
        )
        assert "domain" in answers
        assert answers["domain"]["choice"] == "frontend"
        assert answers["domain"]["index"] == 0
        assert answers["domain"]["confidence"] > 0.5

        assert "intent" in answers
        assert answers["intent"]["choice"] == "bugfix"
        assert answers["intent"]["index"] == 1


def test_laya_engine_with_onnx_installed(tmp_path):
    # Simulate installed ONNX model
    fake_model = tmp_path / "model_int8.onnx"
    fake_model.write_bytes(b"0" * 15_000_000)

    mock_answers = {
        "domain": {"choice": "frontend", "index": 0, "confidence": 0.98},
        "intent": {"choice": "bugfix", "index": 1, "confidence": 0.95},
        "risk_level": {"index": 0, "confidence": 0.90},
        "core_breach": {"index": 0, "confidence": 0.99},
    }

    with patch("guard.core.laya_onnx.get_model_path", return_value=fake_model), \
         patch("guard.core.laya_onnx.is_model_installed", return_value=True), \
         patch.object(LayaONNXRuntime, "predict_questions", return_value=mock_answers):
        engine = LayaEngine(model_name="laya-int8")
        assert engine.mode == "laya_onnx_neural"
        res = engine.triage("Center the modal dialog button")
        assert res.domain == DomainType.FRONTEND
        assert res.intent == TaskIntent.BUGFIX
        assert res.risk_level == RiskLevel.LOW
        assert res.core_breach_risk is False
        assert res.engine_mode == "laya_onnx_neural"
        assert "Confidence: 98.0%" in res.reasoning
