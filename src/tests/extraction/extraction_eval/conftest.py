# src/tests/extraction/extraction_eval/conftest.py
"""데이터 추출 평가 — pytest fixture"""

import json, os, pytest

DATASETS_DIR = os.path.join(os.path.dirname(__file__), "datasets")
GLOBAL_RESULTS = []


def load_extraction_dataset() -> list[dict]:
    with open(os.path.join(DATASETS_DIR, "extraction.json"), "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session", autouse=True)
def print_summary(request):
    yield
    if not GLOBAL_RESULTS:
        return
    print("\n" + "=" * 70)
    print("  데이터 추출 DeepEval 평가 종합 리포트")
    print("=" * 70)
    for r in GLOBAL_RESULTS:
        status = "PASS" if r["score"] >= 0.7 else "FAIL"
        print(f"  [{status}] {r['id']}: {r['score']:.2%}")
    print("=" * 70)
