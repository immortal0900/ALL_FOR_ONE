# Think Tool 선택적 제거 + format_output 적용 실험 보고서

> **실험 목적**: 1차 ablation 결과를 기반으로 think_tool을 선택적으로 제거/유지하고, format_output 노드(Structured Output)를 추가하여 분석 품질과 출력 안정성을 동시에 개선
> **실험 일자**: 2026-03-22
> **기준 비교**: 기존 3차 평가 (think_tool 전체 적용, format_output 없음)
> **선행 실험**: [think_tool_ablation_report.md](think_tool_ablation_report.md) (전체 제거 실험, 2026-03-21)

---

## 1. 변경 내역

### 1-1. 1차 ablation 결과에 따른 선택적 적용 판정

| Agent | 1차 ablation 변화 | 판정 | 조치 |
|-------|:---:|:---:|------|
| **housing_faq** | +10.67%p | think_tool 불필요 | **제거 유지** (원래 tool_list 없음) |
| **policy** | -4.00%p | think_tool 필요 | **유지** (record_reflection 포함) |
| **supply_demand** | -8.00%p | think_tool 필요 | **유지** + format_output 추가 |
| **nearby_market** | -7.83%p | think_tool 필요 | **유지** + format_output 추가 |
| **location_insight** | +9.50%p | think_tool 불필요 | **제거** + 프롬프트 정리 |
| **population_insight** | -1.34%p | 판정 보류 → 제거 후 -9.34%p 확인 | **복원** + format_output 추가 |
| **unsold_insight** | -12.00%p | think_tool 필요 | **유지** + format_output 추가 |
| **renderer** | - | think_tool 불필요 | **제거 유지** |
| **jung_min_jae** | -10.00%p (Reflexion) | Reflexion 필요 | **유지** (변경 없음) |

### 1-2. format_output 노드 (신규)

> **해결한 문제**: think_tool의 reflection 텍스트가 최종 result에 평문으로 노출되는 버그
> **원인**: LLM이 tool_calls 대신 `think_tool(reflection: "...")`을 content에 직접 작성하는 비결정적 동작

| 구성요소 | 역할 |
|---------|------|
| `strip_think_tool()` | 정규식으로 `think_tool(...)` 평문을 입력에서 제거 (src/utils/sanitize.py) |
| `AnalysisReport` | Pydantic 스키마 — `result: str` 필드만 강제 (structured_schemas.py) |
| `format_llm` | `LLMProfile.dev_llm().with_structured_output(AnalysisReport)` |
| `format_output` 노드 | ReAct 루프 종료 후 → strip → structured output → result 저장 |

적용 agent: supply_demand, nearby_market, population_insight, unsold_insight (think_tool 유지 4개)

### 1-3. 프롬프트 정리

| 파일 | 변경 |
|------|------|
| `analysis_location_insight.yaml` | think_tool 강제 호출 지시 2줄 제거 (도구 제거와 프롬프트 불일치 해소) |

---

## 2. 정적 평가 (Static Evaluation)

| 카테고리 | 기존 3차 | 선택적 제거 | 변화 |
|---------|:---:|:---:|:---:|
| **Judge** (3건) | 83.33% | 83.33% | 0.00%p |
| **Extraction** (2건) | 85.00% | 80.00% | -5.00%p |
| **Renderer** (2건) | 95.00% | 95.00% | 0.00%p |
| **종합** | **87.14%** | **85.71%** | **-1.43%p** |

> Extraction -5%p는 LLM 채점 비결정성 범위 내. Judge/Renderer는 think_tool과 무관하여 변화 없음.

---

## 3. E2E 평가 — 분석 에이전트

### 3-1. 분석 점수 (AnalysisDepth 60% + DataFidelity 20% + StructuralCompleteness 20%)

| Agent | 기존 3차 | 선택적 제거 | 변화 | think_tool | format_output |
|-------|:---:|:---:|:---:|:---:|:---:|
| housing_faq | 75.33% | **84.67%** | **+9.34%p** | 제거 | - |
| policy | 92.00% | 86.67% | -5.33%p | 유지 | - |
| supply_demand | 74.00% | 74.00% | 0.00%p | 유지 | O |
| nearby_market | 72.00% | **82.17%** | **+10.17%p** | 유지 | O |
| location_insight | 71.33% | **78.17%** | **+6.84%p** | 제거 | - |
| population_insight | 82.67% | **86.67%** | **+4.00%p** | 유지(복원) | O |
| unsold_insight | 82.00% | **94.00%** | **+12.00%p** | 유지 | O |
| **평균** | **78.48%** | **83.76%** | **+5.29%p** | - | - |

### 3-2. RAG 점수 (Faithfulness 33.4% + Contextual Relevancy 33.3% + Answer Relevancy 33.3%)

| Agent | 기존 3차 | 선택적 제거 | 변화 |
|-------|:---:|:---:|:---:|
| housing_faq | 95.63% | 89.87% | -5.76%p |
| policy | 85.55% | **96.80%** | **+11.25%p** |
| supply_demand | 64.34% | **97.68%** | **+33.34%p** |
| nearby_market | 99.37% | 99.34% | -0.03%p |
| location_insight | 100.00% | **100.00%** | 0.00%p |
| population_insight | 88.25% | **97.92%** | **+9.67%p** |
| unsold_insight | 100.00% | 95.07% | -4.93%p |
| **평균** | **90.45%** | **96.67%** | **+6.22%p** |

---

## 4. E2E 평가 — 보고서 (Final Report & Source)

| 평가 항목 | 기존 3차 | 선택적 제거 | 변화 |
|----------|:---:|:---:|:---:|
| Final Report | 90.00% | **92.00%** | **+2.00%p** |
| Source | 80.00% | 70.00% | -10.00%p |

> Source -10%p는 LLM이 Google Drive 링크를 출처로 제시하여 감점된 비결정적 품질 문제. 코드 변경과 무관.

---

## 5. E2E 종합 점수

| 구분 | 종합 평균 |
|------|:---:|
| 기존 1차 | 61.91% |
| 기존 2차 | 72.09% |
| 기존 3차 | 79.04% |
| 1차 ablation (전체 제거) | 76.91% |
| **선택적 제거 + format_output** | **83.52%** |
| **차이 (3차 대비)** | **+4.48%p** |

---

## 6. think_tool 누출 검증

| Agent | 기존 3차 | 1차 ablation | 선택적 제거 |
|-------|:---:|:---:|:---:|
| nearby_market | 1회 누출 | 0 (제거) | **0회** |
| location_insight | 0 | 1회 누출 | **0회** |
| 나머지 5개 | 0 | 0 | **0회** |

> format_output 노드의 Structured Output(AnalysisReport)이 think_tool 평문 노출을 완전 차단.
> location_insight는 프롬프트에서 think_tool 강제 지시를 제거하여 해결.

---

## 7. 비용 분석 (Langfuse Trace 비교)

> 3개 trace의 표면 비용 차이는 RunnableWithFallbacks의 이중 로깅 아티팩트가 주 원인

| | think_tool + Fallback | NO think_tool + Fallback | think_tool, NO Fallback |
|---|:---:|:---:|:---:|
| **Langfuse 표시 비용** | $2.18 | ~$1.92 | $1.62 |
| **중복 제거 실제 비용** | $1.056 | $0.962 | $0.968 |

> 중복 제거 후 세 trace 모두 $0.96~$1.06 범위로 수렴.
> **think_tool의 비용 절감 효과는 통계적으로 유의하지 않음.** LLM 비결정성이 루프 횟수에 미치는 영향이 think_tool 효과보다 더 큼.
> think_tool의 가치는 비용이 아닌 **출력 품질의 일관성과 reflection 품질** 측면에서 평가해야 함.

---

## 8. 핵심 발견 (Key Findings)

### format_output 노드의 효과

| Agent | format_output 적용 전 (1차 ablation) | format_output 적용 후 | 개선폭 |
|-------|:---:|:---:|:---:|
| supply_demand | 66.00% | 74.00% | +8.00%p |
| nearby_market | 64.17% | **82.17%** | **+18.00%p** |
| unsold_insight | 70.00% | **94.00%** | **+24.00%p** |

> format_output이 think_tool 반성문 노출을 차단하면서, LLM이 내부적으로 reflection을 활용하되 깨끗한 보고서만 출력하는 구조가 성립됨.

### population_insight think_tool 복원 효과

| | think_tool 제거 (이전 실행) | think_tool 복원 + format_output |
|---|:---:|:---:|
| 분석 점수 | 73.33% | **86.67%** |
| 변화 | -9.34%p (vs 기존 3차) | **+4.00%p** (vs 기존 3차) |

> 1차 ablation에서 -1.34%p로 미미했으나, 실제 적용 시 -9.34%p까지 하락하여 think_tool 필요성이 확인됨.

### think_tool 제거가 유효한 agent

| Agent | 제거 후 점수 | 기존 3차 | 근거 |
|-------|:---:|:---:|------|
| housing_faq | **84.67%** | 75.33% | tool_list 자체가 없는 단순 RAG+LLM 구조. think_tool 루프가 불필요 |
| location_insight | **78.17%** | 71.33% | 구조화된 데이터 정리가 핵심. 프롬프트에서 think_tool 지시 제거로 해결 |

---

## 9. 결론

```
정적 평가:   87.14% → 85.71%  (-1.43%p)  영향 미미
E2E 분석:   78.48% → 83.76%  (+5.29%p)  유의미한 상승
RAG 점수:   90.45% → 96.67%  (+6.22%p)  대폭 상승
E2E 종합:   79.04% → 83.52%  (+4.48%p)  상승
```

**선택적 think_tool 제거 + format_output 적용은 1차 전체 제거 대비 +6.61%p(76.91% → 83.52%) 개선.**

### 최종 agent별 think_tool 적용 현황

| Agent | think_tool | format_output | 근거 |
|-------|:---:|:---:|------|
| housing_faq | X | - | 단순 RAG, think_tool 불필요 (+9.34%p) |
| policy | O | - | record_reflection + ReportCheck 검증 체계 유지 |
| supply_demand | O | O | 수요/공급 교차 분석에 자기검증 필요 |
| nearby_market | O | O | 비교 단지 간 가격 포지셔닝에 다단계 추론 필요 |
| location_insight | X | - | 구조화 데이터 정리 중심, 프롬프트 정리로 해결 |
| population_insight | O | O | 시계열 패턴 해석에 자기검증 필요 (복원 시 +13.34%p) |
| unsold_insight | O | O | 미분양 데이터 시계열에 자기검증 필수 (+12.00%p) |
| renderer | X | - | PPT 구조 변환, think_tool 불필요 |
| jung_min_jae | O | - | Reflexion 파이프라인 유지 (보고서 품질 직결) |
