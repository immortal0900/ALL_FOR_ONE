# src/tests/analysis/analysis_eval/custom_metrics.py
"""
7개 분석 에이전트 평가용 커스텀 메트릭 (G-Eval + RAG Built-in)

[설계 원칙]
- 팩토리 패턴: 매 호출 시 새 메트릭 인스턴스를 생성하여
  테스트 케이스 간 .score 덮어쓰기(race condition) 방지
- 점수 분리: RAG 에이전트는 '분석 점수'와 'RAG 점수'를 독립 산출
  (합산하지 않음 -- 각각 100% 기준)
"""

from typing import Optional

from deepeval.metrics import (
    GEval,
    FaithfulnessMetric,
    ContextualRelevancyMetric,
    AnswerRelevancyMetric,
)
from deepeval.test_case import LLMTestCaseParams
from tests.analysis.analysis_eval.custom_llm import evaluator_llm


# RAG 검색(pgvector)을 사용하는 에이전트 목록
# get_metrics_for_type()과 calculate_separated_scores() 양쪽에서 참조
RAG_AGENTS = [
    "policy", "housing_faq", "population_insight",
    "supply_demand", "location_insight", "nearby_market",
    "unsold_insight",
]


# ============================================================
# 1. 분석 메트릭 팩토리 (모든 에이전트 공통)
# ============================================================
def _create_analysis_metrics() -> list[GEval]:
    """호출할 때마다 새 인스턴스를 생성하여 score 간섭을 방지합니다."""
    analysis_depth = GEval(
        name="AnalysisDepth",
        evaluation_steps=[
            "[가점] 데이터의 단순 나열이 아닌, 원인/이유 규명 등 분석 심도가 깊으면 가점",
            "[감점] 데이터의 단순 나열이나 표면적 사실만 서술하고 원인/이유 규명 등 분석 심도가 얕으면 감점",
            "[가점] 시계열 변화에 대한 해석과 흐름 설명이 포함되어 있으면 높은 가점",
            "[감점] 시계열 변화에 대한 해석이나 흐름(과거-현재-미래)에 대한 설명이 빠져 있으면 감점",
            "[가점] 분석을 바탕으로 한 향후 전망이나 객관적인 결론이 명확히 도출되었으면 가점",
            "[감점] 분석 결과에 따른 향후 전망이나 결론 제시 없이 부실하게 마무리되면 감점",
            "[필수] 판단 이유는 반드시 한국어로 작성할 것",
        ],
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.RETRIEVAL_CONTEXT,
        ],
        threshold=0.7,
        model=evaluator_llm,
        verbose_mode=False,
    )

    data_fidelity = GEval(
        name="DataFidelity",
        evaluation_steps=[
            "[가점] 제공된 검색 컨텍스트(retrieval_context)와 최종 출력물(actual_output)의 수치 정보 및 팩트가 완벽히 일치하면 가점",
            "[감점] 제공된 검색 컨텍스트와 최종 출력물의 수치 정보가 불일치하거나 왜곡되어 있으면 감점",
            "[가점] 검색 결과에 명시된 출처를 명확히 표기하고 그 내용을 바탕으로만 안전하게 서술했다면 가점",
            "[감점] 검색 결과에 전혀 존재하지 않는 통계나 숫자를 임의로(할루시네이션) 지어내어 인용했다면 크게 감점",
            "[필수] 판단 이유는 반드시 한국어로 작성할 것",
        ],
        evaluation_params=[
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.RETRIEVAL_CONTEXT,
        ],
        threshold=0.8,
        model=evaluator_llm,
        verbose_mode=False,
    )

    structural_completeness = GEval(
        name="StructuralCompleteness",
        evaluation_steps=[
            "[가점] Markdown 구조(헤더, 목록, 표 등)가 규칙에 맞게 가독성 있게 잘 적용되었으면 가점",
            "[감점] Markdown 구조가 깨져 있거나 시각적으로 가독성이 떨어지게 작성되었으면 감점",
            "[가점] 서론(개요), 본론(상세 분석), 결론 형태의 논리적 흐름이 체계적으로 갖춰져 있으면 가점",
            "[감점] 서론-본론-결론의 논리적 흐름 없이 단편적인 문장만 두서없이 나열되어 있으면 감점",
            "[가점] 전문적인 보고서 어조(문어체)를 일관되게 유지했다면 가점",
            "[감점] 전문적인 보고서 포맷을 따르지 않거나 적절하지 않은 어투가 섞여 있으면 감점",
            "[필수] 판단 이유는 반드시 한국어로 작성할 것",
        ],
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=evaluator_llm,
        verbose_mode=False,
    )

    return [analysis_depth, data_fidelity, structural_completeness]


# ============================================================
# 2. RAG 메트릭 팩토리 (RAG 에이전트 전용)
# ============================================================
def _create_rag_metrics() -> list:
    """RAG 3대 지표 인스턴스를 새로 생성합니다.

    [존재 이유]
    DeepEval의 Built-in RAG 메트릭(FaithfulnessMetric 등)은
    GEval과 달리 생성자에 name 파라미터가 없고 .name 속성도 없습니다.
    calculate_separated_scores()의 가중치 키와 일치시키기 위해
    수동으로 .name을 설정합니다.
    """
    faithfulness = FaithfulnessMetric(threshold=0.7, model=evaluator_llm, verbose_mode=False)
    faithfulness.name = "Faithfulness"

    contextual_relevancy = ContextualRelevancyMetric(threshold=0.7, model=evaluator_llm, verbose_mode=False)
    contextual_relevancy.name = "Contextual Relevancy"

    answer_relevancy = AnswerRelevancyMetric(threshold=0.7, model=evaluator_llm, verbose_mode=False)
    answer_relevancy.name = "Answer Relevancy"

    return [faithfulness, contextual_relevancy, answer_relevancy]


# ============================================================
# 유틸리티 함수
# ============================================================
def get_metrics_for_type(agent_name: str) -> list:
    """
    에이전트별 메트릭 조합을 새 인스턴스로 반환합니다.

    - 모든 에이전트: 분석 3대 지표 (AnalysisDepth, DataFidelity, StructuralCompleteness)
    - RAG 에이전트: 분석 3대 지표 + RAG 3대 지표 (Faithfulness, Contextual Relevancy, Answer Relevancy)
    """
    metrics = _create_analysis_metrics()

    if agent_name in RAG_AGENTS:
        metrics.extend(_create_rag_metrics())

    return metrics


def get_primary_metric(agent_name: str) -> str:
    """유형별 주요(대표) 메트릭 이름 반환"""
    return "AnalysisDepth"


def calculate_separated_scores(agent_name: str, scores: dict[str, float]) -> dict[str, Optional[float]]:
    """
    일반 분석 점수와 RAG 검색 점수를 명확히 분리하여 반환합니다.

    RAG 에이전트: {"analysis_score": 0.85, "rag_score": 0.78}  (점수 2개)
    비-RAG 에이전트: {"analysis_score": 0.85, "rag_score": None}  (점수 1개)

    각 점수는 독립적인 100% 기준이며, 합산하지 않습니다.
    """
    # 1. 일반 분석 지표 (모든 에이전트 공통 적용)
    analysis_weights = {
        "AnalysisDepth": 0.40,
        "DataFidelity": 0.40,
        "StructuralCompleteness": 0.20,
    }

    analysis_score = 0.0
    for name, weight in analysis_weights.items():
        analysis_score += scores.get(name, 0.0) * weight

    result: dict[str, Optional[float]] = {
        "analysis_score": analysis_score,
        "rag_score": None,
    }

    # 2. RAG 검색 지표 (RAG 사용 에이전트만 적용)
    if agent_name in RAG_AGENTS:
        rag_weights = {
            "Faithfulness": 0.334,
            "Contextual Relevancy": 0.333,
            "Answer Relevancy": 0.333,
        }

        rag_score = 0.0
        for name, weight in rag_weights.items():
            rag_score += scores.get(name, 0.0) * weight

        result["rag_score"] = rag_score

    return result
