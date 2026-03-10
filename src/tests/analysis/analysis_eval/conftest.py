# src/tests/analysis/analysis_eval/conftest.py
"""
분석 에이전트 평가 테스트 — pytest fixture 및 데이터 로더

세션 스코프로 데이터셋을 한 번만 로드하고,
테스트 종료 시 종합 리포트를 출력합니다.
"""

import json
import os

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
# 전역 결과 저장소
# ============================================================
# 테스트 전체에서 결과를 누적합니다.
GLOBAL_RESULTS = []

# e2e_result fixture는 src/tests/conftest.py에 정의되어 있습니다.
# pytest가 상위 디렉토리의 conftest.py를 자동 탐색하므로
# analysis/source/final_report 테스트에서 공유됩니다.
