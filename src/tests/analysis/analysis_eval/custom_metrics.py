# src/tests/analysis/analysis_eval/custom_metrics.py
"""
분석 에이전트 평가를 위한 커스텀 G-Eval 메트릭

7개 분석 에이전트(housing_faq, policy, supply_demand, nearby_market,
location_insight, population_insight, unsold_insight)의 보고서 출력 품질을
DeepEval의 G-Eval을 활용하여 평가합니다.

[아키텍처 맥락]
이 메트릭들은 각 분석 에이전트의 LLM 호출 결과(보고서)를 채점합니다.
에이전트 자체는 원래 지정된 모델(GPT-4.1 등)로 실행되고,
채점만 evaluator_llm(gpt-5-mini)이 수행합니다.
"""

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams
from .custom_llm import evaluator_llm


# ============================================================
# 1. AnalysisDepth (분석 심도)
# ============================================================
# 이 메트릭이 없을 경우: 데이터를 무시하고 일반론만 작성하는 보고서를
# 탐지할 수 없어 보고서 품질이 전반적으로 하락합니다.
analysis_depth = GEval(
    name="AnalysisDepth",
    evaluation_steps=[
        "[가점] 제공된 데이터의 핵심 수치(가격, 비율, 추세 등)를 구체적으로 인용하며 분석한 경우 높은 점수",
        "[감점] 제공된 데이터를 무시하고 일반론만 서술한 경우 감점",
        "[가점] 시계열 추세(전년 대비, 최근 N개월 등)를 해석한 경우 가점",
        "[감점] 근거 없는 단정적 예측('확실히 상승할 것')을 한 경우 크게 감점. 반대로 데이터 기반 조건부 전망은 가점",
        "[필수] 판단 이유는 반드시 한국어로 작성할 것",
    ],
    evaluation_params=[
        LLMTestCaseParams.INPUT,
        LLMTestCaseParams.ACTUAL_OUTPUT,
    ],
    threshold=0.7,
    model=evaluator_llm,
)


# ============================================================
# 2. DataFidelity (데이터 충실도)
# ============================================================
# 이 메트릭이 없을 경우: LLM이 입력 데이터에 없는 수치를 만들어내는
# 환각(hallucination)을 탐지할 수 없어 보고서 신뢰도가 하락합니다.
data_fidelity = GEval(
    name="DataFidelity",
    evaluation_steps=[
        "[감점] 입력 데이터에 없는 수치나 통계를 만들어낸 경우(환각) 크게 감점",
        "[감점] 입력 데이터의 수치를 잘못 인용한 경우(오기) 감점",
        "[가점] 입력 데이터의 핵심 수치를 정확하게 인용하며 설명한 경우 높은 점수",
        "[가점] 데이터 출처(기관명, 기준 시점)를 명시한 경우 가점",
        "[필수] 판단 이유는 반드시 한국어로 작성할 것",
    ],
    evaluation_params=[
        LLMTestCaseParams.INPUT,
        LLMTestCaseParams.ACTUAL_OUTPUT,
    ],
    threshold=0.7,
    model=evaluator_llm,
)


# ============================================================
# 3. StructuralCompleteness (구조적 완성도)
# ============================================================
# 이 메트릭이 없을 경우: 구조 없이 평문으로만 나열되거나
# 결론 없이 끊기는 보고서를 탐지할 수 없습니다.
structural_completeness = GEval(
    name="StructuralCompleteness",
    evaluation_steps=[
        "[가점] Markdown 헤더(##, ###)로 섹션이 체계적으로 구분된 경우 높은 점수",
        "[감점] 구조 없이 평문으로만 나열된 경우 감점",
        "[가점] 핵심 지표, 현황, 시사점 등의 논리적 흐름이 있는 경우 가점",
        "[감점] 보고서가 중간에 끊기거나 결론 없이 끝난 경우 크게 감점. 반대로 명확한 종합 판단이 있으면 가점",
        "[필수] 판단 이유는 반드시 한국어로 작성할 것",
    ],
    evaluation_params=[
        LLMTestCaseParams.INPUT,
        LLMTestCaseParams.ACTUAL_OUTPUT,
    ],
    threshold=0.7,
    model=evaluator_llm,
)


# ============================================================
# 메트릭 리스트 및 유틸리티
# ============================================================
ALL_METRICS = [analysis_depth, data_fidelity, structural_completeness]

# 테스트 유형별 메트릭 매핑
METRICS_BY_TYPE = {
    "analysis_report": ALL_METRICS,
    "data_extraction": [data_fidelity],
}

# 유형별 주요 메트릭 (가중치 60%)
PRIMARY_METRIC_BY_TYPE = {
    "analysis_report": "AnalysisDepth",
    "data_extraction": "DataFidelity",
}


def get_metrics_for_type(question_type: str) -> list[GEval]:
    """테스트 유형에 맞는 메트릭 리스트를 반환합니다."""
    return METRICS_BY_TYPE.get(question_type, ALL_METRICS)


def get_primary_metric(question_type: str) -> str:
    """테스트 유형의 주요 메트릭 이름을 반환합니다."""
    return PRIMARY_METRIC_BY_TYPE.get(question_type, ALL_METRICS[0].name)


def calculate_weighted_score(
    question_type: str,
    metric_scores: dict[str, float],
) -> float:
    """
    주요 메트릭 60%, 보조 메트릭들 40% 균등 분배로 가중 점수를 계산합니다.

    Args:
        question_type: 테스트 유형 (analysis_report / data_extraction)
        metric_scores: {"MetricName": score, ...} 딕셔너리

    Returns:
        가중 평균 점수 (0.0 ~ 1.0)
    """
    primary_metric = get_primary_metric(question_type)
    primary_score = metric_scores.get(primary_metric, 0.0)

    secondary_scores = [
        score for name, score in metric_scores.items()
        if name != primary_metric
    ]

    if secondary_scores:
        secondary_avg = sum(secondary_scores) / len(secondary_scores)
    else:
        secondary_avg = 0.0

    primary_weight = 0.6
    secondary_weight = 0.4
    return (primary_score * primary_weight) + (secondary_avg * secondary_weight)
