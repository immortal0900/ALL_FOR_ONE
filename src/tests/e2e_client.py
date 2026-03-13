# src/tests/e2e_client.py
import httpx
import time
import os
from typing import Dict, Any

# 서버 파이프라인은 장시간 소요(40분+)되므로 HTTP 클라이언트 타임아웃을 충분히 설정
# Ref: https://www.python-httpx.org/advanced/timeouts/
_HTTP_TIMEOUT = httpx.Timeout(connect=30.0, read=60.0, write=30.0, pool=10.0)

# 폴링 간격 (초) — 서버가 장시간 작업이므로 30초로 늘려 불필요한 요청 감소
_POLL_INTERVAL = 30


def get_server_url() -> str:
    # 기본적으로 로컬 8080 포트를 사용하거나 환경변수를 따름
    return os.getenv("DEEPEVAL_SERVER_URL", "http://localhost:8080").strip()


class E2EClient:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or get_server_url()

    def run_pipeline(self, start_input: Dict[str, Any], timeout: int = 7200) -> Dict[str, Any]:
        """
        서버에 생성 파이프라인(/invoke)을 요청하고
        결과가 나올 때까지 폴링하여 최종 output을 반환합니다.

        Args:
            start_input: 파이프라인 시작 입력값
            timeout: 최대 대기 시간(초), 기본값 7200 (2시간)
                     환경변수 PIPELINE_TIMEOUT으로도 제어 가능

        Raises:
            TimeoutError: timeout 초과 시
            RuntimeError: 서버 오류 또는 파이프라인 실패 시
        """
        print(f"\n[E2EClient] 서버({self.base_url})에 파이프라인 요청 중...")

        # 1. 파이프라인 트리거
        try:
            resp = httpx.post(
                f"{self.base_url}/invoke",
                json={"start_input": start_input},
                timeout=_HTTP_TIMEOUT,
            )
            resp.raise_for_status()
        except Exception as e:
            raise RuntimeError(f"서버 /invoke 호출 실패: {e}")

        job_id = resp.json()["job_id"]
        print(f"[E2EClient] Job ID 할당됨: {job_id}")

        # 2. 결과 폴링 (30초 간격 — 장시간 작업에 불필요한 폴링 최소화)
        start_time = time.time()
        poll_count = 0
        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(
                    f"파이프라인 실행 시간 초과 ({timeout}초 경과)\n"
                    f"  타임아웃 연장: conftest.py timeout 값 또는 PIPELINE_TIMEOUT 환경변수 조정\n"
                    f"  캐시 재활용: e2e_result.json이 존재하면 E2E_MODE=eval_only(기본값)로 평가만 실행 가능"
                )

            try:
                status_resp = httpx.get(
                    f"{self.base_url}/status/{job_id}",
                    timeout=_HTTP_TIMEOUT,
                ).json()
            except Exception as e:
                print(f"  [경고] 상태 조회 실패 (재시도): {e}")
                time.sleep(_POLL_INTERVAL)
                continue

            status = status_resp["status"]

            if status == "completed":
                print(f"[E2EClient] 파이프라인 완료 ({elapsed:.1f}초 소요)")
                break
            elif status == "failed":
                err_msg = status_resp.get("message", "알 수 없는 에러")
                raise RuntimeError(f"파이프라인 실행 중 서버 에러: {err_msg}")

            # 진행 중이면 30초 대기
            poll_count += 1
            print(f"  ...진행중 [{poll_count}회 폴링 / 경과 {elapsed:.0f}초] (상태: {status})")
            time.sleep(_POLL_INTERVAL)

        # 3. 최종 결과 가져오기
        result_resp = httpx.get(
            f"{self.base_url}/result/{job_id}",
            timeout=_HTTP_TIMEOUT,
        )
        result_resp.raise_for_status()

        return result_resp.json()["output"]
