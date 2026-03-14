from enum import StrEnum
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
import openai
import os
import time
import asyncio
from dotenv import load_dotenv
from functools import wraps

load_dotenv()

# Langfuse 추적기 (Graceful Degradation: 미설치 시에도 안전)
from utils.langfuse_tracker import tracker as _langfuse_tracker


# Monkey patch for langchain-google-genai max_retries bug
def patch_google_genai():
    """langchain-google-genai의 max_retries 버그를 우회하는 패치"""
    try:
        from langchain_google_genai import chat_models

        original_chat_with_retry = chat_models._chat_with_retry

        @wraps(original_chat_with_retry)
        def patched_chat_with_retry(generation_method, **kwargs):
            # max_retries 파라미터 제거
            kwargs.pop("max_retries", None)
            return original_chat_with_retry(
                generation_method=generation_method, **kwargs
            )

        chat_models._chat_with_retry = patched_chat_with_retry
    except Exception as e:
        print(f"Google Genai 패치 적용 실패 (무시 가능): {e}")


# 패치 적용
patch_google_genai()


# 재시도하지 않을 구조적 에러 (코드 버그)
# 이 에러들은 반복해도 결과가 동일하므로 즉시 전파하여 디버깅을 빠르게 합니다.
_NON_RETRYABLE_ERRORS = (AttributeError, TypeError, ValueError, ImportError, SyntaxError)

# 재시도할 일시적 에러 (Transient Error)
# openai 예외 계층: APITimeoutError -> APIConnectionError -> APIError
# RateLimitError, InternalServerError -> APIStatusError -> APIError
# isinstance 체크이므로 SDK 에러 메시지 변경에 영향받지 않습니다.
# 이것이 없을 경우: 문자열 매칭("api", "error")에 의존하게 되어
# str(APITimeoutError)="Request timed out." 처럼 패턴에 걸리지 않는 예외가 재시도되지 않습니다.
_RETRYABLE_ERRORS = (
    openai.APITimeoutError,      # 요청 시간 초과
    openai.APIConnectionError,   # 네트워크 연결 실패
    openai.RateLimitError,       # 429 Too Many Requests
    openai.InternalServerError,  # 500 서버 내부 오류
)


class RetryableChatOpenAI(ChatOpenAI):
    """Exponential Backoff 재시도 로직과 Langfuse 자동 추적이 적용된 ChatOpenAI 클래스.

    [Langfuse 자동 주입 흐름]
    invoke()/ainvoke() 호출
      → _merge_langfuse_config()로 기존 config에 CallbackHandler 추가
      → super().invoke()가 콜백을 통해 Langfuse 서버로 trace 전송

    [존재 이유]
    이 클래스 한 곳에서 Langfuse 콜백을 주입하므로
    28개 LLM 호출 지점을 개별 수정할 필요가 없습니다.

    [OpenAI SDK 내부 retry 비활성화]
    이 클래스가 자체 재시도 로직(5회, Exponential Backoff)을 관리하므로
    OpenAI SDK의 내부 retry(ChatOpenAI 기본 max_retries=2)와 중복되지 않도록
    max_retries=0으로 비활성화합니다.
    이것이 없을 경우: 5(외부) x 3(내부) = 15회 시도로 timeout이 컴파운딩되어
    최악 수 시간 대기가 발생할 수 있습니다.
    """

    max_retries: int = 0

    def _merge_langfuse_config(self, config=None):
        """기존 config에 Langfuse CallbackHandler를 안전하게 병합합니다.

        [존재 이유]
        LangGraph ToolNode 등이 내부적으로 자체 callbacks를 config에 전달합니다.
        기존 callbacks를 덮어쓰면 도구 호출이 실패하므로,
        반드시 append 방식으로 병합해야 합니다.

        Args:
            config: 기존 LangChain config (None 가능)

        Returns:
            Langfuse 콜백이 병합된 config (추적 비활성화 시 원본 그대로 반환)
        """
        return _langfuse_tracker.merge_config(config)

    def _get_total_timeout(self) -> float:
        """전체 retry 루프의 시간 제한을 계산합니다.

        단일 요청 timeout(request_timeout)의 2배를 전체 제한으로 사용합니다.
        이것이 없을 경우: 5회 retry x request_timeout = 최대 25분 무응답 대기 가능.
        2배로 설정하면 최소 1회 완전한 timeout + 1회 빠른 retry가 가능하되
        무한 대기는 방지됩니다.
        """
        raw_timeout = self.request_timeout
        if isinstance(raw_timeout, (list, tuple)):
            raw_timeout = max(raw_timeout)
        return (raw_timeout or 300) * 2

    def invoke(self, input, config=None, **kwargs):
        """동기 호출 시 재시도 로직 + Langfuse 자동 추적 적용"""
        config = self._merge_langfuse_config(config)
        max_retries = 5
        total_timeout = self._get_total_timeout()
        start_time = time.monotonic()

        for i in range(max_retries):
            # 전체 시간 제한 초과 시 마지막 에러와 함께 즉시 중단
            elapsed = time.monotonic() - start_time
            if elapsed > total_timeout:
                raise TimeoutError(
                    f"RetryableChatOpenAI 전체 재시도 시간 제한 초과 "
                    f"({total_timeout:.0f}초 중 {elapsed:.0f}초 경과, "
                    f"{i}회 시도 후 중단)"
                )

            try:
                return super().invoke(input, config=config, **kwargs)
            except _NON_RETRYABLE_ERRORS:
                # 구조적 에러는 재시도 무의미 → 즉시 전파
                raise
            except _RETRYABLE_ERRORS as e:
                # 일시적 에러 → exponential backoff 후 재시도
                if i == max_retries - 1:
                    raise
                wait_time = (2 ** i) + 1
                print(
                    f"[Retry {i+1}/{max_retries}] "
                    f"{type(e).__name__}: {e} -> {wait_time}s 후 재시도"
                )
                time.sleep(wait_time)
                continue
            except Exception:
                # 분류되지 않은 에러 → 즉시 전파 (디버깅 용이)
                raise

    async def ainvoke(self, input, config=None, **kwargs):
        """비동기 호출 시 재시도 로직 + Langfuse 자동 추적 적용"""
        config = self._merge_langfuse_config(config)
        max_retries = 5
        total_timeout = self._get_total_timeout()
        start_time = time.monotonic()

        for i in range(max_retries):
            # 전체 시간 제한 초과 시 마지막 에러와 함께 즉시 중단
            elapsed = time.monotonic() - start_time
            if elapsed > total_timeout:
                raise TimeoutError(
                    f"RetryableChatOpenAI 전체 재시도 시간 제한 초과 "
                    f"({total_timeout:.0f}초 중 {elapsed:.0f}초 경과, "
                    f"{i}회 시도 후 중단)"
                )

            try:
                return await super().ainvoke(input, config=config, **kwargs)
            except _NON_RETRYABLE_ERRORS:
                # 구조적 에러는 재시도 무의미 → 즉시 전파
                raise
            except _RETRYABLE_ERRORS as e:
                # 일시적 에러 → exponential backoff 후 재시도
                if i == max_retries - 1:
                    raise
                wait_time = (2 ** i) + 1
                print(
                    f"[Retry {i+1}/{max_retries}] "
                    f"{type(e).__name__}: {e} -> {wait_time}s 후 재시도"
                )
                await asyncio.sleep(wait_time)
                continue
            except Exception:
                # 분류되지 않은 에러 → 즉시 전파 (디버깅 용이)
                raise


class ModelName(StrEnum):
    GPT_4_1_MINI = "gpt-4.1-mini"
    GPT_4_1 = "gpt-4.1"
    GPT_5_MINI = "gpt-5-mini"
    GPT_5 = "gpt-5"
    GPT_5_LASTEST = "gpt-5-chat-latest"
    GPT_5_PRO = "gpt-5-pro-2025-10-06"

    CLAUDE_OPUS_4_1_20250805 = "claude-opus-4-1-20250805"
    CLAUDE_SONNET_4_5_20250929 = "claude-sonnet-4-5-20250929"

    GEMINI_2_5_PRO = "gemini-2.5-pro"


class LLMProfile(StrEnum):

    # 개발자가 사용할 LLM
    DEV = ModelName.GPT_5_MINI.value

    # 챗봇용 LLM
    CHAT_BOT = ModelName.GPT_5_MINI.value

    # 분석용 LLM
    ANALYSIS = ModelName.GPT_5_MINI.value

    # 보고서 작성용 LLM
    REPORT = ModelName.GPT_5.value

    # 보고서 PPT 변환용 LLM
    RENDERING = ModelName.CLAUDE_SONNET_4_5_20250929

    @staticmethod
    def renderer_llm():
        return RetryableChatOpenAI(
            model=LLMProfile.RENDERING.value,
            temperature=0,
            request_timeout=300,
        )
        # return ChatAnthropic(
        #     model_name=LLMProfile.RENDERING.value, temperature=0.0, max_tokens=32000
        # )

    @staticmethod
    def dev_llm():
        return RetryableChatOpenAI(
            model=LLMProfile.DEV.value,
            temperature=0,
            request_timeout=300,
        )

    @staticmethod
    def chat_bot_llm():
        return RetryableChatOpenAI(
            model=LLMProfile.CHAT_BOT.value,
            temperature=0,
            request_timeout=300,
        )

    @staticmethod
    def analysis_llm():
        return RetryableChatOpenAI(
            model=LLMProfile.ANALYSIS.value,
            temperature=0,
            request_timeout=300,
            # reasoning_effort="high", # minimal, low, medium, high
            # verbosity="high",
        )

    # @staticmethod
    # def analysis_llm():
    #     return ChatGoogleGenerativeAI(
    #         model=LLMProfile.ANALYSIS.value,
    #         temperature=0,
    #         max_tokens=8192,  # Gemini 최대 출력 토큰
    #         max_retries=0,  # max_retries를 0으로 설정하여 SDK 호환성 문제 방지
    #         google_api_key=os.getenv("GEMINI_API_KEY"),  # 환경변수 미설정 시 직접 전달
    #     )

    @staticmethod
    def report_llm():
        # jung_min_jae 6회 순차 호출(4세그먼트+검토+수정), 대용량 컨텍스트 고려
        return RetryableChatOpenAI(
            model=LLMProfile.REPORT.value,
            request_timeout=300,
        )
