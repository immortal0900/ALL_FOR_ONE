# ALL-FOR-ONE: AI-Powered Real Estate Research Platform

> 멀티에이전트 시스템을 활용한 부동산 시장 분석 및 리서치 보고서 자동 생성 플랫폼

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![LangChain](https://img.shields.io/badge/LangChain-Agents-00A67E?style=flat)](https://python.langchain.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Workflow-FF4785?style=flat)](https://langchain-ai.github.io/langgraph/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-316192?style=flat&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io/)

---

## 목차

- [프로젝트 소개](#프로젝트-소개)
- [주요 기능](#주요-기능)
- [기술 스택](#기술-스택)
- [시스템 아키텍처](#시스템-아키텍처)
- [빠른 시작](#빠른-시작)
- [설치 가이드](#설치-가이드)
- [사용 방법](#사용-방법)
- [프로젝트 구조](#프로젝트-구조)
- [API 문서](#api-문서)
- [추가 문서](#추가-문서)
- [라이선스](#라이선스)
- [연락처](#연락처)

---

## 프로젝트 소개

**ALL-FOR-ONE**은 7개의 전문 AI 에이전트가 협업하여 부동산 시장을 다각도로 분석하고, 종합적인 리서치 보고서를 자동으로 생성하는 멀티에이전트 시스템입니다.

### 프로젝트 배경

부동산 시장 분석에는 입지, 인구 통계, 경제 지표, 정책 변화 등 다양한 요소를 종합적으로 고려해야 합니다. 각 분야의 전문가처럼 작동하는 AI 에이전트들이 병렬로 데이터를 수집하고 분석하며, 이를 하나의 통합된 보고서로 작성하는 자동화 시스템을 구축했습니다.

### 핵심 특징

- **7개 전문 AI 에이전트**: 입지, 인구, 경제, 정책, 수급, 미분양, 주변시세 분석
- **병렬 처리**: LangGraph 기반 워크플로우로 효율적인 분석
- **RAG 시스템**: PostgreSQL + pgvector를 활용한 벡터 검색
- **다양한 데이터 소스**: 공공 API, 웹 크롤링, 로컬 데이터베이스 통합
- **자동 보고서 생성**: 세그먼트별 작성 및 자체 검증 시스템
- **대화형 챗봇**: Streamlit 기반 사용자 인터페이스

---

## 주요 기능

### 1. 멀티에이전트 분석 시스템

7개의 전문 에이전트가 병렬로 실행되어 각 분야를 심층 분석합니다:

| 에이전트 | 분석 영역 | 주요 데이터 소스 |
|---------|---------|----------------|
| **입지 분석** | 교통, 교육, 편의시설 | Kakao API, Gemini AI |
| **정책 분석** | 부동산 정책, 규제 변화 | 웹 크롤링, RAG 검색 |
| **수급 분석** | 공급/수요 균형, 거래량 | KOSTAT, R-ONE, ECOS API |
| **미분양 분석** | 미분양 현황 및 추이 | 로컬 CSV 데이터 |
| **인구 분석** | 인구 구조 및 이동 추세 | KOSTAT API, PostgreSQL |
| **주변 시장** | 인근 매매/분양 시세 | 공공데이터포털, Perplexity AI |
| **청약 FAQ** | 청약 규칙 및 조건 | RAG 벡터 검색 |

### 2. 지능형 보고서 생성

- **세그먼트별 작성**: 3단계 세그먼트로 구조화된 보고서
- **자체 검증**: 보고서 완성도 평가 및 재작성
- **컨텍스트 관리**: RAG 기반 관련 문서 자동 참조

### 3. 대화형 인터페이스

- **Streamlit 챗봇**: 직관적인 웹 기반 UI
- **실시간 응답**: 스트리밍 방식으로 답변 생성
- **세션 관리**: 대화 내역 저장 및 불러오기

---

## 기술 스택

### AI & ML Framework

![LangChain](https://img.shields.io/badge/LangChain-00A67E?style=for-the-badge&logo=chainlink&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-FF4785?style=for-the-badge)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)
![Anthropic](https://img.shields.io/badge/Anthropic-191919?style=for-the-badge)
![Google Gemini](https://img.shields.io/badge/Google_Gemini-8E75B2?style=for-the-badge&logo=google&logoColor=white)

### 데이터베이스

![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![pgvector](https://img.shields.io/badge/pgvector-336791?style=for-the-badge)

### 백엔드 & API

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python_3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)

### 프론트엔드

![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)

### 외부 API & 서비스

- **Kakao Maps API**: 지도, 좌표, 거리 계산
- **Perplexity AI**: 실시간 웹 검색
- **KOSTAT (통계청)**: 인구, 주택 통계
- **한국은행 (ECOS)**: 금리 데이터
- **FRED**: 미국 금리 데이터
- **R-ONE (부동산원)**: 매매수급지수
- **공공데이터포털**: 실거래가 조회

---

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                        사용자 입력                             │
│                   (주소, 규모, 타입 등)                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    Main Agent                                │
│              (전체 워크플로우 조율)                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 Analysis Graph (병렬 실행)                      │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │입지 분석  │ │정책 분석  │ │수급 분석  │ │미분양    │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                  │
│  │인구 분석  │ │주변시장   │ │청약 FAQ  │                  │
│  └──────────┘ └──────────┘ └──────────┘                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              보고서 작성 Agent                                  │
│     (7개 분석 결과 종합 → 구조화된 보고서 생성)                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  최종 리서치 보고서                              │
└─────────────────────────────────────────────────────────────┘
```

**상세 문서**:
- [PROJECT_ARCHITECTURE.md](./PROJECT_ARCHITECTURE.md) - 전체 아키텍처 및 워크플로우
- [AGENT_DATA_SOURCES.md](./AGENT_DATA_SOURCES.md) - 각 에이전트의 데이터 출처 분석

---

## 빠른 시작

### 필수 요구사항

- Python 3.11 이상
- PostgreSQL 14 이상 (pgvector 확장 지원)
- Docker (권장)
- 다음 서비스의 API 키:
  - OpenAI API Key
  - Anthropic API Key (Claude)
  - Google Gemini API Key
  - Kakao REST API Key
  - 공공데이터포털 API Key

### 1분 만에 실행하기

```bash
# 1. 저장소 클론
git clone https://github.com/YOUR_USERNAME/ALL-FOR-ONE.git
cd ALL-FOR-ONE

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일을 열어 API 키 입력

# 3. PostgreSQL + pgvector 실행 (Docker)
docker run -d \
  --name rag_pg \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=ragdb \
  -p 5432:5432 \
  ankane/pgvector:latest

# 4. pgvector 확장 활성화
docker exec -it rag_pg psql -U postgres -d ragdb -c 'CREATE EXTENSION IF NOT EXISTS vector;'

# 5. Python 의존성 설치
pip install -r requirements.txt

# 6. Streamlit 챗봇 실행
streamlit run src/chatbot/frontend/streamlit_chat.py
```

브라우저에서 `http://localhost:8501`로 접속하여 챗봇을 사용할 수 있습니다.

---

## 설치 가이드

### 1. Python 환경 설정

```bash
# Python 3.11+ 설치 확인
python --version

# 가상환경 생성 (선택사항)
python -m venv .venv

# 가상환경 활성화
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. PostgreSQL + pgvector 설정

#### Docker 사용 (권장)

```bash
# PostgreSQL + pgvector 컨테이너 실행
docker run -d \
  --name rag_pg \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=ragdb \
  -p 5432:5432 \
  -v $(pwd)/pgdata:/var/lib/postgresql/data \
  ankane/pgvector:latest

# pgvector 확장 활성화
docker exec -it rag_pg psql -U postgres -d ragdb -c 'CREATE EXTENSION IF NOT EXISTS vector;'

# 확인
docker exec -it rag_pg psql -U postgres -d ragdb -c '\dx'
```

#### 로컬 PostgreSQL 사용

```sql
-- psql 접속 후
CREATE EXTENSION IF NOT EXISTS vector;
```

### 4. 환경 변수 설정

`.env.example` 파일을 `.env`로 복사하고 API 키를 입력합니다:

```bash
cp .env.example .env
```

**필수 환경 변수**:

```env
# LLM 서비스
OPENAI_API_KEY=sk-proj-your-openai-api-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here
GEMINI_API_KEY=your-gemini-api-key-here

# 검색 서비스
TAVILY_API_KEY=tvly-your-tavily-api-key-here
PERPLEXITY_API_KEY=pplx-your-perplexity-api-key-here

# 한국 부동산 API
REAL_TIME_SALE_SEARCH_API_KEY=your-real-time-sale-api-key-here
KAKAO_REST_API_KEY=your-kakao-rest-api-key-here

# 통계 API
KOSIS_CONSUMER_KEY=your-kosis-consumer-key-here
KOSIS_CONSUMER_SECRET_KEY=your-kosis-consumer-secret-key-here
ECOS_API_KEY=your-ecos-api-key-here
FRED_API_KEY=your-fred-api-key-here

# 데이터베이스
POSTGRES_URL=postgresql://postgres:postgres@localhost:5432/ragdb

# LangSmith (선택사항 - 디버깅용)
LANGSMITH_API_KEY=lsv2_your-langsmith-api-key-here
LANGSMITH_TRACING=false
```

### 5. RAG 데이터 인덱싱 (선택사항)

벡터 검색을 사용하려면 데이터를 인덱싱해야 합니다:

```bash
# Jupyter 노트북으로 인덱싱 실행
jupyter notebook src/tools/rag/indexing/
```

각 `*_indexing.ipynb` 파일을 실행하여 데이터를 벡터 스토어에 저장합니다.

---

## 사용 방법

### 1. Streamlit 챗봇 사용

```bash
streamlit run src/chatbot/frontend/streamlit_chat.py
```

브라우저에서 `http://localhost:8501`로 접속하여:

1. 좌측 사이드바에서 분석 대상 정보 입력
   - 주소
   - 세대수
   - 타입 (예: 84㎡)
2. "분석 시작" 버튼 클릭
3. 7개 에이전트가 순차적으로 분석 진행
4. 최종 보고서 확인 및 다운로드

### 2. FastAPI 서버 실행

```bash
uvicorn src.chatbot.backend.main:app --reload
```

API 문서: `http://localhost:8000/docs`

### 3. Python 코드로 직접 사용

```python
from agents.main.main_agent import main_graph
from agents.state.start_state import StartInput

# 입력 데이터 준비
start_input = StartInput(
    target_area="서울특별시 강남구 역삼동",
    total_units=500,
    scale="중형",
    main_type="84㎡"
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
│   ├── agents/              # 에이전트 관리
│   │   ├── main/           # 메인 워크플로우
│   │   ├── analysis/       # 7개 분석 에이전트
│   │   └── state/          # LangGraph 상태 정의
│   ├── prompts/            # YAML 기반 프롬프트 관리
│   ├── tools/              # 에이전트 도구
│   │   ├── rag/           # RAG 관련 도구
│   │   └── *.py           # 각종 API 도구
│   ├── data/              # 데이터 파일
│   ├── chatbot/           # 챗봇 인터페이스
│   │   ├── frontend/      # Streamlit UI
│   │   └── backend/       # FastAPI 서버
│   └── utils/             # 유틸리티 함수
├── docs/                  # 추가 문서
├── .env.example           # 환경 변수 템플릿
├── requirements.txt       # Python 의존성
└── README.md             # 이 파일
```

**상세 문서**: [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md)

---

## API 문서

### FastAPI 엔드포인트

서버 실행 후 `http://localhost:8000/docs`에서 Swagger UI를 확인할 수 있습니다.

**주요 엔드포인트**:

- `POST /chat`: 챗봇 대화 (스트리밍)
- `POST /analyze`: 부동산 분석 실행
- `GET /health`: 서버 상태 확인

---

## 추가 문서

프로젝트의 다양한 측면에 대한 상세 문서를 제공합니다:

| 문서 | 설명 |
|------|------|
| [PROJECT_ARCHITECTURE.md](./PROJECT_ARCHITECTURE.md) | 전체 시스템 아키텍처 및 워크플로우 |
| [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md) | 폴더 구조 및 파일 설명 |
| [AGENT_DATA_SOURCES.md](./AGENT_DATA_SOURCES.md) | 각 에이전트의 데이터 출처 분석 |
| [AGENT_TECH_STACK.md](./AGENT_TECH_STACK.md) | 에이전트별 기술 스택 정리 |

---

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.



---

## 감사의 말

이 프로젝트는 다음 오픈소스 프로젝트들의 도움을 받았습니다:

- [LangChain](https://github.com/langchain-ai/langchain) - 에이전트 프레임워크
- [LangGraph](https://github.com/langchain-ai/langgraph) - 워크플로우 오케스트레이션
- [pgvector](https://github.com/pgvector/pgvector) - PostgreSQL 벡터 확장
- [Streamlit](https://github.com/streamlit/streamlit) - 웹 UI 프레임워크

---

<div align="center">


[⬆ Back to Top](#all-for-one-ai-powered-real-estate-research-platform)

</div>
