# src/tests/final_report/report_eval/test_final_report.py
"""
최종 보고서(jung_min_jae) 평가 테스트

E2E 서버가 생산한 실제 최종 보고서(e2e_result["final_report"])를 평가합니다.

[실행 방법]
set PYTHONIOENCODING=utf-8 && uv run deepeval test run src/tests/final_report/report_eval/test_final_report.py -v > test_final_report_results.txt 2>&1
"""

import pytest
from deepeval.test_case import LLMTestCase
from .custom_metrics import get_all_metrics, calculate_weighted_score, PRIMARY_METRIC
from .conftest import GLOBAL_RESULTS
from tests.format_utils import print_module_header, print_case_result, append_detail


def _format_input_from_e2e(start_input: dict) -> str:
    """e2e_result의 start_input을 평가용 input 문자열로 변환합니다."""
    target = start_input.get("target_area", "")
    main_type = start_input.get("main_type", "")
    units = start_input.get("total_units", "")
    return (
        f"[사업지] {target}\n"
        f"[주력 타입] {main_type}\n"
        f"[세대수] {units}세대\n"
        f"[요청] 위 사업지에 대한 분양성 검토 최종 보고서를 작성하시오."
    )


def test_final_report(e2e_result):
    """E2E 서버가 생산한 최종 분양성 검토 보고서 평가"""
    # E2E 결과에서 실제 최종 보고서 추출
    final_report = e2e_result.get("final_report", "")
    if not final_report:
        pytest.skip("E2E 결과에 'final_report'가 비어 있습니다.")

    # input: 서버에 전달된 사업지 정보
    input_text = _format_input_from_e2e(e2e_result.get("start_input", {}))

    # 팩토리 패턴: 새 메트릭 인스턴스 생성
    metrics = get_all_metrics()

    test_case = LLMTestCase(
        input=input_text,
        actual_output=final_report,
    )

    # metric.measure() 반환값 직접 사용
    metric_scores = {}
    for metric in metrics:
        metric_scores[metric.name] = metric.measure(test_case)

    weighted = calculate_weighted_score(metric_scores)

    # 주요 메트릭의 판단 이유 추출
    primary = next((m for m in metrics if m.name == PRIMARY_METRIC), metrics[0])

    print_module_header("최종 보고서(Final Report)", 1)
    print_case_result(
        case_id="e2e_final_report",
        description="E2E 서버 생산 최종 분양성 검토 보고서",
        input_text=input_text,
        output_text=final_report,
        score=weighted,
        reason=primary.reason,
    )

    append_detail("final_report", {
        "id": "e2e_final_report",
        "input": input_text,
        "output": final_report,
        "score": weighted,
        "metric_scores": metric_scores,
        "reason": primary.reason,
    })

    GLOBAL_RESULTS.append({"id": "e2e_final_report", "score": weighted})

    assert weighted >= 0.7, f"최종 보고서 점수 {weighted:.2%}로 기준(70%) 미달"
