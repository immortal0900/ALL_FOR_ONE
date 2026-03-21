# scripts/query_langfuse_metrics.py
"""
Langfuse Metrics REST API를 직접 호출하여 토큰/비용/호출수를 조회하는 독립 스크립트.

[존재 이유]
현재 SDK v3.14.5에는 `client.api.metrics` 네임스페이스가 없어
Python SDK의 Metrics API wrapper를 사용할 수 없습니다.
이 스크립트는 SDK 업그레이드 없이 REST API를 직접 호출하여
동일한 결과를 얻습니다.

[아키텍처 위치]
프로덕션 코드(langfuse_tracker.py)와 완전히 독립된 일회성 조회 스크립트.
.env의 인증 키만 재활용합니다.

사용법:
    python scripts/query_langfuse_metrics.py
    python scripts/query_langfuse_metrics.py --from "2026-03-21T15:45:07" --to "2026-03-21T23:59:59"

    --from / --to 는 KST(한국 시간)로 입력합니다. 내부에서 UTC로 자동 변환됩니다.

공식 문서: https://langfuse.com/docs/metrics/features/metrics-api
"""

import os
import sys
import json
import base64
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

# .env 파일 위치: 프로젝트 루트
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# KST = UTC+9
_KST = timezone(timedelta(hours=9))


def _kst_to_utc(kst_str: str) -> str:
    """KST 시간 문자열을 UTC ISO 8601 문자열로 변환합니다.

    [데이터 흐름]
    "2026-03-21T15:45:07" (KST, UTC+9)
    → datetime(2026, 3, 21, 15, 45, 7, tzinfo=KST)
    → datetime(2026, 3, 21, 6, 45, 7, tzinfo=UTC)
    → "2026-03-21T06:45:07Z"

    이 변환이 없으면 Langfuse에 KST 시간을 UTC로 잘못 전달하여
    9시간 뒤의 데이터를 조회하게 되고, 결과가 빈 배열로 돌아옵니다.
    """
    # 이미 'Z' 접미사가 있으면 UTC로 간주하여 그대로 반환
    if kst_str.endswith("Z"):
        return kst_str

    dt_kst = datetime.fromisoformat(kst_str).replace(tzinfo=_KST)
    dt_utc = dt_kst.astimezone(timezone.utc)
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_auth_header() -> str:
    """Basic Auth 헤더를 구성합니다.

    Langfuse REST API는 Basic Auth(public_key:secret_key)를 사용합니다.
    이 함수가 없으면 매 요청마다 base64 인코딩 로직을 반복해야 합니다.
    """
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")

    if not public_key or not secret_key:
        print("[ERROR] LANGFUSE_PUBLIC_KEY 또는 LANGFUSE_SECRET_KEY가 .env에 설정되지 않았습니다.")
        sys.exit(1)

    credentials = f"{public_key}:{secret_key}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"


def query_metrics_v2(
    from_ts: str,
    to_ts: str,
    base_url: str,
    auth_header: str,
) -> dict:
    """v2 Metrics API (observations view)로 모델별 비용/토큰/호출수를 조회합니다.

    [데이터 흐름]
    클라이언트 -> GET /api/public/v2/metrics?query={...} -> Langfuse Cloud
    -> 서버 사이드 aggregation -> JSON 응답 반환

    Args:
        from_ts: 조회 시작 시간 (ISO 8601, UTC)
        to_ts: 조회 종료 시간 (ISO 8601, UTC)
        base_url: Langfuse Cloud 기본 URL
        auth_header: Basic Auth 헤더 값

    Returns:
        Langfuse API 응답 JSON (dict)
    """
    query = json.dumps({
        "view": "observations",
        "metrics": [
            {"measure": "totalCost", "aggregation": "sum"},
            {"measure": "totalTokens", "aggregation": "sum"},
            {"measure": "count", "aggregation": "count"},
        ],
        "dimensions": [{"field": "providedModelName"}],
        "filters": [],
        "fromTimestamp": from_ts,
        "toTimestamp": to_ts,
    })

    response = requests.get(
        f"{base_url}/api/public/v2/metrics",
        headers={"Authorization": auth_header},
        params={"query": query},
        timeout=30,
    )

    if response.status_code != 200:
        print(f"[ERROR] v2 Metrics API 응답 실패 (HTTP {response.status_code})")
        print(response.text)
        return {}

    return response.json()


def query_metrics_v1_fallback(
    from_ts: str,
    to_ts: str,
    base_url: str,
    auth_header: str,
) -> dict:
    """v1 Legacy Metrics API (traces view) fallback.

    v2의 observations view에서 totalTokens가 지원되지 않을 경우 사용합니다.
    traces view는 trace 단위로 집계되므로 dimension 필드가 다릅니다 (name 기준).
    """
    query = json.dumps({
        "view": "traces",
        "metrics": [
            {"measure": "totalTokens", "aggregation": "sum"},
            {"measure": "totalCost", "aggregation": "sum"},
            {"measure": "count", "aggregation": "count"},
        ],
        "dimensions": [{"field": "name"}],
        "filters": [],
        "fromTimestamp": from_ts,
        "toTimestamp": to_ts,
    })

    response = requests.get(
        f"{base_url}/api/public/metrics",
        headers={"Authorization": auth_header},
        params={"query": query},
        timeout=30,
    )

    if response.status_code != 200:
        print(f"[ERROR] v1 Metrics API 응답 실패 (HTTP {response.status_code})")
        print(response.text)
        return {}

    return response.json()


def _print_results(data: list, title: str) -> None:
    """조회 결과를 보기 좋게 출력합니다."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")

    if not data:
        print("  (결과 없음)")
        return

    # 합계 누적용
    total_cost = 0.0
    total_tokens = 0
    total_calls = 0

    for row in data:
        # dimension 필드명은 API 버전에 따라 다를 수 있음
        model = row.get("providedModelName") or row.get("name") or "(unknown)"

        # v2 응답 키: "sum_totalCost", "sum_totalTokens", "count_count"
        # (measure_aggregation이 아닌 aggregation_measure 형식)
        cost = float(row.get("sum_totalCost", 0) or 0)
        tokens = int(float(row.get("sum_totalTokens", 0) or 0))
        calls = int(row.get("count_count", 0) or 0)

        total_cost += cost
        total_tokens += tokens
        total_calls += calls

        print(f"\n  Model: {model}")
        print(f"    Cost:   ${cost:.6f}")
        print(f"    Tokens: {tokens:,}")
        print(f"    Calls:  {calls}")

    print(f"\n{'-' * 60}")
    print(f"  TOTAL")
    print(f"    Cost:   ${total_cost:.6f}")
    print(f"    Tokens: {total_tokens:,}")
    print(f"    Calls:  {total_calls}")
    print(f"{'=' * 60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Langfuse Metrics API로 토큰/비용/호출수 조회"
    )
    parser.add_argument(
        "--from", dest="from_ts",
        default="2026-03-21T15:45:07",
        help="조회 시작 시간 (KST, 기본: 2026-03-21T15:45:07)",
    )
    parser.add_argument(
        "--to", dest="to_ts",
        default="2026-03-21T23:59:59",
        help="조회 종료 시간 (KST, 기본: 2026-03-21T23:59:59)",
    )
    args = parser.parse_args()

    # KST -> UTC 변환
    from_utc = _kst_to_utc(args.from_ts)
    to_utc = _kst_to_utc(args.to_ts)

    base_url = os.getenv("LANGFUSE_BASE_URL", "https://us.cloud.langfuse.com")
    auth_header = _build_auth_header()

    print(f"[INFO] 입력 시간 (KST): {args.from_ts} ~ {args.to_ts}")
    print(f"[INFO] 변환 시간 (UTC): {from_utc} ~ {to_utc}")
    print(f"[INFO] Langfuse URL: {base_url}")

    # Step 1: v2 Metrics API (observations view) 시도
    print("\n[Step 1] v2 Metrics API (observations view) 호출 중...")
    result_v2 = query_metrics_v2(from_utc, to_utc, base_url, auth_header)

    v2_data = result_v2.get("data", [])
    if v2_data:
        _print_results(v2_data, "v2 Observations View - 모델별 집계")

        # totalTokens가 0이면 v1 fallback 시도
        has_tokens = any(float(r.get("sum_totalTokens", 0) or 0) > 0 for r in v2_data)
        if not has_tokens:
            print("[WARN] v2에서 totalTokens가 0입니다. v1 fallback을 시도합니다...")
        else:
            return
    else:
        print("[WARN] v2 응답에 데이터가 없습니다. v1 fallback을 시도합니다...")

    # Step 2: v1 Legacy fallback (traces view)
    print("\n[Step 2] v1 Legacy Metrics API (traces view) 호출 중...")
    result_v1 = query_metrics_v1_fallback(from_utc, to_utc, base_url, auth_header)

    v1_data = result_v1.get("data", [])
    _print_results(v1_data, "v1 Traces View - trace name별 집계")


if __name__ == "__main__":
    main()
