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

# Python 패키지 설치
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

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
