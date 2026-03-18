"""
루리웹 크롤러
- 대상: 베스트 게시판 (게임/밈/짤 문화, 20대 이용자 많음)
- 방식: requests + BeautifulSoup
"""

import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from utils.db import save_meme

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ruliweb] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer": "https://bbs.ruliweb.com/",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

BOARDS = [
    {"url": "https://bbs.ruliweb.com/best/humor",  "name": "유머 베스트"},
    {"url": "https://bbs.ruliweb.com/best/picture","name": "짤방 베스트"},
]


def fetch_board(url: str, pages: int = 3) -> list[dict]:
    posts = []

    for page in range(1, pages + 1):
        page_url = f"{url}?page={page}"
        try:
            resp = requests.get(page_url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            log.warning(f"요청 실패 {page_url}: {e}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        for row in soup.select("tr.table_body, tr.tr_best"):
            title_el   = row.select_one("a.deco")
            view_el    = row.select_one("td.hit")
            like_el    = row.select_one("td.recomd")

            if not title_el:
                continue

            href = title_el.get("href", "")
            if not href.startswith("http"):
                href = "https://bbs.ruliweb.com" + href

            posts.append({
                "title": title_el.text.strip(),
                "url":   href,
                "view":  _parse_num(view_el),
                "like":  _parse_num(like_el),
            })

        time.sleep(random.uniform(1.5, 3.0))

    return posts


def _parse_num(el) -> int:
    if not el:
        return 0
    try:
        return int(el.text.strip().replace(",", ""))
    except ValueError:
        return 0


def run():
    total_new = 0

    for board in BOARDS:
        log.info(f"수집: {board['name']}")
        posts = fetch_board(board["url"])
        log.info(f"  → {len(posts)}건 발견")

        for post in posts:
            if post["view"] < 200:
                continue

            saved = save_meme(
                title=post["title"],
                url=post["url"],
                source="ruliweb",
                platform="domestic",
                view_count=post["view"],
                like_count=post["like"],
                extra={"board": board["name"]},
            )
            if saved:
                total_new += 1

    log.info(f"루리웹 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
