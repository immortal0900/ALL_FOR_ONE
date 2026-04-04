from langchain_community.vectorstores import PGVector
from langchain_openai import OpenAIEmbeddings
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from threading import Lock

load_dotenv()

_pgvector_cache = {}
_pgvector_lock = Lock()

# pgroonga raw SQL 실행용 엔진 캐시
_engine_cache = None
_engine_lock = Lock()

# 컬렉션 이름 → UUID 매핑 캐시
_collection_id_cache = {}


import urllib.parse
def _prepare_connection_string(connection_url: str) -> str:
    """
    Supabase 연결 문자열을 처리합니다.
    Supabase는 connection pooling을 사용하므로 연결 문자열을 조정합니다.
    연결 안정성을 위한 파라미터를 추가합니다.
    """
    if not connection_url:
        return connection_url

    # 터미널에서 set 명령어로 입력한 따옴표(") 혹은 작은따옴표(')가 
    # 문자열 자체로 들어온 경우 SQLAlchemy가 파싱하지 못하므로 양끝 제거
    connection_url = connection_url.strip('"').strip("'")

    # 비밀번호 특수문자 URL 인코딩 (SQLAlchemy 파싱 오류 방지)
    try:
        # 형태: dialect://user:pass@host:port/db...?
        if "://" in connection_url and "@" in connection_url:
            prefix, rest = connection_url.split("://", 1)
            auth, host_part = rest.split("@", 1)
            if ":" in auth:
                user, pwd = auth.split(":", 1)
                encoded_pwd = urllib.parse.quote_plus(urllib.parse.unquote_plus(pwd))
                connection_url = f"{prefix}://{user}:{encoded_pwd}@{host_part}"
    except Exception as e:
        print(f"[Warning] URL 인코딩 중 오류: {e}")

    if "pooler.supabase.com" in connection_url:
        pass
    elif "supabase.com" in connection_url or "supabase.co" in connection_url:
        if "pooler" not in connection_url:
            if "@aws-" in connection_url and ".pooler." not in connection_url:
                connection_url = connection_url.replace(
                    "@aws-", "@aws-0-ap-northeast-2.pooler."
                )
            elif ".supabase.co" in connection_url:
                connection_url = connection_url.replace(
                    ".supabase.co", ".supabase.com" # 풀러 교정이 필요 시 다른 부분에서 처리됨
                )

    if "?" in connection_url:
        if "connect_timeout" not in connection_url:
            connection_url += "&connect_timeout=10"
        if "keepalives_idle" not in connection_url:
            connection_url += "&keepalives_idle=30"
        if "keepalives_interval" not in connection_url:
            connection_url += "&keepalives_interval=10"
        if "keepalives_count" not in connection_url:
            connection_url += "&keepalives_count=5"
    else:
        connection_url += "?connect_timeout=10&keepalives_idle=30&keepalives_interval=10&keepalives_count=5"

    return connection_url


def get_pgvector_store(collection_name: str):
    """
    PGVector 스토어를 안전하게 1회만 초기화하고 재사용.
    SQLAlchemy 메타데이터 중복 정의 문제도 함께 방지.
    Supabase 연결 풀링 문제 해결.
    연결이 끊어졌을 경우 재생성합니다.
    """
    with _pgvector_lock:
        if collection_name not in _pgvector_cache:
            try:
                from langchain_community.vectorstores import pgvector as pgv

                meta = pgv.BaseModel.metadata
                for tname in list(meta.tables.keys()):
                    if tname.startswith("langchain_pg_"):
                        meta.remove(meta.tables[tname])
            except Exception as e:
                print(f"[PGVector Init Warning] {e}")

            emb = OpenAIEmbeddings(model="text-embedding-3-large")
            connection_url = os.getenv("POSTGRES_URL")

            if connection_url:
                connection_url = _prepare_connection_string(connection_url)

            _pgvector_cache[collection_name] = PGVector(
                embedding_function=emb,
                connection_string=connection_url,
                collection_name=collection_name,
                use_jsonb=True,
                engine_args={
                    "pool_pre_ping": True,   # 커넥션 사용 전 "SELECT 1" 헬스체크
                    "pool_recycle": 300,     # 5분마다 커넥션 재생성 (Supabase idle timeout 전에)
                    "pool_size": 5,          # 기본 풀 크기
                    "max_overflow": 3,       # 버스트 시 추가 허용 커넥션
                },
            )
        else:
            pass

        return _pgvector_cache[collection_name]


def get_sql_engine():
    """
    pgroonga raw SQL 실행용 SQLAlchemy 엔진을 반환합니다.
    싱글톤 패턴으로 캐싱하여 반복 생성을 방지합니다.

    LangChain PGVector 클래스가 raw SQL(pgroonga &@~ 연산자 등)을 노출하지 않으므로,
    키워드 검색 시 이 엔진을 통해 직접 SQL을 실행합니다.
    """
    global _engine_cache
    with _engine_lock:
        if _engine_cache is None:
            connection_url = os.getenv("POSTGRES_URL")
            if connection_url:
                connection_url = _prepare_connection_string(connection_url)

            _engine_cache = create_engine(
                connection_url,
                pool_pre_ping=True,
                pool_recycle=300,
                pool_size=5,
                max_overflow=3,
            )
        return _engine_cache


def get_collection_id(collection_name: str) -> str:
    """
    컬렉션 이름으로 UUID를 조회합니다.
    결과를 캐싱하여 반복 쿼리를 방지합니다.

    pgroonga 키워드 검색 시 collection_id로 필터링해야
    다른 컬렉션의 문서가 결과에 섞이지 않습니다.

    Args:
        collection_name: 컬렉션 이름 (예: "policy_documents", "NATIONAL_POLICY")

    Returns:
        컬렉션 UUID 문자열

    Raises:
        ValueError: 컬렉션이 존재하지 않는 경우
    """
    if collection_name in _collection_id_cache:
        return _collection_id_cache[collection_name]

    engine = get_sql_engine()
    sql = text(
        "SELECT uuid FROM langchain_pg_collection WHERE name = :name"
    )

    with engine.connect() as conn:
        result = conn.execute(sql, {"name": collection_name})
        row = result.fetchone()

    if not row:
        raise ValueError(
            f"컬���션 '{collection_name}'이 존재하지 않습니다. "
            f"인덱서를 먼저 실행하세요."
        )

    collection_id = str(row[0])
    _collection_id_cache[collection_name] = collection_id
    return collection_id
