# 주요 작업 내역 정리

## 프로젝트 개요
- **프로젝트명**: ALL_FOR_ONE (RAG Commander)
- **배포 환경**: 
  - FastAPI: Railway (Docker)
  - Streamlit: Streamlit Community Cloud
  - PostgreSQL: Supabase

## 주요 해결한 문제들

### 1. SSL 연결 오류 해결
**문제**: Streamlit Cloud에서 Railway FastAPI로 요청 시 SSL 에러 발생
- 에러: `[SSL: DECRYPTION_FAILED_OR_BAD_RECORD_MAC] decryption failed or bad record mac`

**해결 방법**:
- `src/streamlit/web.py`에 커스텀 SSLAdapter 클래스 추가
- SSL 컨텍스트를 직접 설정하여 암호화/복호화 문제 우회
- `SECLEVEL=1` 설정으로 낮은 보안 수준의 암호화 허용

**수정 파일**:
- `src/streamlit/web.py`: SSLAdapter 클래스 및 Session 기반 요청 추가

### 2. PostgreSQL 연결 문제 해결
**문제**: Supabase PostgreSQL 연결 시 `server closed the connection unexpectedly` 에러 발생

**해결 방법**:
- `src/tools/rag/vector_store.py`에 연결 문자열 처리 함수 추가
- Supabase connection pooling URL 자동 변환
- Keepalive 파라미터 추가:
  - `connect_timeout=10`
  - `keepalives_idle=30`
  - `keepalives_interval=10`
  - `keepalives_count=5`

**수정 파일**:
- `src/tools/rag/vector_store.py`: `_prepare_connection_string()` 함수 추가

### 3. Railway HTTP 타임아웃 문제 해결 (비동기 작업 처리)
**문제**: Railway 프록시 타임아웃 (최대 15분, 변경 불가)으로 인한 502 에러
- 에러: `upstream headers response timeout`
- 작업 소요 시간이 15분 이상 걸릴 수 있음

**해결 방법**:
- 비동기 작업 처리 아키텍처로 변경
- `POST /invoke`: 작업 시작 후 즉시 `job_id` 반환 (HTTP 연결 즉시 종료)
- `GET /status/{job_id}`: 작업 상태 확인 (폴링용)
- `GET /result/{job_id}`: 작업 완료 후 결과 조회
- 백그라운드 작업은 Railway 타임아웃과 무관하게 계속 실행됨

**수정 파일**:
- `src/fastapi/main_api.py`: 비동기 작업 처리 시스템 추가
  - `run_graph_task()`: 백그라운드 작업 실행 함수
  - 작업 상태 저장소 (메모리 딕셔너리)
  - 3개 엔드포인트: `/invoke`, `/status/{job_id}`, `/result/{job_id}`
- `src/streamlit/web.py`: 폴링 방식으로 변경
  - 작업 시작 → 상태 확인 폴링 (5초마다) → 결과 조회

### 4. 코드에서 이모티콘 제거
**요청사항**: 모든 코드에서 이모티콘 제거

**수정 파일**:
- `src/streamlit/web.py`: 모든 이모티콘 제거
- `src/tools/send_gmail.py`: print 문 및 HTML 내용에서 이모티콘 제거
- `src/utils/google_drive_uploader.py`: 이모티콘 제거
- `src/agents/renderer/renderer_logic.py`: print 문에서 이모티콘 제거

### 5. 라이브러리 업데이트
**목적**: SSL 관련 라이브러리를 최신 버전으로 업데이트

**수정 파일**:
- `pyproject.toml`: 다음 패키지 추가
  - `requests>=2.31.0`
  - `urllib3>=2.0.0`
  - `certifi>=2023.7.22`
- `requirements.txt`: 새로 생성 (Streamlit Cloud용)

### 6. 환경 변수 설정 파일 생성
**목적**: Railway 및 Streamlit Cloud 환경 변수 설정 가이드

**생성 파일**:
- `UV_SYNC_GUIDE.md`: uv 가상환경 동기화 가이드

## 현재 배포 상태

### Railway (FastAPI)
- **도메인**: `https://allforone-production.up.railway.app`
- **포트**: 8080
- **상태**: 정상 작동 중
- **주요 환경 변수**:
  - `POSTGRES_URL`: Supabase PostgreSQL 연결 문자열
  - `GOOGLE_CREDENTIALS_JSON`: Google OAuth 인증 정보
  - `GOOGLE_TOKEN_JSON`: Google OAuth 토큰
  - 기타 API 키들 (OPENAI_API_KEY, ANTHROPIC_API_KEY 등)

### Streamlit Cloud
- **앱 이름**: `all_for_one`
- **Main file**: `src/streamlit/web.py`
- **주요 환경 변수**:
  - `API_URL`: Railway FastAPI URL
  - 기타 API 키들

### Supabase (PostgreSQL)
- **연결 방식**: Connection pooling 사용
- **확인된 컬렉션**:
  - `AGE_POPULATION`
  - `HOUSING_FAQ`
  - `HOUSING_RULE`
  - `MOVE_PEOPLE`
  - `PLANNING_MOVE_KEY`
  - `POLICY_PDF`
  - `policy_documents`

## 주요 파일 변경사항

### 수정된 파일
1. `src/streamlit/web.py`
   - SSLAdapter 클래스 추가
   - Session 기반 요청으로 변경
   - 이모티콘 제거
   - 비동기 작업 처리: 폴링 방식으로 상태 확인 및 결과 조회

2. `src/fastapi/main_api.py`
   - 비동기 작업 처리 시스템 추가
   - 작업 시작/상태 확인/결과 조회 엔드포인트 구현
   - 백그라운드 작업 실행 함수 추가

3. `src/tools/rag/vector_store.py`
   - Supabase 연결 문자열 처리 함수 추가
   - Keepalive 파라미터 추가

4. `src/tools/send_gmail.py`
   - 이모티콘 제거

5. `src/utils/google_drive_uploader.py`
   - 이모티콘 제거

6. `src/agents/renderer/renderer_logic.py`
   - 이모티콘 제거

7. `pyproject.toml`
   - SSL 관련 라이브러리 추가

### 새로 생성된 파일
1. `requirements.txt`: Streamlit Cloud용 의존성 파일
2. `UV_SYNC_GUIDE.md`: uv 가상환경 동기화 가이드

## 알려진 이슈 및 해결 방법

### 1. Railway HTTP 타임아웃 (해결 완료)
- **문제**: Railway 프록시 타임아웃이 최대 15분으로 제한되어 있고 변경 불가
- **해결**: 비동기 작업 처리 아키텍처로 변경 완료
  - 작업 시작 후 즉시 응답하여 타임아웃 회피
  - 백그라운드 작업은 Railway 타임아웃과 무관하게 실행
  - 클라이언트는 폴링 방식으로 상태 확인 및 결과 조회

### 2. uv pip sync로 인한 패키지 제거
- **문제**: `uv pip sync requirements.txt` 실행 시 348개 패키지가 제거됨
- **원인**: `requirements.txt`에는 5개 패키지만 포함되어 있음
- **해결 방법**: `uv sync` 명령어 사용 (pyproject.toml 기반)

## 다음 단계 권장사항

1. **테스트**
   - Streamlit 앱에서 보고서 생성 요청 테스트
   - 작업 시작 → 상태 확인 → 결과 조회 흐름 확인
   - 15분 이상 걸리는 작업도 정상 완료되는지 확인

2. **가상환경 복구** (필요시)
   ```cmd
   uv sync
   ```

## 기술 스택

- **Python**: 3.12
- **패키지 관리**: uv
- **웹 프레임워크**: FastAPI, Streamlit
- **데이터베이스**: PostgreSQL (Supabase) with pgvector
- **배포**: Railway (Docker), Streamlit Cloud
- **인증**: Google OAuth2 (Gmail, Drive)

## 참고 문서

- `DEPLOYMENT_SUMMARY.md`: 배포 작업 내역
- `DB_MIGRATION_GUIDE.md`: 데이터베이스 마이그레이션 가이드
- `STREAMLIT_CLOUD_GUIDE.md`: Streamlit Cloud 배포 가이드
- `RAILWAY_DEPLOYMENT.md`: Railway 배포 가이드
- `UV_SYNC_GUIDE.md`: uv 가상환경 동기화 가이드

