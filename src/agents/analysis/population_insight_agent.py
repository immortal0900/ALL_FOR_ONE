from langgraph.graph import StateGraph, START, END
from agents.state.analysis_state import PopulationInsightState
from agents.state.structured_schemas import AnalysisReport
from agents.state.start_state import StartInput
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from utils.util import get_today_str
from utils.llm import LLMProfile
from utils.sanitize import strip_think_tool
from prompts import PromptManager, PromptType
from langgraph.prebuilt import ToolNode
from tools.kostat_api import get_move_population
from tools.context_to_csv import age_population_to_drive, move_population_to_drive


@tool(parse_docstring=False)
def think_tool(reflection: str) -> str:
    """
    [역할]
    인구 분석(연령층 분포·순이동 추세) 단계의 내부 반성·점검(Reflection) 담당자입니다.
    데이터 품질·핵심 수치·시계열 패턴을 짧고 구조적으로 요약해 기록합니다.
    이 반성문은 내부용이며, 최종 보고서에 직접 노출되지 않습니다.

    [언제 호출할 것인지]
    - 연령층 분포/인구이동 데이터를 수집한 직후 1회 호출(필수)
    - 시계열 해석을 마친 직후 1회 호출(필수)

    [강력 지시]
    - 해당 지역에 관련된 내용만 기록
    - 허상 가정, 출처 없는 수치 금지
    - Think step by step 방식으로 생각하세요

    [검증 체크리스트]
    - 정량 수치가 어긋난 것이 있는가?
    - 시계열 판단하기에 좋은 형식으로 되어있는가?
    - 잘못된 내용은 없는가?
    """
    return f"Reflection recorded: {reflection}"


output_key = PopulationInsightState.KEY.population_insight_output
start_input_key = PopulationInsightState.KEY.start_input
age_population_context_key = PopulationInsightState.KEY.age_population_context
move_population_context_key = PopulationInsightState.KEY.move_population_context
age_population_download_link_key = PopulationInsightState.KEY.age_population_download_link
move_population_download_link_key = PopulationInsightState.KEY.move_population_download_link
messages_key = PopulationInsightState.KEY.messages
target_area_key = StartInput.KEY.target_area


llm = LLMProfile.analysis_llm()
tool_list = [think_tool]
llm_with_tools = llm.bind_tools(tool_list)
tool_node = ToolNode(tool_list)
format_llm = LLMProfile.dev_llm().with_structured_output(AnalysisReport)

from perplexity import Perplexity
search_client = Perplexity()

from tools.rag.retriever.age_population_retriever import age_population_retrieve
def age_population(state: PopulationInsightState) -> PopulationInsightState:
    start_input = state[start_input_key] 
    target_area = start_input[target_area_key]
    docs = age_population_retrieve(target_area)
    return {
        age_population_context_key: docs,
        age_population_download_link_key: age_population_to_drive(docs,target_area),
    }

def move_population(state: PopulationInsightState) -> PopulationInsightState: 
    start_input = state[start_input_key] 
    target_area = start_input[target_area_key]
    docs = get_move_population(target_area)
    return {
        move_population_context_key: docs,
        move_population_download_link_key: move_population_to_drive(docs,target_area),
    }


def analysis_setting(state: PopulationInsightState) -> PopulationInsightState:
    start_input = state[start_input_key]
    target_area = start_input[target_area_key]
    
    age_context = state[age_population_context_key]
    move_context = state[move_population_context_key]

    system_prompt = PromptManager(PromptType.POPULATION_INSIGHT_SYSTEM).get_prompt()
    humun_prompt = PromptManager(PromptType.POPULATION_INSIGHT_HUMAN).get_prompt(
        date=get_today_str(),
        target_area=target_area,
        age_context=age_context,
        move_context=move_context,
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=humun_prompt),
    ]
    return {messages_key: messages}


def agent(state: PopulationInsightState) -> PopulationInsightState:
    """ReAct 루프를 수행합니다. 결과 저장은 format_output에서 담당합니다."""
    messages = state.get(messages_key, [])
    response = llm_with_tools.invoke(messages)
    new_messages = messages + [response]
    return {**state, messages_key: new_messages}


def format_output(state: PopulationInsightState) -> PopulationInsightState:
    """ReAct 루프 종료 후 think_tool 반성문을 제거하고 깨끗한 보고서만 추출합니다."""
    messages = state.get(messages_key, [])
    raw_content = messages[-1].content

    cleaned = strip_think_tool(raw_content)
    report = format_llm.invoke(cleaned)

    new_state = {**state}
    new_state[output_key] = {
        "result": report.result,
        age_population_context_key: state[age_population_context_key],
        move_population_context_key: state[move_population_context_key],
        age_population_download_link_key: state[age_population_download_link_key],
        move_population_download_link_key: state[move_population_download_link_key],
    }
    return new_state


def router(state: PopulationInsightState):
    messages = state[messages_key]
    last_ai_message = messages[-1]
    if last_ai_message.tool_calls:
        return "tools"
    return "format_output"


age_population_retrieve_key = "age_population_retrieve"
move_population_retrieve_key = "move_population_retrieve"
analysis_setting_key = "analysis_setting"
tools_key = "tools"
agent_key = "agent"
format_output_key = "format_output"

graph_builder = StateGraph(PopulationInsightState)
graph_builder.add_node(age_population_retrieve_key, age_population)
graph_builder.add_node(move_population_retrieve_key, move_population)
graph_builder.add_node(analysis_setting_key, analysis_setting)
graph_builder.add_node(tools_key, tool_node)
graph_builder.add_node(agent_key, agent)
graph_builder.add_node(format_output_key, format_output)

graph_builder.add_edge(START, age_population_retrieve_key)
graph_builder.add_edge(START, move_population_retrieve_key)
graph_builder.add_edge(age_population_retrieve_key, analysis_setting_key)
graph_builder.add_edge(move_population_retrieve_key, analysis_setting_key)
graph_builder.add_edge(analysis_setting_key, agent_key)
graph_builder.add_conditional_edges(agent_key, router, [tools_key, format_output_key])
graph_builder.add_edge(tools_key, agent_key)
graph_builder.add_edge(format_output_key, END)

population_insight_graph = graph_builder.compile()
