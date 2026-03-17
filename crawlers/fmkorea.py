"""
에펨코리아 크롤러
- 대상: 유머/짤방 게시판
- 방식: requests + BeautifulSoup
- 주기: 1~2시간 (GitHub Actions cron)
"""

import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from utils.db import save_meme

logging.basicConfig(level=logging.INFO, format="%(asctime)s [fmk] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.fmkorea.com/",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# 수집할 게시판 (경로: 이름)
BOARDS = {
    "humor": "유머",
    "best": "베스트",
    "funny_face": "개드립",
}

BASE_URL = "https://www.fmkorea.com"


def fetch_board(board_key: str, page: int = 1) -> list[dict]:
    """에펨코리아 게시판 한 페이지 파싱"""
    url = f"{BASE_URL}/{board_key}" if page == 1 else f"{BASE_URL}/{board_key}/{page}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.warning(f"요청 실패 {board_key} p{page}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    posts = []

    for item in soup.select("li.li_normal, ul.list_ul > li"):
        title_el = item.select_one("h3.title a, .title a")
        view_el  = item.select_one(".hits, .count_view")
        like_el  = item.select_one(".recomm, .count_like")

        if not title_el:
            continue

        href = title_el.get("href", "")
        if not href.startswith("/"):
            continue

        posts.append({
            "title": title_el.text.strip(),
            "url":   BASE_URL + href,
            "view":  _parse_num(view_el),
            "like":  _parse_num(like_el),
            "board": board_key,
        })

    return posts


def fetch_post_image(url: str) -> str:
    """게시글 본문 첫 번째 이미지 추출"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        img = soup.select_one(".xe_content img, .rd_body img")
        if img:
            src = img.get("src") or img.get("data-src") or ""
            if src.startswith("//"):
                src = "https:" + src
            return src
        return ""
    except Exception:
        return ""


def _parse_num(el) -> int:
    if not el:
        return 0
    try:
        return int(el.text.strip().replace(",", "").replace("조회", "").strip())
    except ValueError:
        return 0


def run(pages: int = 3):
    total_new = 0

    for board_key, board_name in BOARDS.items():
        log.info(f"수집 시작: {board_name} ({board_key})")

        for page in range(1, pages + 1):
            posts = fetch_board(board_key, page)
            log.info(f"  p{page} → {len(posts)}건")

            for post in posts:
                if post["view"] < 300:
                    continue

                image_url = fetch_post_image(post["url"])

                saved = save_meme(
                    title=post["title"],
                    url=post["url"],
                    source="fmkorea",
                    platform="domestic",
                    image_url=image_url,
                    view_count=post["view"],
                    like_count=post["like"],
                    extra={"board": post["board"]},
                )
                if saved:
                    total_new += 1

                time.sleep(random.uniform(1.5, 3.0))

            time.sleep(random.uniform(2.0, 4.0))

    log.info(f"에펨코리아 완료 — 신규 {total_new}건 저장")
    return total_new


if __name__ == "__main__":
    run()
