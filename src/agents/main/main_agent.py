from dotenv import load_dotenv

load_dotenv()

from tools.send_gmail import gmail_authenticate, send_gmail

from langgraph.graph.state import Command, Literal

from agents.state.start_state import StartInput
from agents.state.main_state import MainState
from agents.state.analysis_state import (
    HousingFaqState,
    LocationInsightState,
    PolicyState,
    PopulationInsightState,
    SupplyDemandState,
    UnsoldInsightState,
    NearbyMarketState,
)
from utils.llm import LLMProfile
from langgraph.graph import StateGraph, START, END
from prompts import PromptManager, PromptType
from agents.analysis.analysis_graph import analysis_graph
from agents.jung_min_jae.jung_min_jae_agent import report_graph
from copy import deepcopy


housing_faq_key = "housing_faq"
location_insight_key = "location_insight"
policy_output_key = "policy_output"
supply_demand_key = "supply_demand"
unsold_insight_key = "unsold_insight"
population_insight_key = "population_insight"
nearby_market_key = "nearby_market"

housing_faq_context_key = HousingFaqState.KEY.housing_faq_context
housing_faq_download_link_key = HousingFaqState.KEY.housing_faq_download_link
housing_rule_context_key = HousingFaqState.KEY.housing_rule_context
housing_rule_download_link_key = HousingFaqState.KEY.housing_rule_download_link

location_kakao_api_distance_context_key = (
    LocationInsightState.KEY.kakao_api_distance_context
)
location_kakao_api_distance_download_link_key = (
    LocationInsightState.KEY.kakao_api_distance_download_link
)

nearby_kakao_api_distance_context_key = NearbyMarketState.KEY.kakao_api_distance_context
nearby_kakao_api_distance_download_link_key = (
    NearbyMarketState.KEY.kakao_api_distance_download_link
)

national_context_key = PolicyState.KEY.national_context
national_download_link_key = PolicyState.KEY.national_download_link
region_context_key = PolicyState.KEY.region_context
region_download_link_key = PolicyState.KEY.region_download_link

unsold_unit_key = UnsoldInsightState.KEY.unsold_unit
unsold_unit_download_link_key = UnsoldInsightState.KEY.unsold_unit_download_link

move_population_context_key = PopulationInsightState.KEY.move_population_context
move_population_download_link_key = (
    PopulationInsightState.KEY.move_population_download_link
)
age_population_context_key = PopulationInsightState.KEY.age_population_context
age_population_download_link_key = (
    PopulationInsightState.KEY.age_population_download_link
)

home_mortgage_key = SupplyDemandState.KEY.home_mortgage
home_mortgage_download_link_key = SupplyDemandState.KEY.home_mortgage_download_link
use_kor_rate_key = SupplyDemandState.KEY.use_kor_rate
use_kor_rate_download_link_key = SupplyDemandState.KEY.use_kor_rate_download_link
one_people_gdp_key = SupplyDemandState.KEY.one_people_gdp
one_people_grdp_key = SupplyDemandState.KEY.one_people_grdp
one_people_gdp_grdp_download_link_key = (
    SupplyDemandState.KEY.one_people_gdp_grdp_download_link
)
planning_move_key = SupplyDemandState.KEY.planning_move
planning_move_download_link_key = SupplyDemandState.KEY.planning_move_download_link
housing_sales_volume_key = SupplyDemandState.KEY.housing_sales_volume
housing_sales_volume_download_link_key = (
    SupplyDemandState.KEY.housing_sales_volume_download_link
)
jeonse_price_key = SupplyDemandState.KEY.jeonse_price
jeonse_price_download_link_key = SupplyDemandState.KEY.jeonse_price_download_link
pre_promise_competition_key = SupplyDemandState.KEY.pre_promise_competition
pre_promise_competition_download_link_key = (
    SupplyDemandState.KEY.pre_promise_competition_download_link
)
sale_price_key = SupplyDemandState.KEY.sale_price
sale_price_download_link_key = SupplyDemandState.KEY.sale_price_download_link

year10_after_house_key = SupplyDemandState.KEY.year10_after_house
trade_balance_key = SupplyDemandState.KEY.trade_balance

start_llm = LLMProfile.chat_bot_llm()
messages_key = MainState.KEY.messages
start_input_key = MainState.KEY.start_input
email_key = StartInput.KEY.email
analysis_outputs_key = MainState.KEY.analysis_outputs
final_report_key = MainState.KEY.final_report
status_key = MainState.KEY.status


def start(state: MainState) -> MainState:
    return {**state, status_key: "ANALYSIS"}


async def analysis_graph_node(state: MainState) -> MainState:

    result = await analysis_graph.ainvoke(
        {"start_input": deepcopy(state[start_input_key])}
    )
    return {
        "analysis_outputs": result.get("analysis_outputs", {}),
        status_key: "JUNG_MIN_JAE",
    }


def jung_min_jae_graph(state: MainState) -> MainState:

    result = report_graph.invoke(
        {
            "start_input": deepcopy(state[start_input_key]),
            "analysis_outputs": deepcopy(state[analysis_outputs_key]),
            "segment": 1,
        }
    )

    return {"final_report": result["final_report"], status_key: "RENDERING"}


def _build_source_prompt(analysis_outputs: dict) -> str:
    """분석 결과에서 출처 페이지 프롬프트를 생성합니다."""
    housing_faq = analysis_outputs[housing_faq_key]
    location_insight = analysis_outputs[location_insight_key]
    policy_output = analysis_outputs[policy_output_key]
    supply_demand = analysis_outputs[supply_demand_key]
    unsold_insight = analysis_outputs[unsold_insight_key]
    population_insight = analysis_outputs[population_insight_key]
    nearby_market = analysis_outputs[nearby_market_key]

    return PromptManager(PromptType.MAIN_SOUCE_PAGE).get_prompt(
        # 청약 정리
        housing_faq_context=housing_faq[housing_faq_context_key],
        housing_faq_download_link=housing_faq[housing_faq_download_link_key],
        housing_rule_context=housing_faq[housing_rule_context_key],
        housing_rule_download_link=housing_faq[housing_rule_download_link_key],
        # 입지분석
        location_context=location_insight[location_kakao_api_distance_context_key],
        location_download_link=location_insight[
            location_kakao_api_distance_download_link_key
        ],
        # 매매가 비교
        nearby_context=nearby_market[nearby_kakao_api_distance_context_key],
        nearby_download_link=nearby_market[nearby_kakao_api_distance_download_link_key],
        # 정책
        national_news_context=policy_output[national_context_key],
        national_download_link=policy_output[national_download_link_key],
        region_context=policy_output[region_context_key],
        region_download_link=policy_output[region_download_link_key],
        # 미분양
        unsold_unit=unsold_insight[unsold_unit_key],
        unsold_unit_download_link=unsold_insight[unsold_unit_download_link_key],
        # 인구분석
        move_population_context=population_insight[move_population_context_key],
        move_population_download_link=population_insight[
            move_population_download_link_key
        ],
        age_population_context=population_insight[age_population_context_key],
        age_population_download_link=population_insight[
            age_population_download_link_key
        ],
        # 공급과 수요
        home_mortgage=supply_demand[home_mortgage_key],
        home_mortgage_download_link=supply_demand[home_mortgage_download_link_key],
        use_kor_rate=supply_demand[use_kor_rate_key],
        use_kor_rate_download_link=supply_demand[use_kor_rate_download_link_key],
        one_people_gdp=supply_demand[one_people_gdp_key],
        one_people_grdp=supply_demand[one_people_grdp_key],
        one_people_gdp_grdp_download_link=supply_demand[
            one_people_gdp_grdp_download_link_key
        ],
        planning_move=supply_demand[planning_move_key],
        planning_move_download_link=supply_demand[planning_move_download_link_key],
        housing_sales_volume=supply_demand[housing_sales_volume_key],
        housing_sales_volume_download_link=supply_demand[
            housing_sales_volume_download_link_key
        ],
        jeonse_price=supply_demand[jeonse_price_key],
        jeonse_price_download_link=supply_demand[jeonse_price_download_link_key],
        pre_promise_competition=supply_demand[pre_promise_competition_key],
        pre_promise_competition_download_link=supply_demand[
            pre_promise_competition_download_link_key
        ],
        sale_price=supply_demand[sale_price_key],
        sale_price_download_link=supply_demand[sale_price_download_link_key],
        year10_after_house=supply_demand[year10_after_house_key],
        trade_balance=supply_demand[trade_balance_key],
    )


def _build_drive_links(analysis_outputs: dict) -> dict[str, str]:
    """분석 결과에서 Google Drive 다운로드 링크 딕셔너리를 생성합니다."""
    housing_faq = analysis_outputs[housing_faq_key]
    location_insight = analysis_outputs[location_insight_key]
    policy_output = analysis_outputs[policy_output_key]
    supply_demand = analysis_outputs[supply_demand_key]
    unsold_insight = analysis_outputs[unsold_insight_key]
    population_insight = analysis_outputs[population_insight_key]
    nearby_market = analysis_outputs[nearby_market_key]

    return {
        "주택청약 FAQ": housing_faq[housing_faq_download_link_key],
        "주택공급 규칙": housing_faq[housing_rule_download_link_key],
        "입지분석 (카카오 API 거리데이터)": location_insight[
            location_kakao_api_distance_download_link_key
        ],
        "주변 단지 매매가 비교": nearby_market[
            nearby_kakao_api_distance_download_link_key
        ],
        "국가 정책 뉴스": policy_output[national_download_link_key],
        "지역 정책 뉴스": policy_output[region_download_link_key],
        "미분양 통계": unsold_insight[unsold_unit_download_link_key],
        "인구 이동 통계": population_insight[move_population_download_link_key],
        "연령별 인구 분포": population_insight[age_population_download_link_key],
        "주택담보대출 금리": supply_demand[home_mortgage_download_link_key],
        "한국 및 미국 금리 비교": supply_demand[use_kor_rate_download_link_key],
        "1인당 GDP & GRDP": supply_demand[one_people_gdp_grdp_download_link_key],
        "입주 예정 단지": supply_demand[planning_move_download_link_key],
        "매매거래량 통계": supply_demand[housing_sales_volume_download_link_key],
        "전세가격 통계": supply_demand[jeonse_price_download_link_key],
        "매매가격 통계": supply_demand[sale_price_download_link_key],
        "청약 경쟁률": supply_demand[pre_promise_competition_download_link_key],
    }


def final_node(state: MainState) -> MainState:
    """출처 페이지 생성 및 이메일 발송을 수행하는 최종 노드."""
    analysis_outputs = state[analysis_outputs_key]

    # 1) 출처 페이지 프롬프트 생성 및 LLM 호출
    prompt = _build_source_prompt(analysis_outputs)
    res = LLMProfile.dev_llm().invoke(prompt)

    # 2) 이메일 발송
    email = state[start_input_key][email_key]
    start_input = state[start_input_key]
    title = f"{start_input['target_area']} {start_input['main_type']} {start_input['total_units']} 사업보고서 작성"

    gmail_authenticate()
    send_gmail(
        to=email,
        title=title,
        md_content_final=state[final_report_key],
        md_content_source=res.content,
        drive_links=_build_drive_links(analysis_outputs),
    )

    return {"source": res.content, status_key: "DONE"}


graph_builder = StateGraph(MainState)

start_key = "start"
analysis_graph_key = "analysis_graph"
jung_min_jae_key = "jung_min_jae_graph"
final_key = "final"

graph_builder.add_node(start_key, start)
graph_builder.add_node(analysis_graph_key, analysis_graph_node)
graph_builder.add_node(jung_min_jae_key, jung_min_jae_graph)
graph_builder.add_node(final_key, final_node)

graph_builder.add_edge(START, start_key)
graph_builder.add_edge(start_key, analysis_graph_key)
graph_builder.add_edge(analysis_graph_key, jung_min_jae_key)
graph_builder.add_edge(jung_min_jae_key, final_key)
graph_builder.add_edge(final_key, END)
