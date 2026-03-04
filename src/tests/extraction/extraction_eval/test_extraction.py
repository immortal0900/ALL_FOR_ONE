# src/tests/extraction/extraction_eval/test_extraction.py
"""
데이터 추출/필터링 평가 테스트

[실행]
set PYTHONIOENCODING=utf-8 && uv run deepeval test run src/tests/extraction/extraction_eval/test_extraction.py -v > test_extraction_results.txt 2>&1
"""

from deepeval.test_case import LLMTestCase
from .custom_metrics import get_all_metrics
from .conftest import load_extraction_dataset, GLOBAL_RESULTS


def test_extraction():
    """데이터 추출 정확성 평가"""
    dataset = load_extraction_dataset()
    metrics = get_all_metrics()
    scores = []

    for item in dataset:
        tc = LLMTestCase(input=item["input"], actual_output=item["actual_output"])
        item_scores = {}
        for m in metrics:
            m.measure(tc)
            item_scores[m.name] = m.score if m.score else 0.0

        avg = sum(item_scores.values()) / len(item_scores)
        scores.append(avg)
        q_id = item.get("id", "unknown")
        print(f"  * [{q_id}] 점수: {avg:.2%}")
        for m in metrics:
            print(f"    - {m.name}: {m.score:.2f}")
            if m.reason:
                print(f"    - 판단 이유: {m.reason}")
        GLOBAL_RESULTS.append({"id": q_id, "score": avg})

    if scores:
        overall = sum(scores) / len(scores)
        assert overall >= 0.7, f"추출 평균 {overall:.2%}로 기준(70%) 미달"
