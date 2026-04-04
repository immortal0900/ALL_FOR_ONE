"""
국가 정책 뉴스 CSV 공통 로더

pandas로 CSV를 읽고 제목 정제까지 한 단계로 처리합니다.
인덱서(national_policy_indexer.py)와 retriever fallback 모두 이 함수를 사용하여
로드/정제 로직의 불일치를 방지합니다.

page_content 포맷은 하류 netional_news_to_drive()의 정규식 파싱과 일치합니다:
    날짜: {date}
    제목: {title}
    링크: {link}
"""

import re
from typing import List

import pandas as pd
from langchain_core.documents import Document
from utils.util import get_project_root

CSV_FILE_PATH = (
    get_project_root() / "src" / "data" / "policy_factors"
    / "국토교통부_부동산정책(2024~2025) - 최종.csv"
)

# CSV 제목 컬럼의 보일러플레이트 패턴
# 원본: "{제목}{제목반복} 관련 보도자료 내용입니다. 자세한 내용은 첨부파일을...{날짜}{부처명}"
_BOILERPLATE_PATTERN = re.compile(
    r"관련 보도자료 내용입니다.*$", re.DOTALL
)

# 제목이 연속으로 2번 반복되는 패턴 제거
# 예: "서울 3곳 도심 복합지구 지정서울 3곳 도심 복합지구 지정" -> "서울 3곳 도심 복합지구 지정"
_DUPLICATE_TITLE_PATTERN = re.compile(r"^(.{10,}?)\1")


def _clean_title(raw_title: str) -> str:
    """
    CSV 제목 컬럼에서 순수 제목만 추출합니다.

    원본 형태: "{제목}{제목반복} 관련 보도자료 내용입니다...{날짜}{부처명}"
    -> 보일러플레이트 제거 -> 중복 제목 제거 -> 순수 제목 반환

    이 함수가 없으면:
    - 임베딩에 보일러플레이트 노이즈가 포함되어 벡터 검색 정확도 하락
    - pgroonga 키워드 검색에서 "보도자료", "첨부파일" 같은 무의미한 토큰이 매칭됨
    """
    cleaned = _BOILERPLATE_PATTERN.sub("", raw_title).strip()

    dup_match = _DUPLICATE_TITLE_PATTERN.match(cleaned)
    if dup_match:
        cleaned = dup_match.group(1).strip()

    return cleaned if cleaned else raw_title.strip()


def load_national_policy_documents() -> List[Document]:
    """
    국가 정책 CSV를 pandas로 읽고 정제된 Document 리스트를 반환합니다.

    인덱서와 retriever fallback 모두 이 함수를 사용하여
    동일한 page_content 포맷을 보장합니다.

    Returns:
        정제된 Document 리스트 (page_content: "날짜: ...\n제목: ...\n링크: ..." 포맷)
    """
    df = pd.read_csv(CSV_FILE_PATH, encoding="utf-8")
    docs = []

    for _, row in df.iterrows():
        date = str(row["날짜"]).strip()
        year_raw = str(row["연도"]).strip()
        raw_title = str(row["제목"])
        link = str(row["링크"]).strip()

        if not raw_title or not date:
            continue

        title = _clean_title(raw_title)

        # netional_news_to_drive()가 파싱하는 정확한 포맷:
        #   r"날짜:\s*([0-9\-]+)"
        #   r"제목:\s*(.*?)\n링크:" (re.DOTALL)
        #   r"링크:\s*(https?://[^\s]+)"
        page_content = f"날짜: {date}\n제목: {title}\n링크: {link}"

        metadata = {
            "source": "국토교통부_부동산정책",
            "date": date,
            "year": int(year_raw) if year_raw.isdigit() else 0,
            "link": link,
        }

        docs.append(Document(page_content=page_content, metadata=metadata))

    return docs
