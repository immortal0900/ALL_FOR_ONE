# src/tests/judge/judge_eval/custom_metrics.py
"""
보고서 자가 검증(Critique/Judge) 평가용 G-Eval 메트릭
대상: policy_agent의 evaluate_report_completeness()

[설계] 팩토리 패턴 -- 매 호출 시 새 인스턴스 생성으로 score 간섭 방지
"""

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams
from tests.analysis.analysis_eval.custom_llm import evaluator_llm


def _create_critique_accuracy() -> GEval:
    return GEval(
        name="CritiqueAccuracy",
        evaluation_steps=[
            "[가점] 원본 초안(draft)에서 실제로 누락된 필수 목차를 `missing_sections`에 정확히 지적한 경우 높은 점수",
            "[감점] 초안에 이미 존재하는 내용을 누락되었다고 잘못 지적(Over-critique)한 경우 감점",
            "[감점] 초안에 명확히 빠진 필수 목차가 있는데도 찾아내지 못한(Under-critique) 경우 크게 감점",
            "[가점] `missing_information`에 누락된 수치나 디테일을 구체적으로 서술한 경우 가점",
            "[가점] `search_queries`가 누락된 정보를 채우기에 적합한 키워드로 구성된 경우 가점",
            "[필수] 판단 이유는 반드시 한국어로 작성할 것",
        ],
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=evaluator_llm,
    )


def get_all_metrics() -> list[GEval]:
    """호출할 때마다 새 메트릭 인스턴스 리스트를 반환합니다."""
    return [_create_critique_accuracy()]
