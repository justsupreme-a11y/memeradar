"""
데일리패션 크롤러
- dailyfashion.co.kr — 패션 뉴스 전문 미디어
- 스트릿패션 / 브랜드 / 트렌드
"""

import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from utils.db import save_meme
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [dailyfashion] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://www.dailyfashion.co.kr/",
}

BASE_URL = "https://www.dailyfashion.co.kr"

SECTIONS = [
    {"url": BASE_URL,                              "name": "메인"},
    {"url": f"{BASE_URL}/news/articleList.html",   "name": "뉴스"},
    {"url": f"{BASE_URL}/section/section002.html", "name": "트렌드"},
]


def fetch_section(url: str, name: str) -> list[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        items = []
        seen  = set()

        for el in soup.select(".article-title a, .item-title a, h2 a, h3 a, h4 a, .titles a, a.title"):
            title = el.text.strip()
            href  = el.get("href", "")
            if not title or not href or href in seen:
                continue
            if len(title) < 5:
                continue
            seen.add(href)

            if not href.startswith("http"):
                href = BASE_URL + href

            img_el = el.find_previous("img") or el.find_next("img")
            image_url = ""
            if img_el:
                image_url = img_el.get("src") or img_el.get("data-src") or ""

            items.append({"title": title, "url": href, "image_url": image_url})

        return items[:20]

    except Exception as e:
        log.warning(f"데일리패션 {name} 실패: {e}")
        return []


def run():
    total_new = 0
    global_seen = set()

    for section in SECTIONS:
        log.info(f"수집: 데일리패션 {section['name']}")
        items = fetch_section(section["url"], section["name"])

        unique = [i for i in items if i["url"] not in global_seen]
        for i in unique:
            global_seen.add(i["url"])

        log.info(f"  → {len(unique)}건")

        for item in unique:
            category = classify_category(item["title"])
            if category == "general":
                category = "fashion"

            saved = save_meme(
                title=item["title"],
                url=item["url"],
                source="dailyfashion",
                platform="domestic",
                image_url=item["image_url"],
                category=category,
                extra={"section": section["name"]},
                skip_filter=True,
            )
            if saved:
                total_new += 1

        time.sleep(random.uniform(1.5, 2.5))

    log.info(f"데일리패션 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
