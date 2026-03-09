# src/tests/final_report/report_eval/test_final_report.py
"""
최종 보고서(jung_min_jae) 평가 테스트

E2E 서버가 생산한 실제 최종 보고서(e2e_result["final_report"])를 평가합니다.

[실행 방법]
set PYTHONIOENCODING=utf-8 && uv run deepeval test run src/tests/final_report/report_eval/test_final_report.py -v > test_final_report_results.txt 2>&1
"""

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from .custom_metrics import get_all_metrics, calculate_weighted_score, PRIMARY_METRIC
from .conftest import GLOBAL_RESULTS


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

    # assert_test: DeepEval에 결과를 공식 등록 (.temp_test_run_data.json 기록)
    try:
        assert_test(test_case, metrics)
    except AssertionError:
        pass

    metric_scores = {}
    for metric in metrics:
        metric_scores[metric.name] = metric.score if metric.score else 0.0

    weighted = calculate_weighted_score(metric_scores)

    print(f"\n  * [E2E] 최종 보고서 가중 점수: {weighted:.2%}")
    for metric in metrics:
        marker = " [주요]" if metric.name == PRIMARY_METRIC else ""
        score_val = metric.score if metric.score else 0.0
        print(f"    - {metric.name}{marker}: {score_val:.2f}")
        if metric.name == PRIMARY_METRIC and metric.reason:
            print(f"    - 판단 이유: {metric.reason}")

    GLOBAL_RESULTS.append({"id": "e2e_final_report", "score": weighted})

    assert weighted >= 0.7, f"최종 보고서 점수 {weighted:.2%}로 기준(70%) 미달"
