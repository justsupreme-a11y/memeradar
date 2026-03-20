"""
인스티즈 크롤러 v3
- instiz.net/hot.htm — HOT 인기글
- 중복 방지: URL 기반 해시
- 공지/이벤트 제외
- 조회수 필터링
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
    {"url": f"{BASE_URL}/hot.htm",        "name": "HOT 인기글"},
    {"url": f"{BASE_URL}/hot.htm?type=2", "name": "연예 인기글"},
    {"url": f"{BASE_URL}/hot.htm?type=1", "name": "이슈 인기글"},
]

SKIP_KEYWORDS = [
    "공지", "notice", "안내", "이벤트", "광고", "운영",
    "신고", "규정", "공고", "모집", "투표", "[공지]", "[안내]",
]

MIN_VIEWS = 500


def is_skip(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in SKIP_KEYWORDS)


def normalize_url(href: str) -> str:
    """URL 정규화 — 중복 방지용"""
    if href.startswith("http"):
        return href.split("?")[0]  # 쿼리스트링 제거
    return (BASE_URL + href).split("?")[0]


def fetch_board(url: str, name: str) -> list[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        posts = []
        seen  = set()

        # 인스티즈 HOT 페이지 셀렉터
        for a in soup.select("a[href*='/pt/']"):
            title = a.text.strip()
            href  = a.get("href", "")

            if not title or not href:
                continue
            if len(title) < 3:
                continue
            if is_skip(title):
                continue

            norm = normalize_url(href)
            if norm in seen:
                continue
            seen.add(norm)

            url_full = BASE_URL + href if href.startswith("/") else href

            # 부모 행에서 조회수 찾기
            parent   = a.find_parent("tr") or a.find_parent("li")
            view_count = 0
            if parent:
                view_el = parent.select_one(".listview, .view_count, .count")
                if view_el:
                    try:
                        view_count = int(view_el.text.strip().replace(",", ""))
                    except Exception:
                        pass

            if view_count > 0 and view_count < MIN_VIEWS:
                continue

            posts.append({
                "title":      title,
                "url":        url_full,
                "view_count": view_count,
            })

        return posts

    except Exception as e:
        log.warning(f"인스티즈 {name} 실패: {e}")
        return []


def run():
    total_new  = 0
    global_seen = set()  # 보드 간 중복 방지

    for board in BOARDS:
        log.info(f"수집: {board['name']}")
        posts = fetch_board(board["url"], board["name"])

        # 보드 간 중복 제거
        unique = []
        for p in posts:
            norm = normalize_url(p["url"])
            if norm not in global_seen:
                global_seen.add(norm)
                unique.append(p)

        log.info(f"  → {len(unique)}건 (중복 제거 후)")

        for post in unique:
            category = classify_category(post["title"])
            saved = save_meme(
                title=post["title"],
                url=post["url"],
                source="instiz",
                platform="domestic",
                view_count=post["view_count"],
                category=category,
                extra={"board": board["name"]},
            )
            if saved:
                total_new += 1

        time.sleep(random.uniform(2.0, 4.0))

    log.info(f"인스티즈 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
