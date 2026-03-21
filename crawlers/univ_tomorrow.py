"""
대학내일 크롤러 v4
- univ20.com 실제 URL 재확인
"""

import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from utils.db import save_meme
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [univ20] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://univ20.com/",
}

BASE_URL = "https://univ20.com"

SECTIONS = [
    {"url": BASE_URL,                          "name": "메인"},
    {"url": f"{BASE_URL}/trendy",              "name": "트렌디"},
    {"url": f"{BASE_URL}/hot",                 "name": "핫"},
    {"url": f"{BASE_URL}/culture",             "name": "컬처"},
]


def fetch_section(url: str, name: str) -> list[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        items = []
        seen  = set()

        # 다양한 셀렉터 시도
        for el in soup.select("a[href*='univ20.com'], article a, .post a, h2 a, h3 a, h4 a, .title a, .headline a"):
            title = el.text.strip()
            href  = el.get("href", "")
            if not title or not href or href in seen:
                continue
            if len(title) < 5:
                continue
            if href in (BASE_URL, BASE_URL + "/", "#", "/"):
                continue

            if not href.startswith("http"):
                href = BASE_URL + href

            seen.add(href)

            img_el = el.find_previous("img") or el.find_next("img")
            image_url = ""
            if img_el:
                image_url = img_el.get("src") or img_el.get("data-src") or ""

            items.append({"title": title, "url": href, "image_url": image_url})

        return items[:20]
    except Exception as e:
        log.warning(f"대학내일 {name} 실패: {e}")
        return []


def run():
    total_new = 0
    global_seen = set()

    for section in SECTIONS:
        log.info(f"수집: {section['name']}")
        items = fetch_section(section["url"], section["name"])

        unique = []
        for item in items:
            if item["url"] not in global_seen:
                global_seen.add(item["url"])
                unique.append(item)

        log.info(f"  → {len(unique)}건")

        for item in unique:
            category = classify_category(item["title"])
            saved = save_meme(
                title=item["title"], url=item["url"],
                source="univ_tomorrow", platform="domestic",
                image_url=item["image_url"], category=category,
                extra={"section": section["name"]},
            )
            if saved:
                total_new += 1

        time.sleep(random.uniform(1.5, 3.0))

    log.info(f"대학내일 완료 — 신규 {total_new}건")
    return total_new

if __name__ == "__main__":
    run()
