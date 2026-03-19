"""
고구마팜 크롤러 v3
- 실제 구조: WordPress 블로그
- 메인 페이지에서 최신 글 파싱
"""

import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from utils.db import save_meme
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [goguma] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

BASE_URL = "https://gogumafarm.kr"

PAGES = [
    {"url": BASE_URL,                    "name": "메인"},
    {"url": f"{BASE_URL}/category/meme", "name": "밈"},
    {"url": f"{BASE_URL}/category/trend","name": "트렌드"},
]


def fetch_page(url: str, name: str) -> list[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        items = []
        seen  = set()

        # WordPress 표준 셀렉터들
        selectors = [
            "article .entry-title a",
            "article h2 a",
            "article h3 a",
            ".post-title a",
            "h2.wp-block-post-title a",
            ".wp-block-post-title a",
            "h2 a[href*='gogumafarm']",
            "h3 a[href*='gogumafarm']",
        ]

        for sel in selectors:
            for el in soup.select(sel):
                title = el.text.strip()
                href  = el.get("href", "")
                if not title or not href or href in seen:
                    continue
                if len(title) < 4:
                    continue
                if href == BASE_URL or href == BASE_URL + "/":
                    continue
                seen.add(href)

                img_el = el.find_previous("img") or el.find_next("img")
                image_url = ""
                if img_el:
                    image_url = img_el.get("src") or img_el.get("data-src") or ""

                items.append({
                    "title":     title,
                    "url":       href if href.startswith("http") else BASE_URL + href,
                    "image_url": image_url,
                })

        return items[:20]

    except Exception as e:
        log.warning(f"고구마팜 {url} 실패: {e}")
        return []


def run():
    total_new = 0

    for page in PAGES:
        log.info(f"수집: 고구마팜 {page['name']}")
        items = fetch_page(page["url"], page["name"])
        log.info(f"  → {len(items)}건")

        for item in items:
            category = classify_category(item["title"])
            saved = save_meme(
                title=item["title"],
                url=item["url"],
                source="gogumafarm",
                platform="domestic",
                image_url=item["image_url"],
                category=category,
                extra={"section": page["name"]},
            )
            if saved:
                total_new += 1

        time.sleep(random.uniform(2.0, 3.0))

    log.info(f"고구마팜 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
