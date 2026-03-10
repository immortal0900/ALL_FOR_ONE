# src/tests/final_report/report_eval/conftest.py
"""최종 보고서 평가 — pytest fixture"""

import json
import os

DATASETS_DIR = os.path.join(os.path.dirname(__file__), "datasets")
GLOBAL_RESULTS = []


def load_final_report_dataset() -> list[dict]:
    filepath = os.path.join(DATASETS_DIR, "final_report.json")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
