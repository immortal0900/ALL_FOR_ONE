# agents/analysis/location_insight_agent.py
"""
입지 분석 에이전트 (LocationInsight).

파이프라인:
  gemini_search → kakao_api_distance → analysis_setting → agent (ReAct loop) → END

Structured Output 적용:
  - gemini_search_tool: Gemini API에 LocationInsightGeminiSchema 강제
  → 주변호재·지역특징이 스키마를 준수한 JSON 문자열로 반환됩니다.
"""

import json

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from agents.state.analysis_state import LocationInsightState
from agents.state.start_state import StartInput
from agents.state.structured_schemas import LocationInsightGeminiSchema
from prompts import PromptManager, PromptType
from tools.context_to_csv import location_kakao_to_drive
from tools.gemini_search_tool import gemini_search
from tools.kakao_api_distance_tool import get_location_profile
from tools.perplexity_search_tool import perplexity_search
from utils.llm import LLMProfile
from utils.util import get_today_str


# ---------------------------------------------------------------------------
# LLM 및 Tool 설정
# ---------------------------------------------------------------------------

llm = LLMProfile.analysis_llm()


tool_list = [perplexity_search]
llm_with_tools = llm.bind_tools(tool_list)
tool_node = ToolNode(tool_list)


# ---------------------------------------------------------------------------
# State 키 상수 (Single Source of Truth)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 노드 함수
# ---------------------------------------------------------------------------


def gemini_search_tool(state: LocationInsightState) -> LocationInsightState:
    """
    Gemini로 사업지 주변 입지 특징과 호재를 검색합니다.

    [Structured Output 적용]
    LocationInsightGeminiSchema를 response_schema로 전달하므로
    Gemini API가 해당지역특징·주변호재를 스키마를 준수한 JSON 문자열로 반환합니다.
    """
    start_input = state[start_input_key]
    target_area = start_input[target_area_key]
    main_type = start_input[main_type_key]
    total_units = start_input[total_units_key]
    date = get_today_str()

    # 프롬프트: 입력(동적 변수) 부분만 정의, 출력 형태는 스키마가 담당
    prompt = f"""
    <CONTEXT>
    사업지: {target_area}
    세대수: {total_units}세대
    타입: {main_type}
    일시: {date}
    </CONTEXT>

    <GOAL>
    - <CONTEXT>에 나와 있는 정보를 참고해서 해당 사업지에 맞는 핵심 데이터 선별을 위해
      부동산과 관련된 해당 지역의 구매 성향과 패턴을 추려주세요.
    - <CONTEXT>를 참고해서 {date} 이후의 주변 호재(GTX, 재개발, 신규 상업시설, 교통 인프라 등)를
      찾아주세요.
    </GOAL>

    <RULE>
    - 해당 지역에 실제로 확인된 정보만 포함하세요.
    - 수치가 있는 경우 구체적인 수치를 기재하세요 (예: '2027년 GTX-A 성남역 개통 예정').
    - 추측이나 단정적 표현은 금지합니다.
    </RULE>
    """

    # Structured Output: LocationInsightGeminiSchema 스키마 강제
    # .model_json_schema()로 dict를 전달해야 Gemini API가 JSON 직렬화 가능
    raw_dict = gemini_search(
        prompt,
        response_schema=LocationInsightGeminiSchema.model_json_schema(),
    )

    return {gemini_search_key: raw_dict}


def kakao_api_distance_tool(state: LocationInsightState) -> LocationInsightState:
    """사업지 주소를 카카오 API로 조회하여 입지 정보를 수집합니다."""
    start_input = state[start_input_key]
    target_area = start_input[target_area_key]

    result = get_location_profile.invoke({"address": target_area})

    return {
        kakao_api_distance_context_key: result,
        kakao_api_distance_download_link_key: location_kakao_to_drive(
            result, target_area
        ),
    }


def analysis_setting(state: LocationInsightState) -> LocationInsightState:
    """
    수집된 컨텍스트를 종합하여 LLM 메시지를 구성합니다.

    [gemini_search 직렬화]
    gemini_search_key는 JSON 문자열(str)이므로 프롬프트에 그대로 주입됩니다.
    별도의 json.dumps() 직렬화가 필요하지 않습니다.
    """
    start_input = state[start_input_key]
    target_area = start_input[target_area_key]
    total_units = start_input[total_units_key]
    main_type = start_input[main_type_key]
    gemini_search_data = state.get(gemini_search_key, "")
    kakao_api_distance_context = state.get(kakao_api_distance_context_key, {})
    perplexity_search_data = state.get(perplexity_search_key, "")

    system_prompt = PromptManager(PromptType.LOCATION_INSIGHT_SYSTEM).get_prompt()
    human_prompt = PromptManager(PromptType.LOCATION_INSIGHT_HUMAN).get_prompt(
        target_area=target_area,
        total_units=total_units,
        main_type=main_type,
        date=get_today_str(),
        gemini_search=gemini_search_data,
        kakao_api_distance_context=kakao_api_distance_context,
        perplexity_search=perplexity_search_data,
    )
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt),
    ]
    return {**state, messages_key: messages}


def agent(state: LocationInsightState) -> LocationInsightState:
    """최종 입지 분석 보고서를 생성하고 결과를 State에 저장합니다."""
    messages = state.get(messages_key, [])
    response = llm_with_tools.invoke(messages)
    new_messages = messages + [response]
    new_state = {**state, messages_key: new_messages}
    new_state[output_key] = {
        "result": response.content,
        gemini_search_key: state[gemini_search_key],
        kakao_api_distance_context_key: state[kakao_api_distance_context_key],
        kakao_api_distance_download_link_key: state[
            kakao_api_distance_download_link_key
        ],
    }
    return new_state


def router(state: LocationInsightState) -> str:
    """Tool 호출 여부에 따라 다음 노드를 결정합니다."""
    messages = state[messages_key]
    last_ai_message = messages[-1]
    if last_ai_message.tool_calls:
        return "tools"
    return "__end__"


# ---------------------------------------------------------------------------
# 그래프 빌드
# ---------------------------------------------------------------------------

_analysis_setting_key = "analysis_setting"
_tools_key = "tools"
_agent_key = "agent"
_gemini_search_node_key = "gemini_search"
_kakao_api_distance_key = "kakao_api_distance"

graph_builder = StateGraph(LocationInsightState)

graph_builder.add_node(_gemini_search_node_key, gemini_search_tool)
graph_builder.add_node(_kakao_api_distance_key, kakao_api_distance_tool)
graph_builder.add_node(_analysis_setting_key, analysis_setting)
graph_builder.add_node(_tools_key, tool_node)
graph_builder.add_node(_agent_key, agent)

graph_builder.add_edge(START, _gemini_search_node_key)
graph_builder.add_edge(_gemini_search_node_key, _kakao_api_distance_key)
graph_builder.add_edge(_kakao_api_distance_key, _analysis_setting_key)
graph_builder.add_edge(_analysis_setting_key, _agent_key)

graph_builder.add_conditional_edges(_agent_key, router, [_tools_key, END])
graph_builder.add_edge(_tools_key, _agent_key)

location_insight_graph = graph_builder.compile()
