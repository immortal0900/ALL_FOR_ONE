from langgraph.graph import StateGraph, START, END
from agents.state.analysis_state import UnsoldInsightState
from langchain_core.tools import tool
from agents.state.start_state import StartInput
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from utils.util import get_today_str
from utils.llm import LLMProfile
from prompts import PromptManager, PromptType
from langgraph.prebuilt import ToolNode
from tools.context_to_csv import unsold_to_drive

@tool(parse_docstring=True)
def think_tool(reflection: str) -> str:
    """미분양(Unsold) 심화 분석 단계의 **전략적 성찰(Reflection)**을 기록/보정하는 도구입니다.

    총 미분양/준공후 미분양/규모·지역 구성을 수집한 직후,
    **시점·단위·정의(준공 전·후)**의 일관성과 **해소 속도/리스크** 해석의 타당성을 점검하고
    다음 액션(추가 수집 vs 보고서 확정)을 결정합니다.

    사용 시점:
        - 국토부 통계누리에서 시군구/규모/준공 후 구분 시계열 확보 직후
        - 급증 구간(window)·증감률 계산 후
        - '준공 후 비중' 상승/하락 판정 전
        - diagnosis(위험도)·narrative_md 확정 직전

    성찰(반드시 포함):
        1) 발견(Findings): 최근 3~5년 시계열 핵심 수치(총량/준공후), 지역·규모 집중, 급증 구간·증감률, 해소율/해소기간.
        2) 공백(Gaps): 특정 시군구 레벨 결측, 준공 후 세부치 결여, 규모대 분포 미확보 등.
        3) 품질(Quality): 단위(호/%)·기간(YYYY-MM)·정의(준공 전·후) 표기, 국가승인통계 원출처 명시 여부.
        4) 인과(Logic): '급증/집중/준공후 비중 상승 → 해소 지연 → 분양성/현금흐름 압박' 연결이 서술과 일치하는가?
        5) 결정(Next step): 추가 확보할 1차 자료와 **구체 쿼리** 제시
           - 예) "stat.molit 시군구별 미분양 2023-2025 다운로드",
                 "규모별(≤60/60~85/>85) 비중 시계열 재확인",
                 "준공 후 미분양 월별 비중 계산"

    도메인 체크리스트:
        - 정의/메타: 국가승인통계, 월별·시군구 단위, 준공 전·후 구분이 반영되었는가?  # 통계누리 메타 참고
        - 급증 판정: window와 delta_pct가 수치로 제시되었는가?
        - 집중도: 권역/시군구/규모대 집중이 **진단(risk_level)**에 반영되었는가?
        - 해소 속도: clear_rate/median_clear_months 추정 근거가 기록되었는가?

    Args:
        reflection: 현재 수집·해석 상태, 공백·품질 점검, 다음 단계에 대한 **구체적 성찰 서술**.
            예) "2024-07~2025-03 급증(+38%). 준공후 비중 27%→33% 상승.
                수도권보단 지방 기여↑. 규모는 60~85㎡ 비중 확대.
                시군구 결측 2곳 → stat.molit 상세 조회 필요.
                median_clear_months=5~7개월 잠정."

    Returns:
        성찰 기록 확인 메시지(내부 로그용). 예: "Reflection recorded: <요약>"

    주의:
        - 수치에는 **단위/기간**(호/%/YYYY-MM)을 반드시 포함하십시오.
        - '준공 후' 비중과 급증 구간(window)은 리스크 판단의 핵심입니다.
        - 1차 공식 출처(국토부 통계누리/통계청/KRIHS)를 우선하십시오.
    """
    return f"Reflection recorded: {reflection}"


output_key = UnsoldInsightState.KEY.unsold_insight_output
start_input_key = UnsoldInsightState.KEY.start_input
messages_key = UnsoldInsightState.KEY.messages
unsold_unit_key = UnsoldInsightState.KEY.unsold_unit
unsold_unit_download_link_key = UnsoldInsightState.KEY.unsold_unit_download_link
target_area_key = StartInput.KEY.target_area


llm = LLMProfile.analysis_llm()
tool_list = [think_tool]
llm_with_tools = llm.bind_tools(tool_list)
tool_node = ToolNode(tool_list)


from tools.unsold_units import unsold_units


def get_unsold_unit(state: UnsoldInsightState) -> UnsoldInsightState:
    start_input = state[start_input_key]
    target_area = start_input[target_area_key]
    docs = unsold_units(target_area)
    
    return {unsold_unit_key: docs,
            unsold_unit_download_link_key:unsold_to_drive(docs,target_area)}


def analysis_setting(state: UnsoldInsightState) -> UnsoldInsightState:
    start_input = state[start_input_key]
    target_area = start_input[target_area_key]
    unsold_unit = state[unsold_unit_key]

    system_prompt = PromptManager(PromptType.UNSOLD_INSIGHT_SYSTEM).get_prompt()
    humun_prompt = PromptManager(PromptType.UNSOLD_INSIGHT_HUMAN).get_prompt(
        date=get_today_str(), target_area=target_area, unsold_unit=unsold_unit
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=humun_prompt),
    ]
    return {messages_key: messages}


def agent(state: UnsoldInsightState) -> UnsoldInsightState:
    messages = state.get(messages_key, [])
    response = llm_with_tools.invoke(messages)
    new_messages = messages + [response]
    new_state = {**state, messages_key: new_messages}
    new_state[output_key] = {
        "result": response.content,
        unsold_unit_key: state[unsold_unit_key],
        unsold_unit_download_link_key:state[unsold_unit_download_link_key]
    }
    return new_state


def router(state: UnsoldInsightState):
    messages = state[messages_key]
    last_ai_message = messages[-1]
    if last_ai_message.tool_calls:
        return "tools"
    return "__end__"


unsold_unit_key = "unsold_unit"
analysis_setting_key = "analysis_setting"
tools_key = "tools"
agent_key = "agent"
graph_builder = StateGraph(UnsoldInsightState)
graph_builder.add_node(unsold_unit_key, get_unsold_unit)
graph_builder.add_node(analysis_setting_key, analysis_setting)
graph_builder.add_node(tools_key, tool_node)
graph_builder.add_node(agent_key, agent)

graph_builder.add_edge(START, unsold_unit_key)
graph_builder.add_edge(unsold_unit_key, analysis_setting_key)
graph_builder.add_edge(analysis_setting_key, agent_key)
graph_builder.add_conditional_edges(agent_key, router, [tools_key, END])
graph_builder.add_edge(tools_key, agent_key)

unsold_insight_graph = graph_builder.compile()
