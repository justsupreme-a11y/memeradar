"""
인스티즈 크롤러
- 대상: 인기 게시판 (아이돌/셀럽 밈 원산지)
- 방식: requests + BeautifulSoup
"""

import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from utils.db import save_meme
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [instiz] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://www.instiz.net/",
}

BASE_URL = "https://www.instiz.net"

BOARDS = [
    {"path": "/pt",   "name": "인기 게시판"},
    {"path": "/name", "name": "연예인 이슈"},
]


def fetch_board(path: str) -> list[dict]:
    url = BASE_URL + path
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        posts = []
        for row in soup.select(".listbody tr, .list_wrap li, li.media_end_list_item"):
            title_el = row.select_one("a.listsubject, .list_title a, a.subject")
            if not title_el:
                continue

            title = title_el.text.strip()
            href  = title_el.get("href", "")
            if not title or not href:
                continue

            if href.startswith("/"):
                href = BASE_URL + href

            # 조회수/댓글 파싱
            view_el    = row.select_one(".listview, .view_count")
            comment_el = row.select_one(".listcomment, .comment_count")

            view_count    = _parse_num(view_el)
            comment_count = _parse_num(comment_el)

            posts.append({
                "title":         title,
                "url":           href,
                "view_count":    view_count,
                "comment_count": comment_count,
            })

        return posts
    except Exception as e:
        log.warning(f"인스티즈 {path} 실패: {e}")
        return []


def _parse_num(el) -> int:
    if not el:
        return 0
    try:
        return int(el.text.strip().replace(",", ""))
    except Exception:
        return 0


def run():
    total_new = 0

    for board in BOARDS:
        log.info(f"수집: 인스티즈 {board['name']}")
        posts = fetch_board(board["path"])
        log.info(f"  → {len(posts)}건")

        for post in posts:
            if post["view_count"] < 100:
                continue

            category = classify_category(post["title"])
            # 인스티즈는 셀럽 관련이 많으므로 기본값 celeb
            if category == "general":
                category = "celeb"

            saved = save_meme(
                title=post["title"],
                url=post["url"],
                source="instiz",
                platform="domestic",
                view_count=post["view_count"],
                comment_count=post["comment_count"],
                category=category,
                extra={"board": board["name"]},
            )
            if saved:
                total_new += 1

        time.sleep(random.uniform(1.5, 3.0))

    log.info(f"인스티즈 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
