"""
pgroonga 전문 검색 인덱스 생성 스크립트

langchain_pg_embedding 테이블의 document(본문)와 cmetadata(메타데이터) 컬럼에
pgroonga 인덱스를 생성합니다.

pgroonga는 Groonga 기반 PostgreSQL 전문 검색 확장으로,
기본 TokenBigram 토크나이저가 한국어를 바이그램으로 분해하여 처리합니다.
참고: https://supabase.com/docs/guides/database/extensions/pgroonga

이 인덱스가 생성되면 pgvector(벡터 검색)와 pgroonga(키워드 검색)가
같은 테이블에서 수행되어, UUID 기준 점수 합산이 가능한 Hybrid Search가 됩니다.

이 스크립트는 멱등(idempotent)합니다 — IF NOT EXISTS로 중복 실행해도 안전합니다.
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

# pgroonga 확장 활성화
ENABLE_EXTENSION_SQL = text(
    "CREATE EXTENSION IF NOT EXISTS pgroonga;"
)

# document 컬럼 전문 검색 인덱스
# document(varchar)에는 page_content가 저장됨
# pgroonga의 &@~ 연산자로 키워드 검색 시 이 인덱스를 사용
CREATE_DOC_INDEX_SQL = text("""
    CREATE INDEX IF NOT EXISTS langchain_pg_embedding_pgroonga_doc_idx
    ON langchain_pg_embedding
    USING pgroonga (document);
""")

# cmetadata(jsonb) 컬럼 전문 검색 인덱스
# 메타데이터 필드(policy_type, date 등) 내부의 텍스트도 검색 가능
CREATE_META_INDEX_SQL = text("""
    CREATE INDEX IF NOT EXISTS langchain_pg_embedding_pgroonga_meta_idx
    ON langchain_pg_embedding
    USING pgroonga (cmetadata);
""")

VERIFY_INDEX_SQL = text("""
    SELECT indexname, indexdef
    FROM pg_indexes
    WHERE tablename = 'langchain_pg_embedding'
      AND indexname LIKE '%pgroonga%';
""")


def create_pgroonga_indexes():
    """
    pgroonga 확장을 활성화하고 전문 검색 인덱스를 생성합니다.

    실행 흐름:
    1. pgroonga 확장 활성화
    2. document 컬럼 인덱스 생성
    3. cmetadata 컬럼 인덱스 생성
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

    # Step 1: pgroonga 확장 활성화
    print("[1/4] pgroonga 확장 활성화 중...")
    try:
        with engine.connect() as conn:
            conn.execute(ENABLE_EXTENSION_SQL)
            conn.commit()
        print("[1/4] pgroonga 확장 활성화 완료")
    except Exception as e:
        print(f"[Error] pgroonga 확장 활성화 실패: {e}")
        print("       Supabase Dashboard > Database > Extensions에서 pgroonga를 활성화하세요.")
        raise

    # Step 2: document 인덱스 생성
    print("[2/4] document 컬럼 pgroonga 인덱스 생성 중...")
    try:
        with engine.connect() as conn:
            conn.execute(CREATE_DOC_INDEX_SQL)
            conn.commit()
        print("[2/4] document 인덱스 생성 완료")
    except Exception as e:
        print(f"[Error] document 인덱스 생성 실패: {e}")
        raise

    # Step 3: cmetadata 인덱스 생성
    print("[3/4] cmetadata 컬럼 pgroonga 인덱스 생성 중...")
    try:
        with engine.connect() as conn:
            conn.execute(CREATE_META_INDEX_SQL)
            conn.commit()
        print("[3/4] cmetadata 인덱스 생성 완료")
    except Exception as e:
        print(f"[Error] cmetadata 인덱스 생성 실패: {e}")
        raise

    # Step 4: 검증
    print("[4/4] pgroonga 인덱스 존재 검증 중...")
    try:
        with engine.connect() as conn:
            result = conn.execute(VERIFY_INDEX_SQL)
            rows = result.fetchall()

            if rows:
                for row in rows:
                    print(f"   -> {row[0]}")
                print(f"[4/4] 검증 성공: pgroonga 인덱스 {len(rows)}개 확인")
            else:
                print("[Warning] 인덱스가 생성되었으나 pg_indexes에서 확인되지 않습니다.")
    except Exception as e:
        print(f"[Error] 검증 중 오류: {e}")

    engine.dispose()
    print("pgroonga 인덱스 설정이 완료되었습니다.")


if __name__ == "__main__":
    create_pgroonga_indexes()
