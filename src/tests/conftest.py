# src/tests/conftest.py
"""
전체 테스트 모듈 공유 fixture

e2e_result fixture를 세션 스코프로 한 번만 서버를 호출하고,
analysis / final_report / source 등 E2E 연동 테스트에서 공유합니다.

[중요] autouse=False — judge/extraction/renderer 등 정적 데이터셋만
사용하는 모듈은 서버 호출 없이 독립 실행 가능합니다.
"""

import json
import pytest
from tests.e2e_client import E2EClient


@pytest.fixture(scope="session")
def e2e_result():
    """
    E2E 서버 파이프라인을 세션당 1회 호출하고 결과를 캐싱합니다.

    사용 모듈: analysis_eval, report_eval, source_eval
    미사용 모듈: judge_eval, extraction_eval, renderer_eval (정적 데이터셋)

    반환값 구조:
        {
            "start_input": {...},
            "analysis_outputs": {...},  # 7개 에이전트 분석 결과
            "final_report": str,         # 최종 보고서
            "source": str,               # 출처 추출
            "status": str,
            "messages": list,
        }
    """
    client = E2EClient()
    start_input = {
        "target_area": "서울특별시 강남구 대치동",
        "main_type": "84㎡",
        "email": "immortal0900@gmail.com",
        "total_units": "500",
    }

    print("\n[E2E] 파이프라인 서버 호출 시작...")
    # 최대 40분 대기 (서버 파이프라인 완주에 약 30분 소요)
    result_dict = client.run_pipeline(start_input=start_input, timeout=2400)
    print("[E2E] 파이프라인 리턴 완료. 결과 객체를 캐싱합니다.")

    # 결과 객체를 JSON 파일로 저장 (디버깅/재활용 용도)
    with open("e2e_result.json", "w", encoding="utf-8") as f:
        json.dump(result_dict, f, ensure_ascii=False, indent=4)

    return result_dict
