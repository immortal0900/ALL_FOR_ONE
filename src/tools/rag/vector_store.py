from langchain_community.vectorstores import PGVector
from langchain_openai import OpenAIEmbeddings
import os
from dotenv import load_dotenv
from threading import Lock

load_dotenv()

_pgvector_cache = {}
_pgvector_lock = Lock()

def _prepare_connection_string(connection_url: str) -> str:
    """
    Supabase 연결 문자열을 처리합니다.
    Supabase는 connection pooling을 사용하므로 연결 문자열을 조정합니다.
    연결 안정성을 위한 파라미터를 추가합니다.
    """
    if not connection_url:
        return connection_url
    
    if "pooler.supabase.com" in connection_url:
        pass
    elif "supabase.com" in connection_url or "supabase.co" in connection_url:
        if "pooler" not in connection_url:
            if "@aws-" in connection_url and ".pooler." not in connection_url:
                connection_url = connection_url.replace("@aws-", "@aws-0-ap-northeast-2.pooler.")
            elif ".supabase.co" in connection_url:
                connection_url = connection_url.replace(".supabase.co", ".pooler.supabase.com")
    
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
            )
        else:
            try:
                store = _pgvector_cache[collection_name]
                store._conn
            except Exception:
                print(f"[PGVector] 연결이 끊어져 재생성합니다: {collection_name}")
                del _pgvector_cache[collection_name]
                emb = OpenAIEmbeddings(model="text-embedding-3-large")
                connection_url = os.getenv("POSTGRES_URL")
                if connection_url:
                    connection_url = _prepare_connection_string(connection_url)
                _pgvector_cache[collection_name] = PGVector(
                    embedding_function=emb,
                    connection_string=connection_url,
                    collection_name=collection_name,
                    use_jsonb=True,
                )

        return _pgvector_cache[collection_name]
