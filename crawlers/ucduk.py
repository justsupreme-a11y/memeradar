"""
웃긴대학 크롤러
- 대상: 베스트 게시판 (짤/밈 전문 커뮤니티)
- 방식: requests + BeautifulSoup
- 특징: 정적 HTML, 봇 차단 약함
"""

import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from utils.db import save_meme

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ucduk] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.ucduk.com/",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

BASE_URL  = "https://www.ucduk.com"
BEST_URL  = f"{BASE_URL}/best"


def fetch_best(pages: int = 3) -> list[dict]:
    posts = []

    for page in range(1, pages + 1):
        url = f"{BEST_URL}?page={page}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            log.warning(f"요청 실패 p{page}: {e}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        for item in soup.select("div.list_item, li.list-item, .best_item"):
            title_el = item.select_one("a.subject, .title a, a.tit")
            view_el  = item.select_one(".hit, .view_count, .count")
            like_el  = item.select_one(".recom, .like, .good")

            if not title_el:
                continue

            href = title_el.get("href", "")
            if href.startswith("/"):
                href = BASE_URL + href
            if not href.startswith("http"):
                continue

            # 이미지 URL 시도
            img_el    = item.select_one("img")
            image_url = img_el.get("src", "") if img_el else ""
            if image_url.startswith("//"):
                image_url = "https:" + image_url

            posts.append({
                "title":     title_el.text.strip(),
                "url":       href,
                "view":      _parse_num(view_el),
                "like":      _parse_num(like_el),
                "image_url": image_url,
            })

        time.sleep(random.uniform(1.5, 2.5))

    return posts


def _parse_num(el) -> int:
    if not el:
        return 0
    try:
        return int(el.text.strip().replace(",", "").replace("조회", "").strip())
    except ValueError:
        return 0


def run():
    log.info("수집: 웃긴대학 베스트")
    posts = fetch_best(pages=3)
    log.info(f"  → {len(posts)}건 발견")

    total_new = 0
    for post in posts:
        if post["view"] < 100:
            continue

        saved = save_meme(
            title=post["title"],
            url=post["url"],
            source="ucduk",
            platform="domestic",
            image_url=post.get("image_url", ""),
            view_count=post["view"],
            like_count=post["like"],
        )
        if saved:
            total_new += 1

    log.info(f"웃긴대학 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
