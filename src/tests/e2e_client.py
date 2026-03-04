# src/tests/e2e_client.py
import httpx
import time
import os
from typing import Dict, Any

def get_server_url() -> str:
    # 기본적으로 로컬 8080 포트를 사용하거나 환경변수를 따름
    return os.getenv("DEEPEVAL_SERVER_URL", "http://localhost:8080")

class E2EClient:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or get_server_url()

    def run_pipeline(self, start_input: Dict[str, Any], timeout: int = 600) -> Dict[str, Any]:
        """
        서버에 생성 파이프라인(/invoke)을 요청하고
        결과가 나올 때까지 폴링하여 최종 output을 반환합니다.
        
        timeout: 최대 대기 시간 (초)
        """
        print(f"\n[E2EClient] 서버({self.base_url})에 파이프라인 요청 중...")
        
        # 1. 파이프라인 트리거
        try:
            resp = httpx.post(f"{self.base_url}/invoke", json={"start_input": start_input})
            resp.raise_for_status()
        except Exception as e:
            raise RuntimeError(f"서버 /invoke 호출 실패: {e}")
            
        job_id = resp.json()["job_id"]
        print(f"[E2EClient] Job ID 할당됨: {job_id}")

        # 2. 결과 폴링
        start_time = time.time()
        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"파이프라인 실행 시간 초과 ({timeout}초)")
                
            status_resp = httpx.get(f"{self.base_url}/status/{job_id}").json()
            status = status_resp["status"]
            
            if status == "completed":
                print(f"[E2EClient] 파이프라인 완료 ({time.time() - start_time:.1f}초)")
                break
            elif status == "failed":
                err_msg = status_resp.get("message", "알 수 없는 에러")
                raise RuntimeError(f"파이프라인 실행 중 서버 에러: {err_msg}")
            
            # 진행 중이면 대기 (10초 간격)
            print(f"  ...진행중 (상태: {status})")
            time.sleep(10)

        # 3. 최종 결과 가져오기
        result_resp = httpx.get(f"{self.base_url}/result/{job_id}")
        result_resp.raise_for_status()
        
        return result_resp.json()["output"]
