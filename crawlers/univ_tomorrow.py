"""
대학내일 크롤러 v2
- 실제 URL: univ20.com (매거진 사이트)
- 방식: requests + BeautifulSoup
"""

import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from utils.db import save_meme
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [univ20] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://www.univ20.com/",
}

BASE_URL = "https://www.univ20.com"

SECTIONS = [
    {"url": f"{BASE_URL}/category/trend", "name": "트렌드"},
    {"url": f"{BASE_URL}/category/culture", "name": "문화"},
    {"url": f"{BASE_URL}/category/life", "name": "라이프"},
    {"url": BASE_URL, "name": "메인"},
]


def fetch_section(url: str, name: str) -> list[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        articles = []
        # 다양한 셀렉터 시도
        selectors = [
            "article a", ".post-title a", "h2 a", "h3 a",
            ".entry-title a", ".article-title a", ".item-title a",
        ]

        seen = set()
        for sel in selectors:
            for el in soup.select(sel):
                title = el.text.strip()
                href  = el.get("href", "")
                if not title or not href or href in seen:
                    continue
                if len(title) < 5:
                    continue
                seen.add(href)

                img_el    = el.find_next("img")
                image_url = ""
                if img_el:
                    image_url = img_el.get("src") or img_el.get("data-src") or ""

                articles.append({
                    "title":     title,
                    "url":       href if href.startswith("http") else BASE_URL + href,
                    "image_url": image_url,
                })

        return articles[:20]
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
                extra={"section": section["name"]},
            )
            if saved:
                total_new += 1

        time.sleep(random.uniform(1.0, 2.0))

    log.info(f"대학내일 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
