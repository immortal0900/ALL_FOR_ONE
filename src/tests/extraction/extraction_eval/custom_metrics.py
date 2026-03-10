# src/tests/extraction/extraction_eval/custom_metrics.py
"""
데이터 추출/필터링 평가용 G-Eval 메트릭

대상: policy_agent의 evaluate_report_completeness(), supply_demand_agent의 trade_balance()

[설계] 팩토리 패턴 -- 매 호출 시 새 인스턴스 생성으로 score 간섭 방지
"""

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams
from tests.analysis.analysis_eval.custom_llm import evaluator_llm


def _create_extraction_accuracy() -> GEval:
    return GEval(
        name="ExtractionAccuracy",
        evaluation_steps=[
            "[가점] 지시된 조건(지역명, 필터 기준)에 정확히 부합하는 데이터만 추출한 경우 높은 점수",
            "[감점] 관련 없는 지역이나 데이터를 포함한 경우 감점",
            "[감점] 원본에 없는 데이터를 만들어낸 경우 크게 감점",
            "[가점] 간결하고 불필요한 설명 없이 핵심만 추출한 경우 가점",
            "[감점] 불필요한 사족이 많으면 감점",
            "[필수] 판단 이유는 반드시 한국어로 작성할 것",
        ],
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=evaluator_llm,
        verbose_mode=False,
    )


def get_all_metrics() -> list[GEval]:
    """호출할 때마다 새 메트릭 인스턴스 리스트를 반환합니다."""
    return [_create_extraction_accuracy()]
