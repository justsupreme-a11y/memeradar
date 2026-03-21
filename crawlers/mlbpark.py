"""
MLB파크 크롤러
- mlbpark.donga.com/mp/b.php?b=bullpen — 자유게시판 (불펜)
- 연예/사회 이슈 커뮤니티 반응
"""

import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from utils.db import save_meme
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [mlbpark] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://mlbpark.donga.com/",
}

BASE_URL   = "https://mlbpark.donga.com"
BOARD_URL  = f"{BASE_URL}/mp/b.php"

BOARDS = [
    {"params": "?p=1&b=bullpen",  "name": "불펜 최신"},
    {"params": "?p=1&b=bullpen&sort=r", "name": "불펜 추천순"},
]

MIN_RECOMMEND = 5


def fetch_board(params: str, name: str) -> list[dict]:
    try:
        url  = BOARD_URL + params
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        posts = []
        seen  = set()

        for row in soup.select("tr.list, tr[class*='list'], .board-list tr"):
            title_el = row.select_one("td.tit a, td.title a, .subject a, a.title")
            if not title_el:
                continue

            title = title_el.text.strip()
            href  = title_el.get("href", "")
            if not title or not href or href in seen:
                continue
            if len(title) < 3:
                continue

            seen.add(href)
            url_full = BASE_URL + href if href.startswith("/") else href

            # 추천수
            rec_el = row.select_one("td.recom, .recommend, .rec")
            recommend = 0
            if rec_el:
                try:
                    recommend = int(rec_el.text.strip().replace(",", ""))
                except Exception:
                    pass

            # 추천순 정렬 시 최소 추천수 필터
            if "sort=r" in params and recommend < MIN_RECOMMEND:
                continue

            posts.append({
                "title":     title,
                "url":       url_full,
                "recommend": recommend,
            })

        return posts

    except Exception as e:
        log.warning(f"MLB파크 {name} 실패: {e}")
        return []


def run():
    total_new   = 0
    global_seen = set()

    for board in BOARDS:
        log.info(f"수집: MLB파크 {board['name']}")
        posts = fetch_board(board["params"], board["name"])

        unique = [p for p in posts if p["url"] not in global_seen]
        for p in unique:
            global_seen.add(p["url"])

        log.info(f"  → {len(unique)}건")

        for post in unique:
            category = classify_category(post["title"])
            saved = save_meme(
                title=post["title"],
                url=post["url"],
                source="mlbpark",
                platform="domestic",
                like_count=post["recommend"],
                category=category,
                extra={"board": board["name"], "recommend": post["recommend"]},
            )
            if saved:
                total_new += 1

        time.sleep(random.uniform(2.0, 3.0))

    log.info(f"MLB파크 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
