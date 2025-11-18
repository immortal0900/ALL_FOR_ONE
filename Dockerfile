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

# Python 의존성만 설치 (패키지 자체는 설치하지 않음)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    docling>=2.57.0 \
    docx2txt>=0.9 \
    fastapi>=0.121.0 \
    folium>=0.20.0 \
    geopy>=2.4.1 \
    google-api-python-client>=2.0.0 \
    google-auth-oauthlib>=1.2.3 \
    google-genai>=1.47.0 \
    jupyter>=1.1.1 \
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
    markdown>=3.9 \
    numpy>=2.3.4 \
    pandas>=2.3.3 \
    pdfminer>=20191125 \
    pdfplumber>=0.11.7 \
    perplexityai>=0.17.1 \
    pgvector>=0.4.1 \
    pi-heif>=1.1.1 \
    pillow>=11.3.0 \
    pip>=25.3 \
    psutil>=7.1.2 \
    psycopg2-binary>=2.9.11 \
    pymupdf>=1.26.5 \
    pypdf>=4.0.0 \
    pypdf2>=3.0.1 \
    python-dotenv>=1.1.1 \
    ragas>=0.3.8 \
    rank-bm25>=0.2.2 \
    reportlab>=4.4.4 \
    scikit-learn>=1.7.2 \
    selenium>=4.37.0 \
    sentence-transformers>=5.1.1 \
    tavily-python>=0.7.12 \
    streamlit>=1.39.0 \
    uvicorn>=0.32.0 \
    transformers>=4.57.1 \
    unstructured>=0.18.15 \
    weasyprint>=66.0 \
    xhtml2pdf>=0.2.17

# PyTorch CPU 설치
RUN pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.4.1+cpu \
    torchvision==0.19.1+cpu \
    torchaudio==2.4.1+cpu

# 실행 스테이지
FROM python:3.12-slim

WORKDIR /app

# 실행에 필요한 시스템 패키지만 설치
RUN apt-get update && apt-get install -y \
    curl \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# 빌드 스테이지에서 Python 패키지 복사
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin /usr/local/bin

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

# FastAPI 실행
CMD uvicorn src.fastapi.main_api:app --host 0.0.0.0 --port ${PORT:-8080}
