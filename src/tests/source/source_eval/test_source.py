# src/tests/source/source_eval/test_source.py
"""
출처 추출 평가 테스트

E2E 서버가 생산한 실제 출처 추출 결과(e2e_result["source"])를 평가합니다.
input은 최종 보고서(e2e_result["final_report"]) -- 출처 추출 에이전트가
최종 보고서를 입력받아 출처를 나열하는 구조이기 때문입니다.

[실행]
set PYTHONIOENCODING=utf-8 && uv run deepeval test run src/tests/source/source_eval/test_source.py -v > test_source_results.txt 2>&1
"""

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from .custom_metrics import get_all_metrics
from .conftest import GLOBAL_RESULTS


def test_source(e2e_result):
    """E2E 서버가 생산한 출처 추출 완전성 평가"""
    # E2E 결과에서 실제 출처 추출 결과 가져오기
    source_output = e2e_result.get("source", "")
    if not source_output:
        pytest.skip("E2E 결과에 'source'가 비어 있습니다.")

    # input: 최종 보고서 (출처 추출의 입력물)
    final_report = e2e_result.get("final_report", "")
    if not final_report:
        pytest.skip("E2E 결과에 'final_report'가 비어 있습니다.")

    # 팩토리 패턴: 새 메트릭 인스턴스 생성
    metrics = get_all_metrics()

    tc = LLMTestCase(
        input=final_report,
        actual_output=source_output,
    )

    # assert_test: DeepEval에 결과를 공식 등록 (.temp_test_run_data.json 기록)
    try:
        assert_test(tc, metrics)
    except AssertionError:
        pass

    item_scores = {}
    for m in metrics:
        item_scores[m.name] = m.score if m.score else 0.0

    avg = sum(item_scores.values()) / len(item_scores)

    print(f"\n  * [E2E] 출처 추출 점수: {avg:.2%}")
    for m in metrics:
        score_val = m.score if m.score else 0.0
        print(f"    - {m.name}: {score_val:.2f}")
        if m.reason:
            print(f"    - 판단 이유: {m.reason}")

    GLOBAL_RESULTS.append({"id": "e2e_source", "score": avg})

    assert avg >= 0.7, f"출처 추출 점수 {avg:.2%}로 기준(70%) 미달"
