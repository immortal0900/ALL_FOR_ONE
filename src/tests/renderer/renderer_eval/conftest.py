# src/tests/renderer/renderer_eval/conftest.py
"""PPT 변환 평가 — pytest fixture"""

import json, os

DATASETS_DIR = os.path.join(os.path.dirname(__file__), "datasets")
GLOBAL_RESULTS = []


def load_renderer_dataset():
    with open(os.path.join(DATASETS_DIR, "renderer.json"), "r", encoding="utf-8") as f:
        return json.load(f)