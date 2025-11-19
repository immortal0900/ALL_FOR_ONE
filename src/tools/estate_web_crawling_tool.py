"""간단한 주택 정책 기사 크롤링 도구.

- 대상 사이트: https://housing-post.com (직접 HTML 구조를 확인해서 작성)
- 사용 목적: 외부 모듈에서 함수를 불러 기사 데이터를 바로 활용
"""

"""
from tools.estate_web_crowling import export_policy_factors

saved_path = export_policy_factors(max_page=3)
print(saved_path)

"""


import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from utils.util import get_project_root

BASE_URL = "https://housing-post.com"
LIST_PATH = "/List.aspx?CNO=11389"
MAX_PAGE = 3
DATA_ROOT = get_project_root() / "src" / "data" / "policy_factors"


def _collect_form_inputs(soup):
    inputs = {}
    for tag in soup.select("form input"):
        name = tag.get("name")
        if not name:
            continue
        input_type = (tag.get("type") or "").lower()
        if input_type in {"submit", "image", "button"}:
            continue
        inputs[name] = tag.get("value", "")
    return inputs


def _extract_event_target(href_value):
    marker = "__doPostBack('"
    if not href_value or marker not in href_value:
        return ""
    start = href_value.index(marker) + len(marker)
    end = href_value.find("'", start)
    return href_value[start:end] if end != -1 else ""


def _collect_links(soup):
    links = []
    for anchor in soup.select("a.alink"):
        href = anchor.get("href")
        if href and "View.aspx" in href:
            full_url = urljoin(BASE_URL, href)
            if full_url not in links:
                links.append(full_url)
    return links


def _fetch_article(url):
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    encoding = response.encoding or response.apparent_encoding or "utf-8"
    response.encoding = encoding
    return response.text


def _parse_article(article_url):
    soup = BeautifulSoup(_fetch_article(article_url), "html.parser")

    title_box = soup.select_one(".article-title")
    title = title_box.get_text(strip=True) if title_box else ""

    meta_box = soup.select_one(".article-meta")
    date_text = ""
    if meta_box:
        spans = meta_box.find_all("span")
        if len(spans) > 1:
            raw_date = spans[1].get_text(" ", strip=True)
            date_text = raw_date.replace("승인", "", 1).strip()

    body_box = soup.select_one(".article-body")
    content = body_box.get_text("\n", strip=True) if body_box else ""

    return {
        # "url": article_url,
        "title": title,
        "date": date_text,
        "content": content,
    }


def _collect_articles(max_page: int = MAX_PAGE):
    session = requests.Session()
    listing_url = urljoin(BASE_URL, LIST_PATH)

    response = session.get(listing_url, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    form_inputs = _collect_form_inputs(soup)

    links = _collect_links(soup)
    current_page = 1

    while current_page < max_page:
        target_page = current_page + 1
        target = ""

        for anchor in soup.select("a.paging"):
            if anchor.get_text(strip=True) == str(target_page):
                target = _extract_event_target(anchor.get("href"))
                break

        if not target:
            break

        payload = form_inputs.copy()
        payload["__EVENTTARGET"] = target
        payload["__EVENTARGUMENT"] = ""

        response = session.post(listing_url, data=payload, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        form_inputs = _collect_form_inputs(soup)

        for link in _collect_links(soup):
            if link not in links:
                links.append(link)

        current_page = target_page

    articles = []
    for link in links:
        articles.append(_parse_article(link))

    return articles


from utils.llm import LLMProfile


def collect_articles_result():
    articles = _collect_articles()

    # 빈 리스트 체크
    if not articles:
        print("경고: 수집된 기사가 없습니다.")
        return []

    llm = LLMProfile.dev_llm().invoke(
        f"""
        당신은 부동산 정책 뉴스를 JSON 목록으로 만든 것 중에 각 원소마다 데이터 형식은 똑같이 유지한채
        각 뉴스의 content 라고 적힌 키값의 내용을 변경해서 출력하는 역할을 맡고 있습니다.

        [목표]
        JSON 목록을 유지한채 각 뉴스안의 content의 값을 수정하는 것입니다.
        - 정책만 이야기하도록 수정해주세요.
        - 불필요한 미래전망 예상이나 주관적인 내용은 제거해주시고 정책 내용만 남겨주세요

        [추가 지침]
        - title 키 데이터에 이상한 글 이있으면 title도 같이 수정 해주세요.
            - 예시: '\u200b\u200b\' 와 같이 인코딩 안된것 같은 부분

        [강력 지침]
        - *JSON형식으로만 답변*하세요
        - 절대 JSON 파일 외에 다른 말을 하지마세요
        - 인삿말 및 마지막말 같은걸 절대 하지마세요
        - 응답은 반드시 유효한 JSON 배열로 시작해야 합니다 (예: [{{...}}])

        [JSON 파일]
        {articles}
        """
    )

    # LLM 응답 검증
    content = llm.content.strip()
    if not content:
        print("경고: LLM이 빈 응답을 반환했습니다. 원본 데이터를 반환합니다.")
        return articles

    # JSON 마크다운 코드 블록 제거 (```json ... ``` 형식)
    if content.startswith("```"):
        # ```json 또는 ``` 제거
        lines = content.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    # JSON 파싱 시도
    try:
        result = json.loads(content)
        return result
    except json.JSONDecodeError as e:
        print(f"JSON 파싱 에러: {e}")
        print(f"LLM 응답 (처음 500자): {content[:500]}")
        print("원본 데이터를 반환합니다.")
        return articles


# def build_output_path(base_dir=DATA_ROOT):
#     base_dir = Path(base_dir)
#     base_dir.mkdir(parents=True, exist_ok=True)
#     today = datetime.now().strftime("%Y%m%d")
#     return base_dir / f"policy_factors_{today}.json"


# def save_articles(records, file_path):
#     with Path(file_path).open("w", encoding="utf-8") as file:
#         json.dump(records, file, ensure_ascii=False, indent=2)


# def export_policy_factors(max_page: int = MAX_PAGE, base_dir=DATA_ROOT):
#     articles = collect_articles(max_page=max_page)
#     output_path = build_output_path(base_dir=base_dir)
#     save_articles(articles, output_path)
#     return output_path
