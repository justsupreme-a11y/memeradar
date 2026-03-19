"""
Know Your Meme 크롤러 v2
- URL 수정: /newsfeed/trending 으로 변경
- Confirmed 밈만 수집
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
    "Accept-Language": "en-US,en;q=0.9",
}

BASE_URL = "https://knowyourmeme.com"

PAGES = [
    {"url": f"{BASE_URL}/newsfeed/trending", "label": "트렌딩"},
    {"url": f"{BASE_URL}/memes",             "label": "최신"},
    {"url": f"{BASE_URL}/memes?sort=latest-additions", "label": "신규"},
]


def fetch_page(url: str) -> list[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        memes = []

        # 뉴스피드 트렌딩 파싱
        for item in soup.select("article, .entry, .meme-entry, h2 a, .newsfeed-entry"):
            title_el  = item.select_one("h2 a, h3 a, .entry-title a, a.title")
            img_el    = item.select_one("img")

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
                if image_url.startswith("//"):
                    image_url = "https:" + image_url

            memes.append({
                "title":     title,
                "url":       href,
                "image_url": image_url,
            })

        # 중복 제거
        seen = set()
        unique = []
        for m in memes:
            if m["url"] not in seen:
                seen.add(m["url"])
                unique.append(m)

        return unique
    except Exception as e:
        log.warning(f"KYM {url} 실패: {e}")
        return []


def run():
    total_new = 0

    for page_cfg in PAGES:
        log.info(f"수집: KYM {page_cfg['label']}")
        memes = fetch_page(page_cfg["url"])
        log.info(f"  → {len(memes)}건")

        for meme in memes:
            # /memes/ 경로만 저장 (뉴스/포럼 제외)
            if "/memes/" not in meme["url"] and "/newsfeed/" not in meme["url"]:
                continue

            category = classify_category(meme["title"])

            saved = save_meme(
                title=meme["title"],
                url=meme["url"],
                source="kym",
                platform="global",
                image_url=meme["image_url"],
                category=category,
                extra={"page": page_cfg["label"]},
            )
            if saved:
                total_new += 1

        time.sleep(random.uniform(2.0, 4.0))

    log.info(f"KYM 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
