from langgraph.graph import StateGraph, START, END
from agents.state.analysis_state import LocationInsightState
from agents.state.start_state import StartInput
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from utils.util import get_today_str
from utils.llm import LLMProfile
from prompts import PromptManager, PromptType
from langgraph.prebuilt import ToolNode
from tools.context_to_csv import location_kakao_to_drive


@tool(parse_docstring=False)
def think_tool(reflection: str) -> str:
    """
    [역할]
    당신은 입지/호재 정리 전문가의 내부 반성·점검(Reflection) 담당자입니다.
    최종 보고서에 들어갈 본문(Markdown)을 쓰기 직전에, 데이터 품질·핵심 수치·리스크·보고서용 한 줄 메시지를 짧고 구조적으로 요약해 think_tool에 기록합니다. 이 반성문은 내부용이며, 최종 보고서에 직접 노출되지 않습니다.

    [언제 호출할 것인지]
    - 데이터 수집/정제 → 핵심 수치 산출 → 시계열 해석을 마친 직후 1회 호출(필수)
    - 추가 데이터로 최신 데이터로 바뀌면 갱신 시마다 1회 재호출(선택)

    [강력 지시]
    - 해당 지역에 관련된 내용만 기록
    - 허상 가정,출처 수치 금지
    - 다음 단계(보고서 에이전트)가 바로 쓸 수 있는 한 줄 핵심 메시지 포함

    [나쁜 예]
    - “경제가 좋아진듯함. 분위기 좋음.”(수치·기간·단위·근거 없음)
    - “인근 해운대의 입지는 이렇다~”(대상 지역 외 서술)
    - “향후 집값 상승 확실.”(근거 없는 단정)

    [검증 체크리스트]
    - 정량 수치가 어긋난 것 이 있는가?
    - GPT가 시계열 판단하기에 좋은 형식으로 되어있는가?
    - 잘못된 내용은 없는가?
    """
    return f"Reflection recorded: {reflection}"


output_key = LocationInsightState.KEY.location_insight_output
start_input_key = LocationInsightState.KEY.start_input
messages_key = LocationInsightState.KEY.messages
target_area_key = StartInput.KEY.target_area
main_type_key = StartInput.KEY.main_type
total_units_key = StartInput.KEY.total_units
web_context_key = LocationInsightState.KEY.web_context
kakao_api_distance_context_key = LocationInsightState.KEY.kakao_api_distance_context
kakao_api_distance_download_link_key = (
    LocationInsightState.KEY.kakao_api_distance_download_link
)
gemini_search_key = LocationInsightState.KEY.gemini_search
perplexity_search_key = LocationInsightState.KEY.perplexity_search

from tools.gemini_search_tool import gemini_search
from tools.perplexity_search_tool import perplexity_search
from tools.kakao_api_distance_tool import get_location_profile

llm = LLMProfile.analysis_llm()
tool_list = [think_tool, perplexity_search]
llm_with_tools = llm.bind_tools(tool_list)
tool_node = ToolNode(tool_list)


def gemini_search_tool(state: LocationInsightState) -> LocationInsightState:
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
    - <CONTEXT>에 나와 있는 정보를 참고해서 해당 사업지에 맞는 핵심 데이터 선별을 위해 부동산과 관련된 해당지역에 구매성향과 패턴을 추려서 출력해주세요.
    - <CONTEXT>를 참고해서 {date} 이후의 주변호재를 <OUTPUT>을 참조해서 "json 형식" 으로만만 출력해주세요
    </GOAL>
    <OUTPUT>
    {{
      "해당지역 특징": []
      "주변호재": [
        {{
          "name": "",
          "location": "",
          "description": "",
          "status": ""
        }}
      ]
    }}
    </OUTPUT>
    """
    result = gemini_search(prompt)
    return {gemini_search_key: result}


def kakao_api_distance_tool(state: LocationInsightState) -> LocationInsightState:
    start_input = state[start_input_key]
    target_area = start_input[target_area_key]
    # result = get_location_profile(target_area)
    result = get_location_profile.invoke({"address": target_area})

    return {
        kakao_api_distance_context_key: result,
        kakao_api_distance_download_link_key: location_kakao_to_drive(
            result, target_area
        ),
    }


def analysis_setting(state: LocationInsightState) -> LocationInsightState:
    start_input = state[start_input_key]
    target_area = start_input[target_area_key]
    total_units = start_input[total_units_key]
    main_type = start_input[main_type_key]
    gemini_search = state.get(gemini_search_key, "")
    kakao_api_distance_context = state.get(kakao_api_distance_context_key, {})
    perplexity_search = state.get(perplexity_search_key, "")

    system_prompt = PromptManager(PromptType.LOCATION_INSIGHT_SYSTEM).get_prompt()
    human_prompt = PromptManager(PromptType.LOCATION_INSIGHT_HUMAN).get_prompt(
        target_area=target_area,
        total_units=total_units,
        main_type=main_type,
        date=get_today_str(),
        gemini_search=gemini_search,
        kakao_api_distance_context=kakao_api_distance_context,
        perplexity_search=perplexity_search,
    )
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt),
    ]
    return {**state, messages_key: messages}


def agent(state: LocationInsightState) -> LocationInsightState:
    messages = state.get(messages_key, [])
    response = llm_with_tools.invoke(messages)
    new_messages = messages + [response]
    new_state = {**state, messages_key: new_messages}
    # new_state[output_key] = response.content
    new_state[output_key] = {
        "result": response.content,
        gemini_search_key: state[gemini_search_key],
        kakao_api_distance_context_key: state[kakao_api_distance_context_key],
        kakao_api_distance_download_link_key: state[
            kakao_api_distance_download_link_key
        ],
    }
    return new_state


def router(state: LocationInsightState):
    messages = state[messages_key]
    last_ai_message = messages[-1]
    if last_ai_message.tool_calls:
        return "tools"
    return "__end__"


web_search_key = "web_search"
analysis_setting_key = "analysis_setting"
tools_key = "tools"
agent_key = "agent"
gemini_search_node_key = "gemini_search"
kakao_api_distance_key = "kakao_api_distance"
perplexity_search_key = "perplexity_search"

graph_builder = StateGraph(LocationInsightState)

graph_builder.add_node(gemini_search_node_key, gemini_search_tool)
graph_builder.add_node(kakao_api_distance_key, kakao_api_distance_tool)
graph_builder.add_node(analysis_setting_key, analysis_setting)
# graph_builder.add_node(perplexity_search_key, perplexity_search_tool)

graph_builder.add_node(tools_key, tool_node)
graph_builder.add_node(agent_key, agent)

graph_builder.add_edge(START, gemini_search_node_key)
graph_builder.add_edge(gemini_search_node_key, kakao_api_distance_key)
graph_builder.add_edge(kakao_api_distance_key, analysis_setting_key)
graph_builder.add_edge(analysis_setting_key, agent_key)

graph_builder.add_conditional_edges(agent_key, router, [tools_key, END])
graph_builder.add_edge(tools_key, agent_key)

location_insight_graph = graph_builder.compile()
