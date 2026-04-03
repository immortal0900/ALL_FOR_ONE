"""
pgvector HNSW 인덱스 생성 스크립트

langchain_pg_embedding 테이블 전체에 HNSW(Hierarchical Navigable Small World) 인덱스를 생성합니다.
모든 컬렉션(NATIONAL_POLICY, policy_documents, UNSOLD_HOUSING 등)이
동일한 테이블을 공유하므로, 전체 벡터 검색 성능이 향상됩니다.

HNSW vs IVFFlat 선택 근거:
- IVFFlat은 데이터 분포에 따라 클러스터를 생성하므로 데이터 변경 시 리빌드 필요
- HNSW는 그래프 기반으로 삽입/삭제 시에도 자동 유지되어 운영 부담이 적음
- 현재 데이터 규모(수천 건 이하)에서 HNSW가 정확도와 속도 모두 우수

전제 조건:
- embedding 컬럼이 vector(차원 미지정)로 선언된 경우 HNSW 인덱스를 생성할 수 없음
  pgvector는 인덱스 생성 시 컬럼에 고정 차원이 필요하기 때문.
- 이 스크립트는 먼저 컬럼 타입을 vector(3072)로 변경한 뒤 인덱스를 생성합니다.
  (text-embedding-3-large의 출력 차원 = 3072)

이 스크립트는 멱등(idempotent)합니다 — IF NOT EXISTS / IF로 중복 실행해도 안전합니다.
"""

import os
import sys
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))

from utils.util import get_project_root

env_path = get_project_root() / ".env"
load_dotenv(dotenv_path=env_path, override=True)

# .env localhost 덮어쓰기 방어 로직
postgres_url = os.getenv("POSTGRES_URL")
if postgres_url and "localhost" in postgres_url:
    print("[Warning] localhost 접속 정보 감지. Supabase 주소를 명시적으로 찾습니다.")
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("POSTGRES_URL") and "supabase" in line:
                raw_url = line.split("=", 1)[1].strip().strip('"').strip("'")
                try:
                    prefix_part, rest = raw_url.split("://", 1)
                    auth_part, host_part = rest.split("@", 1)
                    user_part, pass_part = auth_part.split(":", 1)
                    encoded_pass = urllib.parse.quote_plus(pass_part)
                    os.environ["POSTGRES_URL"] = (
                        f"{prefix_part}://{user_part}:{encoded_pass}@{host_part}"
                    )
                except Exception:
                    os.environ["POSTGRES_URL"] = raw_url
                break

from tools.rag.vector_store import _prepare_connection_string

# text-embedding-3-large 출력 차원
EMBEDDING_DIMENSIONS = 3072

# HNSW 인덱스 파라미터
# m=16: 각 노드가 유지하는 연결 수. 높을수록 정확하지만 메모리 사용 증가.
#        16은 수천 건 규모에서 권장되는 기본값.
# ef_construction=64: 인덱스 구축 시 탐색 범위. 높을수록 빌드가 느리지만 정확도 향상.
#                      64는 정확도/빌드 시간의 균형점.
HNSW_M = 16
HNSW_EF_CONSTRUCTION = 64

# Step 1: embedding 컬럼에 차원 부여 (vector -> vector(3072))
# pgvector HNSW 인덱스는 고정 차원 컬럼에서만 생성 가능.
# vector(차원 미지정) 컬럼에 인덱스를 걸면 "column does not have dimensions" 에러 발생.
# 참고: https://github.com/pgvector/pgvector#hnsw
ALTER_COLUMN_SQL = text(f"""
    ALTER TABLE langchain_pg_embedding
    ALTER COLUMN embedding TYPE vector({EMBEDDING_DIMENSIONS});
""")

# 현재 컬럼 타입 확인용 (이미 차원이 지정되었으면 ALTER 생략)
CHECK_COLUMN_SQL = text("""
    SELECT atttypmod
    FROM pg_attribute
    WHERE attrelid = 'langchain_pg_embedding'::regclass
      AND attname = 'embedding';
""")

# Step 2: HNSW 인덱스 생성
# pgvector HNSW는 vector 타입 최대 2000차원까지만 지원.
# text-embedding-3-large는 3072차원이므로 halfvec으로 캐스팅하여 인덱싱.
# halfvec(half-precision float)은 최대 4000차원까지 HNSW 인덱스 가능.
# 정밀도 손실은 float32 -> float16 수준이지만 recall에 미치는 영향은 미미함.
# 참고: https://supabase.com/docs/guides/ai/vector-indexes/hnsw-indexes
CREATE_INDEX_SQL = text(f"""
    CREATE INDEX IF NOT EXISTS langchain_pg_embedding_hnsw_idx
    ON langchain_pg_embedding
    USING hnsw ((embedding::halfvec({EMBEDDING_DIMENSIONS})) halfvec_cosine_ops)
    WITH (m = {HNSW_M}, ef_construction = {HNSW_EF_CONSTRUCTION});
""")

VERIFY_INDEX_SQL = text("""
    SELECT indexname, indexdef
    FROM pg_indexes
    WHERE tablename = 'langchain_pg_embedding'
      AND indexname = 'langchain_pg_embedding_hnsw_idx';
""")


def create_hnsw_index():
    """
    embedding 컬럼에 차원을 부여하고 HNSW 인덱스를 생성합니다.

    실행 흐름:
    1. embedding 컬럼 타입 확인 (이미 차원이 있으면 ALTER 생략)
    2. vector -> vector(3072)로 타입 변경
    3. HNSW 인덱스 생성
    4. 인덱스 존재 검증
    """
    connection_url = os.getenv("POSTGRES_URL")
    if not connection_url:
        print("[Error] POSTGRES_URL 환경변수가 설정되지 않았습니다.")
        return

    connection_url = _prepare_connection_string(connection_url)

    engine = create_engine(
        connection_url,
        pool_pre_ping=True,
        pool_recycle=300,
    )

    # Step 1: embedding 컬럼 차원 확인 및 변경
    print(f"[1/3] embedding 컬럼 차원 확인 중...")
    try:
        with engine.connect() as conn:
            result = conn.execute(CHECK_COLUMN_SQL)
            row = result.fetchone()
            # atttypmod: -1이면 차원 미지정, 양수이면 차원이 지정됨
            atttypmod = row[0] if row else -1

            if atttypmod == -1:
                print(f"   -> 차원 미지정 상태. vector({EMBEDDING_DIMENSIONS})로 변경합니다...")
                conn.execute(ALTER_COLUMN_SQL)
                conn.commit()
                print(f"[1/3] 컬럼 타입 변경 완료: vector -> vector({EMBEDDING_DIMENSIONS})")
            else:
                current_dim = atttypmod
                print(f"[1/3] 이미 차원이 지정되어 있습니다 (atttypmod={current_dim}). ALTER 생략.")
    except Exception as e:
        print(f"[Error] 컬럼 타입 변경 실패: {e}")
        raise

    # Step 2: HNSW 인덱스 생성
    print(f"[2/3] HNSW 인덱스 생성 중 (m={HNSW_M}, ef_construction={HNSW_EF_CONSTRUCTION})...")
    try:
        with engine.connect() as conn:
            conn.execute(CREATE_INDEX_SQL)
            conn.commit()
        print("[2/3] HNSW 인덱스 생성 완료")
    except Exception as e:
        print(f"[Error] 인덱스 생성 실패: {e}")
        raise

    # Step 3: 인덱스 존재 검증
    print("[3/3] 인덱스 존재 검증 중...")
    try:
        with engine.connect() as conn:
            result = conn.execute(VERIFY_INDEX_SQL)
            rows = result.fetchall()

            if rows:
                print(f"[3/3] 검증 성공: {rows[0][0]}")
                print(f"       정의: {rows[0][1]}")
            else:
                print("[Warning] 인덱스가 생성되었으나 pg_indexes에서 확인되지 않습니다.")
    except Exception as e:
        print(f"[Error] 검증 중 오류: {e}")

    engine.dispose()
    print("HNSW 인덱스 설정이 완료되었습니다.")


if __name__ == "__main__":
    create_hnsw_index()
