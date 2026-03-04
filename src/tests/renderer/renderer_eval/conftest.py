# src/tests/renderer/renderer_eval/conftest.py
"""PPT 변환 평가 — pytest fixture"""

import json, os, pytest

DATASETS_DIR = os.path.join(os.path.dirname(__file__), "datasets")
GLOBAL_RESULTS = []


def load_renderer_dataset():
    with open(os.path.join(DATASETS_DIR, "renderer.json"), "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session", autouse=True)
def print_summary(request):
    yield
    if not GLOBAL_RESULTS:
        return
    print("\n" + "=" * 70)
    print("  PPT 변환 DeepEval 평가 종합 리포트")
    print("=" * 70)
    for r in GLOBAL_RESULTS:
        status = "PASS" if r["score"] >= 0.7 else "FAIL"
        print(f"  [{status}] {r['id']}: {r['score']:.2%}")
    print("=" * 70)
