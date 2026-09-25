"""
Laya ONNX Native Neural Engine.
Embedded System 1 triage runtime using quantized ONNX checkpoints and tokenizers.
Provides high-accuracy, calibrated, non-autoregressive neural classification
without requiring PyTorch or heavy ML dependencies.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import httpx
import numpy as np

# Special token IDs for ModernBERT / Laya
CLS_ID = 50281
SEP_ID = 50282
PAD_ID = 50283
MASK_ID = 50284

QTYPES = {
    "choice": 0,
    "score": 1,
    "noul": 2,
}

MODEL_URLS = {
    "laya-int4": "https://huggingface.co/techtheist/laya-onnx/resolve/main/en/model_int4.onnx",
    "laya-int8": "https://huggingface.co/techtheist/laya-onnx/resolve/main/en/model_int8.onnx",
}

DEFAULT_MODEL = "laya-int4"  # 262MB single-file quantized checkpoint


def get_laya_model_dir() -> Path:
    """Return local directory for cached Laya neural model weights."""
    model_dir = Path.home() / ".guard" / "models" / "laya"
    model_dir.mkdir(parents=True, exist_ok=True)
    return model_dir


def get_model_path(model_name: str = DEFAULT_MODEL) -> Path:
    """Get absolute path to local ONNX model file."""
    norm_name = "model_int4.onnx" if "int4" in model_name.lower() else "model_int8.onnx"
    return get_laya_model_dir() / norm_name


def get_assets_dir() -> Path:
    """Get path to embedded assets directory."""
    return Path(__file__).resolve().parent.parent / "assets" / "laya"


def is_model_installed(model_name: str = DEFAULT_MODEL) -> bool:
    """Check if model weight file exists locally."""
    p = get_model_path(model_name)
    return p.is_file() and p.stat().st_size > 10_000_000  # At least 10MB


def download_laya_model(
    model_name: str = DEFAULT_MODEL,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Path:
    """
    Download quantized ONNX model weights from HuggingFace.
    Streams download into .tmp file and renames atomically upon completion.
    """
    key = "laya-int4" if "int4" in model_name.lower() else "laya-int8"
    url = MODEL_URLS[key]
    dest_path = get_model_path(key)
    tmp_path = dest_path.with_suffix(".tmp")

    headers = {"User-Agent": "laya-ocr-guard/0.5.0"}
    with httpx.stream("GET", url, headers=headers, follow_redirects=True, timeout=120.0) as resp:
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to download Laya ONNX model from {url}: HTTP {resp.status_code}")

        total_bytes = int(resp.headers.get("content-length", 0))
        downloaded = 0

        with open(tmp_path, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total_bytes)

    if tmp_path.exists():
        if dest_path.exists():
            dest_path.unlink()
        tmp_path.rename(dest_path)

    return dest_path


class LayaONNXRuntime:
    """
    In-process ONNX Runtime session for Laya System 1 Triage.
    Caches session and tokenizer in memory.
    """

    _session = None
    _tokenizer = None
    _rl_config = None
    _loaded_model: Optional[str] = None

    @classmethod
    def load_tokenizer(cls):
        if cls._tokenizer is None:
            from tokenizers import Tokenizer
            tok_file = get_assets_dir() / "tokenizer.json"
            if not tok_file.exists():
                raise FileNotFoundError(f"Missing Laya tokenizer asset at {tok_file}")
            cls._tokenizer = Tokenizer.from_file(str(tok_file))
        return cls._tokenizer

    @classmethod
    def load_rl_config(cls) -> Dict[str, Any]:
        if cls._rl_config is None:
            cfg_file = get_assets_dir() / "rl_agent_config.json"
            if cfg_file.exists():
                cls._rl_config = json.loads(cfg_file.read_text(encoding="utf-8"))
            else:
                cls._rl_config = {}
        return cls._rl_config

    @classmethod
    def get_session(cls, model_name: str = DEFAULT_MODEL, device: str = "cpu"):
        norm_key = "laya-int4" if "int4" in model_name.lower() else "laya-int8"
        if cls._session is not None and cls._loaded_model == norm_key:
            return cls._session

        import onnxruntime as ort

        model_file = get_model_path(norm_key)
        if not model_file.exists():
            raise FileNotFoundError(
                f"Laya ONNX model not found at {model_file}. Run 'guard laya download' or allow auto-download."
            )

        available = ort.get_available_providers()
        providers = (
            ["CUDAExecutionProvider", "CPUExecutionProvider"]
            if device.lower() in ("gpu", "cuda") and "CUDAExecutionProvider" in available
            else ["CPUExecutionProvider"]
        )

        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        sess_options.intra_op_num_threads = min(os.cpu_count() or 4, 8)

        cls._session = ort.InferenceSession(str(model_file), sess_options=sess_options, providers=providers)
        cls._loaded_model = norm_key
        return cls._session

    @classmethod
    def build_sequence(
        cls,
        tokenizer,
        qtype_str: str,
        instructions: str,
        options: List[str],
        state: str,
        max_len: int = 512,
        head_max_len: int = 192,
    ) -> Tuple[List[int], List[int]]:
        """
        Format sequence according to Laya specification:
        [CLS] <type> question: <instructions> [SEP] [MASK] opt0 [MASK] opt1 ... [SEP] <state> [SEP]
        """
        head_ids = [i for i in tokenizer.encode(f"{qtype_str} question: {instructions}").ids if i not in (CLS_ID, SEP_ID)]

        opt_ids_list = []
        for opt in options:
            opt_ids = [i for i in tokenizer.encode(" " + str(opt)).ids if i not in (CLS_ID, SEP_ID)]
            opt_ids_list.append([MASK_ID] + opt_ids[:48])

        # Enforce budget for option tokens
        opt_budget = head_max_len - sum(len(o) for o in opt_ids_list)
        if opt_budget < 16:
            per = max(4, (head_max_len - 16) // max(1, len(opt_ids_list)))
            opt_ids_list = [o[:per] for o in opt_ids_list]
            opt_budget = head_max_len - sum(len(o) for o in opt_ids_list)

        head_ids = head_ids[: max(8, opt_budget)]
        ids = [CLS_ID] + head_ids + [SEP_ID]

        markers = []
        for opt_ids in opt_ids_list:
            markers.append(len(ids))
            ids.extend(opt_ids)
        ids.append(SEP_ID)

        state_ids = [i for i in tokenizer.encode(state).ids if i not in (CLS_ID, SEP_ID)]
        room = max(0, max_len - len(ids) - 1)
        ids = ids + state_ids[:room] + [SEP_ID]

        final_ids = ids[:max_len]
        valid_markers = [m for m in markers if m < max_len]
        return final_ids, valid_markers

    @classmethod
    def predict_questions(
        cls,
        state: str,
        questions: Dict[str, Dict[str, Any]],
        model_name: str = DEFAULT_MODEL,
        device: str = "cpu",
    ) -> Dict[str, Dict[str, Any]]:
        """
        Evaluate batch of typed questions in a single forward pass through ONNX Runtime.
        """
        tokenizer = cls.load_tokenizer()
        session = cls.get_session(model_name=model_name, device=device)
        rl_cfg = cls.load_rl_config()
        temp_by_opts = rl_cfg.get("temperature_by_options", {})

        q_items = []
        max_seq_len = 0
        max_markers_len = 0

        for qid, qdef in questions.items():
            qtype_str = qdef.get("type", "choice")
            instructions = qdef.get("instructions", "")
            options = qdef.get("options", [])
            qtype_code = QTYPES.get(qtype_str, 0)

            seq, markers = cls.build_sequence(
                tokenizer=tokenizer,
                qtype_str=qtype_str,
                instructions=instructions,
                options=options,
                state=state,
            )
            max_seq_len = max(max_seq_len, len(seq))
            max_markers_len = max(max_markers_len, len(markers))
            q_items.append({
                "qid": qid,
                "qtype_str": qtype_str,
                "qtype_code": qtype_code,
                "options": options,
                "seq": seq,
                "markers": markers,
            })

        batch_size = len(q_items)
        if batch_size == 0:
            return {}

        # Pad batch tensors
        input_ids = np.full((batch_size, max_seq_len), PAD_ID, dtype=np.int64)
        attention_mask = np.zeros((batch_size, max_seq_len), dtype=np.int64)
        marker_pos = np.zeros((batch_size, max_markers_len), dtype=np.int64)
        marker_mask = np.zeros((batch_size, max_markers_len), dtype=bool)
        qtype = np.zeros((batch_size,), dtype=np.int64)

        for i, item in enumerate(q_items):
            seq = item["seq"]
            markers = item["markers"]
            input_ids[i, :len(seq)] = seq
            attention_mask[i, :len(seq)] = 1
            marker_pos[i, :len(markers)] = markers
            marker_mask[i, :len(markers)] = True
            qtype[i] = item["qtype_code"]

        ort_inputs = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "marker_pos": marker_pos,
            "marker_mask": marker_mask,
            "qtype": qtype,
        }

        ort_outs = session.run(["logits", "act_logits"], ort_inputs)
        logits = ort_outs[0]  # shape: [batch_size, max_markers_len]

        answers: Dict[str, Dict[str, Any]] = {}

        for i, item in enumerate(q_items):
            qid = item["qid"]
            qtype_str = item["qtype_str"]
            opts = item["options"]
            num_opts = len(opts)
            valid_logits = logits[i, :num_opts]

            # Temperature scaling for calibrated probability
            temp_key = f"{qtype_str}:{num_opts}"
            temperature = float(temp_by_opts.get(temp_key, 1.5))
            temperature = max(0.5, min(5.0, temperature))

            scaled_logits = valid_logits / temperature
            exp_logits = np.exp(scaled_logits - np.max(scaled_logits))
            probs = exp_logits / np.sum(exp_logits)

            best_idx = int(np.argmax(probs))
            confidence = float(probs[best_idx])
            best_opt = opts[best_idx] if best_idx < len(opts) else ""

            answers[qid] = {
                "choice": best_opt,
                "index": best_idx,
                "confidence": confidence,
                "probs": probs.tolist(),
            }

        return answers
