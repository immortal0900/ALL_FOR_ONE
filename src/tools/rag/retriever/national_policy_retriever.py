"""
국가 정책 뉴스 Retriever
pgvector(벡터 검색) + pgroonga(키워드 검색)를 결합한 Hybrid Search를 구현합니다.

두 검색 모두 같은 langchain_pg_embedding 테이블에서 수행되므로,
UUID 기준 점수 합산이 의미 있는 진정한 Hybrid Search입니다.

반환 형태: List[str] (각 원소가 "날짜: ...\n제목: ...\n링크: ..." 포맷)
이 포맷은 하류 netional_news_to_drive()의 정규식 파싱과 일치해야 합니다.
"""

import json
import re
from typing import List, Optional, Dict, Tuple

from langchain_core.documents import Document
from sqlalchemy import text

from tools.rag.vector_store import (
    get_pgvector_store,
    get_sql_engine,
    get_collection_id,
)
from tools.rag.db_collection_name import NATIONAL_POLICY_KEY
from tools.rag.document_loader.national_policy_loader import (
    load_national_policy_documents,
)


class NationalPolicyRetriever:
    """
    국가 정책 뉴스 검색 시스템
    pgvector 벡터 유사도(0.7)와 pgroonga 키워드 검색(0.3)을
    UUID 기준으로 합산하는 Hybrid Search를 수행합니다.
    """

    def __init__(self):
        """pgvector 스토어를 초기화합니다."""
        self.vector_store = get_pgvector_store(NATIONAL_POLICY_KEY)
        self.collection_id = get_collection_id(NATIONAL_POLICY_KEY)

    def semantic_search(self, query: str, k: int = 15) -> List[Tuple[Document, float]]:
        """
        벡터 유사도 기반 검색을 수행합니다.

        Args:
            query: 검색 쿼리
            k: 반환할 문서 개수

        Returns:
            (Document, distance) 튜플 리스트. distance는 코사인 거리 (낮을수록 유사).
        """
        return self.vector_store.similarity_search_with_score(query, k=k)

    def keyword_search(self, query: str, k: int = 15) -> List[Tuple[Document, float]]:
        """
        pgroonga 전문 검색으로 키워드 매칭 문서를 반환합니다.

        Args:
            query: pgroonga 검색 쿼리 (OR/AND/- 연산자 지원)
            k: 반환할 문서 개수

        Returns:
            (Document, score) 튜플 리스트. score는 pgroonga 관련도 (높을수록 관련).
        """
        engine = get_sql_engine()

        sql = text("""
            SELECT uuid, document, cmetadata,
                   pgroonga_score(tableoid, ctid) AS score
            FROM langchain_pg_embedding
            WHERE collection_id = :cid
              AND document &@~ :query
            ORDER BY score DESC
            LIMIT :k
        """)

        results = []
        with engine.connect() as conn:
            rows = conn.execute(
                sql,
                {"cid": self.collection_id, "query": query, "k": k},
            )
            for row in rows:
                metadata = row[2] if isinstance(row[2], dict) else json.loads(row[2])
                doc = Document(page_content=row[1], metadata=metadata)
                doc.metadata["uuid"] = str(row[0])
                results.append((doc, float(row[3])))

        return results

    def hybrid_search(
        self,
        query: str,
        keywords: Optional[List[str]] = None,
        semantic_weight: float = 0.7,
        k: int = 15,
    ) -> List[str]:
        """
        Hybrid Search를 수행합니다.
        pgvector 벡터 유사도와 pgroonga 키워드 검색 결과를
        UUID 기준으로 합산하여 최종 순위를 결정합니다.

        Args:
            query: 검색 쿼리
            keywords: 미사용 (하위 호환용)
            semantic_weight: 벡터 검색 가중치 (기본 0.7)
            k: 반환할 문서 개수

        Returns:
            page_content 문자열 리스트 (점수순 정렬)
        """
        # 1. 벡터 검색 (pgvector)
        semantic_results = self.semantic_search(query, k=k * 2)

        # 2. pgroonga 키워드 검색
        pgroonga_query = self._build_pgroonga_query(query)
        keyword_results = self.keyword_search(pgroonga_query, k=k * 2)

        # 3. 점수 정규화 + UUID 기준 합산
        combined = self._merge_scores(
            semantic_results, keyword_results, semantic_weight
        )

        # 4. 상위 k개의 page_content 반환
        sorted_results = sorted(
            combined.values(), key=lambda x: x["score"], reverse=True
        )
        return [item["doc"].page_content for item in sorted_results[:k]]

    def _merge_scores(
        self,
        semantic_results: List[Tuple[Document, float]],
        keyword_results: List[Tuple[Document, float]],
        semantic_weight: float,
    ) -> Dict[str, dict]:
        """
        벡터 검색과 키워드 검색 결과를 UUID 기준으로 합산합니다.

        점수 정규화:
        - pgvector: 코사인 거리 (0~2, 낮을수록 유사) → 1 - (dist/max_dist)
        - pgroonga: relevance score (높을수록 관련) → score/max_score
        """
        keyword_weight = 1.0 - semantic_weight
        combined: Dict[str, dict] = {}

        if semantic_results:
            max_dist = max(dist for _, dist in semantic_results) or 1.0
            for doc, dist in semantic_results:
                doc_id = self._get_doc_id(doc)
                norm_score = semantic_weight * (1.0 - dist / max_dist) if max_dist > 0 else 0.0
                combined[doc_id] = {"doc": doc, "score": norm_score}

        if keyword_results:
            max_kw_score = max(score for _, score in keyword_results) or 1.0
            for doc, score in keyword_results:
                doc_id = self._get_doc_id(doc)
                norm_score = keyword_weight * (score / max_kw_score) if max_kw_score > 0 else 0.0

                if doc_id in combined:
                    combined[doc_id]["score"] += norm_score
                else:
                    combined[doc_id] = {"doc": doc, "score": norm_score}

        return combined

    def _get_doc_id(self, doc: Document) -> str:
        """Document의 고유 ID를 반환합니다."""
        if "uuid" in doc.metadata:
            return doc.metadata["uuid"]
        source = doc.metadata.get("source", "")
        chunk_id = doc.metadata.get("chunk_id", 0)
        return f"{source}_{chunk_id}"

    def _build_pgroonga_query(self, query: str) -> str:
        """
        원본 쿼리에서 국가 정책 뉴스 도메인 키워드를 추출하여
        pgroonga OR 쿼리로 확장합니다.

        Args:
            query: 원본 검색 쿼리

        Returns:
            pgroonga &@~ 연산자용 쿼리 문자열
        """
        keywords = []

        important_terms = [
            # 정책 방향
            "공급", "규제", "안정화", "완화", "강화", "대책",
            # 주택 유형/시장
            "재건축", "재개발", "분양", "청약", "전매제한",
            "아파트", "주택", "오피스텔", "임대", "전세",
            # 금융/대출
            "대출", "주담대", "전세대출", "금리", "LTV", "DTI", "DSR",
            # 세금
            "취득세", "양도세", "재산세", "종부세",
            # 지역
            "수도권", "서울", "경기", "지방", "투기과열지구", "조정대상지역",
            # 정책 주체/수단
            "국토교통부", "금융위", "한국은행",
            "공공주택", "복합지구", "정비사업", "도시정비",
        ]

        query_upper = query.upper()
        for term in important_terms:
            if term.upper() in query_upper:
                keywords.append(term)

        # 숫자 패턴 추출 (날짜, 비율, 금액 등)
        numbers = re.findall(r"\d+(?:\.\d+)?[%년월일억원만호세대]?", query)
        keywords.extend(numbers)

        all_terms = [query] + keywords
        return " OR ".join(all_terms)


def national_policy_retrieve(
    query: Optional[str] = None, k: int = 15
) -> List[str]:
    """
    국가 정책 뉴스를 검색합니다.

    query가 주어지면 pgvector + pgroonga Hybrid Search로 관련 뉴스를 선별하고,
    query가 None이면 공통 로더로 CSV 전량 로드하여 fallback합니다.

    Args:
        query: 검색 쿼리 (None이면 CSV 전량 로드)
        k: 반환할 문서 개수

    Returns:
        "날짜: ...\n제목: ...\n링크: ..." 포맷의 문자열 리스트
    """
    if query is None:
        # Fallback: 공통 로더로 CSV 전량 로드 (인덱서와 동일한 정제 로직)
        docs = load_national_policy_documents()
        return [doc.page_content for doc in docs]

    retriever = NationalPolicyRetriever()
    return retriever.hybrid_search(query, k=k)
