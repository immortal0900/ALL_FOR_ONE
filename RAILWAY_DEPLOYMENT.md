# Railway 배포 가이드 (Docker 기반)

이 가이드는 RAG Commander를 Railway에 Docker 컨테이너로 배포하는 방법을 설명합니다.

## 사전 준비

### 1. GitHub 저장소 준비
코드를 GitHub에 업로드해야 합니다.

```bash
git init
git add .
git commit -m "Add Docker configuration for Railway deployment"
git remote add origin https://github.com/사용자명/저장소명.git
git push -u origin main
```

### 2. Railway 계정 생성
1. https://railway.app 접속
2. "Start a New Project" 클릭
3. GitHub로 로그인

### 3. 로컬 데이터베이스 백업
Railway 배포 전에 로컬 PostgreSQL 데이터를 백업해야 합니다.

상세 가이드: **[DB_MIGRATION_GUIDE.md](./DB_MIGRATION_GUIDE.md)** 참고

간단 버전:
```bash
# 로컬 DB 백업
pg_dump -h localhost -U postgres -d ragdb -F c -f ragdb_backup.dump
```

---

## 배포 방식 선택

### 방법 A: Docker 컨테이너 배포 (권장)
- FastAPI + Streamlit을 하나의 컨테이너에서 실행
- 설정이 간단하고 비용 절감
- 본 가이드에서 설명

### 방법 B: 분리된 서비스 배포
- FastAPI와 Streamlit을 별도 서비스로 배포
- 독립적인 스케일링 가능
- 구 버전 가이드 참고 (하단)

---

## 방법 A: Docker 컨테이너 배포 (권장)

### 1. Railway PostgreSQL 생성

1. Railway 대시보드에서 "New" → "Database" → "Add PostgreSQL"
2. 자동 프로비저닝 완료 대기 (1-2분)
3. PostgreSQL 서비스 클릭 → "Connect" 탭 → URL 복사

**URL 형식:**
```
postgresql://postgres:password@region.railway.app:5432/railway
```

### 2. pgvector Extension 활성화

로컬 터미널에서 Railway DB에 연결:

```bash
# Railway PostgreSQL URL 복사 후 실행
psql postgresql://postgres:password@region.railway.app:5432/railway

# pgvector extension 생성
CREATE EXTENSION IF NOT EXISTS vector;

# 확인
\dx
```

`vector` extension이 목록에 나타나면 성공입니다.

### 3. 로컬 DB를 Railway DB로 복원

```bash
# 방법 1: Dump 파일 사용
pg_restore -h region.railway.app -U postgres -d railway -v ragdb_backup.dump

# 방법 2: 직접 복제 (더 빠름)
pg_dump -h localhost -U postgres -d ragdb | psql postgresql://postgres:password@region.railway.app:5432/railway
```

**예상 소요 시간:** 10-30분 (데이터 크기에 따라)

### 4. 데이터 복원 확인

```bash
psql postgresql://postgres:password@region.railway.app:5432/railway

# 테이블 확인
\dt

# 벡터 컬렉션 확인
SELECT collection_name, COUNT(*)
FROM langchain_pg_collection
GROUP BY collection_name;

# 임베딩 개수 확인
SELECT COUNT(*) FROM langchain_pg_embedding;
```

기대 결과:
- `langchain_pg_collection`: 5-10개 컬렉션
- `langchain_pg_embedding`: 수천 개의 벡터
- 기타 CSV 데이터 테이블들

### 5. Railway 서비스 생성

1. Railway 대시보드에서 "New" → "GitHub Repo" 선택
2. RAG Commander 저장소 선택
3. 서비스 이름: `rag-commander-app`

### 6. Start Command 설정

서비스 클릭 → "Settings" → "Start Command"에 입력:

```bash
chmod +x start.sh && ./start.sh
```

또는 더 명시적으로:

```bash
bash start.sh
```

**설명:**
- `start.sh` 스크립트가 FastAPI와 Streamlit을 자동으로 시작합니다
- FastAPI는 백그라운드에서, Streamlit은 포그라운드에서 실행됩니다

### 7. 환경 변수 설정

서비스 클릭 → "Variables" 탭에서 다음 환경 변수 추가:

#### 필수 환경 변수

```bash
# Database
POSTGRES_URL=postgresql://postgres:password@region.railway.app:5432/railway

# FastAPI Configuration
FASTAPI_PORT=8080
FASTAPI_URL=http://localhost:8080

# LLM Services (최소 1개 필요)
OPENAI_API_KEY=sk-proj-your-key
ANTHROPIC_API_KEY=sk-ant-your-key
GEMINI_API_KEY=your-key

# Search APIs (권장)
TAVILY_API_KEY=tvly-your-key
PERPLEXITY_API_KEY=pplx-your-key
FIRECRAWL_API_KEY=fc-your-key

# Korean Real Estate APIs (필수)
R_ONE_API_KEY=your-key
MOLIT_API_KEY=your-key
KAKAO_REST_API_KEY=your-key
GONG_GONG_DATA_API_KEY=your-key

# Statistics APIs
KOSIS_CONSUMER_KEY=your-key
KOSIS_CONSUMER_SECRET_KEY=your-key
ECOS_API_KEY=your-key

# Monitoring (선택)
LANGSMITH_API_KEY=lsv2-your-key
LANGSMITH_TRACING=false
```

**참고:** `.env.example` 파일에 전체 목록이 있습니다.

#### Railway 자동 제공 변수

Railway가 자동으로 설정하는 변수:
- `PORT`: Streamlit이 사용할 포트 (자동 할당)
- `RAILWAY_ENVIRONMENT`: production/staging

### 8. 도메인 생성

서비스 클릭 → "Settings" → "Networking" → "Generate Domain"

자동 생성된 URL:
```
https://rag-commander-app-production-xxxx.up.railway.app
```

---

## 배포 확인

### 1. 빌드 로그 모니터링

"Deployments" 탭에서 빌드 진행 상황 확인:

```
Building...
Installing dependencies...
Building Docker image...
Starting application...
FastAPI started (PID: xxx)
FastAPI is ready!
Starting Streamlit frontend...
```

**예상 빌드 시간:** 5-10분 (첫 빌드)

### 2. Health Check

생성된 도메인으로 접속:

```bash
# FastAPI health check
curl https://your-app.up.railway.app:8080/

# Streamlit은 Railway PORT로 자동 연결
# 브라우저에서 https://your-app.up.railway.app 접속
```

### 3. 첫 리포트 생성 테스트

1. Streamlit UI에서 테스트 데이터 입력:
   - 사업지 장소: `서울특별시 송파구 신천동`
   - 단지 타입: `84제곱미터`
   - 세대수: `2275`
   - 이메일: 본인 이메일

2. "보고서 작성 시작" 클릭

3. **예상 소요 시간:** 13-15분

4. 완료 시 이메일로 리포트 수신 확인

---

## 문제 해결

### 빌드 실패

**증상:** Build failed 에러

**해결:**
1. "Logs" 탭에서 에러 메시지 확인
2. 일반적인 원인:
   - `pyproject.toml` 의존성 문제
   - Docker 빌드 오류
   - 메모리 부족

**해결책:**
```bash
# railway.toml 파일 생성으로 메모리 증가
[build]
  builder = "nixpacks"

[deploy]
  startCommand = "bash start.sh"
  healthcheckPath = "/"
  healthcheckTimeout = 100
```

### start.sh 실행 권한 오류

**증상:** `Permission denied: start.sh`

**해결:**
Dockerfile에 이미 `chmod +x start.sh`가 포함되어 있습니다. 그래도 오류 발생 시:

```dockerfile
# Dockerfile 마지막 부분 수정
RUN chmod +x start.sh
RUN dos2unix start.sh  # Windows에서 작성한 경우
```

### FastAPI가 시작되지 않음

**증상:** Streamlit은 실행되지만 FastAPI 연결 실패

**확인:**
```bash
# Railway Logs에서 확인
FastAPI started (PID: xxx)
FastAPI is ready!
```

**해결:**
1. `FASTAPI_PORT` 환경 변수 확인 (8080)
2. `start.sh`에서 uvicorn 명령 확인
3. 로그에서 포트 충돌 확인

### PostgreSQL 연결 오류

**증상:** `psycopg2.OperationalError: could not connect`

**해결:**
1. `POSTGRES_URL` 환경 변수 확인
2. Railway PostgreSQL 서비스 실행 상태 확인
3. pgvector extension 설치 확인:
   ```sql
   \dx vector
   ```

### 리포트 생성 실패

**증상:** 15분 후에도 완료되지 않거나 에러

**확인 사항:**
1. **API 키 유효성:**
   - OpenAI API 잔액 확인
   - Anthropic API 한도 확인

2. **데이터베이스 연결:**
   ```bash
   # Railway Logs에서 확인
   "Successfully retrieved X vectors from collection"
   ```

3. **메모리 부족:**
   - Railway 플랜 업그레이드 (512MB → 1GB)

### 이메일 전송 실패

**증상:** 리포트는 생성되지만 이메일 미수신

**원인:**
- `credentials.json`, `token.json` 파일이 Docker 이미지에 포함되지 않음 (`.dockerignore`)

**해결:**
1. 이메일 기능 비활성화 (임시)
2. 또는 환경 변수로 Gmail OAuth 토큰 전달 (고급)

---

## 비용 계산

### Railway 요금제

| 항목 | 무료 플랜 | Hobby 플랜 | Pro 플랜 |
|------|----------|------------|----------|
| 월 크레딧 | $5 | $10 | $20 |
| CPU | 공유 | 공유 | 전용 |
| RAM | 512MB | 512MB-8GB | 2GB-32GB |
| 적합성 | 테스트 | 소규모 | 프로덕션 |

### 예상 비용 (Hobby 플랜 기준)

**소규모 트래픽 (일 10회):**
- PostgreSQL: $5-7/월
- App Service (512MB): $10-15/월
- 아웃바운드: $2-3/월
- **총합:** $17-25/월

**API 비용 별도:**
- OpenAI GPT-4/GPT-5: 리포트당 $0.50-2.00
- 일 10회 × 30일 = 월 300회
- API 비용: $150-600/월 (변동적)

**권장:** LangSmith 트레이싱 비활성화로 추가 비용 절감

---

## 모니터링

### Railway 대시보드

실시간 모니터링:
- CPU 사용률
- 메모리 사용량
- 네트워크 트래픽
- 배포 상태

### LangSmith (선택)

`LANGSMITH_TRACING=true` 설정 시:
- 각 에이전트 실행 시간
- LLM 호출 통계
- 에러 추적

**주의:** 트레이싱 활성화 시 비용 증가

### 로그 확인

```bash
# 실시간 로그
railway logs --follow

# 최근 100줄
railway logs --tail 100
```

---

## 프로덕션 최적화

### 1. 환경 분리

`.env.production` 파일 생성:
```bash
LANGSMITH_TRACING=false
OPENAI_API_KEY=production-key
```

### 2. 헬스체크 개선

`src/fastapi/main_api.py`에 헬스체크 추가:
```python
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
```

### 3. 로깅 설정

```python
import logging
logging.basicConfig(level=logging.INFO)
```

### 4. 에러 알림

Railway → Settings → Notifications에서 이메일 알림 설정

---

## 대안: 방법 B - 분리된 서비스 배포

FastAPI와 Streamlit을 별도 서비스로 배포하려면:

### FastAPI 서비스

Start Command:
```bash
uvicorn src.fastapi.main_api:app --host 0.0.0.0 --port $PORT
```

### Streamlit 서비스

Start Command:
```bash
streamlit run src/streamlit/web.py --server.address 0.0.0.0 --server.port $PORT
```

환경 변수 추가:
```bash
FASTAPI_URL=https://your-fastapi-service.up.railway.app
```

**장점:**
- 독립적인 스케일링
- FastAPI만 재시작 가능

**단점:**
- 두 배의 비용
- 설정 복잡

---

## 참고 문서

- [DB_MIGRATION_GUIDE.md](./DB_MIGRATION_GUIDE.md) - 데이터베이스 마이그레이션 상세 가이드
- [.env.example](./.env.example) - 환경 변수 템플릿
- [Railway 공식 문서](https://docs.railway.app)
- [Docker 공식 문서](https://docs.docker.com)

---

## 체크리스트

배포 전 확인:

- [ ] GitHub에 코드 푸시 완료
- [ ] 로컬 DB 백업 완료 (`ragdb_backup.dump`)
- [ ] Railway 계정 생성
- [ ] Railway PostgreSQL 생성
- [ ] pgvector extension 설치
- [ ] 로컬 DB 복원 완료
- [ ] 환경 변수 18개 설정 완료
- [ ] `start.sh` 실행 권한 확인
- [ ] `.dockerignore` 파일 확인
- [ ] 빌드 성공 확인
- [ ] 도메인 생성 완료
- [ ] 첫 리포트 생성 테스트 완료

---

## 다음 단계

배포 완료 후:

1. **보안 강화**
   - API 인증 추가
   - Rate limiting 설정
   - CORS 정책 강화

2. **성능 모니터링**
   - Railway 대시보드 정기 확인
   - API 사용량 모니터링
   - 에러 로그 분석

3. **비용 최적화**
   - 불필요한 API 호출 제거
   - 캐싱 전략 구현
   - LangSmith 트레이싱 선택적 사용

4. **사용자 피드백**
   - 리포트 품질 평가
   - 응답 시간 개선
   - UI/UX 개선

---

문의사항이나 문제 발생 시 GitHub Issues에 등록해주세요.
