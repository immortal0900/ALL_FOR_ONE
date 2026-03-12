# src/tests/analysis/analysis_eval/custom_llm.py
"""
DeepEval 평가용 커스텀 LLM 래퍼

평가(채점) 전용 모델로 gpt-5-mini를 사용합니다.
기존 에이전트들은 LLMProfile에 지정된 원래 모델(GPT-4.1, Claude Sonnet 등)을 그대로 사용하며,
이 래퍼는 오직 DeepEval의 G-Eval 메트릭 채점에만 사용됩니다.

[아키텍처 맥락]
- 이 모듈이 없으면: DeepEval이 기본 모델(gpt-4.1)을 사용하여 평가하게 되어,
  프로젝트에서 의도한 평가 모델과 일치하지 않을 수 있습니다.
- 싱글톤 패턴으로 모든 메트릭이 동일한 LLM 인스턴스를 재사용합니다.
"""

import os
from dotenv import load_dotenv
from deepeval.models.base_model import DeepEvalBaseLLM

load_dotenv()


# ============================================================
# 평가 모델 설정
# ============================================================
EVAL_MODEL_NAME = "gpt-5-mini"


class ProjectEvaluatorLLM(DeepEvalBaseLLM):
    """
    DeepEval 평가 전용 LLM 래퍼

    프로젝트의 RetryableChatOpenAI 래퍼를 활용하여
    동일한 재시도 로직과 API 키 설정을 공유합니다.

    [필수 구현 메서드]
    - generate(): 동기 텍스트 생성 (채점 프롬프트 처리)
    - a_generate(): 비동기 텍스트 생성
    - load_model(): 모델 객체 반환
    - get_model_name(): 모델 식별자 반환
    """

    def __init__(self, model_name: str = EVAL_MODEL_NAME, temperature: float = 0):
        """
        Args:
            model_name: 평가에 사용할 모델명 (기본: gpt-5-mini)
            temperature: 채점 일관성을 위해 0으로 고정

        Raises:
            EnvironmentError: OPENAI_API_KEY가 설정되지 않은 경우
        """
        if not os.getenv("OPENAI_API_KEY"):
            raise EnvironmentError(
                "OPENAI_API_KEY 환경변수가 설정되지 않았습니다. "
                ".env 파일에 OPENAI_API_KEY=<your-key>를 추가하세요."
            )

        # 프로젝트의 RetryableChatOpenAI를 재사용하여 재시도 로직 공유
        from utils.llm import RetryableChatOpenAI

        # response_format: DeepEval GEval이 JSON으로 score/reason을 요청하므로
        # API 레벨에서 유효한 JSON 출력을 강제하여 파싱 실패 방지
        # (이 설정이 없으면 LLM이 한국어 응답 중 Python 문자열 연결 등 비표준 구문을 삽입하여
        #  trimAndLoadJson()에서 ValueError 발생)
        self.model = RetryableChatOpenAI(
            model=model_name,
            temperature=temperature,
            request_timeout=120,  # 평가 호출 무한 대기 방지 (120초)
            model_kwargs={"response_format": {"type": "json_object"}},
        )
        self._model_name = model_name
        super().__init__()

    def generate(self, prompt: str) -> str:
        """동기 방식으로 평가 프롬프트를 처리하여 채점 결과를 반환합니다."""
        response = self.model.invoke(prompt)
        return response.content

    async def a_generate(self, prompt: str) -> str:
        """비동기 방식으로 평가 프롬프트를 처리하여 채점 결과를 반환합니다."""
        response = await self.model.ainvoke(prompt)
        return response.content

    def load_model(self):
        """모델 객체를 반환합니다."""
        return self.model

    def get_model_name(self) -> str:
        """모델 식별자를 반환합니다."""
        return self._model_name


# ============================================================
# 싱글톤 인스턴스
# ============================================================
# 모든 테스트에서 동일한 평가 LLM 인스턴스를 재사용합니다.
# temperature=0으로 고정하여 채점 결과의 일관성을 보장합니다.
evaluator_llm = ProjectEvaluatorLLM()
