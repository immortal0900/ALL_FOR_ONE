import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트 경로 추가 (모듈 임포트를 위해)
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))

from langchain_core.documents import Document
from tools.rag.vector_store import get_pgvector_store
from tools.rag.document_loader.csv_loader import load_csv_loader

env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path, override=True)

# .env 파일에 중복된 POSTGRES_URL이 있는 경우 (예: localhost 설정이 덮어씀) 방어 로직
postgres_url = os.getenv("POSTGRES_URL")
if postgres_url and "localhost" in postgres_url:
    print("[Warning] .env 파일 하단에 덮어씌워진 localhost 접속 정보가 감지되었습니다.")
    print("원활한 진행을 위해 Supabase 주소(pooler)를 명시적으로 찾습니다.")
    import urllib.parse
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("POSTGRES_URL") and "supabase" in line:
                # 라인에서 따옴표, 공백 제거
                raw_url = line.split("=", 1)[1].strip().strip('"').strip("'")
                
                # SQLAlchemy 호환성을 위해 비밀번호 파트의 특수문자 URL 인코딩 ('!' 등)
                # 구조: postgresql://[user]:[password]@[host]:[port]/[db]
                try:
                    prefix_part, rest = raw_url.split("://", 1)
                    auth_part, host_part = rest.split("@", 1)
                    user_part, pass_part = auth_part.split(":", 1)
                    encoded_pass = urllib.parse.quote_plus(pass_part)
                    safe_url = f"{prefix_part}://{user_part}:{encoded_pass}@{host_part}"
                    os.environ["POSTGRES_URL"] = safe_url
                except Exception as e:
                    # 파싱 실패시 원본 삽입
                    os.environ["POSTGRES_URL"] = raw_url
                break

UNSOLD_HOUSING_COLLECTION = "UNSOLD_HOUSING"
CSV_FILE_PATH = project_root / "data" / "unsold_units" / "미분양_데이터 - 최종.csv"


def build_unsold_housing_index():
    print(f"[1/3] CSV 파일 로드 시작: {CSV_FILE_PATH}")
    
    if not CSV_FILE_PATH.exists():
        print(f"[Error] 파일을 찾을 수 없습니다: {CSV_FILE_PATH}")
        return

    # CSVLoader 초기화 (미분양 현황 데이터용)
    loader = load_csv_loader(
        file_path=str(CSV_FILE_PATH),
        encoding="utf-8",
        # 향후 조회 편의성을 위해 '시도'와 '시군구'를 메타데이터로 추출
        metadata_columns=["시도", "시군구", "연도", "월"]
    )
    
    docs = loader.load()
    print(f"[1/3] 로드 완료. 총 {len(docs)}행의 데이터가 추출되었습니다.")
    
    # ---------------------------------------------------------
    # Document 정제 프로세스
    # CSV loader 기본 출력물의 형식을 더 검색 최적화 되도록 변경
    # ---------------------------------------------------------
    print("[2/3] 벡터 검색 최적화를 위한 Document 재구성 중...")
    refined_docs = []
    
    for idx, doc in enumerate(docs):
        # CSVLoader 설정 시 metadata_columns로 지정한 필드는 doc.metadata에 바로 들어갑니다.
        # 지정되지 않은 '미분양' 같은 필드는 doc.page_content에 남아있습니다.
        content_lines = doc.page_content.split("\n")
        data_dict = {}
        for line in content_lines:
            if ":" in line:
                key, val = line.split(":", 1)
                data_dict[key.strip()] = val.strip()
                
        sido = str(doc.metadata.get("시도", "")).strip()
        sigungu = str(doc.metadata.get("시군구", "")).strip()
        year = str(doc.metadata.get("연도", "")).strip()
        month = str(doc.metadata.get("월", "")).strip()
        
        # 쉼표(,) 제거나 빈 문자열 방어 처리
        unsold_raw = data_dict.get("미분양", "0").replace(",", "").strip()
        if not unsold_raw:
            unsold_raw = "0"
            
        unsold_count = unsold_raw
        
        # '계' 같은 불필요한 행 필터링 (선택적)
        if sigungu == "계" or sido == "계":
            continue

        page_content = f"[{sido} {sigungu}] 지역의 {year}년 {month}월 미분양 아파트 세대수는 총 {unsold_count}세대입니다."
        
        # 새로운 메타데이터 구성 (RAG 필터링 용이성)
        new_metadata = {
            "source": str(CSV_FILE_PATH.name),
            "region": f"{sido} {sigungu}".strip(),
            "sido": sido,
            "sigungu": sigungu,
            "year": int(year) if year.isdigit() else 0,
            "month": int(month) if month.isdigit() else 0,
            "unsold_count": int(unsold_count) if unsold_count.isdigit() else 0,
            "row": idx
        }
        
        refined_docs.append(Document(page_content=page_content, metadata=new_metadata))

    print(f"[2/3] Document 정제 완료 (필터링 후 {len(refined_docs)}건)")

    # ---------------------------------------------------------
    # Supabase PGVector 적재
    # ---------------------------------------------------------
    print(f"[3/3] Supabase PGVector 테이블({UNSOLD_HOUSING_COLLECTION})에 임베딩 및 적재 시작...")
    try:
        store = get_pgvector_store(UNSOLD_HOUSING_COLLECTION)
        
        # 기존 컬렉션 삭제 (CASCADE로 langchain_pg_embedding에서 해당 collection_id 행만 삭제)
        # 다른 에이전트(age_population 등)의 데이터에는 영향 없음
        print("   -> 기존 UNSOLD_HOUSING 컬렉션 초기화 중...")
        store.delete_collection()
        
        # 인메모리 캐시에 남은 삭제된 컬렉션 객체 무효화
        # (이것이 없으면 get_pgvector_store()가 캐시된 죽은 객체를 반환)
        from tools.rag.vector_store import _pgvector_cache
        _pgvector_cache.pop(UNSOLD_HOUSING_COLLECTION, None)
        
        # 새 컬렉션으로 재생성
        store = get_pgvector_store(UNSOLD_HOUSING_COLLECTION)
        
        # 너무 커서 한 번에 안 올라갈 수 있으므로 청크 단위 삽입 (필요시 조절)
        batch_size = 500
        total_batches = (len(refined_docs) + batch_size - 1) // batch_size
        
        for i in range(total_batches):
            start_idx = i * batch_size
            end_idx = min(start_idx + batch_size, len(refined_docs))
            
            # 타입 힌팅 에러를 방어하고 메모리 누수를 방지하기 위한 이터레이터 활용
            batch_docs: list[Document] = [doc for doc in refined_docs[start_idx:end_idx]]
            
            store.add_documents(batch_docs)
            print(f"   -> Batch {i+1}/{total_batches} 적재 완료 ({len(batch_docs)}건)")
            
        print("[3/3] 성공적으로 모든 미분양 데이터가 Supabase(pgvector)에 이관되었습니다!")
    except Exception as e:
        print(f"[Error] 적재 중 오류 발생: {e}")

if __name__ == "__main__":
    build_unsold_housing_index()
