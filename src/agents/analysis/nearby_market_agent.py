# agents/analysis/nearby_market_agent.py
"""
주변 시세 분석 에이전트 (NearbyMarket).

파이프라인:
  gemini_search → [kakao_api_distance, get_real_estate_price, perplexity_search]
               → analysis_setting → agent (ReAct loop) → END

Structured Output 적용:
  - gemini_search_tool   : Gemini API에 NearbyMarketGeminiSchema 강제
  - perplexity_search_tool: Perplexity API에 NearbyMarketPerplexitySchema 강제
  → 하류 노드에서 json.loads() / extract_json_from_text() 불필요
"""

import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from agents.state.analysis_state import NearbyMarketState
from agents.state.start_state import StartInput
from agents.state.structured_schemas import (
    AnalysisReport,
    NearbyMarketGeminiSchema,
    NearbyMarketPerplexitySchema,
)
from utils.sanitize import strip_think_tool
from prompts import PromptManager, PromptType
from tools.context_to_csv import nearby_complexes_to_csv
from tools.gemini_search_tool import gemini_search
from tools.kakao_api_distance_tool import get_location_profile
from tools.perplexity_search_tool import (
    perplexity_search,
    perplexity_search_structured,
)
from tools.real_time_sale_search_api_tool import get_real_estate_price
from utils.llm import LLMProfile
from utils.util import get_today_str


# ---------------------------------------------------------------------------
# LLM 및 Tool 설정
# ---------------------------------------------------------------------------

llm = LLMProfile.analysis_llm()


@tool(parse_docstring=False)
def think_tool(reflection: str) -> str:
    """
    [역할]
    당신은 사업지 주변 매매 아파트, 분양 아파트들 각각의 시세와 입지를 정리하는 전문가의
    내부 반성·점검(Reflection) 담당자입니다.
    최종 보고서에 들어갈 본문(Markdown)을 쓰기 직전에, 데이터 품질·핵심 수치·리스크·보고서용
    한 줄 메시지를 짧고 구조적으로 요약해 think_tool에 기록합니다.
    이 반성문은 내부용이며, 최종 보고서에 직접 노출되지 않습니다.

    [언제 호출할 것인지]
    - Node 하나의 결과를 받고 tool을 사용하기 전에 호출(필수)
    - 데이터 수집/정제 → 핵심 수치 산출 → 시계열 해석을 마친 직후 1회 호출(필수)
    - 추가 데이터로 최신 데이터로 바뀌면 갱신 시마다 1회 재호출(선택)

    [강력 지시]
    - 해당 지역에 관련된 내용만 기록
    - 허상 가정, 출처 수치 금지
    - Think step by step 방식으로 생각하세요.
    - 다음 단계(보고서 에이전트)가 바로 쓸 수 있는 한 줄 핵심 메시지 포함

    [나쁜 예]
    - "경제가 좋아진듯함. 분위기 좋음."(수치·기간·단위·근거 없음)
    - "인근 해운대의 입지는 이렇다~"(대상 지역 외 서술)
    - "향후 집값 상승 확실."(근거 없는 단정)

    [검증 체크리스트]
    - 정량 수치가 어긋난 것이 있는가?
    - GPT가 시계열 판단하기에 좋은 형식으로 되어있는가?
    - 잘못된 내용은 없는가?
    """
    return f"Reflection recorded: {reflection}"


tool_list = [think_tool, perplexity_search, get_real_estate_price, get_location_profile]
llm_with_tools = llm.bind_tools(tool_list)
tool_node = ToolNode(tool_list)
format_llm = LLMProfile.dev_llm().with_structured_output(AnalysisReport)


# ---------------------------------------------------------------------------
# State 키 상수 (Single Source of Truth)
# ---------------------------------------------------------------------------

output_key = NearbyMarketState.KEY.nearby_market_output
start_input_key = NearbyMarketState.KEY.start_input
web_context_key = NearbyMarketState.KEY.web_context
messages_key = NearbyMarketState.KEY.messages
target_area_key = StartInput.KEY.target_area
main_type_key = StartInput.KEY.main_type
total_units_key = StartInput.KEY.total_units
kakao_api_distance_context_key = NearbyMarketState.KEY.kakao_api_distance_context
kakao_api_distance_download_link_key = (
    NearbyMarketState.KEY.kakao_api_distance_download_link
)
gemini_search_key = NearbyMarketState.KEY.gemini_search
real_estate_price_context_key = NearbyMarketState.KEY.real_estate_price_context
perplexity_search_key = NearbyMarketState.KEY.perplexity_search


# ---------------------------------------------------------------------------
# 노드 함수
# ---------------------------------------------------------------------------


def gemini_search_tool(state: NearbyMarketState) -> NearbyMarketState:
    """
    Gemini를 통해 사업지 주변 매매아파트 3개·분양아파트 3개의 시세를 검색합니다.

    [Structured Output 적용]
    NearbyMarketGeminiSchema를 response_schema로 전달하므로
    Gemini API가 순수 JSON 문자열을 반환합니다.
    반환값을 json.loads()하면 하류 노드에서 바로 dict로 소비할 수 있습니다.
    """
    start_input = state[start_input_key]
    target_area = start_input[target_area_key]
    main_type = start_input[main_type_key]
    total_units = start_input[total_units_key]
    date = get_today_str()

    # 프롬프트: 입력(동적 변수) 부분만 정의, 출력 형태는 스키마가 담당
    # → <OUTPUT> 예시 JSON을 제거하여 프롬프트를 간소화
    prompt = f"""
    <CONTEXT>
    사업지: {target_area}
    세대수: {total_units}세대
    타입: {main_type}
    일시: {date}
    </CONTEXT>

    <GOAL>
    - <CONTEXT>의 주소, 규모, 타입, 일시가 유사하고,
      최단거리에 있는 매매아파트 3개를 찾아 각각의 평당매매가격(준공연도 포함),
      분양아파트 3개를 찾아 각각의 평당분양가격을 출력해 주세요.
    </GOAL>

    <RULE>
    - 주소는 반드시 공식 행정구역명을 사용하세요 (예: "서울특별시", "경기도", "부산광역시").
    - "서울시" 대신 "서울특별시", "경기" 대신 "경기도"처럼 정확한 행정구역명을 사용하세요.
    - 카카오 지도 API가 인식할 수 있는 정확한 주소 형식으로 작성하세요.
    - 정확한 정보인지 확인하고 출력해 주세요.
    </RULE>
    """

    # Structured Output: NearbyMarketGeminiSchema 스키마 강제
    raw_json = gemini_search(
        prompt,
        response_schema=NearbyMarketGeminiSchema.model_json_schema(),
    )

    return {gemini_search_key: raw_json}


def kakao_api_distance_tool(state: NearbyMarketState) -> NearbyMarketState:
    """
    gemini_search_tool이 반환한 아파트 주소를 받아
    카카오 API로 입지 정보와 사업지까지의 거리를 조회합니다.

    [Structured Output 연계]
    gemini_search_key에는 이미 스키마를 준수하는 JSON 문자열이 저장되어 있으므로
    extract_json_from_text() 없이 json.loads()로 바로 파싱합니다.
    """
    start_input = state[start_input_key]
    target_area = start_input[target_area_key]
    gemini_raw = state[gemini_search_key]

    try:
        gemini_data = json.loads(gemini_raw)
    except (json.JSONDecodeError, TypeError) as e:
        print(f"[ERROR] Gemini JSON 파싱 실패 (kakao_api_distance_tool): {e}")
        return {kakao_api_distance_context_key: []}

    all_result = []

    def _query_with_retry(address: str) -> dict:
        """주소 조회 실패 시 앞 3 토큰으로 재시도합니다."""
        result = get_location_profile.invoke({"address": address})
        if result.get("좌표") is None:
            parts = address.split()
            if len(parts) > 1:
                retry_result = get_location_profile.invoke(
                    {"address": " ".join(parts[:3])}
                )
                if retry_result.get("좌표") is not None:
                    retry_result["주소"] = address
                    return retry_result
        return result

    for apt in gemini_data.get("매매아파트", []):
        result = _query_with_retry(apt["주소와단지명"])
        result["타입"] = "매매아파트"
        result["원본정보"] = apt
        all_result.append(result)

    for apt in gemini_data.get("분양아파트", []):
        result = _query_with_retry(apt["주소와단지명"])
        result["타입"] = "분양아파트"
        result["원본정보"] = apt
        all_result.append(result)

    return {
        kakao_api_distance_context_key: all_result,
        kakao_api_distance_download_link_key: nearby_complexes_to_csv(
            all_result, target_area
        ),
    }


def get_real_estate_price_tool(state: NearbyMarketState) -> NearbyMarketState:
    """
    gemini_search_tool이 반환한 매매아파트 주소를 받아
    실거래가를 조회합니다.
    """
    gemini_raw = state[gemini_search_key]

    try:
        gemini_data = json.loads(gemini_raw)
    except (json.JSONDecodeError, TypeError) as e:
        print(f"[ERROR] Gemini JSON 파싱 실패 (get_real_estate_price_tool): {e}")
        return {real_estate_price_context_key: []}

    sale_results = []
    for apt in gemini_data.get("매매아파트", []):
        result_str = get_real_estate_price.invoke(
            {"address_or_apartment": apt["주소와단지명"]}
        )
        result = json.loads(result_str)
        result["타입"] = "매매아파트"
        sale_results.append(result)

    return {real_estate_price_context_key: sale_results}


def perplexity_search_tool(state: NearbyMarketState) -> NearbyMarketState:
    """
    gemini_search_tool이 반환한 분양아파트 목록을 Perplexity로 최신 정보 검증합니다.

    [Structured Output 적용]
    perplexity_search_structured()를 사용하여 NearbyMarketPerplexitySchema를 강제합니다.
    반환값이 스키마를 준수하는 순수 JSON 문자열이므로 파싱이 단순해집니다.
    """
    gemini_raw = state[gemini_search_key]

    try:
        gemini_data = json.loads(gemini_raw)
    except (json.JSONDecodeError, TypeError) as e:
        print(f"[ERROR] Gemini JSON 파싱 실패 (perplexity_search_tool): {e}")
        return {perplexity_search_key: ""}

    new_apts = gemini_data.get("분양아파트", [])
    if not new_apts:
        return {perplexity_search_key: ""}

    # 검색 쿼리 구성: 주소와단지명 + 주요 정보를 포함한 자연어 질의
    query_parts = []
    for apt in new_apts:
        address = apt.get("주소와단지명", "")
        apt_name = address.split()[-1] if address else ""
        query_text = (
            f"{address} {apt_name} 분양가격 평당분양가 청약경쟁률 계약조건 "
            f"{apt.get('청약일시', '')}"
        )
        current_price = apt.get("평당분양가격", "")
        if current_price and current_price != "검증 불가":
            query_text += f" {current_price}"
        query_parts.append(query_text)

    combined_query = f"""
    다음 분양아파트 {len(query_parts)}개의 정확한 분양 정보를 검색하고 검증해주세요:

    {chr(10).join(f'{i+1}. {q}' for i, q in enumerate(query_parts))}

    각 아파트의 다음 정보를 정확히 찾아주세요:
    - 평당 분양가격 (만원 단위)
    - 계약조건 (계약금, 중도금 비율 등)
    - 청약경쟁률 (비율 형식)
    - 청약일시 (정확한 날짜)
    """

    # Structured Output: NearbyMarketPerplexitySchema 스키마 강제
    result_text = perplexity_search_structured(
        query=combined_query,
        response_schema=NearbyMarketPerplexitySchema.model_json_schema(),
    )

    return {perplexity_search_key: result_text}


def analysis_setting(state: NearbyMarketState) -> NearbyMarketState:
    """
    수집된 컨텍스트를 종합하여 LLM 메시지(System + Human)를 구성합니다.

    [gemini_search 직렬화]
    gemini_search_key는 JSON 문자열이므로 프롬프트에 그대로 주입할 수 있습니다.
    Pydantic dict가 아닌 원시 JSON 문자열을 사용하므로 별도 직렬화가 불필요합니다.
    """
    start_input = state[start_input_key]
    target_area = start_input[target_area_key]
    total_units = start_input[total_units_key]
    main_type = start_input[main_type_key]
    gemini_search_data = state.get(gemini_search_key, "")
    kakao_api_distance_context = state.get(kakao_api_distance_context_key, "")
    real_estate_price_context = state.get(real_estate_price_context_key, "")
    perplexity_search_data = state.get(perplexity_search_key, "")

    system_prompt = PromptManager(PromptType.NEARBY_MARKET_SYSTEM).get_prompt(
        target_area=target_area,
        total_units=total_units,
        main_type=main_type,
        date=get_today_str(),
        gemini_search=gemini_search_data,
        kakao_api_distance_context=kakao_api_distance_context,
        real_estate_price_context=real_estate_price_context,
        perplexity_search=perplexity_search_data,
    )
    human_prompt = PromptManager(PromptType.NEARBY_MARKET_HUMAN).get_prompt(
        target_area=target_area,
        total_units=total_units,
        main_type=main_type,
        date=get_today_str(),
        gemini_search=gemini_search_data,
        kakao_api_distance_context=kakao_api_distance_context,
        real_estate_price_context=real_estate_price_context,
        perplexity_search=perplexity_search_data,
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt),
    ]
    return {**state, messages_key: messages}


def agent(state: NearbyMarketState) -> NearbyMarketState:
    """ReAct 루프를 수행합니다. 결과 저장은 format_output에서 담당합니다."""
    messages = state.get(messages_key, [])
    response = llm_with_tools.invoke(messages)
    new_messages = messages + [response]
    return {**state, messages_key: new_messages}


def format_output(state: NearbyMarketState) -> NearbyMarketState:
    """ReAct 루프 종료 후 think_tool 반성문을 제거하고 깨끗한 보고서만 추출합니다."""
    messages = state.get(messages_key, [])
    raw_content = messages[-1].content

    # 1차 방어: 정규식으로 think_tool(reflection: "...") 패턴 제거
    cleaned = strip_think_tool(raw_content)

    # 2차 방어: Structured Output으로 순수 보고서만 추출
    report = format_llm.invoke(cleaned)

    new_state = {**state}
    new_state[output_key] = {
        "result": report.result,
        gemini_search_key: state.get(gemini_search_key),
        kakao_api_distance_context_key: state.get(kakao_api_distance_context_key),
        real_estate_price_context_key: state.get(real_estate_price_context_key),
        perplexity_search_key: state.get(perplexity_search_key),
        kakao_api_distance_download_link_key: state.get(
            kakao_api_distance_download_link_key
        ),
    }
    return new_state


def router(state: NearbyMarketState) -> str:
    """Tool 호출 여부에 따라 다음 노드를 결정합니다."""
    messages = state[messages_key]
    last_ai_message = messages[-1]
    if last_ai_message.tool_calls:
        return "tools"
    return "format_output"


# ---------------------------------------------------------------------------
# 그래프 빌드
# ---------------------------------------------------------------------------

_web_context_key = "web_search"
_analysis_setting_key = "analysis_setting"
_tools_key = "tools"
_agent_key = "agent"
_gemini_search_node_key = "gemini_search"
_kakao_api_distance_key = "kakao_api_distance"
_real_estate_price_key = "real_estate_price"
_perplexity_search_node_key = "perplexity_search"

graph_builder = StateGraph(NearbyMarketState)

graph_builder.add_node(_gemini_search_node_key, gemini_search_tool)
graph_builder.add_node(_kakao_api_distance_key, kakao_api_distance_tool)
graph_builder.add_node(_real_estate_price_key, get_real_estate_price_tool)
graph_builder.add_node(_perplexity_search_node_key, perplexity_search_tool)
_format_output_key = "format_output"

graph_builder.add_node(_analysis_setting_key, analysis_setting)
graph_builder.add_node(_tools_key, tool_node)
graph_builder.add_node(_agent_key, agent)
graph_builder.add_node(_format_output_key, format_output)

graph_builder.add_edge(START, _gemini_search_node_key)
graph_builder.add_edge(_gemini_search_node_key, _kakao_api_distance_key)
graph_builder.add_edge(_gemini_search_node_key, _real_estate_price_key)
graph_builder.add_edge(_gemini_search_node_key, _perplexity_search_node_key)

graph_builder.add_edge(_kakao_api_distance_key, _analysis_setting_key)
graph_builder.add_edge(_real_estate_price_key, _analysis_setting_key)
graph_builder.add_edge(_perplexity_search_node_key, _analysis_setting_key)
graph_builder.add_edge(_analysis_setting_key, _agent_key)

graph_builder.add_conditional_edges(_agent_key, router, [_tools_key, _format_output_key])
graph_builder.add_edge(_tools_key, _agent_key)
graph_builder.add_edge(_format_output_key, END)

nearby_market_graph = graph_builder.compile()
