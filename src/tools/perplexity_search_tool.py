# tools/perplexity_search_tool.py
"""
Perplexity AI API 래퍼 모듈.

공식 문서: https://docs.perplexity.ai
Structured Output: https://docs.perplexity.ai/guides/structured-outputs
"""

import os
import logging
from typing import Optional

from dotenv import load_dotenv
from langchain_core.tools import tool
from perplexity import Perplexity

# Langfuse 수동 추적 (Graceful Degradation)
from utils.langfuse_tracker import tracker as _langfuse_tracker

load_dotenv()

logger = logging.getLogger(__name__)

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
client = Perplexity(api_key=PERPLEXITY_API_KEY)

_DEFAULT_MODEL = "sonar-reasoning-pro"


@_langfuse_tracker.observe(as_type="generation")
def _call_perplexity_api(
    name: str,
    query: str,
    response_schema: Optional[dict] = None
) -> str:
    """Perplexity API 호출 및 Langfuse 추적을 수행하는 헬퍼 함수.

    [존재 이유]
    일반 검색(perplexity_search)과 구조화 검색(perplexity_search_structured)
    모두에서 중복되는 API 호출 및 추적 로직을 통합합니다.
    """
    _langfuse_tracker.update_observation(
        name=name,
        model=_DEFAULT_MODEL,
        input=query[:500],
        metadata={"has_schema": response_schema is not None},
    )

    kwargs: dict = {
        "model": _DEFAULT_MODEL,
        "messages": [{"role": "user", "content": query}]
    }

    if response_schema is not None:
         kwargs["response_format"] = {
             "type": "json_schema",
             "json_schema": {"schema": response_schema},
         }

    try:
        response = client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content

        # citations 추가 로직 (일반 텍스트 응답일 때만)
        if response_schema is None:
            citations = getattr(response, "citations", [])
            if citations:
                content += "\n\n[Perplexity 출처]"
                for idx, citation in enumerate(citations, 1):
                    content += f"\n{idx}. {citation}"
            else:
                content += "\n\n[출처: Perplexity AI 검색]"

        usage = getattr(response, "usage", None)
        usage_meta = None
        if usage:
            input_tokens = getattr(usage, "prompt_tokens", 0)
            output_tokens = getattr(usage, "completion_tokens", 0)
            total_tokens = getattr(usage, "total_tokens", input_tokens + output_tokens)
            usage_meta = {
                "input": input_tokens,
                "output": output_tokens,
                "total": total_tokens,
            }

        _langfuse_tracker.update_observation(
            output=content[:2000],
            usage=usage_meta
        )

        return content

    except Exception as e:
        error_msg = f"Perplexity API 오류: {str(e)}"
        _langfuse_tracker.update_observation(
            output=error_msg,
            level="ERROR",
            status_message=str(e),
        )
        # 에이전트가 재시도할 수 있도록 예외를 던지거나 에러 문자열을 반환합니다.
        # 기존 로직과 맞추기 위해 에러 발생 시 Exception을 그대로 raise 할 수도 있으나,
        # Gemini 쪽과 유사하게 에러 메시지 반환을 선호할 수 있습니다. 
        # 원본 구조를 최대한 유지합니다.
        raise


@tool
def perplexity_search(query: str) -> str:
    """Perplexity AI를 사용하여 최신 정보를 검색합니다.

    이 도구는 실시간 웹 검색을 통해 최신 정보, 뉴스, 데이터를 찾아
    사실 확인과 검증을 수행합니다.
    부동산 호재, 개발 계획, 교통 인프라 등의 정보를 검증할 때 사용하세요.

    Args:
        query: 검색할 질문이나 프롬프트. 구체적이고 명확한 질문을 사용하세요.

    Returns:
        str: Perplexity AI의 검색 결과 및 출처 링크
    """
    return _call_perplexity_api("perplexity-search", query)


def perplexity_search_structured(
    query: str,
    response_schema: dict,
    citations_key: Optional[str] = None,
) -> str:
    """
    Structured Output이 적용된 Perplexity 검색 함수.

    LangChain @tool 데코레이터가 없는 일반 함수입니다.
    에이전트 노드 함수에서 JSON 스키마를 강제해야 할 때 직접 호출합니다.

    [perplexity_search vs perplexity_search_structured]
    - perplexity_search   : LLM이 tool_call로 자유 질의 → 텍스트 반환 (policy_agent 등)
    - perplexity_search_structured : 노드 함수에서 스키마 강제 → 순수 JSON 반환 (nearby_market_agent 등)

    [존재 이유]
    스키마 없이 Perplexity를 호출하면 응답에 마크다운·출처 링크가 혼재되어
    json.loads()가 실패할 수 있습니다. 이 함수는 API 레벨에서 JSON Schema를 강제하므로
    하류에서 별도 파싱 로직이 필요하지 않습니다.

    Args:
        query:           Perplexity에 전달할 검색 쿼리.
                         동적 변수가 포함된 f-string을 그대로 전달해도 됩니다.
        response_schema: Pydantic BaseModel.model_json_schema() 로 생성한 dict.
                         API가 이 스키마를 준수한 JSON 문자열을 반환합니다.
        citations_key:   (미사용) 출처를 별도 키에 담으려는 경우를 위한 예약 파라미터.

    Returns:
        str: response_schema를 준수하는 순수 JSON 문자열.
             json.loads() 로 바로 파싱 가능합니다.

    공식 문서: https://docs.perplexity.ai/guides/structured-outputs
    """
    return _call_perplexity_api("perplexity-search-structured", query, response_schema)
