# src/tests/extraction/extraction_eval/conftest.py
"""데이터 추출 평가 — pytest fixture"""

import json, os

DATASETS_DIR = os.path.join(os.path.dirname(__file__), "datasets")
GLOBAL_RESULTS = []


def load_extraction_dataset() -> list[dict]:
    with open(os.path.join(DATASETS_DIR, "extraction.json"), "r", encoding="utf-8") as f:
        return json.load(f)
