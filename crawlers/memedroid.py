"""
Memedroid 크롤러
- 대상: memedroid.com 트렌딩 밈
- 커뮤니티 투표 기반 — 진짜 밈만 올라옴
- 방식: requests + BeautifulSoup
"""

import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from utils.db import save_meme
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [memedroid] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.memedroid.com/",
}

BASE_URL = "https://www.memedroid.com"

PAGES = [
    {"url": f"{BASE_URL}/memes/tag/trending", "label": "트렌딩"},
    {"url": f"{BASE_URL}/memes/tag/hot",      "label": "핫"},
]


def fetch_page(url: str) -> list[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        memes = []
        for item in soup.select("article.gallery-item, .meme-item, .item-card"):
            title_el  = item.select_one("a[title], .item-title a, h2 a, h3 a")
            img_el    = item.select_one("img")
            rating_el = item.select_one(".rating, .score, .votes")

            if not title_el:
                # title 없으면 img alt 사용
                if img_el and img_el.get("alt"):
                    title = img_el["alt"].strip()
                    href  = item.select_one("a")
                    href  = href.get("href", "") if href else ""
                else:
                    continue
            else:
                title = title_el.get("title") or title_el.text.strip()
                href  = title_el.get("href", "")

            if not title or not href:
                continue
            if not href.startswith("http"):
                href = BASE_URL + href

            image_url = ""
            if img_el:
                image_url = (
                    img_el.get("data-src") or
                    img_el.get("src") or ""
                )
                if image_url.startswith("//"):
                    image_url = "https:" + image_url

            rating = 0
            if rating_el:
                try:
                    rating = int(rating_el.text.strip().replace(",", "").replace("%", ""))
                except Exception:
                    pass

            memes.append({
                "title":     title,
                "url":       href,
                "image_url": image_url,
                "rating":    rating,
            })

        return memes
    except Exception as e:
        log.warning(f"Memedroid {url} 실패: {e}")
        return []


def run():
    total_new = 0

    for page in PAGES:
        log.info(f"수집: Memedroid {page['label']}")
        memes = fetch_page(page["url"])
        log.info(f"  → {len(memes)}건")

        for meme in memes:
            category = classify_category(meme["title"])
            saved = save_meme(
                title=meme["title"],
                url=meme["url"],
                source="memedroid",
                platform="global",
                image_url=meme["image_url"],
                view_count=meme["rating"],
                category=category,
                extra={"section": page["label"], "rating": meme["rating"]},
            )
            if saved:
                total_new += 1

        time.sleep(random.uniform(2.0, 4.0))

    log.info(f"Memedroid 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
