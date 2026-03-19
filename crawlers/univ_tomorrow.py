"""
대학내일 크롤러 v3
- 실제 URL 확인: univ20.com
- 트렌드/문화 기사 수집
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
    "Referer": "https://univ20.com/",
}

SITES = [
    {"url": "https://univ20.com",                "name": "대학내일"},
    {"url": "https://univ20.com/campus",         "name": "캠퍼스"},
    {"url": "https://univ20.com/trendy",         "name": "트렌디"},
]


def fetch_site(url: str, name: str) -> list[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        items = []
        seen  = set()

        selectors = [
            "article a", ".post a", ".article a",
            "h2 a", "h3 a", "h4 a",
            ".title a", ".headline a",
            "a.article-title", "a.post-title",
        ]

        for sel in selectors:
            for el in soup.select(sel):
                title = el.text.strip()
                href  = el.get("href", "")
                if not title or not href or href in seen:
                    continue
                if len(title) < 5:
                    continue
                if href in ("#", "/", url):
                    continue
                seen.add(href)

                if not href.startswith("http"):
                    href = "https://univ20.com" + href

                img_el = el.find_previous("img") or el.find_next("img")
                image_url = ""
                if img_el:
                    image_url = img_el.get("src") or img_el.get("data-src") or ""

                items.append({
                    "title":     title,
                    "url":       href,
                    "image_url": image_url,
                })

        return items[:20]

    except Exception as e:
        log.warning(f"대학내일 {name} 실패: {e}")
        return []


def run():
    total_new = 0

    for site in SITES:
        log.info(f"수집: {site['name']}")
        items = fetch_site(site["url"], site["name"])
        log.info(f"  → {len(items)}건")

        for item in items:
            category = classify_category(item["title"])
            saved = save_meme(
                title=item["title"],
                url=item["url"],
                source="univ_tomorrow",
                platform="domestic",
                image_url=item["image_url"],
                category=category,
                extra={"section": site["name"]},
            )
            if saved:
                total_new += 1

        time.sleep(random.uniform(1.5, 3.0))

    log.info(f"대학내일 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
