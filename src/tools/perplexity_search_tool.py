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


def _track_perplexity_generation(name: str, model: str, query: str, result: str):
    """Perplexity API 호출을 Langfuse에 generation으로 기록합니다.

    [존재 이유]
    Perplexity SDK는 LangChain CallbackHandler를 지원하지 않으므로
    수동으로 Langfuse에 generation 정보를 전송해야 합니다.

    Args:
        name:   추적 이름 (예: "perplexity-search")
        model:  사용된 모델명
        query:  입력 쿼리
        result: API 응답 텍스트
    """
    langfuse_client = _langfuse_tracker.get_client()
    if langfuse_client is None:
        return

    try:
        with langfuse_client.start_as_current_observation(
            as_type="generation",
            name=name,
            model=model,
            input=query[:500],
        ) as span:
            span.update(output=result[:2000])
    except Exception as e:
        logger.debug("Langfuse Perplexity 추적 실패 (무시 가능): %s", e)


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
    response = client.chat.completions.create(
        model=_DEFAULT_MODEL,
        messages=[{"role": "user", "content": query}],
    )

    content = response.choices[0].message.content

    citations = []
    if hasattr(response, "citations") and response.citations:
        citations = response.citations

    result = content
    if citations:
        result += "\n\n[Perplexity 출처]"
        for idx, citation in enumerate(citations, 1):
            result += f"\n{idx}. {citation}"
    else:
        result += "\n\n[출처: Perplexity AI 검색]"

    # Langfuse 수동 추적
    _track_perplexity_generation("perplexity-search", _DEFAULT_MODEL, query, result)

    return result


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
    # response_format: type="json_schema" + json_schema dict 전달
    # 참고: https://docs.perplexity.ai/guides/structured-outputs
    response = client.chat.completions.create(
        model=_DEFAULT_MODEL,
        messages=[{"role": "user", "content": query}],
        response_format={
            "type": "json_schema",
            "json_schema": {"schema": response_schema},
        },
    )

    result = response.choices[0].message.content

    # Langfuse 수동 추적
    _track_perplexity_generation(
        "perplexity-search-structured", _DEFAULT_MODEL, query, result
    )

    return result
