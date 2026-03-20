from langgraph.graph import StateGraph, START, END
from agents.state.analysis_state import PopulationInsightState
from agents.state.start_state import StartInput
from langchain_core.messages import SystemMessage, HumanMessage
from utils.util import get_today_str
from utils.llm import LLMProfile
from prompts import PromptManager, PromptType
from tools.kostat_api import get_move_population
from tools.context_to_csv import age_population_to_drive,move_population_to_drive


output_key = PopulationInsightState.KEY.population_insight_output
start_input_key = PopulationInsightState.KEY.start_input
age_population_context_key = PopulationInsightState.KEY.age_population_context
move_population_context_key = PopulationInsightState.KEY.move_population_context
age_population_download_link_key = PopulationInsightState.KEY.age_population_download_link
move_population_download_link_key = PopulationInsightState.KEY.move_population_download_link
messages_key = PopulationInsightState.KEY.messages
target_area_key = StartInput.KEY.target_area


llm = LLMProfile.analysis_llm()

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
    messages = state.get(messages_key, [])
    response = llm.invoke(messages)
    new_messages = messages + [response]
    new_state = {**state, messages_key: new_messages}
    new_state[output_key] = {
        "result": response.content,
        age_population_context_key: state[age_population_context_key],
        move_population_context_key: state[move_population_context_key],
        age_population_download_link_key: state[age_population_download_link_key],
        move_population_download_link_key: state[move_population_download_link_key],
    }
    return new_state


age_population_retrieve_key = "age_population_retrieve"
move_population_retrieve_key = "move_population_retrieve"

analysis_setting_key = "analysis_setting"
agent_key = "agent"
graph_builder = StateGraph(PopulationInsightState)
graph_builder.add_node(age_population_retrieve_key, age_population)
graph_builder.add_node(move_population_retrieve_key, move_population)
graph_builder.add_node(analysis_setting_key, analysis_setting)
graph_builder.add_node(agent_key, agent)

graph_builder.add_edge(START, age_population_retrieve_key)
graph_builder.add_edge(START, move_population_retrieve_key)
graph_builder.add_edge(age_population_retrieve_key, analysis_setting_key)
graph_builder.add_edge(move_population_retrieve_key, analysis_setting_key)
graph_builder.add_edge(analysis_setting_key, agent_key)

graph_builder.add_edge(agent_key, END)

population_insight_graph = graph_builder.compile()
