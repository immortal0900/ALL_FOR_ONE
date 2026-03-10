# src/tests/renderer/renderer_eval/test_renderer.py
"""
PPT 변환(renderer) 평가 테스트

[실행]
set PYTHONIOENCODING=utf-8 && uv run deepeval test run src/tests/renderer/renderer_eval/test_renderer.py -v > test_renderer_results.txt 2>&1
"""

from deepeval.test_case import LLMTestCase
from .custom_metrics import get_all_metrics
from .conftest import load_renderer_dataset, GLOBAL_RESULTS
from tests.format_utils import print_module_header, print_case_result, append_detail


def test_renderer():
    """SlidePlan JSON 변환 품질 평가"""
    dataset = load_renderer_dataset()
    scores = []

    print_module_header("PPT 변환(Renderer)", len(dataset))

    for item in dataset:
        metrics = get_all_metrics()
        tc = LLMTestCase(input=item["input"], actual_output=item["actual_output"])

        metric_scores = {}
        for m in metrics:
            metric_scores[m.name] = m.measure(tc)

        avg = sum(metric_scores.values()) / len(metric_scores)
        scores.append(avg)

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

        append_detail("renderer", {
            "id": q_id,
            "description": q_desc,
            "input": item["input"],
            "output": item["actual_output"],
            "score": avg,
            "reason": primary.reason,
        })

        GLOBAL_RESULTS.append({"id": q_id, "score": avg})

    if scores:
        overall = sum(scores) / len(scores)
        assert overall >= 0.7, f"PPT 변환 평균 {overall:.2%}로 기준(70%) 미달"
