# Tech Stack

> **AI Multi-Agent 부동산 분양성 검토 솔루션** — Analysis Part 담당 기술 스택
>
> 3개 분석 에이전트(입지분석 / 주변시세 / 정책분석) 설계 및 구현,
> RAG 파이프라인 전 구간(Loader → Chunker → Retriever) 직접 설계,
> FastAPI 백엔드 배포 및 Streamlit 프론트엔드 연동까지 End-to-End 담당

---

## Multi-Agent Orchestration

![LangGraph](https://img.shields.io/badge/LangGraph-1.0-4B8BBE?style=for-the-badge&logo=python&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-1.0-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)

| 기술 | 적용 내용 |
|:---|:---|
| **StateGraph** | 에이전트별 독립 상태 그래프 설계, 노드 간 조건부 라우팅(Conditional Edge) 구현 |
| **ToolNode** | LLM Tool Calling 기반 도구 자율 선택 및 실행 파이프라인 |
| **TypedDict State** | `Annotated` 타입 기반 상태 스키마로 에이전트 간 데이터 흐름 제어 |
| **Reflection Pattern** | `think_tool`을 통한 에이전트 자기 점검 루프 — 데이터 품질 및 수치 검증 후 최종 출력 |
| **Parallel Execution** | 입지분석 · 주변시세 · 정책분석 3개 에이전트 병렬 실행 구조 설계 |

---

## LLM Integration & Multi-Model Strategy

![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4.1_|_GPT--5-412991?style=for-the-badge&logo=openai&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google-Gemini_2.5_Pro-4285F4?style=for-the-badge&logo=google&logoColor=white)
![Anthropic](https://img.shields.io/badge/Anthropic-Claude_Sonnet_4.5-D4A574?style=for-the-badge&logo=anthropic&logoColor=white)
![Perplexity](https://img.shields.io/badge/Perplexity-AI_Search-20B2AA?style=for-the-badge)

| 기술 | 적용 내용 |
|:---|:---|
| **Role-based LLM Profile** | 태스크 특성별 모델 분리 — 분석(GPT-4.1) · 보고서(GPT-5) · 렌더링(Claude Sonnet 4.5) |
| **RetryableChatOpenAI** | Exponential Backoff 자동 재시도(5회) — sync / async 모두 지원하는 커스텀 LLM 래퍼 |
| **Gemini Grounding Search** | Google Gemini API 기반 실시간 웹 그라운딩 검색 — 지역 개발 호재 및 최신 정보 수집 |
| **Perplexity Search** | 최신 정보 보완용 실시간 검색 도구 — 에이전트가 Tool Calling으로 자율 호출 |

---

## RAG Pipeline

### Retrieval Strategy

![PGVector](https://img.shields.io/badge/PGVector-Semantic_Search-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![BM25](https://img.shields.io/badge/BM25-Keyword_Search-FF6F00?style=for-the-badge)
![Hybrid](https://img.shields.io/badge/Hybrid-70%25_Semantic_+_30%25_Keyword-9C27B0?style=for-the-badge)

| 기술 | 적용 내용 |
|:---|:---|
| **Hybrid Search** | 시맨틱(70%) + 키워드(30%) 가중 결합 — 부동산 도메인 전문 용어(LTV, DTI, DSR 등) 검색 최적화 |
| **PGVector Similarity** | OpenAI `text-embedding-3-large` 임베딩 기반 벡터 유사도 검색 |
| **BM25 Retriever** | 통계 데이터(전세가 · 매매가 · GRDP 등) 대상 키워드 정밀 검색 |
| **LLM-Assisted Retrieval** | LLM으로 쿼리에서 지역명(자치구) 사전 추출 후 검색 범위 축소 및 정확도 향상 |

### Document Processing

![PyMuPDF](https://img.shields.io/badge/PyMuPDF-PDF_Loader-CC0000?style=for-the-badge)
![PDFPlumber](https://img.shields.io/badge/PDFPlumber-Table_Extraction-2196F3?style=for-the-badge)
![CSVLoader](https://img.shields.io/badge/CSVLoader-Structured_Data-4CAF50?style=for-the-badge)

| 기술 | 적용 내용 |
|:---|:---|
| **Adaptive Loader** | 문서 특성에 따라 최적 PDF 로더 자동 선택 (PyMuPDF → Unstructured → PDFPlumber) |
| **PolicyPDFLoader** | 정책 PDF 전용 로더 — 정규식 기반 날짜 · 정책 유형 · 제목 메타데이터 자동 추출 |
| **MD5 Deduplication** | 해시 기반 문서 중복 제거로 인덱싱 비용 절감 |
| **Multi-Format Support** | PDF · Markdown · JSON · CSV 통합 처리 파이프라인 |

### Text Splitting & Chunking

![RecursiveTextSplitter](https://img.shields.io/badge/Recursive-Text_Splitter-FF9800?style=for-the-badge)
![Semantic Chunking](https://img.shields.io/badge/Semantic-Cosine_Similarity-673AB7?style=for-the-badge)

| 기술 | 적용 내용 |
|:---|:---|
| **Adaptive Chunker** | 문서 평균 길이에 따라 Character / Token 기반 분할 전략 자동 전환 |
| **Semantic Chunker** | Cosine Similarity + Sigmoid 임계값 기반 의미 단위 문단 클러스터링 |

---

## Prompt Engineering

![YAML](https://img.shields.io/badge/YAML-Template_Management-CB171E?style=for-the-badge&logo=yaml&logoColor=white)

| 기술 | 적용 내용 |
|:---|:---|
| **YAML 기반 프롬프트 관리** | System / Human 프롬프트를 코드에서 완전 분리 — 코드 변경 없이 프롬프트 독립 수정 가능 |
| **PromptManager** | `PromptType` Enum 기반 중앙집중식 프롬프트 로딩 시스템 |
| **도메인 특화 설계** | 입지분석 · 주변시세 · 정책분석 · 최종보고서 4개 전문 영역별 프롬프트 설계 (총 677줄+) |
| **input_variables 바인딩** | 런타임 데이터(검색 결과 · API 응답)를 프롬프트 템플릿에 동적 주입 |

---

## Tool Use & External API Integration

![Kakao](https://img.shields.io/badge/Kakao-Local_API-FFCD00?style=for-the-badge&logo=kakao&logoColor=black)
![MOLIT](https://img.shields.io/badge/국토교통부-실거래가_API-003876?style=for-the-badge)
![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup4-Web_Crawling-43B02A?style=for-the-badge)
![Gemini Search](https://img.shields.io/badge/Gemini-Grounding_Search-4285F4?style=for-the-badge&logo=google&logoColor=white)

| 기술 | 적용 내용 |
|:---|:---|
| **Kakao Local API** | 주소-좌표 변환 · 카테고리 검색(학교 · 지하철 · 마트 · 병원) · 키워드 검색(공원 · 재건축) |
| **국토부 실거래가 API** | 아파트 매매 실거래가 실시간 조회 — 공공데이터포털 OpenAPI + XML 파싱 |
| **Web Crawling** | BeautifulSoup 기반 주택 정책 기사 크롤링 + LLM 요약 파이프라인 |
| **LangChain @tool** | 모든 외부 도구를 LangChain Tool 규격으로 래핑 — LLM이 Tool Calling으로 자율 호출 |

---

## Vector Database & Storage

![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-Cloud_DB-3FCF8E?style=for-the-badge&logo=supabase&logoColor=white)
![OpenAI Embeddings](https://img.shields.io/badge/OpenAI-text--embedding--3--large-412991?style=for-the-badge&logo=openai&logoColor=white)

| 기술 | 적용 내용 |
|:---|:---|
| **PostgreSQL + pgvector** | 벡터 유사도 검색 확장 모듈 기반 벡터 데이터베이스 |
| **Supabase** | 클라우드 PostgreSQL 호스팅 + Connection Pooling |
| **Thread-Safe Singleton** | `threading.Lock` 기반 벡터 스토어 팩토리 — 동시 요청 안전성 보장 |
| **Collection 분리** | 데이터 도메인별 독립 컬렉션 운영 (인구 · 정책 · FAQ · 주택규정 등) |

---

## Backend API

![FastAPI](https://img.shields.io/badge/FastAPI-0.121-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?style=for-the-badge&logo=pydantic&logoColor=white)
![Uvicorn](https://img.shields.io/badge/Uvicorn-ASGI-499848?style=for-the-badge)

| 기술 | 적용 내용 |
|:---|:---|
| **Async Job Queue** | `asyncio.create_task` 기반 비동기 작업 큐 — 장시간 에이전트 실행 비동기 처리 |
| **Polling Pattern** | `POST /invoke` → `GET /status/{job_id}` → `GET /result/{job_id}` |
| **CORS** | Streamlit Cloud ↔ Railway 도메인 간 Cross-Origin 통신 설정 |

---

## Deployment & Infrastructure

![Docker](https://img.shields.io/badge/Docker-Multi--Stage-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Railway](https://img.shields.io/badge/Railway-Backend-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)
![Streamlit Cloud](https://img.shields.io/badge/Streamlit-Cloud-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)

| 기술 | 적용 내용 |
|:---|:---|
| **Multi-Stage Docker** | Builder / Runtime 분리로 이미지 경량화 (Python 3.12-slim + 한글 폰트 포함) |
| **Railway** | FastAPI 백엔드 클라우드 배포 + 환경변수 관리 |
| **Streamlit Community Cloud** | 프론트엔드 배포 — `FASTAPI_URL`에 Railway 도메인 연결 |
| **docker-compose** | PostgreSQL(pgvector) + App 컨테이너 로컬 개발 환경 구성 |

---

## Core Language & Ecosystem

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![uv](https://img.shields.io/badge/uv-Package_Manager-DE5C43?style=for-the-badge)
![dotenv](https://img.shields.io/badge/.env-Secret_Management-ECD53F?style=for-the-badge)
