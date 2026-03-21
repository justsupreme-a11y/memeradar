"""
디스패치 크롤러
- dispatch.co.kr/category/exclusive — [단독] 기사만
- 셀럽/연예인 밈/이슈 원산지
"""

import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from utils.db import save_meme
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [dispatch] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://www.dispatch.co.kr/",
}

BASE_URL = "https://www.dispatch.co.kr"

PAGES = [
    {"url": f"{BASE_URL}/category/exclusive", "name": "단독"},
    {"url": f"{BASE_URL}/category/star",      "name": "스타"},
    {"url": f"{BASE_URL}",                    "name": "메인"},
]

# 단독 기사 신호 키워드
EXCLUSIVE_KEYWORDS = ["[단독]", "단독", "열애", "결별", "결혼", "임신", "이별", "스캔들"]


def fetch_page(url: str, name: str) -> list[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        items = []
        seen  = set()

        for el in soup.select("article a, .post-title a, h2 a, h3 a, .entry-title a, a[href*='dispatch.co.kr']"):
            title = el.text.strip()
            href  = el.get("href", "")

            if not title or not href or href in seen:
                continue
            if len(title) < 5:
                continue
            if href in (BASE_URL, BASE_URL + "/", "#"):
                continue

            seen.add(href)

            if not href.startswith("http"):
                href = BASE_URL + href

            img_el = el.find_previous("img") or el.find_next("img")
            image_url = ""
            if img_el:
                image_url = img_el.get("src") or img_el.get("data-src") or ""

            items.append({
                "title":     title,
                "url":       href,
                "image_url": image_url,
            })

        return items[:30]

    except Exception as e:
        log.warning(f"디스패치 {name} 실패: {e}")
        return []


def is_exclusive(title: str) -> bool:
    return any(kw in title for kw in EXCLUSIVE_KEYWORDS)


def run():
    total_new = 0
    global_seen = set()

    for page in PAGES:
        log.info(f"수집: 디스패치 {page['name']}")
        items = fetch_page(page["url"], page["name"])

        unique = [i for i in items if i["url"] not in global_seen]
        for i in unique:
            global_seen.add(i["url"])

        log.info(f"  → {len(unique)}건")

        for item in unique:
            category = classify_category(item["title"])
            if category == "general":
                category = "celeb"

            saved = save_meme(
                title=item["title"],
                url=item["url"],
                source="dispatch",
                platform="domestic",
                image_url=item["image_url"],
                category=category,
                extra={
                    "section":    page["name"],
                    "exclusive":  is_exclusive(item["title"]),
                },
                skip_filter=True,  # 디스패치는 자체 큐레이션
            )
            if saved:
                total_new += 1

        time.sleep(random.uniform(2.0, 3.0))

    log.info(f"디스패치 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
