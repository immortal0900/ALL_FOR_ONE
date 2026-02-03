# ALL-FOR-ONE API & Data Flow 문서

> 최종 업데이트: 2026-02-03
> 프로젝트: 부동산 분양성 검토 보고서 자동 생성 시스템

---

## 목차

1. [개요](#1-개요)
2. [데이터 흐름 상세](#2-데이터-흐름-상세)
3. [메인 워크플로우](#3-메인-워크플로우)
4. [플로우 다이어그램](#4-플로우-다이어그램)
5. [이메일 발송](#5-이메일-발송)
6. [부록](#6-부록)

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
    
    A --> B
    B --> C1 & C2 & C3 & C4 & C5 & C6 & C7
    C1 & C2 & C3 & C4 & C5 & C6 & C7 --> D1 & D2 & D3 & D4
    C1 & C2 & C3 & C4 & C5 & C6 & C7 --> E
    E --> F1 & F2 & F3
    F1 & F2 & F3 --> G
    
    style A fill:#e3f2fd,color:#000
    style B fill:#fff3e0,color:#000
    style E fill:#fff9c4,color:#000
    style G fill:#c8e6c9,color:#000
```

### 1.2 기술 스택

| 구분 | 기술 | 버전 | 용도 |
|-----|------|-----|------|
| Language | Python | 3.12+ | 메인 언어 |
| Framework | FastAPI | 0.121.0+ | REST API 서버 |
| Agent Framework | LangGraph | 1.0.0+ | 멀티에이전트 오케스트레이션 |
| LLM Framework | LangChain | 1.0.3+ | LLM 통합 |
| Vector DB | PostgreSQL + pgvector | 14+ | RAG 벡터 검색 |
| LLM | OpenAI GPT-4o | - | 보고서 작성 |
| LLM | Anthropic Claude | - | 분석 에이전트 |
| LLM | Google Gemini | - | 웹 검색 |
| PDF 생성 | WeasyPrint | 66.0+ | Markdown → PDF |
| 이메일 | Gmail API | - | 보고서 발송 |
| 파일 저장 | Google Drive API | - | CSV/PDF 업로드 |

### 1.3 외부 API 서비스

| 서비스 | 용도 | 사용 에이전트 |
|-------|------|-------------|
| Kakao Maps API | 좌표 변환, 거리 계산, 주변 시설 | 입지분석, 주변시장 |
| KOSTAT (통계청) | 인구 이동, 10년 노후 주택 | 인구분석, 공급/수요 |
| ECOS (한국은행) | 한국 금리 | 공급/수요 |
| FRED (미국 연준) | 미국 금리 | 공급/수요 |
| R-ONE (부동산원) | 매매수급지수 | 공급/수요 |
| 공공데이터포털 | 실거래가 조회 | 주변시장 |
| Perplexity AI | 실시간 웹 검색 | 정책, 입지, 주변시장 |
| Google Gemini | AI 기반 검색 | 입지, 주변시장 |

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
        P1[analysis_setting<br/>프롬프트 구성]
        P2[generate_initial_report<br/>초안 작성]
        P3[evaluate_completeness<br/>완성도 평가]
        P4{is_complete?}
        P5[execute_retrieval<br/>추가 검색]
        P6[revise_report<br/>보고서 수정]
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
    P4 -->|No| P5 --> P6 --> P3
    P4 -->|Yes| O1
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
| `national_policy_retrieve()` | RAG (pgvector) | 국가 정책 뉴스 벡터 검색 |
| `collect_articles_result()` | 웹 크롤링 | 지역 정책 기사 수집 |
| `PolicyPDFRetriever.hybrid_search()` | RAG (pgvector) | 정책 PDF 하이브리드 검색 |
| `perplexity_search()` | AI 웹 검색 | 부족한 정보 보완 |

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
| `gemini_search()` | Google Gemini AI | 주변 매매 3개 + 분양 3개 아파트 검색 |
| `get_location_profile()` | Kakao Maps API | 각 아파트 입지 정보 |
| `get_real_estate_price()` | 공공데이터포털 API | 매매아파트 실거래가 |
| `perplexity_search()` | Perplexity AI | 분양아파트 가격/경쟁률 검증 |

**수집 정보 (아파트당):**
- 매매아파트: 주소, 세대수, 타입, 평당매매가격, 준공연도, 거리, 주변호재
- 분양아파트: 주소, 세대수, 타입, 평당분양가격, 청약경쟁률, 청약일시, 계약조건, 거리

**출력 구조:**
```python
nearby_market_output = {
    "result": str,                              # LLM 분석 보고서
    "gemini_search": str,                       # Gemini 검색 결과 (JSON)
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
        D1[get_unsold_unit<br/>미분양 현황 로컬 CSV]
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
| `unsold_units()` | 로컬 CSV | 시군구별 미분양 현황 (월별) |

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

### 2.3 데이터 유형 분류

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
| `{주소}_미분양_temp.csv` | 로컬 원본 | 로컬 CSV 파일 |

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

<!-- APPENDIX:ENV:END -->

### B. 파일 구조

```
src/
├── agents/
│   ├── main/
│   │   └── main_agent.py           # 메인 워크플로우
│   ├── analysis/
│   │   ├── analysis_graph.py       # 7개 에이전트 병렬 실행
│   │   ├── policy_agent.py         # 정책 분석
│   │   ├── housing_faq_agent.py    # 청약 FAQ
│   │   ├── location_insight_agent.py   # 입지 분석
│   │   ├── nearby_market_agent.py  # 주변 시장
│   │   ├── population_insight_agent.py # 인구 분석
│   │   ├── supply_demand_agent.py  # 공급/수요
│   │   └── unsold_insight_agent.py # 미분양
│   ├── jung_min_jae/
│   │   └── jung_min_jae_agent.py   # 보고서 작성
│   └── state/
│       ├── start_state.py          # 사용자 입력 상태
│       ├── main_state.py           # 메인 상태
│       └── analysis_state.py       # 분석 에이전트 상태
├── tools/
│   ├── send_gmail.py               # 이메일 발송
│   ├── context_to_csv.py           # CSV 변환/업로드
│   ├── kakao_api_distance_tool.py  # Kakao API
│   ├── gemini_search_tool.py       # Gemini 검색
│   ├── perplexity_search_tool.py   # Perplexity 검색
│   ├── kostat_api.py               # 통계청 API
│   ├── kor_usa_rate.py             # 금리 조회
│   └── rag/
│       ├── retriever/              # RAG 리트리버들
│       └── vector_store.py         # pgvector 연결
└── utils/
    ├── llm.py                      # LLM 프로필 관리
    └── google_drive_uploader.py    # Drive 업로드
```

### C. 변경 이력

<!-- APPENDIX:HISTORY:START -->
| 날짜 | 버전 | 변경 내용 | 작성자 |
|-----|------|----------|-------|
| 2026-02-03 | 1.0.0 | 최초 작성 - 7개 에이전트 데이터 흐름 문서화 | - |
<!-- APPENDIX:HISTORY:END -->

<!-- SECTION:APPENDIX:END -->
