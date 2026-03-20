"""
네이트판 크롤러
- pann.nate.com/talk/ranking — 실시간 인기글
"""

import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from utils.db import save_meme
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [pannate] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://pann.nate.com/",
}

BASE_URL = "https://pann.nate.com"

BOARDS = [
    {"url": f"{BASE_URL}/talk/ranking",         "name": "실시간 인기"},
    {"url": f"{BASE_URL}/talk/ranking?type=d",  "name": "일간 인기"},
]


def fetch_board(url: str, name: str) -> list[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        posts = []
        seen  = set()

        for item in soup.select(".post-item, .ranking-list li, li.item"):
            title_el = item.select_one("a.title, .title a, strong a, h4 a")
            if not title_el:
                continue

            title = title_el.text.strip()
            href  = title_el.get("href", "")
            if not title or not href or href in seen:
                continue

            seen.add(href)
            url_full = BASE_URL + href if href.startswith("/") else href

            vote_el   = item.select_one(".num-recomm, .vote, .like")
            view_el   = item.select_one(".num-view, .view")
            view_count = 0
            like_count = 0

            if view_el:
                try:
                    view_count = int(view_el.text.strip().replace(",", ""))
                except Exception:
                    pass
            if vote_el:
                try:
                    like_count = int(vote_el.text.strip().replace(",", ""))
                except Exception:
                    pass

            posts.append({
                "title":      title,
                "url":        url_full,
                "view_count": view_count,
                "like_count": like_count,
            })

        return posts

    except Exception as e:
        log.warning(f"네이트판 {name} 실패: {e}")
        return []


def run():
    total_new = 0

    for board in BOARDS:
        log.info(f"수집: 네이트판 {board['name']}")
        posts = fetch_board(board["url"], board["name"])
        log.info(f"  → {len(posts)}건")

        for post in posts:
            category = classify_category(post["title"])
            saved = save_meme(
                title=post["title"],
                url=post["url"],
                source="pannate",
                platform="domestic",
                view_count=post["view_count"],
                like_count=post["like_count"],
                category=category,
                extra={"board": board["name"]},
            )
            if saved:
                total_new += 1

        time.sleep(random.uniform(2.0, 3.0))

    log.info(f"네이트판 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
