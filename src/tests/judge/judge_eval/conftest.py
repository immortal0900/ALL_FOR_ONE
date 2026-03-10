# src/tests/judge/judge_eval/conftest.py
"""보고서 평가자(Judge) 테스트용 pytest fixture"""

import json
import os
DATASETS_DIR = os.path.join(os.path.dirname(__file__), "datasets")
GLOBAL_RESULTS = []


def load_judge_dataset() -> list[dict]:
    filepath = os.path.join(DATASETS_DIR, "judge.json")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
