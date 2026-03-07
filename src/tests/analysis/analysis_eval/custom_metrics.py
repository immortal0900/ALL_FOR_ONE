# src/tests/analysis/analysis_eval/custom_metrics.py
import os
from deepeval.metrics import (
    GEval,
    FaithfulnessMetric,
    ContextualRelevancyMetric,
    AnswerRelevancyMetric
)
from deepeval.test_case import LLMTestCaseParams
from tests.analysis.analysis_eval.custom_llm import evaluator_llm

# ============================================================
# 1. RAG 3대 지표 (DeepEval Built-in)
# ============================================================
# threshold는 0.7로 엄격하게 설정
faithfulness_metric = FaithfulnessMetric(threshold=0.7, model=evaluator_llm)
contextual_relevancy_metric = ContextualRelevancyMetric(threshold=0.7, model=evaluator_llm)
answer_relevancy_metric = AnswerRelevancyMetric(threshold=0.7, model=evaluator_llm)


# ============================================================
# 2. 기존 커스텀 지표 (G-Eval)
# ============================================================
analysis_depth = GEval(
    name="AnalysisDepth",
    evaluation_steps=[
        "[가점] 데이터의 단순 나열이 아닌, 원인/이유 규명 등 분석 심도가 깊으면 가점",
        "[감점] 데이터의 단순 나열이나 표면적 사실만 서술하고 원인/이유 규명 등 분석 심도가 얕으면 감점",
        "[가점] 시계열 변화에 대한 해석과 흐름 설명이 포함되어 있으면 높은 가점",
        "[감점] 시계열 변화에 대한 해석이나 흐름(과거-현재-미래)에 대한 설명이 빠져 있으면 감점",
        "[가점] 분석을 바탕으로 한 향후 전망이나 객관적인 결론이 명확히 도출되었으면 가점",
        "[감점] 분석 결과에 따른 향후 전망이나 결론 제시 없이 부실하게 마무리되면 감점",
        "[필수] 판단 이유는 반드시 한국어로 작성할 것"
    ],
    evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.RETRIEVAL_CONTEXT],
    threshold=0.7,
    model=evaluator_llm,
)

data_fidelity = GEval(
    name="DataFidelity",
    evaluation_steps=[
        "[가점] 제공된 검색 컨텍스트(retrieval_context)와 최종 출력물(actual_output)의 수치 정보 및 팩트가 완벽히 일치하면 가점",
        "[감점] 제공된 검색 컨텍스트와 최종 출력물의 수치 정보가 불일치하거나 왜곡되어 있으면 감점",
        "[가점] 검색 결과에 명시된 출처를 명확히 표기하고 그 내용을 바탕으로만 안전하게 서술했다면 가점",
        "[감점] 검색 결과에 전혀 존재하지 않는 통계나 숫자를 임의로(할루시네이션) 지어내어 인용했다면 크게 감점",
        "[필수] 판단 이유는 반드시 한국어로 작성할 것"
    ],
    evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.RETRIEVAL_CONTEXT],
    threshold=0.8,
    model=evaluator_llm,
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
        "[필수] 판단 이유는 반드시 한국어로 작성할 것"
    ],
    evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
    threshold=0.7,
    model=evaluator_llm,
)


# ============================================================
# 유틸리티 함수
# ============================================================
def get_metrics_for_type(agent_name: str):
    """테스트 유형별 메트릭 조합 반환"""
    # 기본 지표
    metrics = [analysis_depth, data_fidelity, structural_completeness]
    
    # RAG 검색(pgvector)을 사용하는 에이전트 목록
    rag_agents = [
        "policy", "housing_faq", "population_insight", 
        "supply_demand", "location_insight", "nearby_market", 
        "unsold_insight" # 기존 로컬 CSV에서 Supabase RAG로 마이그레이션됨
    ]
    
    # RAG 기반인 경우 RAG 3대 지표 추가
    if agent_name in rag_agents:
        metrics.extend([
            faithfulness_metric,
            contextual_relevancy_metric,
            answer_relevancy_metric
        ])
        
    return metrics

def get_primary_metric(agent_name: str) -> str:
    """유형별 주요(대표) 메트릭 이름 반환"""
    return "AnalysisDepth"

from typing import Optional

def calculate_separated_scores(agent_name: str, scores: dict[str, float]) -> dict[str, Optional[float]]:
    """
    일반 분석 점수와 RAG 검색 점수를 명확히 분리하여 반환합니다.
    
    Returns:
        dict: {"analysis_score": float, "rag_score": float | None}
    """
    # 1. 일반 분석 지표 (모든 에이전트 공통 적용)
    # 총 가중치 합이 1.0이 되도록 배분
    analysis_weights = {
        "AnalysisDepth": 0.40,
        "DataFidelity": 0.40,
        "StructuralCompleteness": 0.20
    }
    
    analysis_score = 0.0
    for name, weight in analysis_weights.items():
        analysis_score += scores.get(name, 0.0) * weight
        
    result = {"analysis_score": analysis_score, "rag_score": None}
    
    # 2. RAG 검색 지표 (RAG 사용 에이전트만 적용)
    rag_agents = ["policy", "housing_faq", "population_insight", "supply_demand", "location_insight", "nearby_market"]
    
    if agent_name in rag_agents:
        # 총 가중치 합이 1.0이 되도록 배분 (동등하게 1/3씩)
        rag_weights = {
            "Faithfulness": 0.334,
            "Contextual Relevancy": 0.333,
            "Answer Relevancy": 0.333
        }
        
        rag_score = 0.0
        for name, weight in rag_weights.items():
            rag_score += scores.get(name, 0.0) * weight
            
        result["rag_score"] = rag_score
        
    return result
