"""
웃긴대학(humoruniv) 크롤러
- 실제 도메인: web.humoruniv.com (구 ucduk.py가 잘못된 도메인 ucduk.com을 사용 — 대체)
- 유머자료실(pds) 게시판, 정적 서버 렌더링 HTML — requests + BeautifulSoup으로 파싱 가능
"""

import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from utils.db import save_meme
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [humoruniv] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://web.humoruniv.com/",
}

BASE_URL  = "https://web.humoruniv.com/board/humor/"
LIST_URL  = BASE_URL + "list.html?table=pds"

MIN_LIKE_COUNT = 5  # 최소 품질 기준 — 추천수 낮은 잡글 제외


def fetch_list() -> list[dict]:
    try:
        resp = requests.get(LIST_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        posts = []
        for row in soup.select("tr[id^='li_chk_']"):
            title_el = row.select_one("td.li_sbj span[id^='title_chk_']")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 3:
                continue

            link_el = row.select_one("td.li_sbj a[href*='read.html']")
            href = link_el.get("href", "") if link_el else ""
            if not href:
                continue
            url_full = href if href.startswith("http") else BASE_URL + href.lstrip("/")

            # 썸네일
            img_el = row.select_one("td.li_num img.thumb")
            image_url = img_el.get("src", "") if img_el else ""
            if image_url and image_url.startswith("//"):
                image_url = "https:" + image_url

            # 조회수 / 추천수 — td.li_und 두 개 (첫번째: 조회, 두번째: 추천 span.o)
            und_cells = row.select("td.li_und")
            view_count = 0
            like_count = 0
            if len(und_cells) >= 1:
                try:
                    view_count = int(und_cells[0].get_text(strip=True).replace(",", ""))
                except Exception:
                    pass
            if len(und_cells) >= 2:
                like_el = und_cells[1].select_one("span.o") or und_cells[1]
                try:
                    like_count = int(like_el.get_text(strip=True).replace(",", ""))
                except Exception:
                    pass

            posts.append({
                "title":      title,
                "url":        url_full,
                "image_url":  image_url,
                "view_count": view_count,
                "like_count": like_count,
            })

        return posts

    except Exception as e:
        log.warning(f"목록 수집 실패: {e}")
        return []


def run():
    total_new = 0
    log.info("수집: 웃긴대학 유머자료실")

    posts = fetch_list()
    log.info(f"  → {len(posts)}건 발견")

    for post in posts:
        if post["like_count"] < MIN_LIKE_COUNT:
            continue

        category = classify_category(post["title"])
        saved = save_meme(
            title=post["title"], url=post["url"],
            source="humoruniv", platform="domestic",
            image_url=post["image_url"],
            view_count=post["view_count"],
            like_count=post["like_count"],
            category=category,
        )
        if saved:
            total_new += 1

    time.sleep(random.uniform(1.0, 2.0))

    log.info(f"웃긴대학 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()

