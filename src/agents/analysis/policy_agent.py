# 구조와 상태 정의
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

# 프로젝트 내부 모듈
from agents.state.analysis_state import PolicyState
from agents.state.start_state import StartInput
from agents.state.policy_types import ReportCheck
from prompts import PromptManager, PromptType
from tools.context_to_csv import region_news_to_drive, netional_news_to_drive
from tools.estate_web_crawling_tool import collect_articles_result
from tools.rag.retriever.policy_pdf_retriever import PolicyPDFRetriever
from tools.rag.retriever.national_policy_retriever import national_policy_retrieve
from tools.perplexity_search_tool import perplexity_search
from utils.llm import LLMProfile
from utils.util import get_today_str


@tool(parse_docstring=True)
def think_tool(reflection: str) -> str:
    """
    각 노드가 끝날 때마다 메모를 남기는 도구, 내부 반성·점검(Reflection)용

    Args:
        reflection: 중간 추론 내용(체크리스트, 검증사항, 계획 등)

    Returns:
        추론이 기록되었다는 확인 메세지

    [RAG 충실도 규칙 - 반드시 준수]
    - 검색된 보도자료/뉴스 원문의 정확한 수치와 문구를 인용할 것
    - 검색 결과에 명시되지 않은 내용을 추론하거나 일반화하지 말 것
    - 출처를 [보도자료 제목, 날짜] 또는 [뉴스 제목, 날짜] 형식으로 반드시 기록할 것
    - Supabase에서 검색된 청약 규정/FAQ 데이터는 원문 그대로 인용하고 재해석하지 말 것
    """
    return f"Reflection recorded: {reflection}"


llm = LLMProfile.analysis_llm()
tool_list = [think_tool, perplexity_search]
llm_with_tools = llm.bind_tools(tool_list)
tool_node = ToolNode(tool_list)
evaluator_llm = llm.with_structured_output(ReportCheck)


output_key = PolicyState.KEY.policy_output
start_input_key = PolicyState.KEY.start_input
target_area_key = StartInput.KEY.target_area
policy_period_key = StartInput.KEY.policy_period
policy_count_key = StartInput.KEY.policy_count
policy_list_key = StartInput.KEY.policy_list
messages_key = PolicyState.KEY.messages
national_context_key = PolicyState.KEY.national_context
region_context_key = PolicyState.KEY.region_context
national_download_link_key = PolicyState.KEY.national_download_link
region_download_link_key = PolicyState.KEY.region_download_link
pdf_context_key = PolicyState.KEY.pdf_context
retry_count_key = PolicyState.KEY.retry_count

MAX_ITERATIONS = 3  # 재검색 최대 횟수, LLM이 전체 보고서를 작성 → 평가 → 재검색하는 전체 사이클당 1번씩 증가


def record_reflection(title: str, hint: str) -> None:
    """
    노드가 끝날 때마다 think_tool 도구를 호출하여 간단한 메모 남김
    """
    think_tool.invoke({"reflection": f"{title}\n{hint}"})


# 1. 자료수집
def national_news(state: PolicyState) -> PolicyState:
    docs = national_policy_retrieve()
    record_reflection("국가 뉴스 수집", "전국 정책 기사 정리")
    return {
        national_context_key: docs,
        national_download_link_key: netional_news_to_drive(docs),
    }


def region_news(state: PolicyState) -> PolicyState:
    docs = collect_articles_result()
    record_reflection("지역 뉴스 수집", "지역 기사 묶음 확보")
    return {
        region_context_key: docs,
        region_download_link_key: region_news_to_drive(docs),
    }


def policy_pdf_retrieve(state: PolicyState) -> PolicyState:
    retriever = PolicyPDFRetriever()
    start_input = state.get(start_input_key, {})
    policy_period = start_input.get(StartInput.KEY.policy_period, "")
    policy_count = start_input.get(StartInput.KEY.policy_count, "")
    policy_list = start_input.get(StartInput.KEY.policy_list, "")
    target_area = start_input.get(StartInput.KEY.target_area, "")

    # 검색 쿼리 구성: policy_list가 있으면 우선 사용
    query_parts = []
    if policy_list:
        # policy_list가 있으면 이를 최우선으로 사용
        query_parts.append(policy_list)
        record_reflection("정책 리스트 우선", f"policy_list 사용: {policy_list}")
    elif policy_period:
        query_parts.append(policy_period)

    if target_area:
        query_parts.append(target_area)

    query = " ".join(query_parts) if query_parts else target_area or "정책"

    # policy_count를 k 값으로 사용 (기본값 3)
    try:
        k = int(policy_count) if policy_count else 3
    except (ValueError, TypeError):
        k = 3

    docs = retriever.hybrid_search(query, k=k * 2)  # 더 많은 문서 검색
    record_reflection("PDF 검색", f"정책 PDF 주요 문단 확보: {query}")
    return {pdf_context_key: docs}


# 프롬프트 세팅
def analysis_setting(state: PolicyState) -> PolicyState:
    start_input = state[start_input_key]
    policy_period = start_input[StartInput.KEY.policy_period]
    policy_count = start_input[StartInput.KEY.policy_count]
    policy_list = start_input[StartInput.KEY.policy_list]
    target_area_value = start_input[StartInput.KEY.target_area]

    system_prompt = PromptManager(PromptType.POLICY_SYSTEM).get_prompt(
        policy_period=policy_period,
        policy_count=policy_count,
        policy_list=policy_list,
    )
    human_prompt = PromptManager(PromptType.POLICY_HUMAN).get_prompt(
        target_area=target_area_value,
        date=get_today_str(),
        national_news_context=state[national_context_key],
        region_news_context=state[region_context_key],
        policy_period=policy_period,
        policy_count=policy_count,
        policy_list=policy_list,
        main_type=start_input.get(StartInput.KEY.main_type, ""),
        total_units=start_input.get(StartInput.KEY.total_units, ""),
        pdf_context=state.get(pdf_context_key, ""),
    )
    # Segment 01: 뉴스 정보만 제공
    segment_01_prompt = PromptManager(
        PromptType.POLICY_COMPARISON_SEGMENT_01
    ).get_prompt(
        target_area=target_area_value,
        main_type=start_input.get(StartInput.KEY.main_type, ""),
        total_units=start_input.get(StartInput.KEY.total_units, ""),
        national_news_context=state[national_context_key],
        region_news_context=state[region_context_key],
    )

    # Segment 02: comp.md 스타일 정책 비교 (전체 구조 포함)
    segment_02_prompt = PromptManager(
        PromptType.POLICY_COMPARISON_SEGMENT_02
    ).get_prompt(
        policy_period=policy_period,
        policy_count=policy_count,
        policy_list=policy_list,
        pdf_context=state.get(pdf_context_key, ""),
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt),
        HumanMessage(content=segment_01_prompt),
        HumanMessage(content=segment_02_prompt),
    ]
    record_reflection("프롬프트 준비", "SEGMENT 01(뉴스) + SEGMENT 02(comp.md 전체)")
    return {
        messages_key: messages,
        "documents": state.get(pdf_context_key, []),
        "yaml_context": {
            "summary": PromptManager(PromptType.POLICY_COMPARISON_SUMMARY).get_prompt(
                target_area=target_area_value,
                pdf_context=state.get(pdf_context_key, ""),
            ),
            "segment_01": segment_01_prompt,
            "segment_02": segment_02_prompt,
        },
        "iteration": 0,
    }


# 3. 보고서 작성 및 평가
def generate_initial_report(state: PolicyState) -> PolicyState:
    """
    자료 기반 보고서 초안 작성
    comp.md 스타일로 작성하도록 지시
    """
    messages = state[messages_key]

    # comp.md 스타일로 작성하라는 추가 지시 추가
    format_instruction = HumanMessage(
        content=(
            "\n\n**최우선 지시: 먼저 제공된 PDF 자료로 보고서를 작성하세요!**\n"
            "PDF 정보로 최대한 작성하되, 정말 필요한 경우에만 perplexity_search 도구를 사용하세요.\n\n"
            "**보고서는 반드시 SEGMENT 2의 구조를 정확히 따라 작성하세요:**\n"
            "SEGMENT 1의 뉴스 정보를 참고하되, 보고서에는 포함하지 마세요.\n"
            "SEGMENT 2의 comp.md 스타일 구조(개요 → 정책 목표 → 주요 정책 비교 10개 항목 → 주요 차이점 요약 → 평가 및 반응 → 전망 및 과제)를 정확히 따라 작성하세요.\n\n"
            "**6가지 엄격한 규칙:**\n"
            "1. 보고서 시작 금지: '※', '아래는', '주의사항' 등 메타 설명 절대 금지. 바로 '## **개요**'부터 시작\n"
            "2. 할루시네이션 절대 금지: PDF에 명시된 정확한 수치만 사용. PDF에 없으면 빈칸('-') 또는 생략\n"
            "3. 애매한 표현 완전 금지 생략하지 않고 구체적 정보를 기재: '동일', '유지', '기존 규제 유지', '변동 없음', '동일 적용', '같음' 등 모든 애매한 표현 절대 금지\n"
            "   - 나쁜 예: 'LTV 동일', '기존과 동일', '동일 (유지)'\n"
            "   - 좋은 예: '수도권 규제지역 LTV 40% (무주택·1주택 기준)'\n"
            "4. 출처 필수 명시: 각 표 항목과 내용마다 [출처: 파일명] 형식으로 출처 명시\n"
            "5. PDF 없는 내용 처리 (선택적):\n"
            "   - 빈칸('-')이 3개 이상이면 perplexity_search 도구 사용 고려\n"
            "   - perplexity_search('구체적인 질문') 형태로 호출\n"
            "   - Perplexity 결과 사용 시: '[출처: Perplexity - 링크]' 형식으로 명시\n"
            "   - 예: perplexity_search('2025년 6월 27일 디딤돌 대출 일반 한도')\n"
            "6. Perplexity 출처 표기:\n"
            "   - Perplexity 답변에 포함된 링크를 반드시 함께 표기\n"
            "   - 형식예시: [출처: Perplexity - https://example.com]\n\n"
            "표는 간결하게 작성하고, 핵심 내용만 포함하세요. "
            "장황한 설명은 제거하고 사실만 기록하세요.\n"
            "policy_list에 명시된 정책들을 우선적으로 비교 분석하세요.\n\n"
            "**지금 바로 보고서를 작성하세요 (## **개요**부터 시작):**"
        )
    )

    messages_with_format = messages + [format_instruction]
    response = llm_with_tools.invoke(
        messages_with_format
    )  # LLM에 메시지를 전달하여 보고서 초안을 생성
    new_messages = messages + [response]
    record_reflection("초안 작성", "자료 기반 첫 보고서 작성")
    return {
        messages_key: new_messages,
        "report_draft": response.content,
    }


def evaluate_report_completeness(state: PolicyState) -> PolicyState:
    """
    보고서 완성도 평가
    
    """
    draft = state["report_draft"]
    yaml_context = state.get("yaml_context", {})

    # Segment 02 스타일의 필수 구조 체크
    required_structure = (
        "SEGMENT 2의 구조를 모두 포함해야 합니다:\n"
        "1. 개요 (각 정책의 정식 명칭, 배경, 성격, 시행 시점, 출처)\n"
        "2. 정책 목표 (각 정책별 목표)\n"
        "3. 주요 정책 비교 (표 형식으로 10개 항목):\n"
        "   - 1. 주택담보대출 한도\n"
        "   - 2. 다주택자 규제\n"
        "   - 3. 실거주 의무\n"
        "   - 4. 생애최초 주택구입자 규제\n"
        "   - 5. 규제지역 지정\n"
        "   - 6. DSR(총부채원리금상환비율) 규제\n"
        "   - 7. 전세대출 및 신용대출\n"
        "   - 8. 가계대출 총량 관리\n"
        "   - 9. 생활안정자금 목적 주담대\n"
        "   - 10. 중도금 대출 규제\n"
        "4. 주요 차이점 요약 (각 정책의 특징)\n"
        "5. 평가 및 반응 (긍정적/부정적 평가, 출처)\n"
        "6. 전망 및 과제 (단기 효과, 장기 과제)\n"
        "7. 참고 자료 (각 정책 보도자료 링크)\n\n"
        "**추가 체크사항:**\n"
        "- '동일', '유지', '기존 규제 유지', '변동 없음', '동일 적용' 같은 애매한 표현이 없는지 확인\n"
        "- 모든 항목에 구체적인 수치와 내용이 있는지 확인\n"
        "- 각 항목에 출처가 명시되어 있는지 확인\n"
    )

    template = (
        required_structure + "=== Segment 02 ===\n"
        f"{yaml_context.get('segment_02', '')}\n\n"
    )
    prompt = (
        "다음 *보고서 초안*이 *SEGMENT 2의 구조*를 모두 채웠는지 살펴보고, 부족한 항목과 검색어를 알려주세요.\n\n"
        f"[필수 구조]\n{required_structure}\n\n"
        f"[템플릿]\n{template}\n\n"
        f"[보고서 초안]\n{draft}"
    )
    check = evaluator_llm.invoke(prompt)
    record_reflection("완성도 평가", "필수 섹션 충족 여부 판단")
    return {"completeness_check": check}


def decide_next_step(state: PolicyState) -> str:
    """
    조건분기: 완성 시 종료, 부족하면 재검색
    """
    check = state[
        "completeness_check"
    ]  # 이전 단계에서 평가한 보고서 완성도 결과 가져옴
    if check.is_complete:
        return "__end__"
    if (
        state.get("iteration", 0) >= MAX_ITERATIONS
    ):  # 최대 반복 횟수에 도달하면 더 이상 재검색하지 않고 종료
        return "__end__"
    return "execute_retrieval"  # 보고서에 부족한 내용이 있으니 추가 자료를 검색하는 노드(execute_retrieval)로 이동
    #  "execute_retrieval" 는 다음 노드


# 4. 재검색과 수정
def execute_additional_retrieval(state: PolicyState) -> PolicyState:
    queries = state[
        "completeness_check"
    ].search_queries  # evaluate_report_completeness에서 나온 부족한 항목과 검색어 리스트
    retriever = PolicyPDFRetriever()
    new_docs = []
    for query in queries:
        new_docs.extend(
            retriever.hybrid_search(query, k=3)
        )  # 각 검색어로 관련 문서를 찾아서 new_docs 리스트에 추가
    added_docs = state["documents"] + new_docs
    record_reflection("추가 검색", "부족한 섹션 보강 자료 확보")
    return {
        "documents": added_docs,
        "iteration": state.get("iteration", 0) + 1,
    }


def revise_report(state: PolicyState) -> PolicyState:
    draft = state["report_draft"]
    check = state["completeness_check"]
    docs = state["documents"]
    prompt = (
        "이전 초안과 부족했던 내용을 참고해 보고서를 보완해 주세요.\n\n"
        "**중요: SEGMENT 2의 comp.md 스타일을 정확히 유지하세요.**\n"
        "구조: 개요 → 정책 목표 → 주요 정책 비교 10개 항목(표 형식) → 주요 차이점 요약 → 평가 및 반응 → 전망 및 과제 → 참고 자료\n\n"
        "**5가지 엄격한 규칙 준수:**\n"
        "1. 메타 설명 절대 금지: '※', '아래는', '주의사항' 등 제거\n"
        "2. 할루시네이션 금지: PDF의 정확한 수치만 사용. PDF 없으면 빈칸('-')\n"
        "3. 애매한 표현 완전 금지: '동일', '유지', '기존 규제 유지', '변동 없음', '동일 적용' 등 절대 금지\n"
        "   - 반드시 구체적 내용으로 작성 (예: 수도권 규제지역 LTV 40%)\n"
        "4. 출처 명시: 모든 내용에 [출처: 파일명] 추가\n"
        "5. PDF 없는 내용: 빈칸('-') 또는 perplexity_search 도구로 검색 후 [출처: Perplexity]\n\n"
        f"[부족한 섹션]\n{check.missing_sections}\n\n"
        f"[필요한 정보]\n{check.missing_information}\n\n"
        f"[추가 자료]\n{docs}\n\n"
        f"[이전 초안]\n{draft}\n\n"
        "표는 간결하게 작성하고 핵심만 포함하세요.\n"
        "policy_list에 명시된 정책들을 우선적으로 비교하세요."
    )
    reply = llm_with_tools.invoke([HumanMessage(content=prompt)])
    record_reflection("보고서 수정", "추가 자료 반영")
    return {
        "report_draft": reply.content,  #  LLM이 생성한 수정된 보고서 내용을 report_draft 상태 키에 저장장. reply는 llm_with_tools.invoke()의 응답 객체이고, .content는 실제 텍스트 내용
        messages_key: state[messages_key]
        + [reply],  # 대화 로그에 수정된 보고서 내용을 추가
    }


def agent(state: PolicyState) -> PolicyState:
    """최종 결과 묶어 반환"""

    output = {
        "result": state["report_draft"],
        national_context_key: state[national_context_key],
        region_context_key: state[region_context_key],
        national_download_link_key: state[national_download_link_key],
        region_download_link_key: state[region_download_link_key],
    }
    record_reflection("최종 기록", "보고서와 참고링크 정리")
    return {output_key: output}


def router(state: PolicyState) -> str:
    """Tool 호출 여부에 따라 분기"""
    messages = state[messages_key]
    last_ai_message = messages[-1]
    if hasattr(last_ai_message, 'tool_calls') and last_ai_message.tool_calls:
        return "tools"
    return "evaluate_completeness"


national_news_key = "national_news"
region_news_key = "region_news"
analysis_setting_key = "analysis_setting"
tools_key = "tools"
agent_key = "agent"
draft_key = "draft"
policy_pdf_retrieve_key = "policy_pdf_retrieve"
analysis_setting_key = "analysis_setting"
execute_retrieval_key = "execute_retrieval"
evaluate_completeness_key = "evaluate_completeness"
revise_report_key = "revise"


graph_builder = StateGraph(PolicyState)
graph_builder.add_node(national_news_key, national_news)
graph_builder.add_node(region_news_key, region_news)
graph_builder.add_node(policy_pdf_retrieve_key, policy_pdf_retrieve)
graph_builder.add_node(analysis_setting_key, analysis_setting)
graph_builder.add_node(draft_key, generate_initial_report)
graph_builder.add_node(execute_retrieval_key, execute_additional_retrieval)
graph_builder.add_node(evaluate_completeness_key, evaluate_report_completeness)
graph_builder.add_node(revise_report_key, revise_report)
graph_builder.add_node(tools_key, tool_node)
graph_builder.add_node(agent_key, agent)

graph_builder.add_edge(START, national_news_key)
graph_builder.add_edge(START, region_news_key)
graph_builder.add_edge(national_news_key, policy_pdf_retrieve_key)
graph_builder.add_edge(region_news_key, policy_pdf_retrieve_key)
graph_builder.add_edge(policy_pdf_retrieve_key, analysis_setting_key)
graph_builder.add_edge(analysis_setting_key, draft_key)

# draft 노드에서 tool 호출 여부에 따라 분기
graph_builder.add_conditional_edges(
    draft_key,
    router,
    {
        "tools": tools_key,
        "evaluate_completeness": evaluate_completeness_key,
    },
)

# tool 실행 후 다시 draft로
graph_builder.add_edge(tools_key, draft_key)

graph_builder.add_conditional_edges(
    evaluate_completeness_key,
    decide_next_step,
    [execute_retrieval_key, END],
)

graph_builder.add_edge(execute_retrieval_key, revise_report_key)

# revise 노드에서도 tool 호출 가능
graph_builder.add_conditional_edges(
    revise_report_key,
    router,
    {
        "tools": tools_key,
        "evaluate_completeness": evaluate_completeness_key,
    },
)

graph_builder.add_edge(evaluate_completeness_key, agent_key)

policy_graph = graph_builder.compile()
