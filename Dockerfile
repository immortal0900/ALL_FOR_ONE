# RAG Commander - FastAPI Docker Image
# 멀티스테이지 빌드로 이미지 크기 최적화

# 빌드 스테이지
FROM python:3.12-slim as builder

WORKDIR /build

# 빌드에 필요한 시스템 패키지만 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libcairo2-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 의존성 파일 복사
COPY pyproject.toml ./
COPY README.md ./

# Python 의존성 설치 (서버 런타임에 필요한 패키지만)
# Railway 캐시 마운트: id=s/<SERVICE_ID>-<경로> 형식 필수 (공식 문서)
# --no-cache-dir 제거: 캐시 마운트에 pip 다운로드 파일을 저장하여 2회차 빌드 가속
RUN --mount=type=cache,id=s/714ca360-aa98-41ee-9a7a-e383f637ab4d-/root/.cache/pip,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install \
    fastapi>=0.121.0 \
    geopy>=2.4.1 \
    google-api-python-client>=2.0.0 \
    google-auth-oauthlib>=1.2.3 \
    google-genai>=1.47.0 \
    langchain>=1.0.3 \
    langchain-anthropic>=1.0.0 \
    langchain-community>=0.4.1 \
    langchain-core>=1.0.2 \
    langchain-experimental>=0.0.42 \
    langchain-google-genai>=2.1.0 \
    langchain-mcp-adapters>=0.1.11 \
    langchain-openai>=1.0.1 \
    langchain-tavily>=0.2.12 \
    langchain-teddynote>=0.5.3 \
    langgraph>=1.0.0 \
    langfuse>=3.0.0 \
    markdown>=3.9 \
    numpy>=2.3.4 \
    pandas>=2.3.3 \
    pdfplumber>=0.11.7 \
    perplexityai>=0.17.1 \
    pgvector>=0.4.1 \
    pillow>=11.3.0 \
    psutil>=7.1.2 \
    psycopg2-binary>=2.9.11 \
    pypdf2>=3.0.1 \
    python-dotenv>=1.1.1 \
    rank-bm25>=0.2.2 \
    reportlab>=4.4.4 \
    scikit-learn>=1.7.2 \
    tavily-python>=0.7.12 \
    uvicorn>=0.32.0 \
    weasyprint>=66.0
#
# [제거된 패키지 19개 — 총 ~2.1GB 절감]
#
# 완전 미사용 (src/에서 import 0건):
#   docling (~200MB)        — 문서 변환 라이브러리, 프로젝트에서 미사용
#   docx2txt (~1MB)         — Word 파일 변환, 미사용
#   pdfminer (~5MB)         — PDF 파싱, weasyprint 사용 중
#   unstructured (~300MB)   — 비정형 데이터 파서, 미사용
#   pi-heif (~5MB)          — HEIF 이미지 변환, 미사용
#   xhtml2pdf (~10MB)       — HTML->PDF 변환, weasyprint 사용 중
#   pypdf (~5MB)            — PyPDF2만 사용 (default_loader.py)
#   sentence-transformers (~100MB) — Embedding은 OpenAI API 사용
#
# 테스트/개발 전용 (src/tests/ 또는 src/lab/에서만 사용):
#   deepeval (~50MB)        — 테스트 프레임워크, 로컬 실행
#   ragas (~30MB)           — 실험 노트북 전용
#   selenium (~20MB)        — 웹 크롤링 테스트 전용
#   jupyter (~100MB)        — 노트북 실행용, 서버에서 미사용
#   folium (~5MB)           — 지도 시각화, 노트북 전용
#   pymupdf (~30MB)         — PDF 파싱, 노트북 전용
#
# 별도 앱 / 로컬 모델 추론 불필요:
#   streamlit (~80MB)       — FastAPI와 별도 앱, Docker는 FastAPI만 실행
#   torch+torchvision+torchaudio (~880MB) — Embedding은 OpenAI API 사용, 로컬 추론 없음
#   transformers (~300MB)   — 노트북 전용, 서버에서 로컬 모델 추론 없음

# 실행 스테이지
FROM python:3.12-slim

WORKDIR /app

# 실행에 필요한 시스템 패키지만 설치 (WeasyPrint 포함)
# 한글 폰트 설치 추가 (PDF 렌더링용)
RUN apt-get update && apt-get install -y \
    curl \
    libcairo2 \
    libgobject-2.0-0 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    fonts-noto-cjk \
    fonts-noto-cjk-extra \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv

# 빌드 스테이지에서 Python 패키지 복사
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin /usr/local/bin

# 프로젝트 루트 마커 파일 복사 (get_project_root 함수용)
COPY pyproject.toml ./

# 애플리케이션 코드 복사
COPY src/ ./src/

# 데이터 파일만 복사 (필요한 것만)
COPY src/data/ ./src/data/

# 포트 노출
EXPOSE 8080

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/ || exit 1

# 환경 변수
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/src

# FastAPI 실행
CMD uvicorn src.fastapi.main_api:app --host 0.0.0.0 --port ${PORT:-8080}
