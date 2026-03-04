# src/tests/renderer/renderer_eval/custom_metrics.py
"""PPT 변환(renderer) 평가용 G-Eval 메트릭"""

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams
from tests.analysis.analysis_eval.custom_llm import evaluator_llm

slide_plan_structure = GEval(
    name="SlidePlanStructure",
    evaluation_steps=[
        "[가점] JSON 형식이 유효하고 파싱 가능한 경우 높은 점수",
        "[감점] JSON 형식이 깨지거나 파싱 불가능한 경우 크게 감점",
        "[감점] 보고서 원문에 없는 내용을 추가(환각)한 경우 감점. 반대로 원문 충실하게 변환하면 가점",
        "[감점] 텍스트가 깨지거나 잘린 경우 감점",
        "[필수] 판단 이유는 반드시 한국어로 작성할 것",
    ],
    evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
    threshold=0.7,
    model=evaluator_llm,
)

ALL_METRICS = [slide_plan_structure]

def get_all_metrics(): return ALL_METRICS
