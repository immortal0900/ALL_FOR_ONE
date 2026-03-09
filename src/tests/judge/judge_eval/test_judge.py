# src/tests/judge/judge_eval/test_judge.py
"""
보고서 컴플리트니스 검수자(Judge) 기능 테스트

[실행]
set PYTHONIOENCODING=utf-8 && uv run deepeval test run src/tests/judge/judge_eval/test_judge.py -v > test_judge_results.txt 2>&1
"""

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from .custom_metrics import get_all_metrics
from .conftest import load_judge_dataset, GLOBAL_RESULTS


def test_judge_accuracy():
    """초안에 대한 누락 섹션 및 검색어 도출(검수) 능력 평가"""
    dataset = load_judge_dataset()
    scores = []

    for item in dataset:
        # 팩토리 패턴: 매 테스트 케이스마다 새 메트릭 인스턴스 생성
        metrics = get_all_metrics()
        tc = LLMTestCase(input=item["input"], actual_output=item["actual_output"])

        # assert_test: DeepEval에 결과를 공식 등록 (.temp_test_run_data.json 기록)
        try:
            assert_test(tc, metrics)
        except AssertionError:
            pass

        item_scores = {}
        for m in metrics:
            item_scores[m.name] = m.score if m.score else 0.0

        avg = sum(item_scores.values()) / len(item_scores)
        rounded_avg = round(avg, 4)
        scores.append(rounded_avg)
        q_id = item.get("id", "unknown")

        print(f"  * [{q_id}] 점수: {avg:.2%}")
        for m in metrics:
            score_val = m.score if m.score else 0.0
            print(f"    - {m.name}: {score_val:.2f}")
            if m.reason:
                print(f"    - 판단 이유: {m.reason}")

        GLOBAL_RESULTS.append({"id": q_id, "score": rounded_avg})

    if scores:
        overall = sum(scores) / len(scores)
        rounded_overall = round(overall, 4)
        assert rounded_overall >= 0.7, f"검수 성능 평균 {overall:.2%}로 기준(70%) 미달"
