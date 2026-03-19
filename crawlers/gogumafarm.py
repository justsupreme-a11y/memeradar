"""
고구마팜 크롤러
- 대상: gogumafarm.kr 밈 큐레이션 기사
- 마케터가 정리한 밈 + 브랜드 활용 포인트
- 방식: requests + BeautifulSoup
"""

import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from utils.db import save_meme
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [gogumafarm] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://gogumafarm.kr/",
}

BASE_URL = "https://gogumafarm.kr"

PAGES = [
    {"url": f"{BASE_URL}/meme",    "label": "밈"},
    {"url": f"{BASE_URL}/trend",   "label": "트렌드"},
    {"url": f"{BASE_URL}/marketing","label": "마케팅"},
]


def fetch_page(url: str) -> list[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        items = []
        for article in soup.select("article, .post-item, .card, .entry"):
            title_el = article.select_one("h2 a, h3 a, .title a, a.post-title")
            img_el   = article.select_one("img")

            if not title_el:
                continue

            title = title_el.text.strip()
            href  = title_el.get("href", "")
            if not title or not href:
                continue
            if not href.startswith("http"):
                href = BASE_URL + href

            image_url = ""
            if img_el:
                image_url = img_el.get("src") or img_el.get("data-src") or ""

            items.append({
                "title":     title,
                "url":       href,
                "image_url": image_url,
            })

        return items
    except Exception as e:
        log.warning(f"고구마팜 {url} 실패: {e}")
        return []


def run():
    total_new = 0

    for page in PAGES:
        log.info(f"수집: 고구마팜 {page['label']}")
        items = fetch_page(page["url"])
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
                extra={"section": page["label"]},
            )
            if saved:
                total_new += 1

        time.sleep(random.uniform(1.5, 3.0))

    log.info(f"고구마팜 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
