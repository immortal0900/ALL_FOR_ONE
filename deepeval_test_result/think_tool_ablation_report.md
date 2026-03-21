# Think Tool + Reflexion 제거 실험 보고서 (Ablation Study)

> **실험 목적**: think_tool(React 패턴)과 Reflexion 파이프라인을 동시에 제거했을 때 분석 품질 변화를 정량적으로 측정
> **실험 일자**: 2026-03-21
> **실험 브랜치**: `experiment/no-think-tool` (main에 merge 후 revert 완료)

### 제거 대상 구분

> think_tool과 Reflexion은 **별개의 메커니즘**이며, 이번 실험에서는 둘 다 동시에 제거함

| 메커니즘 | 설명 | 적용 agent | 제거 방식 |
|---------|------|-----------|----------|
| **think_tool (React 패턴)** | LLM이 도구 호출 전 구조화된 사고(self-reflection)를 수행하는 도구. `llm.bind_tools([think_tool])`로 바인딩하고, router가 tool_calls 여부를 감지하여 `tools ↔ agent` 루프를 형성 | 8개 agent 전체 | tool 바인딩에서 think_tool 제거 |
| **Reflexion 파이프라인** | 최종 보고서 초안에 대해 자기검증(reflect_agent → apply_reflection) 루프를 수행하여 반복 개선 | jung_min_jae_agent | reflection 루프를 bypass로 우회 |
| **record_reflection** | 각 노드(뉴스 검색, PDF 검색, 초안 작성 등) 실행 후 think_tool을 직접 호출하여 단계별 성찰을 기록 | policy_agent | record_reflection 함수를 `pass`로 무효화 |

### 제거 상세 내역 (8개 파일)

| 파일 | think_tool 제거 | 추가 제거 사항 |
|------|:---:|------|
| `supply_demand_agent.py` | O | tools ↔ agent 루프 제거 |
| `population_insight_agent.py` | O | tools ↔ agent 루프 제거 |
| `unsold_insight_agent.py` | O | tools ↔ agent 루프 제거 |
| `policy_agent.py` | O | record_reflection → `pass` 무효화 |
| `location_insight_agent.py` | O | tools ↔ agent 루프 제거 |
| `nearby_market_agent.py` | O | tools ↔ agent 루프 제거 |
| `renderer_agent.py` | O | tools ↔ agent 루프 제거 |
| `jung_min_jae_agent.py` | O | reflection 파이프라인 → bypass 우회 |

> **Note**: policy_agent의 `evaluate_report_completeness`(ReportCheck 6점 검증)는 이번 실험에서 제거하지 않음. Reflexion과 함께 제거했어야 했으나 누락된 상태로 실험이 진행됨.

---

## 1. 정적 평가 (Static Evaluation)

> think_tool과 무관한 agent(Judge, Extraction, Renderer)의 기본 성능 확인

| 카테고리 | 기존 버전 | 제거 버전 | 변화 |
|---------|----------|---------|------|
| **Judge** (3건) | 83.33% PASS | 83.33% PASS | **0.00%p** |
| **Extraction** (2건) | 85.00% PASS | 80.00% PASS | **-5.00%p** |
| **Renderer** (2건) | 95.00% PASS | 95.00% PASS | **0.00%p** |
| **종합 평균** | **87.14%** | **85.71%** | **-1.43%p** |

### 정적 평가 개별 케이스

| 케이스 | 기존 | 제거 | 변화 |
|--------|------|------|------|
| judge_001 (일부 누락 초안) | 60.00% | 60.00% | 0.00%p |
| judge_002 (완벽한 초안) | 100.00% | 100.00% | 0.00%p |
| judge_003 (구체적 데이터 부족) | 90.00% | 90.00% | 0.00%p |
| extraction_001 | 80.00% | 80.00% | 0.00%p |
| extraction_002 | 90.00% | **80.00%** | **-10.00%p** |
| renderer_001 | 90.00% | 90.00% | 0.00%p |
| renderer_002 | 100.00% | 100.00% | 0.00%p |

---

## 2. E2E 평가 — 분석 에이전트 (Analysis Agents)

> 기존 3차 평가(가장 최근, 안정화된 수치)와 제거 버전을 비교

### 2-1. 분석 점수 (AnalysisDepth 60% + DataFidelity 20% + StructuralCompleteness 20%)

| Agent | 기존 (3차) | 제거 버전 | 변화 | 판정 |
|-------|-----------|---------|------|------|
| housing_faq | 75.33% | 86.00% | **+10.67%p** | 상승 |
| policy | 92.00% | 88.00% | **-4.00%p** | 하락 |
| supply_demand | 74.00% | 66.00% | **-8.00%p** | 하락 |
| nearby_market | 72.00% | 64.17% | **-7.83%p** | 하락 |
| location_insight | 71.33% | 80.83% | **+9.50%p** | 상승 |
| population_insight | 82.67% | 81.33% | **-1.34%p** | 미미한 하락 |
| unsold_insight | 82.00% | 70.00% | **-12.00%p** | 큰 하락 |
| **평균** | **78.48%** | **76.62%** | **-1.86%p** | 하락 |

### 2-2. RAG 점수 (Faithfulness 33.4% + Contextual Relevancy 33.3% + Answer Relevancy 33.3%)

| Agent | 기존 (3차) | 제거 버전 | 변화 | 판정 |
|-------|-----------|---------|------|------|
| housing_faq | 95.63% | 93.92% | -1.71%p | 미미한 하락 |
| policy | 85.55% | 91.90% | **+6.35%p** | 상승 |
| supply_demand | 64.34% | 75.91% | **+11.57%p** | 큰 상승 |
| nearby_market | 99.37% | 100.00% | +0.63%p | 유지 |
| location_insight | 100.00% | 99.71% | -0.29%p | 유지 |
| population_insight | 88.25% | 100.00% | **+11.75%p** | 큰 상승 |
| unsold_insight | 100.00% | 100.00% | 0.00%p | 유지 |
| **평균** | **90.45%** | **94.49%** | **+4.04%p** | 상승 |

---

## 3. E2E 평가 — 보고서 (Final Report & Source)

| 평가 항목 | 기존 (3차) | 제거 버전 | 변화 |
|----------|-----------|---------|------|
| Final Report | 90.00% | 80.00% | **-10.00%p** |
| Source | 80.00% | 80.00% | **0.00%p** |

---

## 4. E2E 종합 점수

| 구분 | 종합 평균 |
|------|---------|
| 기존 1차 | 61.91% |
| 기존 2차 | 72.09% |
| 기존 3차 | **79.04%** |
| **제거 버전** | **76.91%** |
| **차이 (3차 대비)** | **-2.13%p** |

---

## 5. 핵심 발견 (Key Findings)

### 제거 시 하락하는 영역 (think_tool의 자기검증이 효과적인 곳)

| Agent | 하락폭 | 원인 분석 |
|-------|--------|---------|
| **unsold_insight** | -12.00%p | 미분양 데이터의 시계열 패턴 해석에 think_tool의 자기검증이 중요 |
| **supply_demand** | -8.00%p | 수요/공급 교차 분석에서 논리적 일관성 검증 필요 |
| **nearby_market** | -7.83%p | 비교 단지 간 가격 포지셔닝 판단에 다단계 추론 필요 |
| **Final Report** | -10.00%p | jung_min_jae_agent의 Reflexion 파이프라인 우회로 종합 보고서 품질 하락 |

### 제거 시 상승하는 영역 (think_tool이 오버헤드인 곳)

| Agent | 상승폭 | 원인 분석 |
|-------|--------|---------|
| **housing_faq** | +10.67%p | FAQ 기반 정보 추출은 단순 검색이라 think_tool 루프가 오히려 방해 |
| **location_insight** | +9.50%p | 입지 정보는 구조화된 데이터 정리가 핵심, 과도한 추론 불필요 |

### RAG 점수는 오히려 상승 (+4.04%p)

> think_tool 제거 시 **검색 컨텍스트에 대한 충실도(Faithfulness)가 향상**됨.
> think_tool의 자기검증 과정에서 추가 추론이 발생하면 원본 데이터에서 벗어나는 환각(Hallucination)이 증가할 수 있음을 시사.

---

## 6. 결론

```
정적 평가:  87.14% → 85.71%  (-1.43%p)  영향 미미
E2E 평가:  79.04% → 76.91%  (-2.13%p)  소폭 하락
RAG 점수:  90.45% → 94.49%  (+4.04%p)  오히려 상승
```

**think_tool(React 패턴)은 복잡한 분석 태스크에서 분석 깊이를 높이지만, 단순 정보 추출 태스크에서는 오버헤드로 작용하며, RAG 충실도를 소폭 저하시키는 양면성을 가짐. Reflexion 파이프라인(jung_min_jae_agent)은 최종 보고서 품질에 직접적 영향(-10%p).**

### 향후 고려사항

1. **think_tool 선택적 적용**: 복잡도가 높은 agent(unsold, supply_demand, nearby_market)에만 think_tool 유지, 단순 추출 agent(housing_faq, location_insight)에서는 제거 검토
2. **Reflexion 파이프라인 유지**: jung_min_jae_agent의 Reflexion은 최종 보고서 품질에 직접 기여하므로 유지 권장
3. **RAG 충실도 개선**: think_tool 자기검증 과정에서 원본 데이터 참조를 강제하는 프롬프트 추가 검토
