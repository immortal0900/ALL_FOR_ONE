from langgraph.graph import StateGraph, START, END
from agents.state.analysis_state import SupplyDemandState
from langchain_core.tools import tool
from agents.state.start_state import StartInput
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from utils.util import get_today_str
from utils.llm import LLMProfile

from prompts import PromptManager, PromptType
from langgraph.prebuilt import ToolNode
import json
from tools.context_to_csv import (
    jense_to_drive,
    sales_to_drive,
    rate_to_drive,
    home_mortagage_to_drive,
    housing_sales_volume_to_drive,
    planning_move_to_csv,
    pre_promise_competition_to_csv,
    gdp_and_grdp_to_drive,
)


@tool(parse_docstring=False)
def think_tool(reflection: str) -> str:
    """
    [역할]
    당신은 공급과 수요 정리 전문가의 내부 반성·점검(Reflection) 담당자입니다.
    최종 보고서에 들어갈 본문(Markdown)을 쓰기 직전에, 데이터 품질·시계열 해석·핵심 수치·리스크·보고서용 한 줄 메시지를 짧고 구조적으로 요약해 think_tool에 기록합니다. 이 반성문은 내부용이며, 최종 보고서에 직접 노출되지 않습니다.

    [언제 호출할 것인지]
    - 데이터 수집/정제 → 핵심 수치 산출 → 시계열 해석을 마친 직후 1회 호출(필수)
    - 추가 데이터로 추세가 바뀌면 갱신 시마다 1회 재호출(선택)

    [강력 지시]
    - 해당 지역에 관련된 내용만 기록
    - 허상 가정,출처 수치 금지
    - 다음 단계(보고서 에이전트)가 바로 쓸 수 있는 한 줄 핵심 메시지 포함

    [나쁜 예]
    - “경제가 좋아진듯함. 분위기 좋음.”(수치·기간·단위·근거 없음)
    - “인근 해운대의 GRDP는 이렇다~”(대상 지역 외 서술)
    - “향후 집값 상승 확실.”(근거 없는 단정)

    [검증 체크리스트]
    - 정량 수치가 어긋난 것 이 있는가?
    - GPT가 시계열 판단하기에 좋은 형식으로 되어있는가?
    - 잘못된 내용은 없는가?
    """
    return f"Reflection recorded: {reflection}"


output_key = SupplyDemandState.KEY.supply_demand_output
start_input_key = SupplyDemandState.KEY.start_input
messages_key = SupplyDemandState.KEY.messages
target_area_key = StartInput.KEY.target_area
year10_after_house_key = SupplyDemandState.KEY.year10_after_house
jeonse_price_key = SupplyDemandState.KEY.jeonse_price
sale_price_key = SupplyDemandState.KEY.sale_price
trade_balance_key = SupplyDemandState.KEY.trade_balance
use_kor_rate_key = SupplyDemandState.KEY.use_kor_rate
home_mortgage_key = SupplyDemandState.KEY.home_mortgage
one_people_gdp_key = SupplyDemandState.KEY.one_people_gdp
one_people_grdp_key = SupplyDemandState.KEY.one_people_grdp
housing_sales_volume_key = SupplyDemandState.KEY.housing_sales_volume
planning_move_key = SupplyDemandState.KEY.planning_move
pre_promise_competition_key = SupplyDemandState.KEY.pre_promise_competition

jeonse_price_download_link_key = SupplyDemandState.KEY.jeonse_price_download_link
sale_price_download_link_key = SupplyDemandState.KEY.sale_price_download_link
use_kor_rate_download_link_key = SupplyDemandState.KEY.use_kor_rate_download_link
home_mortgage_download_link_key = SupplyDemandState.KEY.home_mortgage_download_link
one_people_gdp_grdp_download_link_key = (
    SupplyDemandState.KEY.one_people_gdp_grdp_download_link
)

housing_sales_volume_download_link_key = (
    SupplyDemandState.KEY.housing_sales_volume_download_link
)
planning_move_download_link_key = SupplyDemandState.KEY.planning_move_download_link
pre_promise_competition_download_link_key = (
    SupplyDemandState.KEY.pre_promise_competition_download_link
)


llm = LLMProfile.analysis_llm()
tool_list = [think_tool]
llm_with_tools = llm.bind_tools(tool_list)
tool_node = ToolNode(tool_list)

from perplexity import Perplexity

search_client = Perplexity()

from tools.kostat_api import get_10_year_after_house


# 10년 이상 노후도
def year10_after_house(state: SupplyDemandState) -> SupplyDemandState:
    start_input = state[start_input_key]
    target_area = start_input[target_area_key]
    # 10년 이상 노후도
    # get_10_year_after_house("서울특별시 강동구 상일로6길 26")
    # 응답: '2048'
    year10_house_cnt = get_10_year_after_house(target_area)[0]["house_cnt"]
    return {year10_after_house_key: year10_house_cnt}


def supply_housing(state: SupplyDemandState) -> SupplyDemandState:

    return {}


# 청약 경쟁률
from tools.pre_promise_competition_tool_v2 import pre_promise


async def pre_promise_competition(state: SupplyDemandState) -> SupplyDemandState:
    start_input = state[start_input_key]
    target_area = start_input[target_area_key]
    result = await pre_promise(target_area)

    return {
        pre_promise_competition_key: result,
        pre_promise_competition_download_link_key: pre_promise_competition_to_csv(
            result, target_area
        ),
    }


from tools.rag.retriever.sale_price_retriever import sale_price_retrieve
from tools.rag.retriever.jeonse_price_retriever import jeonse_price_retrieve


# 매매가/전세가
def sale_and_jeonse_price_ratio(state: SupplyDemandState) -> SupplyDemandState:
    start_input = state[start_input_key]
    target_area = start_input[target_area_key]

    # 자치구: 강남구, 단위 천원
    # 2020년 1월: 769973.0
    # 2020년 2월: 772140.0
    # 2020년 3월: 774435.0
    # 2020년 4월: 776656.0
    sale_price = sale_price_retrieve(target_area)
    jeonse_price = jeonse_price_retrieve(target_area)
    return {
        jeonse_price_key: jeonse_price,
        sale_price_key: sale_price,
        jeonse_price_download_link_key: jense_to_drive(jeonse_price),
        sale_price_download_link_key: sales_to_drive(sale_price),
    }


from tools.Trade_Balance_tool import get_trade_balance


# 매매수급지수
def trade_balance(state: SupplyDemandState) -> SupplyDemandState:
    # 서울>강북지역
    # 서울>강남지역
    # 서울>강북지역>도심권
    # 서울>강남지역>서남권
    # 서울>강남지역>동남권
    # 서울>강북지역>동북권
    # 서울>강북지역>서북권

    start_input = state[start_input_key]
    target_area = start_input[target_area_key]
    seoul_balance = get_trade_balance("서울")

    llm_result = LLMProfile.chat_bot_llm().invoke(
        f"""
        {seoul_balance}\n\n
        
        [질문]
        위에서 말하는 강북 및 강남은 실제 자치구가 아니라 
        대한민국 서울 한강 중심에서 계산되는 위치를 말합니다. 
        그러니 위 내용중에 {target_area} 에 맞는 지역을 선택해주세요. 
        
        [강력 지침]
        - 불필요한 말을 하지마십시오
        - 위의 내용 중 {target_area}에 해당되는 내용만 추출해서 말씀하십시오          
        """
    )

    return {trade_balance_key: llm_result.content}


from tools.rag.retriever.planning_move_retriever import planning_move_retrieve


# 입주 예정 물량
def planning_move(state: SupplyDemandState) -> SupplyDemandState:
    # '입주예정월: 202601\n지역: 서울\n사업유형: 임대\n주소: 서울특별시 강북구 수유동 47-52\n주택명: 수유동47-52(청년안심주택)\n세대수: 426',
    start_input = state[start_input_key]
    target_area = start_input[target_area_key]
    docs = planning_move_retrieve(target_area)
    return {
        planning_move_key: docs,
        planning_move_download_link_key: planning_move_to_csv(docs, target_area),
    }


from tools.rag.retriever.housing_sales_volume_retriever import (
    housing_sales_volume_retrieve,
)


# 매매 거래량
def housing_sales_volume(state: SupplyDemandState) -> SupplyDemandState:
    start_input = state[start_input_key]
    target_area = start_input[target_area_key]
    volumes = housing_sales_volume_retrieve(target_area)

    return {
        housing_sales_volume_key: volumes,
        housing_sales_volume_download_link_key: housing_sales_volume_to_drive(
            volumes, target_area
        ),
    }


from tools.kor_usa_rate import get_rate


# 금리
def use_kor_rate(state: SupplyDemandState) -> SupplyDemandState:
    # {'date': '2025-09', 'kr_rate': 2.5, 'us_rate': 4.22}
    jsons = json.loads(get_rate())
    return {
        use_kor_rate_key: jsons["data"],
        use_kor_rate_download_link_key: rate_to_drive(jsons["data"]),
    }


from tools.rag.retriever.home_mortgage_retriever import home_mortgage_retrieve


# 주택담보금리
def get_home_mortgage(state: SupplyDemandState) -> SupplyDemandState:
    # ' 2025-08-01\n대출평균(연%): 4.06\n가계대출(연%): 4.17\n주택담보대출(연%): 3.96',
    docs = home_mortgage_retrieve()
    return {
        home_mortgage_key: home_mortgage_retrieve(),
        home_mortgage_download_link_key: home_mortagage_to_drive(docs),
    }


from tools.kostat_api import get_one_people_gdp
from tools.rag.retriever.one_people_grdp_retriever import one_people_grdp_retrieve


# gdp 혹은 grdp
def get_gdp_and_grdp(state: SupplyDemandState) -> SupplyDemandState:
    start_input = state[start_input_key]
    target_area = start_input[target_area_key]
    # '2018': 36791700,
    # '2019': 37006320,
    # get_one_people_gdp()

    # 강남구\n2018_당해년가격: 78135292000000...
    # one_people_grdp_retrieve(target_area)
    gdp = get_one_people_gdp()
    grdp = one_people_grdp_retrieve(target_area)
    return {
        one_people_gdp_key: gdp,
        one_people_grdp_key: grdp,
        one_people_gdp_grdp_download_link_key: gdp_and_grdp_to_drive(
            get_one_people_gdp(), one_people_grdp_retrieve(target_area), target_area
        ),
    }


def analysis_setting(state: SupplyDemandState) -> SupplyDemandState:
    start_input = state[start_input_key]
    target_area = start_input[target_area_key]

    year10_after_house = state[year10_after_house_key]
    jeonse_price = state[jeonse_price_key]
    sale_price = state[sale_price_key]
    trade_balance = state[trade_balance_key]
    use_kor_rate = state[use_kor_rate_key]
    home_mortgage = state[home_mortgage_key]
    one_people_gdp = state[one_people_gdp_key]
    one_people_grdp = state[one_people_grdp_key]
    housing_sales_volume = state[housing_sales_volume_key]
    planning_move = state[planning_move_key]
    pre_promise_competition = state[pre_promise_competition_key]

    system_prompt = PromptManager(PromptType.SUPPLY_DEMAND_SYSTEM).get_prompt()
    humun_prompt = PromptManager(PromptType.SUPPLY_DEMAND_HUMAN).get_prompt(
        target_area=target_area,
        date=get_today_str(),
        year10_after_house=year10_after_house,
        jeonse_price=jeonse_price,
        sale_price=sale_price,
        trade_balance=trade_balance,
        use_kor_rate=use_kor_rate,
        home_mortgage=home_mortgage,
        one_people_gdp=one_people_gdp,
        one_people_grdp=one_people_grdp,
        housing_sales_volume=housing_sales_volume,
        planning_move=planning_move,
        pre_promise_competition=pre_promise_competition,        
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=humun_prompt),
    ]
    return {messages_key: messages}


def agent(state: SupplyDemandState) -> SupplyDemandState:
    messages = state.get(messages_key, [])
    response = llm_with_tools.invoke(messages)
    new_messages = messages + [response]
    new_state = {**state, messages_key: new_messages}
    new_state[output_key] = {
        "result": response.content,
        year10_after_house_key: state[year10_after_house_key],
        jeonse_price_key: state[jeonse_price_key],
        sale_price_key: state[sale_price_key],
        trade_balance_key: state[trade_balance_key],
        use_kor_rate_key: state[use_kor_rate_key],
        home_mortgage_key: state[home_mortgage_key],
        one_people_gdp_key: state[one_people_gdp_key],
        one_people_grdp_key: state[one_people_grdp_key],
        housing_sales_volume_key: state[housing_sales_volume_key],
        planning_move_key: state[planning_move_key],        
        pre_promise_competition_key: state[pre_promise_competition_key],
        
        jeonse_price_download_link_key: state[jeonse_price_download_link_key],
        sale_price_download_link_key: state[sale_price_download_link_key],
        use_kor_rate_download_link_key: state[use_kor_rate_download_link_key],
        home_mortgage_download_link_key: state[home_mortgage_download_link_key],
        one_people_gdp_grdp_download_link_key: state[one_people_gdp_grdp_download_link_key],
        housing_sales_volume_download_link_key: state[housing_sales_volume_download_link_key],
        planning_move_download_link_key: state[planning_move_download_link_key],
        pre_promise_competition_download_link_key: state[pre_promise_competition_download_link_key],        
    }
    return new_state


def router(state: SupplyDemandState):
    messages = state[messages_key]
    last_ai_message = messages[-1]
    if last_ai_message.tool_calls:
        return "tools"
    return "__end__"


pre_promise_competition_key = "pre_promise_competition"

year10_after_house_key = "year10_after_house"
sale_and_jeonse_price_ratio_key = "sale_and_jeonse_price_ratio"
trade_balance_key = "trade_balance"

planning_move_key = "planning_move"
housing_sales_volume_key = "housing_sales_volume"
use_kor_rate_key = "use_kor_rate"

get_home_mortgage_key = "get_home_mortgage"
get_gdp_and_grdp_key = "get_gdp_and_grdp"

analysis_setting_key = "analysis_setting"


tools_key = "tools"
agent_key = "agent"
graph_builder = StateGraph(SupplyDemandState)

graph_builder.add_node(pre_promise_competition_key, pre_promise_competition)
graph_builder.add_node(year10_after_house_key, year10_after_house)
graph_builder.add_node(sale_and_jeonse_price_ratio_key, sale_and_jeonse_price_ratio)
graph_builder.add_node(trade_balance_key, trade_balance)
graph_builder.add_node(planning_move_key, planning_move)
graph_builder.add_node(housing_sales_volume_key, housing_sales_volume)
graph_builder.add_node(use_kor_rate_key, use_kor_rate)
graph_builder.add_node(get_home_mortgage_key, get_home_mortgage)
graph_builder.add_node(get_gdp_and_grdp_key, get_gdp_and_grdp)

graph_builder.add_node(analysis_setting_key, analysis_setting)
graph_builder.add_node(tools_key, tool_node)
graph_builder.add_node(agent_key, agent)

graph_builder.add_edge(START, pre_promise_competition_key)
graph_builder.add_edge(START, year10_after_house_key)
graph_builder.add_edge(START, sale_and_jeonse_price_ratio_key)
graph_builder.add_edge(START, trade_balance_key)
graph_builder.add_edge(START, planning_move_key)
graph_builder.add_edge(START, housing_sales_volume_key)
graph_builder.add_edge(START, use_kor_rate_key)
graph_builder.add_edge(START, get_home_mortgage_key)
graph_builder.add_edge(START, get_gdp_and_grdp_key)

graph_builder.add_edge(pre_promise_competition_key, analysis_setting_key)
graph_builder.add_edge(year10_after_house_key, analysis_setting_key)
graph_builder.add_edge(sale_and_jeonse_price_ratio_key, analysis_setting_key)
graph_builder.add_edge(trade_balance_key, analysis_setting_key)
graph_builder.add_edge(planning_move_key, analysis_setting_key)
graph_builder.add_edge(housing_sales_volume_key, analysis_setting_key)
graph_builder.add_edge(use_kor_rate_key, analysis_setting_key)
graph_builder.add_edge(get_home_mortgage_key, analysis_setting_key)
graph_builder.add_edge(get_gdp_and_grdp_key, analysis_setting_key)

graph_builder.add_edge(analysis_setting_key, agent_key)

graph_builder.add_conditional_edges(agent_key, router, [tools_key, END])
graph_builder.add_edge(tools_key, agent_key)

supply_demand_graph = graph_builder.compile()
