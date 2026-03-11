from agents.state.renderer_state import RendererState
from agents.state.start_state import StartInput
from tools.send_gmail import send_gmail
from utils.llm import LLMProfile
from agents.renderer.renderer_logic import render_sliceplan_local
from prompts import PromptManager, PromptType
from utils.util import get_today_str
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, START, END  


@tool(parse_docstring=False)
def think_tool(reflection: str) -> str:
    """
    [역할]
    당신은 부동산 관련 정책 정리 전문가의 내부 반성·점검(Reflection) 담당자입니다.
    SlidePlan을 쓰기 직전에, 최종 보고서에  구조적으로 요약해 think_tool에 기록합니다.
    이 반성문은 내부용이며, SlidePlan에 직접 노출되지 않습니다.

    [언제 호출할 것인지]
    - 프롬프트 to SlidePlan 변환 후 1회 호출(필수)

    [검증 체크리스트]
    - SlidePlan이 만들어낸 말이 있는가?
    - SlidePlan에 깨진 단어나 텍스트가 있는가?
    - SlidePlan에 최종 보고서에 없는 내용이 있는가?
    """
    return f"Reflection recorded: {reflection}"

start_input_key = RendererState.KEY.start_input
analysis_outputs_key = RendererState.KEY.analysis_outputs
messages_key = RendererState.KEY.messages
final_report_key = RendererState.KEY.final_report

target_area_key = StartInput.KEY.target_area
main_type_key = StartInput.KEY.main_type
total_units_key = StartInput.KEY.total_units
email_key = StartInput.KEY.email

ppt_title_key = RendererState.KEY.ppt_title
ppt_summary_title_key = RendererState.KEY.ppt_summary_title
ppt_path_key = RendererState.KEY.ppt_path
slide_plan_key = RendererState.KEY.slide_plan

llm = LLMProfile.renderer_llm()
tool_list = [think_tool]
llm_with_tools = llm.bind_tools(tool_list)
tool_node = ToolNode(tool_list)


def init(state: RendererState) -> RendererState:
    start_input = state[start_input_key]
    target_area = start_input[target_area_key]
    main_type = start_input[main_type_key]
    total_units = start_input[total_units_key]
    final_report = state[final_report_key]

    ppt_title = (
        f"{target_area}\n {main_type}, {total_units}세대 사업 보고서"
    )
    summary_title_llm = LLMProfile.dev_llm()
    llm_result = summary_title_llm.invoke(
        PromptManager(PromptType.RENDERER_SUMMARY_TITLE).get_prompt(
            final_report=final_report
        )
    )
    summary_title = llm_result.content

    prompt_system = PromptManager(PromptType.RENDERER_SYSTEM).get_prompt()
    prompt_human = PromptManager(PromptType.RENDERER_HUMAN).get_prompt(
        date=get_today_str(),
        title=ppt_title,
        summary_title=summary_title,
        final_report=final_report,
    )
    
    messages = [
        SystemMessage(content=prompt_system),
        HumanMessage(content=prompt_human),
    ]
    
    return {
        ppt_title_key: ppt_title,
        ppt_summary_title_key: summary_title,        
        messages_key:messages
    }
    
def agent(state: RendererState) -> RendererState:
    messages = state[messages_key]
    response = llm_with_tools.invoke(messages)
    new_messages = messages + [response]
    new_state = {**state, messages_key: new_messages}    
    return new_state
    
from tools.send_gmail import gmail_authenticate
from tools.send_gmail import send_gmail

def rendering(state: RendererState) -> RendererState:
    
    title = state[ppt_title_key]
    final_report = state[final_report_key]
    email = state[start_input_key][email_key]
    messages = state[messages_key]
    last_message = messages[-1]
    slide_plan = JsonOutputParser().parse(last_message.content)

    path = render_sliceplan_local(slide_plan)
    gmail_authenticate()
    send_gmail(
        to=email,
        title=title,
        md_content_final=final_report,
        md_content_source="",
    )
    
    return {
        **state,
        ppt_path_key: path,
        slide_plan_key : slide_plan
    }
    
def router(state: RendererState):
    messages = state[messages_key]
    last_ai_message = messages[-1]
    if last_ai_message.tool_calls:
        return "tools"
    return "rendering"



init_key = "init"
tools_key = "tools"
agent_key = "agent"
rendering_key = "rendering"
graph_builder = StateGraph(RendererState)
graph_builder.add_node(init_key, init)
graph_builder.add_node(agent_key, agent)
graph_builder.add_node(tools_key, tool_node)
graph_builder.add_node(rendering_key, rendering)

graph_builder.add_edge(START, init_key)
graph_builder.add_edge(init_key, agent_key)
graph_builder.add_conditional_edges(agent_key, router, [tools_key, rendering_key])

graph_builder.add_edge(tools_key, agent_key)
graph_builder.add_edge(rendering_key, END)

renderer_graph = graph_builder.compile()


