# src/tests/final_report/report_eval/custom_metrics.py
"""
최종 보고서(jung_min_jae) 평가를 위한 커스텀 G-Eval 메트릭

분양성 검토 최종 보고서의 전문성과 분석 범위 충족도를 평가합니다.

[설계] 팩토리 패턴 -- 매 호출 시 새 인스턴스 생성으로 score 간섭 방지
"""

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams
from tests.analysis.analysis_eval.custom_llm import evaluator_llm

PRIMARY_METRIC = "ReportProfessionalism"


# ============================================================
# 메트릭 팩토리
# ============================================================
def _create_report_professionalism() -> GEval:
    return GEval(
        name="ReportProfessionalism",
        evaluation_steps=[
            "[가점] 부동산 전문 용어(분양가, 매매가, 수급지수 등)를 적절히 사용한 경우 높은 점수",
            "[감점] 비전문적이거나 구어체 표현을 사용한 경우 감점. 반대로 보고서에 적합한 문어체를 유지하면 가점",
            "[가점] 각 분석 항목의 결과를 종합하여 총평을 도출한 경우 가점",
            "[감점] 분석 항목 간 논리적 모순이 있는 경우 크게 감점",
            '[가점] 명확한 결론 도출: "분양 가능" 또는 "리스크 높음" + 구체적 분양가 레인지 제시하면 가점',
            '[감점] 명확한 결론 도출: "분양 가능" 또는 "리스크 높음" + 구체적 분양가 레인지 제시 못하면 감점',
            "[가점] 판단은 정량 데이터에 근거하며, 출처를 명확히 표기하면 가점",
            "[감점] 판단은 정량 데이터에 근거하지 않고, 출처를 명확히 표기 못하면 감점",
            "[필수] 판단 이유는 반드시 한국어로 작성할 것",
        ],
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=evaluator_llm,
    )


def _create_analysis_coverage() -> GEval:
    return GEval(
        name="AnalysisCoverage",
        evaluation_steps=[
            "[감점] 7개 분석 영역(입지, 정책, 청약FAQ, 수급, 인구, 미분양, 주변시장) 중 하나라도 완전히 누락된 경우 감점",
            "[가점] 모든 분석 영역이 언급되고 각 영역에서 핵심 인사이트가 포함된 경우 높은 점수",
            "[감점] 7개 분석 영역(입지, 정책, 청약FAQ, 수급, 인구, 미분양, 주변시장) 중 특정 영역이 한 줄로만 축소된 경우 감점",
            "[가점] 7개 분석 영역(입지, 정책, 청약FAQ, 수급, 인구, 미분양, 주변시장)을 균형 있게 다루면 가점",
            "[가점] 입지-수요-정책-가격을 단편적으로 나열하지 않고 인과관계로 연결하면 가점",
            "[필수] 판단 이유는 반드시 한국어로 작성할 것",
        ],
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=evaluator_llm,
    )


def get_all_metrics() -> list[GEval]:
    """호출할 때마다 새 메트릭 인스턴스 리스트를 반환합니다."""
    return [_create_report_professionalism(), _create_analysis_coverage()]


def calculate_weighted_score(metric_scores: dict[str, float]) -> float:
    """주요 메트릭 60%, 보조 메트릭 40%로 가중 점수 계산"""
    primary_score = metric_scores.get(PRIMARY_METRIC, 0.0)
    secondary_scores = [s for n, s in metric_scores.items() if n != PRIMARY_METRIC]
    secondary_avg = sum(secondary_scores) / len(secondary_scores) if secondary_scores else 0.0
    return (primary_score * 0.6) + (secondary_avg * 0.4)
