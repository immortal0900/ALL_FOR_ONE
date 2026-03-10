# src/tests/source/source_eval/conftest.py
"""출처 추출 평가 — pytest fixture"""

import json, os

DATASETS_DIR = os.path.join(os.path.dirname(__file__), "datasets")
GLOBAL_RESULTS = []


def load_source_dataset():
    with open(os.path.join(DATASETS_DIR, "source.json"), "r", encoding="utf-8") as f:
        return json.load(f)
