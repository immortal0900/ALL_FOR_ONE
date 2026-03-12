from langgraph.graph import StateGraph, START, END
from agents.state.analysis_state import HousingFaqState
from agents.state.start_state import StartInput


start_input_key = HousingFaqState.KEY.start_input
output_key = HousingFaqState.KEY.housing_faq_output
target_area_key = StartInput.KEY.target_area
main_type_key = StartInput.KEY.main_type
total_units_key = StartInput.KEY.total_units
housing_faq_context_key = HousingFaqState.KEY.housing_faq_context
housing_rule_context_key = HousingFaqState.KEY.housing_rule_context
housing_faq_download_link_key = HousingFaqState.KEY.housing_faq_download_link
housing_rule_download_link_key = HousingFaqState.KEY.housing_rule_download_link
messages_key = HousingFaqState.KEY.messages

from tools.rag.retriever.housing_faq_retriever import (
    housing_rule_retrieve,
    housing_faq_retrieve,
)

from tools.context_to_csv import (
    housing_faq_context_to_drive,
    housing_rule_context_to_drive,
)


def get_rule_data(state: HousingFaqState) -> HousingFaqState:
    start_input = state[start_input_key]
    target_area = start_input[target_area_key]
    main_type = start_input[main_type_key]
    total_units = start_input[total_units_key]

    retriever = housing_rule_retrieve()
    query = f"사업지:{target_area}\n타입:{main_type}\n세대수:{total_units}\n 위 내용과 조금이라도 관련된 주택 공급 내용"
    docs = []
    for doc in retriever.invoke(query):
        docs.append(doc.page_content)

    return {
        housing_rule_context_key: docs,
        housing_rule_download_link_key: housing_rule_context_to_drive(docs),
    }


def get_faq_data(state: HousingFaqState) -> HousingFaqState:
    start_input = state[start_input_key]
    target_area = start_input[target_area_key]
    main_type = start_input[main_type_key]
    total_units = start_input[total_units_key]

    retriever = housing_faq_retrieve()
    query = f"사업지:{target_area}\n타입:{main_type}\n세대수:{total_units}\n 위 내용과 조금이라도 관련된 청약 질의 내용 모두"
    docs = []
    for doc in retriever.invoke(query):
        docs.append(doc.page_content)
    return {
        housing_faq_context_key: docs,
        housing_faq_download_link_key: housing_faq_context_to_drive(docs),
    }


from prompts import PromptManager, PromptType
from langchain_core.messages import HumanMessage, SystemMessage


def analysis_setting(state: HousingFaqState) -> HousingFaqState:
    start_input = state[start_input_key]
    target_area = start_input[target_area_key]
    main_type = start_input[main_type_key]
    faq_context = state[housing_faq_context_key]
    rule_context = state[housing_rule_context_key]
    system_prompt = PromptManager(PromptType.HOUSING_FAQ_SYSTEM).get_prompt()
    total_units = start_input[total_units_key]
    human_prompt = PromptManager(PromptType.HOUSING_FAQ_HUMAN).get_prompt(
        target_area=target_area,
        main_type=main_type,
        total_units=total_units,
        hosuing_faq_context=faq_context,
        hosuing_rule_context=rule_context,
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt),
    ]

    return {messages_key: messages}


from utils.llm import LLMProfile

llm = LLMProfile.analysis_llm()


def call_llm(state: HousingFaqState) -> HousingFaqState:
    messages = state.get(messages_key, [])
    response = llm.invoke(messages)
    new_messages = messages + [response]
    new_state = {**state, messages_key: new_messages}
    new_state[output_key] = {
        "result": response.content,
        housing_faq_context_key: state[housing_faq_context_key],
        housing_rule_context_key: state[housing_rule_context_key],
        housing_faq_download_link_key: state[housing_faq_download_link_key],
        housing_rule_download_link_key: state[housing_rule_download_link_key],
    }
    return new_state


graph_builder = StateGraph(HousingFaqState)
graph_builder.add_node("get_rule_data", get_rule_data)
graph_builder.add_node("get_faq_data", get_faq_data)
graph_builder.add_node("analysis_setting", analysis_setting)
graph_builder.add_node("call_llm", call_llm)

graph_builder.add_edge(START, "get_rule_data")
graph_builder.add_edge(START, "get_faq_data")
graph_builder.add_edge("get_rule_data", "analysis_setting")
graph_builder.add_edge("get_faq_data", "analysis_setting")
graph_builder.add_edge("analysis_setting", "call_llm")
graph_builder.add_edge("call_llm", END)

housing_faq_graph = graph_builder.compile()
