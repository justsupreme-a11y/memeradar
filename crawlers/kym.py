"""
Know Your Meme 크롤러 v3
- 트렌딩 URL: knowyourmeme.com/newsfeed/trending (확인됨)
- 방식: requests + BeautifulSoup
"""

import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from utils.db import save_meme
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [kym] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://knowyourmeme.com/",
}

BASE_URL = "https://knowyourmeme.com"

PAGES = [
    {"url": f"{BASE_URL}/newsfeed/trending", "label": "트렌딩"},
    {"url": f"{BASE_URL}/memes/trending",    "label": "밈 트렌딩"},
    {"url": f"{BASE_URL}/memes",             "label": "최신 밈"},
]


def fetch_page(url: str, label: str) -> list[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        items = []
        seen  = set()

        # 다양한 셀렉터 시도
        selectors = [
            "h2 a[href*='/memes/']",
            "h1 a[href*='/memes/']",
            "a.entry-title[href*='/memes/']",
            ".entry h2 a",
            ".newsfeed h2 a",
            "article h2 a",
            "article h3 a",
            ".infinite-scroll-component a[href*='/memes/']",
        ]

        for sel in selectors:
            for el in soup.select(sel):
                title = el.text.strip()
                href  = el.get("href", "")
                if not title or not href or href in seen:
                    continue
                if len(title) < 2:
                    continue
                seen.add(href)

                if not href.startswith("http"):
                    href = BASE_URL + href

                img_el = el.find_previous("img") or el.find_next("img")
                image_url = ""
                if img_el:
                    image_url = img_el.get("src") or img_el.get("data-src") or ""
                    if image_url.startswith("//"):
                        image_url = "https:" + image_url

                items.append({
                    "title":     title,
                    "url":       href,
                    "image_url": image_url,
                })

        return items

    except Exception as e:
        log.warning(f"KYM {url} 실패: {e}")
        return []


def run():
    total_new = 0

    for page in PAGES:
        log.info(f"수집: KYM {page['label']}")
        items = fetch_page(page["url"], page["label"])
        log.info(f"  → {len(items)}건")

        for item in items:
            category = classify_category(item["title"])
            saved = save_meme(
                title=item["title"],
                url=item["url"],
                source="kym",
                platform="global",
                image_url=item["image_url"],
                category=category,
                extra={"page": page["label"]},
            )
            if saved:
                total_new += 1

        time.sleep(random.uniform(2.0, 4.0))

    log.info(f"KYM 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
