"""
더쿠 크롤러 v2
- 공지/이벤트/광고 제외
- 조회수 + 댓글수 기준 필터링
- HOT 게시판만 수집
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
    {"url": f"{BASE_URL}/hot", "name": "HOT"},
    # hot2 제거 — URL 폐지됨, HOT 단독으로 충분
]

# 제목에 이게 포함되면 스킵
SKIP_KEYWORDS = [
    "공지", "notice", "안내", "이벤트", "event", "광고",
    "운영", "신고", "규정", "공고", "모집", "투표",
]

MIN_VIEWS    = 5000   # 조회수 최소
MIN_COMMENTS = 10     # 댓글수 최소


def is_notice(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in SKIP_KEYWORDS)


def fetch_board(url: str, name: str) -> list[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        posts = []
        seen  = set()

        # HOT과 스퀘어 둘 다 같은 table.bd_lst 구조 사용
        for row in soup.select("table.bd_lst tr"):
            row_class = " ".join(row.get("class", []))
            if "notice" in row_class or "gong" in row_class:
                continue

            title_el = row.select_one("td.title a")
            if not title_el:
                continue

            title = title_el.text.strip()
            href  = title_el.get("href", "")

            if not title or not href or href in seen:
                continue
            if len(title) < 2:
                continue
            if is_notice(title):
                continue

            seen.add(href)
            url_full = BASE_URL + href if href.startswith("/") else href

            # 조회수
            view_el = row.select_one("td.m_no")
            view_count = 0
            if view_el:
                try:
                    view_count = int(view_el.text.strip().replace(",", ""))
                except Exception:
                    pass

            # 댓글수
            comment_el = row.select_one("td.reply_num, .reply")
            comment_count = 0
            if comment_el:
                try:
                    comment_count = int(comment_el.text.strip().replace(",", "").strip("[]"))
                except Exception:
                    pass

            # 조회수/댓글 필터
            if view_count < MIN_VIEWS and comment_count < MIN_COMMENTS:
                continue

            posts.append({
                "title":         title,
                "url":           url_full,
                "view_count":    view_count,
                "comment_count": comment_count,
            })

        # 스퀘어는 구조가 다를 경우 대비 — article 형태도 시도
        if not posts:
            for el in soup.select("li.item, .list_item, article"):
                title_el = el.select_one("a.title, .subject a, h3 a, h4 a")
                if not title_el:
                    continue
                title = title_el.text.strip()
                href  = title_el.get("href", "")
                if not title or not href or href in seen or len(title) < 2:
                    continue
                if is_notice(title):
                    continue
                seen.add(href)
                url_full = BASE_URL + href if href.startswith("/") else href
                posts.append({
                    "title":         title,
                    "url":           url_full,
                    "view_count":    0,
                    "comment_count": 0,
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
        log.info(f"  → {len(posts)}건 (필터 후)")

        for post in posts:
            category = classify_category(post["title"])
            saved = save_meme(
                title=post["title"],
                url=post["url"],
                source="theqoo",
                platform="domestic",
                view_count=post["view_count"],
                comment_count=post["comment_count"],
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
