from tools.rag.vector_store import get_pgvector_store
from tools.rag.db_collection_name import UNSOLD_HOUSING_KEY
from utils.llm import LLMProfile

def unsold_units(target_area):
    """
    RAG(Supabase) 기반으로 특정 지역의 미분양 현황 데이터를 검색합니다.
    """
    llm = LLMProfile.dev_llm().invoke(
        f"""
        당신은 대한민국 서울특별시 자치구를 찾아주는 도우미 입니다. 
        에이전트 흐름중 사용하고 있습니다. 주소 질문에 특정 자치구만 찾아서 
        그부분만 출력해주시면 됩니다.

        [강력 지침]
        - 자치구 말이외에 절대 다른말을 하지마세요
        - 자치구만 말씀하세요

        [예시]
        1. "서울특별시 종로구" -> "종로구"
        2. "서울 강동구 서초동" -> "강남구"

        질문: {target_area}
        """
    )
    query = llm.content.strip()

    # Supabase (pgvector) 컬렉션 로드
    store = get_pgvector_store(UNSOLD_HOUSING_KEY)
    
    # 쿼리 기반 유사도 검색 수행 (충분한 시계열 데이터를 위해 k=50 정도 스캔)
    # metadata 필터링도 가능하면 추가할 수 있으나, 일단 유사도 검색으로 지역 필터링을 시도합니다.
    retrieved_docs = store.similarity_search(query, k=50)
    
    # 기존 에이전트 코드가 결과로 dict list 형태를 기대함에 맞게 매핑
    result = []
    for doc in retrieved_docs:
        meta = doc.metadata
        # 기존 pandas DataFrame 컬럼 형식을 모방
        result.append({
            "시도": meta.get("sido", ""),
            "시군구": meta.get("sigungu", ""),
            "연도": meta.get("year", ""),
            "월": meta.get("month", ""),
            "미분양": meta.get("unsold_count", 0),
            "내용": doc.page_content
        })
        
    return result