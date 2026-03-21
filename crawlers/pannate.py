"""
네이트판 크롤러 v2
- pann.nate.com/talk/ranking — 톡커들의 선택 (실시간 인기)
- JavaScript 렌더링 없이 파싱 가능
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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://pann.nate.com/",
}

BASE_URL = "https://pann.nate.com"

BOARDS = [
    {"url": f"{BASE_URL}/talk/ranking",       "name": "실시간 인기"},
    {"url": f"{BASE_URL}/talk/ranking?type=d","name": "일간 인기"},
    {"url": f"{BASE_URL}/talk/c20030",        "name": "엔터톡"},
]


def fetch_board(url: str, name: str) -> list[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        posts = []
        seen  = set()

        # 네이트판 실제 HTML 구조
        for item in soup.select("ul.talk_list li, .list_talk li, .ranking_list li, li.item"):
            title_el = item.select_one("a.subject, a.tit, strong a, .title a, h4 a, h3 a, a[href*='/talk/']")
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

            # 조회수/추천수
            view_el = item.select_one(".num_view, .view, span.cnt")
            like_el = item.select_one(".num_recomm, .recomm, .like")
            view_count = 0
            like_count = 0
            if view_el:
                try:
                    view_count = int(view_el.text.strip().replace(",","").replace("조회","").strip())
                except Exception:
                    pass
            if like_el:
                try:
                    like_count = int(like_el.text.strip().replace(",","").replace("추천","").strip())
                except Exception:
                    pass

            posts.append({
                "title":      title,
                "url":        url_full,
                "view_count": view_count,
                "like_count": like_count,
            })

        # 셀렉터 실패 시 a[href*='/talk/'] 폴백
        if not posts:
            for a in soup.select("a[href*='/talk/']"):
                title = a.text.strip()
                href  = a.get("href", "")
                if not title or not href or href in seen or len(title) < 5:
                    continue
                if href in ("/talk/ranking", "/talk/"):
                    continue
                seen.add(href)
                url_full = BASE_URL + href if href.startswith("/") else href
                posts.append({"title": title, "url": url_full, "view_count": 0, "like_count": 0})

        return posts

    except Exception as e:
        log.warning(f"네이트판 {name} 실패: {e}")
        return []


def run():
    total_new = 0
    global_seen = set()

    for board in BOARDS:
        log.info(f"수집: 네이트판 {board['name']}")
        posts = fetch_board(board["url"], board["name"])

        unique = [p for p in posts if p["url"] not in global_seen]
        for p in unique:
            global_seen.add(p["url"])

        log.info(f"  → {len(unique)}건")

        for post in unique:
            category = classify_category(post["title"])
            saved = save_meme(
                title=post["title"], url=post["url"],
                source="pannate", platform="domestic",
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
