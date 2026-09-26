"""
Calibration gate for the Laya neural triage.

The neural model is only trusted after it proves itself on a labelled prompt set: measured on
real repositories the int8 model returned near-uniform probabilities (~0.2 for each of 5 domains)
and scored at chance level, below the keyword reflex engine. `guard laya calibrate` measures the
installed model; triage uses it only when the recorded accuracy for that exact model file
reaches PASS_ACCURACY, otherwise it falls back to the reflex engine.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

PASS_ACCURACY = 0.7

# (prompt, expected domain) written the way users give tasks, in English and Vietnamese
LABELLED_PROMPTS: List[Tuple[str, str]] = [
    ("Fix the modal close button alignment and dark mode colors in Settings.tsx", "frontend"),
    ("Sửa lỗi màu chữ bubble chat ở chế độ sáng trong style.css", "frontend"),
    ("Thêm nút expand cho ô chat input và giữ phím ArrowUp duyệt lịch sử", "frontend"),
    ("Make the landing page responsive on mobile widths", "frontend"),
    ("Add a REST endpoint POST /api/orders with validation", "backend"),
    ("Thêm API /v1/chat/completions hỗ trợ SSE streaming trong proxy", "backend"),
    ("Fix the N+1 query in the user repository and add an index migration", "backend"),
    ("Sửa lỗi CORS header thiếu trên response SSE của gateway", "backend"),
    ("Write a Dockerfile and docker-compose for the service", "infra"),
    ("Thêm GitHub Actions workflow chạy test và deploy lên Cloud Run", "infra"),
    ("Configure nginx reverse proxy and TLS certificates", "infra"),
    ("Add Terraform module for the S3 bucket and IAM role", "infra"),
    ("Build the Flutter login screen and request camera permission on Android", "mobile"),
    ("Sửa crash khi mở màn hình profile trên iOS (SwiftUI)", "mobile"),
    ("Add push notifications to the React Native app", "mobile"),
    ("Add a settings page that saves preferences through a new /api/settings endpoint", "fullstack"),
]


def calibration_file() -> Path:
    return Path.home() / ".guard" / "laya_calibration.json"


def _model_fingerprint(model_path: Path) -> Dict[str, object]:
    st = model_path.stat()
    return {"model_file": str(model_path), "size": st.st_size, "mtime": int(st.st_mtime)}


def neural_is_calibrated(model_path: Optional[Path]) -> bool:
    """True only when this exact model file passed calibration."""
    if model_path is None or not model_path.is_file():
        return False
    try:
        record = json.loads(calibration_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    fp = _model_fingerprint(model_path)
    return bool(record.get("passed")) and all(record.get(k) == v for k, v in fp.items())


def calibrate(model_path: Path, classify: Callable[[str], str]) -> Dict[str, object]:
    """Run the labelled prompts through `classify`, record and return the result."""
    rows = []
    start = time.perf_counter()
    for prompt, expected in LABELLED_PROMPTS:
        got = classify(prompt)
        rows.append({"prompt": prompt, "expected": expected, "got": got})
    correct = sum(r["expected"] == r["got"] for r in rows)
    record = {
        **_model_fingerprint(model_path),
        "accuracy": correct / len(rows),
        "correct": correct,
        "total": len(rows),
        "passed": correct / len(rows) >= PASS_ACCURACY,
        "threshold": PASS_ACCURACY,
        "seconds": round(time.perf_counter() - start, 1),
        "misses": [r for r in rows if r["expected"] != r["got"]],
    }
    path = calibration_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record
