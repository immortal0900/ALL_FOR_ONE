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
from langchain_core.tools import tool
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


@tool(parse_docstring=False)
def think_tool(reflection: str) -> str:
    """
    [역할]
    당신은 입지/호재 정리 전문가의 내부 반성·점검(Reflection) 담당자입니다.
    최종 보고서에 들어갈 본문(Markdown)을 쓰기 직전에, 데이터 품질·핵심 수치·리스크·보고서용
    한 줄 메시지를 짧고 구조적으로 요약해 think_tool에 기록합니다.
    이 반성문은 내부용이며, 최종 보고서에 직접 노출되지 않습니다.

    [언제 호출할 것인지]
    - 데이터 수집/정제 → 핵심 수치 산출 → 시계열 해석을 마친 직후 1회 호출(필수)
    - 추가 데이터로 최신 데이터로 바뀌면 갱신 시마다 1회 재호출(선택)

    [강력 지시]
    - 해당 지역에 관련된 내용만 기록
    - 허상 가정, 출처 수치 금지
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


tool_list = [think_tool, perplexity_search]
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
