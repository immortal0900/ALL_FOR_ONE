import os
import requests
from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv()

KAKAO_BASE_URL = "https://dapi.kakao.com"
DEFAULT_RADIUS = 3000

"""
주소를 좌표로 변환하고 좌표를 기준으로 주변 입지를 검색하는 도구
"""


def _load_api_key():
    key = os.getenv("KAKAO_REST_API_KEY")
    if key:
        return key
    raise RuntimeError(
        "카카오 REST API 키가 없습니다. .env 파일에 KAKAO_REST_API_KEY를 추가해 주세요."
    )


def _call_kakao(path, params):
    headers = {"Authorization": f"KakaoAK {_load_api_key()}"}
    response = requests.get(
        f"{KAKAO_BASE_URL}{path}",
        headers=headers,
        params=params,
        timeout=10,
    )
    data = response.json()
    return data.get("documents") or []


def normalize_address(address: str) -> list[str]:
    """
    주소를 카카오 API가 인식할 수 있는 여러 형식으로 정규화합니다.
    
    Args:
        address: 정규화할 주소 문자열
        
    Returns:
        정규화된 주소 리스트 (여러 변형 포함)
    """
    if not address:
        return []
    
    normalized = []
    
    address_original = address.strip()
    normalized.append(address_original)
    
    address_lower = address_original.lower()
    
    replacements = {
        "서울시": "서울특별시",
        "서울": "서울특별시",
        "경기": "경기도",
        "경기도": "경기도",
        "부산시": "부산광역시",
        "부산": "부산광역시",
        "대구시": "대구광역시",
        "대구": "대구광역시",
        "인천시": "인천광역시",
        "인천": "인천광역시",
        "광주시": "광주광역시",
        "광주": "광주광역시",
        "대전시": "대전광역시",
        "대전": "대전광역시",
        "울산시": "울산광역시",
        "울산": "울산광역시",
        "세종시": "세종특별자치시",
        "세종": "세종특별자치시",
        "강원": "강원도",
        "강원도": "강원도",
        "충북": "충청북도",
        "충청북도": "충청북도",
        "충남": "충청남도",
        "충청남도": "충청남도",
        "전북": "전라북도",
        "전라북도": "전라북도",
        "전남": "전라남도",
        "전라남도": "전라남도",
        "경북": "경상북도",
        "경상북도": "경상북도",
        "경남": "경상남도",
        "경상남도": "경상남도",
        "제주": "제주특별자치도",
        "제주도": "제주특별자치도",
    }
    
    for old, new in replacements.items():
        if old in address_original:
            normalized_addr = address_original.replace(old, new)
            if normalized_addr not in normalized:
                normalized.append(normalized_addr)
    
    address_parts = address_original.split()
    if len(address_parts) > 1:
        partial_address = " ".join(address_parts[:3])
        if partial_address not in normalized:
            normalized.append(partial_address)
    
    if len(address_parts) > 2:
        partial_address2 = " ".join(address_parts[:2])
        if partial_address2 not in normalized:
            normalized.append(partial_address2)
    
    return normalized


def get_coordinates(address):
    """주소를 경도/위도로 변환."""
    documents = _call_kakao("/v2/local/search/address.json", {"query": address})
    if not documents:
        return None
    first = documents[0]
    return {"longitude": float(first["x"]), "latitude": float(first["y"])}


def get_coordinates_with_retry(address: str):
    """
    주소를 경도/위도로 변환합니다. 실패 시 여러 방법으로 재시도합니다.
    
    Args:
        address: 변환할 주소 문자열
        
    Returns:
        좌표 딕셔너리 또는 None
    """
    normalized_addresses = normalize_address(address)
    
    for normalized_addr in normalized_addresses:
        coords = get_coordinates(normalized_addr)
        if coords:
            return coords
    
    return None


def _build_place(place):
    return {
        "이름": place.get("place_name", ""),
        "주소": place.get("road_address_name") or place.get("address_name", ""),
        "거리(미터)": int(place.get("distance") or 0),
    }


def _format_places(documents):
    places = [_build_place(place) for place in documents]
    return sorted(places, key=lambda item: item["거리(미터)"])[:3]


def _search_category(coords, category_code, radius):
    params = {
        "category_group_code": category_code,
        "x": coords["longitude"],
        "y": coords["latitude"],
        "radius": radius,
        "size": 15,
    }
    return _format_places(_call_kakao("/v2/local/search/category.json", params))


def _search_keyword(coords, keyword, radius):
    params = {
        "query": keyword,
        "x": coords["longitude"],
        "y": coords["latitude"],
        "radius": radius,
        "size": 15,
    }
    return _format_places(_call_kakao("/v2/local/search/keyword.json", params))


def _get_school_info(coords, radius):
    return _search_category(coords, "SC4", radius)


def _get_academy_info(coords, radius):
    return _search_category(coords, "AC5", radius)


def _get_transport_info(coords, radius):
    return _search_category(coords, "SW8", radius)


def _get_convenience_info(coords, radius):
    mart = _search_category(coords, "MT1", radius)
    hospital = _search_category(coords, "HP8", radius)
    return {"대형마트": mart, "병원": hospital}


def _get_nature_info(coords, radius):
    return _search_keyword(coords, "공원", radius)


def _get_future_value_info(coords, radius):
    return _search_keyword(coords, "재건축", radius)


@tool
def get_location_profile(address, radius=DEFAULT_RADIUS):
    """주소를 좌표로 변환하고 주변 입지를 조사하고 해당 주소와 입지 사이의 거리를 검색하는 도구"""
    coords = get_coordinates_with_retry(address)
    if not coords:
        return {"주소": address, "좌표": None, "메시지": "좌표를 찾지 못했습니다."}
    return {
        "주소": address,
        "좌표": coords,
        "교육환경": {
            "학교": _get_school_info(coords, radius),
            "학원": _get_academy_info(coords, radius),
        },
        "교통여건": _get_transport_info(coords, radius),
        "편의여건": _get_convenience_info(coords, radius),
        "자연환경": _get_nature_info(coords, radius),
        "미래가치": _get_future_value_info(coords, radius),
    }


__all__ = ["get_location_profile"]


if __name__ == "__main__":
    sample_address = "서울시 강남구 도곡동 527 도곡렉슬"
    profile = get_location_profile.invoke({"address": sample_address})
    print(profile)

"""
[사용예시]

# 방법 1: 이 파일에서 직접 사용 (Tool 객체로 사용)
from src.tools.kakao_api_distance_tool import get_location_profile

result = get_location_profile.invoke({"address": "서울특별시 강남구 역삼동"})
print(result)

# 방법 2: 다른 파일에서 import해서 사용
from src.tools.kakao_api_distance_tool import get_location_profile

address = "서울시 강남구 도곡동 527"
radius = 5000
result = get_location_profile.invoke({"address": address, "radius": radius})
print(result)

# 방법 3: LangChain Agent에 Tool로 전달
from langchain_core.agents import AgentExecutor, create_tool_calling_agent
from langchain_openai import ChatOpenAI

tools = [get_location_profile]
llm = ChatOpenAI(model="gpt-4")
agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)

result = agent_executor.invoke({"input": "서울시 강남구 역삼동 주변 입지 정보를 알려줘"})

"""
