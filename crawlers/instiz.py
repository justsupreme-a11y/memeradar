"""
인스티즈 크롤러 v2
- 실제 URL: instiz.net/hot.htm (HOT 인기글)
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://www.instiz.net/",
}

BASE_URL = "https://www.instiz.net"

BOARDS = [
    {"url": f"{BASE_URL}/hot.htm",         "name": "HOT 인기글"},
    {"url": f"{BASE_URL}/hot.htm?type=2",  "name": "연예 인기글"},
    {"url": f"{BASE_URL}/hot.htm?type=1",  "name": "이슈 인기글"},
]


def fetch_board(url: str, name: str) -> list[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        posts = []
        seen = set()

        # 인스티즈 HOT 페이지 실제 셀렉터
        for item in soup.select(".hotissue_wrap li, .hot_list li, li.item"):
            title_el = item.select_one("a")
            if not title_el:
                continue

            title = title_el.text.strip()
            href  = title_el.get("href", "")

            if not title or not href or href in seen:
                continue
            if len(title) < 3:
                continue

            seen.add(href)
            if not href.startswith("http"):
                href = BASE_URL + href

            # 조회수 파싱
            view_el    = item.select_one(".count, .views, .view")
            view_count = 0
            if view_el:
                try:
                    view_count = int(view_el.text.strip().replace(",", ""))
                except Exception:
                    pass

            posts.append({
                "title":      title,
                "url":        href,
                "view_count": view_count,
            })

        # 셀렉터가 안 맞으면 모든 a 태그에서 추출
        if not posts:
            for a in soup.select("a[href*='/pt/']"):
                title = a.text.strip()
                href  = a.get("href", "")
                if not title or not href or href in seen or len(title) < 3:
                    continue
                seen.add(href)
                if not href.startswith("http"):
                    href = BASE_URL + href
                posts.append({"title": title, "url": href, "view_count": 0})

        return posts

    except Exception as e:
        log.warning(f"인스티즈 {name} 실패: {e}")
        return []


def run():
    total_new = 0

    for board in BOARDS:
        log.info(f"수집: {board['name']}")
        posts = fetch_board(board["url"], board["name"])
        log.info(f"  → {len(posts)}건")

        for post in posts:
            category = classify_category(post["title"])
            if category == "general":
                category = "celeb"

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
