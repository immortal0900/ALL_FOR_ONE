# src/tests/conftest.py
"""
전체 테스트 모듈 공유 fixture

e2e_result fixture를 세션 스코프로 한 번만 서버를 호출하고,
analysis / final_report / source 등 E2E 연동 테스트에서 공유합니다.

[중요] autouse=False — judge/extraction/renderer 등 정적 데이터셋만
사용하는 모듈은 서버 호출 없이 독립 실행 가능합니다.

[실행 모드 — E2E_MODE 환경변수]
  eval_only (기본): 캐시 파일(e2e_result.json)에서 로드, 서버 호출 없음
  cache_only:       서버 호출 → 캐시 저장 → 평가 생략 (데이터 수집만)
  full:             서버 호출 → 캐시 저장 → 평가 실행 (전체 파이프라인)

[타임아웃 설정]
서버 파이프라인 정상 완주 시간은 38~55분입니다.
기본값 7200초(2시간)으로 충분한 여유를 확보합니다.
환경변수 PIPELINE_TIMEOUT으로 조정 가능합니다.
"""

import json
import os
from datetime import datetime
import pytest
from tests.e2e_client import E2EClient


# ============================================================
# Langfuse 테스트 세션 추적
# ============================================================
# [존재 이유]
# 이 fixture가 없으면 DeepEval 평가 LLM 호출(gpt-5-mini)이 Langfuse에
# session_id=null, tags=null로 기록되어 프로덕션 trace와 구분할 수 없습니다.
# session_id + tags를 ContextVar에 설정하면 merge_config()가 모든 호출에 자동 주입합니다.
# ============================================================
@pytest.fixture(scope="session", autouse=True)
def langfuse_test_session():
    """DeepEval 평가 세션 전체를 Langfuse session/tags로 추적합니다.

    [데이터 흐름]
    fixture 시작
      → tracker.set_test_context() → ContextVar에 session_id + tags 저장
      → 모든 테스트 실행 (RetryableChatOpenAI.invoke() → merge_config() → metadata 자동 주입)
      → fixture 종료
      → tracker.clear_test_context() → ContextVar 복원
      → tracker.flush() → 버퍼에 남은 trace를 Langfuse로 강제 전송

    Yields:
        session_id (str): 이 테스트 실행의 Langfuse 세션 ID (예: "deepeval-20260321-154507")
    """
    from utils.langfuse_tracker import tracker

    session_id = f"deepeval-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    tags = ["deepeval", "evaluation"]

    tokens = tracker.set_test_context(session_id=session_id, tags=tags)
    print(f"\n[Langfuse] 테스트 세션 추적 시작: {session_id}")
    print(f"[Langfuse] 태그: {tags}")

    yield session_id

    tracker.clear_test_context(tokens)
    tracker.flush()
    print(f"\n[Langfuse] 테스트 세션 추적 종료: {session_id}")


# ============================================================
# E2E 실행 모드
# ============================================================
# [존재 이유]
# 서버 호출(40분+)과 평가(수 분)를 분리하여 개발 반복 속도를 높입니다.
# 이 설정이 없으면 데이터셋/메트릭만 수정해도 매번 40분 서버 호출을 기다려야 합니다.
E2E_MODE = os.getenv("E2E_MODE", "eval_only").strip()
CACHE_PATH = "e2e_result.json"


@pytest.fixture(scope="session")
def e2e_result():
    """
    E2E 서버 파이프라인 결과를 반환합니다.

    실행 모드(E2E_MODE)에 따라 데이터 소스가 달라집니다:
      eval_only:  캐시 파일 로드 (서버 호출 없음)
      cache_only: 서버 호출 → 캐시 저장 → pytest.skip (평가 생략)
      full:       서버 호출 → 캐시 저장 → 결과 반환 (평가 진행)

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
    # ---- eval_only: 캐시 파일에서 로드, 서버 호출 없음 ----
    if E2E_MODE == "eval_only":
        if not os.path.exists(CACHE_PATH):
            pytest.fail(
                f"캐시 파일({CACHE_PATH})이 없습니다.\n"
                f"  E2E_MODE=full 또는 cache_only로 먼저 실행하세요."
            )
        print(f"\n[E2E] eval_only 모드 — 캐시({CACHE_PATH}) 로드")
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    # ---- cache_only / full: 서버 호출 + 캐시 저장 ----
    timeout = int(os.getenv("PIPELINE_TIMEOUT", "7200"))

    client = E2EClient()
    start_input = {
        "target_area": "서울특별시 강남구 대치동",
        "main_type": "84㎡",
        "email": "immortal0900@gmail.com",
        "total_units": "500",
    }

    print(f"\n[E2E] {E2E_MODE} 모드 — 서버 호출 시작 (최대 대기: {timeout}초 / {timeout//60}분)")
    # Langfuse 태그를 전달하여 파이프라인 trace에서 테스트 실행을 구분
    result_dict = client.run_pipeline(
        start_input=start_input,
        timeout=timeout,
        tags=["deepeval", "pipeline"],
    )
    print("[E2E] 파이프라인 리턴 완료. 캐시 파일을 저장합니다.")

    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(result_dict, f, ensure_ascii=False, indent=4)
    print(f"[E2E] 캐시 저장 완료: {CACHE_PATH}")

    # cache_only: 서버 호출 + 캐시 저장까지만, 평가는 생략
    if E2E_MODE == "cache_only":
        pytest.skip("cache_only 모드: 캐시 저장 완료, 평가 생략")

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
