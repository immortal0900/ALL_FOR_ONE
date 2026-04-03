"""
국가 정책 뉴스 Retriever
pgvector 기반 Hybrid Search(벡터 0.7 + 키워드 0.3)를 구현합니다.

반환 형태: List[str] (각 원소가 "날짜: ...\n제목: ...\n링크: ..." 포맷)
이 포맷은 하류 netional_news_to_drive()의 정규식 파싱과 일치해야 합니다.
"""

import re
from typing import List, Optional

from tools.rag.vector_store import get_pgvector_store
from tools.rag.db_collection_name import NATIONAL_POLICY_KEY
from tools.rag.document_loader.csv_loader import load_csv_loader
from utils.util import get_project_root


class NationalPolicyRetriever:
    """
    국가 정책 뉴스 검색 시스템
    의미 기반 검색(벡터 유사도)과 키워드 기반 재랭킹을 결합한 Hybrid Search를 수행합니다.

    PolicyPDFRetriever와 달리 별도 in-memory 캐시 없이,
    pgvector에서 가져온 후보 문서를 대상으로 키워드 점수를 계산합니다.
    (데이터가 약 350건으로 적어 k*2개 후보 내에서 재랭킹이 충분)
    """

    def __init__(self):
        """pgvector 스토어를 초기화합니다."""
        self.vector_store = get_pgvector_store(NATIONAL_POLICY_KEY)

    def semantic_search(self, query: str, k: int = 15) -> List[str]:
        """
        벡터 유사도 기반 검색을 수행합니다.

        Args:
            query: 검색 쿼리
            k: 반환할 문서 개수

        Returns:
            page_content 문자열 리스트
        """
        docs = self.vector_store.similarity_search(query, k=k)
        return [doc.page_content for doc in docs]

    def hybrid_search(
        self,
        query: str,
        keywords: Optional[List[str]] = None,
        semantic_weight: float = 0.7,
        k: int = 15,
    ) -> List[str]:
        """
        Hybrid Search를 수행합니다.
        벡터 유사도 점수(semantic_weight)와 키워드 빈도 점수(1-semantic_weight)를
        결합하여 최종 순위를 결정합니다.

        Args:
            query: 검색 쿼리
            keywords: 검색할 키워드 리스트 (None이면 자동 추출)
            semantic_weight: 의미 검색 가중치 (기본 0.7)
            k: 반환할 문서 개수

        Returns:
            page_content 문자열 리스트 (점수순 정렬)
        """
        # 벡터 검색으로 후보 k*2개 확보
        candidates = self.vector_store.similarity_search(query, k=k * 2)

        if not candidates:
            return []

        # 키워드 자동 추출
        if keywords is None:
            keywords = self._extract_keywords(query)

        keyword_weight = 1.0 - semantic_weight

        # 각 후보에 점수 부여: 벡터 순위 점수 + 키워드 매칭 점수
        scored = []
        candidate_count = len(candidates)

        for rank, doc in enumerate(candidates):
            # 벡터 순위 점수: 상위일수록 높은 점수 (1.0 -> 0.0)
            semantic_score = semantic_weight * (
                (candidate_count - rank) / candidate_count
            )

            # 키워드 매칭 점수: 매칭된 키워드 비율
            keyword_score = 0.0
            if keywords:
                content_lower = doc.page_content.lower()
                matched = sum(
                    1 for kw in keywords if kw.lower() in content_lower
                )
                keyword_score = keyword_weight * (matched / len(keywords))

            scored.append((doc.page_content, semantic_score + keyword_score))

        # 점수순 정렬
        scored.sort(key=lambda x: x[1], reverse=True)

        return [content for content, _ in scored[:k]]

    def _extract_keywords(self, query: str) -> List[str]:
        """
        쿼리에서 국가 정책 뉴스 도메인 키워드를 추출합니다.

        PolicyPDFRetriever._extract_keywords()와 유사하지만,
        정책 뉴스 도메인에 맞는 키워드 목록을 사용합니다.
        (PDF 정책 문서는 LTV/DTI/DSR 등 대출 규제 수치가 핵심이지만,
         뉴스는 정책 방향성, 공급/규제/시장 키워드가 더 중요)

        Args:
            query: 검색 쿼리

        Returns:
            추출된 키워드 리스트
        """
        keywords = []

        # 국가 정책 뉴스 도메인 키워드
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
        numbers_pattern = r"\d+(?:\.\d+)?[%년월일억원만호세대]?"
        numbers = re.findall(numbers_pattern, query)
        keywords.extend(numbers)

        return keywords


def national_policy_retrieve(
    query: Optional[str] = None, k: int = 15
) -> List[str]:
    """
    국가 정책 뉴스를 검색합니다.

    query가 주어지면 pgvector Hybrid Search로 관련 뉴스를 선별하고,
    query가 None이면 기존 동작(CSV 전량 로드)으로 fallback합니다.

    Fallback이 필요한 이유:
    - 인덱싱이 아직 실행되지 않은 환경에서도 시스템이 동작해야 함
    - policy_agent의 start_input이 비어있는 경우 대비

    Args:
        query: 검색 쿼리 (None이면 CSV 전량 로드)
        k: 반환할 문서 개수 (query 사용 시에만 적용)

    Returns:
        "날짜: ...\n제목: ...\n링크: ..." 포맷의 문자열 리스트
    """
    if query is None:
        # Fallback: CSV 파일 전량 로드 (기존 동작)
        path = (
            get_project_root() / "src" / "data" / "policy_factors"
            / "국토교통부_부동산정책(2024~2025) - 최종.csv"
        )
        loader = load_csv_loader(
            path, encoding="utf-8", autodetect_encoding=True
        )
        docs = loader.load()
        return [doc.page_content for doc in docs]

    retriever = NationalPolicyRetriever()
    return retriever.hybrid_search(query, k=k)
