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
from tests.analysis.analysis_eval.custom_metrics import (
    get_metrics_for_type,
    calculate_separated_scores,
    get_primary_metric,
)
from tests.analysis.analysis_eval.conftest import load_dataset, GLOBAL_RESULTS


# ============================================================
# Context 추출 헬퍼 함수
# ============================================================
def _extract_retrieval_contexts(agent_name: str, output_dict: dict) -> list[str]:
    """
    각 에이전트 결과 딕셔너리에서 RAG 컨텍스트를 찾아 문자열 리스트로 반환합니다.
    """
    contexts = []
    
    # 에이전트별 키 매핑 테이블 (analysis_outputs_schema 기반)
    CONTEXT_MAPPING = {
        "policy": ["national_context", "region_context", "pdf_context"],
        "housing_faq": ["housing_faq_context", "housing_rule_context"],
        "unsold_insight": ["unsold_unit"],
        "population_insight": ["age_population_context", "move_population_context"],
        "supply_demand": [
            "year10_after_house", "jeonse_price", "sale_price", "trade_balance",
            "use_kor_rate", "home_mortgage", "one_people_gdp", "one_people_grdp",
            "housing_sales_volume", "planning_move", "pre_promise_competition"
        ],
        "location_insight": ["rag_context", "web_context", "kakao_api_distance_context", "gemini_search", "perplexity_search"],
        "nearby_market": ["kakao_api_distance_context", "gemini_search", "real_estate_price_context", "perplexity_search", "rag_context", "web_context"]
    }
    
    keys_to_extract = CONTEXT_MAPPING.get(agent_name, [])
    for key in keys_to_extract:
        val = output_dict.get(key)
        if val and isinstance(val, str) and val.strip():
            contexts.append(val)
        elif val and isinstance(val, list):
            # 문자열 리스트일 경우 안전하게 Join
            joined_str = "\n".join(str(v) for v in val if v)
            if joined_str.strip():
                contexts.append(joined_str)
            
    # 비어 있을 경우 에러를 피하기 위해 기본 컨텍스트 1개라도 주기
    if not contexts:
        contexts.append("문서 검색 기록이 존재하지 않습니다.")
        
    return contexts

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
    # 예: e2e_result["analysis_outputs"]["housing_faq"]["result"]
    if "analysis_outputs" not in e2e_result:
        pytest.fail("서버 결과에 'analysis_outputs' 키가 없습니다.")
        
    outputs = e2e_result["analysis_outputs"]
    if agent_name not in outputs or "result" not in outputs[agent_name]:
        pytest.fail(f"서버 결과에 {agent_name}['result'] 데이터가 없습니다.")
        
    actual_agent_record = outputs[agent_name]["result"]

    # RAG 메트릭 채점을 위해 서버 응답에서 관련 데이터 추출
    retrieval_context = _extract_retrieval_contexts(agent_name, outputs[agent_name])

    # 유형별로 테스트 케이스 그룹핑
    cases_by_type: dict[str, list[tuple]] = {}
    for item in dataset:
        q_type = item.get("type", "analysis_report")
        test_case = LLMTestCase(
            input=item["input"],
            actual_output=actual_agent_record,
            retrieval_context=retrieval_context,
        )
        cases_by_type.setdefault(q_type, []).append((test_case, item))

    # 유형별 평가 수행
    for question_type, case_list in cases_by_type.items():
        metrics = get_metrics_for_type(agent_name)
        primary_metric_name = get_primary_metric(agent_name)

        type_scores = []
        for test_case, q_info in case_list:
            metric_scores = {}

            # [핵심] 개별 채점(measure) 수행
            for metric in metrics:
                metric.measure(test_case)
                metric_scores[metric.name] = metric.score if metric.score else 0.0

            separated_scores = calculate_separated_scores(agent_name, metric_scores)
            type_scores.append(separated_scores)

            # 결과 출력
            q_id = q_info.get("id", "unknown")
            q_desc = q_info.get("description", "")
            print("\n" + "="*50)
            print(f"  * [{q_id}] {q_desc}")
            print(f"    - 입력: {test_case.input}")
            print(f"    - 실제 서버 출력:\n{test_case.actual_output}\n")
            print(f"    - [일반 분석 점수]: {separated_scores['analysis_score']:.2%}")
            if separated_scores['rag_score'] is not None:
                print(f"    - [RAG 검색 점수]: {separated_scores['rag_score']:.2%}")
            else:
                print(f"    - [RAG 검색 점수]: 미대상 (N/A)")

            for metric in metrics:
                marker = " [주요]" if metric.name == primary_metric_name else ""
                print(f"    - {metric.name}{marker}: {metric.score:.2f}")
                if metric.name == primary_metric_name and metric.reason:
                    print(f"    - 판단 이유: {metric.reason}")

        if type_scores:
            avg_analysis = sum(s["analysis_score"] for s in type_scores) / len(type_scores)
            
            # RAG 점수가 존재하는 에이전트인지 확인하여 평균 산출
            valid_rag_scores = [float(s["rag_score"]) for s in type_scores if s["rag_score"] is not None]
            avg_rag = sum(valid_rag_scores) / len(valid_rag_scores) if valid_rag_scores else None

            summary["results"].append({
                "type": question_type,
                "analysis_score": avg_analysis,
                "rag_score": avg_rag,
                "count": len(type_scores)
            })

    GLOBAL_RESULTS.append(summary)

    # 전체 평균 점수 계산 및 assertion
    # assert 조건, 메세지: 지정된 조건이 참(True)이면 통과, 거짓(False)일 때만 에러 메시지를 발생
    if isinstance(summary.get("results"), list) and summary["results"]:
        all_scores = []
        for r in summary["results"]:
            if isinstance(r, dict) and "analysis_score" in r and isinstance(r["analysis_score"], (int, float)):
                all_scores.append(float(r["analysis_score"]))
                
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
