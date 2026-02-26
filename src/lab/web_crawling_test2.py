import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://housing-post.com"
LIST_PATH = "/List.aspx?CNO=11389"
MAX_PAGE = 3
DATA_ROOT = Path("C:/RAG_COMMANDER/src/data/policy_factors")


def fetch_html(full_url):
    response = requests.get(full_url, timeout=20)
    response.raise_for_status()
    encoding = response.encoding or response.apparent_encoding or "utf-8"
    response.encoding = encoding
    return response.text

def collect_form_inputs(soup):
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


def extract_event_target(href_value):
    if not href_value:
        return ""
    marker = "__doPostBack('"
    if marker not in href_value:
        return ""
    start = href_value.index(marker) + len(marker)
    end = href_value.find("'", start)
    if end == -1:
        return ""
    return href_value[start:end]


def collect_links(soup):
    links = []
    for anchor in soup.select("a.alink"):
        href = anchor.get("href")
        if href and "View.aspx" in href:
            full_url = urljoin(BASE_URL, href)
            if full_url not in links:
                links.append(full_url)
    return links


def gather_article_links():
    collected = []
    session = requests.Session()

    first_url = urljoin(BASE_URL, LIST_PATH)
    response = session.get(first_url, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    form_inputs = collect_form_inputs(soup)
    collected.extend(collect_links(soup))

    current_page = 1
    while current_page < MAX_PAGE:
        next_page = current_page + 1
        target = ""
        for anchor in soup.select("a.paging"):
            if anchor.get_text(strip=True) == str(next_page):
                target = extract_event_target(anchor.get("href"))
                break
        if not target:
            break

        payload = form_inputs.copy()
        payload["__EVENTTARGET"] = target
        payload["__EVENTARGUMENT"] = ""

        response = session.post(first_url, data=payload, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        form_inputs = collect_form_inputs(soup)

        for link in collect_links(soup):
            if link not in collected:
                collected.append(link)

        current_page = next_page

    return collected


def parse_article(article_url):
    article_html = fetch_html(article_url)
    soup = BeautifulSoup(article_html, "html.parser")

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
        "url": article_url,
        "title": title,
        "date": date_text,
        "content": content,
    }

def save_as_json(records, file_path):
    with file_path.open("w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)


def main():
    today = datetime.now().strftime("%Y%m%d")
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    output_file = DATA_ROOT / f"policy_factors_{today}.json"

    article_links = gather_article_links()
    articles = []
    for link in article_links:
        article_data = parse_article(link)
        articles.append(article_data)

    save_as_json(articles, output_file)
    print(f"저장 완료: {output_file}")


if __name__ == "__main__":
    main()
