# tools/gemini_search_tool.py
"""
Google Gemini API 래퍼 모듈.

공식 문서: https://ai.google.dev/gemini-api/docs
Structured Output: https://ai.google.dev/gemini-api/docs/structured-output
"""

import os
import time
from typing import Optional

import google.genai as genai
from dotenv import load_dotenv

# Langfuse 수동 추적 (Graceful Degradation)
from utils.langfuse_tracker import tracker as _langfuse_tracker

load_dotenv()

# Gemini API 클라이언트 생성
# 공식 문서: https://ai.google.dev/gemini-api/docs/python-sdk
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

_DEFAULT_MODEL = "gemini-2.5-pro"
_MAX_RETRIES = 3
_RETRY_DELAY_SECONDS = 2


def gemini_search(prompt: str, response_schema: Optional[dict] = None) -> str:
    """
    Gemini API를 사용하여 프롬프트에 대한 응답을 생성합니다.
    서버 오류 시 최대 3번까지 재시도합니다.

    [Langfuse 추적]
    호출 시 Langfuse에 generation으로 기록됩니다.
    @tracker.observe 데코레이터를 사용하여 안전하게 토큰과 비용을 추적합니다.
    LANGFUSE_ENABLED=false이면 추적 없이 기존과 동일하게 동작합니다.

    [response_schema 없을 때]
    자유 형식 텍스트를 반환합니다. 기존 동작과 동일합니다.

    [response_schema 있을 때]
    Gemini API가 schema를 준수한 순수 JSON 문자열을 반환합니다.
    마크다운 코드 블록, 설명 텍스트가 포함되지 않으므로
    하류에서 extract_json_from_text() 없이 바로 json.loads() 가능합니다.

    Args:
        prompt:          Gemini에게 전달할 프롬프트 텍스트.
                         동적 변수(target_area, total_units 등)는 이 인자에서 처리하며,
                         response_schema(출력 형태)와 완전히 분리됩니다.
        response_schema: Pydantic BaseModel.model_json_schema() 로 생성한 dict.
                         None이면 비구조화 출력(기존 동작)을 유지합니다.

    Returns:
        Gemini가 생성한 응답 텍스트.
        response_schema 지정 시: 순수 JSON 문자열.
        response_schema 미지정 시: 자유 형식 텍스트.

    Raises:
        최대 재시도 횟수 초과 시 오류 메시지 문자열을 반환합니다(예외 전파 없이).
    """

@_langfuse_tracker.observe(as_type="generation")
def gemini_search(prompt: str, response_schema: Optional[dict] = None) -> str:
    # response_schema 가 전달된 경우에만 JSON 강제 모드로 호출
    # 참고: https://ai.google.dev/gemini-api/docs/structured-output
    generation_config = (
        {
            "response_mime_type": "application/json",
            "response_json_schema": response_schema,
        }
        if response_schema is not None
        else None
    )

    # Langfuse 수동 추적: 컨텍스트에 메타데이터 기록
    _langfuse_tracker.update_observation(
        name="gemini-search",
        model=_DEFAULT_MODEL,
        input=prompt[:500],  # 프롬프트 앞부분만 기록 (비용 절약)
        metadata={"has_schema": response_schema is not None},
    )

    for attempt in range(_MAX_RETRIES):
        try:
            # Ref: https://googleapis.github.io/python-genai/
            response = client.models.generate_content(
                model=_DEFAULT_MODEL,
                contents=prompt,
                config=generation_config,
                timeout=180.0,
            )
            result_text = response.text

            # Langfuse: 성공 시 출력 및 usage 기록
            try:
                # response: 데이터를 꺼내올 대상 객체,
                # usage_metadata: 사용량 관련 메타데이터
                usage = getattr(response, "usage_metadata", None)
                usage_details = None
                if usage:
                    input_tokens = getattr(usage, "prompt_token_count", 0)
                    output_tokens = getattr(usage, "candidates_token_count", 0)
                    total_tokens = getattr(usage, "total_token_count", input_tokens + output_tokens)
                    
                    usage_details = {
                        "input": input_tokens,
                        "output": output_tokens,
                        "total": total_tokens
                    }

                _langfuse_tracker.update_observation(
                    output=result_text[:500],
                    usage=usage_details,
                )
            except Exception:
                pass

            return result_text

        except Exception as e:
            error_message = str(e)
            is_last_attempt = attempt == _MAX_RETRIES - 1

            if is_last_attempt:
                error_result = f"Gemini API 오류: {error_message}. 잠시 후 다시 시도해주세요."

                # Langfuse: 실패 시 에러 기록
                try:
                    _langfuse_tracker.update_observation(
                        output=error_result,
                        level="ERROR",
                        status_message=error_message,
                    )
                except Exception:
                    pass

                return error_result

            time.sleep(_RETRY_DELAY_SECONDS)

    return "Gemini API 호출 실패"


if __name__ == "__main__":
    test_prompt = f"""
    <CONTEXT>
    사업지: 서울특별시 강남구 언주로 711
    세대수: 1000세대
    타입: 84m²
    일시: 2025-11-07
    </CONTEXT>

    <GOAL>
    - <CONTEXT>의 주소, 규모, 타입, 일시가 유사하고, 최단거리에 있는
      매매아파트 3개의 평당매매가격과 분양아파트 3개의 평당분양가격을 찾아주세요.
    </GOAL>
    """
    result = gemini_search(test_prompt)
    print(result)
