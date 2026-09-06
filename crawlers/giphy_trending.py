"""
Giphy 트렌딩 크롤러 v1
- 공식 Giphy API 사용 — 베타 키는 가입 즉시 발급, 승인 절차 없음
- 무료 티어: 시간당 100회 호출 (2시간 주기 크론에서 1회만 호출하므로 여유 충분)
- Tenor는 2026-06-30부로 API 완전 종료되어 후보에서 제외함
"""

import os
import logging

import requests
from utils.db import save_meme
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [giphy] %(message)s")
log = logging.getLogger(__name__)

GIPHY_API_KEY = os.environ.get("GIPHY_API_KEY", "")
TRENDING_URL  = "https://api.giphy.com/v1/gifs/trending"

LIMIT  = 25
RATING = "pg-13"


def humanize_slug(slug: str) -> str:
    # "excited-yes-woo-12345" 같은 slug에서 끝의 id 조각을 떼고 사람이 읽을 문구로 변환
    parts = slug.split("-")
    if parts and parts[-1].isalnum() and any(c.isdigit() for c in parts[-1]):
        parts = parts[:-1]
    return " ".join(parts).strip()



def fetch_trending() -> list[dict]:
    if not GIPHY_API_KEY:
        log.warning("GIPHY_API_KEY 미설정 — 스킵")
        return []

    try:
        resp = requests.get(
            TRENDING_URL,
            params={"api_key": GIPHY_API_KEY, "limit": LIMIT, "rating": RATING},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])

        items = []
        for gif in data:
            title = (gif.get("title") or "").strip()
            slug  = gif.get("slug") or ""
            if not title:
                title = humanize_slug(slug)
            if not title or len(title) < 2:
                continue

            images = gif.get("images", {})
            image_url = (
                images.get("downsized_medium", {}).get("url")
                or images.get("original", {}).get("url")
                or ""
            )

            items.append({
                "title":     title,
                "url":       gif.get("url", ""),
                "image_url": image_url,
            })

        return items

    except Exception as e:
        log.warning(f"Giphy 트렌딩 실패: {e}")
        return []

def run():
    total_new = 0

    log.info("수집: Giphy 트렌딩")
    items = fetch_trending()
    log.info(f"  → {len(items)}건")

    for item in items:
        category = classify_category(item["title"])
        saved = save_meme(
            title=item["title"],
            url=item["url"],
            source="giphy",
            platform="global",
            image_url=item["image_url"],
            category=category,
            extra={"page": "trending"},
        )
        if saved:
            total_new += 1

    log.info(f"Giphy 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
