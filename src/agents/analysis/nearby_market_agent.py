from langgraph.graph import StateGraph, START, END
from agents.state.analysis_state import NearbyMarketState
from agents.state.start_state import StartInput
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from utils.util import get_today_str
from utils.llm import LLMProfile
from langchain_openai import ChatOpenAI
from prompts import PromptManager, PromptType
from langgraph.prebuilt import ToolNode
import json
from tools.context_to_csv import nearby_complexes_to_csv


def extract_json_from_text(text: str) -> str:
    """
    텍스트에서 JSON 부분만 추출합니다.
    마크다운 코드 블록을 제거하고 JSON만 반환합니다.
    """
    if not text:
        return ""

    text = text.strip()

    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    start_pos = text.find("{")
    end_pos = text.rfind("}")

    # find()와 rfind()는 문자열에서 찾는 문자가 없으면 -1을 반환합니다.
    # find(): 왼쪽부터 찾음
    # rfind(): 오른쪽부터 찾음

    if start_pos == -1 or end_pos == -1:
        return text

    if end_pos <= start_pos:
        return text

    return text[start_pos : end_pos + 1]


@tool(parse_docstring=False)
def think_tool(reflection: str) -> str:
    """
    [역할]
    당신은 사업지 주변 매매 아파트, 분양 아파트들 각각의 시세와 입지를 정리하는 전문가의 내부 반성·점검(Reflection) 담당자입니다.
    최종 보고서에 들어갈 본문(Markdown)을 쓰기 직전에, 데이터 품질·핵심 수치·리스크·보고서용 한 줄 메시지를 짧고 구조적으로 요약해 think_tool에 기록합니다. 이 반성문은 내부용이며, 최종 보고서에 직접 노출되지 않습니다.

    [언제 호출할 것인지]
    - Node 하나의 결과를 받고 tool을 사용하기 전에 호출(필수)
    - 데이터 수집/정제 → 핵심 수치 산출 → 시계열 해석을 마친 직후 1회 호출(필수)
    - 추가 데이터로 최신 데이터로 바뀌면 갱신 시마다 1회 재호출(선택)


    [강력 지시]
    - 해당 지역에 관련된 내용만 기록
    - 허상 가정,출처 수치 금지
    - Think step by step 방식으로 생각하세요.
    - 다음 단계(보고서 에이전트)가 바로 쓸 수 있는 한 줄 핵심 메시지 포함

    [나쁜 예]
    - “경제가 좋아진듯함. 분위기 좋음.”(수치·기간·단위·근거 없음)
    - “인근 해운대의 입지는 이렇다~”(대상 지역 외 서술)
    - “향후 집값 상승 확실.”(근거 없는 단정)

    [검증 체크리스트]
    - 정량 수치가 어긋난 것이 있는가?
    - GPT가 시계열 판단하기에 좋은 형식으로 되어있는가?
    - 잘못된 내용은 없는가?
    """
    return f"Reflection recorded: {reflection}"


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


from tools.kakao_api_distance_tool import get_location_profile
from tools.gemini_search_tool import gemini_search
from tools.perplexity_search_tool import perplexity_search
from tools.real_time_sale_search_api_tool import get_real_estate_price

llm = LLMProfile.analysis_llm()
tool_list = [think_tool, perplexity_search, get_real_estate_price, get_location_profile]
llm_with_tools = llm.bind_tools(tool_list)
tool_node = ToolNode(tool_list)


def gemini_search_tool(state: NearbyMarketState) -> NearbyMarketState:
    start_input = state[start_input_key]
    target_area = start_input[target_area_key]
    main_type = start_input[main_type_key]
    total_units = start_input[total_units_key]
    date = get_today_str()

    prompt = f"""
    <CONTEXT>
    사업지: {target_area}
    세대수: {total_units}세대
    타입: {main_type}
    일시: {date}
    </CONTEXT>

    <GOAL>
    - <CONTEXT>의 주소, 규모, 타입, 일시가 유사하고, 최단거리에 있는 매매아파트 3개, 분양아파트트 3개를 찾아서 매매아파트 3개는 각각의 평당매매가격, 분양단지 3개는 각각의 평당분양가격을 출력해 주세요
    </GOAL>
    <RULE>
    - 다른말은 생략하고 무조건 <OUTPUT>형식("json 형식")으로만 출력해주세요.
    - 매매아파트는 준공연도를 명시하세요.
    - 마크다운 코드블록은 제거하고 출력해 주세요.
    - 정확한 정보인지 확인하고 출력해 주세요.
    - 주소는 반드시 공식 행정구역명을 사용하세요 (예: "서울특별시", "경기도", "부산광역시" 등).
    - "서울시" 대신 "서울특별시", "경기" 대신 "경기도"처럼 정확한 행정구역명을 사용하세요.
    - 카카오 지도 API가 인식할 수 있는 정확한 주소 형식으로 작성하세요.
    </RULE>
    <OUTPUT>
    {{
      "매매아파트": [
        {{
          "주소와단지명": "",
          "세대수": "",
          "타입": "",
          "평당매매가격": "",
          "준공연도": "",
          "사업지와의의거리": "",
          "주변호재": ""
        }}
      ],
      "분양아파트": [
        {{
          "주소와단지명": "",
          "세대수": "",
          "타입": "",
          "평당분양가격": "",
          "청약경쟁률": "",
          "청약일시": "",
          "계약조건": "",
          "사업지와의거리": "",
          "주변호재": ""
        }}
      ]
    }}
    </OUTPUT>
    """
    result = gemini_search(prompt)
    return {gemini_search_key: result}


# gemini_search_tool 의 주소를 받아서 입지 정보와 거리를 조회하고 결과를 반환하는 도구
def kakao_api_distance_tool(state: NearbyMarketState) -> NearbyMarketState:
    start_input = state[start_input_key]
    target_area = start_input[target_area_key]
    gemini_result = state[gemini_search_key]
    json_text = extract_json_from_text(gemini_result)

    if not json_text:
        return {kakao_api_distance_context_key: []}

    try:
        gemini_data = json.loads(json_text)
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 파싱 실패: {e}")
        print(f"[DEBUG] 원본 Gemini 응답:\n{gemini_result}")
        print(f"[DEBUG] 추출된 JSON 텍스트:\n{json_text}")
        return {kakao_api_distance_context_key: []}

    all_result = []

    # 매매아파트 3개 처리
    for apt in gemini_data["매매아파트"]:
        address = apt["주소와단지명"]
        result = get_location_profile.invoke({"address": address})

        if result.get("좌표") is None:
            address_parts = address.split()
            if len(address_parts) > 1:
                retry_address = " ".join(address_parts[:3])
                retry_result = get_location_profile.invoke({"address": retry_address})
                if retry_result.get("좌표") is not None:
                    result = retry_result
                    result["주소"] = address

        result["타입"] = "매매아파트"
        result["원본정보"] = apt
        all_result.append(result)

    # 분양아파트 3개 처리
    for apt in gemini_data["분양아파트"]:
        address = apt["주소와단지명"]
        result = get_location_profile.invoke({"address": address})

        if result.get("좌표") is None:
            address_parts = address.split()
            if len(address_parts) > 1:
                retry_address = " ".join(address_parts[:3])
                retry_result = get_location_profile.invoke({"address": retry_address})
                if retry_result.get("좌표") is not None:
                    result = retry_result
                    result["주소"] = address

        result["타입"] = "분양아파트"
        result["원본정보"] = apt
        all_result.append(result)

    return {
        kakao_api_distance_context_key: all_result,
        kakao_api_distance_download_link_key: nearby_complexes_to_csv(
            all_result, target_area
        ),
    }


# gemini_search_tool 의 매매아파트 주소를 받아서 실거래가를 조회하고 결과를 반환하는 도구
def get_real_estate_price_tool(state: NearbyMarketState) -> NearbyMarketState:
    gemini_result = state[gemini_search_key]
    json_text = extract_json_from_text(gemini_result)

    if not json_text:
        return {real_estate_price_context_key: []}

    try:
        gemini_data = json.loads(json_text)
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 파싱 실패 (get_real_estate_price_tool): {e}")
        print(f"[DEBUG] 원본 Gemini 응답:\n{gemini_result}")
        print(f"[DEBUG] 추출된 JSON 텍스트:\n{json_text}")
        return {real_estate_price_context_key: []}

    sale_results = []
    # 매매아파트 3개 처리
    for apt in gemini_data["매매아파트"]:
        address = apt["주소와단지명"]
        result_str = get_real_estate_price.invoke({"address_or_apartment": address})
        result = json.loads(result_str)
        result["타입"] = "매매아파트"
        sale_results.append(result)

    return {real_estate_price_context_key: sale_results}


def perplexity_search_tool(state: NearbyMarketState) -> NearbyMarketState:
    gemini_result = state[gemini_search_key]
    json_text = extract_json_from_text(gemini_result)

    if not json_text:
        return {perplexity_search_key: ""}

    try:
        gemini_data = json.loads(json_text)
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 파싱 실패 (perplexity_search_tool): {e}")
        print(f"[DEBUG] 원본 Gemini 응답:\n{gemini_result}")
        print(f"[DEBUG] 추출된 JSON 텍스트:\n{json_text}")
        return {perplexity_search_key: ""}

    query_parts = []

    for apt in gemini_data["분양아파트"]:
        address = apt["주소와단지명"]
        apt_name = address.split()[-1] if address else ""
        current_price = apt.get("평당분양가격", "")
        contract_condition = apt.get("계약조건", "")
        contract_rate = apt.get("청약경쟁률", "")
        contract_date = apt.get("청약일시", "")

        query_text = f"{address} {apt_name} 분양가격 평당분양가 청약경쟁률 계약조건 {contract_date}"
        if current_price and current_price != "검증 불가":
            query_text += f" {current_price}"
        query_parts.append(query_text)

    combined_query = f"""
    다음 분양아파트 3개의 정확한 분양 정보를 검색하고 검증해주세요:

    1. {query_parts[0] if len(query_parts) > 0 else ""}
    2. {query_parts[1] if len(query_parts) > 1 else ""}
    3. {query_parts[2] if len(query_parts) > 2 else ""}

    각 아파트의 다음 정보를 정확히 찾아주세요:
    - 평당 분양가격 (만원 단위)
    - 계약조건 (계약금, 중도금 비율 등)
    - 청약경쟁률 (비율 형식)
    - 청약일시 (정확한 날짜)

    반드시 JSON 형식으로만 출력하세요:
    {{
        "분양아파트": [
            {{
                "주소와단지명": "",
                "평당분양가격": "",
                "계약조건": "",
                "청약경쟁률": "",
                "청약일시": "",
                "비고": ""
            }}
        ]
    }}
    """

    result = perplexity_search.invoke({"query": combined_query})

    result_text = result if isinstance(result, str) else str(result)

    if "검증 불가" in result_text or "확인 불가" in result_text:
        for apt in gemini_data["분양아파트"]:
            address = apt["주소와단지명"]
            apt_name = address.split()[-1] if address else ""
            retry_query = f"{address} {apt_name} 분양 공고 분양가 청약"
            retry_result = perplexity_search.invoke({"query": retry_query})
            if "검증 불가" not in retry_result and "확인 불가" not in retry_result:
                result_text = retry_result
                break

    return {perplexity_search_key: result_text}


def analysis_setting(state: NearbyMarketState) -> NearbyMarketState:
    start_input = state[start_input_key]
    target_area = start_input[target_area_key]
    total_units = start_input[total_units_key]
    main_type = start_input[main_type_key]
    gemini_search = state.get(gemini_search_key, "")
    kakao_api_distance_context = state.get(kakao_api_distance_context_key, "")
    real_estate_price_context = state.get(real_estate_price_context_key, "")
    perplexity_search = state.get(perplexity_search_key, "")

    system_prompt = PromptManager(PromptType.NEARBY_MARKET_SYSTEM).get_prompt(
        target_area=target_area,
        total_units=total_units,
        main_type=main_type,
        date=get_today_str(),
        gemini_search=gemini_search,
        kakao_api_distance_context=kakao_api_distance_context,
        real_estate_price_context=real_estate_price_context,
        perplexity_search=perplexity_search,
    )
    human_prompt = PromptManager(PromptType.NEARBY_MARKET_HUMAN).get_prompt(
        target_area=target_area,
        total_units=total_units,
        main_type=main_type,
        date=get_today_str(),
        gemini_search=gemini_search,
        kakao_api_distance_context=kakao_api_distance_context,
        real_estate_price_context=real_estate_price_context,
        perplexity_search=perplexity_search,
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt),
    ]
    return {**state, messages_key: messages}


def agent(state: NearbyMarketState) -> NearbyMarketState:
    messages = state.get(messages_key, [])
    response = llm_with_tools.invoke(messages)
    new_messages = messages + [response]
    new_state = {**state, messages_key: new_messages}
    # new_state[output_key] = response.content
    new_state[output_key] = {
        "result": response.content,
        gemini_search_key: state[gemini_search_key],
        kakao_api_distance_context_key: state[kakao_api_distance_context_key],
        real_estate_price_context_key: state[real_estate_price_context_key],
        perplexity_search_key: state[perplexity_search_key],
        kakao_api_distance_download_link_key: state[
            kakao_api_distance_download_link_key
        ],
    }
    return new_state


def router(state: NearbyMarketState):
    messages = state[messages_key]
    last_ai_message = messages[-1]
    if last_ai_message.tool_calls:
        return "tools"
    return "__end__"


web_context_key = "web_search"
analysis_setting_key = "analysis_setting"
tools_key = "tools"
agent_key = "agent"
gemini_search_key = "gemini_search"
kakao_api_distance_key = "kakao_api_distance"
real_estate_price_key = "real_estate_price"
perplexity_search_key = "perplexity_search"

graph_builder = StateGraph(NearbyMarketState)

graph_builder.add_node(gemini_search_key, gemini_search_tool)
graph_builder.add_node(kakao_api_distance_key, kakao_api_distance_tool)
graph_builder.add_node(real_estate_price_key, get_real_estate_price_tool)
graph_builder.add_node(perplexity_search_key, perplexity_search_tool)
graph_builder.add_node(analysis_setting_key, analysis_setting)

graph_builder.add_node(tools_key, tool_node)
graph_builder.add_node(agent_key, agent)

graph_builder.add_edge(START, gemini_search_key)
graph_builder.add_edge(gemini_search_key, kakao_api_distance_key)
graph_builder.add_edge(gemini_search_key, real_estate_price_key)
graph_builder.add_edge(gemini_search_key, perplexity_search_key)

graph_builder.add_edge(kakao_api_distance_key, analysis_setting_key)
graph_builder.add_edge(real_estate_price_key, analysis_setting_key)
graph_builder.add_edge(perplexity_search_key, analysis_setting_key)
graph_builder.add_edge(analysis_setting_key, agent_key)

graph_builder.add_conditional_edges(agent_key, router, [tools_key, END])
graph_builder.add_edge(tools_key, agent_key)

nearby_market_graph = graph_builder.compile()
