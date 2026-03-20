"""
마케팅 인사이트 크롤러
- HS애드 블로그: "이달의 밈집" 등 마케터 큐레이션
- 대홍기획 매거진: 트렌드 분석
- 오픈서베이 블로그: 소비자 트렌드 데이터
"""

import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from utils.db import save_meme
from utils.category import classify_category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [mkt_insight] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

SOURCES = [
    {
        "name":      "HS애드 블로그",
        "source":    "hsad",
        "urls":      ["https://blog.hsad.co.kr/category/trend/"],
        "selectors": [".entry-title a", "h2 a", "h3 a", ".post-title a"],
        "base":      "https://blog.hsad.co.kr",
    },
    {
        "name":      "대홍기획 매거진",
        "source":    "daehong",
        "urls":      ["https://magazine.daehong.com/trend"],
        "selectors": [".article-title a", ".title a", "h2 a", "h3 a"],
        "base":      "https://magazine.daehong.com",
    },
    {
        "name":      "오픈서베이 블로그",
        "source":    "opensurvey",
        "urls":      ["https://blog.opensurvey.co.kr/trendreport/"],
        "selectors": [".entry-title a", "h2 a", ".post-title a"],
        "base":      "https://blog.opensurvey.co.kr",
    },
]


def fetch_source(src: dict) -> list[dict]:
    items = []
    seen  = set()

    for url in src["urls"]:
        try:
            headers = {**HEADERS, "Referer": src["base"] + "/"}
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            for sel in src["selectors"]:
                for el in soup.select(sel):
                    title = el.text.strip()
                    href  = el.get("href", "")
                    if not title or not href or href in seen:
                        continue
                    if len(title) < 5:
                        continue
                    seen.add(href)

                    if not href.startswith("http"):
                        href = src["base"] + href

                    img_el = el.find_previous("img") or el.find_next("img")
                    image_url = ""
                    if img_el:
                        image_url = img_el.get("src") or img_el.get("data-src") or ""

                    items.append({
                        "title":     title,
                        "url":       href,
                        "image_url": image_url,
                    })

            time.sleep(random.uniform(1.0, 2.0))

        except Exception as e:
            log.warning(f"{src['name']} {url} 실패: {e}")

    return items[:20]


def run():
    total_new = 0

    for src in SOURCES:
        log.info(f"수집: {src['name']}")
        items = fetch_source(src)
        log.info(f"  → {len(items)}건")

        for item in items:
            category = classify_category(item["title"])
            if category == "general":
                category = "trend"

            saved = save_meme(
                title=item["title"],
                url=item["url"],
                source=src["source"],
                platform="domestic",
                image_url=item["image_url"],
                category=category,
                extra={"source_name": src["name"]},
            )
            if saved:
                total_new += 1

        time.sleep(random.uniform(2.0, 3.0))

    log.info(f"마케팅 인사이트 완료 — 신규 {total_new}건")
    return total_new


if __name__ == "__main__":
    run()
