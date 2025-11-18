# Streamlit Community Cloud 배포 가이드

Streamlit Community Cloud에서 Streamlit 앱을 배포하는 방법입니다.

## 1. Streamlit Cloud 준비

### 1-1. 계정 생성
1. https://share.streamlit.io 접속
2. GitHub 계정으로 로그인

### 1-2. 저장소 준비
- GitHub에 코드가 올라가 있어야 함
- Streamlit 앱 파일이 있어야 함 (예: src/streamlit/web.py)

## 2. 앱 배포

### 2-1. 새 앱 생성
1. Streamlit Cloud 대시보드에서 "New app" 클릭
2. GitHub 저장소 선택
3. Branch 선택 (보통 main)
4. Main file path 입력: `src/streamlit/web.py`

### 2-2. 고급 설정 (선택사항)
1. "Advanced settings" 클릭
2. Python version 선택 (3.12 권장)

## 3. 환경 변수 설정

### 3-1. Secrets 설정
1. 앱 페이지에서 "Settings" 클릭
2. "Secrets" 탭 클릭
3. TOML 형식으로 환경 변수 입력:

```toml
[secrets]
FASTAPI_URL = "https://railway에서_생성한_도메인"
LANGSMITH_API_KEY = "..."
OPENAI_API_KEY = "..."
TAVILY_API_KEY = "..."
등등...
```

### 3-2. FastAPI URL 설정
- Railway에서 배포한 FastAPI 도메인 주소 입력
- 예: `FASTAPI_URL = "https://프로젝트명.up.railway.app"`

## 4. Streamlit 코드 수정

### 4-1. 환경 변수 읽기
Streamlit 코드에서 환경 변수를 읽도록 수정:

```python
import os

# FastAPI URL 가져오기
api_url = os.getenv("FASTAPI_URL", "http://localhost:8080")
```

현재 코드는 이미 이렇게 되어 있음 (web.py 45번째 줄)

## 5. 배포 확인

### 5-1. 배포 상태 확인
1. 앱 페이지에서 배포 로그 확인
2. 성공하면 "App is live!" 메시지 표시

### 5-2. 앱 접속
1. 생성된 Streamlit 앱 URL 확인
2. 브라우저에서 접속하여 테스트

## 6. 문제 해결

### 6-1. 배포 실패
- Main file path가 올바른지 확인
- Python 버전 호환성 확인
- 의존성 파일 확인 (requirements.txt 또는 pyproject.toml)

### 6-2. FastAPI 연결 오류
- FASTAPI_URL이 올바른지 확인
- Railway에서 FastAPI가 실행 중인지 확인
- CORS 설정 확인 (필요시)

### 6-3. 환경 변수 오류
- Secrets에 변수가 올바르게 입력되었는지 확인
- 변수명 대소문자 확인

## 참고사항

- Streamlit Community Cloud는 무료
- GitHub 저장소가 공개되어 있어야 함
- 자동 배포: GitHub에 push하면 자동 재배포
- 앱 URL 형식: https://앱이름.streamlit.app

