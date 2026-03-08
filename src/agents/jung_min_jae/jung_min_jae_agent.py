from langgraph.graph import StateGraph, START, END
from langchain_core.tools import tool
from utils.llm import LLMProfile
from prompts import PromptManager, PromptType
from utils.util import get_today_str
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from agents.state.jung_min_jae_state import JungMinJaeState
from agents.state.start_state import StartInput
from agents.state.analysis_state import AnalysisGraphState

# ToolNode import (버전 호환)
try:
    from langgraph.prebuilt import ToolNode
except Exception:
    from langgraph.prebuilt.tool_node import ToolNode


@tool(parse_docstring=True)
def think_tool(reflection: str) -> str:
    """부동산 대행사 핵심 분석가가 분양성 검토 보고서를 완성하기 전에 **자체 검증(자아성찰)**을 수행하는 도구입니다.

    Args:
        reflection (str): 방금 작성한 보고서 초안 또는 섹션 내용.

    Returns:
        str: 점검 결과 및 개선 제안 Markdown 텍스트.

    점검 기준:
        1. 각 페이지 시작부에 핵심 인사이트의 근거가 명확한가
        2. 근거로 사용할 데이터를 명확하게 표기했는가
        3. 근거로 사용할 데이터는 정확한 데이터인가
        4. 비슷한 스펙의 주변 매매아파트, 분양아파트와 요인비교분석에 현재의 정책, 경제지표, 공급과 수요, 미분양 분석, 인구 분석 등의 내용을 종합해서 분양성과 분양가를 평가 했는가
        5. 최종 보고서 양식을 벗어난 불필요한 말을 하지 않았는가


    위 기준에 따라 **보완 의견**을 Markdown 형식으로 작성하고,
    필요 시 개선 제안이나 문장 수정 예시도 함께 포함한다.
    """
    return f"Reflection recorded: {reflection}"


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
reflect_llm = LLMProfile.dev_llm().bind_tools([think_tool])


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
    # seg = state.get(segment_key, 1)
    # if seg <= 1:
    #     return None

    # summary_prompt = PromptManager(PromptType.JUNG_MIN_JAE_SUMMARY).get_prompt()
    # buffers = state.get(segment_buffers_key, {})
    # segments = list(buffers.values())
    # response = LLMProfile.dev_llm().invoke(
    #     [SystemMessage(content=summary_prompt), HumanMessage(content=str(segments))]
    # )
    # return f"# 이전 세그먼트 요약/맥락\n{response.content}"
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

    location_insight = analysis_outputs.get(location_insight_output_key, {})["result"]
    policy = analysis_outputs.get(policy_output_key, {})["result"]
    housing_faq = analysis_outputs.get(housing_faq_output_key, {})["result"]
    nearby_market = analysis_outputs.get(nearby_market_output_key, {})["result"]
    population_insight = analysis_outputs.get(population_insight_output_key, {})["result"]
    supply_demand = analysis_outputs.get(supply_demand_output_key, {})["result"]
    unsold_insight = analysis_outputs.get(unsold_insight_output_key, {})["result"]

    directive = segment_directive(seg)
    # prev_context = prev_segment_context(state) or ""
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


def reflection_prompt(state: JungMinJaeState) -> JungMinJaeState:
    """LLM이 도구(think_tool)를 반드시 호출하도록 지시하되,
    reflection 파라미터에는 '원문이 아닌 네가 만든 검토 결과'만 담게 한다."""
    final_text = state.get(final_draft_key, "")  # ✅ draft를 대상으로
    msgs = state.get(messages_key, []) or []

    sys = SystemMessage(
        content=(
            "너는 품질 검증자다. 반드시 `think_tool`만 tool call로 호출해서 '검토 결과'를 생성하라. "
            "원문 전체를 넘기지 말고, 체크리스트에 따른 네 자가점검 결과(수정 제안 포함)를 "
            "tool 파라미터 `reflection`에 넣어 제출하라. 일반 텍스트로 답하지 말고 오직 도구만 호출하라."
        )
    )
    hm = HumanMessage(
        content=(
            "아래 최종 병합 텍스트를 검토하라. 체크리스트 기반으로 **문장 수정 제안/누락 데이터/근거 표기** "
            "등을 정리한 네 '검토 결과'를 만들어, 반드시 `think_tool`로 제출해라.\n\n"
            f"### 대상 텍스트\n{final_text}"
        )
    )
    return {messages_key: msgs + [sys, hm]}


def reflect_agent(state: JungMinJaeState) -> JungMinJaeState:
    """도구 바인딩된 LLM으로 tool_call 유도"""
    msgs = state.get(messages_key, [])
    resp = reflect_llm.invoke(msgs)
    return {messages_key: msgs + [resp]}


def apply_reflection(state: JungMinJaeState) -> JungMinJaeState:
    draft = state.get(final_draft_key, "") or ""
    msgs = state.get(messages_key, []) or []

    feedback = ""
    for m in reversed(msgs):
        if isinstance(m, ToolMessage) and (
            getattr(m, "name", "") == "think_tool"
            or m.additional_kwargs.get("name") == "think_tool"
        ):
            feedback = m.content or ""
            break

    if feedback.strip():
        editor_sys = SystemMessage(
            content=(
                "너는 수석 편집자다. 아래 [초안]을 [피드백]을 반영해 수정하라. "
                "반드시 '고객에게 전달할 최종 보고서 본문만' 출력하고, "
                "피드백 원문이나 메모, 머리말/꼬리말 같은 부가 텍스트는 싣지 마라. "
                "**반드시 Markdown 형식으로 작성하세요. # 는 대제목, ## 는 소제목, ### 는 주요지표입니다.**"
            )
        )
        editor_hm = HumanMessage(content=f"[초안]\n{draft}\n\n[피드백]\n{feedback}")
        revised = llm.invoke([editor_sys, editor_hm]).content
        return {final_report_key: revised, review_feedback_key: feedback}
    else:
        return {final_report_key: draft, review_feedback_key: ""}


def router(state: JungMinJaeState):
    """세그먼트 진행/병합/성찰 분기"""
    seg = state.get(segment_key, 1)

    if seg <= 4:
        return "reporting"

    # seg == 5 (4 초과)
    if not state.get(final_report_key):
        return "finalize_merge"

    # 병합 완료 후에는 성찰 프롬프트 단계로
    return "reflection_prompt"


# -------------------------
# 6) 그래프 구성
# -------------------------
retriever_key = "retriever"
reporting_key = "reporting"
agent_key = "agent"
finalize_key = "finalize_merge"
reflection_prompt_key = "reflection_prompt"
reflect_agent_key = "reflect_agent"
tool_node_key = "think_tool_node"
apply_reflection_key = "apply_reflection"

graph_builder = StateGraph(JungMinJaeState)

# 노드 추가
graph_builder.add_node(retriever_key, retriever)
graph_builder.add_node(reporting_key, reporting)
graph_builder.add_node(agent_key, agent)
graph_builder.add_node(finalize_key, finalize_merge)
graph_builder.add_node(reflection_prompt_key, reflection_prompt)
graph_builder.add_node(reflect_agent_key, reflect_agent)

# ToolNode: think_tool을 실제 LangGraph 도구 실행 노드로 등록
tool_node = ToolNode(tools=[think_tool], messages_key=messages_key)
graph_builder.add_node(tool_node_key, tool_node)

graph_builder.add_node(apply_reflection_key, apply_reflection)

# 엣지 구성
graph_builder.add_edge(START, retriever_key)
graph_builder.add_edge(retriever_key, reporting_key)
graph_builder.add_edge(reporting_key, agent_key)

# 에이전트 루프 → 병합/성찰로 분기
graph_builder.add_conditional_edges(
    agent_key,
    router,
    [reporting_key, finalize_key, reflection_prompt_key, END],
)

# 병합 이후 성찰 흐름
graph_builder.add_edge(finalize_key, reflection_prompt_key)
graph_builder.add_edge(reflection_prompt_key, reflect_agent_key)
graph_builder.add_edge(reflect_agent_key, tool_node_key)
graph_builder.add_edge(tool_node_key, apply_reflection_key)
graph_builder.add_edge(apply_reflection_key, END)

# 그래프 컴파일
report_graph = graph_builder.compile()
