# src/tests/judge/judge_eval/conftest.py
"""보고서 평가자(Judge) 테스트용 pytest fixture"""

import json
import os
import pytest

DATASETS_DIR = os.path.join(os.path.dirname(__file__), "datasets")
GLOBAL_RESULTS = []

def load_judge_dataset() -> list[dict]:
    filepath = os.path.join(DATASETS_DIR, "judge.json")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture(scope="session", autouse=True)
def print_summary(request):
    yield
    if not GLOBAL_RESULTS:
        return
    print("\n" + "=" * 70)
    print("  검수자(Judge) DeepEval 평가 종합 리포트")
    print("=" * 70)
    for r in GLOBAL_RESULTS:
        status = "PASS" if r["score"] >= 0.7 else "FAIL"
        print(f"  [{status}] {r['id']}: {r['score']:.2%}")
    print("=" * 70)
