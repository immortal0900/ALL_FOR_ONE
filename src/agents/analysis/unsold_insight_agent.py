from langgraph.graph import StateGraph, START, END
from agents.state.analysis_state import UnsoldInsightState
from agents.state.start_state import StartInput
from langchain_core.messages import SystemMessage, HumanMessage
from utils.util import get_today_str
from utils.llm import LLMProfile
from prompts import PromptManager, PromptType
from tools.context_to_csv import unsold_to_drive


output_key = UnsoldInsightState.KEY.unsold_insight_output
start_input_key = UnsoldInsightState.KEY.start_input
messages_key = UnsoldInsightState.KEY.messages
unsold_unit_key = UnsoldInsightState.KEY.unsold_unit
unsold_unit_download_link_key = UnsoldInsightState.KEY.unsold_unit_download_link
target_area_key = StartInput.KEY.target_area


llm = LLMProfile.analysis_llm()


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
    response = llm.invoke(messages)
    new_messages = messages + [response]
    new_state = {**state, messages_key: new_messages}
    new_state[output_key] = {
        "result": response.content,
        unsold_unit_key: state[unsold_unit_key],
        unsold_unit_download_link_key:state[unsold_unit_download_link_key]
    }
    return new_state


unsold_unit_key = "unsold_unit"
analysis_setting_key = "analysis_setting"
agent_key = "agent"
graph_builder = StateGraph(UnsoldInsightState)
graph_builder.add_node(unsold_unit_key, get_unsold_unit)
graph_builder.add_node(analysis_setting_key, analysis_setting)
graph_builder.add_node(agent_key, agent)

graph_builder.add_edge(START, unsold_unit_key)
graph_builder.add_edge(unsold_unit_key, analysis_setting_key)
graph_builder.add_edge(analysis_setting_key, agent_key)
graph_builder.add_edge(agent_key, END)

unsold_insight_graph = graph_builder.compile()
