# src/tests/analysis/analysis_eval/test_analysis.py
"""
7개 분석 에이전트 평가 테스트

각 분석 에이전트의 LLM 출력(보고서)을 DeepEval의 커스텀 G-Eval 메트릭으로 채점합니다.

[핵심 설계]
- 각 테스트 케이스마다 metric.measure(test_case) 개별 호출
- evaluate() 일괄 실행 대신 개별 호출로 메트릭별 score/reason 즉시 수집
- 실패한 메트릭만 재실행하거나 디버깅하기 용이

[실행 방법]
set PYTHONIOENCODING=utf-8 && uv run deepeval test run src/tests/analysis/analysis_eval/test_analysis.py -v > test_analysis_results.txt 2>&1
"""

import pytest
from deepeval.test_case import LLMTestCase
from .custom_metrics import (
    get_metrics_for_type,
    calculate_weighted_score,
    get_primary_metric,
)
from .conftest import load_dataset, GLOBAL_RESULTS


# ============================================================
# 평가 실행 핵심 함수
# ============================================================
def run_evaluation_for_agent(agent_name: str, e2e_result: dict):
    """
    특정 분석 에이전트의 데이터셋을 로드하고 평가를 실행합니다.

    [핵심] 각 테스트 케이스마다 metric.measure(test_case) 개별 호출
    -> evaluate() 일괄 실행 대신 메트릭별 결과를 세밀하게 수집

    Args:
        agent_name: 에이전트 식별자 (예: "housing_faq")
        e2e_result: conftest에서 주입된 서버 파이프라인 전체 실행 결과 객체
    """
    dataset = load_dataset(agent_name)
    summary = {"agent": agent_name, "results": []}

    # e2e_result에서 이 에이전트의 결과물 추출
    # 예: e2e_result["housing_faq_output"]["result"]
    output_key = f"{agent_name}_output"
    
    # 서버 결과 형식 검증
    if output_key not in e2e_result or "result" not in e2e_result[output_key]:
        pytest.fail(f"서버 결과에 {output_key}['result'] 데이터가 없습니다.")
        
    actual_agent_record = e2e_result[output_key]["result"]

    # 유형별로 테스트 케이스 그룹핑
    cases_by_type: dict[str, list[tuple]] = {}
    for item in dataset:
        q_type = item.get("type", "analysis_report")
        test_case = LLMTestCase(
            input=item["input"],
            # JSON의 모의 답안 대신 실제 서버에서 생산된 문자열 지정!
            actual_output=actual_agent_record,
        )
        cases_by_type.setdefault(q_type, []).append((test_case, item))

    # 유형별 평가 수행
    for question_type, case_list in cases_by_type.items():
        metrics = get_metrics_for_type(question_type)
        primary_metric_name = get_primary_metric(question_type)

        type_scores = []
        for test_case, q_info in case_list:
            metric_scores = {}

            # [핵심] 개별 채점(measure) 수행
            for metric in metrics:
                metric.measure(test_case)
                metric_scores[metric.name] = metric.score if metric.score else 0.0

            weighted_score = calculate_weighted_score(question_type, metric_scores)
            type_scores.append(weighted_score)

            # 결과 출력
            q_id = q_info.get("id", "unknown")
            q_desc = q_info.get("description", "")
            print(f"  * [{q_id}] {q_desc}")
            print(f"    - 입력: {test_case.input}")
            print(f"    - 실제 서버 출력:\n{test_case.actual_output}\n")
            print(f"    - 가중 점수: {weighted_score:.2%}")

            for metric in metrics:
                marker = " [주요]" if metric.name == primary_metric_name else ""
                print(f"    - {metric.name}{marker}: {metric.score:.2f}")
                if metric.name == primary_metric_name and metric.reason:
                    print(f"    - 판단 이유: {metric.reason}")

        if type_scores:
            type_avg = sum(type_scores) / len(type_scores)
            summary["results"].append({
                "type": question_type,
                "score": type_avg,
                "count": len(type_scores),
            })

    GLOBAL_RESULTS.append(summary)

    # 전체 평균 점수 계산 및 assertion
    # assert 조건, 메세지: 지정된 조건이 참(True)이면 통과, 거짓(False)일 때만 에러 메시지를 발생
    all_scores = [r["score"] for r in summary["results"]]
    if all_scores:
        overall_avg = sum(all_scores) / len(all_scores)
        assert overall_avg >= 0.7, (
            f"{agent_name} 전체 평균 점수 {overall_avg:.2%}로 "
            f"기준(70%) 미달"
        )


# ============================================================
# 에이전트별 테스트 함수
# ============================================================
def test_housing_faq(e2e_result):
    """청약 FAQ 분석 에이전트 평가"""
    run_evaluation_for_agent("housing_faq", e2e_result)


def test_policy(e2e_result):
    """정책 분석 에이전트 평가"""
    run_evaluation_for_agent("policy", e2e_result)


def test_supply_demand(e2e_result):
    """수급 분석 에이전트 평가"""
    run_evaluation_for_agent("supply_demand", e2e_result)


def test_nearby_market(e2e_result):
    """주변 시장 분석 에이전트 평가"""
    run_evaluation_for_agent("nearby_market", e2e_result)


def test_location_insight(e2e_result):
    """입지 분석 에이전트 평가"""
    run_evaluation_for_agent("location_insight", e2e_result)


def test_population_insight(e2e_result):
    """인구 분석 에이전트 평가"""
    run_evaluation_for_agent("population_insight", e2e_result)


def test_unsold_insight(e2e_result):
    """미분양 분석 에이전트 평가"""
    run_evaluation_for_agent("unsold_insight", e2e_result)
