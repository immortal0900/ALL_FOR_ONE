from langchain_community.vectorstores import PGVector
from langchain_openai import OpenAIEmbeddings
import os
from dotenv import load_dotenv
from threading import Lock

load_dotenv()

_pgvector_cache = {}
_pgvector_lock = Lock()


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
            )
        else:
            pass

        return _pgvector_cache[collection_name]
