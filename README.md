# ALL-FOR-ONE: AI 멀티에이전트 부동산 분석 시스템

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.0+-FF4785?style=flat)](https://langchain-ai.github.io/langgraph/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.121+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-316192?style=flat&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io/)

> **7개의 전문 AI 에이전트**가 부동산 시장을 다각도로 분석하고, **종합 리서치 보고서를 자동 생성**하는 멀티에이전트 시스템

---

## 목차

- [이 프로젝트가 해결하는 문제](#이-프로젝트가-해결하는-문제)
- [시스템 작동 방식](#시스템-작동-방식)
- [7개 전문 에이전트](#7개-전문-에이전트)
- [핵심 기술](#핵심-기술)
  - [1. LangGraph 기반 ReAct 패턴 멀티에이전트](#1-langgraph-기반-react-패턴-멀티에이전트)
  - [2. YAML 기반 프롬프트 관리 시스템](#2-yaml-기반-프롬프트-관리-시스템-promptmanager)
  - [3. 하이브리드 검색 RAG 시스템](#3-하이브리드-검색hybrid-search-rag-시스템)
  - [4. 다중 외부 API 오케스트레이션](#4-다중-외부-api-오케스트레이션-tool-시스템)
  - [5. think_tool 기반 Reflection](#5-think_tool-기반-reflection성찰-메커니즘)
  - [6. 정책 뉴스 웹 크롤링 + LLM 정제](#6-정책-뉴스-웹-크롤링--llm-정제-파이프라인)
- [기술 스택](#기술-스택)
- [빠른 시작](#빠른-시작-5분)
- [상세 설치 가이드](#상세-설치-가이드)
- [사용 방법](#사용-방법)
- [프로젝트 구조](#프로젝트-구조)
- [관련 문서](#관련-문서)

---

## 이 프로젝트가 해결하는 문제

부동산 분양성 검토 보고서를 작성하려면 **입지, 정책, 인구, 경제지표, 주변시세** 등 다양한 데이터를 수집하고 분석해야 합니다. 이 과정은 보통 **수일~수주**가 걸리며, 전문 인력이 필요합니다.

| 기존 방식 | ALL-FOR-ONE |
|----------|-------------|
| 데이터 수집에 수일 소요 | 7개 에이전트가 **병렬로 자동 수집** |
| 분석가의 주관적 판단 | AI가 **객관적 데이터 기반** 분석 |
| 보고서 작성에 수일 소요 | **자동 보고서 생성 + 자체 검증** |
| 출처 정리가 번거로움 | **원본 데이터 CSV + 출처 문서 자동 생성** |

## **결과물**: 사용자가 주소와 세대수등 정보를 입력하면, **PDF 보고서 + 원본 데이터 CSV** 총 17개가 이메일로 발송됩니다.

### 부동산 가격 예측 보고서_INPUT
[![부동산 가격 예측 보고서_INPUT](https://img.youtube.com/vi/t15m7Y2QNsw/sddefault.jpg)](https://youtube.com/shorts/t15m7Y2QNsw)
- 사업지 주소, 단지 타입, 세대수 이메일 주소, 원하는 주요정책 선택

### 부동산 가격 예측 보고서_OUTPUT
[![부동산 가격 예측 보고서_OUTPUT](https://img.youtube.com/vi/MsCLVyzsxjY/sddefault.jpg)](https://youtu.be/MsCLVyzsxjY)
- RAG를 이용해 API 와 DB에 있는 부동산 정보들을 가져와서 각각의 정보를 7개의 분석 에이전트가 작성 에이전트에게 전달하여 보고서 작성 후 이메일로 발송
- 출처에서 뽑은 정보는 이메일에 파일로 첨부되어 직접확인 가능(블랙박스 방지)

#### OUT 이메일 내용(총 17개)

**PDF 파일 (2개) - LLM이 작성한 보고서:**
{제목}_최종보고서.pdf - 7개 에이전트 분석 결과를 종합한 최종 보고서
{제목}__데이터출처모음.pdf - 출처 페이지 (데이터 원본 링크 모음)

**CSV 파일 (15개) - 원본 데이터:**
| 에이전트 | 파일명 | 데이터 유형 |
|---------|--------|-----------|
| 청약 FAQ | `주택청약FAQ_temp.csv` | RAG 원본 |
| 청약 FAQ | `주택공급규칙_temp.csv` | RAG 원본 (LLM 요약) |
| 입지분석 | `{주소}_입지분석_카카오_temp.csv` | API 원본 |
| 주변시장 | `{주소}_주변단지_정보_temp.csv` | API+LLM 원본 |
| 정책 | `국가적_정책_모음_temp.csv` | RAG 원본 |
| 정책 | `지역별_정책_모음_temp.csv` | 크롤링 원본 |
| 미분양 | `{주소}_미분양_temp.csv` | 로컬 CSV 원본 |
| 인구분석 | `{주소}_인구이동_temp.csv` | API 원본 |
| 인구분석 | `{주소}_연령층분포_temp.csv` | RAG 원본 |
| 공급/수요 | `주택담보대출_temp.csv` | RAG 원본 |
| 공급/수요 | `미국_한국_금리_temp.csv` | API 원본 |
| 공급/수요 | `{주소}_GDP_와_GRDP_temp.csv` | API+RAG 원본 |
| 공급/수요 | `{주소}_입주예정단지_temp.csv` | RAG 원본 |
| 공급/수요 | `{주소}_매매수급지수_temp.csv` | RAG 원본 |
| 공급/수요 | `{구}_월별_전세가격_temp.csv` | RAG 원본 |
| 공급/수요 | `{구}_월별_매매가격_temp.csv` | RAG 원본 |
| 공급/수요 | `{주소}_청약경쟁률_temp.csv` | 크롤링 원본 |



---

## 시스템 작동 방식

### 전체 파이프라인

```mermaid
flowchart TB
    subgraph Phase1["Phase 1: 시작"]
        A["사용자 입력<br/>(주소/타입/세대수/이메일)"]
        B["start 노드<br/>상태 초기화"]
    end
    
    subgraph Phase2["Phase 2: 병렬 분석"]
        C["analysis_graph_node"]
        D1["정책 분석<br/>policy_agent"]
        D2["청약 FAQ<br/>housing_faq_agent"]
        D3["입지 분석<br/>location_insight_agent"]
        D4["주변 시장<br/>nearby_market_agent"]
        D5["인구 분석<br/>population_insight_agent"]
        D6["수급 분석<br/>supply_demand_agent"]
        D7["미분양 분석<br/>unsold_insight_agent"]
        E["join_results<br/>7개 결과 병합"]
    end
    
    subgraph Phase3["Phase 3: 보고서 작성"]
        F["jung_min_jae_graph"]
        G1["Segment 1 작성<br/>(개요/입지/정책)"]
        G2["Segment 2 작성<br/>(공급수요/미분양)"]
        G3["Segment 3 작성<br/>(인구/주변시장)"]
        G4["Segment 4 작성<br/>(종합평가/결론)"]
        H["finalize_merge<br/>세그먼트 병합"]
        I["reflection_prompt<br/>자체 검증 준비"]
        J["reflect_agent<br/>think_tool 호출"]
        K["apply_reflection<br/>피드백 반영"]
    end
    
    subgraph Phase4["Phase 4: 파일 생성 및 발송"]
        L["final_node"]
        M1["최종보고서.pdf 생성"]
        M2["데이터출처모음.pdf 생성"]
        M3["Google Drive 업로드"]
        N["Gmail 발송"]
    end
    
    O["완료"]
    
    A --> B
    B --> C
    C --> D1 & D2 & D3 & D4 & D5 & D6 & D7
    D1 & D2 & D3 & D4 & D5 & D6 & D7 --> E
    E --> F
    F --> G1 --> G2 --> G3 --> G4
    G4 --> H --> I --> J --> K
    K --> L
    L --> M1 & M2 & M3
    M1 & M2 & M3 --> N
    N --> O
    
    style A fill:#e3f2fd,color:#000
    style E fill:#fff3e0,color:#000
    style K fill:#fff9c4,color:#000
    style O fill:#c8e6c9,color:#000
```

### 상태 전이 다이어그램

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

---

## 7개 전문 에이전트

각 에이전트는 **ReAct 패턴**(추론 → 행동 → 관찰 반복)으로 동작하며, 필요한 도구를 자율적으로 선택합니다.

| 에이전트 | 분석 영역 | 데이터 소스 | 출력 CSV |
|---------|---------|------------|----------|
| **입지 분석** | 교통, 교육, 편의시설, 자연환경 | Kakao Maps API, Gemini AI | `입지분석_카카오.csv` |
| **정책 분석** | 부동산 정책, 규제 변화 | RAG 벡터검색, 웹 크롤링 | `국가정책.csv`, `지역정책.csv` |
| **수급 분석** | 금리, 거래량, 매매수급지수, GDP | KOSTAT, ECOS, FRED, R-ONE API | 8개 CSV |
| **미분양 분석** | 시군구별 미분양 현황 | 로컬 CSV 데이터 | `미분양.csv` |
| **인구 분석** | 연령별 인구, 인구 이동 | KOSTAT API, RAG 검색 | `연령층분포.csv`, `인구이동.csv` |
| **주변 시장** | 인근 매매/분양 시세 | 공공데이터포털, Perplexity AI | `주변단지_정보.csv` |
| **청약 FAQ** | 청약 규칙, 당첨 조건 | RAG 벡터검색 | `청약FAQ.csv`, `공급규칙.csv` |

### 분석 그래프 병렬 실행 구조

```mermaid
flowchart TB
    subgraph START["시작"]
        S["start_input<br/>(주소/타입/세대수)"]
    end
    
    subgraph PARALLEL["병렬 실행 (7개 에이전트)"]
        direction TB
        P1["policy_graph<br/>정책 분석"]
        P2["housing_faq_graph<br/>청약 FAQ"]
        P3["location_insight_graph<br/>입지 분석"]
        P4["nearby_market_graph<br/>주변 시장"]
        P5["population_insight_graph<br/>인구 분석"]
        P6["supply_demand_graph<br/>수급 분석"]
        P7["unsold_insight_graph<br/>미분양 분석"]
    end
    
    subgraph JOIN["결과 병합"]
        J["join_results"]
    end
    
    subgraph OUTPUT["출력"]
        O["analysis_outputs<br/>(7개 분석 결과)"]
    end
    
    S --> P1 & P2 & P3 & P4 & P5 & P6 & P7
    P1 & P2 & P3 & P4 & P5 & P6 & P7 --> J
    J --> O
    
    style S fill:#e3f2fd,color:#000
    style J fill:#fff3e0,color:#000
    style O fill:#c8e6c9,color:#000
```

---

## 핵심 기술

### 1. LangGraph 기반 ReAct 패턴 멀티에이전트

#### 선택 이유

| 기존 방식의 한계 | 해결 필요성 |
|-----------------|------------|
| 단순 LLM Chain은 한 번의 호출로 끝나 복잡한 분석 불가 | 부동산 분석은 입지/정책/시세 등 **다중 데이터 소스**를 순차적으로 조합해야 함 |
| 고정된 파이프라인은 데이터 부족 시 대응 불가 | Agent가 스스로 **도구 호출 여부를 판단**하고, 부족하면 재검색하는 동적 흐름 필요 |
| 일반 Agent는 상태 관리가 어려워 멀티스텝 추론 실패 | LangGraph의 **StateGraph**로 상태를 명시적으로 관리하여 복잡한 워크플로우 구현 |

#### 구현 방법

**구현 파일**: 
- `src/agents/analysis/location_insight_agent.py`
- `src/agents/analysis/nearby_market_agent.py`
- `src/agents/analysis/policy_agent.py`

**핵심 로직**:
1. **StateGraph 정의**: 각 Agent별로 전용 State 클래스를 정의하여 입력/출력/중간 상태를 타입 안전하게 관리
2. **Node 분리**: 데이터 수집(gemini_search, kakao_api_distance), 프롬프트 설정(analysis_setting), 추론(agent), 도구 실행(tools) 노드를 분리
3. **Conditional Edge**: `router` 함수로 LLM 응답에 `tool_calls`가 있으면 도구 노드로, 없으면 종료로 분기
4. **병렬 실행**: `nearby_market_agent`에서 kakao_api, real_estate_price, perplexity_search 노드를 병렬로 실행하여 응답 시간 단축

#### ReAct 패턴 흐름

```mermaid
flowchart TB
    START["START"] --> DataCollection["데이터 수집<br/>(병렬)"]
    DataCollection --> PromptSetting["프롬프트 설정<br/>(analysis_setting)"]
    PromptSetting --> Agent["Agent<br/>(LLM 추론)"]
    Agent --> Router{"tool_calls<br/>있음?"}
    Router -->|Yes| Tools["Tools<br/>(도구 실행)"]
    Tools --> Agent
    Router -->|No| END["END"]
    
    style START fill:#e3f2fd,color:#000
    style Router fill:#fff9c4,color:#000
    style END fill:#c8e6c9,color:#000
```

#### 핵심 기능

- Agent가 **자율적으로 도구 호출 여부를 판단**하여 필요한 정보만 수집
- 상태 기반 워크플로우로 **멀티스텝 추론**이 안정적으로 동작
- 노드 단위 분리로 **디버깅과 테스트가 용이**
- 병렬 노드 실행으로 **응답 시간 최적화**

**참고**: [LangGraph 공식 문서](https://langchain-ai.github.io/langgraph/), [ReAct 논문](https://arxiv.org/abs/2210.03629)

---

### 2. YAML 기반 프롬프트 관리 시스템 (PromptManager)

#### 선택 이유

| 기존 방식의 한계 | 해결 필요성 |
|-----------------|------------|
| 프롬프트를 Python 코드에 하드코딩하면 수정 시 배포 필요 | 프롬프트 변경만으로 Agent 동작을 조정하려면 **코드/프롬프트 분리** 필수 |
| 긴 프롬프트가 코드 가독성을 해침 | YAML 파일로 분리하여 **멀티라인 프롬프트**를 깔끔하게 관리 |
| 동일 프롬프트를 여러 곳에서 사용 시 중복 발생 | **PromptType Enum**으로 중앙 집중 관리하여 일관성 보장 |
| 세그먼트별 다른 프롬프트 적용이 복잡함 | `segment_directive()` 함수로 **세그먼트 번호에 따라 동적 로딩** |

#### 구현 방법

**구현 파일**: 
- `src/prompts/PromptManager.py` (PromptManager 클래스)
- `src/prompts/PromptType.py` (Enum 정의)
- `src/prompts/jung_min_jae.yaml` (SEGMENT_01~04, SYSTEM, HUMAN, SUMMARY)
- `src/agents/jung_min_jae/jung_min_jae_agent.py` (세그먼트별 프롬프트 로딩)

**핵심 로직**:
1. **PromptType Enum**: 프롬프트 이름, YAML 경로, 설명을 하나의 Enum 멤버로 관리
2. **YAML 파싱**: `yaml.safe_load()`로 파일을 읽고, 각 키를 PromptTemplate 객체로 변환
3. **변수 치환**: `get_prompt(**kwargs)` 메서드로 `{target_area}`, `{date}` 등 플레이스홀더를 런타임 값으로 치환
4. **세그먼트별 분기**: `segment_directive(seg)` 함수가 세그먼트 번호에 따라 SEGMENT_01~04 프롬프트를 동적으로 반환

#### 프롬프트 관리 흐름

```mermaid
flowchart LR
    subgraph YAML["YAML 파일"]
        Y1["jung_min_jae.yaml"]
        Y2["SEGMENT_01"]
        Y3["SEGMENT_02"]
        Y4["SEGMENT_03"]
        Y5["SEGMENT_04"]
    end
    
    subgraph Enum["PromptType Enum"]
        E1["JUNG_MIN_JAE_SEGMENT_01"]
        E2["JUNG_MIN_JAE_SEGMENT_02"]
        E3["JUNG_MIN_JAE_SEGMENT_03"]
        E4["JUNG_MIN_JAE_SEGMENT_04"]
    end
    
    subgraph Manager["PromptManager"]
        M1["get_prompt(**kwargs)"]
        M2["변수 치환<br/>{target_area} → 실제값"]
    end
    
    subgraph Agent["Agent"]
        A1["segment_directive(seg)"]
        A2["LLM에 프롬프트 전달"]
    end
    
    Y1 --> Y2 & Y3 & Y4 & Y5
    Y2 --> E1
    Y3 --> E2
    Y4 --> E3
    Y5 --> E4
    E1 & E2 & E3 & E4 --> M1
    M1 --> M2
    M2 --> A1
    A1 --> A2
    
    style Y1 fill:#e3f2fd,color:#000
    style M1 fill:#fff9c4,color:#000
    style A2 fill:#c8e6c9,color:#000
```

#### 코드 예시

```python
# src/agents/jung_min_jae/jung_min_jae_agent.py
def segment_directive(seg: int) -> str:
    if seg == 1:
        return PromptManager(PromptType.JUNG_MIN_JAE_SEGMENT_01).get_prompt()
    if seg == 2:
        return PromptManager(PromptType.JUNG_MIN_JAE_SEGMENT_02).get_prompt()
    if seg == 3:
        return PromptManager(PromptType.JUNG_MIN_JAE_SEGMENT_03).get_prompt()
    return PromptManager(PromptType.JUNG_MIN_JAE_SEGMENT_04).get_prompt()
```

#### 핵심 기능

- 프롬프트 수정 시 **코드 변경 없이 YAML 파일만 수정**
- **타입 안전성**: PromptType Enum으로 오타 방지 및 IDE 자동완성 지원
- **변수 검증**: `input_variables` 리스트로 필수 변수 누락 시 에러 발생
- 보고서 **세그먼트별로 최적화된 프롬프트** 적용 (사업환경/정책/수요/종합결론)

**참고**: [PyYAML 공식 문서](https://pyyaml.org/wiki/PyYAMLDocumentation), [Python Enum 공식 문서](https://docs.python.org/3/library/enum.html)

---

### 3. 하이브리드 검색(Hybrid Search) RAG 시스템

#### 선택 이유

| 기존 방식의 한계 | 해결 필요성 |
|-----------------|------------|
| **순수 벡터 검색**은 "LTV 70%"같은 정확한 수치 매칭에 약함 | 정책 문서에서 **정확한 규제 수치**를 찾으려면 키워드 매칭 필수 |
| **순수 키워드 검색**은 "대출 규제 강화"와 "주담대 한도 축소"를 연결 못함 | **의미적 유사성**을 파악하여 동의어/유사 표현 검색 필요 |
| 두 방식을 단순 병합하면 중복 결과 발생 | **가중치 기반 스코어 병합**으로 두 방식의 장점만 결합 |

#### 구현 방법

**구현 파일**: 
- `src/tools/rag/retriever/policy_pdf_retriever.py` (PolicyPDFRetriever 클래스)
- `src/tools/rag/document_loader/policy_pdf_loader.py` (PolicyPDFLoader 클래스)
- `src/tools/rag/chunker/default_chunker.py` (RecursiveCharacterTextSplitter)

**핵심 로직**:
1. **문서 로딩**: `PolicyPDFLoader`가 PDF에서 텍스트 추출 + 정책 유형/날짜/제목 메타데이터 자동 추출
2. **청킹**: `RecursiveCharacterTextSplitter`로 1500자 단위 분할 (150자 오버랩)
3. **벡터 저장**: PGVector(Supabase)에 OpenAI Embedding과 함께 저장
4. **하이브리드 검색**: 벡터 검색 + 키워드 검색을 가중치로 병합

#### 하이브리드 검색 흐름

```mermaid
flowchart TB
    subgraph Input["입력"]
        Q["검색 쿼리<br/>'LTV 규제 강화 정책'"]
    end
    
    subgraph SemanticSearch["의미 검색 (Semantic)"]
        S1["OpenAI Embedding"]
        S2["벡터 유사도 계산"]
        S3["상위 k*2개 결과"]
    end
    
    subgraph KeywordSearch["키워드 검색 (Keyword)"]
        K1["키워드 추출<br/>(LTV, 규제, 강화)"]
        K2["TF 빈도 계산"]
        K3["상위 k*2개 결과"]
    end
    
    subgraph Merge["스코어 병합"]
        M1["순위 기반 점수 계산"]
        M2["가중치 적용<br/>(0.7 : 0.3)"]
        M3["중복 제거 + 정렬"]
    end
    
    subgraph Output["출력"]
        O["상위 k개 문서"]
    end
    
    Q --> S1 --> S2 --> S3
    Q --> K1 --> K2 --> K3
    S3 --> M1
    K3 --> M1
    M1 --> M2 --> M3 --> O
    
    style Q fill:#e3f2fd,color:#000
    style M2 fill:#fff9c4,color:#000
    style O fill:#c8e6c9,color:#000
```

#### 코드 예시

```python
# src/tools/rag/retriever/policy_pdf_retriever.py
def hybrid_search(self, query, keywords=None, semantic_weight=0.7, k=5):
    # 1. 의미 검색 (벡터 유사도)
    semantic_results = self.semantic_search(query, k=k*2)
    
    # 2. 키워드 추출 (쿼리에서 LTV, DSR 등 중요 용어 자동 추출)
    if keywords is None:
        keywords = self._extract_keywords(query)
    
    # 3. 키워드 검색 (TF 빈도)
    keyword_results = self.keyword_search(keywords, k=k*2)
    
    # 4. 스코어 병합 (순위 기반 점수 + 가중치 적용)
    combined_scores = {}
    for idx, doc in enumerate(semantic_results):
        rank_score = (len(semantic_results) - idx) / len(semantic_results)
        combined_scores[doc_id] = semantic_weight * rank_score
    
    for idx, doc in enumerate(keyword_results):
        keyword_score = (1 - semantic_weight) * (1 - idx / len(keyword_results))
        combined_scores[doc_id] += keyword_score  # 기존 점수에 추가
    
    return sorted_by_score[:k]
```

#### 핵심 기능

- **의미 검색 + 키워드 검색 결합**으로 정책 문서 검색 정확도 향상
- 정책 용어(LTV, DSR, 규제지역 등) **자동 키워드 추출**
- 메타데이터(정책 유형, 날짜, 제목) 기반 **필터링 가능**
- Supabase PostgreSQL + PGVector로 **서버리스 벡터 DB** 구현

**참고**: [PGVector 공식 문서](https://github.com/pgvector/pgvector), [LangChain Text Splitters](https://python.langchain.com/docs/modules/data_connection/document_transformers/)

---

### 4. 다중 외부 API 오케스트레이션 Tool 시스템

#### 선택 이유

| 기존 방식의 한계 | 해결 필요성 |
|-----------------|------------|
| 각 API를 별도 함수로 호출하면 Agent가 사용 불가 | LangChain `@tool` 데코레이터로 래핑하여 **Agent가 자율적으로 호출** 가능 |
| API 응답 형식이 제각각이라 후처리 복잡 | 도구 내부에서 **통일된 JSON 형식**으로 변환하여 반환 |
| API 실패 시 전체 파이프라인 중단 | **재시도 로직 + 폴백 전략** 내장으로 안정성 확보 |
| 주소 형식 불일치로 API 호출 실패 빈번 | `normalize_address()` 함수로 **주소 정규화** 전처리 |

#### 구현 방법

**구현 파일**: 
- `src/tools/kakao_api_distance_tool.py` (입지 분석: 학교/교통/편의시설 거리)
- `src/tools/real_time_sale_search_api_tool.py` (국토부 실거래가 API)
- `src/tools/gemini_search_tool.py` (Gemini 2.5 Pro 검색)
- `src/tools/kostat_api.py` (통계청 API)
- `src/tools/kor_usa_rate.py` (한미 금리 조회)

#### API 오케스트레이션 흐름

```mermaid
flowchart TB
    subgraph Agent["Agent (LLM)"]
        A1["도구 선택 판단"]
        A2["tool_calls 생성"]
    end
    
    subgraph Tools["Tool 시스템"]
        T1["@tool 데코레이터"]
        T2["주소 정규화<br/>(서울시 → 서울특별시)"]
        T3["재시도 로직<br/>(3회)"]
    end
    
    subgraph APIs["외부 API"]
        API1["Kakao Maps API<br/>좌표/거리 계산"]
        API2["공공데이터포털<br/>실거래가 조회"]
        API3["Gemini 2.5 Pro<br/>웹 검색"]
        API4["KOSTAT API<br/>인구/주택 통계"]
        API5["ECOS/FRED<br/>금리 데이터"]
    end
    
    subgraph Response["응답 처리"]
        R1["JSON 형식 통일"]
        R2["에러 핸들링"]
        R3["Agent에 결과 반환"]
    end
    
    A1 --> A2 --> T1
    T1 --> T2 --> T3
    T3 --> API1 & API2 & API3 & API4 & API5
    API1 & API2 & API3 & API4 & API5 --> R1
    R1 --> R2 --> R3
    R3 --> A1
    
    style A1 fill:#e3f2fd,color:#000
    style T3 fill:#fff9c4,color:#000
    style R3 fill:#c8e6c9,color:#000
```

#### 코드 예시

**1. Kakao API 입지 분석 도구**

```python
# src/tools/kakao_api_distance_tool.py
@tool
def get_location_profile(address, radius=3000):
    """주소를 좌표로 변환하고 주변 입지를 조사"""
    coords = get_coordinates_with_retry(address)  # 주소 정규화 + 재시도
    return {
        "교육환경": {"학교": _get_school_info(coords), "학원": _get_academy_info(coords)},
        "교통여건": _get_transport_info(coords),
        "편의여건": {"대형마트": ..., "병원": ...},
        "자연환경": _get_nature_info(coords),
        "미래가치": _get_future_value_info(coords),
    }
```

**2. 국토부 실거래가 API 도구**

```python
# src/tools/real_time_sale_search_api_tool.py
@tool
def get_real_estate_price(address_or_apartment, ...):
    """아파트 매매 실거래가 조회 (최근 5년 역순 검색)"""
    lawd_cd = extract_region_code(address)      # 주소 → 법정동코드 변환
    apartment_name = extract_apartment_name_from_kakao(address)  # 아파트명 추출
    return search_latest_transaction(...)       # XML 파싱 + 평당가격 계산
```

**3. Gemini Search 도구**

```python
# src/tools/gemini_search_tool.py
def gemini_search(prompt: str):
    """Gemini 2.5 Pro로 실시간 검색 (3회 재시도)"""
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-pro", 
                contents=prompt
            )
            return response.text
        except Exception:
            time.sleep(2)
```

#### 핵심 기능

- Agent가 **필요에 따라 도구를 자율 선택**하여 호출
- 주소 정규화(`서울시` → `서울특별시`)로 **API 호출 성공률 향상**
- 실거래가 **최근 5년 역순 검색**으로 최신 거래 자동 추출
- 재시도 로직으로 **일시적 API 장애 대응**

**참고**: [Kakao 로컬 API](https://developers.kakao.com/docs/latest/ko/local/dev-guide), [국토부 실거래가 공개 API](https://www.data.go.kr/data/15057511/openapi.do), [Google Gemini API](https://ai.google.dev/gemini-api/docs)

---

### 5. think_tool 기반 Reflection(성찰) 메커니즘

#### 선택 이유

| 기존 방식의 한계 | 해결 필요성 |
|-----------------|------------|
| LLM이 한 번에 최종 답변을 생성하면 **검증 단계 없음** | 보고서 품질 보장을 위해 **자체 검증 단계** 필수 |
| 외부 검증자를 두면 비용 증가 | **동일 Agent 내부에서 성찰**하여 추가 비용 최소화 |
| 단순 프롬프트로 "검토해줘"라고 하면 형식적 응답만 생성 | **Tool 형태**로 강제하여 구조화된 성찰 결과 확보 |
| 성찰 결과가 최종 보고서에 반영 안 됨 | `apply_reflection` 노드에서 **피드백 기반 수정** 실행 |

#### 구현 방법

**구현 파일**: 
- `src/agents/analysis/location_insight_agent.py`
- `src/agents/analysis/nearby_market_agent.py`
- `src/agents/analysis/policy_agent.py`
- `src/agents/jung_min_jae/jung_min_jae_agent.py`

#### Reflection 흐름

```mermaid
flowchart TB
    subgraph SegmentWriting["세그먼트 작성"]
        S1["Segment 1 작성"]
        S2["Segment 2 작성"]
        S3["Segment 3 작성"]
        S4["Segment 4 작성"]
    end
    
    subgraph Merge["병합"]
        M["finalize_merge<br/>4개 세그먼트 병합"]
    end
    
    subgraph Reflection["Reflection 프로세스"]
        R1["reflection_prompt<br/>성찰 지시 프롬프트"]
        R2["reflect_agent<br/>LLM이 think_tool 호출"]
        R3["ToolNode<br/>think_tool 실행"]
        R4["apply_reflection<br/>피드백 반영 수정"]
    end
    
    subgraph Output["출력"]
        O["final_report<br/>최종 보고서"]
    end
    
    S1 --> S2 --> S3 --> S4
    S4 --> M
    M --> R1 --> R2 --> R3 --> R4
    R4 --> O
    
    style S1 fill:#e3f2fd,color:#000
    style R3 fill:#fff9c4,color:#000
    style O fill:#c8e6c9,color:#000
```

#### 코드 예시

**1. think_tool 정의**

```python
# src/agents/jung_min_jae/jung_min_jae_agent.py
@tool(parse_docstring=True)
def think_tool(reflection: str) -> str:
    """자체 검증(자아성찰) 수행 도구
    
    점검 기준:
    1. 핵심 인사이트의 근거가 명확한가
    2. 근거 데이터가 정확한가
    3. 주변 매매/분양 비교 시 정책/경제지표 반영했는가
    4. 불필요한 말이 없는가
    """
    return f"Reflection recorded: {reflection}"
```

**2. 피드백 적용**

```python
# src/agents/jung_min_jae/jung_min_jae_agent.py
def apply_reflection(state):
    draft = state.get(final_draft_key)
    feedback = extract_feedback_from_tool_message(state)
    
    if feedback.strip():
        editor_prompt = "아래 [초안]을 [피드백]을 반영해 수정하라..."
        revised = llm.invoke([
            editor_sys, 
            HumanMessage(content=f"[초안]\n{draft}\n\n[피드백]\n{feedback}")
        ])
        return {final_report_key: revised.content}
    return {final_report_key: draft}
```

#### 핵심 기능

- **Tool 형태**로 성찰을 강제하여 구조화된 검증 결과 확보
- 검증 체크리스트(데이터 정확성, 근거 명시, 수치 검증)를 **프롬프트에 내장**
- 성찰 결과가 **자동으로 최종 보고서에 반영**
- 분석 Agent(입지/시세/정책)에도 동일한 think_tool 패턴 적용

**참고**: [Reflexion 논문](https://arxiv.org/abs/2303.11366), [LangGraph ToolNode](https://langchain-ai.github.io/langgraph/reference/prebuilt/)

---

### 6. 정책 뉴스 웹 크롤링 + LLM 정제 파이프라인

#### 선택 이유

| 기존 방식의 한계 | 해결 필요성 |
|-----------------|------------|
| 정책 뉴스를 수동으로 수집하면 **시간 소모** 큼 | 크롤링 자동화로 최신 정책 뉴스 **실시간 수집** |
| 뉴스 원문에 광고/미래 전망 등 **노이즈** 포함 | LLM으로 **정책 핵심 내용만 추출**하여 정제 |
| BeautifulSoup만으로 복잡한 페이징 처리 어려움 | `__doPostBack` 기반 **ASP.NET 페이징 처리** 구현 |

#### 구현 방법

**구현 파일**: 
- `src/tools/estate_web_crawling_tool.py`

#### 크롤링 + LLM 정제 흐름

```mermaid
flowchart TB
    subgraph Crawling["웹 크롤링"]
        C1["Session 생성"]
        C2["첫 페이지 요청"]
        C3["ViewState/EventValidation 수집"]
        C4["__doPostBack으로 다음 페이지"]
        C5["기사 목록 수집"]
    end
    
    subgraph Parsing["기사 파싱"]
        P1["기사 상세 페이지 요청"]
        P2["제목/내용/날짜 추출"]
        P3["JSON 목록 생성"]
    end
    
    subgraph LLMRefine["LLM 정제"]
        L1["GPT-4o 호출"]
        L2["노이즈 제거<br/>(광고/미래전망)"]
        L3["정책 핵심만 추출"]
        L4["인코딩 오류 수정"]
    end
    
    subgraph Output["출력"]
        O["정제된 뉴스 JSON"]
    end
    
    C1 --> C2 --> C3 --> C4 --> C5
    C5 --> P1 --> P2 --> P3
    P3 --> L1 --> L2 --> L3 --> L4
    L4 --> O
    
    style C1 fill:#e3f2fd,color:#000
    style L1 fill:#fff9c4,color:#000
    style O fill:#c8e6c9,color:#000
```

#### 코드 예시

**1. ASP.NET 폼 기반 페이징 크롤링**

```python
# src/tools/estate_web_crawling_tool.py
def _collect_articles(max_page=3):
    session = requests.Session()
    soup = BeautifulSoup(response.text, "html.parser")
    form_inputs = _collect_form_inputs(soup)  # ViewState, EventValidation 등 수집
    
    while current_page < max_page:
        # __doPostBack 이벤트 타겟 추출
        target = _extract_event_target(anchor.get("href"))
        payload = {**form_inputs, "__EVENTTARGET": target}
        response = session.post(listing_url, data=payload)  # POST로 다음 페이지 요청
```

**2. LLM 기반 노이즈 제거**

```python
# src/tools/estate_web_crawling_tool.py
def collect_articles_result():
    articles = _collect_articles()
    
    llm_response = LLMProfile.dev_llm().invoke(f"""
        JSON 목록의 각 뉴스 content를 수정하세요:
        - 정책만 이야기하도록 수정
        - 불필요한 미래전망/주관적 내용 제거
        - title의 인코딩 오류 수정
        
        [강력 지침] JSON 형식으로만 답변
        {articles}
    """)
    
    return json.loads(clean_json(llm_response.content))
```

#### 핵심 기능

- **ASP.NET 폼 기반 페이징** 처리로 복잡한 웹사이트 크롤링
- Session 유지로 **인증/상태 관리** 처리
- LLM 정제로 **노이즈 제거 + 정책 핵심만 추출**
- JSON 마크다운 코드블록 자동 제거 + 파싱 에러 폴백 처리

**참고**: [BeautifulSoup 공식 문서](https://www.crummy.com/software/BeautifulSoup/bs4/doc/), [Requests 공식 문서](https://docs.python-requests.org/)

---

## 핵심 기술 요약

| 기술/기능 | 선택 이유 | 구현 방법 | 핵심 기능 |
|----------|----------|----------|----------|
| **LangGraph ReAct Agent** | 복잡한 분석에 동적 도구 호출 필요 | StateGraph + Conditional Edge + ToolNode | 자율적 도구 호출, 멀티스텝 추론, 병렬 노드 실행 |
| **PromptManager** | 프롬프트/코드 분리로 유지보수성 향상 | PromptType Enum + YAML + 세그먼트별 동적 로딩 | 코드 변경 없이 프롬프트 수정, 타입 안전성 |
| **하이브리드 검색 RAG** | 벡터 검색 + 키워드 검색 장점 결합 | PGVector + 가중치 기반 스코어 병합 | 정책 수치 정확 검색, 의미적 유사 문서 검색 |
| **다중 API Tool 시스템** | Agent가 외부 데이터 자율 수집 | @tool 래핑 + 주소 정규화 + 재시도 로직 | Kakao 입지, 국토부 실거래가, Gemini 검색 통합 |
| **think_tool Reflection** | 보고서 품질 자체 검증 | Tool 강제 호출 + 피드백 기반 수정 | 구조화된 성찰, 자동 피드백 반영 |
| **뉴스 크롤링 + LLM 정제** | 최신 정책 뉴스 자동 수집/정제 | ASP.NET 페이징 + LLM 노이즈 제거 | 실시간 수집, 정책 핵심만 추출 |

---

## 기술 스택

### AI & ML Framework

| 기술 | 용도 |
|-----|------|
| ![LangGraph](https://img.shields.io/badge/LangGraph-FF4785?style=flat) | 멀티에이전트 워크플로우 오케스트레이션 |
| ![LangChain](https://img.shields.io/badge/LangChain-00A67E?style=flat) | LLM 통합, 도구 래핑, RAG 파이프라인 |
| ![OpenAI](https://img.shields.io/badge/GPT--4o-412991?style=flat&logo=openai&logoColor=white) | 보고서 작성, 분석 추론 |
| ![Gemini](https://img.shields.io/badge/Gemini_2.5-8E75B2?style=flat&logo=google&logoColor=white) | 실시간 웹 검색, 주변 아파트 조사 |
| ![Claude](https://img.shields.io/badge/Claude-191919?style=flat) | 복잡한 분석 태스크 |

### Backend & Database

| 기술 | 용도 |
|-----|------|
| ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white) | REST API 서버 |
| ![PostgreSQL](https://img.shields.io/badge/PostgreSQL+pgvector-316192?style=flat&logo=postgresql&logoColor=white) | 벡터 데이터베이스 (RAG) |
| ![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white) | 웹 UI (챗봇 인터페이스) |

### 외부 API

| 서비스 | 용도 |
|-------|------|
| Kakao Maps API | 좌표 변환, 주변 시설 거리 계산 |
| KOSTAT (통계청) | 인구 이동, 노후 주택 통계 |
| ECOS (한국은행) | 한국 금리 데이터 |
| FRED (미국 연준) | 미국 금리 데이터 |
| R-ONE (부동산원) | 매매수급지수 |
| 공공데이터포털 | 실거래가 조회 |
| Perplexity AI | 실시간 웹 검색 |

### 인프라 구성

| 구성 요소 | 서비스 | 용도 |
|----------|--------|------|
| **Vector DB** | Supabase PostgreSQL + PGVector | 정책 문서 임베딩 저장 및 검색 |
| **Backend API** | Railway (FastAPI) | Agent 실행 API 서버 |
| **Frontend** | Streamlit Community Cloud | 사용자 인터페이스 |
| **LLM** | OpenAI GPT-4o, Gemini 2.5 Pro | Agent 추론, 검색, 정제 |

---

## 빠른 시작 (5분)

### 사전 요구사항

- Python 3.12 이상
- Docker (PostgreSQL용)
- API 키: OpenAI, Gemini, Kakao (최소 필수)

### 1. 저장소 클론 및 의존성 설치

```bash
git clone https://github.com/YOUR_USERNAME/ALL-FOR-ONE.git
cd ALL-FOR-ONE

# uv 사용 (권장)
pip install uv
uv sync

# 또는 pip 사용
pip install -r requirements.txt
```

### 2. PostgreSQL + pgvector 실행

```bash
docker run -d \
  --name rag_pg \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=ragdb \
  -p 5432:5432 \
  ankane/pgvector:latest

# pgvector 확장 활성화
docker exec -it rag_pg psql -U postgres -d ragdb -c 'CREATE EXTENSION IF NOT EXISTS vector;'
```

### 3. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열어 API 키를 입력합니다:

```env
# 필수
POSTGRES_URL=postgresql://postgres:postgres@localhost:5432/ragdb
OPENAI_API_KEY=sk-proj-...
GEMINI_API_KEY=AIza...
KAKAO_REST_API_KEY=...

# 권장 (더 풍부한 분석)
ANTHROPIC_API_KEY=sk-ant-...
PERPLEXITY_API_KEY=pplx-...
ECOS_API_KEY=...
```

### 4. Streamlit 챗봇 실행

```bash
streamlit run src/chatbot/frontend/streamlit_chat.py
```

브라우저에서 `http://localhost:8501` 접속 후:
1. 사이드바에 주소/타입/세대수 입력
2. "분석 시작" 클릭
3. 7개 에이전트가 순차적으로 분석 진행
4. 이메일로 보고서 수신

---

## 상세 설치 가이드

### 환경 변수 전체 목록

<details>
<summary>클릭하여 펼치기</summary>

```env
# ═══════════════════════════════════════════════════════════
# 데이터베이스 (필수)
# ═══════════════════════════════════════════════════════════
POSTGRES_URL=postgresql://postgres:postgres@localhost:5432/ragdb

# ═══════════════════════════════════════════════════════════
# LLM 서비스 (최소 1개 필수, OpenAI 권장)
# ═══════════════════════════════════════════════════════════
OPENAI_API_KEY=sk-proj-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
GEMINI_API_KEY=your-gemini-key-here

# ═══════════════════════════════════════════════════════════
# 검색 서비스 (권장)
# ═══════════════════════════════════════════════════════════
TAVILY_API_KEY=tvly-your-key-here
PERPLEXITY_API_KEY=pplx-your-key-here

# ═══════════════════════════════════════════════════════════
# 한국 부동산 API (데이터 수집용)
# ═══════════════════════════════════════════════════════════
KAKAO_REST_API_KEY=your-kakao-key-here
REAL_TIME_SALE_SEARCH_API_KEY=your-key-here
GONG_GONG_DATA_API_KEY=your-key-here
R_ONE_API_KEY=your-key-here
MOLIT_API_KEY=your-key-here

# ═══════════════════════════════════════════════════════════
# 통계 API (선택)
# ═══════════════════════════════════════════════════════════
KOSIS_CONSUMER_KEY=your-key-here
KOSIS_CONSUMER_SECRET_KEY=your-key-here
ECOS_API_KEY=your-key-here
FRED_API_KEY=your-key-here

# ═══════════════════════════════════════════════════════════
# 디버깅 (선택)
# ═══════════════════════════════════════════════════════════
LANGSMITH_API_KEY=lsv2_your-key-here
LANGSMITH_TRACING=false
```

</details>

### RAG 데이터 인덱싱

벡터 검색을 사용하려면 데이터를 사전에 인덱싱해야 합니다:

```bash
# Jupyter 노트북으로 인덱싱 실행
jupyter notebook src/tools/rag/indexing/
```

각 `*_indexing.ipynb` 파일을 실행하여 정책 문서, 청약 FAQ 등을 벡터 스토어에 저장합니다.

---

## 사용 방법

### 1. Streamlit 챗봇 (권장)

```bash
streamlit run src/chatbot/frontend/streamlit_chat.py
```

### 2. FastAPI 서버

```bash
uvicorn src.chatbot.backend.main:app --reload --port 8000
```

API 문서: `http://localhost:8000/docs`

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/chat` | POST | 챗봇 대화 (스트리밍) |
| `/analyze` | POST | 부동산 분석 실행 |
| `/health` | GET | 서버 상태 확인 |

### 3. Python 코드로 직접 사용

```python
from agents.main.main_agent import main_graph
from agents.state.start_state import StartInput

# 입력 데이터 준비
start_input = StartInput(
    target_area="서울특별시 강남구 역삼동",
    total_units="500세대",
    main_type="84제곱미터",
    email="user@example.com"
)

# 메인 그래프 실행
result = main_graph.invoke({
    "start_input": start_input.model_dump(),
    "messages": []
})

# 최종 보고서 확인
print(result["final_report"])
```

---

## 프로젝트 구조

```
ALL-FOR-ONE/
├── src/
│   ├── agents/                    # 에이전트 정의
│   │   ├── main/                  # 메인 워크플로우 (진입점)
│   │   │   └── main_agent.py      # LangGraph 메인 그래프
│   │   ├── analysis/              # 7개 분석 에이전트
│   │   │   ├── analysis_graph.py       # 병렬 실행 그래프
│   │   │   ├── policy_agent.py         # 정책 분석
│   │   │   ├── location_insight_agent.py    # 입지 분석
│   │   │   ├── nearby_market_agent.py  # 주변 시장
│   │   │   ├── population_insight_agent.py  # 인구 분석
│   │   │   ├── supply_demand_agent.py  # 수급 분석
│   │   │   ├── unsold_insight_agent.py # 미분양 분석
│   │   │   └── housing_faq_agent.py    # 청약 FAQ
│   │   ├── jung_min_jae/          # 보고서 작성 에이전트
│   │   │   └── jung_min_jae_agent.py   # 4단계 세그먼트 + Reflection
│   │   └── state/                 # LangGraph 상태 정의
│   │       ├── start_state.py     # 사용자 입력 상태
│   │       ├── main_state.py      # 메인 그래프 상태
│   │       └── analysis_state.py  # 분석 에이전트 상태
│   │
│   ├── prompts/                   # YAML 기반 프롬프트 관리
│   │   ├── PromptManager.py       # 프롬프트 로더
│   │   ├── PromptType.py          # Enum 정의
│   │   ├── jung_min_jae.yaml      # 보고서 작성 프롬프트
│   │   ├── analysis_policy.yaml   # 정책 분석 프롬프트
│   │   ├── analysis_location_insight.yaml  # 입지 분석 프롬프트
│   │   └── *.yaml                 # 기타 에이전트 프롬프트
│   │
│   ├── tools/                     # 에이전트 도구
│   │   ├── kakao_api_distance_tool.py   # Kakao API 입지 분석
│   │   ├── gemini_search_tool.py        # Gemini AI 검색
│   │   ├── perplexity_search_tool.py    # Perplexity 검색
│   │   ├── kostat_api.py                # 통계청 API
│   │   ├── kor_usa_rate.py              # 한미 금리 조회
│   │   ├── real_time_sale_search_api_tool.py  # 실거래가 API
│   │   ├── estate_web_crawling_tool.py  # 정책 뉴스 크롤링
│   │   ├── send_gmail.py                # 이메일 발송
│   │   ├── context_to_csv.py            # CSV 생성 + Drive 업로드
│   │   └── rag/                         # RAG 관련 도구
│   │       ├── retriever/               # 하이브리드 검색 리트리버
│   │       │   └── policy_pdf_retriever.py
│   │       ├── document_loader/         # 문서 로더
│   │       ├── chunker/                 # 텍스트 청커
│   │       └── indexing/                # 벡터 인덱싱 노트북
│   │
│   ├── chatbot/                   # 챗봇 인터페이스
│   │   ├── frontend/              # Streamlit UI
│   │   │   └── streamlit_chat.py
│   │   └── backend/               # FastAPI 서버
│   │       └── main.py
│   │
│   ├── data/                      # 로컬 데이터 파일
│   │   ├── policy_factors/        # 정책 PDF
│   │   ├── population_insight/    # 인구 데이터
│   │   ├── supply_demand/         # 수급 데이터
│   │   └── unsold_units/          # 미분양 데이터
│   │
│   └── utils/                     # 유틸리티
│       ├── llm.py                 # LLM 프로필 관리
│       └── google_drive_uploader.py
│
├── docs/                          # 상세 문서
│   ├── 핵심기술.md                 # 기술 상세 설명
│   └── API_FLOW.md                # 데이터 흐름 문서
│
├── output/                        # 생성된 보고서 샘플
├── .env.example                   # 환경 변수 템플릿
├── pyproject.toml                 # Python 의존성
├── docker-compose.yml             # Docker 설정
└── README.md                      # 이 파일
```

---

## 관련 문서

| 문서 | 설명 |
|------|------|
| [docs/핵심기술.md](./docs/핵심기술.md) | ReAct 패턴, 하이브리드 RAG, think_tool 등 핵심 기술 상세 |
| [docs/API_FLOW.md](./docs/API_FLOW.md) | 7개 에이전트의 데이터 흐름 및 API 연동 상세 |
| [PROJECT_ARCHITECTURE.md](./PROJECT_ARCHITECTURE.md) | 전체 시스템 아키텍처 |
| [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md) | 폴더 구조 상세 설명 |
| [AGENT_TECH_STACK.md](./AGENT_TECH_STACK.md) | 에이전트별 기술 스택 |

---

## 감사의 말

이 프로젝트는 다음 오픈소스 프로젝트들을 활용하였습니다:

- [LangGraph](https://github.com/langchain-ai/langgraph) - 멀티에이전트 워크플로우
- [LangChain](https://github.com/langchain-ai/langchain) - LLM 통합 프레임워크
- [pgvector](https://github.com/pgvector/pgvector) - PostgreSQL 벡터 확장
- [Streamlit](https://github.com/streamlit/streamlit) - 웹 UI 프레임워크
- [FastAPI](https://github.com/tiangolo/fastapi) - 고성능 API 프레임워크

---

## 참고 자료

- [LangGraph 공식 문서](https://langchain-ai.github.io/langgraph/)
- [LangChain Tools](https://python.langchain.com/docs/modules/tools/)
- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)
- [Reflexion: Language Agents with Verbal Reinforcement Learning](https://arxiv.org/abs/2303.11366)
- [PGVector](https://github.com/pgvector/pgvector)
- [Kakao Developers](https://developers.kakao.com/)
- [국토교통부 실거래가 공개시스템](https://rt.molit.go.kr/)

---

<div align="center">

**[Back to Top](#all-for-one-ai-멀티에이전트-부동산-분석-시스템)**

</div>
