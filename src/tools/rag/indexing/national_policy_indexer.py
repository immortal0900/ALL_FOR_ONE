"""
국가 정책 뉴스 CSV -> pgvector 인덱서

공통 로더(national_policy_loader.py)로 CSV를 읽고 정제한 뒤
pgvector에 임베딩과 함께 적재합니다.

공통 로더를 사용하는 이유:
- 인덱서와 retriever fallback이 동일한 정제 로직을 공유
- CSV 로드 + _clean_title() 정제를 한 단계로 처리
"""

import os
import sys
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv

# src/ 디렉토리를 sys.path에 추가해야 tools.rag.* 등 모듈 임포트가 가능
src_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(src_root))

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from tools.rag.vector_store import get_pgvector_store
from tools.rag.db_collection_name import NATIONAL_POLICY_KEY
from tools.rag.document_loader.national_policy_loader import (
    load_national_policy_documents,
    CSV_FILE_PATH,
)
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


def build_national_policy_index():
    """
    국가 정책 뉴스 CSV를 pgvector에 임베딩하여 적재합니다.

    처리 흐름:
    1. 공통 로더로 CSV 로드 + 제목 정제
    2. RecursiveCharacterTextSplitter 적용 (chunk_size=500)
       - 각 행이 약 100~200자이므로 실제 분할은 발생하지 않음
    3. 기존 컬렉션 삭제 후 배치 삽입
    """
    # 1. 공통 로더로 CSV 로드 + 정제
    print(f"[1/3] CSV 로드 + 정제 시작: {CSV_FILE_PATH}")
    docs = load_national_policy_documents()
    print(f"[1/3] 로드 완료. 총 {len(docs)}건")

    # 2. 텍스트 분할 (각 행이 ~200자이므로 실제 분할은 거의 발생하지 않음)
    print("[2/3] 텍스트 분할 중...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )

    split_docs = []
    for doc in docs:
        chunks = text_splitter.split_text(doc.page_content)
        for chunk_idx, chunk in enumerate(chunks):
            split_doc = Document(
                page_content=chunk,
                metadata={
                    **doc.metadata,
                    "chunk_id": chunk_idx,
                    "total_chunks": len(chunks),
                },
            )
            split_docs.append(split_doc)

    print(f"[2/3] 분할 완료 ({len(split_docs)}건)")

    # 3. pgvector 적재
    print(f"[3/3] Supabase pgvector({NATIONAL_POLICY_KEY})에 임베딩 및 적재 시작...")
    try:
        store = get_pgvector_store(NATIONAL_POLICY_KEY)

        print("   -> 기존 NATIONAL_POLICY 컬렉션 초기화 중...")
        store.delete_collection()

        # 인메모리 캐시 무효화
        from tools.rag.vector_store import _pgvector_cache
        _pgvector_cache.pop(NATIONAL_POLICY_KEY, None)

        store = get_pgvector_store(NATIONAL_POLICY_KEY)

        batch_size = 100
        total_batches = (len(split_docs) + batch_size - 1) // batch_size

        for i in range(total_batches):
            start_idx = i * batch_size
            end_idx = min(start_idx + batch_size, len(split_docs))
            batch_docs = split_docs[start_idx:end_idx]

            store.add_documents(batch_docs)
            print(f"   -> Batch {i + 1}/{total_batches} 적재 완료 ({len(batch_docs)}건)")

        print(
            f"[3/3] 성공적으로 {len(split_docs)}건의 국가 정책 데이터가 "
            f"Supabase(pgvector)에 적재되었습니다!"
        )
    except Exception as e:
        print(f"[Error] 적재 중 오류 발생: {e}")
        raise


if __name__ == "__main__":
    build_national_policy_index()
