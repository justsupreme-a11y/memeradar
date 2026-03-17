"""
디시인사이드 크롤러
- 대상: 유머/짤방 게시판 (humor, gall)
- 방식: requests + BeautifulSoup
- 주기: 1~2시간 (GitHub Actions cron)
"""

import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from utils.db import save_meme

logging.basicConfig(level=logging.INFO, format="%(asctime)s [dci] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.dcinside.com/",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# 수집할 게시판 목록 (갤러리ID: 이름)
BOARDS = {
    "humor": "유머",
    "humorpan": "유머짤방",
    "meme_image": "밈",
}

BASE_URL = "https://gall.dcinside.com/board/lists"


def fetch_board(gallery_id: str, page: int = 1) -> list[dict]:
    """게시판 한 페이지 목록 수집"""
    params = {
        "id": gallery_id,
        "page": page,
        "exception_mode": "recommend",  # 추천 게시물만
    }
    try:
        resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.warning(f"요청 실패 {gallery_id} p{page}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    posts = []

    for row in soup.select("tr.us-post, tr.ub-content"):
        # 공지/광고 제외
        if row.select_one(".icon_notice") or row.select_one(".icon_ad"):
            continue

        title_el = row.select_one(".gall_tit a:first-child")
        num_el   = row.select_one(".gall_num")
        view_el  = row.select_one(".gall_count")
        like_el  = row.select_one(".gall_recommend")

        if not title_el:
            continue

        post_no = num_el.text.strip() if num_el else ""
        if not post_no.isdigit():
            continue

        posts.append({
            "title":     title_el.text.strip(),
            "url":       f"https://gall.dcinside.com/board/view/?id={gallery_id}&no={post_no}",
            "view":      int(view_el.text.strip().replace(",", "")) if view_el else 0,
            "like":      int(like_el.text.strip().replace(",", "")) if like_el else 0,
            "gallery":   gallery_id,
        })

    return posts


def fetch_post_image(url: str) -> str:
    """게시글 본문에서 첫 번째 이미지 URL 추출"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        img = soup.select_one(".writing_view_box img")
        return img["src"] if img and img.get("src") else ""
    except Exception:
        return ""


def run(pages: int = 3):
    """
    모든 등록 게시판을 순회하며 수집.
    pages: 게시판당 수집할 페이지 수
    """
    total_new = 0

    for gallery_id, board_name in BOARDS.items():
        log.info(f"수집 시작: {board_name} ({gallery_id})")

        for page in range(1, pages + 1):
            posts = fetch_board(gallery_id, page)
            log.info(f"  p{page} → {len(posts)}건")

            for post in posts:
                # 조회수 임계값 — 너무 낮은 건 스킵
                if post["view"] < 500:
                    continue

                image_url = fetch_post_image(post["url"])

                saved = save_meme(
                    title=post["title"],
                    url=post["url"],
                    source="dcinside",
                    platform="domestic",
                    image_url=image_url,
                    view_count=post["view"],
                    like_count=post["like"],
                    extra={"gallery": post["gallery"]},
                )
                if saved:
                    total_new += 1

                # 예의 바른 딜레이 (IP 차단 방지)
                time.sleep(random.uniform(1.5, 3.0))

            time.sleep(random.uniform(2.0, 4.0))

    log.info(f"디시인사이드 완료 — 신규 {total_new}건 저장")
    return total_new


if __name__ == "__main__":
    run()
