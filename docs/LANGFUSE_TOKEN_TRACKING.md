# Langfuse 토큰/비용 추적 가이드

프로젝트의 모든 LLM 호출을 Langfuse를 통해 추적하여 토큰 사용량과 비용을 모니터링합니다.

## 초기 설정

### 1. Langfuse 계정 생성
1. [Langfuse Cloud](https://cloud.langfuse.com) 가입
2. 프로젝트 생성
3. **Settings → API Keys**에서 Secret Key / Public Key 복사

### 2. 환경변수 설정

**로컬 개발** (`.env`):
```bash
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key
LANGFUSE_BASE_URL=https://cloud.langfuse.com
LANGFUSE_ENABLED=true
```

**Railway 배포**: Railway 대시보드 → Variables에 동일한 4개 변수 추가

### 3. 의존성 설치
```bash
uv sync
# 또는
pip install langfuse
```

## 아키텍처

```
RetryableChatOpenAI.invoke() ──→ _merge_langfuse_config() ──→ CallbackHandler 자동 주입
                                                               │
gemini_search()      ──→ tracker.get_client() ──→ 수동 generation 기록   ──→  Langfuse Cloud
perplexity_search()  ──→ tracker.get_client() ──→ 수동 generation 기록   ──→  대시보드
molit_search()       ──→ tracker.get_client() ──→ 수동 generation 기록   ──→  확인
```

**핵심 파일**: `src/utils/langfuse_tracker.py` (TokenTracker 싱글톤)

## 추적 비활성화

`LANGFUSE_ENABLED=false`로 설정하면 모든 추적이 비활성화되고, 기존 시스템은 정상 작동합니다 (Graceful Degradation).

## 태그 구조

| 대분류 | 세부 태그 | 설명 |
|--------|----------|------|
| policy | report, evaluation, revision | 정책 분석 |
| nearby-market | report | 주변 시세 분석 |
| location | report | 입지 분석 |
| supply-demand | report, trade | 수급 분석 |
| population | report | 인구 분석 |
| unsold | report | 미분양 분석 |
| housing-faq | report | 청약 FAQ |
| renderer | title, slideplan | PPT 생성 |
| chatbot | response | 챗봇 응답 |
| jungminjae | directive, report, reflection, revision | 보고서 작성 |
| tool | gemini-search, perplexity, kostat, csv-convert | 도구 호출 |

## 추적 대상 LLM 호출 지점

<!-- LANGFUSE:TRACKING_POINTS:START -->
| # | 파일 | 함수 | 용도 | 모델 | 추적 방식 |
|---|------|------|------|------|----------|
| 1 | policy_agent.py | generate_initial_report() | 정책 보고서 초안 | GPT-5-mini | 자동(CallbackHandler) |
| 2 | policy_agent.py | evaluate_report_completeness() | 보고서 평가 | GPT-5-mini | 자동 |
| 3 | policy_agent.py | revise_report() | 보고서 수정 | GPT-5-mini | 자동 |
| 4 | nearby_market_agent.py | agent() | 주변 시세 보고서 | GPT-5-mini | 자동 |
| 5 | location_insight_agent.py | agent() | 입지 분석 보고서 | GPT-5-mini | 자동 |
| 6 | supply_demand_agent.py | trade_balance() | 매매수급 분석 | GPT-5-mini | 자동 |
| 7 | supply_demand_agent.py | agent() | 수급 보고서 | GPT-5-mini | 자동 |
| 8 | population_insight_agent.py | agent() | 인구 보고서 | GPT-5-mini | 자동 |
| 9 | unsold_insight_agent.py | agent() | 미분양 보고서 | GPT-5-mini | 자동 |
| 10 | housing_faq_agent.py | call_llm() | 청약 FAQ | GPT-5-mini | 자동 |
| 11 | renderer_agent.py | init() | PPT 제목 | GPT-5-mini | 자동 |
| 12 | renderer_agent.py | agent() | SlidePlan 생성 | Claude Sonnet 4.5 | 자동 |
| 13 | chatbot_graph_agent.py | generate_response() | 챗봇 응답 | GPT-5 | 자동 |
| 14 | jung_min_jae_agent.py | reporting() | 세그먼트 지시 | GPT-5-mini | 자동 |
| 15 | jung_min_jae_agent.py | agent() | 세그먼트 보고서 | GPT-5 | 자동 |
| 16 | jung_min_jae_agent.py | reflect_agent() | 자아성찰 | GPT-5-mini | 자동 |
| 17 | jung_min_jae_agent.py | apply_reflection() | 성찰 반영 | GPT-5 | 자동 |
| 18 | main_agent.py | final_node() | 출처 페이지 | GPT-5-mini | 자동 |
| 19 | kostat_api.py | get_move_population() | 인구이동 쿼리 | GPT-5-mini | 자동 |
| 20 | kostat_api.py | get_one_people_gdp() | GDP 쿼리 | GPT-5-mini | 자동 |
| 21 | kostat_api.py | chain.invoke() | SQL 쿼리 | GPT-5-mini | 자동 |
| 22 | unsold_units.py | unsold_units() | 미분양 쿼리 | GPT-5-mini | 자동 |
| 23 | context_to_csv.py | CSV 변환 | CSV 포맷 변환 | GPT-5-mini | 자동 |
| 24 | estate_web_crawling_tool.py | 크롤링 | 결과 정리 | GPT-5-mini | 자동 |
| 25 | pre_promise_competition_tool_v2.py | pre_promise() | 청약 경쟁률 | GPT-5-mini | 자동 |
| 26 | gemini_search_tool.py | gemini_search() | 부동산 검색 | Gemini 2.5 Pro | 수동(Low-Level SDK) |
| 27 | perplexity_search_tool.py | perplexity_search() 외 | 최신 정보 검색 | Sonar Reasoning Pro | 수동 |
| 28 | molit_search_tool.py | search_policy_news() | 국토부 검색 | Perplexity | 수동 |
<!-- LANGFUSE:TRACKING_POINTS:END -->

## 대시보드 확인

1. [Langfuse Dashboard](https://cloud.langfuse.com) 로그인
2. **Traces** 탭에서 전체 호출 이력 확인
3. **Analytics** 탭에서 토큰 사용량/비용 통계 확인
4. 태그별 필터링으로 기능별 비용 분석

## 문제 해결

| 증상 | 원인 | 해결 |
|------|------|------|
| 대시보드에 trace가 안 보임 | `LANGFUSE_ENABLED=false` | `.env`에서 `true`로 변경 |
| Import 에러 | langfuse 미설치 | `uv sync` 또는 `pip install langfuse` |
| 인증 실패 | API 키 오류 | Langfuse Settings에서 키 재발급 |
| 일부 호출만 추적됨 | Gemini/Perplexity는 수동 추적 | 해당 파일의 추적 코드 확인 |

## 새 LLM 호출 추가 시

`/langfuse-sync` 명령으로 자동 동기화하거나, 수동으로:

1. **LangChain 호출**: `LLMProfile.xxx_llm()` 사용 → 자동 추적 (추가 작업 없음)
2. **네이티브 API 호출**: `_langfuse_tracker.get_client()` 수동 추적 코드 추가
3. 이 문서의 추적 대상 테이블 업데이트
