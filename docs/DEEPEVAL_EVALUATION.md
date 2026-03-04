# DeepEval 평가 시스템 가이드

## 개요

이 프로젝트의 모든 LLM 호출 지점에 대해 DeepEval 기반 평가 시스템을 구축하였습니다.
평가(채점)에는 `gpt-5-mini` 모델을 사용하며, 기존 에이전트들은 원래 지정된 모델을 그대로 사용합니다.

---

## 초기 설정

### 1. 환경 변수

`.env` 파일에 아래 키가 설정되어 있어야 합니다:

```
OPENAI_API_KEY=<your-openai-api-key>
```

### 2. 의존성 설치 (환경별 가이드)

프로젝트가 Railway 등에 배포되거나 Docker 환경일 수 있으므로 상황에 맞게 설치합니다.

**A. 로컬 개발 환경 (uv 사용 시)**
```bash
uv add deepeval
```

---

## 평가 대상 LLM 호출 지점

<!-- DEEPEVAL:EVAL_POINTS:START -->
| # | 파일 | 함수 | 용도 | 분류 | 메트릭 | threshold |
|---|------|------|------|------|--------|-----------|
| 1 | housing_faq_agent.py | call_llm() | 청약 FAQ 분석 | RAG+분석 | AnalysisDepth, DataFidelity, StructuralCompleteness | 0.7 |
| 2 | policy_agent.py | generate_initial_report() | 정책 분석 보고서 | 에이전트 | AnalysisDepth, DataFidelity, StructuralCompleteness | 0.7 |
| 3 | policy_agent.py | evaluate_report_completeness() | 보고서 평가 | 검수 | CritiqueAccuracy | 0.7 |
| 4 | policy_agent.py | revise_report() | 보고서 수정 | 에이전트 | AnalysisDepth, DataFidelity, StructuralCompleteness | 0.7 |
| 5 | supply_demand_agent.py | trade_balance() | 지역 필터링 | 추출 | ExtractionAccuracy | 0.7 |
| 6 | supply_demand_agent.py | agent() | 수급 분석 | 에이전트 | AnalysisDepth, DataFidelity, StructuralCompleteness | 0.7 |
| 7 | nearby_market_agent.py | agent() | 주변시장 분석 | 에이전트 | AnalysisDepth, DataFidelity, StructuralCompleteness | 0.7 |
| 8 | location_insight_agent.py | agent() | 입지 분석 | 에이전트 | AnalysisDepth, DataFidelity, StructuralCompleteness | 0.7 |
| 9 | population_insight_agent.py | agent() | 인구 분석 | 에이전트 | AnalysisDepth, DataFidelity, StructuralCompleteness | 0.7 |
| 10 | unsold_insight_agent.py | agent() | 미분양 분석 | 에이전트 | AnalysisDepth, DataFidelity, StructuralCompleteness | 0.7 |
| 11 | jung_min_jae_agent.py | agent()+reflect+apply | 최종 보고서 | 보고서 | ReportProfessionalism, AnalysisCoverage | 0.7 |
| 12 | renderer_agent.py | init()+agent() | PPT 변환 | 변환 | SlidePlanStructure | 0.7 |
| 13 | main_agent.py | final_node() | 출처 추출 | 출처 | SourceCompleteness | 0.7 |
<!-- DEEPEVAL:EVAL_POINTS:END -->

---

## 테스트 실행 (결과 txt 저장)

```bash
# 분석 에이전트 평가 (7개)
set PYTHONIOENCODING=utf-8 && uv run deepeval test run src/tests/analysis/analysis_eval/test_analysis.py -v > test_analysis_results.txt 2>&1

# 최종 보고서 평가
set PYTHONIOENCODING=utf-8 && uv run deepeval test run src/tests/final_report/report_eval/test_final_report.py -v > test_final_report_results.txt 2>&1

# 데이터 추출 평가 (trade_balance 전용)
set PYTHONIOENCODING=utf-8 && uv run deepeval test run src/tests/extraction/extraction_eval/test_extraction.py -v > test_extraction_results.txt 2>&1

# 검수(Judge) 평가 (evaluate_report_completeness 전용)
set PYTHONIOENCODING=utf-8 && uv run deepeval test run src/tests/judge/judge_eval/test_judge.py -v > test_judge_results.txt 2>&1

# PPT 변환 평가
set PYTHONIOENCODING=utf-8 && uv run deepeval test run src/tests/renderer/renderer_eval/test_renderer.py -v > test_renderer_results.txt 2>&1

# 출처 추출 평가
set PYTHONIOENCODING=utf-8 && uv run deepeval test run src/tests/source/source_eval/test_source.py -v > test_source_results.txt 2>&1
```

---

## 커스텀 메트릭 요약

| 메트릭 | 평가 기준 | 대상 |
|--------|----------|------|
| **AnalysisDepth** | 데이터 기반 분석 심도, 시계열 해석, 근거 있는 전망 | 7개 분석 에이전트 |
| **DataFidelity** | 입력 데이터 환각 방지, 정확한 수치 인용 | 7개 분석 에이전트 |
| **StructuralCompleteness** | Markdown 구조, 논리적 흐름, 결론 포함 | 7개 분석 에이전트 |
| **ReportProfessionalism** | 전문 용어, 문어체, 논리적 일관성 | 최종 보고서 |
| **AnalysisCoverage** | 7개 분석 영역 균형 반영, 교차 분석 | 최종 보고서 |
| **CritiqueAccuracy** | 누락 섹션 정확 지적, 재검색 키워드 품질 | 검수자 (evaluate_report_completeness) |
| **ExtractionAccuracy** | 정확한 필터링, 환각 없는 추출 | 데이터 추출 (trade_balance) |
| **SlidePlanStructure** | JSON 유효성, 원문 충실도 | PPT 변환 |
| **SourceCompleteness** | 출처 빠짐없이 구조화 | 출처 추출 |

---

## 결과 해석

- **점수 범위**: 0.0 ~ 1.0 (threshold 기본 0.7)
- **가중 점수**: 주요 메트릭 60%, 보조 메트릭 40%
- **PASS/FAIL**: 가중 평균 >= 0.7 → PASS

---

## 데이터셋 추가/수정

각 그룹의 `datasets/` 디렉터리의 JSON 파일을 수정합니다.

```json
{
    "id": "unique_id",
    "type": "analysis_report",
    "description": "테스트 설명",
    "input": "LLM에 입력할 데이터",
    "actual_output": "LLM이 생성해야 할 출력"
}
```

---

## 새 LLM 호출 추가 시

`/deepeval-sync` 워크플로우를 실행하여 새로운 LLM 호출 지점을 탐지하고 평가 시스템에 추가합니다.
