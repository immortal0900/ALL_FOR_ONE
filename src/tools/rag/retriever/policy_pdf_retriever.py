"""
정책 PDF Retriever
pgvector(벡터 검색) + pgroonga(키워드 검색)를 결합한 Hybrid Search를 구현합니다.

두 검색 모두 같은 langchain_pg_embedding 테이블에서 수행되므로,
UUID 기준 점수 합산이 의미 있는 진정한 Hybrid Search입니다.
"""

import json
import re
from typing import List, Optional, Dict, Tuple

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import text

from tools.rag.vector_store import (
    get_pgvector_store,
    get_sql_engine,
    get_collection_id,
)
from tools.rag.document_loader.policy_file_loader import PolicyDocument

# 컬렉션 이름 상수
POLICY_DOCUMENTS_COLLECTION = "policy_documents"


class PolicyPDFRetriever:
    """
    정책 문서 검색 시스템
    pgvector 벡터 유사도(0.7)와 pgroonga 키워드 검색(0.3)을
    UUID 기준으로 합산하는 Hybrid Search를 수행합니다.
    """

    def __init__(self):
        """PolicyPDFRetriever 초기화"""
        self.vector_store = get_pgvector_store(POLICY_DOCUMENTS_COLLECTION)
        self.collection_id = get_collection_id(POLICY_DOCUMENTS_COLLECTION)

    def add_documents(self, policy_documents: List[PolicyDocument]) -> None:
        """
        정책 문서를 벡터 스토어에 추가합니다.

        Args:
            policy_documents: 추가할 PolicyDocument 리스트
        """
        langchain_docs = []

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=150,
        )

        for policy_doc in policy_documents:
            if not isinstance(policy_doc.content, str):
                raise TypeError(
                    f"policy_doc.content는 문자열이어야 합니다. "
                    f"현재 타입: {type(policy_doc.content)}"
                )

            chunks = text_splitter.split_text(policy_doc.content)
            for chunk_idx, chunk in enumerate(chunks):
                langchain_doc = Document(
                    page_content=chunk,
                    metadata={
                        "source": policy_doc.file_path,
                        "policy_date": policy_doc.policy_date,
                        "policy_type": policy_doc.policy_type.value,
                        "title": policy_doc.title,
                        "chunk_id": chunk_idx,
                        "total_chunks": len(chunks),
                    },
                )
                langchain_docs.append(langchain_doc)

        self.vector_store.add_documents(langchain_docs)

    def semantic_search(self, query: str, k: int = 5) -> List[Tuple[Document, float]]:
        """
        벡터 유사도 기반 검색을 수행합니다.

        Args:
            query: 검색 쿼리
            k: 반환할 문서 개수

        Returns:
            (Document, distance) 튜플 리스트. distance는 코사인 거리 (낮을수록 유사).
        """
        if not self.vector_store:
            return []

        return self.vector_store.similarity_search_with_score(query, k=k)

    def keyword_search(self, query: str, k: int = 5) -> List[Tuple[Document, float]]:
        """
        pgroonga 전문 검색으로 키워드 매칭 문서를 반환합니다.

        pgroonga의 &@~ 연산자가 document 컬럼을 검색하고,
        pgroonga_score()가 TF-IDF 기반 관련도 점수를 반환합니다.

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
        k: int = 5,
    ) -> List[Document]:
        """
        Hybrid Search를 수행합니다.
        pgvector 벡터 유사도와 pgroonga 키워드 검색 결과를
        UUID 기준으로 점수를 합산하여 최종 순위를 결정합니다.

        Args:
            query: 검색 쿼리
            keywords: 검색할 키워드 리스트 (None이면 자동 추출)
            semantic_weight: 벡터 검색 가중치 (기본 0.7)
            k: 반환할 문서 개수

        Returns:
            검색된 Document 리스트 (점수순 정렬)
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

        # 4. 상위 k개 반환
        sorted_results = sorted(
            combined.values(), key=lambda x: x["score"], reverse=True
        )
        return [item["doc"] for item in sorted_results[:k]]

    def _merge_scores(
        self,
        semantic_results: List[Tuple[Document, float]],
        keyword_results: List[Tuple[Document, float]],
        semantic_weight: float,
    ) -> Dict[str, dict]:
        """
        벡터 검색과 키워드 검색 결과를 UUID 기준으로 합산합니다.

        점수 정규화:
        - pgvector: 코사인 거리 (0~2, 낮을수록 유사) → 1 - (dist/max_dist)로 변환
        - pgroonga: relevance score (높을수록 관련) → score/max_score로 정규화
        """
        keyword_weight = 1.0 - semantic_weight
        combined: Dict[str, dict] = {}

        # 벡터 결과 점수 정규화
        if semantic_results:
            max_dist = max(dist for _, dist in semantic_results) or 1.0
            for doc, dist in semantic_results:
                doc_id = self._get_doc_id(doc)
                norm_score = semantic_weight * (1.0 - dist / max_dist) if max_dist > 0 else 0.0
                combined[doc_id] = {"doc": doc, "score": norm_score}

        # 키워드 결과 점수 정규화 + 합산
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
        """
        Document의 고유 ID를 반환합니다.
        pgroonga 결과에는 uuid가 있고, pgvector 결과에는 metadata 기반 ID를 사용합니다.
        """
        if "uuid" in doc.metadata:
            return doc.metadata["uuid"]
        source = doc.metadata.get("source", "")
        chunk_id = doc.metadata.get("chunk_id", 0)
        return f"{source}_{chunk_id}"

    def _build_pgroonga_query(self, query: str) -> str:
        """
        원본 쿼리에서 도메인 키워드를 추출하여 pgroonga OR 쿼리로 확장합니다.

        도메인 키워드 목록의 역할:
        - AS-IS: Python `if keyword in content` 매칭용
        - TO-BE: 쿼리 확장(Query Expansion) — 사용자 쿼리에서 도메인 용어를 감지하면
                  관련 용어를 pgroonga 쿼리에 추가하여 검색 범위 확대

        Args:
            query: 원본 검색 쿼리

        Returns:
            pgroonga &@~ 연산자용 쿼리 문자열
        """
        keywords = []

        important_terms = [
            "LTV", "DTI", "DSR", "규제지역", "투기과열지구", "조정대상지역",
            "대출", "주담대", "전세대출", "신용대출", "중도금대출",
            "주택", "아파트", "분양", "청약", "전매제한",
            "취득세", "양도세", "재산세", "종부세",
            "수도권", "지방", "서울", "경기",
            "금리", "한도", "만기", "상환",
        ]

        query_upper = query.upper()
        for term in important_terms:
            if term.upper() in query_upper:
                keywords.append(term)

        # 숫자 패턴 추출 (날짜, 비율, 금액 등)
        numbers = re.findall(r"\d+(?:\.\d+)?[%년월일억원]?", query)
        keywords.extend(numbers)

        # 원본 쿼리 + 도메인 키워드를 OR로 결합
        all_terms = [query] + keywords
        return " OR ".join(all_terms)

    def as_retriever(self, search_kwargs: Optional[Dict] = None):
        """
        LangChain Retriever 인터페이스를 제공합니다.

        Args:
            search_kwargs: 검색 옵션 딕셔너리

        Returns:
            LangChain Retriever 객체
        """
        if search_kwargs is None:
            search_kwargs = {"k": 5}

        return self.vector_store.as_retriever(search_kwargs=search_kwargs)
