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

    for attempt in range(_MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=_DEFAULT_MODEL,
                contents=prompt,
                config=generation_config,
            )
            return response.text

        except Exception as e:
            error_message = str(e)
            is_last_attempt = attempt == _MAX_RETRIES - 1

            if is_last_attempt:
                return f"Gemini API 오류: {error_message}. 잠시 후 다시 시도해주세요."

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
