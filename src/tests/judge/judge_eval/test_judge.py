# src/tests/judge/judge_eval/test_judge.py
"""
보고서 컴플리트니스 검수자(Judge) 기능 테스트

[실행]
set PYTHONIOENCODING=utf-8 && uv run deepeval test run src/tests/judge/judge_eval/test_judge.py -v > test_judge_results.txt 2>&1
"""

from deepeval.test_case import LLMTestCase
from .custom_metrics import get_all_metrics
from .conftest import load_judge_dataset, GLOBAL_RESULTS
from tests.format_utils import print_module_header, print_case_result, append_detail


def test_judge_accuracy():
    """초안에 대한 누락 섹션 및 검색어 도출(검수) 능력 평가"""
    dataset = load_judge_dataset()
    scores = []

    print_module_header("검수자(Judge)", len(dataset))

    for item in dataset:
        metrics = get_all_metrics()
        tc = LLMTestCase(input=item["input"], actual_output=item["actual_output"])

        metric_scores = {}
        for m in metrics:
            metric_scores[m.name] = m.measure(tc)

        avg = sum(metric_scores.values()) / len(metric_scores)
        rounded_avg = round(avg, 4)
        scores.append(rounded_avg)

        q_id = item.get("id", "unknown")
        q_desc = item.get("description", "")
        primary = metrics[0]

        print_case_result(
            case_id=q_id,
            description=q_desc,
            input_text=item["input"],
            output_text=item["actual_output"],
            score=avg,
            reason=primary.reason,
        )

        append_detail("judge", {
            "id": q_id,
            "description": q_desc,
            "input": item["input"],
            "output": item["actual_output"],
            "score": rounded_avg,
            "reason": primary.reason,
        })

        GLOBAL_RESULTS.append({"id": q_id, "score": rounded_avg})

    if scores:
        overall = sum(scores) / len(scores)
        rounded_overall = round(overall, 4)
        assert rounded_overall >= 0.7, f"검수 성능 평균 {overall:.2%}로 기준(70%) 미달"
