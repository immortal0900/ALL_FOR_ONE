# 배포 작업 내역 정리

## 프로젝트 구조
- **FastAPI**: Railway에 배포 (Docker 사용)
- **Streamlit**: Streamlit Community Cloud에 배포
- **PostgreSQL**: Railway 또는 Supabase 사용

## 배포된 서비스

### 1. FastAPI (Railway)
- **도메인**: `https://allforone-production.up.railway.app`
- **포트**: 8080
- **상태**: 정상 작동 중 (`{"status": "ok"}` 응답 확인됨)

### 2. Streamlit (Streamlit Cloud)
- **앱 이름**: `all_for_one`
- **Main file**: `src/streamlit/web.py`
- **Branch**: `main`

## 주요 변경사항

### 1. Dockerfile 최적화
- **멀티스테이지 빌드** 적용으로 이미지 크기 최적화 (10GB → 4GB 이하)
- **빌드 스테이지**: 빌드 도구만 사용
- **실행 스테이지**: 최소 패키지만 포함
- **WeasyPrint 의존성** 추가:
  - `libcairo2`
  - `libgobject-2.0-0`
  - `libpango-1.0-0`
  - `libpangoft2-1.0-0`
  - `libpangocairo-1.0-0`
  - `libgdk-pixbuf-2.0-0`
  - `shared-mime-info`

### 2. FastAPI 코드 수정 (`src/fastapi/main_api.py`)
- **CORS 미들웨어 추가**:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",  # 로컬 개발
        "https://*.streamlit.app",  # Streamlit Cloud
        "https://*.railway.app",  # Railway
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. Streamlit 코드 수정 (`src/streamlit/web.py`)
- **API_URL 환경변수 사용**:
```python
# 환경에 따른 API URL 설정
api_url = None

# Streamlit Cloud Secrets 확인
if hasattr(st, "secrets"):
    try:
        if "API_URL" in st.secrets:
            api_url = st.secrets["API_URL"]
    except (KeyError, AttributeError, TypeError):
        pass

# Secrets에서 못 찾으면 환경 변수 확인
if not api_url:
    api_url = os.getenv("API_URL")

# 둘 다 없으면 기본값 사용 (로컬 개발)
if not api_url:
    api_url = "http://localhost:8080"
```

### 4. pyproject.toml 수정
- PyTorch 관련 패키지 추가:
  - `torch>=2.4.1`
  - `torchvision>=0.19.1`
  - `torchaudio>=2.4.1`

## 환경변수 설정

### Railway (FastAPI 서비스)
Railway 대시보드 → 서비스 → Variables 탭에서 설정:
- `POSTGRES_URL`: PostgreSQL 연결 정보
- 기타 API 키들 (OPENAI_API_KEY, ANTHROPIC_API_KEY 등)

### Streamlit Cloud
Settings → Secrets 탭에서 TOML 형식으로 설정:
```toml
[secrets]
API_URL = "https://allforone-production.up.railway.app"
POSTGRES_URL = "postgresql://..."
LANGSMITH_API_KEY = "..."
OPENAI_API_KEY = "..."
# 기타 필요한 API 키들...
```

**중요**: `API_URL` 변수명 사용 (기존 `FASTAPI_URL` 아님)

## 해결된 문제들

### 1. Docker 이미지 크기 초과 (10GB → 4GB 제한)
- **원인**: 빌드 도구와 불필요한 파일 포함
- **해결**: 멀티스테이지 빌드 + .dockerignore 최적화

### 2. WeasyPrint 라이브러리 오류
- **오류**: `libgobject-2.0-0`, `libpangoft2-1.0-0` 등 누락
- **해결**: Dockerfile 실행 스테이지에 필요한 시스템 라이브러리 추가

### 3. Python 모듈 경로 오류
- **오류**: `ModuleNotFoundError: No module named 'agents'`
- **해결**: Dockerfile에 `ENV PYTHONPATH=/app/src` 추가

### 4. Streamlit에서 FastAPI 연결 실패
- **오류**: `localhost:8080` 연결 시도
- **해결**: 
  - FastAPI에 CORS 미들웨어 추가
  - Streamlit에서 `API_URL` 환경변수 사용
  - Streamlit Cloud Secrets 설정

## 배포 확인 방법

### FastAPI 확인
```bash
curl https://allforone-production.up.railway.app/
# 응답: {"status": "ok"}
```

### Streamlit 확인
1. Streamlit Cloud 앱 URL 접속
2. 폼 제출 시 `localhost:8080` 오류가 없어야 함
3. Railway URL로 연결되어야 함

## 다음 작업 시 참고사항

1. **코드 변경 후 배포**:
   - GitHub에 push하면 자동 재배포됨
   - Railway: 자동 재배포
   - Streamlit Cloud: 자동 재배포

2. **환경변수 추가 시**:
   - Railway: Variables 탭에서 추가
   - Streamlit Cloud: Secrets 탭에서 TOML 형식으로 추가

3. **로컬 개발**:
   - FastAPI: `uvicorn src.fastapi.main_api:app --reload`
   - Streamlit: `streamlit run src/streamlit/web.py`
   - `API_URL` 환경변수 없으면 자동으로 `localhost:8080` 사용

4. **CORS 설정**:
   - 현재 와일드카드 패턴 사용 중 (`*.streamlit.app`, `*.railway.app`)
   - 프로덕션에서는 특정 도메인만 허용하는 것이 더 안전함

## 관련 파일
- `Dockerfile`: Railway 배포용
- `src/fastapi/main_api.py`: FastAPI 엔드포인트
- `src/streamlit/web.py`: Streamlit 프론트엔드
- `pyproject.toml`: Python 의존성
- `.dockerignore`: Docker 빌드 제외 파일
- `RAILWAY_DEPLOYMENT_GUIDE.md`: Railway 배포 가이드
- `STREAMLIT_CLOUD_GUIDE.md`: Streamlit Cloud 배포 가이드

