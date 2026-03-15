# ALL-FOR-ONE API & Data Flow 문서

> 최종 업데이트: 2026-03-15
> 프로젝트: 부동산 분양성 검토 보고서 자동 생성 시스템

---

## 목차

1. [개요](#1-개요)
2. [데이터 흐름 상세](#2-데이터-흐름-상세)
3. [메인 워크플로우](#3-메인-워크플로우)
4. [플로우 다이어그램](#4-플로우-다이어그램)
5. [이메일 발송](#5-이메일-발송)
6. [부록](#6-부록)
7. [Langfuse Observability](#7-langfuse-observability)
8. [DeepEval 테스트 아키텍처](#8-deepeval-테스트-아키텍처)

---

<!-- SECTION:OVERVIEW:START -->
## 1. 개요

### 1.1 시스템 아키텍처

```mermaid
flowchart TB
    subgraph Input["사용자 입력"]
        A[StartInput<br/>주소/타입/세대수/이메일]
    end
    
    subgraph MainAgent["Main Agent"]
        B[main_agent.py<br/>워크플로우 조율]
    end
    
    subgraph AnalysisGraph["Analysis Graph - 7개 에이전트 병렬 실행"]
        C1[정책 분석<br/>policy_agent]
        C2[청약 FAQ<br/>housing_faq_agent]
        C3[입지 분석<br/>location_insight_agent]
        C4[주변 시장<br/>nearby_market_agent]
        C5[인구 분석<br/>population_insight_agent]
        C6[공급/수요<br/>supply_demand_agent]
        C7[미분양 분석<br/>unsold_insight_agent]
    end
    
    subgraph DataSources["데이터 소스"]
        D1[(PostgreSQL<br/>+ pgvector)]
        D2[외부 API<br/>Kakao/KOSTAT/ECOS]
        D3[웹 크롤링<br/>뉴스/청약정보]
        D4[AI 검색<br/>Gemini/Perplexity]
    end
    
    subgraph ReportAgent["보고서 작성 Agent"]
        E[jung_min_jae_agent.py<br/>4단계 세그먼트 작성]
    end
    
    subgraph Output["출력"]
        F1[최종보고서.pdf]
        F2[데이터출처모음.pdf]
        F3[원본 CSV 17개]
    end
    
    subgraph Delivery["전달"]
        G[Gmail API<br/>+ Google Drive]
    end

    subgraph Observability["Observability"]
        OBS[Langfuse<br/>토큰/비용 추적]
    end

    A --> B
    B --> C1 & C2 & C3 & C4 & C5 & C6 & C7
    C1 & C2 & C3 & C4 & C5 & C6 & C7 --> D1 & D2 & D3 & D4
    C1 & C2 & C3 & C4 & C5 & C6 & C7 --> E
    E --> F1 & F2 & F3
    F1 & F2 & F3 --> G
    B -.-> OBS
    E -.-> OBS
    D4 -.-> OBS

    style A fill:#e3f2fd,color:#000
    style B fill:#fff3e0,color:#000
    style E fill:#fff9c4,color:#000
    style G fill:#c8e6c9,color:#000
    style OBS fill:#f3e5f5,color:#000
```

### 1.2 기술 스택

| 구분 | 기술 | 버전 | 용도 |
|-----|------|-----|------|
| Language | Python | 3.12+ | 메인 언어 |
| Framework | FastAPI | 0.121.0+ | REST API 서버 |
| Agent Framework | LangGraph | 1.0.0+ | 멀티에이전트 오케스트레이션 |
| LLM Framework | LangChain | 1.0.3+ | LLM 통합 |
| Vector DB | PostgreSQL + pgvector | 14+ | RAG 벡터 검색 |
| LLM | OpenAI GPT-5-mini | - | 보고서 작성 |
| LLM | OpenAI GPT-5 | - | 분석 에이전트 |
| LLM | Google Gemini | - | 웹 검색 |
| PDF 생성 | WeasyPrint | 66.0+ | Markdown → PDF |
| 이메일 | Gmail API | - | 보고서 발송 |
| 파일 저장 | Google Drive API | - | CSV/PDF 업로드 |
| Observability | Langfuse | 3.x | 토큰/비용 추적 (Observability) |
| LLM 테스트 | DeepEval | 3.8.8+ | LLM 평가 테스트 프레임워크 |
| 웹 검색 | Tavily Search | - | 웹 검색 (청약경쟁률) |

### 1.3 외부 API 서비스

| 서비스 | 용도 | 사용 에이전트 |
|-------|------|-------------|
| Kakao Maps API | 좌표 변환, 거리 계산, 주변 시설 | 입지분석, 주변시장 |
| KOSTAT (통계청) | 인구 이동, 10년 노후 주택 | 인구분석, 공급/수요 |
| ECOS (한국은행) | 한국 금리 | 공급/수요 |
| FRED (미국 연준) | 미국 금리 | 공급/수요 |
| R-ONE (부동산원) | 매매수급지수 | 공급/수요 |
| 공공데이터포털 | 실거래가 조회 | 주변시장 |
| Perplexity AI | 실시간 웹 검색 | 정책, 입지, 주변시장, 공급/수요 |
| Google Gemini | AI 기반 검색 | 입지, 주변시장 |
| Langfuse Cloud | 토큰/비용 추적, 세션 관리 | 전체 (자동 주입) |
| Tavily Search API | 웹 검색 | 공급/수요 (청약경쟁률) |

### 1.4 포트 정보

| 서비스 | 포트 | 설명 |
|-------|------|------|
| FastAPI (Service) | 8080 | 메인 분석 API |
| FastAPI (Chatbot) | 8000 | 챗봇 API |
| PostgreSQL | 5432 | 벡터 DB |
| Streamlit | 8501 | 웹 UI |
<!-- SECTION:OVERVIEW:END -->

---

<!-- SECTION:DATA:START -->
## 2. 데이터 흐름 상세

### 2.1 사용자 입력 (StartInput)

```mermaid
classDiagram
    class StartInput {
        +target_area: str
        +main_type: str
        +email: str
        +total_units: str
        +policy_period: Optional[str]
        +policy_count: Optional[int]
        +policy_list: Optional[str]
        +brand: Optional[str]
        +orientation: Optional[str]
        +parking_ratio: Optional[float]
        +terrain_condition: Optional[str]
        +gross_area: Optional[float]
        +floor_area_ratio_range: Optional[float]
        +building_coverage_ratio_range: Optional[float]
    }
```

| 필드 | 타입 | 필수 | 설명 | 예시 |
|-----|------|-----|------|-----|
| target_area | string | O | 사업지 주소 | 서울특별시 강남구 역삼동 |
| main_type | string | O | 대표 타입 | 84제곱미터 |
| email | string | O | 보고서 수신 이메일 | user@example.com |
| total_units | string | O | 전체 세대수 | 1000세대 |
| policy_period | string | X | 분석할 정책 기간 | 최근 1년 |
| policy_count | int | X | 분석할 정책 개수 | 3 |
| policy_list | string | X | 특정 정책 리스트 | ['2025.10.15', '2025.06.27'] |

---

### 2.2 7개 분석 에이전트 데이터 흐름

<!-- DATA:AGENTS:START -->

#### 2.2.1 정책 분석 에이전트 (Policy Agent)

```mermaid
flowchart LR
    subgraph Input["입력"]
        I1[target_area]
        I2[policy_period]
        I3[policy_list]
    end
    
    subgraph DataCollection["데이터 수집 - 병렬"]
        D1[national_news<br/>국가 정책 RAG]
        D2[region_news<br/>지역 뉴스 크롤링]
        D3[policy_pdf_retrieve<br/>정책 PDF RAG]
    end
    
    subgraph Processing["처리"]
        P1[analysis_setting<br/>SEGMENT 01: 뉴스<br/>SEGMENT 02: comp.md 비교]
        P2[generate_initial_report<br/>초안 작성]
        P3[evaluate_completeness<br/>완성도 평가<br/>6점 검증]
        P4{is_complete?}
        P5[execute_retrieval<br/>추가 검색]
        P5b{blanks >= 3?}
        P5c[perplexity_search<br/>부족 정보 보완]
        P6[revise_report<br/>보고서 수정]
        LIMIT["MAX_ITERATIONS = 3<br/>무한 루프 방지"]
    end

    subgraph Output["출력"]
        O1[policy_output.result<br/>분석 보고서]
        O2[national_context<br/>국가 뉴스 원본]
        O3[region_context<br/>지역 뉴스 원본]
        O4[국가적_정책_모음.csv]
        O5[지역별_정책_모음.csv]
    end

    I1 & I2 & I3 --> D1 & D2 & D3
    D1 & D2 & D3 --> P1
    P1 --> P2 --> P3 --> P4
    P4 -->|No| P5
    P5 --> P5b
    P5b -->|Yes| P5c --> P6
    P5b -->|No| P6
    P6 --> P3
    P4 -->|Yes| O1
    LIMIT -.-> P4
    D1 --> O2 --> O4
    D2 --> O3 --> O5

    style I1 fill:#e3f2fd,color:#000
    style O1 fill:#c8e6c9,color:#000
    style O4 fill:#fff9c4,color:#000
    style O5 fill:#fff9c4,color:#000
    style LIMIT fill:#ffcdd2,color:#000
```

**프롬프트 구조:**
- **SEGMENT 01**: 국가 뉴스(`national_news`) + 지역 뉴스(`region_news`) 기반 정책 동향 분석
- **SEGMENT 02**: `comp.md` 전체 비교 (기존 정책 vs 신규 정책 차이점 비교표 작성)

**완성도 평가 6점 검증 항목:**
개요 / 목표 / 비교표 / 차이점 / 평가 / 전망

**데이터 소스:**
| 함수 | 소스 타입 | 설명 |
|------|----------|------|
| `national_policy_retrieve()` | RAG (pgvector) | 국가 정책 뉴스 벡터 검색 |
| `collect_articles_result()` | 웹 크롤링 | 지역 정책 기사 수집 |
| `PolicyPDFRetriever.hybrid_search()` | RAG (pgvector) | 정책 PDF 하이브리드 검색 |
| `perplexity_search()` | AI 웹 검색 | 부족한 정보 보완 (PDF 공백 >= 3건 시) |

**출력 구조:**
```python
policy_output = {
    "result": str,                    # LLM 분석 보고서
    "national_context": str,          # 국가 뉴스 원본
    "region_context": str,            # 지역 뉴스 원본
    "national_download_link": str,    # 국가 뉴스 CSV 링크
    "region_download_link": str,      # 지역 뉴스 CSV 링크
}
```

---

#### 2.2.2 청약 FAQ 에이전트 (Housing FAQ Agent)

```mermaid
flowchart LR
    subgraph Input["입력"]
        I1[target_area]
        I2[main_type]
        I3[total_units]
    end
    
    subgraph DataCollection["데이터 수집 - 병렬"]
        D1[get_rule_data<br/>주택공급규칙 RAG]
        D2[get_faq_data<br/>청약 FAQ RAG]
    end
    
    subgraph Processing["처리"]
        P1[analysis_setting<br/>프롬프트 구성]
        P2[call_llm<br/>LLM 분석]
    end
    
    subgraph Output["출력"]
        O1[housing_faq_output.result<br/>분석 보고서]
        O2[housing_faq_context<br/>FAQ 원본]
        O3[housing_rule_context<br/>규칙 원본]
        O4[주택청약FAQ.csv]
        O5[주택공급규칙.csv]
    end
    
    I1 & I2 & I3 --> D1 & D2
    D1 & D2 --> P1 --> P2 --> O1
    D1 --> O3 --> O5
    D2 --> O2 --> O4
    
    style I1 fill:#e3f2fd,color:#000
    style O1 fill:#c8e6c9,color:#000
    style O4 fill:#fff9c4,color:#000
    style O5 fill:#fff9c4,color:#000
```

**데이터 소스:**
| 함수 | 소스 타입 | 설명 |
|------|----------|------|
| `housing_rule_retrieve()` | RAG (pgvector) | 주택공급규칙 법령 검색 |
| `housing_faq_retrieve()` | RAG (pgvector) | 청약 FAQ Q&A 검색 |

**출력 구조:**
```python
housing_faq_output = {
    "result": str,                       # LLM 분석 보고서
    "housing_faq_context": list[str],    # FAQ 원본 리스트
    "housing_rule_context": list[str],   # 규칙 원본 리스트
    "housing_faq_download_link": str,    # FAQ CSV 링크
    "housing_rule_download_link": str,   # 규칙 CSV 링크
}
```

---

#### 2.2.3 입지 분석 에이전트 (Location Insight Agent)

```mermaid
flowchart LR
    subgraph Input["입력"]
        I1[target_area]
        I2[main_type]
        I3[total_units]
    end
    
    subgraph DataCollection["데이터 수집 - 순차"]
        D1[gemini_search<br/>지역 특징/호재]
        D2[kakao_api_distance<br/>주변 시설 거리]
    end
    
    subgraph Processing["처리"]
        P1[analysis_setting<br/>프롬프트 구성]
        P2[agent<br/>LLM 분석]
        P3{tool_calls?}
        P4[perplexity_search<br/>추가 검색]
    end
    
    subgraph Output["출력"]
        O1[location_insight_output.result<br/>분석 보고서]
        O2[kakao_api_distance_context<br/>시설 거리 원본]
        O3[입지분석_카카오.csv]
    end
    
    I1 & I2 & I3 --> D1 --> D2
    D2 --> P1 --> P2 --> P3
    P3 -->|Yes| P4 --> P2
    P3 -->|No| O1
    D2 --> O2 --> O3
    
    style I1 fill:#e3f2fd,color:#000
    style O1 fill:#c8e6c9,color:#000
    style O3 fill:#fff9c4,color:#000
```

**데이터 소스:**
| 함수 | 소스 타입 | 설명 |
|------|----------|------|
| `gemini_search()` | Google Gemini AI | 지역 특징, 주변 호재 검색 |
| `get_location_profile()` | Kakao Maps API | 주변 시설 좌표/거리 계산 |
| `perplexity_search()` | Perplexity AI | 추가 정보 검색 (선택적) |

**Kakao API 수집 카테고리:**
- 교통여건: 지하철역, 버스정류장
- 교육환경: 초등학교, 중학교, 고등학교, 학원
- 편의여건: 대형마트, 병원, 은행, 공원
- 자연환경: 하천, 산
- 미래가치: 개발 예정 지역

**출력 구조:**
```python
location_insight_output = {
    "result": str,                              # LLM 분석 보고서
    "gemini_search": str,                       # Gemini 검색 결과
    "kakao_api_distance_context": dict,         # 시설 거리 데이터
    "kakao_api_distance_download_link": str,    # CSV 링크
}
```

---

#### 2.2.4 주변 시장 에이전트 (Nearby Market Agent)

```mermaid
flowchart LR
    subgraph Input["입력"]
        I1[target_area]
        I2[main_type]
        I3[total_units]
    end
    
    subgraph DataCollection["데이터 수집"]
        D1[gemini_search<br/>주변 매매/분양 아파트 3+3개]
        D2[kakao_api_distance<br/>각 아파트 입지]
        D3[get_real_estate_price<br/>실거래가 조회]
        D4[perplexity_search<br/>분양가 검증]
    end
    
    subgraph Processing["처리"]
        P1[analysis_setting<br/>프롬프트 구성]
        P2[agent<br/>LLM 분석]
    end
    
    subgraph Output["출력"]
        O1[nearby_market_output.result<br/>분석 보고서]
        O2[kakao_api_distance_context<br/>주변 단지 정보]
        O3[주변단지_정보.csv]
    end
    
    I1 & I2 & I3 --> D1
    D1 --> D2 & D3 & D4
    D2 & D3 & D4 --> P1 --> P2 --> O1
    D2 --> O2 --> O3
    
    style I1 fill:#e3f2fd,color:#000
    style O1 fill:#c8e6c9,color:#000
    style O3 fill:#fff9c4,color:#000
```

**데이터 소스:**
| 함수 | 소스 타입 | 설명 |
|------|----------|------|
| `gemini_search()` | Google Gemini AI | 주변 매매 3개 + 분양 3개 아파트 검색 (Structured Output: `NearbyMarketGeminiSchema` → [2.4 참조](#24-structured-output-스키마)) |
| `get_location_profile()` | Kakao Maps API | 각 아파트 입지 정보 |
| `get_real_estate_price()` | 공공데이터포털 API | 매매아파트 실거래가 |
| `perplexity_search()` | Perplexity AI | 분양아파트 가격/경쟁률 검증 (Structured Output: `NearbyMarketPerplexitySchema` → [2.4 참조](#24-structured-output-스키마)) |

**수집 정보 (아파트당):**
- 매매아파트: 주소, 세대수, 타입, 평당매매가격, 준공연도, 거리, 주변호재
- 분양아파트: 주소, 세대수, 타입, 평당분양가격, 청약경쟁률, 청약일시, 계약조건, 거리

**출력 구조:**
```python
nearby_market_output = {
    "result": str,                              # LLM 분석 보고서
    "gemini_search": str,                       # Gemini 검색 결과 (JSON Schema 강제)
    "kakao_api_distance_context": list[dict],   # 6개 아파트 입지 정보
    "real_estate_price_context": list[dict],    # 매매 실거래가
    "perplexity_search": str,                   # 분양가 검증 결과
    "kakao_api_distance_download_link": str,    # CSV 링크
}
```

---

#### 2.2.5 인구 분석 에이전트 (Population Insight Agent)

```mermaid
flowchart LR
    subgraph Input["입력"]
        I1[target_area]
    end
    
    subgraph DataCollection["데이터 수집 - 병렬"]
        D1[age_population<br/>연령별 인구 RAG]
        D2[move_population<br/>인구 이동 KOSTAT]
    end
    
    subgraph Processing["처리"]
        P1[analysis_setting<br/>프롬프트 구성]
        P2[agent<br/>LLM 분석]
        P3{tool_calls?}
        P4[think_tool<br/>자체 검증]
    end
    
    subgraph Output["출력"]
        O1[population_insight_output.result<br/>분석 보고서]
        O2[age_population_context<br/>연령 인구 원본]
        O3[move_population_context<br/>이동 인구 원본]
        O4[연령층분포.csv]
        O5[인구이동.csv]
    end
    
    I1 --> D1 & D2
    D1 & D2 --> P1 --> P2 --> P3
    P3 -->|Yes| P4 --> P2
    P3 -->|No| O1
    D1 --> O2 --> O4
    D2 --> O3 --> O5
    
    style I1 fill:#e3f2fd,color:#000
    style O1 fill:#c8e6c9,color:#000
    style O4 fill:#fff9c4,color:#000
    style O5 fill:#fff9c4,color:#000
```

**데이터 소스:**
| 함수 | 소스 타입 | 설명 |
|------|----------|------|
| `age_population_retrieve()` | RAG (pgvector) | 연령별 인구 분포 (월별) |
| `get_move_population()` | KOSTAT API | 지역간 인구 이동 통계 |

**출력 구조:**
```python
population_insight_output = {
    "result": str,                            # LLM 분석 보고서
    "age_population_context": str,            # 연령별 인구 원본
    "move_population_context": list[dict],    # 인구 이동 원본
    "age_population_download_link": str,      # 연령 CSV 링크
    "move_population_download_link": str,     # 이동 CSV 링크
}
```

---

#### 2.2.6 공급/수요 분석 에이전트 (Supply Demand Agent)

```mermaid
flowchart TB
    subgraph Input["입력"]
        I1[target_area]
    end
    
    subgraph DataCollection["데이터 수집 - 9개 병렬"]
        D1[pre_promise_competition<br/>청약 경쟁률]
        D2[year10_after_house<br/>10년 이상 노후]
        D3[sale_and_jeonse_price<br/>매매/전세가]
        D4[trade_balance<br/>매매수급지수]
        D5[planning_move<br/>입주 예정]
        D6[housing_sales_volume<br/>매매 거래량]
        D7[use_kor_rate<br/>한미 금리]
        D8[get_home_mortgage<br/>주택담보금리]
        D9[get_gdp_and_grdp<br/>GDP/GRDP]
    end
    
    subgraph Processing["처리"]
        P1[analysis_setting<br/>프롬프트 구성]
        P2[agent<br/>LLM 분석]
    end
    
    subgraph Output["출력"]
        O1[supply_demand_output.result<br/>분석 보고서]
        O2[11개 원본 데이터 + 8개 CSV]
    end
    
    I1 --> D1 & D2 & D3 & D4 & D5 & D6 & D7 & D8 & D9
    D1 & D2 & D3 & D4 & D5 & D6 & D7 & D8 & D9 --> P1
    P1 --> P2 --> O1
    D1 & D2 & D3 & D4 & D5 & D6 & D7 & D8 & D9 --> O2
    
    style I1 fill:#e3f2fd,color:#000
    style O1 fill:#c8e6c9,color:#000
```

**데이터 소스 (9개 병렬):**
| 함수 | 소스 타입 | 설명 | CSV 파일 |
|------|----------|------|---------|
| `pre_promise()` | 웹 크롤링 | 청약 경쟁률 | `{주소}_청약경쟁률.csv` |
| `get_10_year_after_house()` | KOSTAT API | 10년 이상 노후 주택 | - |
| `sale_price_retrieve()` | RAG (pgvector) | 매매가격 시계열 | `{구}_월별_매매가격.csv` |
| `jeonse_price_retrieve()` | RAG (pgvector) | 전세가격 시계열 | `{구}_월별_전세가격.csv` |
| `get_trade_balance()` | R-ONE API | 매매수급지수 | - |
| `planning_move_retrieve()` | RAG (pgvector) | 입주 예정 단지 | `{주소}_입주예정단지.csv` |
| `housing_sales_volume_retrieve()` | RAG (pgvector) | 매매 거래량 | `{주소}_매매수급지수.csv` |
| `get_rate()` | ECOS/FRED API | 한미 금리 비교 | `미국_한국_금리.csv` |
| `home_mortgage_retrieve()` | RAG (pgvector) | 주택담보대출 금리 | `주택담보대출.csv` |
| `get_one_people_gdp()` | KOSTAT API | 1인당 GDP | `{주소}_GDP_와_GRDP.csv` |
| `one_people_grdp_retrieve()` | RAG (pgvector) | 1인당 GRDP | (위와 병합) |

**출력 구조:**
```python
supply_demand_output = {
    "result": str,                                 # LLM 분석 보고서
    "year10_after_house": str,                     # 10년 노후 원본
    "jeonse_price": str,                           # 전세가 원본
    "sale_price": str,                             # 매매가 원본
    "trade_balance": str,                          # 수급지수 원본
    "use_kor_rate": list[dict],                    # 한미 금리 원본
    "home_mortgage": list[str],                    # 담보금리 원본
    "one_people_gdp": dict,                        # GDP 원본
    "one_people_grdp": str,                        # GRDP 원본
    "housing_sales_volume": list[str],             # 거래량 원본
    "planning_move": list[dict],                   # 입주예정 원본
    "pre_pomise_competition": list[dict],          # 경쟁률 원본
    # + 8개 download_link
}
```

---

#### 2.2.7 미분양 분석 에이전트 (Unsold Insight Agent)

```mermaid
flowchart LR
    subgraph Input["입력"]
        I1[target_area]
    end
    
    subgraph DataCollection["데이터 수집"]
        D1[unsold_units<br/>미분양 현황 RAG<br/>pgvector 벡터 검색]
    end
    
    subgraph Processing["처리"]
        P1[analysis_setting<br/>프롬프트 구성]
        P2[agent<br/>LLM 분석]
        P3{tool_calls?}
        P4[think_tool<br/>자체 검증]
    end
    
    subgraph Output["출력"]
        O1[unsold_insight_output.result<br/>분석 보고서]
        O2[unsold_unit<br/>미분양 원본]
        O3[미분양.csv]
    end
    
    I1 --> D1 --> P1 --> P2 --> P3
    P3 -->|Yes| P4 --> P2
    P3 -->|No| O1
    D1 --> O2 --> O3
    
    style I1 fill:#e3f2fd,color:#000
    style O1 fill:#c8e6c9,color:#000
    style O3 fill:#fff9c4,color:#000
```

**데이터 소스:**
| 함수 | 소스 타입 | 설명 |
|------|----------|------|
| `unsold_units()` | RAG (pgvector) | 시군구별 미분양 현황 (월별, `unsold_housing_indexer.py`로 사전 벡터 인덱싱) |

**출력 구조:**
```python
unsold_insight_output = {
    "result": str,                       # LLM 분석 보고서
    "unsold_unit": list[dict],           # 미분양 원본 데이터
    "unsold_unit_download_link": str,    # CSV 링크
}
```

<!-- DATA:AGENTS:END -->

---

### 2.3 Structured Output 스키마

`src/agents/state/structured_schemas.py`에서 관리되는 Pydantic 스키마입니다.
LLM이 자유 텍스트(마크다운+설명)를 반환하면 `json.loads()` 파싱이 실패할 수 있으므로, API 레벨에서 JSON 형식을 강제하여 파싱 실패율을 0%로 만듭니다.

| 스키마 | 사용 에이전트 | 대상 API | 용도 |
|-------|-------------|---------|------|
| `NearbyMarketGeminiSchema` | 주변시장 | Gemini | 매매 3 + 분양 3 아파트 (세대수/타입/평당가/준공연도/거리) |
| `LocationInsightGeminiSchema` | 입지분석 | Gemini | 지역특징 + 주변호재 리스트 |
| `NearbyMarketPerplexitySchema` | 주변시장 | Perplexity | 분양아파트 검증 (가격/조건/경쟁률) |
| `CompetitionItem` / `PrePromiseCompetitionResult` | 공급/수요 | Tavily + LLM | 청약경쟁률 파싱 (주소/공고일/경쟁률) |
| `HousingRuleItem` / `HousingRuleList` | 청약FAQ | LLM (CSV 변환) | 주택공급규칙 요약 (조문명/핵심요약/주요조건) |
| `MovePopulationQuery` | 인구분석 | LLM (Text-to-SQL) | SQL 컬럼명 강제 (year/origin/destination/total) |

**Structured Output 적용 흐름:**

```mermaid
flowchart LR
    A[사용자 질의] --> B[LLM 호출<br/>+ Pydantic Schema]
    B --> C{JSON 유효?}
    C -->|Yes| D[json.loads 성공<br/>후속 노드 정상 처리]
    C -->|No| E[API 레벨에서<br/>재시도/에러 반환]

    style A fill:#e3f2fd,color:#000
    style D fill:#c8e6c9,color:#000
    style E fill:#ffcdd2,color:#000
```

> **스키마가 없을 경우:** Gemini가 `"주변에는 래미안 아파트가 있고..."` 같은 자연어를 반환 → 후속 노드에서 `json.loads()` 실패 → 에이전트 전체 크래시

---

### 2.4 데이터 유형 분류

| 유형 | 설명 | 예시 |
|-----|------|------|
| **RAG 원본** | pgvector에서 벡터 검색으로 가져온 원본 | 청약 FAQ, 주택공급규칙, 매매가격 |
| **API 원본** | 외부 API에서 직접 조회한 원본 | Kakao 시설 거리, KOSTAT 인구 이동 |
| **크롤링 원본** | 웹에서 수집한 원본 | 정책 뉴스, 청약 경쟁률 |
| **AI 검색 원본** | LLM 기반 검색 결과 | Gemini/Perplexity 검색 결과 |
| **LLM 분석** | 에이전트가 원본을 분석한 결과 | `output.result` |
| **LLM 요약** | 원본을 LLM으로 요약/정제한 것 | 주택공급규칙 요약 |

<!-- SECTION:DATA:END -->

---

<!-- SECTION:FLOW:START -->
## 3. 메인 워크플로우

### 3.1 전체 파이프라인

```mermaid
flowchart TB
    subgraph Phase1["Phase 1: 시작"]
        A[StartInput 수신] --> B[start 노드<br/>상태 초기화]
    end
    
    subgraph Phase2["Phase 2: 병렬 분석"]
        B --> C[analysis_graph_node]
        C --> D1[policy_agent] & D2[housing_faq_agent] & D3[location_insight_agent]
        C --> D4[nearby_market_agent] & D5[population_insight_agent]
        C --> D6[supply_demand_agent] & D7[unsold_insight_agent]
        D1 & D2 & D3 & D4 & D5 & D6 & D7 --> E[join_results<br/>7개 결과 병합]
    end
    
    subgraph Phase3["Phase 3: 보고서 작성"]
        E --> F[jung_min_jae_graph]
        F --> G1[Segment 1 작성] --> G2[Segment 2 작성]
        G2 --> G3[Segment 3 작성] --> G4[Segment 4 작성]
        G4 --> H[finalize_merge<br/>세그먼트 병합]
        H --> I[reflection_prompt<br/>자체 검증 준비]
        I --> J[reflect_agent<br/>think_tool 호출]
        J --> K[apply_reflection<br/>피드백 반영]
    end
    
    subgraph Phase4["Phase 4: 파일 생성 및 발송"]
        K --> L[final_node]
        L --> M1[최종보고서.pdf 생성]
        L --> M2[데이터출처모음.pdf 생성]
        L --> M3[Google Drive 업로드]
        M1 & M2 & M3 --> N[Gmail 발송]
    end
    
    N --> O[완료]
    
    style A fill:#e3f2fd,color:#000
    style E fill:#fff3e0,color:#000
    style K fill:#fff9c4,color:#000
    style O fill:#c8e6c9,color:#000
```

### 3.2 상태 전이

```mermaid
stateDiagram-v2
    [*] --> START_CONFIRMATION: 시작
    START_CONFIRMATION --> ANALYSIS: start()
    ANALYSIS --> JUNG_MIN_JAE: analysis_graph_node()
    JUNG_MIN_JAE --> RENDERING: jung_min_jae_graph()
    RENDERING --> DONE: final_node()
    DONE --> [*]: 완료
    
    note right of ANALYSIS: 7개 에이전트 병렬 실행
    note right of JUNG_MIN_JAE: 4단계 세그먼트 작성
    note right of RENDERING: PDF 생성 + 이메일 발송
```

### 3.3 보고서 작성 에이전트 (Jung Min Jae) 상세

```mermaid
flowchart TB
    subgraph Input["입력"]
        I1[start_input<br/>사용자 입력]
        I2[analysis_outputs<br/>7개 에이전트 결과]
    end
    
    subgraph Segments["4단계 세그먼트 작성"]
        S1[Segment 1<br/>개요/입지/정책]
        S2[Segment 2<br/>공급수요/미분양]
        S3[Segment 3<br/>인구/주변시장]
        S4[Segment 4<br/>종합평가/결론]
    end
    
    subgraph Loop["세그먼트 루프"]
        L1[retreiver<br/>RAG 컨텍스트]
        L2[reporting<br/>프롬프트 구성]
        L3[agent<br/>LLM 작성]
        L4{seg <= 4?}
    end
    
    subgraph Merge["병합 및 검증"]
        M1[finalize_merge<br/>4개 세그먼트 병합]
        M2[reflection_prompt<br/>검증 프롬프트]
        M3[reflect_agent<br/>think_tool 호출]
        M4[apply_reflection<br/>피드백 반영]
    end
    
    subgraph Output["출력"]
        O1[final_report<br/>최종 보고서 Markdown]
    end
    
    I1 & I2 --> L1 --> L2 --> L3 --> L4
    L4 -->|Yes| S1 --> S2 --> S3 --> S4
    S4 --> L4
    L4 -->|No| M1 --> M2 --> M3 --> M4 --> O1
    
    style I1 fill:#e3f2fd,color:#000
    style I2 fill:#e3f2fd,color:#000
    style O1 fill:#c8e6c9,color:#000
```

**세그먼트별 내용:**
| 세그먼트 | 포함 내용 | 참조 에이전트 |
|---------|---------|-------------|
| Segment 1 | 개요, 입지 분석, 정책 동향 | location_insight, policy |
| Segment 2 | 공급/수요 분석, 미분양 현황 | supply_demand, unsold_insight |
| Segment 3 | 인구 분석, 주변 시장 비교 | population_insight, nearby_market |
| Segment 4 | 청약 조건, 종합 평가, 결론 | housing_faq, 전체 |

**조건부 컨텍스트 주입 (토큰 폭발 방지):**

세그먼트가 4번 반복되면서 기초자료(수만 토큰)가 매번 누적되면 `ContextOverflowError`가 발생합니다 (1턴 7만 → 4턴 28만 토큰). 이를 방지하기 위해:

- **seg == 1**: `SystemMessage` + 7개 에이전트 결과 전체를 `HumanMessage`로 주입 (최초 1회만)
- **seg >= 2**: 이전 메시지 기억(Attention)을 활용하여, 짧은 **세그먼트 작성 지시서**만 `HumanMessage`로 추가

> LLM의 Attention 메커니즘이 이전 대화를 기억하므로, 기초자료를 다시 넣을 필요가 없습니다.

**think_tool 자체 검증 (5점 체크리스트):**

보고서 병합 후 `reflect_agent`가 `think_tool`을 호출하여 아래 5개 항목을 검증합니다:

| # | 검증 항목 |
|---|----------|
| 1 | 각 페이지 시작부에 핵심 인사이트의 근거가 명확한가 |
| 2 | 근거로 사용할 데이터를 명확하게 표기했는가 |
| 3 | 근거로 사용할 데이터는 정확한 데이터인가 |
| 4 | 비교분석에 정책/경제지표/공급수요/미분양/인구 등을 종합했는가 |
| 5 | 최종 보고서 양식을 벗어난 불필요한 말을 하지 않았는가 |

<!-- SECTION:FLOW:END -->

---

<!-- SECTION:EMAIL:START -->
## 4. 플로우 다이어그램

### 4.1 분석 그래프 병렬 실행 구조

```mermaid
flowchart TB
    subgraph START["시작"]
        S[start_input]
    end
    
    subgraph PARALLEL["병렬 실행 (7개 에이전트)"]
        direction TB
        P1[policy_graph]
        P2[housing_faq_graph]
        P3[location_insight_graph]
        P4[nearby_market_graph]
        P5[population_insight_graph]
        P6[supply_demand_graph]
        P7[unsold_insight_graph]
    end
    
    subgraph JOIN["결과 병합"]
        J[join_results]
    end
    
    subgraph OUTPUT["출력"]
        O[analysis_outputs]
    end
    
    S --> P1 & P2 & P3 & P4 & P5 & P6 & P7
    P1 & P2 & P3 & P4 & P5 & P6 & P7 --> J
    J --> O
    
    style S fill:#e3f2fd,color:#000
    style J fill:#fff3e0,color:#000
    style O fill:#c8e6c9,color:#000
```

### 4.2 PDF 생성 및 이메일 발송 흐름

```mermaid
flowchart TB
    subgraph Input["입력"]
        I1[final_report<br/>최종 보고서 Markdown]
        I2[source_page<br/>출처 페이지 Markdown]
        I3[drive_links<br/>15개 CSV 링크]
    end
    
    subgraph PDFGeneration["PDF 생성 (WeasyPrint)"]
        P1[markdown_to_pdf<br/>최종보고서.pdf]
        P2[markdown_to_pdf<br/>데이터출처모음.pdf]
    end
    
    subgraph DriveUpload["Google Drive 업로드"]
        D1[upload_to_drive<br/>최종보고서.pdf]
        D2[upload_to_drive<br/>데이터출처모음.pdf]
    end
    
    subgraph EmailCompose["이메일 구성"]
        E1[HTML 본문 생성]
        E2[PDF 링크 포함]
        E3[CSV 링크 15개 포함]
    end
    
    subgraph Send["발송"]
        S[Gmail API<br/>send_gmail]
    end
    
    I1 --> P1 --> D1 --> E2
    I2 --> P2 --> D2 --> E2
    I3 --> E3
    E2 & E3 --> E1 --> S
    
    style I1 fill:#e3f2fd,color:#000
    style S fill:#c8e6c9,color:#000
```

<!-- SECTION:EMAIL:END -->

---

<!-- SECTION:DELIVERY:START -->
## 5. 이메일 발송

### 5.1 이메일 발송 흐름

```mermaid
sequenceDiagram
    participant F as final_node
    participant M as markdown_to_pdf
    participant D as Google Drive
    participant G as Gmail API
    participant U as 사용자
    
    F->>M: 최종보고서 Markdown
    M->>M: WeasyPrint 변환
    M->>D: PDF 업로드
    D-->>F: 공유 링크 반환
    
    F->>M: 출처페이지 Markdown
    M->>M: WeasyPrint 변환
    M->>D: PDF 업로드
    D-->>F: 공유 링크 반환
    
    F->>G: HTML 이메일 + 링크들
    G->>U: 이메일 수신
    U->>D: 링크 클릭하여 파일 다운로드
```

### 5.2 이메일에 포함되는 파일 목록

#### PDF 파일 (2개) - LLM 작성 보고서

| 파일명 | 내용 | 데이터 유형 |
|-------|------|-----------|
| `{제목}_최종보고서.pdf` | 7개 에이전트 분석 결과를 종합한 최종 분양성 검토 보고서 | **LLM 분석** |
| `{제목}__데이터출처모음.pdf` | 보고서에 사용된 데이터의 출처 및 원본 링크 모음 | **LLM 요약** |

#### CSV 파일 (15개) - 원본 데이터

<!-- EMAIL:FILES:START -->

**청약 FAQ (2개)**
| 파일명 | 데이터 유형 | 출처 |
|-------|-----------|------|
| `주택청약FAQ_temp.csv` | RAG 원본 | pgvector 벡터 검색 |
| `주택공급규칙_temp.csv` | RAG 원본 + LLM 요약 | pgvector + GPT 요약 |

**입지 분석 (1개)**
| 파일명 | 데이터 유형 | 출처 |
|-------|-----------|------|
| `{주소}_입지분석_카카오_temp.csv` | API 원본 | Kakao Maps API |

**주변 시장 (1개)**
| 파일명 | 데이터 유형 | 출처 |
|-------|-----------|------|
| `{주소}_주변단지_정보_temp.csv` | API + AI 원본 | Kakao API + Gemini |

**정책 (2개)**
| 파일명 | 데이터 유형 | 출처 |
|-------|-----------|------|
| `국가적_정책_모음_temp.csv` | RAG 원본 | pgvector 벡터 검색 |
| `지역별_정책_모음_temp.csv` | 크롤링 원본 | 웹 크롤링 |

**미분양 (1개)**
| 파일명 | 데이터 유형 | 출처 |
|-------|-----------|------|
| `{주소}_미분양_temp.csv` | RAG 원본 | pgvector 벡터 검색 |

**인구 분석 (2개)**
| 파일명 | 데이터 유형 | 출처 |
|-------|-----------|------|
| `{주소}_인구이동_temp.csv` | API 원본 | KOSTAT API |
| `{주소}_연령층분포_temp.csv` | RAG 원본 | pgvector 벡터 검색 |

**공급/수요 (6개)**
| 파일명 | 데이터 유형 | 출처 |
|-------|-----------|------|
| `주택담보대출_temp.csv` | RAG 원본 | pgvector 벡터 검색 |
| `미국_한국_금리_temp.csv` | API 원본 | ECOS + FRED API |
| `{주소}_GDP_와_GRDP_temp.csv` | API + RAG 원본 | KOSTAT API + pgvector |
| `{주소}_입주예정단지_temp.csv` | RAG 원본 | pgvector 벡터 검색 |
| `{주소}_매매수급지수_temp.csv` | RAG 원본 | pgvector 벡터 검색 |
| `{구}_월별_전세가격_temp.csv` | RAG 원본 | pgvector 벡터 검색 |
| `{구}_월별_매매가격_temp.csv` | RAG 원본 | pgvector 벡터 검색 |
| `{주소}_청약경쟁률_temp.csv` | 크롤링 원본 | 웹 크롤링 |

<!-- EMAIL:FILES:END -->

### 5.3 이메일 HTML 구조

```html
<html>
  <body>
    <h2>{사업지} {타입} {세대수} 사업보고서</h2>
    <p>내부 분석 보고서가 완료되었습니다.</p>
    
    <!-- PDF 링크 -->
    <ul>
      <li><a href="{drive_link}">최종보고서.pdf</a></li>
      <li><a href="{drive_link}">데이터출처모음.pdf</a></li>
    </ul>
    
    <hr/>
    
    <!-- 원본 데이터 링크 (15개) -->
    <h4>데이터 다운로드 링크</h4>
    <ul>
      <li><a href="{link}">주택청약 FAQ</a></li>
      <li><a href="{link}">주택공급 규칙</a></li>
      <li><a href="{link}">입지분석 (카카오 API 거리데이터)</a></li>
      <!-- ... 12개 더 -->
    </ul>
    
    <hr/>
    <p>부동산 마케팅 협회 자동화 리포트 시스템 (RAG_COMMANDER)</p>
  </body>
</html>
```

### 5.4 데이터 분류 요약

```mermaid
pie title 이메일 첨부 파일 데이터 유형 분포
    "RAG 원본" : 9
    "API 원본" : 3
    "크롤링 원본" : 2
    "LLM 분석/요약" : 3
```

| 데이터 유형 | 개수 | 설명 |
|-----------|-----|------|
| RAG 원본 | 9개 | pgvector 벡터 검색으로 가져온 원본 |
| API 원본 | 3개 | 외부 API 직접 조회 결과 |
| 크롤링 원본 | 2개 | 웹에서 수집한 원본 |
| LLM 분석/요약 | 3개 | 최종보고서, 출처페이지, 규칙요약 |

### 5.5 7개 에이전트 데이터 출처

> 이메일 첨부 파일(5.2)과는 별개로, 각 분석 에이전트가 보고서 작성을 위해 **실시간으로 수집하는 데이터의 원천**을 정리합니다.

<!-- AGENT:DATA_SOURCES:START -->

#### 1. Policy Agent (정책분석) - 데이터 출처 5개

| # | 데이터 수집 함수 | Tool / Retriever | 주요 데이터 출처 | 데이터 유형 |
|---|---|---|---|---|
| 1 | `national_news()` | `national_policy_retrieve()` | 로컬 CSV (`src/data/policy_factors/국토교통부_부동산정책(2024~2025).csv`) | 국토교통부 정책 기사 |
| 2 | `region_news()` | `collect_articles_result()` | 웹 크롤링 (`https://housing-post.com`) | 지역 부동산 정책 기사 |
| 3 | `policy_pdf_retrieve()` | `PolicyPDFRetriever.hybrid_search()` | Supabase PGVector (collection: `policy_documents`) | 정책 보도자료 PDF 문서 |
| 4 | ReAct 루프 내 Tool | `perplexity_search()` | Perplexity API (model: `sonar-reasoning-pro`) | 실시간 웹 검색 보충 |
| 5 | ReAct 루프 내 Tool | `think_tool()` | 없음 (내부 Reflection) | 내부 검증 메모 |

> 부수적 Tool: `perplexity_search` - 주요 출처는 Perplexity AI API (실시간 웹 인덱스 기반 검색)

#### 2. Housing FAQ Agent (청약분석) - 데이터 출처 2개

| # | 데이터 수집 함수 | Tool / Retriever | 주요 데이터 출처 | 데이터 유형 |
|---|---|---|---|---|
| 1 | `get_rule_data()` | `housing_rule_retrieve()` | Supabase PGVector (collection: `HOUSING_RULE`) | 주택공급규칙 문서 |
| 2 | `get_faq_data()` | `housing_faq_retrieve()` | Supabase PGVector (collection: `HOUSING_FAQ`) | 청약 FAQ 질의응답 |

> 부수적 Tool: 없음 (RAG 전용, 외부 API 미사용)

#### 3. Location Insight Agent (입지분석) - 데이터 출처 3개

| # | 데이터 수집 함수 | Tool / Retriever | 주요 데이터 출처 | 데이터 유형 |
|---|---|---|---|---|
| 1 | `gemini_search_tool()` | `gemini_search()` | Google Gemini API (model: `gemini-2.5-pro`, Structured Output) | 지역 특징 + 주변 호재 |
| 2 | `kakao_api_distance_tool()` | `get_location_profile()` | Kakao Local API (주소→좌표, 카테고리 검색: 학교/학원/교통/마트/병원/공원) | 입지 프로필 + 거리 |
| 3 | ReAct 루프 내 Tool | `perplexity_search()` | Perplexity API (model: `sonar-reasoning-pro`) | 호재 검증 보충 |

> 부수적 Tool: `perplexity_search` - 주요 출처는 Perplexity AI API

#### 4. Nearby Market Agent (주변시세분석) - 데이터 출처 4개

| # | 데이터 수집 함수 | Tool / Retriever | 주요 데이터 출처 | 데이터 유형 |
|---|---|---|---|---|
| 1 | `gemini_search_tool()` | `gemini_search()` | Google Gemini API (model: `gemini-2.5-pro`, Structured Output) | 매매아파트 3개 + 분양아파트 3개 |
| 2 | `kakao_api_distance_tool()` | `get_location_profile()` | Kakao Local API | 아파트별 좌표 + 사업지 거리 |
| 3 | `get_real_estate_price_tool()` | `get_real_estate_price()` | 공공데이터포털 API (`apis.data.go.kr/1613000/RTMSDataSvcAptTrade`) | 아파트 실거래가 |
| 4 | `perplexity_search_tool()` | `perplexity_search_structured()` | Perplexity API (Structured Output) | 분양아파트 최신 분양가 검증 |

> 부수적 Tool (ReAct 루프): `perplexity_search`, `get_real_estate_price`, `get_location_profile` - ReAct 시 추가 호출 가능

#### 5. Supply Demand Agent (공급수요분석) - 데이터 출처 11개

| # | 데이터 수집 함수 | Tool / Retriever | 주요 데이터 출처 | 데이터 유형 |
|---|---|---|---|---|
| 1 | `year10_after_house()` | `get_10_year_after_house()` | 통계청 SGIS API (`sgisapi.kostat.go.kr/OpenAPI3/stats/house.json`) | 10년 이상 노후주택 수 |
| 2 | `pre_promise_competition()` | `pre_promise()` → `tavily_search()` | Tavily 웹 검색 API (depth: advanced) | 청약 경쟁률 |
| 3 | `sale_and_jeonse_price_ratio()` | `sale_price_retrieve()` | Supabase PGVector (collection: 매매가격) | 매매가격 시계열 |
| 4 | `sale_and_jeonse_price_ratio()` | `jeonse_price_retrieve()` | Supabase PGVector (collection: 전세가격) | 전세가격 시계열 |
| 5 | `trade_balance()` | `get_trade_balance()` | R-ONE API (한국부동산원, `reb.or.kr/r-one/openapi`) | 매매수급지수 |
| 6 | `planning_move()` | `planning_move_retrieve()` | Supabase PGVector (collection: `PLANNING_MOVE_KEY`) | 입주예정 단지 물량 |
| 7 | `housing_sales_volume()` | `housing_sales_volume_retrieve()` | Supabase PGVector (collection: 매매거래량) | 매매 거래량 시계열 |
| 8 | `use_kor_rate()` | `get_rate()` | FRED API (`api.stlouisfed.org`) + 한국은행 ECOS API (`ecos.bok.or.kr`) | 한미 기준금리 비교 |
| 9 | `get_home_mortgage()` | `home_mortgage_retrieve()` | Supabase PGVector (collection: 주택담보대출) | 주택담보대출 금리 시계열 |
| 10 | `get_gdp_and_grdp()` | `get_one_people_gdp()` | 하드코딩 데이터 (출처: 우리은행 환율 + 세계은행 GDP 통계) | 1인당 GDP (원화 환산) |
| 11 | `get_gdp_and_grdp()` | `one_people_grdp_retrieve()` | Supabase PGVector + 로컬 CSV (`src/data/economic_metrics/서울 자치구별 GRDP.csv`) | 1인당 GRDP |

> 부수적 Tool: `think_tool` - 내부 Reflection 전용 (데이터 출처 없음)

#### 6. Population Insight Agent (인구분석) - 데이터 출처 2개

| # | 데이터 수집 함수 | Tool / Retriever | 주요 데이터 출처 | 데이터 유형 |
|---|---|---|---|---|
| 1 | `age_population()` | `age_population_retrieve()` | Supabase PGVector (collection: `AGE_POPULATION`) - 원본: 로컬 CSV `src/data/population_insight/202504_202509_연령별인구현황_월간.csv` | 연령별 인구 분포 |
| 2 | `move_population()` | `get_move_population()` | PostgreSQL 직접 쿼리 (table: `age_population`, Text-to-SQL) - 원본: 로컬 Excel `인구이동_전출입_2024~2025.xlsx` | 인구 전출입 통계 |

> 부수적 Tool: `think_tool` - 내부 Reflection 전용

#### 7. Unsold Insight Agent (미분양분석) - 데이터 출처 1개

| # | 데이터 수집 함수 | Tool / Retriever | 주요 데이터 출처 | 데이터 유형 |
|---|---|---|---|---|
| 1 | `get_unsold_unit()` | `unsold_units()` | Supabase PGVector (collection: `UNSOLD_HOUSING_KEY`, similarity_search k=50) | 미분양 현황 시계열 |

> 부수적 Tool: `think_tool` - 내부 Reflection 전용

#### 에이전트별 데이터 출처 총 갯수

| 에이전트 | 주요 데이터 출처 수 | 부수적 Tool 출처 |
|---|:---:|---|
| 1. Policy Agent (정책분석) | **5** | Perplexity API |
| 2. Housing FAQ Agent (청약분석) | **2** | 없음 |
| 3. Location Insight Agent (입지분석) | **3** | Perplexity API |
| 4. Nearby Market Agent (주변시세분석) | **4** | Perplexity API, 공공데이터포털, Kakao API |
| 5. Supply Demand Agent (공급수요분석) | **11** | 없음 (think_tool만) |
| 6. Population Insight Agent (인구분석) | **2** | 없음 (think_tool만) |
| 7. Unsold Insight Agent (미분양분석) | **1** | 없음 (think_tool만) |
| **합계** | **28** | |

#### 데이터 출처 유형별 분류 (고유 14종류)

| 출처 유형 | 세부 출처 | 사용하는 에이전트 |
|---|---|---|
| Supabase PGVector (RAG) | 10개 collection (policy_documents, HOUSING_RULE, HOUSING_FAQ, AGE_POPULATION, UNSOLD_HOUSING, 매매가격, 전세가격, 주택담보대출, 매매거래량, GRDP, PLANNING_MOVE) | Policy, Housing FAQ, Supply Demand, Population, Unsold |
| PostgreSQL 직접 쿼리 | age_population 테이블 (Text-to-SQL) | Population |
| Google Gemini API | gemini-2.5-pro (Structured Output) | Location, Nearby Market |
| Perplexity API | sonar-reasoning-pro | Policy, Location, Nearby Market |
| Kakao Local API | 주소→좌표, 카테고리/키워드 검색 | Location, Nearby Market |
| 공공데이터포털 API | 실거래가 API (RTMSDataSvcAptTrade) | Nearby Market |
| 통계청 SGIS API | 노후주택 통계 | Supply Demand |
| R-ONE API (한국부동산원) | 매매수급지수 | Supply Demand |
| FRED API (미국 연준) | 미국 기준금리 | Supply Demand |
| 한국은행 ECOS API | 한국 기준금리 | Supply Demand |
| Tavily 웹 검색 API | 청약 경쟁률 검색 | Supply Demand |
| 웹 크롤링 | housing-post.com (BeautifulSoup) | Policy |
| 로컬 CSV/Excel | 정책 CSV, 인구이동 Excel, GRDP CSV | Policy, Population, Supply Demand |
| 하드코딩 데이터 | 1인당 GDP (환율 x 달러 GDP) | Supply Demand |

<!-- AGENT:DATA_SOURCES:END -->

<!-- SECTION:DELIVERY:END -->

---

<!-- SECTION:APPENDIX:START -->
## 6. 부록

### A. 환경 변수

<!-- APPENDIX:ENV:START -->

#### 필수 환경 변수

| 변수명 | 설명 | 예시 |
|-------|------|------|
| `POSTGRES_URL` | PostgreSQL 연결 문자열 | `postgresql://postgres:postgres@localhost:5432/ragdb` |
| `OPENAI_API_KEY` | OpenAI API 키 | `sk-proj-...` |
| `ANTHROPIC_API_KEY` | Anthropic API 키 | `sk-ant-...` |
| `GEMINI_API_KEY` | Google Gemini API 키 | `AIza...` |

#### 검색 서비스

| 변수명 | 설명 | 용도 |
|-------|------|------|
| `TAVILY_API_KEY` | Tavily 검색 API | 웹 검색 |
| `PERPLEXITY_API_KEY` | Perplexity AI API | AI 웹 검색 |

#### 한국 부동산 API

| 변수명 | 설명 | 용도 |
|-------|------|------|
| `R_ONE_API_KEY` | 부동산원 API | 매매수급지수 |
| `MOLIT_API_KEY` | 국토교통부 API | 실거래가 |
| `REAL_TIME_SALE_SEARCH_API_KEY` | 실시간 매물 API | 매물 검색 |
| `GONG_GONG_DATA_API_KEY` | 공공데이터포털 API | 실거래가 |
| `KAKAO_REST_API_KEY` | 카카오 REST API | 지도/거리 계산 |

#### 통계 API

| 변수명 | 설명 | 용도 |
|-------|------|------|
| `KOSIS_CONSUMER_KEY` | 통계청 API 키 | 인구/주택 통계 |
| `KOSIS_CONSUMER_SECRET_KEY` | 통계청 API 시크릿 | 인구/주택 통계 |
| `ECOS_API_KEY` | 한국은행 API | 한국 금리 |
| `FRED_API_KEY` | 미국 연준 API | 미국 금리 |

#### 선택 환경 변수

| 변수명 | 설명 | 기본값 |
|-------|------|-------|
| `FASTAPI_URL` | FastAPI 서버 URL | `http://localhost:8080` |
| `LANGSMITH_API_KEY` | LangSmith 추적 API | - |
| `LANGSMITH_TRACING` | 추적 활성화 | `false` |

#### Langfuse (Observability)

| 변수명 | 설명 | 기본값 |
|-------|------|-------|
| `LANGFUSE_SECRET_KEY` | Langfuse Secret Key | - |
| `LANGFUSE_PUBLIC_KEY` | Langfuse Public Key | - |
| `LANGFUSE_HOST` | Langfuse 서버 URL | `https://cloud.langfuse.com` |
| `LANGFUSE_ENABLED` | 추적 활성화 여부 (`true`/`false`) | `false` |

#### DeepEval (Testing)

| 변수명 | 설명 | 기본값 |
|-------|------|-------|
| `DEEPEVAL_SERVER_URL` | E2E 테스트 대상 서버 URL | `http://localhost:8080` |
| `E2E_MODE` | E2E 실행 모드 (`eval_only`/`cache_only`/`full`) | `eval_only` |
| `PIPELINE_TIMEOUT` | 파이프라인 타임아웃 (초) | `7200` |
| `EVAL_QUICK_MODE` | 분석 테스트 빠른 모드 (에이전트당 1건만) | `0` |
| `EVAL_FULL_OUTPUT` | 콘솔에 전체 텍스트 출력 (200자 절단 해제) | `0` |

<!-- APPENDIX:ENV:END -->

### B. 파일 구조

```
src/
├── agents/
│   ├── main/
│   │   └── main_agent.py               # 메인 워크플로우 + Langfuse 세션
│   ├── analysis/
│   │   ├── analysis_graph.py           # 7개 에이전트 병렬 실행
│   │   ├── policy_agent.py             # 정책 분석 (SEGMENT 기반, MAX_ITERATIONS=3)
│   │   ├── housing_faq_agent.py        # 청약 FAQ
│   │   ├── location_insight_agent.py   # 입지 분석
│   │   ├── nearby_market_agent.py      # 주변 시장 (Structured Output)
│   │   ├── population_insight_agent.py # 인구 분석
│   │   ├── supply_demand_agent.py      # 공급/수요
│   │   └── unsold_insight_agent.py     # 미분양
│   ├── jung_min_jae/
│   │   └── jung_min_jae_agent.py       # 보고서 작성 (조건부 컨텍스트 주입)
│   └── state/
│       ├── start_state.py              # 사용자 입력 상태
│       ├── main_state.py               # 메인 상태
│       ├── analysis_state.py           # 분석 에이전트 상태
│       └── structured_schemas.py       # Structured Output 스키마 (9개 Pydantic)
├── fastapi/
│   └── main_api.py                     # FastAPI 서버 + Langfuse 세션 관리
├── tools/
│   ├── send_gmail.py                   # 이메일 발송
│   ├── context_to_csv.py               # CSV 변환/업로드
│   ├── kakao_api_distance_tool.py      # Kakao API
│   ├── gemini_search_tool.py           # Gemini 검색 + Langfuse 추적
│   ├── perplexity_search_tool.py       # Perplexity 검색 + Langfuse 추적
│   ├── kostat_api.py                   # 통계청 API
│   ├── kor_usa_rate.py                 # 금리 조회
│   ├── unsold_units.py                 # 미분양 RAG 검색 (pgvector)
│   └── rag/
│       ├── retriever/                  # RAG 리트리버들
│       ├── indexing/
│       │   └── unsold_housing_indexer.py # 미분양 데이터 벡터 인덱싱
│       └── vector_store.py             # pgvector 연결
├── tests/
│   ├── conftest.py                     # E2E session fixture (3-mode)
│   ├── e2e_client.py                   # E2E HTTP 폴링 클라이언트
│   ├── format_utils.py                 # 통합 출력 포맷터
│   ├── analysis/analysis_eval/         # 7개 분석 에이전트 평가
│   ├── final_report/report_eval/       # 최종 보고서 평가
│   ├── source/source_eval/             # 출처 검증
│   ├── judge/judge_eval/               # 정적: 판정 평가
│   ├── extraction/extraction_eval/     # 정적: 추출 평가
│   └── renderer/renderer_eval/         # 정적: 렌더러 평가
└── utils/
    ├── llm.py                          # LLM 프로필 + Langfuse 자동 추적
    ├── langfuse_tracker.py             # Langfuse 싱글톤 추적기 (TokenTracker)
    └── google_drive_uploader.py        # Drive 업로드
```

### C. 변경 이력

<!-- APPENDIX:HISTORY:START -->
| 날짜 | 버전 | 변경 내용 | 작성자 |
|-----|------|----------|-------|
| 2026-02-03 | 1.0.0 | 최초 작성 - 7개 에이전트 데이터 흐름 문서화 | - |
| 2026-03-14 | 1.1.0 | Langfuse Observability, DeepEval Testing, Structured Output 스키마, 미분양 RAG 전환, Policy SEGMENT 구조, jung_min_jae 토큰 폭발 방지, Tavily 검색 추가 | - |
| 2026-03-15 | 1.2.0 | 7개 분석 에이전트 데이터 출처 전체 정리 (에이전트별 상세표 + 총 28개 출처 + 14종류 유형별 분류) 추가 | - |
<!-- APPENDIX:HISTORY:END -->

<!-- SECTION:APPENDIX:END -->

---

<!-- SECTION:OBSERVABILITY:START -->
## 7. Langfuse Observability

### 7.1 아키텍처 개요

`src/utils/langfuse_tracker.py`의 `TokenTracker` 클래스가 Langfuse 추적의 중앙 관리자 역할을 합니다.
모듈 임포트 시 1회만 생성되는 **싱글톤 패턴**으로, 프로젝트 전체에서 `from utils.langfuse_tracker import tracker`로 동일 인스턴스를 사용합니다.

```mermaid
flowchart LR
    subgraph LangChainAuto["LangChain 자동 추적"]
        L1[RetryableChatOpenAI<br/>OpenAI / Claude]
        L2[CallbackHandler<br/>자동 주입]
    end

    subgraph SDKDirect["SDK 직접 호출 추적"]
        N1["gemini_search_tool.py<br/>@observe 데코레이터"]
        N2["perplexity_search_tool.py<br/>@observe 데코레이터"]
    end

    subgraph Session["세션 관리"]
        S1[main_api.py<br/>session_context]
        S2[ContextVar<br/>_active_session_id]
    end

    subgraph LF["Langfuse Cloud"]
        LFD[대시보드<br/>토큰/비용/세션]
    end

    L1 --> L2 --> LFD
    N1 --> LFD
    N2 --> LFD
    S1 --> S2
    S2 -.-> L2
    S2 -.-> N1
    S2 -.-> N2

    style L1 fill:#e3f2fd,color:#000
    style N1 fill:#fff3e0,color:#000
    style N2 fill:#fff3e0,color:#000
    style LFD fill:#f3e5f5,color:#000
    style S1 fill:#fff9c4,color:#000
```

### 7.2 이중 계층 추적

이 프로젝트의 LLM 호출은 두 경로로 나뉩니다:

| 계층 | 대상 | 설명 | 추적 방식 |
|------|------|------|----------|
| **LangChain 자동 추적** | OpenAI/Claude (`RetryableChatOpenAI`) | LangChain 프레임워크를 경유하는 LLM 호출. `CallbackHandler`가 자동으로 토큰/비용을 기록 | `_merge_langfuse_config()` 자동 주입 |
| **SDK 직접 호출 추적** | Gemini (`google-genai` SDK), Perplexity (`openai` SDK) | LangChain을 거치지 않고 각 SDK를 직접 호출하는 도구. 자동 추적이 불가능하므로 코드에서 직접 기록 | `@observe` 데코레이터 + `update_observation()` |

> **왜 두 계층인가?** Gemini/Perplexity는 LangChain의 ChatModel 인터페이스를 사용하지 않고, 각 SDK의 Client를 직접 호출합니다. LangChain의 CallbackHandler가 이 호출을 감지할 수 없으므로, `@observe` 데코레이터로 수동 기록해야 합니다.

**LangChain 자동 추적 흐름:**
```
llm.invoke(prompt)
  -> RetryableChatOpenAI._merge_langfuse_config()
    -> tracker.merge_config()  # CallbackHandler 추가
      -> super().invoke(input, config)
        -> CallbackHandler가 Langfuse에 trace 전송
```

**SDK 직접 호출 추적 흐름:**
```
@tracker.observe(as_type="generation")
def gemini_search(prompt):
    tracker.update_observation(name="gemini-search", input=prompt)
    response = client.models.generate_content(...)
    tracker.update_observation(output=result, usage=tokens)
```

### 7.3 세션 전파 (Session Propagation)

하나의 사용자 요청에서 발생하는 모든 LLM 호출(OpenAI, Gemini, Perplexity)을 Langfuse 대시보드에서 **단일 세션**으로 묶어 추적합니다.

```mermaid
sequenceDiagram
    participant API as main_api.py
    participant CV as ContextVar
    participant LLM as RetryableChatOpenAI
    participant GEM as gemini_search
    participant LF as Langfuse

    API->>CV: session_context(job_id) 진입<br/>ContextVar에 session_id 저장
    API->>LLM: graph.ainvoke()
    LLM->>CV: _active_session_id.get()
    LLM->>LF: trace (session_id=job_id)
    API->>GEM: gemini_search() 호출
    GEM->>CV: propagate_attributes 자동 전파
    GEM->>LF: generation (session_id=job_id)
    API->>CV: session_context 종료<br/>ContextVar reset
```

- `main_api.py`의 `run_graph_task()`에서 `async with tracker.session_context(session_id=job_id)`로 진입
- `ContextVar(_active_session_id)`가 `asyncio.create_task()` 경계를 넘어 자동 전파
- 28개 노드 함수를 개별 수정하지 않아도 모든 trace에 session_id 자동 주입

### 7.4 Graceful Degradation

Langfuse가 비활성화되거나 설치되지 않은 환경에서도 기존 파이프라인이 정상 작동합니다.

| 조건 | TokenTracker 동작 | 기존 코드 영향 |
|------|-------------------|--------------|
| `LANGFUSE_ENABLED=true` + 패키지 설치 | 모든 메서드 정상 동작 | 추적 활성화 |
| `LANGFUSE_ENABLED=false` | 모든 메서드가 `None` / `{}` 반환 | 추적 비활성화, 코드 변경 불필요 |
| `langfuse` 패키지 미설치 | `_enabled=False` 자동 설정 | 동일 (ImportError 없음) |

### 7.5 통합 지점 요약

| 파일 | 역할 | 추적 방식 |
|------|------|----------|
| `src/utils/llm.py` | LLM 호출 (LangChain 자동 추적) | `CallbackHandler` 자동 병합 |
| `src/tools/gemini_search_tool.py` | Gemini (SDK 직접 호출 추적) | `@observe` + `update_observation` |
| `src/tools/perplexity_search_tool.py` | Perplexity (SDK 직접 호출 추적) | `@observe` + `update_observation` |
| `src/fastapi/main_api.py` | 보고서 파이프라인 세션 관리 | `session_context(job_id)` |
| `src/chatbot/backend/chat_agent_langgraph.py` | 챗봇 세션 추적 | `session_context(session_id)` |

<!-- SECTION:OBSERVABILITY:END -->

---

<!-- SECTION:TESTING:START -->
## 8. DeepEval 테스트 아키텍처

### 8.1 Two-Tier 테스트 구조

테스트는 **서버 호출 여부**에 따라 두 계층으로 나뉩니다:

```mermaid
flowchart TB
    subgraph Tier1["Tier 1: 정적 데이터셋 (서버 호출 없음, ~3분)"]
        S1[Judge<br/>검수자 평가]
        S2[Extraction<br/>추출 정확도]
        S3[Renderer<br/>슬라이드 변환]
    end

    subgraph Tier2["Tier 2: E2E 파이프라인 (서버 호출 필요, ~40분)"]
        E1[Analysis<br/>7개 분석 에이전트]
        E2[Final Report<br/>최종 보고서]
        E3[Source<br/>출처 검증]
    end

    subgraph Fixture["conftest.py - session fixture"]
        F1{E2E_MODE?}
        F2[eval_only<br/>캐시 로드]
        F3[cache_only<br/>서버 호출만]
        F4[full<br/>서버+평가]
    end

    subgraph Output["결과"]
        O1["콘솔 종합 리포트"]
        O2["test_eval_details.json"]
    end

    F1 -->|eval_only| F2
    F1 -->|cache_only| F3
    F1 -->|full| F4
    F2 & F4 --> E1 & E2 & E3
    S1 & S2 & S3 --> O1
    E1 & E2 & E3 --> O1
    O1 --> O2

    style Tier1 fill:#e3f2fd,color:#000
    style Tier2 fill:#fff3e0,color:#000
    style O1 fill:#c8e6c9,color:#000
```

- **Tier 1 (정적)**: 미리 준비된 JSON 데이터셋으로 평가. 서버 호출 없이 빠르게 반복 가능
- **Tier 2 (E2E)**: 실제 서버에 파이프라인 요청을 보내고, 반환된 결과를 평가

### 8.2 E2E Pipeline 실행 모드

`src/tests/conftest.py`의 `e2e_result` fixture는 3가지 모드를 지원합니다:

| 모드 | 환경변수 | 서버 호출 | 캐시 저장 | 평가 실행 | 용도 |
|------|---------|----------|----------|----------|------|
| `eval_only` (기본) | `E2E_MODE=eval_only` | X | X | O | 메트릭/데이터셋 수정 시 빠른 반복 |
| `cache_only` | `E2E_MODE=cache_only` | O | O | X | 서버 결과 수집만 (40분+) |
| `full` | `E2E_MODE=full` | O | O | O | 전체 파이프라인 검증 |

> **왜 3개 모드인가?** 서버 파이프라인 실행에 40분 이상 소요되므로, 메트릭 로직만 수정했을 때 서버를 다시 호출하지 않고 캐시된 결과로 빠르게 재평가(`eval_only`)할 수 있습니다.

### 8.3 E2EClient

`src/tests/e2e_client.py`는 장시간 실행되는 서버 파이프라인과 통신하는 HTTP 클라이언트입니다.

```mermaid
sequenceDiagram
    participant TC as 테스트 코드
    participant EC as E2EClient
    participant SV as FastAPI 서버

    TC->>EC: run_pipeline(start_input)
    EC->>SV: POST /invoke
    SV-->>EC: job_id 반환
    loop 30초 간격 폴링
        EC->>SV: GET /status/{job_id}
        SV-->>EC: status: running
    end
    SV-->>EC: status: completed
    EC->>SV: GET /result/{job_id}
    SV-->>EC: 파이프라인 결과
    EC-->>TC: e2e_result dict
```

- 타임아웃: `PIPELINE_TIMEOUT` 환경변수 (기본 7200초 = 2시간)
- 서버 URL: `DEEPEVAL_SERVER_URL` 환경변수 (기본 `http://localhost:8080`)

### 8.4 평가 메트릭 체계

#### 분석 에이전트 메트릭 (7개 에이전트 공통)

| 메트릭 | 기본 가중치 | 임계값 | 평가 항목 |
|--------|-----------|--------|----------|
| AnalysisDepth | 60% | 0.7 | 깊이 있는 분석 vs 나열, 시계열 해석, 예측 |
| DataFidelity | 20% | 0.8 | 수치 일관성, 환각(Hallucination) 감지 |
| StructuralCompleteness | 20% | 0.7 | 마크다운 구조, 논리적 흐름, 어조 |

**에이전트별 가중치 오버라이드:**
| 에이전트 | AnalysisDepth | DataFidelity | StructuralCompleteness |
|---------|---------------|-------------|----------------------|
| 기본 (대부분) | 60% | 20% | 20% |
| policy | 20% | 20% | **60%** (표 형식 중요) |
| nearby_market, location_insight | 30% | 20% | 20% |

#### RAG 에이전트 메트릭 (RAG 사용 에이전트만)

| 메트릭 | 가중치 | 임계값 | 평가 항목 |
|--------|--------|--------|----------|
| Faithfulness | 33.4% | 0.7 | 검색 문서에 충실한 답변인가 |
| Contextual Relevancy | 33.3% | 0.7 | 검색된 문서가 질문과 관련 있는가 |
| Answer Relevancy | 33.3% | 0.7 | 답변이 질문에 적절한가 |

> **분석 점수와 RAG 점수는 독립 산출됩니다 (합산 X).** 각각 100% 기준으로 평가하여, 분석 품질과 검색 품질을 별도로 추적합니다.

#### 정적 테스트 메트릭

| 모듈 | 메트릭 | 임계값 |
|------|--------|--------|
| Judge | CritiqueAccuracy | 0.7 |
| Extraction | ExtractionAccuracy | 0.7 |
| Renderer | SlidePlanStructure | 0.7 |
| Final Report | ReportProfessionalism (60%) + AnalysisCoverage (40%) | 0.7 |
| Source | SourceCompleteness | 0.7 |

### 8.5 출력 시스템

`src/tests/format_utils.py`가 통합 출력을 관리합니다:

| 함수 | 역할 |
|------|------|
| `print_module_header()` | 모듈별 헤더 출력 |
| `print_case_result()` | 정적 모듈 개별 케이스 출력 |
| `print_analysis_case_result()` | 분석 모듈 케이스 출력 (분석 + RAG 점수) |
| `append_detail()` | JSON 상세 결과 수집 (`_JSON_DETAIL_STORE`) |
| `save_detail_json()` | `test_eval_details.json` 파일 저장 |
| `print_final_summary()` | 최하단 종합 리포트 출력 |

**종합 리포트 출력 예시:**
```
============================================================
         [ ALL FOR ONE 평가 종합 리포트 ]
============================================================
  [정적 데이터셋]
  Judge               | 평균 80.00% (3건) | PASS
  Extraction          | 평균 85.00% (5건) | PASS
  Renderer            | 평균 90.00% (3건) | PASS

  [E2E 분석 에이전트]
  - housing_faq       | 분석 85.00% | RAG 92.00% (3건)
  - policy            | 분석 80.50% | RAG 88.50% (3건)

  [E2E 보고서]
  Final Report        | 가중 88.00% (1건) | PASS
  Source              | 평균 92.00% (1건) | PASS
============================================================
```

### 8.6 실행 명령어

**정적 테스트 (서버 불필요):**
```bash
# 개별 모듈
set PYTHONIOENCODING=utf-8 && uv run deepeval test run src/tests/judge/judge_eval/test_judge.py -v

# 정적 3개 모듈 한번에
set PYTHONIOENCODING=utf-8 && uv run deepeval test run src/tests/judge/judge_eval/test_judge.py src/tests/extraction/extraction_eval/test_extraction.py src/tests/renderer/renderer_eval/test_renderer.py -v
```

**E2E 테스트 (서버 필요, 40분+):**
```bash
# 서버 결과 수집 + 캐시 저장 (평가 없음)
set PYTHONIOENCODING=utf-8 && set E2E_MODE=cache_only && set DEEPEVAL_SERVER_URL=https://your-server.up.railway.app && uv run deepeval test run src/tests/analysis/analysis_eval/test_analysis.py -v

# 캐시 기반 재평가 (서버 호출 없음)
set PYTHONIOENCODING=utf-8 && set E2E_MODE=eval_only && uv run deepeval test run src/tests/analysis/analysis_eval/test_analysis.py -v
```

**전체 한번에 (서버 1회만 호출):**
```bash
set PYTHONIOENCODING=utf-8 && set E2E_MODE=full && set DEEPEVAL_SERVER_URL=https://your-server.up.railway.app && uv run deepeval test run src/tests/judge/judge_eval/test_judge.py src/tests/extraction/extraction_eval/test_extraction.py src/tests/renderer/renderer_eval/test_renderer.py src/tests/analysis/analysis_eval/test_analysis.py src/tests/final_report/report_eval/test_final_report.py src/tests/source/source_eval/test_source.py -v
```

<!-- SECTION:TESTING:END -->
