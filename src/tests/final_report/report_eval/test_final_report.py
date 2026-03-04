# src/tests/final_report/report_eval/test_final_report.py
"""
최종 보고서(jung_min_jae) 평가 테스트

[실행 방법]
set PYTHONIOENCODING=utf-8 && uv run deepeval test run src/tests/final_report/report_eval/test_final_report.py -v > test_final_report_results.txt 2>&1
"""

import pytest
from deepeval.test_case import LLMTestCase
from .custom_metrics import get_all_metrics, calculate_weighted_score, PRIMARY_METRIC
from .conftest import load_final_report_dataset, GLOBAL_RESULTS


def test_final_report():
    """최종 분양성 검토 보고서 평가"""
    dataset = load_final_report_dataset()
    metrics = get_all_metrics()

    all_scores = []
    for item in dataset:
        test_case = LLMTestCase(
            input=item["input"],
            actual_output=item["actual_output"],
        )

        metric_scores = {}
        for metric in metrics:
            metric.measure(test_case)
            metric_scores[metric.name] = metric.score if metric.score else 0.0

        weighted = calculate_weighted_score(metric_scores)
        all_scores.append(weighted)

        q_id = item.get("id", "unknown")
        print(f"  * [{q_id}] 가중 점수: {weighted:.2%}")
        for metric in metrics:
            marker = " [주요]" if metric.name == PRIMARY_METRIC else ""
            print(f"    - {metric.name}{marker}: {metric.score:.2f}")
            if metric.name == PRIMARY_METRIC and metric.reason:
                print(f"    - 판단 이유: {metric.reason}")

        GLOBAL_RESULTS.append({"id": q_id, "score": weighted})

    if all_scores:
        avg = sum(all_scores) / len(all_scores)
        assert avg >= 0.7, f"최종 보고서 평균 {avg:.2%}로 기준(70%) 미달"
