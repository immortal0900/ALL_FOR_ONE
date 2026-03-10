# src/tests/conftest.py
"""
전체 테스트 모듈 공유 fixture

e2e_result fixture를 세션 스코프로 한 번만 서버를 호출하고,
analysis / final_report / source 등 E2E 연동 테스트에서 공유합니다.

[중요] autouse=False — judge/extraction/renderer 등 정적 데이터셋만
사용하는 모듈은 서버 호출 없이 독립 실행 가능합니다.

[타임아웃 설정]
서버 파이프라인 정상 완주 시간은 38~55분입니다.
기본값 7200초(2시간)으로 충분한 여유를 확보합니다.
환경변수 PIPELINE_TIMEOUT으로 조정 가능합니다.
"""

import json
import os
import pytest
from tests.e2e_client import E2EClient


@pytest.fixture(scope="session")
def e2e_result():
    """
    E2E 서버 파이프라인을 세션당 1회 호출하고 결과를 반환합니다.

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
    # 환경변수로 타임아웃 조정 가능 (기본값 7200초 = 2시간)
    # 서버 파이프라인 정상 완주 시간 38~55분을 고려한 안전 마진
    timeout = int(os.getenv("PIPELINE_TIMEOUT", "7200"))

    client = E2EClient()
    start_input = {
        "target_area": "서울특별시 강남구 대치동",
        "main_type": "84㎡",
        "email": "immortal0900@gmail.com",
        "total_units": "500",
    }

    print(f"\n[E2E] 파이프라인 서버 호출 시작... (최대 대기: {timeout}초 / {timeout//60}분)")
    result_dict = client.run_pipeline(start_input=start_input, timeout=timeout)
    print("[E2E] 파이프라인 리턴 완료. 결과 객체를 저장합니다.")

    # 결과 객체를 JSON 파일로 저장 (디버깅/재활용 용도)
    with open("e2e_result.json", "w", encoding="utf-8") as f:
        json.dump(result_dict, f, ensure_ascii=False, indent=4)

    return result_dict


@pytest.fixture(scope="session", autouse=True)
def unified_summary_report():
    """
    모든 테스트 종료 후 통합 종합 리포트를 출력하고
    전체 상세 결과를 JSON 파일로 저장합니다.

    [설계 결정]
    각 모듈 conftest.py의 GLOBAL_RESULTS를 import하는 방식은
    pytest의 conftest 자동 로딩과 패키지 import의 모듈 경로가 달라
    서로 다른 객체를 참조하는 문제가 있었습니다.
    따라서 format_utils._JSON_DETAIL_STORE(단일 모듈 전역 변수)에서
    직접 빌드하는 방식으로 변경했습니다.
    """
    yield  # 모든 테스트 실행 후

    from tests.format_utils import print_final_summary, save_detail_json
    # all_results=None이면 _JSON_DETAIL_STORE에서 자동 빌드
    print_final_summary()
    save_detail_json()
