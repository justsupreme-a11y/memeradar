"""
대학내일 크롤러
- 대상: 트렌드/문화 기사 (MZ세대 트렌드 전문 미디어)
- 방식: requests + BeautifulSoup
"""

import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from utils.db import save_meme
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [univ_tomorrow] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://www.univtomorrow.co.kr/",
}

BASE_URL = "https://www.univtomorrow.co.kr"

SECTIONS = [
    {"url": f"{BASE_URL}/news/articleList.html?sc_section_code=S1N1", "name": "트렌드"},
    {"url": f"{BASE_URL}/news/articleList.html?sc_section_code=S1N4", "name": "문화"},
    {"url": f"{BASE_URL}/news/articleList.html?sc_section_code=S1N2", "name": "라이프"},
]


def fetch_section(url: str, name: str) -> list[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        articles = []
        for item in soup.select("li.item, .article-list li, .news-list li"):
            title_el = item.select_one("a.titles, .item-title a, h4 a, h3 a")
            img_el   = item.select_one("img")

            if not title_el:
                continue

            title = title_el.text.strip()
            href  = title_el.get("href", "")
            if not title or not href:
                continue

            if href.startswith("/"):
                href = BASE_URL + href

            image_url = ""
            if img_el:
                image_url = img_el.get("src") or img_el.get("data-src") or ""

            articles.append({
                "title":     title,
                "url":       href,
                "image_url": image_url,
                "section":   name,
            })

        return articles
    except Exception as e:
        log.warning(f"대학내일 {name} 실패: {e}")
        return []


def run():
    total_new = 0

    for section in SECTIONS:
        log.info(f"수집: 대학내일 {section['name']}")
        articles = fetch_section(section["url"], section["name"])
        log.info(f"  → {len(articles)}건")

        for article in articles:
            category = classify_category(article["title"])

            saved = save_meme(
                title=article["title"],
                url=article["url"],
                source="univ_tomorrow",
                platform="domestic",
                image_url=article["image_url"],
                category=category,
                extra={"section": article["section"]},
            )
            if saved:
                total_new += 1

        time.sleep(random.uniform(1.0, 2.0))

    log.info(f"대학내일 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
