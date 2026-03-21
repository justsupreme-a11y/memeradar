"""
고구마팜 크롤러 v4
- 실제 URL: gogumafarm.kr
- 카테고리: /소비자-인사이트, /브랜딩 등 슬러그 기반
- WordPress 형태
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
    {"url": BASE_URL,                                    "name": "메인"},
    {"url": f"{BASE_URL}/?category=%EC%86%8C%EB%B9%84%EC%9E%90-%EC%9D%B8%EC%82%AC%EC%9D%B4%ED%8A%B8", "name": "소비자인사이트"},
    {"url": f"{BASE_URL}/?category=%EB%B8%8C%EB%9E%9C%EB%94%A9", "name": "브랜딩"},
]


def fetch_page(url: str, name: str) -> list[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        items = []
        seen  = set()

        # 고구마팜은 <article> 또는 카드 형태
        for el in soup.select("article a, .post a, h2 a, h3 a, .entry-title a, a[href*='gogumafarm.kr']"):
            title = el.text.strip()
            href  = el.get("href", "")
            if not title or not href or href in seen:
                continue
            if len(title) < 5:
                continue
            if href in (BASE_URL, BASE_URL + "/", "#"):
                continue
            if not href.startswith("http"):
                href = BASE_URL + href
            if "gogumafarm.kr" not in href:
                continue
            seen.add(href)

            img_el = el.find_previous("img") or el.find_next("img")
            image_url = ""
            if img_el:
                image_url = img_el.get("src") or img_el.get("data-src") or ""

            items.append({"title": title, "url": href, "image_url": image_url})

        return items[:20]
    except Exception as e:
        log.warning(f"고구마팜 {name} 실패: {e}")
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
                title=item["title"], url=item["url"],
                source="gogumafarm", platform="domestic",
                image_url=item["image_url"], category=category,
                extra={"section": page["name"]},
            )
            if saved:
                total_new += 1
        time.sleep(random.uniform(2.0, 3.0))

    log.info(f"고구마팜 완료 — 신규 {total_new}건")
    return total_new

if __name__ == "__main__":
    run()
