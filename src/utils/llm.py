from enum import StrEnum
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
import os
import time
import asyncio
from dotenv import load_dotenv
from functools import wraps

load_dotenv()


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


class RetryableChatOpenAI(ChatOpenAI):
    """Exponential Backoff 재시도 로직이 적용된 ChatOpenAI 클래스"""

    def invoke(self, input, config=None, **kwargs):
        """동기 호출 시 재시도 로직 적용"""
        max_retries = 5

        for i in range(max_retries):
            try:
                return super().invoke(input, config=config, **kwargs)
            except Exception as e:
                error_str = str(e)

                if i == max_retries - 1:
                    raise

                if "429" in error_str or "rate_limit" in error_str.lower():
                    wait_time = (2**i) + 1
                    print(f"Rate limit hit. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                if "api" in error_str.lower() or "error" in error_str.lower():
                    wait_time = (2**i) + 1
                    print(f"API error occurred. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                raise

    async def ainvoke(self, input, config=None, **kwargs):
        """비동기 호출 시 재시도 로직 적용"""
        max_retries = 5

        for i in range(max_retries):
            try:
                return await super().ainvoke(input, config=config, **kwargs)
            except Exception as e:
                error_str = str(e)

                if i == max_retries - 1:
                    raise

                if "429" in error_str or "rate_limit" in error_str.lower():
                    wait_time = (2**i) + 1
                    print(f"Rate limit hit. Waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue

                if "api" in error_str.lower() or "error" in error_str.lower():
                    wait_time = (2**i) + 1
                    print(f"API error occurred. Waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue

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
    DEV = ModelName.GPT_4_1_MINI.value

    # 챗봇용 LLM
    CHAT_BOT = ModelName.GPT_4_1.value

    # 분석용 LLM
    ANALYSIS = ModelName.GPT_4_1.value

    # 보고서 작성용 LLM
    REPORT = ModelName.GPT_5.value

    # 보고서 PPT 변환용 LLM
    RENDERING = ModelName.CLAUDE_SONNET_4_5_20250929

    @staticmethod
    def renderer_llm():
        return RetryableChatOpenAI(
            model=LLMProfile.RENDERING.value,
            temperature=0,
        )
        # return ChatAnthropic(
        #     model_name=LLMProfile.RENDERING.value, temperature=0.0, max_tokens=32000
        # )

    @staticmethod
    def dev_llm():
        return RetryableChatOpenAI(
            model=LLMProfile.DEV.value,
            temperature=0,
        )

    @staticmethod
    def chat_bot_llm():
        return RetryableChatOpenAI(
            model=LLMProfile.CHAT_BOT.value,
            temperature=0,
        )

    @staticmethod
    def analysis_llm():
        return RetryableChatOpenAI(
            model=LLMProfile.ANALYSIS.value,
            temperature=0,
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
        return RetryableChatOpenAI(
            model=LLMProfile.REPORT.value,
        )
