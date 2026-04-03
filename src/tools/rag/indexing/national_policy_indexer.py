"""
국가 정책 뉴스 CSV -> pgvector 인덱서

CSV 파일(국토교통부_부동산정책)을 읽어서
각 행을 Document로 정제한 뒤 pgvector에 임베딩과 함께 적재합니다.

page_content 포맷은 하류 netional_news_to_drive()의 정규식 파싱과
정확히 일치해야 합니다:
    날짜: {date}
    제목: {title}
    링크: {link}
"""

import os
import re
import sys
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트 경로 추가 (모듈 임포트를 위해)
# src/ 디렉토리를 sys.path에 추가해야 tools.rag.* 등 모듈 임포트가 가능
src_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(src_root))

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from tools.rag.vector_store import get_pgvector_store
from tools.rag.document_loader.csv_loader import load_csv_loader
from tools.rag.db_collection_name import NATIONAL_POLICY_KEY
from utils.util import get_project_root

project_root = get_project_root()  # pyproject.toml 기준 ALL_FOR_ONE/
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path, override=True)

# .env 파일에 중복된 POSTGRES_URL이 있는 경우 (예: localhost 설정이 덮어씀) 방어 로직
postgres_url = os.getenv("POSTGRES_URL")
if postgres_url and "localhost" in postgres_url:
    print("[Warning] .env 파일 하단에 덮어씌워진 localhost 접속 정보가 감지되었습니다.")
    print("원활한 진행을 위해 Supabase 주소(pooler)를 명시적으로 찾습니다.")
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("POSTGRES_URL") and "supabase" in line:
                raw_url = line.split("=", 1)[1].strip().strip('"').strip("'")
                try:
                    prefix_part, rest = raw_url.split("://", 1)
                    auth_part, host_part = rest.split("@", 1)
                    user_part, pass_part = auth_part.split(":", 1)
                    encoded_pass = urllib.parse.quote_plus(pass_part)
                    safe_url = f"{prefix_part}://{user_part}:{encoded_pass}@{host_part}"
                    os.environ["POSTGRES_URL"] = safe_url
                except Exception:
                    os.environ["POSTGRES_URL"] = raw_url
                break

CSV_FILE_PATH = (
    project_root / "src" / "data" / "policy_factors"
    / "국토교통부_부동산정책(2024~2025) - 최종.csv"
)

# CSV 제목 컬럼의 보일러플레이트 패턴
# 원본: "{제목}{제목반복} 관련 보도자료 내용입니다. 자세한 내용은 첨부파일을...{날짜}{부처명}"
BOILERPLATE_PATTERN = re.compile(
    r"관련 보도자료 내용입니다.*$", re.DOTALL
)

# 제목이 연속으로 2번 반복되는 패턴 제거
# 예: "서울 3곳 도심 복합지구 지정서울 3곳 도심 복합지구 지정" -> "서울 3곳 도심 복합지구 지정"
DUPLICATE_TITLE_PATTERN = re.compile(r"^(.{10,}?)\1")


def _clean_title(raw_title: str) -> str:
    """
    CSV 제목 컬럼에서 순수 제목만 추출합니다.

    원본 형태: "{제목}{제목반복} 관련 보도자료 내용입니다...{날짜}{부처명}"
    -> 보일러플레이트 제거 -> 중복 제목 제거 -> 순수 제목 반환
    """
    # 1단계: "관련 보도자료 내용입니다..." 이후 제거
    cleaned = BOILERPLATE_PATTERN.sub("", raw_title).strip()

    # 2단계: 제목이 2번 반복된 경우 1번으로 축소
    dup_match = DUPLICATE_TITLE_PATTERN.match(cleaned)
    if dup_match:
        cleaned = dup_match.group(1).strip()

    return cleaned if cleaned else raw_title.strip()


def build_national_policy_index():
    """
    국가 정책 뉴스 CSV를 pgvector에 임베딩하여 적재합니다.

    처리 흐름:
    1. CSV 로드 (metadata_columns로 날짜, 연도 분리)
    2. 각 행을 정제된 Document로 변환
    3. RecursiveCharacterTextSplitter 적용 (chunk_size=500)
       - 각 행이 약 100~200자이므로 실제 분할은 발생하지 않음
    4. 기존 컬렉션 삭제 후 배치 삽입
    """
    print(f"[1/4] CSV 파일 로드 시작: {CSV_FILE_PATH}")

    if not CSV_FILE_PATH.exists():
        print(f"[Error] 파일을 찾을 수 없습니다: {CSV_FILE_PATH}")
        return

    loader = load_csv_loader(
        file_path=str(CSV_FILE_PATH),
        encoding="utf-8",
        metadata_columns=["날짜", "연도"],
    )
    docs = loader.load()
    print(f"[1/4] 로드 완료. 총 {len(docs)}행의 데이터가 추출되었습니다.")

    # Document 정제: 하류 netional_news_to_drive() 파싱 포맷에 맞춤
    print("[2/4] Document 정제 중...")
    refined_docs = []

    for idx, doc in enumerate(docs):
        # CSVLoader가 metadata_columns 외 나머지를 page_content에 넣음
        # page_content 형태: "제목: {raw_title}\n링크: {link}"
        content_lines = doc.page_content.split("\n")
        data_dict = {}
        for line in content_lines:
            if ":" in line:
                key, val = line.split(":", 1)
                data_dict[key.strip()] = val.strip()

        date = str(doc.metadata.get("날짜", "")).strip()
        year = str(doc.metadata.get("연도", "")).strip()
        raw_title = data_dict.get("제목", "")
        link = data_dict.get("링크", "")

        # 빈 행 또는 헤더 행 필터링
        if not raw_title or not date:
            continue

        clean = _clean_title(raw_title)

        # netional_news_to_drive()가 파싱하는 정확한 포맷:
        #   r"날짜:\s*([0-9\-]+)"
        #   r"제목:\s*(.*?)\n링크:" (re.DOTALL)
        #   r"링크:\s*(https?://[^\s]+)"
        page_content = f"날짜: {date}\n제목: {clean}\n링크: {link}"

        metadata = {
            "source": "국토교통부_부동산정책",
            "date": date,
            "year": int(year) if year.isdigit() else 0,
            "link": link,
            "row": idx,
        }

        refined_docs.append(
            Document(page_content=page_content, metadata=metadata)
        )

    print(f"[2/4] Document 정제 완료 ({len(refined_docs)}건)")

    # 텍스트 분할 (각 행이 ~200자이므로 실제 분할은 거의 발생하지 않음)
    print("[3/4] 텍스트 분할 중...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )

    split_docs = []
    for doc in refined_docs:
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

    print(f"[3/4] 분할 완료 ({len(split_docs)}건)")

    # pgvector 적재
    print(f"[4/4] Supabase pgvector({NATIONAL_POLICY_KEY})에 임베딩 및 적재 시작...")
    try:
        store = get_pgvector_store(NATIONAL_POLICY_KEY)

        # 기존 컬렉션 초기화
        print("   -> 기존 NATIONAL_POLICY 컬렉션 초기화 중...")
        store.delete_collection()

        # 인메모리 캐시 무효화 (삭제된 컬렉션 객체가 재사용되는 것을 방지)
        from tools.rag.vector_store import _pgvector_cache
        _pgvector_cache.pop(NATIONAL_POLICY_KEY, None)

        # 새 컬렉션으로 재생성
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
            f"[4/4] 성공적으로 {len(split_docs)}건의 국가 정책 데이터가 "
            f"Supabase(pgvector)에 적재되었습니다!"
        )
    except Exception as e:
        print(f"[Error] 적재 중 오류 발생: {e}")
        raise


if __name__ == "__main__":
    build_national_policy_index()
