# src/tests/format_utils.py
"""
DeepEval 테스트 통합 출력 유틸리티

[역할]
1. 개별 테스트 케이스 결과를 일관된 포맷으로 콘솔 출력
2. 최하단에 모듈별 종합 리포트 출력
3. 전체 input/output/score/reason을 JSON 파일로 자동 저장

[환경변수]
- EVAL_FULL_OUTPUT=1 : 콘솔에 전체 입출력 표시 (200자 절단 해제)
"""

import os
import json

# ============================================================
# 설정
# ============================================================
# 환경변수로 전체 출력 여부 결정
FULL_OUTPUT = os.getenv("EVAL_FULL_OUTPUT", "0") == "1"

# JSON 상세 결과 저장용 전역 레지스트리
_JSON_DETAIL_STORE: dict[str, list] = {}


# ============================================================
# 텍스트 유틸리티
# ============================================================
def truncate(text: str, max_len: int = 200) -> str:
    """
    FULL_OUTPUT 모드면 전체 반환, 아니면 max_len자 절단 + '...'

    줄바꿈은 공백으로 치환하여 한 줄로 출력합니다.
    """
    if not text:
        return "(없음)"
    text = text.replace("\n", " ").strip()
    if FULL_OUTPUT or len(text) <= max_len:
        return text
    return text[:max_len] + "..."


# ============================================================
# JSON 상세 저장
# ============================================================
def append_detail(module: str, detail: dict):
    """JSON 저장용 상세 결과 추가 (전체 원문 포함)"""
    _JSON_DETAIL_STORE.setdefault(module, []).append(detail)


def save_detail_json(path: str = "test_eval_details.json"):
    """전체 상세 결과를 JSON 파일로 저장"""
    if not _JSON_DETAIL_STORE:
        return
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_JSON_DETAIL_STORE, f, ensure_ascii=False, indent=2)
    print(f"\n  [JSON 상세 결과 저장 완료] {path}")


# ============================================================
# 개별 케이스 출력
# ============================================================
def print_module_header(module_name: str, count: int):
    """모듈 평가 시작 헤더 출력"""
    print(f"\n>>> [{module_name}] 평가 시작 ({count}건)")
    print("-" * 60)


def print_case_result(
    case_id: str,
    description: str,
    input_text: str,
    output_text: str,
    score: float,
    reason: str | None,
):
    """정적 모듈용 개별 테스트 케이스 결과 출력"""
    print(f"\n  * [{case_id}] {description}")
    print(f"    - 입력: {truncate(input_text)}")
    print(f"    - 출력: {truncate(output_text)}")
    print(f"    - 점수: {score:.2%}")
    if reason:
        print(f"    - 판단 이유: {reason}")


def print_analysis_case_result(
    case_id: str,
    description: str,
    input_text: str,
    output_text: str,
    analysis_score: float,
    rag_score: float | None,
    reason: str | None,
):
    """분석 에이전트용 개별 테스트 케이스 결과 출력 (이중 점수)"""
    print(f"\n  * [{case_id}] {description}")
    print(f"    - 입력: {truncate(input_text)}")
    print(f"    - 출력: {truncate(output_text)}")
    print(f"    - 분석 점수: {analysis_score:.2%}")
    if rag_score is not None:
        print(f"    - RAG 점수: {rag_score:.2%}")
    if reason:
        print(f"    - 판단 이유: {reason}")


# ============================================================
# _JSON_DETAIL_STORE에서 종합 리포트용 데이터 빌드
# ============================================================
def build_summary_from_details() -> dict[str, list]:
    """
    _JSON_DETAIL_STORE에서 print_final_summary()가 기대하는 형태로 변환합니다.

    [변환 규칙]
    - 정적 모듈 (judge, extraction, renderer, final_report, source):
      각 항목의 id/score를 그대로 추출
    - 분석 모듈 (analysis):
      agent별로 그룹핑 -> 평균 analysis_score/rag_score 산출
    """
    summary: dict[str, list] = {}

    for module, details in _JSON_DETAIL_STORE.items():
        if not details:
            continue

        if module == "analysis":
            # agent별로 그룹핑
            agent_groups: dict[str, list] = {}
            for d in details:
                agent = d.get("agent", "unknown")
                agent_groups.setdefault(agent, []).append(d)

            analysis_entries = []
            for agent_name, items in agent_groups.items():
                avg_analysis = sum(d["analysis_score"] for d in items) / len(items)
                entry = {
                    "agent": agent_name,
                    "results": [{
                        "type": agent_name,
                        "analysis_score": avg_analysis,
                        "count": len(items),
                    }],
                }
                rag_scores = [d["rag_score"] for d in items if d.get("rag_score") is not None]
                if rag_scores:
                    entry["results"][0]["rag_score"] = sum(rag_scores) / len(rag_scores)
                analysis_entries.append(entry)
            summary["analysis"] = analysis_entries
        else:
            # 정적 모듈: id와 score만 추출
            summary[module] = [{"id": d.get("id", "unknown"), "score": d["score"]} for d in details]

    return summary


# ============================================================
# 종합 리포트
# ============================================================
_PASS_THRESHOLD = 0.7


def print_final_summary(all_results: dict[str, list] | None = None):
    """
    최하단 통합 종합 리포트 출력

    all_results가 None이면 _JSON_DETAIL_STORE에서 자동 빌드합니다.

    all_results 구조:
    {
        "judge": [{"id": "...", "score": 0.8}, ...],
        "extraction": [...],
        "renderer": [...],
        "analysis": [{"agent": "housing_faq", "results": [{"type": "...", "analysis_score": 0.85, "rag_score": 0.92, "count": 3}]}],
        "final_report": [{"id": "...", "score": 0.88}],
        "source": [{"id": "...", "score": 0.92}],
    }
    """
    if all_results is None:
        all_results = build_summary_from_details()

    separator = "=" * 60
    print(f"\n{separator}")
    print("         [ ALL FOR ONE 평가 종합 리포트 ]")
    print(separator)

    total_count = 0
    total_score_sum = 0.0

    # ---- 정적 데이터셋 (judge, extraction, renderer) ----
    static_modules = {
        "judge": "Judge",
        "extraction": "Extraction",
        "renderer": "Renderer",
    }

    print("\n  [정적 데이터셋]")
    for key, label in static_modules.items():
        results = all_results.get(key, [])
        if not results:
            print(f"  {label:<20s}| (결과 없음)")
            continue
        scores = [r["score"] for r in results]
        avg = sum(scores) / len(scores)
        status = "PASS" if avg >= _PASS_THRESHOLD else "FAIL"
        total_count += len(scores)
        total_score_sum += sum(scores)
        print(f"  {label:<20s}| 평균 {avg:>6.2%} ({len(scores)}건) | {status}")

    # ---- E2E 분석 에이전트 ----
    analysis_results = all_results.get("analysis", [])
    if analysis_results:
        print("\n  [E2E 분석 에이전트]")
        for entry in analysis_results:
            # entry는 {"agent": "...", "results": [...]} 형태
            agent_name = entry.get("agent", "unknown")
            agent_results = entry.get("results", [])
            if not agent_results:
                print(f"  - {agent_name:<18s}| (결과 없음)")
                continue

            for r in agent_results:
                a_score = r.get("analysis_score", 0.0)
                r_score = r.get("rag_score")
                count = r.get("count", 1)
                display_name = agent_name[:16] + ".." if len(agent_name) > 18 else agent_name

                line = f"  - {display_name:<18s}| 분석 {a_score:>6.2%}"
                if r_score is not None:
                    line += f" | RAG {r_score:>6.2%}"
                line += f" ({count}건)"
                print(line)

                total_count += count
                total_score_sum += a_score * count

    # ---- E2E 보고서 (final_report, source) ----
    report_modules = {
        "final_report": ("Final Report", "가중"),
        "source": ("Source", "평균"),
    }

    print("\n  [E2E 보고서]")
    for key, (label, score_type) in report_modules.items():
        results = all_results.get(key, [])
        if not results:
            print(f"  {label:<20s}| (결과 없음)")
            continue
        scores = [r["score"] for r in results]
        avg = sum(scores) / len(scores)
        status = "PASS" if avg >= _PASS_THRESHOLD else "FAIL"
        total_count += len(scores)
        total_score_sum += sum(scores)
        print(f"  {label:<20s}| {score_type} {avg:>6.2%} ({len(scores)}건) | {status}")

    # ---- 최종 요약 ----
    overall_avg = total_score_sum / total_count if total_count > 0 else 0.0
    print(f"\n{separator}")
    print(f"  최종 결과: 총 {total_count}건 평가 완료 / 전체 평균 점수 {overall_avg:.2%}")
    print(separator)
