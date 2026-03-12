# agents/state/structured_schemas.py
"""
Gemini / Perplexity Structured Output 전용 Pydantic 스키마 모음.

각 API 호출의 '출력 형태(Shape)'만 이 파일에서 관리합니다.
프롬프트의 동적 변수(target_area, total_units 등)는 입력(Input)이므로
스키마와 완전히 분리됩니다.

관련 공식 문서:
  - Gemini: https://ai.google.dev/gemini-api/docs/structured-output
  - Perplexity: https://docs.perplexity.ai/guides/structured-outputs
"""

from pydantic import BaseModel, Field
from typing import List


# ---------------------------------------------------------------------------
# 1. NearbyMarket (주변 시세) – Gemini 출력 스키마
#    파일: nearby_market_agent.py > gemini_search_tool()
# ---------------------------------------------------------------------------

class SaleApartment(BaseModel):
    """
    매매아파트 1개의 시세·입지 정보.
    없으면 Gemini가 해당 없음을 나타내는 빈 문자열을 사용합니다.
    """

    주소와단지명: str = Field(description="공식 행정구역명이 포함된 단지 전체 주소와 단지명")
    세대수: str = Field(description="총 세대 수 (예: '584세대')")
    타입: str = Field(description="전용면적 타입 (예: '84m²')")
    평당매매가격: str = Field(description="3.3㎡(평)당 매매가격 (예: '4,200만원')")
    준공연도: str = Field(description="입주 또는 준공 연도 (예: '2019년')")
    사업지와의거리: str = Field(description="사업지 기준 직선 또는 도보 거리 (예: '약 350m')")
    주변호재: str = Field(description="입지 강점 또는 주요 개발 호재 요약")


class NewApartment(BaseModel):
    """
    분양아파트 1개의 분양 조건·시세 정보.
    """

    주소와단지명: str = Field(description="공식 행정구역명이 포함된 단지 전체 주소와 단지명")
    세대수: str = Field(description="총 세대 수 (예: '320세대')")
    타입: str = Field(description="전용면적 타입 (예: '84m²')")
    평당분양가격: str = Field(description="3.3㎡(평)당 분양가격 (예: '3,800만원')")
    청약경쟁률: str = Field(description="1순위 청약 경쟁률 (예: '12.5:1')")
    청약일시: str = Field(description="1순위 청약 접수일 (예: '2024년 03월 15일')")
    계약조건: str = Field(description="계약금·중도금·잔금 비율 등 계약 조건 요약")
    사업지와의거리: str = Field(description="사업지 기준 직선 또는 도보 거리 (예: '약 500m')")
    주변호재: str = Field(description="입지 강점 또는 주요 개발 호재 요약")


class NearbyMarketGeminiSchema(BaseModel):
    """
    nearby_market_agent.py > gemini_search_tool() 의 최종 출력 스키마.

    [존재 이유]
    이 스키마 없이는 Gemini가 자유 형식 텍스트를 반환하고,
    하류 노드(kakao_api_distance_tool, get_real_estate_price_tool 등)에서
    매번 extract_json_from_text() + json.loads()로 불안정하게 파싱해야 합니다.
    스키마를 강제하면 파싱 실패 가능성이 API 레벨에서 0이 됩니다.
    """

    매매아파트: List[SaleApartment] = Field(
        description="사업지와 규모·타입이 유사하고 최단거리에 있는 매매아파트 3개"
    )
    분양아파트: List[NewApartment] = Field(
        description="사업지와 규모·타입이 유사하고 최단거리에 있는 분양아파트 3개"
    )


# ---------------------------------------------------------------------------
# 2. LocationInsight (입지 분석) – Gemini 출력 스키마
#    파일: location_insight_agent.py > gemini_search_tool()
# ---------------------------------------------------------------------------

class LocationAdvantage(BaseModel):
    """
    입지 호재 1건의 정보.
    """

    name: str = Field(description="호재 사업명 또는 시설명 (예: '수도권 광역급행철도 GTX-A')")
    location: str = Field(description="위치 또는 노선 정보 (예: '성남역 정차')")
    description: str = Field(description="호재의 내용 및 사업지에 미치는 영향 요약")
    status: str = Field(description="현재 진행 상태 (예: '2025년 개통 예정')")


class LocationInsightGeminiSchema(BaseModel):
    """
    location_insight_agent.py > gemini_search_tool() 의 최종 출력 스키마.

    [존재 이유]
    입지 분석에서 Gemini가 주변호재를 JSON 리스트로 반환해야 하는데,
    스키마 없이는 자유 형식 텍스트(마크다운, 설명 포함)가 반환될 위험이 있습니다.
    """

    해당지역특징: List[str] = Field(
        description="해당 지역 부동산 시장의 구매 성향·패턴 등 특징 요약 리스트"
    )
    주변호재: List[LocationAdvantage] = Field(
        description="사업지 주변의 부동산 호재 목록 (GTX, 재개발, 상업시설 등)"
    )


# ---------------------------------------------------------------------------
# 3. NearbyMarket (주변 시세) – Perplexity 검증 출력 스키마
#    파일: nearby_market_agent.py > perplexity_search_tool()
# ---------------------------------------------------------------------------

class VerifiedNewApartment(BaseModel):
    """
    Perplexity로 검증된 분양아파트 1개의 정보.
    """

    주소와단지명: str = Field(description="공식 행정구역명이 포함된 단지 전체 주소와 단지명")
    평당분양가격: str = Field(description="Perplexity 검색으로 최신 확인된 평당 분양가격")
    계약조건: str = Field(description="계약금·중도금·잔금 비율 등 계약 조건")
    청약경쟁률: str = Field(description="1순위 청약 경쟁률")
    청약일시: str = Field(description="청약 접수일")
    비고: str = Field(description="추가 특이사항 또는 '검증 불가' 표시")


class NearbyMarketPerplexitySchema(BaseModel):
    """
    nearby_market_agent.py > perplexity_search_tool() 의 최종 출력 스키마.

    [존재 이유]
    Perplexity가 반환하는 분양아파트 검증 결과가 마크다운·출처 텍스트와
    혼재될 수 있습니다. 스키마로 강제하면 하류 노드가 바로 dict를 소비할 수 있습니다.
    """

    분양아파트: List[VerifiedNewApartment] = Field(
        description="Perplexity로 검색·검증된 분양아파트 정보 목록"
    )

# ---------------------------------------------------------------------------
# 4. SupplyDemand (공급과 수요) – 청약경쟁률 출력 스키마
#    파일: pre_promise_competition_tool_v2.py > pre_promise()
# ---------------------------------------------------------------------------

class CompetitionItem(BaseModel):
    주소: str = Field(description="아파트 단지 공식 주소")
    공고일: str = Field(description="청약 공고일 (예: '2025-10-02')")
    경쟁률: str = Field(description="청약 경쟁률 (예: '447.90:1'). 항상 ':1' 형식을 준수하세요.")

class PrePromiseCompetitionResult(BaseModel):
    results: List[CompetitionItem] = Field(
        description="검색된 청약 경쟁률 정보 목록. 제공된 청약 내용이 없으면 빈 배열([])을 반환합니다."
    )


# ---------------------------------------------------------------------------
# 5. HousingRule (주택공급규칙) – 주택공급규칙 요약 스키마
#    파일: context_to_csv.py > housing_rule_context_to_drive()
# ---------------------------------------------------------------------------

class HousingRuleItem(BaseModel):
    조문명: str = Field(description="조문명 (예: '제35조(국민주택의 특별공급)')")
    핵심요약: str = Field(description="핵심 내용 1~2줄 요약")
    주요조건: List[str] = Field(description="핵심 조건들을 bullet 형태 리스트 항목으로 분리")
    적용대상: str = Field(default="", description="조문이 다루는 대상 (있다면)")
    비고: str = Field(default="", description="부가 설명 또는 특이사항 (있다면)")

class HousingRuleList(BaseModel):
    rules: List[HousingRuleItem] = Field(description="주택공급규칙 조문별 요약 결과 목록")


# ---------------------------------------------------------------------------
# 6. MovePopulationQuery (인구이동) – TextToSQL 출력 스키마
#    파일: kostat_api.py > get_move_population()
# ---------------------------------------------------------------------------

class MovePopulationQuery(BaseModel):
    """
    get_move_population()에서 LLM이 생성하는 SQL 쿼리의 출력 스키마.

    [존재 이유]
    이 스키마 없이는 LLM이 SELECT *, 한글 alias(AS "전출지") 등
    예측 불가능한 SQL을 생성하여 하류 move_population_to_drive()에서
    KeyError("['origin', 'destination', 'total'] not in index")가 발생합니다.
    StructuredOutput으로 강제하면 LLM이 sql 필드에 순수 SQL만 반환합니다.
    """

    sql: str = Field(
        description=(
            "SELECT year, origin, destination, total FROM age_population WHERE ... "
            "형태의 PostgreSQL 쿼리. "
            "반드시 year, origin, destination, total 4개 컬럼만 SELECT하세요. "
            "id 컬럼과 컬럼 alias(AS)는 사용하지 마세요."
        )
    )

