# PostgreSQL Database Migration Guide

로컬 DB를 클라우드(Railway)로 마이그레이션하는 가이드입니다.

## 방법 1: pg_dump 백업/복원 (권장)

### 1단계: 로컬 DB 백업

```bash
# 전체 데이터베이스 백업
pg_dump -h localhost -U postgres -d ragdb -F c -b -v -f ragdb_backup.dump

# 또는 SQL 형식으로 백업 (텍스트 기반)
pg_dump -h localhost -U postgres -d ragdb > ragdb_backup.sql
```

**백업 파일 크기**: 약 100-200MB (데이터 + 벡터 인덱스)

### 2단계: Railway PostgreSQL 생성

1. Railway 대시보드에서 "New" → "Database" → "Add PostgreSQL"
2. 자동으로 프로비저닝 완료 (1-2분)
3. PostgreSQL URL 복사 (예: `postgresql://postgres:xxx@xxx.railway.app:5432/railway`)

### 3단계: pgvector Extension 활성화

```bash
# Railway PostgreSQL에 연결
psql <RAILWAY_POSTGRES_URL>

# pgvector extension 생성
CREATE EXTENSION IF NOT EXISTS vector;

# 확인
\dx
```

### 4단계: 백업 파일 복원

**Custom 형식(.dump)을 사용한 경우:**
```bash
pg_restore -h <RAILWAY_HOST> -U postgres -d railway -v ragdb_backup.dump
```

**SQL 형식(.sql)을 사용한 경우:**
```bash
psql <RAILWAY_POSTGRES_URL> < ragdb_backup.sql
```

### 5단계: 데이터 검증

```bash
# Railway DB에 연결
psql <RAILWAY_POSTGRES_URL>

# 테이블 확인
\dt

# 벡터 컬렉션 확인
SELECT * FROM langchain_pg_collection;

# 데이터 개수 확인
SELECT COUNT(*) FROM langchain_pg_embedding;
```

**예상 테이블:**
- `langchain_pg_collection` (벡터 컬렉션 메타데이터)
- `langchain_pg_embedding` (벡터 임베딩)
- `age_population` (나이별 인구)
- 기타 CSV 데이터 테이블들

---

## 방법 2: Docker Volume 복사 (대안)

### 1단계: 로컬 PostgreSQL 컨테이너 중지

```bash
docker stop rag_pg
```

### 2단계: pgdata 디렉토리 압축

```bash
# Windows
tar -czf pgdata_backup.tar.gz pgdata/

# 또는 7zip 사용
7z a pgdata_backup.7z pgdata/
```

### 3단계: Railway에서 Persistent Volume 사용

**주의:** Railway는 Postgres addon을 사용하므로 직접 volume mount는 불가능합니다.
→ **방법 1(pg_dump)을 사용하세요.**

---

## 방법 3: 원격 연결로 직접 복제 (가장 간단)

### 로컬 → Railway 직접 복제

```bash
# 로컬 DB에서 dump하고 동시에 Railway로 복원
pg_dump -h localhost -U postgres -d ragdb | psql <RAILWAY_POSTGRES_URL>
```

**장점:** 백업 파일 저장 불필요
**단점:** 네트워크 연결이 중단되면 처음부터 다시 시작

---

## 트러블슈팅

### 문제 1: pgvector extension이 없다는 오류

```sql
-- Railway PostgreSQL에서 실행
CREATE EXTENSION IF NOT EXISTS vector;
```

### 문제 2: 권한 오류 (permission denied)

```bash
# -U 옵션으로 사용자 지정
pg_restore -h <HOST> -U postgres -W -d railway ragdb_backup.dump
# -W: 비밀번호 입력 프롬프트
```

### 문제 3: 테이블 충돌 (already exists)

```bash
# 복원 전 clean 옵션 사용
pg_restore -c -h <HOST> -U postgres -d railway ragdb_backup.dump
# -c: 기존 객체 삭제 후 복원
```

### 문제 4: 복원 시간이 너무 오래 걸림

**예상 시간:**
- 데이터 크기 100MB: 약 5-10분
- 데이터 크기 500MB: 약 20-30분

**최적화:**
```bash
# 병렬 복원 (4개 작업 동시 실행)
pg_restore -j 4 -h <HOST> -U postgres -d railway ragdb_backup.dump
```

---

## 백업 검증 체크리스트

복원 후 아래 항목들을 확인하세요:

- [ ] pgvector extension 설치 확인 (`\dx`)
- [ ] 모든 테이블 존재 확인 (`\dt`)
- [ ] 벡터 컬렉션 개수 확인
  ```sql
  SELECT collection_name, COUNT(*)
  FROM langchain_pg_collection
  GROUP BY collection_name;
  ```
- [ ] 임베딩 데이터 존재 확인
  ```sql
  SELECT COUNT(*) FROM langchain_pg_embedding;
  ```
- [ ] 인덱스 생성 확인 (`\di`)
- [ ] 데이터베이스 크기 확인
  ```sql
  SELECT pg_size_pretty(pg_database_size('railway'));
  ```

**예상 크기:** 100-500MB (데이터 + 인덱스 포함)

---

## Railway 환경변수 설정

백업 복원 후, Railway 서비스에서 환경변수를 설정하세요:

```bash
POSTGRES_URL=<Railway PostgreSQL URL>
```

**주의:** Railway PostgreSQL URL은 다음 형식입니다:
```
postgresql://postgres:<password>@<region>.railway.app:5432/railway
```

---

## 참고사항

1. **백업 주기:** 프로덕션 환경에서는 매일 자동 백업 설정 권장
2. **백업 위치:** 로컬 백업 파일은 안전한 곳에 보관 (Google Drive, S3 등)
3. **테스트:** 복원 후 반드시 리포트 생성 테스트 실행
4. **모니터링:** Railway 대시보드에서 DB 사용량 모니터링

---

## 예상 소요 시간

- 백업: 5-10분
- pgvector 설정: 1분
- 복원: 10-30분
- 검증: 5분

**총 예상 시간:** 30-50분
