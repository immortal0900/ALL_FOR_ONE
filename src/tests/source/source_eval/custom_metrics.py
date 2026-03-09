# src/tests/source/source_eval/custom_metrics.py
"""
출처 추출(main final_node) 평가용 G-Eval 메트릭

[설계] 팩토리 패턴 -- 매 호출 시 새 인스턴스 생성으로 score 간섭 방지
"""

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams
from tests.analysis.analysis_eval.custom_llm import evaluator_llm


def _create_source_completeness() -> GEval:
    return GEval(
        name="SourceCompleteness",
        evaluation_steps=[
            "[가점] 각 분석 항목의 데이터 출처(기관명, 기준일)를 정확히 나열한 경우 높은 점수",
            "[감점] 출처가 누락된 분석 항목이 있는 경우 감점",
            "[감점] 존재하지 않는 출처를 만들어낸 경우 크게 감점",
            "[가점] 출처를 체계적으로 구조화(표 또는 번호 목록)한 경우 가점",
            "[필수] 판단 이유는 반드시 한국어로 작성할 것",
        ],
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=evaluator_llm,
    )


def get_all_metrics() -> list[GEval]:
    """호출할 때마다 새 메트릭 인스턴스 리스트를 반환합니다."""
    return [_create_source_completeness()]
