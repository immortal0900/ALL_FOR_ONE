"""
국토교통부 통계누리 보도자료 검색 도구

이 모듈은 Perplexity API를 사용하여 국토교통부 통계누리 사이트에서
정책 관련 보도자료를 검색하는 LangChain tool을 제공합니다.
"""

import logging
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from perplexity import Perplexity
from dotenv import load_dotenv
import os

# Langfuse 수동 추적 (Graceful Degradation)
from utils.langfuse_tracker import tracker as _langfuse_tracker

load_dotenv()

logger = logging.getLogger(__name__)

class MolitSearchTool:
    """국토교통부 통계누리 검색 클래스"""

    def __init__(self):
        self.client = Perplexity()
        self.base_sites = [
            "www.molit.go.kr",  # 국토교통부
            "stat.molit.go.kr",  # 국토교통통계누리
            "www.molit.go.kr/USR/policyData",  # 정책자료실
        ]

    def search_policy_news(
        self,
        query: str,
        sites: Optional[List[str]] = None,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        국토부 사이트에서 정책 관련 보도자료 검색

        Args:
            query: 검색 키워드
            sites: 검색할 사이트 목록 (기본값: 국토부 관련 사이트)
            max_results: 최대 결과 수

        Returns:
            검색 결과 리스트 (제목, URL, 요약, 날짜 포함)
        """
        if sites is None:
            sites = self.base_sites

        # site: 연산자를 사용하여 특정 사이트만 검색
        site_filter = " OR ".join([f"site:{site}" for site in sites])
        full_query = f"{query} ({site_filter})"
        print(full_query)
    

        try:
            # Perplexity 검색 실행
            response = self.client.search.create(query=[full_query])
            
            results = []
            for result in response.results[:max_results]:
                results.append({
                    "title": result.title,
                    "url": result.url,
                    "snippet": result.snippet,
                    "date": result.date,
                    "last_updated": result.last_updated,
                })
                print(result)

            # Langfuse 수동 추적: 국토부 검색 기록
            langfuse_client = _langfuse_tracker.get_client()
            if langfuse_client is not None:
                try:
                    import json
                    output_data = json.dumps(results, ensure_ascii=False)
                    if len(output_data) > 2000:
                        output_data = output_data[:2000] + "...(truncated)"
                        
                    with langfuse_client.start_as_current_observation(
                        as_type="generation",
                        name="molit-search",
                        model="perplexity-search-api",
                        input=full_query[:500],
                    ) as span:
                        span.update(
                            output=output_data,
                            metadata={"result_count": len(results)},
                        )
                except Exception:
                    pass

            return results

        except Exception as e:
            print(f"검색 중 오류 발생: {e}")
            return []

    def format_results(self, results: List[Dict[str, Any]]) -> str:
        """
        검색 결과를 읽기 쉬운 형태로 포맷팅

        Args:
            results: 검색 결과 리스트

        Returns:
            포맷팅된 문자열
        """
        if not results:
            return "검색 결과가 없습니다."

        formatted = []
        for i, result in enumerate(results, 1):
            formatted.append(f"\n{'='*80}")
            formatted.append(f"[{i}] {result['title']}")
            formatted.append(f"URL: {result['url']}")
            # formatted.append(f"날짜: {result.get('date', 'N/A')}")
            formatted.append(f"날짜: {result.get('last_updated', 'N/A')}")
            formatted.append(f"\n요약:")
            formatted.append(result['snippet'][:300] + "..." if len(result['snippet']) > 300 else result['snippet'])

        formatted.append(f"\n{'='*80}\n")
        formatted.append(f"총 {len(results)}개의 결과")

        return "\n".join(formatted)


# LangChain tool로 래핑
@tool
def search_molit_policy(query: str) -> str:
    """
    국토교통부 통계누리에서 정책 관련 보도자료를 검색합니다.

    이 도구는 국토교통부 공식 사이트와 통계누리에서 정책, 보도자료,
    통계 데이터 등을 검색할 때 사용합니다.

    Args:
        query: 검색할 키워드 (예: "주택공급", "분양가상한제", "재건축")

    Returns:
        검색된 보도자료 목록 (제목, URL, 요약, 날짜 포함)

    Examples:
        >>> search_molit_policy("2025년 주택공급계획")
        >>> search_molit_policy("분양가상한제 정책")
    """
    searcher = MolitSearchTool()
    results = searcher.search_policy_news(query, max_results=5)
    return searcher.format_results(results)


@tool
def search_molit_statistics(query: str, year: Optional[str] = None) -> str:
    """
    국토교통통계누리에서 통계 자료를 검색합니다.

    이 도구는 주택, 건설, 부동산 등 국토교통 관련 통계 데이터를
    검색할 때 사용합니다.

    Args:
        query: 검색할 통계 주제 (예: "아파트 분양실적", "미분양 현황")
        year: 검색할 연도 (선택사항, 예: "2025")

    Returns:
        검색된 통계자료 목록

    Examples:
        >>> search_molit_statistics("아파트 분양실적", "2025")
        >>> search_molit_statistics("주택담보대출")
    """
    searcher = MolitSearchTool()

    # 연도가 지정된 경우 쿼리에 추가
    if year:
        query = f"{year}년 {query}"

    # 통계누리 사이트만 검색
    results = searcher.search_policy_news(
        query,
        sites=["https://www.molit.go.kr/USR/NEWS/m_71/lst.jsp?search_section=p_sec_2"],
        max_results=5
    )
    return searcher.format_results(results)


# 편의 함수
def get_molit_tools():
    """국토부 검색 도구 목록 반환"""
    return [search_molit_policy, search_molit_statistics]

