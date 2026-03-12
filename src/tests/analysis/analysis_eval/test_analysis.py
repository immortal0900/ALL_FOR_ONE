# src/tests/analysis/analysis_eval/test_analysis.py
"""
7개 분석 에이전트 평가 테스트

각 분석 에이전트의 LLM 출력(보고서)을 DeepEval의 커스텀 G-Eval 메트릭으로 채점합니다.

[핵심 설계]
- E2E 서버 파이프라인 결과(e2e_result)에서 actual_output + retrieval_context 추출
- metric.measure()로 원본 metric 객체에 .score/.reason 직접 설정
- RAG 에이전트: 분석 점수(100%)와 RAG 점수(100%)를 독립 산출 (합산 X)
- 비-RAG 에이전트: 분석 점수(100%)만 산출

[실행 방법]
set PYTHONIOENCODING=utf-8 && uv run deepeval test run src/tests/analysis/analysis_eval/test_analysis.py -v > test_analysis_results.txt 2>&1
"""

import time

import pytest
from deepeval.test_case import LLMTestCase
from .custom_metrics import (
    get_metrics_for_type,
    calculate_separated_scores,
    get_primary_metric,
    get_rag_primary_metric,
    RAG_AGENTS,
)
from .conftest import load_dataset, GLOBAL_RESULTS
from tests.format_utils import (
    print_module_header,
    print_analysis_case_result,
    print_rag_case_result,
    append_detail,
)


# ============================================================
# E2E 결과 키 매핑
# ============================================================
# 서버 반환값(e2e_result["analysis_outputs"])의 실제 키와 에이전트명 매핑
# 서버는 "policy_output"을 반환하지만 에이전트명은 "policy"
E2E_KEY_MAP = {
    "policy": "policy_output",
}

# 에이전트별 retrieval_context 추출에 사용할 키 목록
# e2e_result["analysis_outputs"][agent_key] 내부의 컨텍스트 키들
CONTEXT_KEYS = {
    "policy": ["national_context", "region_context"],
    "housing_faq": ["housing_faq_context", "housing_rule_context"],
    "unsold_insight": ["unsold_unit"],
    "population_insight": ["age_population_context", "move_population_context"],
    "supply_demand": [
        "year10_after_house", "jeonse_price", "sale_price",
        "trade_balance", "use_kor_rate", "home_mortgage",
        "one_people_gdp", "one_people_grdp",
        "housing_sales_volume", "planning_move", "pre_promise_competition",
    ],
    "location_insight": ["gemini_search", "kakao_api_distance_context"],
    "nearby_market": [
        "gemini_search", "kakao_api_distance_context",
        "real_estate_price_context", "perplexity_search",
    ],
}


# ============================================================
# 평가용 컨텍스트 절단 (Evaluation Context Truncation)
# ============================================================
# [존재 이유]
# policy(130K자), population(79K자) 등 거대한 retrieval_context를
# 평가 LLM(gpt-5-mini)에 그대로 전달하면 API 응답이 60-120초로 느려지고,
# 126회 순차 호출 시 전체 평가가 2시간 이상 소요되어 사실상 완료 불가.
# 10K자로 절단하면 평가 LLM 입력이 ~2,500토큰으로 제한되어 응답이 15-30초로 단축됨.
# 절단은 평가 LLM에 전달하는 데이터만 영향 — E2E 파이프라인 자체에는 무관.
MAX_CONTEXT_CHARS = 10_000  # 약 2,500 토큰


def _truncate_context(text: str, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    """평가 성능을 위해 컨텍스트를 최대 길이로 절단합니다."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... (truncated for evaluation)"


def _extract_retrieval_contexts(agent_name: str, agent_data: dict) -> list[str]:
    """
    E2E 결과에서 에이전트별 retrieval_context 문자열 리스트를 추출합니다.

    agent_data: e2e_result["analysis_outputs"][agent_key] 딕셔너리
    반환값: ["컨텍스트1 내용", "컨텍스트2 내용", ...] 형태의 문자열 리스트

    [절단 정책]
    각 컨텍스트 청크를 MAX_CONTEXT_CHARS(10K자)로 절단하여
    평가 LLM의 응답 시간을 단축합니다.
    """
    context_keys = CONTEXT_KEYS.get(agent_name, [])
    contexts = []

    for key in context_keys:
        value = agent_data.get(key)
        if value is None:
            continue
        # 값이 문자열이면 그대로, 딕셔너리/리스트면 str()로 변환 후 절단
        text = str(value) if not isinstance(value, str) else value
        contexts.append(_truncate_context(text))

    return contexts if contexts else ["(컨텍스트 없음)"]


# ============================================================
# 평가 실행 핵심 함수
# ============================================================
def run_evaluation_for_agent(agent_name: str, e2e_result: dict):
    """
    특정 분석 에이전트의 E2E 결과를 평가합니다.

    [동작 흐름]
    1. e2e_result에서 해당 에이전트의 actual_output + retrieval_context 추출
    2. LLMTestCase 생성 (input은 데이터셋, actual_output/context는 E2E 결과)
    3. metric.measure()로 각 메트릭 평가 실행
    4. calculate_separated_scores()로 분석/RAG 점수 분리 산출

    Args:
        agent_name: 에이전트 식별자 (예: "housing_faq")
        e2e_result: E2E 서버 파이프라인 반환값
    """
    # E2E 결과에서 에이전트 데이터 추출
    analysis_outputs = e2e_result.get("analysis_outputs", {})
    e2e_key = E2E_KEY_MAP.get(agent_name, agent_name)
    agent_data = analysis_outputs.get(e2e_key, {})

    if not agent_data:
        pytest.skip(f"E2E 결과에 '{e2e_key}' 데이터가 없습니다.")

    # actual_output 추출 ("result" 키에 분석 보고서 문자열이 담김)
    actual_output = agent_data.get("result", "")
    if not actual_output:
        pytest.skip(f"'{e2e_key}'의 result가 비어 있습니다.")

    # retrieval_context 추출
    retrieval_contexts = _extract_retrieval_contexts(agent_name, agent_data)

    # 데이터셋에서 input(질문) 로드
    dataset = load_dataset(agent_name)
    summary = {"agent": agent_name, "results": []}

    # 메트릭 생성 (팩토리 패턴 -- 매번 새 인스턴스)
    metrics = get_metrics_for_type(agent_name)
    primary_metric_name = get_primary_metric(agent_name)
    rag_primary_metric_name = get_rag_primary_metric(agent_name)

    # 분석/RAG 메트릭 이름 목록 (개별 점수 표시용)
    analysis_metric_names = {"AnalysisDepth", "DataFidelity", "StructuralCompleteness"}
    rag_metric_names = {"Faithfulness", "Contextual Relevancy", "Answer Relevancy"}

    print_module_header(f"분석 에이전트 - {agent_name}", len(dataset))

    case_scores = []
    for i, item in enumerate(dataset, 1):
        print(f"\n  [{agent_name}] 케이스 {i}/{len(dataset)} 평가 중...")

        test_case = LLMTestCase(
            input=item["input"],
            actual_output=actual_output,
            retrieval_context=retrieval_contexts,
        )

        # metric.measure() 반환값 직접 사용
        # 개별 메트릭 실패 시 0.0으로 대체하여 테스트 전체 크래시 방지
        # 실패 원인은 [경고] 메시지로 출력하여 진단 가능
        all_metric_scores = {}
        for metric in metrics:
            # .name이 없는 메트릭(Built-in RAG 등) 대비 안전한 이름 추출
            m_name = getattr(metric, "name", type(metric).__name__)
            t0 = time.time()
            try:
                score = metric.measure(test_case)
                elapsed = time.time() - t0
                print(f"    {m_name}: {score:.2f} ({elapsed:.1f}s)")
                all_metric_scores[m_name] = score if score is not None else 0.0
            except Exception as e:
                elapsed = time.time() - t0
                print(f"    [경고] {m_name} 평가 실패 ({elapsed:.1f}s): {e}")
                all_metric_scores[m_name] = 0.0

        # 분석/RAG 점수 분리 산출
        separated = calculate_separated_scores(agent_name, all_metric_scores)
        case_scores.append(separated)

        q_id = item.get("id", "unknown")
        q_desc = item.get("description", "")

        # --- 분석 대표 메트릭에서 reason 추출 ---
        analysis_primary = next(
            (m for m in metrics if getattr(m, "name", None) == primary_metric_name),
            metrics[0],
        )
        analysis_reason = getattr(analysis_primary, "reason", None)

        # --- RAG 대표 메트릭에서 reason 추출 (RAG 에이전트만) ---
        rag_reason = None
        if rag_primary_metric_name:
            rag_primary = next(
                (m for m in metrics if getattr(m, "name", None) == rag_primary_metric_name),
                None,
            )
            if rag_primary:
                rag_reason = getattr(rag_primary, "reason", None)

        # --- 개별 메트릭 점수를 분석/RAG로 분리 ---
        analysis_metrics = {k: v for k, v in all_metric_scores.items() if k in analysis_metric_names}
        rag_metrics = {k: v for k, v in all_metric_scores.items() if k in rag_metric_names}

        # --- [분석 평가] 섹션 출력 ---
        print_analysis_case_result(
            case_id=q_id,
            description=q_desc,
            input_text=item["input"],
            output_text=actual_output,
            analysis_score=separated["analysis_score"],
            analysis_reason=analysis_reason,
            metric_scores=analysis_metrics,
        )

        # --- [RAG 평가] 섹션 출력 (RAG 에이전트만) ---
        if separated["rag_score"] is not None:
            print_rag_case_result(
                retrieval_context=retrieval_contexts,
                output_text=actual_output,
                rag_score=separated["rag_score"],
                rag_reason=rag_reason,
                metric_scores=rag_metrics,
            )

        # --- JSON 상세 결과 저장 ---
        detail_entry = {
            "agent": agent_name,
            "id": q_id,
            "description": q_desc,
            "analysis_score": separated["analysis_score"],
            "rag_score": separated["rag_score"],
            "analysis": {
                "input": item["input"],
                "output": actual_output,
                "score": separated["analysis_score"],
                "reason": analysis_reason,
                "metrics": analysis_metrics,
            },
        }
        if separated["rag_score"] is not None:
            detail_entry["rag"] = {
                "retrieval_context": retrieval_contexts,
                "output": actual_output,
                "score": separated["rag_score"],
                "reason": rag_reason,
                "metrics": rag_metrics,
            }
        append_detail("analysis", detail_entry)

    # 에이전트 평균 점수 계산
    if case_scores:
        avg_analysis = sum(s["analysis_score"] for s in case_scores) / len(case_scores)
        summary_entry = {
            "type": agent_name,
            "analysis_score": avg_analysis,
            "count": len(case_scores),
        }

        # RAG 점수가 있는 에이전트는 RAG 평균도 기록
        rag_scores = [s["rag_score"] for s in case_scores if s["rag_score"] is not None]
        if rag_scores:
            avg_rag = sum(rag_scores) / len(rag_scores)
            summary_entry["rag_score"] = avg_rag

        summary["results"].append(summary_entry)

    GLOBAL_RESULTS.append(summary)

    # 분석 점수 기준으로 assertion (70% 이상)
    if case_scores:
        avg_analysis = sum(s["analysis_score"] for s in case_scores) / len(case_scores)
        assert avg_analysis >= 0.7, (
            f"{agent_name} 분석 점수 평균 {avg_analysis:.2%}로 기준(70%) 미달"
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
