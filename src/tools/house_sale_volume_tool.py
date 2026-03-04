import requests
import pandas as pd


url = "https://kosis.kr/openapi/Param/statisticsParameterData.do"
params = {
    "method": "getList",
    "apiKey": "MzlmNWY2OTczMzRmYmQ5NDQwZTIyNWU5YTVhNWIwZWQ=",
    "itmId": "13103114441T1",  # 거래건수만
    "objL1": "ALL",  # 전체 지역
    "format": "json",
    "jsonVD": "Y",
    "prdSe": "M",
    "startPrdDe": "202401",
    "endPrdDe": "202509",
    "orgId": "408",
    "tblId": "DT_408_2006_S0057",
}
headers = {"User-Agent": "Mozilla/5.0"}

# 전역 데이터프레임 캐시
_trade_df = None

def _get_trade_df() -> pd.DataFrame:
    """KOSIS API를 호출하여 데이터프레임을 캐싱 및 반환 (지연 초기화)"""
    global _trade_df
    if _trade_df is not None:
        return _trade_df

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        _trade_df = pd.DataFrame(data)
        return _trade_df
    except Exception as e:
        print(f"[house_sale_volume_tool] Error fetching KOSIS data: {e}")
        # 실패 시 빈 데이터프레임 반환하여 크래시 방지
        return pd.DataFrame(columns=["C1_NM", "PRD_DE", "ITM_NM", "DT"])
# 주요 컬럼
# PRD_DE: 기간 (예: 202507)
# C1_NM: 지역명 (예: 종로구, 강남구)
# ITM_NM: 항목명 (동(호)수, 면적)
# DT: 데이터 값
# ## 주요컬럼럼
# 'C1_NM'
# 'PRD_DE' = '날짜'
# 'UNIT_NM'='동(호)수'='거래량'


def get_trade_volume(address):
    """주소에서 구 단위 거래량 조회"""
    # 데이터프레임 지연 로딩
    df = _get_trade_df()
    
    district = ""
    # 주소를 공백으로 나눠서 "구"로 끝나는 단어 찾기
    for word in address.split():
        if word.endswith("구"):
            district = word
            break

    if not district or df.empty:
        return pd.DataFrame()

    # 해당 구가 포함된 데이터 필터링 (contains 사용)
    result = (
        df[df["C1_NM"].str.contains(district, na=False)]
        .pivot_table(
            index="PRD_DE",  # 행을 날짜로로
            columns="ITM_NM",  # 열을 항목명(ITM_NM)
            values="DT",  # 값을 DT로(거래량, 면적 숫자)
            aggfunc="first",  # 값이 여러개면 첫번째만만
        )
        .reset_index()
    )

    # 구 이름 추가
    result.insert(
        1, "행정구역", district
    )  # 1번째 위치(두번째 컬럼) 'C1_NM'을 '행정구역으로로'
    result.columns.name = None

    return result.rename(
        columns={"PRD_DE": "날짜", "동(호)수": "거래량", "면적": "면적(천㎡)"}
    )


# 사용 예시
# address = "서울 송파구 마천동 299-23"
# print(get_trade_volume(address))

# address = "서울 송파구 마천동 299-23"


# print(get_trade_volume(address))
