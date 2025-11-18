# Railway 배포 가이드

Railway에서 Docker와 PostgreSQL을 포함한 FastAPI를 배포하는 방법입니다.

## 1. Railway 준비

### 1-1. Railway 계정 생성
1. https://railway.app 접속
2. GitHub 계정으로 로그인

### 1-2. 프로젝트 생성
1. Railway 대시보드에서 "New Project" 클릭
2. "Deploy from GitHub repo" 선택
3. GitHub 저장소 선택

## 2. PostgreSQL 서비스 추가

### 2-1. PostgreSQL 생성
1. Railway 프로젝트에서 "+ New" 클릭
2. "Database" 선택
3. "Add PostgreSQL" 클릭

### 2-2. PostgreSQL 연결 정보 확인
1. PostgreSQL 서비스 클릭
2. "Variables" 탭에서 연결 정보 확인
   - DATABASE_URL 자동 생성됨
   - 예시: `postgresql://postgres:비밀번호@호스트:포트/railway`

## 3. FastAPI 서비스 배포

### 3-1. 서비스 추가
1. 프로젝트에서 "+ New" 클릭
2. "GitHub Repo" 선택
3. 같은 저장소 선택

### 3-2. 환경 변수 설정
1. FastAPI 서비스 클릭
2. "Variables" 탭에서 환경 변수 추가:

먼저 PostgreSQL 연결 정보를 가져옵니다:
1. PostgreSQL 서비스 클릭
2. "Variables" 탭에서 `DATABASE_URL` 또는 `POSTGRES_URL` 복사
3. FastAPI 서비스의 "Variables"에 추가:

```
POSTGRES_URL=postgresql://postgres:비밀번호@호스트:포트/railway
```

기존 .env 파일의 다른 변수들도 추가:
```
LANGSMITH_API_KEY=...
OPENAI_API_KEY=...
TAVILY_API_KEY=...
등등...
```

### 3-3. 배포 설정
1. "Settings" 탭 클릭
2. "Build Command"는 비워두기 (Dockerfile 사용)
3. "Start Command"는 비워두기 (Dockerfile의 CMD 사용)
   - 또는 설정하려면: `uvicorn src.fastapi.main_api:app --host 0.0.0.0 --port $PORT`

### 3-4. 포트 설정
1. "Settings" 탭에서 "Generate Domain" 클릭
2. Railway가 자동으로 포트 할당

## 4. 배포 확인

### 4-1. 배포 상태 확인
1. "Deployments" 탭에서 빌드 로그 확인
2. 성공하면 "Active" 상태 표시

### 4-2. API 테스트
1. 생성된 도메인 주소 확인 (예: https://프로젝트명.up.railway.app)
2. 브라우저에서 `https://도메인/` 접속
3. `{"status": "ok"}` 응답 확인

## 5. 문제 해결

### 5-1. 빌드 실패
- Dockerfile이 프로젝트 루트에 있는지 확인
- pyproject.toml 의존성 확인
- 빌드 로그에서 오류 메시지 확인
- 의존성 설치 시간이 오래 걸릴 수 있음 (PyTorch 등)

### 5-2. 연결 오류
- POSTGRES_URL 환경 변수가 올바른지 확인
- PostgreSQL 서비스가 실행 중인지 확인

### 5-3. 포트 오류
- Railway는 $PORT 환경 변수를 사용
- 코드에서 하드코딩된 포트 제거 필요

## 참고사항

- Railway는 무료 플랜 제공 (제한 있음)
- PostgreSQL은 무료 플랜에서 256MB 제공
- 자동 배포: GitHub에 push하면 자동 배포

