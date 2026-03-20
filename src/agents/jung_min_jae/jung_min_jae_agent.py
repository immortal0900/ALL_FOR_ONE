from langgraph.graph import StateGraph, START, END
from utils.llm import LLMProfile
from prompts import PromptManager, PromptType
from utils.util import get_today_str
from langchain_core.messages import SystemMessage, HumanMessage
from agents.state.jung_min_jae_state import JungMinJaeState
from agents.state.start_state import StartInput
from agents.state.analysis_state import AnalysisGraphState


analysis_outputs_key = JungMinJaeState.KEY.analysis_outputs
start_input_key = JungMinJaeState.KEY.start_input
rag_context_key = JungMinJaeState.KEY.rag_context
final_report_key = JungMinJaeState.KEY.final_report
final_draft_key = JungMinJaeState.KEY.final_draft
segment_key = JungMinJaeState.KEY.segment
segment_buffers_key = JungMinJaeState.KEY.segment_buffers
messages_key = JungMinJaeState.KEY.messages
review_feedback_key = JungMinJaeState.KEY.review_feedback

location_insight_output_key = "location_insight"
policy_output_key = "policy_output"
housing_faq_output_key = "housing_faq"
nearby_market_output_key = "nearby_market"
population_insight_output_key = "population_insight"
supply_demand_output_key = "supply_demand"
unsold_insight_output_key = "unsold_insight"

target_area_key = StartInput.KEY.target_area
main_type_key = StartInput.KEY.main_type
total_units_key = StartInput.KEY.total_units

llm = LLMProfile.report_llm()


def segment_directive(seg: int) -> str:
    if seg == 1:
        return PromptManager(PromptType.JUNG_MIN_JAE_SEGMENT_01).get_prompt()
    if seg == 2:
        return PromptManager(PromptType.JUNG_MIN_JAE_SEGMENT_02).get_prompt()
    if seg == 3:
        return PromptManager(PromptType.JUNG_MIN_JAE_SEGMENT_03).get_prompt()
    return PromptManager(PromptType.JUNG_MIN_JAE_SEGMENT_04).get_prompt()


def prev_segment_context(state: JungMinJaeState) -> str | None:
    # 이전 대화 기록이 LLM의 Memory(messages)에 누적되므로
    # 별도로 요약(summary)을 생성할 필요가 없어 비활성화 처리합니다. (토큰 폭발 방지)
    return None


def retriever(state: JungMinJaeState) -> JungMinJaeState:
    _ = state[start_input_key]
    return {rag_context_key: "rag_test"}


def reporting(state: JungMinJaeState) -> JungMinJaeState:
    seg = state.get(segment_key, 1)

    start_input = state.get(start_input_key, {}) or {}
    analysis_outputs = state.get(analysis_outputs_key, {}) or {}

    target_area = start_input.get(target_area_key, "")
    main_type = start_input.get(main_type_key, "")
    total_units = start_input.get(total_units_key, "")

    location_insight = analysis_outputs.get(location_insight_output_key, {}).get("result", "")
    policy = analysis_outputs.get(policy_output_key, {}).get("result", "")
    housing_faq = analysis_outputs.get(housing_faq_output_key, {}).get("result", "")
    nearby_market = analysis_outputs.get(nearby_market_output_key, {}).get("result", "")
    population_insight = analysis_outputs.get(population_insight_output_key, {}).get("result", "")
    supply_demand = analysis_outputs.get(supply_demand_output_key, {}).get("result", "")
    unsold_insight = analysis_outputs.get(unsold_insight_output_key, {}).get("result", "")

    directive = segment_directive(seg)
    prev_context = ""

    # 기초 자료(Context)는 첫 번째 세그먼트(seg==1)에서 단 한 번만 주입하여
    # State(messages)에 중복복사되는 토큰 폭발을 막습니다.
    # LLM의 Attention 기능으로 seg 2,3,4 도 이 내용을 완벽히 참조합니다.
    if seg == 1:
        system_prompt = PromptManager(PromptType.JUNG_MIN_JAE_SYSTEM).get_prompt(
            date=get_today_str()
        )
        human_prompt = PromptManager(PromptType.JUNG_MIN_JAE_HUMAN).get_prompt(
            target_area=target_area,
            main_type=main_type,
            total_units=total_units,
            housing_faq=housing_faq,
            location_insight=location_insight,
            policy=policy,
            supply_demand=supply_demand,
            unsold_insight=unsold_insight,
            population_insight=population_insight,
            nearby_market=nearby_market,
        )
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"{human_prompt}\n\n{directive}"),
        ]
    else:
        # 두 번째 세그먼트부터는 (방대한 기초 자료 없이) 해당 세그먼트 지시서만 전달
        messages = [
            HumanMessage(content=f"이어지는 작성 지침입니다:\n{directive}")
        ]

    return {messages_key: messages}


def agent(state: JungMinJaeState) -> JungMinJaeState:
    """세그먼트별 보고서 생성"""
    messages = state.get(messages_key, [])
    seg = state.get(segment_key, 1)
    buffers = dict(state.get(segment_buffers_key, {}))

    response = llm.invoke(messages)
    buffers[f"seg{seg}"] = response.content

    new_state = {**state}
    new_state[messages_key] = messages + [response]
    new_state[segment_buffers_key] = buffers
    if seg <= 4:
        new_state[segment_key] = seg + 1
    return new_state


def finalize_merge(state: JungMinJaeState) -> JungMinJaeState:
    """세그먼트 병합 후, 목차/헤더/구분선 간단 정리"""
    buffers = state.get(segment_buffers_key, {})
    merged = "\n\n".join(
        [
            buffers.get("seg1", ""),
            buffers.get("seg2", ""),
            buffers.get("seg3", ""),
            buffers.get("seg4", ""),
        ]
    )
    merged = merged.replace("\n\n--\n\n", "\n\n---\n\n")  # 구분선 통일
    return {final_draft_key: merged}


def bypass_reflection(state: JungMinJaeState) -> JungMinJaeState:
    """think_tool 제거 실험: reflection 파이프라인을 우회하여 draft를 그대로 final_report로 전달"""
    return {final_report_key: state.get(final_draft_key, ""), review_feedback_key: ""}


def router(state: JungMinJaeState):
    """세그먼트 진행/병합 분기"""
    seg = state.get(segment_key, 1)

    if seg <= 4:
        return "reporting"

    # seg == 5 (4 초과)
    if not state.get(final_report_key):
        return "finalize_merge"

    # 병합 완료 후에는 bypass로 바로 종료
    return "bypass_reflection"


# -------------------------
# 6) 그래프 구성
# -------------------------
retriever_key = "retriever"
reporting_key = "reporting"
agent_key = "agent"
finalize_key = "finalize_merge"
bypass_reflection_key = "bypass_reflection"

graph_builder = StateGraph(JungMinJaeState)

# 노드 추가
graph_builder.add_node(retriever_key, retriever)
graph_builder.add_node(reporting_key, reporting)
graph_builder.add_node(agent_key, agent)
graph_builder.add_node(finalize_key, finalize_merge)
graph_builder.add_node(bypass_reflection_key, bypass_reflection)

# 엣지 구성
graph_builder.add_edge(START, retriever_key)
graph_builder.add_edge(retriever_key, reporting_key)
graph_builder.add_edge(reporting_key, agent_key)

# 에이전트 루프 → 병합 분기
graph_builder.add_conditional_edges(
    agent_key,
    router,
    [reporting_key, finalize_key, bypass_reflection_key, END],
)

# 병합 이후 bypass로 바로 종료
graph_builder.add_edge(finalize_key, bypass_reflection_key)
graph_builder.add_edge(bypass_reflection_key, END)

# 그래프 컴파일
report_graph = graph_builder.compile()
