# src/tests/analysis/analysis_eval/conftest.py
"""
분석 에이전트 평가 테스트 — pytest fixture 및 데이터 로더

세션 스코프로 데이터셋을 한 번만 로드하고,
테스트 종료 시 종합 리포트를 출력합니다.
"""

import json
import os
import pytest
from tests.e2e_client import E2EClient

# ============================================================
# 데이터셋 로더
# ============================================================
DATASETS_DIR = os.path.join(os.path.dirname(__file__), "datasets")

# 에이전트명 → 데이터셋 파일명 매핑
AGENT_DATASET_MAP = {
    "housing_faq": "housing_faq.json",
    "policy": "policy.json",
    "supply_demand": "supply_demand.json",
    "nearby_market": "nearby_market.json",
    "location_insight": "location_insight.json",
    "population_insight": "population_insight.json",
    "unsold_insight": "unsold_insight.json",
}


def load_dataset(agent_name: str) -> list[dict]:
    """
    에이전트별 테스트 데이터셋 JSON 파일을 로드합니다.

    Args:
        agent_name: 에이전트 식별자 (예: "housing_faq")

    Returns:
        테스트 케이스 딕셔너리 리스트

    Raises:
        FileNotFoundError: 데이터셋 파일이 없는 경우
    """
    filename = AGENT_DATASET_MAP.get(agent_name)
    if not filename:
        raise ValueError(f"알 수 없는 에이전트: {agent_name}")

    filepath = os.path.join(DATASETS_DIR, filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"데이터셋 파일 없음: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# 종합 리포트 fixture
# ============================================================
# 전역 결과 저장소 — 테스트 전체에서 결과를 누적합니다.
GLOBAL_RESULTS = []


@pytest.fixture(scope="session", autouse=True)
def print_summary_report(request):
    """세션 종료 시 종합 리포트를 출력합니다."""

    yield  # 모든 테스트 실행 후

    if not GLOBAL_RESULTS:
        return

    print("\n" + "=" * 70)
    print("  분석 에이전트 DeepEval 평가 종합 리포트")
    print("=" * 70)

    for result in GLOBAL_RESULTS:
        agent = result["agent"]
        print(f"\n--- {agent} ---")

        for type_result in result.get("results", []):
            q_type = type_result["type"]
            score = type_result["score"]
            count = type_result["count"]
            status = "PASS" if score >= 0.7 else "FAIL"
            print(f"  [{status}] {q_type}: {score:.2%} ({count}건)")

    print("\n" + "=" * 70)


# ============================================================
# E2E 서버 연동 fixture (세션 단위 1회 호출)
# ============================================================
@pytest.fixture(scope="session")
def e2e_result():
    """
    모든 분석 에이전트 평가 전에 딱 한 번 서버 파이프라인을 호출합니다.
    """
    client = E2EClient()
    # 임의의 기준 입력 (이 값을 기준으로 모든 테스트 문항 채점)
    start_input = {
        "target_area": "서울특별시 강남구 대치동",
        "main_type": "84㎡",
        "email": "test@example.com",
        "total_units": "500"
    }
    
    print("\n[E2E] 분석 에이전트 채점을 위한 파이프라인 서버 호출 시작...")
    # 최대 10분 대기
    result_dict = client.run_pipeline(start_input=start_input, timeout=600)
    print("[E2E] 파이프라인 리턴 완료. 결과 객체를 캐싱합니다.")
    
    return result_dict
