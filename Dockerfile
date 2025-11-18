# RAG Commander - FastAPI + Streamlit Docker Image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    pkg-config \
    libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies using uv
RUN uv pip install --system --no-cache -r pyproject.toml

# Copy application source code
COPY src/ ./src/
COPY .streamlit/ ./.streamlit/

# Copy data files (93MB)
COPY src/data/ ./src/data/

# Copy startup script
COPY start.sh ./start.sh
RUN chmod +x start.sh

# Expose ports
# Note: Railway will override with $PORT environment variable
EXPOSE 8080 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Start command - will be overridden by Railway with custom start command
CMD ["./start.sh"]
