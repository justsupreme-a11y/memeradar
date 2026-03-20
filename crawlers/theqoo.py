"""
더쿠 크롤러
- theqoo.net/hot — 핫 게시판
- 셀럽/아이돌 관련 밈 원산지
"""

import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from utils.db import save_meme
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [theqoo] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://theqoo.net/",
}

BASE_URL = "https://theqoo.net"

BOARDS = [
    {"url": f"{BASE_URL}/hot",     "name": "HOT"},
    {"url": f"{BASE_URL}/hot2",    "name": "HOT2"},
    {"url": f"{BASE_URL}/square",  "name": "스퀘어"},
]


def fetch_board(url: str, name: str) -> list[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        posts = []
        seen  = set()

        for row in soup.select("table.bd_lst tr, .bd_lst_wrap tr"):
            title_el = row.select_one("td.title a, .title a")
            if not title_el:
                continue

            title = title_el.text.strip()
            href  = title_el.get("href", "")
            if not title or not href or href in seen:
                continue
            if len(title) < 2:
                continue

            seen.add(href)
            url_full = BASE_URL + href if href.startswith("/") else href

            # 조회수
            view_el    = row.select_one("td.m_no, .m_no")
            view_count = 0
            if view_el:
                try:
                    view_count = int(view_el.text.strip().replace(",", ""))
                except Exception:
                    pass

            posts.append({
                "title":      title,
                "url":        url_full,
                "view_count": view_count,
            })

        return posts

    except Exception as e:
        log.warning(f"더쿠 {name} 실패: {e}")
        return []


def run():
    total_new = 0

    for board in BOARDS:
        log.info(f"수집: 더쿠 {board['name']}")
        posts = fetch_board(board["url"], board["name"])
        log.info(f"  → {len(posts)}건")

        for post in posts:
            category = classify_category(post["title"])
            saved = save_meme(
                title=post["title"],
                url=post["url"],
                source="theqoo",
                platform="domestic",
                view_count=post["view_count"],
                category=category,
                extra={"board": board["name"]},
            )
            if saved:
                total_new += 1

        time.sleep(random.uniform(2.0, 4.0))

    log.info(f"더쿠 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
